from botocore.client import Config
import boto3

from src.core.config import settings

ALLOWED_IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/webp"}


class StorageService:
    @staticmethod
    def get_s3_client():
        return boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            config=Config(signature_version="s3v4"),
        )
    
    @staticmethod
    def generate_upload_url(object_name: str, content_type: str):
        if content_type not in ALLOWED_IMAGE_MIME_TYPES:
            raise ValueError("Unsupported MIME type")
        
        client = StorageService.get_s3_client()
        post = client.generate_presigned_post(
            Bucket=settings.S3_BUCKET,
            Key=object_name,
            Fields={
                "Content-Type": content_type,
                "Cache-Control": "public, max-age=31536000, immutable",
            },
            Conditions=[
                {"Content-Type": content_type},
                {"Cache-Control": "public, max-age=31536000, immutable"},
                ["content-length-range", 1, settings.IMAGE_MAX_SIZE_BYTES],
            ],
            ExpiresIn=settings.IMAGE_UPLOAD_URL_TTL_SECONDS,
        )

        post["url"] = post["url"].replace(
            settings.S3_ENDPOINT,
            settings.S3_PUBLIC_ENDPOINT
        )

        return {
            "upload_url": post["url"],
            "upload_fields": post["fields"],
            "required_headers": {},
            "method": "POST",
            "expires_in": settings.IMAGE_UPLOAD_URL_TTL_SECONDS,
        }
    
    @staticmethod
    def delete_object(object_name: str):
        client = StorageService.get_s3_client()
        client.delete_object(Bucket=settings.S3_BUCKET, Key=object_name)

    @staticmethod
    def get_public_object_url(object_name: str) -> str:
        base = settings.S3_PUBLIC_ENDPOINT.rstrip('/')
        return f"{base}/{settings.S3_BUCKET}/{object_name}"