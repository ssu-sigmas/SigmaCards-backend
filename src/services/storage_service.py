from io import BytesIO

from botocore.client import Config
import boto3
from pypdf import PdfReader

from src.core.config import settings
# TODO: refactor it all blin...
ALLOWED_IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/webp"}
ALLOWED_PDF_MIME_TYPES = {"application/pdf"}


class StorageService:
    PDF_MAX_SIZE_BYTES = 50 * 1024 * 1024

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
    def generate_upload_url(object_name: str, content_type: str, max_size_bytes: int = settings.IMAGE_MAX_SIZE_BYTES):
        if content_type not in ALLOWED_IMAGE_MIME_TYPES and content_type not in ALLOWED_PDF_MIME_TYPES:
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
                ["content-length-range", 1, max_size_bytes],
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
    
    @staticmethod
    def upload_chunk_object(object_name: str, text: str):
        client = StorageService.get_s3_client()

        client.put_object(
            Bucket=settings.S3_BUCKET_TEXT,
            Key=object_name,
            Body=text.encode("utf-8"),
            ContentType="text/plain",
            CacheControl="no-store",
        )

    @staticmethod
    def build_chunk_key(generation_id: str, chunk_id: str) -> str:
        return f"chunks/{generation_id}/{chunk_id}.txt"
    
    @staticmethod
    def get_chunk_object_url(object_name: str) -> str:
        base = settings.S3_PUBLIC_ENDPOINT.rstrip("/")
        return f"{base}/{settings.S3_BUCKET_TEXT}/{object_name}"
    
    @staticmethod
    def ensure_chunks_lifecycle(days: int = 3):
        client = StorageService.get_s3_client()

        lifecycle_config = {
            "Rules": [
                {
                    "ID": "auto-delete-chunks",
                    "Status": "Enabled",
                    "Filter": {"Prefix": "chunks/"},
                    "Expiration": {"Days": days},
                }
            ]
        }

        client.put_bucket_lifecycle_configuration(
            Bucket=settings.S3_BUCKET_TEXT,
            LifecycleConfiguration=lifecycle_config,
        )    

    @staticmethod
    def get_object_bytes(bucket: str, object_name: str) -> bytes:
        client = StorageService.get_s3_client()
        response = client.get_object(Bucket=bucket, Key=object_name)
        return response["Body"].read()

    @staticmethod
    def get_pdf_page_count(object_name: str) -> int:
        file_bytes = StorageService.get_object_bytes(settings.S3_BUCKET, object_name)
        reader = PdfReader(BytesIO(file_bytes))
        return len(reader.pages)

    @staticmethod
    def get_s3_url(bucket: str, object_name: str) -> str:
        base = settings.S3_PUBLIC_ENDPOINT.rstrip("/")
        return f"{base}/{bucket}/{object_name}"