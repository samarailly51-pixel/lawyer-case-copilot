from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from core.config import settings
from core.database import Base, SessionLocal, init_db
from models.entities import Case, Document
from storage_backends import get_storage_backend


def _storage_key(uri: str) -> str:
    parsed = urlparse(uri)
    if parsed.scheme == "local":
        return f"{parsed.netloc}{parsed.path}".lstrip("/")
    if parsed.scheme == "s3":
        return parsed.path.lstrip("/")
    raise ValueError(f"不支持的存储地址：{uri}")


def expired_case_candidates(db: Session) -> list[Case]:
    if settings.data_retention_days <= 0:
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.data_retention_days)
    return list(db.scalars(select(Case).where(
        Case.is_demo.is_(False),
        Case.status.in_(("closed", "archived")),
        Case.updated_at < cutoff,
    ).order_by(Case.updated_at)))


def purge_expired_cases(db: Session, *, execute: bool = False) -> dict:
    candidates = expired_case_candidates(db)
    result = {
        "execute": execute,
        "retention_days": settings.data_retention_days,
        "candidate_count": len(candidates),
        "deleted_case_ids": [],
        "storage_errors": [],
    }
    if not execute:
        result["candidates"] = [
            {"id": case.id, "title": case.title, "status": case.status, "updated_at": case.updated_at.isoformat()}
            for case in candidates
        ]
        return result

    storage = get_storage_backend()
    for case in candidates:
        documents = list(db.scalars(select(Document).where(Document.case_id == case.id)))
        for document in documents:
            if not document.file_path:
                continue
            try:
                storage.delete(_storage_key(document.file_path))
            except (OSError, ValueError, RuntimeError) as exc:
                result["storage_errors"].append({
                    "case_id": case.id,
                    "document_id": document.id,
                    "error": str(exc),
                })
        if result["storage_errors"] and any(item["case_id"] == case.id for item in result["storage_errors"]):
            continue
        for table in reversed(Base.metadata.sorted_tables):
            if table.name == Case.__tablename__ or "case_id" not in table.c:
                continue
            db.execute(delete(table).where(table.c.case_id == case.id))
        db.execute(delete(Case).where(Case.id == case.id))
        result["deleted_case_ids"].append(case.id)
    db.commit()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview or execute the configured case data-retention policy.")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    if args.execute and args.confirm != "DELETE-EXPIRED-CASES":
        raise SystemExit("执行删除必须同时传入 --confirm DELETE-EXPIRED-CASES")
    init_db()
    with SessionLocal() as db:
        print(json.dumps(purge_expired_cases(db, execute=args.execute), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
