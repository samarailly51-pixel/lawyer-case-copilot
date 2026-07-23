from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class KnowledgeSourceCreate(BaseModel):
    scope: Literal["general", "traffic_injury", "internal", "personal_experience"]
    title: str = Field(min_length=2, max_length=240)
    excerpt: str = Field(min_length=10, max_length=20000)
    source_name: str = Field(min_length=2, max_length=240)
    source_url: str = Field(min_length=1, max_length=500)
    published_or_updated_at: date
    jurisdiction: str = Field(min_length=1, max_length=100)
    applicability_scope: str = Field(min_length=2, max_length=240)
    effective_status: Literal["verified_effective", "verification_required", "historical"]
    verified_by: str = Field(min_length=2, max_length=120)
    stale_risk: bool = True
    metadata_json: dict = Field(default_factory=dict)


class KnowledgeSearch(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    scopes: list[str] = Field(default_factory=lambda: ["general"])
    limit: int = Field(default=5, ge=1, le=20)

