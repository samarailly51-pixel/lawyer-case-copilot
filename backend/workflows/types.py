from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NodeOutput:
    generated_records: int = 0
    warnings: list[str] = field(default_factory=list)
    review_requirements: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


WORKFLOW_NODES = (
    "case_intake",
    "document_processing",
    "fact_extraction",
    "timeline_builder",
    "party_relationship",
    "domain_router",
    "general_case_analysis",
    "traffic_injury_module",
    "evidence_matrix",
    "legal_retrieval",
    "risk_issue",
    "task_planning",
    "draft_report",
    "human_review_gate",
)

