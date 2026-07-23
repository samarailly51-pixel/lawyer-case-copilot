from functools import lru_cache

from core.config import settings
from .base import StorageBackend
from .local import LocalStorageBackend
from .s3 import S3StorageBackend


@lru_cache(maxsize=1)
def get_storage_backend() -> StorageBackend:
    if settings.storage_backend == "s3":
        return S3StorageBackend()
    return LocalStorageBackend()

