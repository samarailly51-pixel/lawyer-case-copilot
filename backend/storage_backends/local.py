from __future__ import annotations

import base64
import hashlib
import re
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from core.config import settings
from .base import StorageBackend, StoredObject


class LocalStorageBackend(StorageBackend):
    def _cipher(self) -> AESGCM:
        if not settings.storage_encryption_key:
            raise RuntimeError("ENCRYPT_UPLOADS=true 时必须配置 STORAGE_ENCRYPTION_KEY")
        try:
            key = base64.urlsafe_b64decode(settings.storage_encryption_key)
        except Exception as exc:
            raise RuntimeError("STORAGE_ENCRYPTION_KEY 必须是 URL-safe Base64") from exc
        if len(key) != 32:
            raise RuntimeError("STORAGE_ENCRYPTION_KEY 解码后必须为 32 字节")
        return AESGCM(key)

    def put(self, case_id: str, filename: str, content: bytes) -> StoredObject:
        digest = hashlib.sha256(content).hexdigest()
        safe_name = re.sub(r"[^\w.\-\u4e00-\u9fff]", "_", Path(filename).name)
        relative = Path(case_id) / f"{digest[:12]}_{safe_name}"
        target = settings.upload_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if settings.encrypt_uploads:
            nonce = hashlib.sha256(f"{case_id}:{digest}".encode()).digest()[:12]
            target = target.with_suffix(target.suffix + ".enc")
            target.write_bytes(nonce + self._cipher().encrypt(nonce, content, case_id.encode()))
            relative = relative.with_suffix(relative.suffix + ".enc")
        else:
            target.write_bytes(content)
        key = relative.as_posix()
        return StoredObject(key=key, uri=f"local://{key}", sha256=digest, encrypted=settings.encrypt_uploads)

    def get(self, key: str) -> bytes:
        content = (settings.upload_dir / key).read_bytes()
        if key.endswith(".enc"):
            nonce, encrypted = content[:12], content[12:]
            case_id = key.split("/", 1)[0]
            return self._cipher().decrypt(nonce, encrypted, case_id.encode())
        return content

