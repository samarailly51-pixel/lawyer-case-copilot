from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass
class RetrievedSource:
    title: str
    excerpt: str
    source_name: str
    source_url: str = ""
    published_or_updated_at: date | None = None
    jurisdiction: str = ""
    scope: str = ""
    stale_risk: bool = True


class Retriever(ABC):
    @abstractmethod
    def retrieve(self, query: str, scopes: list[str], limit: int = 5) -> list[RetrievedSource]:
        raise NotImplementedError

