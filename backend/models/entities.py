from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


def new_id() -> str:
    return str(uuid.uuid4())


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


class ReviewableMixin:
    created_by_type: Mapped[str] = mapped_column(String(20), default="ai")
    review_status: Mapped[str] = mapped_column(String(20), default="unreviewed")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    agent_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class LawFirmWorkspace(TimestampMixin, Base):
    __tablename__ = "law_firm_workspaces"
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="active")
    settings_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class User(TimestampMixin, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(240), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(30), default="active")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkspaceMembership(TimestampMixin, Base):
    __tablename__ = "workspace_memberships"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_workspace_user"),)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("law_firm_workspaces.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(30), default="viewer")
    status: Mapped[str] = mapped_column(String(30), default="active")


class CaseWorkspaceLink(TimestampMixin, Base):
    __tablename__ = "case_workspace_links"
    __table_args__ = (UniqueConstraint("case_id", "workspace_id", name="uq_case_workspace"),)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("law_firm_workspaces.id", ondelete="CASCADE"), index=True)


class KnowledgeWorkspaceLink(TimestampMixin, Base):
    __tablename__ = "knowledge_workspace_links"
    __table_args__ = (UniqueConstraint("knowledge_source_id", "workspace_id", name="uq_knowledge_workspace"),)
    knowledge_source_id: Mapped[str] = mapped_column(ForeignKey("knowledge_sources.id", ondelete="CASCADE"), index=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("law_firm_workspaces.id", ondelete="CASCADE"), index=True)


class Case(TimestampMixin, Base):
    __tablename__ = "cases"
    title: Mapped[str] = mapped_column(String(200))
    case_type: Mapped[str] = mapped_column(String(40), default="other")
    stage: Mapped[str] = mapped_column(String(40), default="intake")
    status: Mapped[str] = mapped_column(String(40), default="active")
    client_name: Mapped[str] = mapped_column(String(120), default="")
    opposing_party: Mapped[str] = mapped_column(String(120), default="")
    lead_lawyer: Mapped[str] = mapped_column(String(120), default="演示律师")
    collaborators: Mapped[list[str]] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text, default="")
    risk_level: Mapped[str] = mapped_column(String(20), default="pending")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)

    documents: Mapped[list["Document"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    parties: Mapped[list["CaseParty"]] = relationship(back_populates="case", cascade="all, delete-orphan")


class CaseParty(TimestampMixin, ReviewableMixin, Base):
    __tablename__ = "case_parties"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    role: Mapped[str] = mapped_column(String(60))
    party_type: Mapped[str] = mapped_column(String(40), default="person")
    masked_contact: Mapped[str] = mapped_column(String(100), default="")
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    case: Mapped[Case] = relationship(back_populates="parties")


class PartyRelationship(TimestampMixin, ReviewableMixin, Base):
    __tablename__ = "party_relationships"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    from_party_id: Mapped[str] = mapped_column(ForeignKey("case_parties.id"))
    to_party_id: Mapped[str] = mapped_column(ForeignKey("case_parties.id"))
    relationship_type: Mapped[str] = mapped_column(String(60))
    description: Mapped[str] = mapped_column(Text, default="")


class Document(TimestampMixin, Base):
    __tablename__ = "documents"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100), default="text/plain")
    file_path: Mapped[str] = mapped_column(String(500), default="")
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    category: Mapped[str] = mapped_column(String(100), default="其他证据")
    classification_source: Mapped[str] = mapped_column(String(20), default="ai")
    parse_status: Mapped[str] = mapped_column(String(30), default="pending")
    parse_warning: Mapped[str] = mapped_column(Text, default="")
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    page_count: Mapped[int] = mapped_column(Integer, default=1)
    sensitive_level: Mapped[str] = mapped_column(String(20), default="confidential")
    case: Mapped[Case] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(TimestampMixin, Base):
    __tablename__ = "document_chunks"
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text)
    start_offset: Mapped[int] = mapped_column(Integer, default=0)
    end_offset: Mapped[int] = mapped_column(Integer, default=0)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    document: Mapped[Document] = relationship(back_populates="chunks")


class DocumentQualityAssessment(TimestampMixin, Base):
    __tablename__ = "document_quality_assessments"
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    text_quality_score: Mapped[float] = mapped_column(Float, default=0)
    injection_risk: Mapped[bool] = mapped_column(Boolean, default=False)
    security_flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=False)
    ocr_provider: Mapped[str] = mapped_column(String(40), default="none")


class SourceReference(TimestampMixin, Base):
    __tablename__ = "source_references"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    target_type: Mapped[str] = mapped_column(String(60), index=True)
    target_id: Mapped[str] = mapped_column(String(36), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quote: Mapped[str] = mapped_column(Text)
    start_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ExtractedFact(TimestampMixin, ReviewableMixin, Base):
    __tablename__ = "extracted_facts"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    fact_type: Mapped[str] = mapped_column(String(60))
    content: Mapped[str] = mapped_column(Text)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    has_conflict: Mapped[bool] = mapped_column(Boolean, default=False)


class FactConflict(TimestampMixin, ReviewableMixin, Base):
    __tablename__ = "fact_conflicts"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    related_fact_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    resolution: Mapped[str] = mapped_column(Text, default="")


class TimelineEvent(TimestampMixin, ReviewableMixin, Base):
    __tablename__ = "timeline_events"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    parties: Mapped[list[str]] = mapped_column(JSON, default=list)
    has_conflict: Mapped[bool] = mapped_column(Boolean, default=False)
    needs_verification: Mapped[bool] = mapped_column(Boolean, default=False)


class EvidenceItem(TimestampMixin, ReviewableMixin, Base):
    __tablename__ = "evidence_items"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    evidence_type: Mapped[str] = mapped_column(String(80))
    fact_to_prove: Mapped[str] = mapped_column(Text)
    purpose: Mapped[str] = mapped_column(Text, default="")
    support_status: Mapped[str] = mapped_column(String(30), default="supports")
    document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)


class LegalIssue(TimestampMixin, ReviewableMixin, Base):
    __tablename__ = "legal_issues"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    analysis: Mapped[str] = mapped_column(Text)
    information_gap: Mapped[str] = mapped_column(Text, default="")
    possible_defense: Mapped[str] = mapped_column(Text, default="")
    lawyer_question: Mapped[str] = mapped_column(Text, default="")


class MissingMaterial(TimestampMixin, ReviewableMixin, Base):
    __tablename__ = "missing_materials"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    reason: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    related_claim: Mapped[str] = mapped_column(String(160), default="")
    suggested_action: Mapped[str] = mapped_column(Text, default="")
    rule_id: Mapped[str | None] = mapped_column(String(120), nullable=True)


class RiskItem(TimestampMixin, ReviewableMixin, Base):
    __tablename__ = "risk_items"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    risk_type: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text)
    trigger_basis: Mapped[str] = mapped_column(Text)
    level: Mapped[str] = mapped_column(String(20), default="medium")
    suggested_review: Mapped[str] = mapped_column(Text, default="")
    mandatory_human_review: Mapped[bool] = mapped_column(Boolean, default=True)
    rule_id: Mapped[str | None] = mapped_column(String(120), nullable=True)


class CaseTask(TimestampMixin, ReviewableMixin, Base):
    __tablename__ = "case_tasks"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    trigger_reason: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    assignee: Mapped[str] = mapped_column(String(120), default="案件负责律师")
    status: Mapped[str] = mapped_column(String(30), default="todo")
    related_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)


class LegalCitation(TimestampMixin, ReviewableMixin, Base):
    __tablename__ = "legal_citations"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(240))
    excerpt: Mapped[str] = mapped_column(Text)
    source_name: Mapped[str] = mapped_column(String(240))
    source_url: Mapped[str] = mapped_column(String(500), default="")
    published_or_updated_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    jurisdiction: Mapped[str] = mapped_column(String(100), default="")
    scope: Mapped[str] = mapped_column(String(200), default="")
    stale_risk: Mapped[bool] = mapped_column(Boolean, default=True)


class KnowledgeSource(TimestampMixin, Base):
    __tablename__ = "knowledge_sources"
    scope: Mapped[str] = mapped_column(String(60), index=True)
    title: Mapped[str] = mapped_column(String(240), index=True)
    excerpt: Mapped[str] = mapped_column(Text)
    source_name: Mapped[str] = mapped_column(String(240))
    source_url: Mapped[str] = mapped_column(String(500))
    published_or_updated_at: Mapped[date] = mapped_column(Date)
    jurisdiction: Mapped[str] = mapped_column(String(100))
    applicability_scope: Mapped[str] = mapped_column(String(240))
    effective_status: Mapped[str] = mapped_column(String(40), default="unverified")
    verified_by: Mapped[str] = mapped_column(String(120))
    stale_risk: Mapped[bool] = mapped_column(Boolean, default=True)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class CompensationItem(TimestampMixin, ReviewableMixin, Base):
    __tablename__ = "compensation_items"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    current_facts: Mapped[str] = mapped_column(Text, default="")
    evidence_summary: Mapped[str] = mapped_column(Text, default="")
    missing_evidence: Mapped[str] = mapped_column(Text, default="")
    required_parameters: Mapped[list[str]] = mapped_column(JSON, default=list)
    rule_source: Mapped[str] = mapped_column(Text, default="待接入经核验的规则来源")
    risk_note: Mapped[str] = mapped_column(Text, default="")


class AgentRun(TimestampMixin, Base):
    __tablename__ = "agent_runs"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    trigger_type: Mapped[str] = mapped_column(String(30), default="manual")
    provider: Mapped[str] = mapped_column(String(60), default="mock")
    model_name: Mapped[str] = mapped_column(String(120), default="deterministic-demo")
    prompt_version: Mapped[str] = mapped_column(String(40), default="mvp-v1")
    config_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str] = mapped_column(Text, default="")


class NodeRun(TimestampMixin, Base):
    __tablename__ = "node_runs"
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), index=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    node_name: Mapped[str] = mapped_column(String(100))
    sequence: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    input_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    output_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str] = mapped_column(Text, default="")
    supersedes_node_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class HumanReview(TimestampMixin, Base):
    __tablename__ = "human_reviews"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    target_type: Mapped[str] = mapped_column(String(60))
    target_id: Mapped[str] = mapped_column(String(36))
    action: Mapped[str] = mapped_column(String(30))
    reviewer: Mapped[str] = mapped_column(String(120), default="案件负责律师")
    original_value: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    revised_value: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    comment: Mapped[str] = mapped_column(Text, default="")
    error_type: Mapped[str] = mapped_column(String(80), default="")


class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_logs"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    actor: Mapped[str] = mapped_column(String(120))
    action: Mapped[str] = mapped_column(String(80))
    target_type: Mapped[str] = mapped_column(String(60))
    target_id: Mapped[str] = mapped_column(String(36))
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class DraftDocument(TimestampMixin, ReviewableMixin, Base):
    __tablename__ = "draft_documents"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(240))
    document_type: Mapped[str] = mapped_column(String(80))
    content: Mapped[str] = mapped_column(Text)
    disclaimer: Mapped[str] = mapped_column(Text, default="本草稿仅供案件负责律师复核，不构成正式法律意见。")


class CaseReport(TimestampMixin, ReviewableMixin, Base):
    __tablename__ = "case_reports"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(240))
    report_type: Mapped[str] = mapped_column(String(80))
    content: Mapped[str] = mapped_column(Text)
    citation_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    disclaimer: Mapped[str] = mapped_column(Text, default="本报告由系统辅助整理，不构成正式法律意见，须由案件负责律师复核。")


class TrafficAccidentInfo(TimestampMixin, ReviewableMixin, Base):
    __tablename__ = "traffic_accident_info"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    accident_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    location: Mapped[str] = mapped_column(String(240), default="")
    parties: Mapped[list[str]] = mapped_column(JSON, default=list)
    vehicles: Mapped[list[str]] = mapped_column(JSON, default=list)
    responsibility_text: Mapped[str] = mapped_column(Text, default="")
    police_handling: Mapped[str] = mapped_column(Text, default="")
    special_flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    current_stage: Mapped[str] = mapped_column(String(60), default="材料整理")


class InjuryRecord(TimestampMixin, ReviewableMixin, Base):
    __tablename__ = "injury_records"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    body_part: Mapped[str] = mapped_column(String(120))
    diagnosis_text: Mapped[str] = mapped_column(Text)
    diagnosis_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    has_conflict: Mapped[bool] = mapped_column(Boolean, default=False)


class TreatmentRecord(TimestampMixin, ReviewableMixin, Base):
    __tablename__ = "treatment_records"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    institution: Mapped[str] = mapped_column(String(200))
    treatment_type: Mapped[str] = mapped_column(String(60))
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str] = mapped_column(Text)


class MedicalExpense(TimestampMixin, ReviewableMixin, Base):
    __tablename__ = "medical_expenses"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    invoice_number: Mapped[str] = mapped_column(String(100))
    expense_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount: Mapped[float] = mapped_column(Float, default=0)
    institution: Mapped[str] = mapped_column(String(200), default="")
    linked_statement: Mapped[bool] = mapped_column(Boolean, default=False)
    duplicate_warning: Mapped[bool] = mapped_column(Boolean, default=False)
    conflict_note: Mapped[str] = mapped_column(Text, default="")


class DisabilityAppraisal(TimestampMixin, ReviewableMixin, Base):
    __tablename__ = "disability_appraisals"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    institution: Mapped[str] = mapped_column(String(200), default="")
    appraisal_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    projects: Mapped[list[str]] = mapped_column(JSON, default=list)
    opinion_text: Mapped[str] = mapped_column(Text, default="")
    materials_complete: Mapped[bool] = mapped_column(Boolean, default=False)


class InsuranceInfo(TimestampMixin, ReviewableMixin, Base):
    __tablename__ = "insurance_info"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    insurer: Mapped[str] = mapped_column(String(200))
    insurance_type: Mapped[str] = mapped_column(String(120), default="待核实")
    policy_number_masked: Mapped[str] = mapped_column(String(120), default="")
    coverage_text: Mapped[str] = mapped_column(Text, default="")
    materials_complete: Mapped[bool] = mapped_column(Boolean, default=False)


class CompensationEvidence(TimestampMixin, ReviewableMixin, Base):
    __tablename__ = "compensation_evidence"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    compensation_item_id: Mapped[str] = mapped_column(ForeignKey("compensation_items.id", ondelete="CASCADE"))
    evidence_item_id: Mapped[str | None] = mapped_column(ForeignKey("evidence_items.id"), nullable=True)
    relationship: Mapped[str] = mapped_column(String(40), default="supports")
    note: Mapped[str] = mapped_column(Text, default="")


class TrafficRiskItem(TimestampMixin, ReviewableMixin, Base):
    __tablename__ = "traffic_risk_items"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    risk_type: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    trigger_basis: Mapped[str] = mapped_column(Text)
    level: Mapped[str] = mapped_column(String(20), default="medium")
    related_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    suggested_review: Mapped[str] = mapped_column(Text)
    mandatory_human_review: Mapped[bool] = mapped_column(Boolean, default=True)
    rule_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
