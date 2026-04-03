from pydantic import BaseModel, Field
from uuid import UUID


class PdfUploadUrlRequest(BaseModel):
    content_type: str = Field(default="application/pdf", description="MIME тип PDF")


class PdfUploadUrlResponse(BaseModel):
    file_id: UUID
    upload_url: str
    object_name: str
    expires_in: int
    method: str
    upload_fields: dict[str, str] = Field(default_factory=dict)
    required_headers: dict[str, str] = Field(default_factory=dict)