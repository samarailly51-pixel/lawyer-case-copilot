from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from core.config import settings
from models.entities import (
    AgentRun, Case, CaseReport, CaseTask, CompensationItem, DisabilityAppraisal, EvidenceItem,
    ExtractedFact, FactConflict, InjuryRecord, InsuranceInfo, LegalCitation, LegalIssue,
    MedicalExpense, MissingMaterial, NodeRun, RiskItem, TimelineEvent, TrafficAccidentInfo,
    TrafficRiskItem, TreatmentRecord,
)
from nodes import NODE_HANDLERS
from providers import get_provider
from services.rules import validate_rule_file
from .types import WORKFLOW_NODES


NODE_MODELS = {
    "fact_extraction": (ExtractedFact, FactConflict),
    "timeline_builder": (TimelineEvent,),
    "general_case_analysis": (LegalIssue, MissingMaterial),
    "traffic_injury_module": (
        TrafficAccidentInfo, InjuryRecord, TreatmentRecord, MedicalExpense, DisabilityAppraisal,
        InsuranceInfo, CompensationItem,
    ),
    "evidence_matrix": (EvidenceItem,),
    "legal_retrieval": (LegalCitation,),
    "risk_issue": (RiskItem, TrafficRiskItem, MissingMaterial),
    "task_planning": (CaseTask,),
    "draft_report": (CaseReport,),
}


class WorkflowOrchestrator:
    def __init__(self, db: Session):
        self.db = db

    def create_run(self, case_id: str, trigger_type: str = "manual") -> AgentRun:
        case = self.db.get(Case, case_id)
        if not case:
            raise ValueError("案件不存在")
        provider = get_provider()
        rules_root = Path(__file__).resolve().parents[1] / "rules" / "traffic_injury"
        evidence_rules = validate_rule_file(rules_root / "evidence_completeness.yaml")
        personal_rules = validate_rule_file(rules_root / "personal_experience_rules.yaml")
        run = AgentRun(
            case_id=case_id,
            status="pending",
            trigger_type=trigger_type,
            provider=provider.name,
            model_name=settings.model_name or "deterministic-demo",
            config_snapshot={
                "case_type": case.case_type,
                "provider": provider.name,
                "temperature": settings.model_temperature,
                "rules_version": {
                    "general": "mvp-v1",
                    "traffic_evidence": evidence_rules.version,
                    "personal_experience": personal_rules.version,
                },
                "enabled_rule_count": {
                    "traffic_evidence": evidence_rules.enabled_rule_count,
                    "personal_experience": personal_rules.enabled_rule_count,
                },
                "retry_policy": {
                    "provider_max_retries": settings.model_max_retries,
                    "provider_retryable": ["timeout", "http_429", "http_5xx"],
                    "node_retry": "manual_single_node",
                },
            },
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def execute(self, run_id: str) -> AgentRun:
        run = self.db.get(AgentRun, run_id)
        if not run:
            raise ValueError("运行记录不存在")
        case = self.db.get(Case, run.case_id)
        if not case:
            raise ValueError("案件不存在")
        run.status = "processing"
        run.started_at = datetime.now(timezone.utc)
        self.db.commit()
        for sequence, node_name in enumerate(WORKFLOW_NODES, start=1):
            if node_name == "traffic_injury_module" and case.case_type != "traffic_injury":
                node = NodeRun(run_id=run.id, case_id=case.id, node_name=node_name, sequence=sequence,
                               status="skipped", input_summary={"reason": "非交通事故人伤案件"}, output_summary={})
                self.db.add(node); self.db.commit()
                continue
            try:
                self._execute_node(run, case, node_name, sequence)
            except Exception as exc:
                run.status = "failed"
                run.error = f"{node_name}: {exc}"
                run.completed_at = datetime.now(timezone.utc)
                self.db.commit()
                return run
        run.status = "awaiting_review"
        run.completed_at = datetime.now(timezone.utc)
        case.progress = max(case.progress, 88)
        self.db.commit()
        self.db.refresh(run)
        return run

    def rerun_node(self, run_id: str, node_name: str) -> NodeRun:
        if node_name not in NODE_HANDLERS:
            raise ValueError("未知工作流节点")
        run = self.db.get(AgentRun, run_id)
        if not run:
            raise ValueError("运行记录不存在")
        case = self.db.get(Case, run.case_id)
        latest = self.db.scalar(
            select(NodeRun).where(NodeRun.run_id == run_id, NodeRun.node_name == node_name)
            .order_by(NodeRun.created_at.desc())
        )
        self._supersede_results(case.id, node_name)
        sequence = latest.sequence if latest else list(WORKFLOW_NODES).index(node_name) + 1
        return self._execute_node(
            run, case, node_name, sequence, latest.id if latest else None,
            execution_reason="single_node_rerun",
        )

    def rerun_from_node(self, run_id: str, from_node: str | None = None) -> AgentRun:
        """Resume a failed run or intentionally rebuild a node and all downstream outputs.

        Lawyer-accepted or lawyer-modified records are never superseded. New AI
        candidates remain unreviewed and therefore cannot silently replace a
        confirmed conclusion.
        """
        run = self.db.get(AgentRun, run_id)
        if not run:
            raise ValueError("运行记录不存在")
        case = self.db.get(Case, run.case_id)
        if not case:
            raise ValueError("案件不存在")
        if from_node is None:
            failed = self.db.scalar(
                select(NodeRun).where(NodeRun.run_id == run_id, NodeRun.status == "failed")
                .order_by(NodeRun.created_at.desc())
            )
            if not failed:
                raise ValueError("当前运行没有失败节点，请明确指定起始节点")
            from_node = failed.node_name
        if from_node not in WORKFLOW_NODES:
            raise ValueError("未知工作流节点")

        run.status = "processing"
        run.error = ""
        run.completed_at = None
        if not run.started_at:
            run.started_at = datetime.now(timezone.utc)
        self.db.commit()
        start_index = list(WORKFLOW_NODES).index(from_node)
        for sequence, node_name in enumerate(WORKFLOW_NODES[start_index:], start=start_index + 1):
            latest = self.db.scalar(
                select(NodeRun).where(NodeRun.run_id == run_id, NodeRun.node_name == node_name)
                .order_by(NodeRun.created_at.desc())
            )
            if node_name == "traffic_injury_module" and case.case_type != "traffic_injury":
                skipped = NodeRun(
                    run_id=run.id, case_id=case.id, node_name=node_name, sequence=sequence,
                    status="skipped", input_summary={"reason": "非交通事故人伤案件", "execution_reason": "downstream_rerun"},
                    output_summary={}, started_at=datetime.now(timezone.utc), completed_at=datetime.now(timezone.utc),
                    supersedes_node_run_id=latest.id if latest else None,
                )
                self.db.add(skipped)
                self.db.commit()
                continue
            try:
                self._execute_node(
                    run, case, node_name, sequence, latest.id if latest else None,
                    execution_reason="downstream_rerun",
                )
            except Exception as exc:
                run.status = "failed"
                run.error = f"{node_name}: {exc}"
                run.completed_at = datetime.now(timezone.utc)
                self.db.commit()
                return run
        run.status = "awaiting_review"
        run.completed_at = datetime.now(timezone.utc)
        case.progress = max(case.progress, 88)
        self.db.commit()
        self.db.refresh(run)
        return run

    def _supersede_results(self, case_id: str, node_name: str) -> None:
        for model in NODE_MODELS.get(node_name, ()):
            self.db.execute(
                update(model).where(
                    model.case_id == case_id,
                    model.is_current.is_(True),
                    model.review_status.not_in(("accepted", "modified")),
                ).values(is_current=False)
            )
        self.db.commit()

    def _execute_node(self, run: AgentRun, case: Case, node_name: str, sequence: int,
                      supersedes: str | None = None, execution_reason: str = "workflow") -> NodeRun:
        self._supersede_results(case.id, node_name)
        node = NodeRun(
            run_id=run.id, case_id=case.id, node_name=node_name, sequence=sequence, status="processing",
            input_summary={"case_id": case.id, "case_type": case.case_type, "execution_reason": execution_reason},
            started_at=datetime.now(timezone.utc), supersedes_node_run_id=supersedes,
        )
        self.db.add(node); self.db.commit(); self.db.refresh(node)
        try:
            output = NODE_HANDLERS[node_name](self.db, case, run.id)
            node.status = "completed"
            node.output_summary = {
                "generated_records": output.generated_records,
                "review_requirements": output.review_requirements,
                "metrics": output.metrics,
            }
            node.warnings = output.warnings
            node.completed_at = datetime.now(timezone.utc)
            self.db.commit(); self.db.refresh(node)
            return node
        except Exception as exc:
            self.db.rollback()
            node = self.db.get(NodeRun, node.id)
            node.status = "failed"
            node.error = str(exc)
            node.completed_at = datetime.now(timezone.utc)
            self.db.commit()
            raise
