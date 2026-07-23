from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.entities import (
    Case, CaseReport, Document, DocumentQualityAssessment, ExtractedFact, HumanReview,
    LegalCitation, MissingMaterial, NodeRun, SourceReference, TrafficRiskItem,
)


@dataclass
class CaseQualityReport:
    case_id: str
    overall_score: float
    document_parse_rate: float
    document_quality_score: float
    fact_source_coverage: float
    fact_review_completion: float
    mandatory_risk_review_completion: float
    citation_freshness_rate: float | None
    unsupported_model_outputs_rejected: int
    counts: dict[str, int]
    warnings: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _ratio(numerator: int, denominator: int, empty_value: float = 1.0) -> float:
    return numerator / denominator if denominator else empty_value


def evaluate_case(db: Session, case_id: str) -> CaseQualityReport:
    case = db.get(Case, case_id)
    if not case:
        raise ValueError("案件不存在")
    documents = list(db.scalars(select(Document).where(Document.case_id == case_id)))
    qualities = list(db.scalars(select(DocumentQualityAssessment).where(DocumentQualityAssessment.case_id == case_id)))
    facts = list(db.scalars(select(ExtractedFact).where(ExtractedFact.case_id == case_id, ExtractedFact.is_current.is_(True))))
    fact_ids = [item.id for item in facts]
    supported_fact_ids = set(db.scalars(
        select(SourceReference.target_id).where(
            SourceReference.case_id == case_id,
            SourceReference.target_type == "fact",
            SourceReference.target_id.in_(fact_ids or [""]),
        )
    ))
    reviewed_facts = sum(item.review_status in {"accepted", "modified", "rejected"} for item in facts)
    risks = list(db.scalars(select(TrafficRiskItem).where(
        TrafficRiskItem.case_id == case_id,
        TrafficRiskItem.is_current.is_(True),
        TrafficRiskItem.mandatory_human_review.is_(True),
    )))
    reviewed_risks = sum(item.review_status in {"accepted", "modified", "rejected"} for item in risks)
    citations = list(db.scalars(select(LegalCitation).where(LegalCitation.case_id == case_id, LegalCitation.is_current.is_(True))))
    rejected = 0
    for node in db.scalars(select(NodeRun).where(NodeRun.case_id == case_id, NodeRun.node_name == "fact_extraction")):
        rejected += int((node.output_summary.get("metrics") or {}).get("rejected_unsupported", 0))

    parse_rate = _ratio(sum(doc.parse_status == "parsed" for doc in documents), len(documents), 0.0)
    document_quality = sum(item.text_quality_score for item in qualities) / len(qualities) if qualities else 0.0
    source_coverage = _ratio(len(supported_fact_ids), len(facts), 0.0)
    fact_review = _ratio(reviewed_facts, len(facts))
    risk_review = _ratio(reviewed_risks, len(risks))
    citation_freshness = _ratio(sum(not item.stale_risk for item in citations), len(citations)) if citations else None
    weighted = [
        (parse_rate, 0.2), (document_quality, 0.15), (source_coverage, 0.3),
        (fact_review, 0.15), (risk_review, 0.2),
    ]
    overall = sum(value * weight for value, weight in weighted)
    warnings: list[str] = []
    if parse_rate < 1:
        warnings.append("存在未完成解析的材料。")
    if document_quality < 0.75:
        warnings.append("材料文本质量偏低，建议人工核对或重新 OCR。")
    if source_coverage < 1:
        warnings.append("存在没有材料引用的当前事实。")
    if fact_review < 1:
        warnings.append("仍有 AI 提取事实等待律师复核。")
    if risk_review < 1:
        warnings.append("仍有强制风险项等待律师处理。")
    if not citations:
        warnings.append("当前没有法律知识引用；系统不会据此生成法律结论。")
    return CaseQualityReport(
        case_id=case_id, overall_score=round(overall, 4), document_parse_rate=round(parse_rate, 4),
        document_quality_score=round(document_quality, 4), fact_source_coverage=round(source_coverage, 4),
        fact_review_completion=round(fact_review, 4), mandatory_risk_review_completion=round(risk_review, 4),
        citation_freshness_rate=round(citation_freshness, 4) if citation_freshness is not None else None,
        unsupported_model_outputs_rejected=rejected,
        counts={
            "documents": len(documents), "facts": len(facts), "supported_facts": len(supported_fact_ids),
            "mandatory_risks": len(risks), "citations": len(citations),
            "quality_flags": sum(item.requires_human_review for item in qualities),
        },
        warnings=warnings,
    )

