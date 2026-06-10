from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import fitz
import pytest

from app.models.documents import DocumentType
from app.pipeline.extraction import CvTextExtractor, DocumentExtractionError


def build_pdf_bytes(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    pdf_bytes = document.tobytes()
    document.close()
    return pdf_bytes


def build_docx_bytes(text: str) -> bytes:
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>{text}</w:t></w:r></w:p>
  </w:body>
</w:document>
"""
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


def test_extracts_text_from_pdf() -> None:
    extractor = CvTextExtractor()

    result = extractor.extract("candidate.pdf", build_pdf_bytes("Python FastAPI Azure AI"))

    assert result.document_type == DocumentType.PDF
    assert "Python FastAPI Azure AI" in result.text
    assert result.character_count == len(result.text)


def test_extracts_text_from_docx() -> None:
    extractor = CvTextExtractor()

    result = extractor.extract("candidate.docx", build_docx_bytes("Microsoft Graph experience"))

    assert result.document_type == DocumentType.DOCX
    assert result.text == "Microsoft Graph experience"


def test_rejects_corrupt_pdf() -> None:
    extractor = CvTextExtractor()

    with pytest.raises(DocumentExtractionError):
        extractor.extract("candidate.pdf", b"not a pdf")


def test_rejects_empty_docx_text() -> None:
    extractor = CvTextExtractor()

    with pytest.raises(DocumentExtractionError):
        extractor.extract("candidate.docx", build_docx_bytes(""))

