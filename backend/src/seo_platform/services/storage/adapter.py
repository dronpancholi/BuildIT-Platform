"""
SEO Platform — Storage Adapter
================================
Pluggable storage architecture. Supports local MinIO for zero-cost dev.
"""

import boto3
from botocore.client import Config

from seo_platform.config import get_settings
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)

class StorageAdapter:
    def __init__(self):
        settings = get_settings()
        self.s3 = boto3.client(
            's3',
            endpoint_url=settings.s3_endpoint if hasattr(settings, 's3_endpoint') else None,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=Config(signature_version='s3v4'),
            region_name=settings.s3_region
        )
        self.bucket = settings.s3_bucket_name

    def upload_file(self, file_path: str, object_name: str):
        """Uploads a file to the S3-compatible storage."""
        try:
            self.s3.upload_file(file_path, self.bucket, object_name)
            logger.info("storage_upload_success", object=object_name)
        except Exception as e:
            logger.error("storage_upload_failed", error=str(e))
            raise

    def get_presigned_url(self, object_name: str, expiration=3600):
        """Generates a presigned URL for the object."""
        try:
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': object_name},
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            logger.error("storage_url_generation_failed", error=str(e))
            return None

storage_adapter = StorageAdapter()
