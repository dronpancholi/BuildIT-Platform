"""
SEO Platform — Storage Adapter
================================
Pluggable storage architecture. Supports local MinIO for zero-cost dev.
Includes bounded timeouts and a circuit breaker so the API never hangs
when MinIO is unreachable.
"""

import threading
import time
from collections import deque

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError, EndpointConnectionError

from seo_platform.config import get_settings
from seo_platform.core.logging import get_logger

logger = get_logger(__name__)


class CircuitOpenError(Exception):
    """Raised when the storage circuit breaker is open and short-circuits calls."""


class _StorageCircuitBreaker:
    """
    Trips after `failure_threshold` consecutive failures.
    Stays open for `reset_timeout_s` before allowing a single probe call.
    Half-open on probe success; re-opens on probe failure.
    """

    def __init__(self, failure_threshold: int = 5, reset_timeout_s: float = 30.0):
        self.failure_threshold = failure_threshold
        self.reset_timeout_s = reset_timeout_s
        self._lock = threading.Lock()
        self._failures: deque[float] = deque()
        self._opened_at: float | None = None
        self._state: str = "closed"  # closed | open | half_open

    def _record_success(self) -> None:
        with self._lock:
            self._failures.clear()
            self._opened_at = None
            self._state = "closed"

    def _record_failure(self) -> None:
        with self._lock:
            now = time.monotonic()
            self._failures.append(now)
            cutoff = now - 60.0
            while self._failures and self._failures[0] < cutoff:
                self._failures.popleft()
            if len(self._failures) >= self.failure_threshold:
                self._state = "open"
                self._opened_at = now
                logger.warning("storage_circuit_breaker_opened", failures=len(self._failures))

    def _allow(self) -> bool:
        with self._lock:
            if self._state == "closed":
                return True
            if self._state == "open":
                if self._opened_at is None or (time.monotonic() - self._opened_at) >= self.reset_timeout_s:
                    self._state = "half_open"
                    logger.info("storage_circuit_breaker_half_open")
                    return True
                return False
            return True

    def state(self) -> str:
        with self._lock:
            return self._state


_circuit = _StorageCircuitBreaker(failure_threshold=5, reset_timeout_s=30.0)


class StorageAdapter:
    def __init__(self):
        settings = get_settings()
        self.s3 = boto3.client(
            's3',
            endpoint_url=settings.s3_endpoint if hasattr(settings, 's3_endpoint') else None,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=Config(
                signature_version='s3v4',
                connect_timeout=2,
                read_timeout=5,
                retries={"max_attempts": 2, "mode": "standard"},
            ),
            region_name=settings.s3_region
        )
        self.bucket = settings.s3_bucket_name

    def _call(self, fn, *args, **kwargs):
        if not _circuit._allow():
            raise CircuitOpenError("storage circuit breaker is open")
        try:
            result = fn(*args, **kwargs)
        except (BotoCoreError, ClientError, EndpointConnectionError, OSError) as e:
            _circuit._record_failure()
            logger.error("storage_call_failed", error=str(e))
            raise
        _circuit._record_success()
        return result

    def upload_fileobj(self, file_obj, object_name: str):
        """Uploads a file-like object to S3-compatible storage."""
        try:
            self._call(self.s3.upload_fileobj, file_obj, self.bucket, object_name)
            logger.info("storage_upload_success", object=object_name)
        except Exception as e:
            logger.error("storage_upload_failed", error=str(e))
            raise

    def upload_file(self, file_path: str, object_name: str):
        """Uploads a file to the S3-compatible storage."""
        try:
            self._call(self.s3.upload_file, file_path, self.bucket, object_name)
            logger.info("storage_upload_success", object=object_name)
        except Exception as e:
            logger.error("storage_upload_failed", error=str(e))
            raise

    def download_file(self, object_name: str, file_path: str):
        """Downloads a file from S3-compatible storage."""
        try:
            self._call(self.s3.download_file, self.bucket, object_name, file_path)
            logger.info("storage_download_success", object=object_name)
        except Exception as e:
            logger.error("storage_download_failed", error=str(e))
            raise

    def delete_file(self, object_name: str):
        """Deletes a file from S3-compatible storage."""
        try:
            self._call(self.s3.delete_object, Bucket=self.bucket, Key=object_name)
            logger.info("storage_delete_success", object=object_name)
        except Exception as e:
            logger.error("storage_delete_failed", error=str(e))
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

    def ensure_bucket(self):
        """Ensure the configured bucket exists."""
        try:
            self._call(self.s3.head_bucket, Bucket=self.bucket)
            logger.info("storage_bucket_exists", bucket=self.bucket)
        except Exception:
            self._call(self.s3.create_bucket, Bucket=self.bucket)
            logger.info("storage_bucket_created", bucket=self.bucket)

    def circuit_state(self) -> str:
        return _circuit.state()


storage_adapter = StorageAdapter()
