from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import select

from core.database import SessionLocal, init_db
from evaluation.metrics import evaluate_case
from models.entities import Case, CompensationItem, ExtractedFact, MissingMaterial, TrafficRiskItem
from services.demo_data import seed_demo_cases


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
            if len(missing) < checks.get("minimum_missing_materials", 0): failures.append("缺失材料识别数量不足")
            if sum(item.mandatory_human_review for item in risks) < checks.get("minimum_mandatory_risks", 0): failures.append("强制人工风险数量不足")
            if quality.fact_source_coverage < checks.get("fact_source_coverage", 0): failures.append("事实来源覆盖不足")
            if quality.unsupported_model_outputs_rejected > checks.get("maximum_unsupported_model_outputs", 10**9): failures.append("无来源模型输出拒绝数量超过阈值")
            if checks.get("must_have_missing_material") and not missing: failures.append("未生成缺失材料")
            if checks.get("must_require_human_review") and not any(item.review_status == "unreviewed" for item in facts): failures.append("AI 事实未进入人工复核队列")
            if checks.get("must_have_conflict") and not any(item.has_conflict for item in facts): failures.append("未识别信息冲突")
            if checks.get("must_have_mandatory_risk") and not any(item.mandatory_human_review for item in risks): failures.append("未生成强制人工风险")
            present_rule_ids = {item.rule_id for item in missing if item.rule_id}
            for rule_id in checks.get("must_have_rule_ids", []):
                if rule_id not in present_rule_ids: failures.append(f"缺少规则输出 {rule_id}")
            results.append({"id": definition["id"], "case_id": case.id, "passed": not failures, "failures": failures, "quality": quality.to_dict()})
    passed_count = sum(item["passed"] for item in results)
    coverage_values = [item["quality"]["fact_source_coverage"] for item in results if item.get("quality")]
    return {
        "passed": passed_count == len(results),
        "summary": {
            "dataset_label": "完全虚构结构化回归集",
            "total_scenarios": len(results),
            "passed_scenarios": passed_count,
            "pass_rate": round(passed_count / len(results), 4) if results else 0.0,
            "average_fact_source_coverage": round(sum(coverage_values) / len(coverage_values), 4) if coverage_values else 0.0,
            "scope_note": "只验证系统输出完整性、可追溯性和人工复核边界，不评价法律结论。",
        },
        "results": results,
    }


def render_markdown(result: dict) -> str:
    summary = result["summary"]
    rows = "\n".join(
        f"| `{item['id']}` | {'通过' if item['passed'] else '失败'} | "
        f"{round((item.get('quality') or {}).get('fact_source_coverage', 0) * 100)}% | "
        f"{'；'.join(item['failures']) or '—'} |"
        for item in result["results"]
    )
    return f"""# 完全虚构回归评测结果

> {summary['scope_note']}

| 指标 | 结果 |
|---|---:|
| 回归场景 | {summary['total_scenarios']} |
| 通过场景 | {summary['passed_scenarios']} |
| 通过率 | {round(summary['pass_rate'] * 100)}% |
| 平均事实来源覆盖 | {round(summary['average_fact_source_coverage'] * 100)}% |

| 场景 | 状态 | 来源覆盖 | 失败原因 |
|---|---|---:|---|
{rows}

本报告由 `python -m evaluation.run_suite` 基于仓库内完全虚构 Demo 数据生成。它不构成模型准确率、法律正确率或真实业务效果声明。
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="运行完全虚构的案件回归评测集")
    parser.add_argument("--dataset", default=str(Path(__file__).resolve().parents[2] / "evals" / "synthetic_cases.jsonl"))
    parser.add_argument("--json-output", help="可选：保存 JSON 结果")
    parser.add_argument("--markdown-output", help="可选：保存 Markdown 结果")
    args = parser.parse_args()
    init_db()
    with SessionLocal() as db:
        seed_demo_cases(db)
    result = run_suite(Path(args.dataset))
    if args.json_output:
        Path(args.json_output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.markdown_output:
        Path(args.markdown_output).write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
