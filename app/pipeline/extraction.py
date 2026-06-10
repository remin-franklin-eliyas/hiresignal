import xml.etree.ElementTree as ET
from io import BytesIO
from zipfile import BadZipFile, ZipFile

import fitz

from app.models.documents import DocumentType, ExtractedDocument
from app.pipeline.attachments import validate_attachment_type


class DocumentExtractionError(RuntimeError):
    pass


class CvTextExtractor:
    def extract(self, filename: str, content: bytes) -> ExtractedDocument:
        suffix = validate_attachment_type(filename)
        if suffix == ".pdf":
            text = self._extract_pdf_text(content)
            document_type = DocumentType.PDF
        elif suffix == ".docx":
            text = self._extract_docx_text(content)
            document_type = DocumentType.DOCX
        else:
            raise DocumentExtractionError("Unsupported document type.")

        try:
            return ExtractedDocument.from_text(filename, document_type, text)
        except ValueError as exc:
            raise DocumentExtractionError("CV text extraction produced no usable text.") from exc

    @staticmethod
    def _extract_pdf_text(content: bytes) -> str:
        try:
            with fitz.open(stream=content, filetype="pdf") as document:
                return "\n".join(page.get_text("text") for page in document)
        except Exception as exc:
            raise DocumentExtractionError("Unable to extract text from PDF CV.") from exc

    @staticmethod
    def _extract_docx_text(content: bytes) -> str:
        try:
            with ZipFile(BytesIO(content)) as archive:
                xml_content = archive.read("word/document.xml")
        except (BadZipFile, KeyError) as exc:
            raise DocumentExtractionError("Unable to read DOCX CV content.") from exc

        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as exc:
            raise DocumentExtractionError("DOCX CV XML is invalid.") from exc

        paragraphs: list[str] = []
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        for paragraph in root.findall(".//w:p", namespace):
            parts: list[str] = []
            for node in paragraph.iter():
                if node.tag == f"{{{namespace['w']}}}t" and node.text:
                    parts.append(node.text)
                elif node.tag == f"{{{namespace['w']}}}tab":
                    parts.append(" ")
                elif node.tag == f"{{{namespace['w']}}}br":
                    parts.append("\n")
            paragraph_text = "".join(parts).strip()
            if paragraph_text:
                paragraphs.append(paragraph_text)

        return "\n".join(paragraphs)


def get_cv_text_extractor() -> CvTextExtractor:
    return CvTextExtractor()
