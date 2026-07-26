from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import select

from core.database import SessionLocal, init_db
from evaluation.metrics import evaluate_case
from evaluation.synthetic_fixtures import ensure_synthetic_case, remove_synthetic_cases
from models.entities import (
    Case,
    CompensationItem,
    ExtractedFact,
    InsuranceInfo,
    LegalIssue,
    MedicalExpense,
    MissingMaterial,
    SourceReference,
    TrafficAccidentInfo,
    TrafficRiskItem,
)
from services.demo_data import seed_demo_cases


def _case_for_definition(db, definition: dict) -> Case | None:
    fixture = definition.get("fixture", "demo")
    if fixture == "demo":
        return db.scalar(
            select(Case).where(
                Case.case_type == definition["case_type"],
                Case.is_demo.is_(True),
            )
        )
    return ensure_synthetic_case(db, fixture)


def _specialist_source_coverage(db, case_id: str, records: list[object]) -> float:
    target_pairs = {
        ("traffic_accident", record.id)
        if isinstance(record, TrafficAccidentInfo)
        else ("medical_expense", record.id)
        if isinstance(record, MedicalExpense)
        else ("insurance", record.id)
        for record in records
    }
    if not target_pairs:
        return 1.0
    supported = {
        (row.target_type, row.target_id)
        for row in db.scalars(select(SourceReference).where(SourceReference.case_id == case_id))
    }
    return len(target_pairs & supported) / len(target_pairs)


def _case_output_text(db, case_id: str) -> str:
    models = (
        ExtractedFact,
        LegalIssue,
        MissingMaterial,
        TrafficAccidentInfo,
        MedicalExpense,
        InsuranceInfo,
        CompensationItem,
        TrafficRiskItem,
    )
    values: list[dict] = []
    for model in models:
        for row in db.scalars(
            select(model).where(model.case_id == case_id, model.is_current.is_(True))
        ):
            values.append(
                {
                    column.name: getattr(row, column.name)
                    for column in model.__table__.columns
                    if column.name not in {"created_at", "updated_at"}
                }
            )
    return json.dumps(values, ensure_ascii=False, default=str)


def run_suite(dataset: Path) -> dict:
    definitions = [
        json.loads(line)
        for line in dataset.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    results = []
    with SessionLocal() as db:
        remove_synthetic_cases(db)
        for definition in definitions:
            case = _case_for_definition(db, definition)
            if not case:
                results.append(
                    {
                        "id": definition["id"],
                        "fixture": definition.get("fixture", "demo"),
                        "passed": False,
                        "failures": ["缺少对应的合成案件"],
                    }
                )
                continue

            checks = definition["checks"]
            quality = evaluate_case(db, case.id)
            facts = list(
                db.scalars(
                    select(ExtractedFact).where(
                        ExtractedFact.case_id == case.id,
                        ExtractedFact.is_current.is_(True),
                    )
                )
            )
            missing = list(
                db.scalars(
                    select(MissingMaterial).where(
                        MissingMaterial.case_id == case.id,
                        MissingMaterial.is_current.is_(True),
                    )
                )
            )
            risks = list(
                db.scalars(
                    select(TrafficRiskItem).where(
                        TrafficRiskItem.case_id == case.id,
                        TrafficRiskItem.is_current.is_(True),
                    )
                )
            )
            compensation = list(
                db.scalars(
                    select(CompensationItem).where(
                        CompensationItem.case_id == case.id,
                        CompensationItem.is_current.is_(True),
                    )
                )
            )
            accidents = list(
                db.scalars(
                    select(TrafficAccidentInfo).where(
                        TrafficAccidentInfo.case_id == case.id,
                        TrafficAccidentInfo.is_current.is_(True),
                    )
                )
            )
            expenses = list(
                db.scalars(
                    select(MedicalExpense).where(
                        MedicalExpense.case_id == case.id,
                        MedicalExpense.is_current.is_(True),
                    )
                )
            )
            insurance = list(
                db.scalars(
                    select(InsuranceInfo).where(
                        InsuranceInfo.case_id == case.id,
                        InsuranceInfo.is_current.is_(True),
                    )
                )
            )
            issues = list(
                db.scalars(
                    select(LegalIssue).where(
                        LegalIssue.case_id == case.id,
                        LegalIssue.is_current.is_(True),
                    )
                )
            )

            failures: list[str] = []
            if quality.counts["documents"] < checks.get("minimum_documents", 0):
                failures.append("材料数量不足")
            if len(facts) < checks.get("minimum_facts", 0):
                failures.append("事实数量不足")
            if len(compensation) < checks.get("minimum_compensation_items", 0):
                failures.append("赔偿项目数量不足")
            if len(missing) < checks.get("minimum_missing_materials", 0):
                failures.append("缺失材料识别数量不足")
            if sum(item.mandatory_human_review for item in risks) < checks.get(
                "minimum_mandatory_risks", 0
            ):
                failures.append("强制人工风险数量不足")
            if quality.fact_source_coverage < checks.get("fact_source_coverage", 0):
                failures.append("事实来源覆盖不足")
            if quality.unsupported_model_outputs_rejected > checks.get(
                "maximum_unsupported_model_outputs", 10**9
            ):
                failures.append("无来源模型输出拒绝数量超过阈值")
            if checks.get("must_have_missing_material") and not missing:
                failures.append("未生成缺失材料")
            if checks.get("must_require_human_review") and not any(
                item.review_status == "unreviewed" for item in facts
            ):
                failures.append("AI 事实未进入人工复核队列")
            if checks.get("must_have_conflict") and not any(item.has_conflict for item in facts):
                failures.append("未识别信息冲突")
            if checks.get("must_have_mandatory_risk") and not any(
                item.mandatory_human_review for item in risks
            ):
                failures.append("未生成强制人工风险")

            present_rule_ids = {item.rule_id for item in missing if item.rule_id}
            for rule_id in checks.get("must_have_rule_ids", []):
                if rule_id not in present_rule_ids:
                    failures.append(f"缺少规则输出 {rule_id}")

            expected_date = checks.get("expected_accident_date")
            if expected_date and not any(
                item.accident_date and item.accident_date.isoformat() == expected_date
                for item in accidents
            ):
                failures.append(f"未提取预期事故日期 {expected_date}")
            expected_location = checks.get("expected_location")
            if expected_location and not any(
                expected_location in item.location for item in accidents
            ):
                failures.append(f"未提取预期事故地点 {expected_location}")
            expected_amount = checks.get("expected_medical_expense")
            if expected_amount is not None and not any(
                abs(item.amount - float(expected_amount)) < 0.01 for item in expenses
            ):
                failures.append(f"未提取预期医疗费 {expected_amount}")
            expected_insurer = checks.get("expected_insurer")
            if expected_insurer and not any(
                expected_insurer in item.insurer for item in insurance
            ):
                failures.append(f"未提取预期保险机构 {expected_insurer}")
            expected_issue = checks.get("expected_issue_title_contains")
            if expected_issue and not any(expected_issue in item.title for item in issues):
                failures.append(f"未生成预期争议点 {expected_issue}")

            specialist_records: list[object] = [*accidents, *expenses, *insurance]
            specialist_coverage = _specialist_source_coverage(
                db, case.id, specialist_records
            )
            if specialist_coverage < checks.get("specialist_source_coverage", 0):
                failures.append("专业字段来源覆盖不足")

            output_text = _case_output_text(db, case.id)
            for forbidden in checks.get("must_not_contain", []):
                if forbidden in output_text:
                    failures.append(f"检测到非当前材料内容：{forbidden}")

            results.append(
                {
                    "id": definition["id"],
                    "fixture": definition.get("fixture", "demo"),
                    "case_id": case.id,
                    "passed": not failures,
                    "failures": failures,
                    "specialist_source_coverage": round(specialist_coverage, 4),
                    "quality": quality.to_dict(),
                }
            )
        remove_synthetic_cases(db)

    passed_count = sum(item["passed"] for item in results)
    coverage_values = [
        item["quality"]["fact_source_coverage"]
        for item in results
        if item.get("quality")
    ]
    return {
        "passed": passed_count == len(results),
        "summary": {
            "dataset_label": "完全虚构的 Demo 与非 Demo 结构化回归集",
            "total_scenarios": len(results),
            "passed_scenarios": passed_count,
            "pass_rate": round(passed_count / len(results), 4) if results else 0.0,
            "average_fact_source_coverage": (
                round(sum(coverage_values) / len(coverage_values), 4)
                if coverage_values
                else 0.0
            ),
            "scope_note": (
                "只验证系统输出完整性、材料忠实性、可追溯性和人工复核边界，"
                "不评价法律结论、医疗判断或真实业务效果。"
            ),
        },
        "results": results,
    }


def render_markdown(result: dict) -> str:
    summary = result["summary"]
    rows = "\n".join(
        f"| `{item['id']}` | `{item.get('fixture', 'demo')}` | "
        f"{'通过' if item['passed'] else '失败'} | "
        f"{round((item.get('quality') or {}).get('fact_source_coverage', 0) * 100)}% | "
        f"{round(item.get('specialist_source_coverage', 1) * 100)}% | "
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

| 场景 | 数据路径 | 状态 | 事实来源覆盖 | 专业字段来源覆盖 | 失败原因 |
|---|---|---|---:|---:|---|
{rows}

本报告由 `python -m evaluation.run_suite` 基于仓库内完全虚构数据生成。
它不构成模型准确率、法律正确率或真实业务效果声明。
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="运行完全虚构的案件回归评测集")
    parser.add_argument(
        "--dataset",
        default=str(
            Path(__file__).resolve().parents[2] / "evals" / "synthetic_cases.jsonl"
        ),
    )
    parser.add_argument("--json-output", help="可选：保存 JSON 结果")
    parser.add_argument("--markdown-output", help="可选：保存 Markdown 结果")
    args = parser.parse_args()
    init_db()
    with SessionLocal() as db:
        seed_demo_cases(db)
    result = run_suite(Path(args.dataset))
    if args.json_output:
        Path(args.json_output).write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if args.markdown_output:
        Path(args.markdown_output).write_text(
            render_markdown(result), encoding="utf-8"
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
