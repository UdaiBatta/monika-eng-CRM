from abc import ABC, abstractmethod
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string


class StorageBackend(ABC):
    @abstractmethod
    def store(self, file_object, key, content_type): ...

    @abstractmethod
    def open(self, key): ...

    @abstractmethod
    def delete(self, key): ...

    @abstractmethod
    def exists(self, key): ...

    @abstractmethod
    def get_metadata(self, key): ...

    def generate_download_access(self, key, *, expires_seconds=60):
        return None


class LocalPrivateStorageBackend(StorageBackend):
    def __init__(self):
        self.root = Path(settings.LOCAL_PRIVATE_STORAGE_ROOT).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key):
        path = (self.root / key).resolve()
        if self.root not in path.parents:
            raise ValueError("Invalid private storage key.")
        return path

    def store(self, file_object, key, content_type):
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_object.seek(0)
        with path.open("xb") as destination:
            chunks = getattr(file_object, "chunks", None)
            for chunk in chunks() if chunks else iter(lambda: file_object.read(1024 * 1024), b""):
                destination.write(chunk)
        file_object.seek(0)
        return key

    def open(self, key):
        return self._path(key).open("rb")

    def delete(self, key):
        try:
            self._path(key).unlink()
        except FileNotFoundError:
            return

    def exists(self, key):
        return self._path(key).is_file()

    def get_metadata(self, key):
        path = self._path(key)
        return {"size_bytes": path.stat().st_size}


class S3CompatibleStorageBackend(StorageBackend):
    """Cloudflare R2/S3 backend loaded only when explicitly configured."""

    def __init__(self):
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError as exc:
            raise ImproperlyConfigured("Install boto3 before enabling R2 document storage.") from exc
        self.client_error = ClientError
        self.bucket = settings.R2_BUCKET_NAME
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.R2_ENDPOINT_URL,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name=settings.R2_REGION,
        )

    def store(self, file_object, key, content_type):
        file_object.seek(0)
        self.client.upload_fileobj(file_object, self.bucket, key, ExtraArgs={"ContentType": content_type})
        file_object.seek(0)
        return key

    def open(self, key):
        raise NotImplementedError("R2 downloads use short-lived signed access.")

    def delete(self, key):
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def exists(self, key):
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except self.client_error:
            return False

    def get_metadata(self, key):
        response = self.client.head_object(Bucket=self.bucket, Key=key)
        return {"size_bytes": response["ContentLength"], "content_type": response.get("ContentType")}

    def generate_download_access(self, key, *, expires_seconds=60):
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_seconds,
        )


def get_storage():
    backend = import_string(settings.DOCUMENT_STORAGE_BACKEND)
    return backend()
