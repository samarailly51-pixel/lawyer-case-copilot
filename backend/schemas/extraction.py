from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class ExtractedFactPayload(BaseModel):
    fact_type: str = Field(min_length=1, max_length=60)
    content: str = Field(min_length=2, max_length=1000)
    document_id: str
    quote: str = Field(min_length=2, max_length=500)
    event_date: date | None = None
    amount: float | None = None
    confidence: float = Field(ge=0, le=1)
    has_conflict: bool = False


class FactExtractionPayload(BaseModel):
    facts: list[ExtractedFactPayload] = Field(default_factory=list, max_length=100)
    warnings: list[str] = Field(default_factory=list)


FACT_EXTRACTION_JSON_SCHEMA = FactExtractionPayload.model_json_schema()

