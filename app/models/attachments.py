from base64 import b64decode

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GraphFileAttachment(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    odata_type: str = Field(alias="@odata.type")
    id: str
    name: str
    content_type: str | None = Field(default=None, alias="contentType")
    size: int = Field(ge=0)
    is_inline: bool = Field(default=False, alias="isInline")
    content_bytes: str | None = Field(default=None, alias="contentBytes")

    @field_validator("odata_type")
    @classmethod
    def require_file_attachment(cls, value: str) -> str:
        if value.lower() != "#microsoft.graph.fileattachment":
            raise ValueError("Only Microsoft Graph fileAttachment objects are supported.")
        return value

    def decoded_content(self) -> bytes:
        if self.content_bytes is None:
            return b""
        return b64decode(self.content_bytes, validate=True)


class GraphAttachmentCollection(BaseModel):
    value: list[GraphFileAttachment]

