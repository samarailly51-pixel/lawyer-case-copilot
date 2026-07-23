from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CaseCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    case_type: Literal["traffic_injury", "contract", "labor", "general_civil", "other"]
    stage: str = "intake"
    client_name: str = ""
    opposing_party: str = ""
    lead_lawyer: str = "案件负责律师"


class CaseUpdate(BaseModel):
    title: str | None = None
    stage: str | None = None
    status: str | None = None
    lead_lawyer: str | None = None
    summary: str | None = None


class CaseOut(ORMModel):
    id: str
    title: str
    case_type: str
    stage: str
    status: str
    client_name: str
    opposing_party: str
    lead_lawyer: str
    collaborators: list[str]
    summary: str
    risk_level: str
    progress: int
    is_demo: bool
    created_at: datetime
    updated_at: datetime


class DocumentOut(ORMModel):
    id: str
    case_id: str
    filename: str
    mime_type: str
    category: str
    classification_source: str
    parse_status: str
    parse_warning: str
    page_count: int
    sensitive_level: str
    created_at: datetime


class DocumentCategoryUpdate(BaseModel):
    category: str = Field(min_length=1, max_length=100)


class RunCreate(BaseModel):
    trigger_type: str = "manual"


class ReviewCreate(BaseModel):
    case_id: str
    target_type: str
    target_id: str
    action: Literal["accepted", "modified", "rejected"]
    reviewer: str = "案件负责律师"
    revised_value: dict[str, Any] = Field(default_factory=dict)
    comment: str = ""
    error_type: str = ""


class BatchReviewCreate(BaseModel):
    case_id: str
    action: Literal["accepted", "rejected"]
    items: list[dict[str, str]] = Field(min_length=1, max_length=100)
    comment: str = ""
    error_type: str = ""


class TaskUpdate(BaseModel):
    status: Literal["todo", "in_progress", "done", "cancelled"] | None = None
    priority: Literal["low", "medium", "high"] | None = None
    assignee: str | None = Field(default=None, max_length=120)
    due_date: date | None = None


class CompensationScenarioRequest(BaseModel):
    parameters: dict[str, float] = Field(default_factory=dict)


class ReviewOut(ORMModel):
    id: str
    case_id: str
    target_type: str
    target_id: str
    action: str
    reviewer: str
    revised_value: dict[str, Any]
    comment: str
    created_at: datetime


class TimelineOut(ORMModel):
    id: str
    event_date: date | None
    title: str
    description: str
    parties: list[str]
    has_conflict: bool
    needs_verification: bool
    review_status: str
    confidence: float | None
