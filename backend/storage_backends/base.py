from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class StoredObject:
    key: str
    uri: str
    sha256: str
    encrypted: bool


class StorageBackend(ABC):
    @abstractmethod
    def put(self, case_id: str, filename: str, content: bytes) -> StoredObject: ...

    @abstractmethod
    def get(self, key: str) -> bytes: ...

