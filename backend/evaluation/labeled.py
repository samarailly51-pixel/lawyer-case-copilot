from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.entities import AgentRun, Case, ExtractedFact, FactConflict, MissingMaterial, TrafficRiskItem


def normalize_label(value: str) -> str:
    return "".join(str(value).lower().split()).strip("。；;，,")


@dataclass
class LabelScore:
    true_positive: int
    false_positive: int
    false_negative: int
    precision: float
    recall: float
    f1: float

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)


def score_labels(expected: Iterable[str], predicted: Iterable[str]) -> LabelScore:
    expected_set = {normalize_label(value) for value in expected if normalize_label(value)}
    predicted_set = {normalize_label(value) for value in predicted if normalize_label(value)}
    true_positive = len(expected_set & predicted_set)
    false_positive = len(predicted_set - expected_set)
    false_negative = len(expected_set - predicted_set)
    precision = true_positive / (true_positive + false_positive) if predicted_set else (1.0 if not expected_set else 0.0)
    recall = true_positive / (true_positive + false_negative) if expected_set else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return LabelScore(
        true_positive=true_positive,
        false_positive=false_positive,
        false_negative=false_negative,
        precision=round(precision, 4), recall=round(recall, 4), f1=round(f1, 4),
    )


def validate_annotation(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if record.get("schema_version") != "1.0":
        errors.append("schema_version 必须为 1.0")
    if not record.get("case_id"):
        errors.append("case_id 不能为空")
    if record.get("authorization_confirmed") is not True:
        errors.append("必须确认材料使用授权")
    if record.get("deidentification_confirmed") is not True:
        errors.append("必须确认材料已脱敏")
    annotator = str(record.get("annotator_id") or "").strip()
    reviewer = str(record.get("reviewer_id") or "").strip()
    if not annotator or not reviewer:
        errors.append("annotator_id 和 reviewer_id 均不能为空")
    elif annotator == reviewer:
        errors.append("标注人与复核人必须是不同人员")
    if record.get("status") != "approved":
        errors.append("只有 status=approved 的双人复核标注可进入评测")
    for field in (
        "facts", "expected_missing_materials", "expected_conflicts",
        "expected_rule_hits", "mandatory_human_review_items",
    ):
        if not isinstance(record.get(field), list):
            errors.append(f"{field} 必须为数组")
    return errors


def _fact_labels(items: list[Any]) -> list[str]:
    values: list[str] = []
    for item in items:
        if isinstance(item, str):
            values.append(item)
        elif isinstance(item, dict):
            values.append(str(item.get("content") or item.get("label") or ""))
    return values


def evaluate_annotation(db: Session, record: dict[str, Any]) -> dict[str, Any]:
    errors = validate_annotation(record)
    if errors:
        return {"case_id": record.get("case_id", ""), "eligible": False, "errors": errors}
    case_id = str(record["case_id"])
    if not db.get(Case, case_id):
        return {"case_id": case_id, "eligible": False, "errors": ["case_id 在当前受控数据库中不存在"]}
    latest_run = db.scalar(select(AgentRun).where(AgentRun.case_id == case_id).order_by(AgentRun.created_at.desc()))
    facts = list(db.scalars(select(ExtractedFact).where(
        ExtractedFact.case_id == case_id, ExtractedFact.is_current.is_(True),
    )))
    missing = list(db.scalars(select(MissingMaterial).where(
        MissingMaterial.case_id == case_id, MissingMaterial.is_current.is_(True),
    )))
    conflicts = list(db.scalars(select(FactConflict).where(
        FactConflict.case_id == case_id, FactConflict.is_current.is_(True),
    )))
    risks = list(db.scalars(select(TrafficRiskItem).where(
        TrafficRiskItem.case_id == case_id, TrafficRiskItem.is_current.is_(True),
    )))
    rule_hits = [item.rule_id for item in [*missing, *risks] if item.rule_id]
    mandatory_items = [item.rule_id or item.risk_type for item in risks if item.mandatory_human_review]
    scores = {
        "facts": score_labels(_fact_labels(record["facts"]), [item.content for item in facts]).to_dict(),
        "missing_materials": score_labels(record["expected_missing_materials"], [item.name for item in missing]).to_dict(),
        "conflicts": score_labels(record["expected_conflicts"], [item.title for item in conflicts]).to_dict(),
        "rule_hits": score_labels(record["expected_rule_hits"], rule_hits).to_dict(),
        "mandatory_human_review": score_labels(record["mandatory_human_review_items"], mandatory_items).to_dict(),
    }
    macro_f1 = round(sum(float(item["f1"]) for item in scores.values()) / len(scores), 4)
    return {
        "case_id": case_id,
        "eligible": True,
        "dataset_scope": "authorized_deidentified_dual_review",
        "system_snapshot": {
            "provider": latest_run.provider if latest_run else None,
            "model_name": latest_run.model_name if latest_run else None,
            "prompt_version": latest_run.prompt_version if latest_run else None,
            "rules_version": (latest_run.config_snapshot or {}).get("rules_version", {}) if latest_run else {},
        },
        "scores": scores,
        "macro_f1": macro_f1,
        "limitations": [
            "指标衡量结构化标签匹配，不评价胜诉率或法律结论正确性。",
            "样本数量、案件分布和标注一致性必须与结果同时披露。",
        ],
    }
