from pathlib import Path

ALLOWED_ATTACHMENT_TYPES = {".pdf", ".docx"}


class AttachmentValidationError(ValueError):
    pass


def validate_attachment_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_ATTACHMENT_TYPES:
        raise AttachmentValidationError("Only PDF and DOCX CV attachments are supported.")
    return suffix


def virus_scan_stub(_: bytes) -> bool:
    return True

