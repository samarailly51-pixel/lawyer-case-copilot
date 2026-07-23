from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import select

from core.database import SessionLocal, init_db
from evaluation.metrics import evaluate_case
from models.entities import Case, CompensationItem, ExtractedFact, MissingMaterial, TrafficRiskItem


def run_suite(dataset: Path) -> dict:
    definitions = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    results = []
    with SessionLocal() as db:
        for definition in definitions:
            case = db.scalar(select(Case).where(Case.case_type == definition["case_type"], Case.is_demo.is_(True)))
            if not case:
                results.append({"id": definition["id"], "passed": False, "failures": ["缺少对应 Demo 案件"]})
                continue
            checks = definition["checks"]
            quality = evaluate_case(db, case.id)
            facts = list(db.scalars(select(ExtractedFact).where(ExtractedFact.case_id == case.id, ExtractedFact.is_current.is_(True))))
            missing = list(db.scalars(select(MissingMaterial).where(MissingMaterial.case_id == case.id, MissingMaterial.is_current.is_(True))))
            risks = list(db.scalars(select(TrafficRiskItem).where(TrafficRiskItem.case_id == case.id, TrafficRiskItem.is_current.is_(True))))
            compensation = list(db.scalars(select(CompensationItem).where(CompensationItem.case_id == case.id, CompensationItem.is_current.is_(True))))
            failures = []
            if quality.counts["documents"] < checks.get("minimum_documents", 0): failures.append("材料数量不足")
            if len(facts) < checks.get("minimum_facts", 0): failures.append("事实数量不足")
            if len(compensation) < checks.get("minimum_compensation_items", 0): failures.append("赔偿项目数量不足")
            if quality.fact_source_coverage < checks.get("fact_source_coverage", 0): failures.append("事实来源覆盖不足")
            if checks.get("must_have_missing_material") and not missing: failures.append("未生成缺失材料")
            if checks.get("must_require_human_review") and not any(item.review_status == "unreviewed" for item in facts): failures.append("AI 事实未进入人工复核队列")
            if checks.get("must_have_conflict") and not any(item.has_conflict for item in facts): failures.append("未识别信息冲突")
            if checks.get("must_have_mandatory_risk") and not any(item.mandatory_human_review for item in risks): failures.append("未生成强制人工风险")
            present_rule_ids = {item.rule_id for item in missing if item.rule_id}
            for rule_id in checks.get("must_have_rule_ids", []):
                if rule_id not in present_rule_ids: failures.append(f"缺少规则输出 {rule_id}")
            results.append({"id": definition["id"], "case_id": case.id, "passed": not failures, "failures": failures, "quality": quality.to_dict()})
    return {"passed": all(item["passed"] for item in results), "results": results}


def main() -> None:
    parser = argparse.ArgumentParser(description="运行完全虚构的案件回归评测集")
    parser.add_argument("--dataset", default=str(Path(__file__).resolve().parents[2] / "evals" / "synthetic_cases.jsonl"))
    args = parser.parse_args()
    init_db()
    result = run_suite(Path(args.dataset))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
