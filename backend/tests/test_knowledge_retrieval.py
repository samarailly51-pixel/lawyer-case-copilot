from __future__ import annotations

from datetime import date
from uuid import uuid4

from sqlalchemy.orm import Session

from core.database import SessionLocal
from models.entities import KnowledgeSource
from services.knowledge import search_knowledge


def _source(
    db: Session,
    *,
    title: str,
    status: str,
    stale: bool,
    updated: date,
) -> KnowledgeSource:
    item = KnowledgeSource(
        scope="general",
        title=title,
        excerpt="合同履行证据的完全虚构检索测试片段，不作为法律依据。",
        source_name="合成评测来源",
        source_url="https://example.invalid/synthetic",
        published_or_updated_at=updated,
        jurisdiction="全国",
        applicability_scope="仅用于自动化检索排序测试",
        effective_status=status,
        verified_by="合成评测",
        stale_risk=stale,
        content_hash=uuid4().hex,
        metadata_json={"synthetic": True},
    )
    db.add(item)
    db.flush()
    return item


def test_verified_fresh_source_outranks_stale_historical_source():
    with SessionLocal() as db:
        historical = _source(
            db,
            title="合同履行证据历史样例",
            status="historical",
            stale=True,
            updated=date(2026, 7, 1),
        )
        verified = _source(
            db,
            title="合同履行证据有效样例",
            status="verified_effective",
            stale=False,
            updated=date(2025, 7, 1),
        )
        db.commit()

        results = search_knowledge(db, "合同履行证据", ["general"], limit=10)
        relevant_ids = [item.id for item in results if item.id in {historical.id, verified.id}]
        assert relevant_ids.index(verified.id) < relevant_ids.index(historical.id)


def test_knowledge_search_respects_scope():
    with SessionLocal() as db:
        item = _source(
            db,
            title="限定范围检索样例",
            status="verified_effective",
            stale=False,
            updated=date(2026, 7, 1),
        )
        db.commit()
        assert item not in search_knowledge(db, "限定范围检索", ["traffic_injury"])


def test_verified_only_filter_excludes_stale_and_unverified_sources():
    with SessionLocal() as db:
        verified = _source(
            db,
            title="核验过滤有效样例",
            status="verified_effective",
            stale=False,
            updated=date(2026, 7, 1),
        )
        stale = _source(
            db,
            title="核验过滤过期样例",
            status="verified_effective",
            stale=True,
            updated=date(2026, 7, 1),
        )
        pending = _source(
            db,
            title="核验过滤待核样例",
            status="verification_required",
            stale=False,
            updated=date(2026, 7, 1),
        )
        db.commit()
        results = search_knowledge(
            db,
            "核验过滤",
            ["general"],
            limit=10,
            verified_only=True,
        )
        result_ids = {item.id for item in results}
        assert verified.id in result_ids
        assert stale.id not in result_ids
        assert pending.id not in result_ids
