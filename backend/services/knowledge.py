from __future__ import annotations

import hashlib
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.entities import KnowledgeSource, KnowledgeWorkspaceLink
from schemas.knowledge import KnowledgeSourceCreate


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
                     workspace_id: str | None = None) -> list[KnowledgeSource]:
    statement = select(KnowledgeSource).where(KnowledgeSource.scope.in_(scopes))
    if workspace_id:
        statement = statement.join(
            KnowledgeWorkspaceLink, KnowledgeWorkspaceLink.knowledge_source_id == KnowledgeSource.id
        ).where(KnowledgeWorkspaceLink.workspace_id == workspace_id)
    candidates = list(db.scalars(statement))
    terms = _terms(query)
    scored: list[tuple[int, KnowledgeSource]] = []
    for item in candidates:
        title = item.title.lower()
        haystack = f"{item.title} {item.excerpt} {item.source_name} {item.jurisdiction} {item.applicability_scope}".lower()
        score = sum(3 if term in title else 1 for term in terms if term in haystack)
        if score:
            score += 2 if item.effective_status == "verified_effective" else 0
            scored.append((score, item))
    scored.sort(key=lambda value: (value[0], value[1].published_or_updated_at), reverse=True)
    return [item for _, item in scored[:limit]]
