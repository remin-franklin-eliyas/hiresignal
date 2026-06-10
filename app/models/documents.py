from enum import StrEnum

from pydantic import BaseModel, Field


class DocumentType(StrEnum):
    PDF = "pdf"
    DOCX = "docx"


class ExtractedDocument(BaseModel):
    filename: str
    document_type: DocumentType
    text: str = Field(min_length=1)
    character_count: int = Field(gt=0)

    @classmethod
    def from_text(
        cls,
        filename: str,
        document_type: DocumentType,
        text: str,
    ) -> "ExtractedDocument":
        normalized = " ".join(text.split())
        return cls(
            filename=filename,
            document_type=document_type,
            text=normalized,
            character_count=len(normalized),
        )
