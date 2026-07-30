from __future__ import annotations

import hashlib
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.entities import KnowledgeSource, KnowledgeWorkspaceLink
from schemas.knowledge import KnowledgeSourceCreate


STATUS_SCORE = {
    "verified_effective": 4.0,
    "verification_required": 0.0,
    "historical": -4.0,
}


def create_knowledge_source(db: Session, payload: KnowledgeSourceCreate) -> KnowledgeSource:
    canonical = "|".join((payload.title, payload.excerpt, payload.source_name, payload.source_url))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    existing = db.scalar(select(KnowledgeSource).where(KnowledgeSource.content_hash == digest))
    if existing:
        return existing
    item = KnowledgeSource(**payload.model_dump(), content_hash=digest)
    db.add(item); db.commit(); db.refresh(item)
    return item


def _terms(query: str) -> set[str]:
    latin = re.findall(r"[A-Za-z0-9_-]{2,}", query.lower())
    chinese = []
    for block in re.findall(r"[\u4e00-\u9fff]+", query):
        chinese.extend(block[index:index + 2] for index in range(max(1, len(block) - 1)))
    return set(latin + chinese)


def search_knowledge(db: Session, query: str, scopes: list[str], limit: int = 5,
                     workspace_id: str | None = None, verified_only: bool = False,
                     exclude_historical: bool = False) -> list[KnowledgeSource]:
    statement = select(KnowledgeSource).where(KnowledgeSource.scope.in_(scopes))
    if verified_only:
        statement = statement.where(
            KnowledgeSource.effective_status == "verified_effective",
            KnowledgeSource.stale_risk.is_(False),
        )
    elif exclude_historical:
        statement = statement.where(KnowledgeSource.effective_status != "historical")
    if workspace_id:
        statement = statement.join(
            KnowledgeWorkspaceLink, KnowledgeWorkspaceLink.knowledge_source_id == KnowledgeSource.id
        ).where(KnowledgeWorkspaceLink.workspace_id == workspace_id)
    candidates = list(db.scalars(statement))
    terms = _terms(query)
    scored: list[tuple[float, KnowledgeSource]] = []
    for item in candidates:
        title = item.title.lower()
        excerpt = item.excerpt.lower()
        metadata = f"{item.source_name} {item.jurisdiction} {item.applicability_scope}".lower()
        matched_terms = {
            term for term in terms if term in title or term in excerpt or term in metadata
        }
        if not matched_terms:
            continue
        score = sum(
            4.0 if term in title else 2.0 if term in excerpt else 1.0
            for term in matched_terms
        )
        normalized_query = query.strip().lower()
        if normalized_query and normalized_query in f"{title} {excerpt}":
            score += 6.0
        score += STATUS_SCORE.get(item.effective_status, -1.0)
        if item.stale_risk:
            score -= 2.0
        if item.jurisdiction and item.jurisdiction.lower() in normalized_query:
            score += 2.0
        scored.append((score, item))
    scored.sort(
        key=lambda value: (
            value[0],
            value[1].published_or_updated_at,
            value[1].id,
        ),
        reverse=True,
    )
    return [item for _, item in scored[:limit]]
