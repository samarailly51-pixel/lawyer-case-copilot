from __future__ import annotations

import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.entities import (
    Case,
    CaseWorkspaceLink,
    Document,
    DocumentChunk,
    DocumentQualityAssessment,
    LawFirmWorkspace,
)
from workflows.orchestrator import WorkflowOrchestrator


TRAFFIC_DOCUMENTS = (
    (
        "合成事故认定书.txt",
        "道路交通事故认定书",
        "2026年03月02日08时30分，事故发生于海州市滨河路与建设路交叉口。"
        "甲方车辆与乙方车辆发生碰撞。交警部门记载：甲方承担主要责任，乙方承担次要责任。",
    ),
    (
        "合成门诊病历.txt",
        "门诊病历",
        "海州市第一医院门诊病历。就诊日期：2026年03月02日。"
        "初步诊断：左桡骨远端骨折。处理：石膏固定并建议复查。",
    ),
    (
        "合成医疗费票据.txt",
        "医疗费用票据",
        "海州市第一医院医疗费票据。票据号：SYN-20260302-01。"
        "开票日期：2026年03月02日。金额：12345.67元。",
    ),
    (
        "合成保险材料.txt",
        "车辆及保险材料",
        "承保机构：海州安行财产保险股份有限公司。险种：机动车交通事故责任强制保险。"
        "保单号：SYNTHETIC-ONLY-2026-0001。",
    ),
)

CONTRACT_DOCUMENTS = (
    (
        "合成合同.txt",
        "合同及协议",
        "2026年01月08日，甲公司与乙公司签订合成测试服务合同，约定项目总价80000元。",
    ),
    (
        "合成付款凭证.txt",
        "付款凭证",
        "2026年01月10日，甲公司支付合同款40000元。凭证编号：SYN-PAY-001。",
    ),
    (
        "合成沟通记录.txt",
        "沟通记录",
        "2026年02月18日，双方通过电子邮件讨论交付验收事项，尚未形成双方确认的验收记录。",
    ),
)


def _create_document(
    db: Session,
    case_id: str,
    filename: str,
    category: str,
    text: str,
) -> None:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    document = Document(
        case_id=case_id,
        filename=filename,
        mime_type="text/plain",
        file_path=f"synthetic-evaluation/{digest}.txt",
        sha256=digest,
        category=category,
        classification_source="user",
        parse_status="parsed",
        extracted_text=text,
        page_count=1,
        sensitive_level="synthetic",
    )
    db.add(document)
    db.flush()
    db.add(
        DocumentChunk(
            document_id=document.id,
            page_number=1,
            chunk_index=0,
            text=text,
            start_offset=0,
            end_offset=len(text),
            ocr_confidence=1.0,
        )
    )
    db.add(
        DocumentQualityAssessment(
            document_id=document.id,
            case_id=case_id,
            text_quality_score=1.0,
            injection_risk=False,
            security_flags=[],
            warnings=[],
            requires_human_review=False,
            ocr_provider="synthetic-text",
        )
    )


def ensure_synthetic_case(db: Session, fixture: str) -> Case:
    """Create and run a deterministic, entirely fictional non-demo case."""
    title = f"SYNTHETIC-EVAL::{fixture}"
    existing = db.scalar(select(Case).where(Case.title == title))
    if existing:
        orchestrator = WorkflowOrchestrator(db)
        run = orchestrator.create_run(existing.id, trigger_type="synthetic_evaluation")
        completed = orchestrator.execute(run.id)
        if completed.status != "awaiting_review":
            raise RuntimeError(f"合成评测工作流执行失败：{completed.error}")
        db.refresh(existing)
        return existing

    workspace = db.scalar(select(LawFirmWorkspace).order_by(LawFirmWorkspace.created_at))
    if not workspace:
        workspace = LawFirmWorkspace(name="合成评测工作空间", slug="synthetic-evaluation")
        db.add(workspace)
        db.flush()

    if fixture == "non_demo_traffic":
        case = Case(
            title=title,
            case_type="traffic_injury",
            client_name="虚构当事人甲",
            opposing_party="虚构当事人乙",
            lead_lawyer="评测律师",
            summary="仅用于自动化回归的完全虚构材料。",
            is_demo=False,
        )
        documents = TRAFFIC_DOCUMENTS
    elif fixture == "non_demo_contract":
        case = Case(
            title=title,
            case_type="contract",
            client_name="虚构甲公司",
            opposing_party="虚构乙公司",
            lead_lawyer="评测律师",
            summary="仅用于自动化回归的完全虚构材料。",
            is_demo=False,
        )
        documents = CONTRACT_DOCUMENTS
    else:
        raise ValueError(f"未知合成评测夹具：{fixture}")

    db.add(case)
    db.flush()
    db.add(CaseWorkspaceLink(case_id=case.id, workspace_id=workspace.id))
    for filename, category, text in documents:
        _create_document(db, case.id, filename, category, text)
    db.commit()
    db.refresh(case)

    orchestrator = WorkflowOrchestrator(db)
    run = orchestrator.create_run(case.id, trigger_type="synthetic_evaluation")
    completed = orchestrator.execute(run.id)
    if completed.status != "awaiting_review":
        raise RuntimeError(f"合成评测工作流执行失败：{completed.error}")
    db.refresh(case)
    return case


def remove_synthetic_cases(db: Session) -> int:
    """Remove only the reserved non-demo cases created by this evaluator."""
    cases = list(db.scalars(select(Case).where(Case.title.like("SYNTHETIC-EVAL::%"))))
    for case in cases:
        db.delete(case)
    db.commit()
    return len(cases)
