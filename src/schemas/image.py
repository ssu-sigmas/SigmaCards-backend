from pydantic import BaseModel, Field
from uuid import UUID


class ImageUploadUrlRequest(BaseModel):
    content_type: str = Field(..., description="MIME тип изображения")

class ImageUploadUrlResponse(BaseModel):
    image_id: UUID
    upload_url: str
    object_name: str
    expires_in: int
    method: str
    upload_fields: dict[str, str] = Field(default_factory=dict)
    required_headers: dict[str, str] = Field(default_factory=dict)