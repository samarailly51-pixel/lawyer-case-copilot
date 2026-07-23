from __future__ import annotations

import json
from pathlib import Path

from .base import RetrievedSource, Retriever


class LocalKnowledgeRetriever(Retriever):
    """Small verified-metadata retriever; intentionally ships without legal conclusions."""

    def __init__(self, root: Path | None = None):
        self.root = root or Path(__file__).resolve().parents[2] / "knowledge_base"

    def retrieve(self, query: str, scopes: list[str], limit: int = 5) -> list[RetrievedSource]:
        results: list[RetrievedSource] = []
        query_terms = {term.lower() for term in query.split() if term.strip()}
        for scope in scopes:
            path = self.root / scope / "index.json"
            if not path.exists():
                continue
            for item in json.loads(path.read_text(encoding="utf-8")):
                haystack = f"{item.get('title', '')} {item.get('excerpt', '')}".lower()
                if query_terms and not any(term in haystack for term in query_terms):
                    continue
                results.append(RetrievedSource(**item))
        return results[:limit]

