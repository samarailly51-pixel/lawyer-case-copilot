from __future__ import annotations

import hashlib

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from document_processing.service import chunk_text
from models.entities import Case, CaseParty, Document, DocumentChunk, DocumentQualityAssessment
from document_processing.quality import assess_text_quality
from workflows import WorkflowOrchestrator


CONTRACT_DOCUMENTS = [
    ("01_品牌设计服务合同.txt", "合同及协议", """虚构演示材料｜品牌设计服务合同
签订日期：2025年1月8日
委托方：青禾餐饮管理有限公司（虚构）
服务方：星图品牌设计工作室（虚构）
合同总价：人民币120,000元。首期款60,000元，成果交付并验收后支付余款。
服务内容：品牌视觉系统设计。双方应通过邮件确认交付清单和验收结果。
"""),
    ("02_首期付款凭证.txt", "付款凭证", """虚构演示材料｜银行转账回单
交易日期：2025年1月10日
付款方：青禾餐饮管理有限公司（虚构）
收款方：星图品牌设计工作室（虚构）
金额：人民币60,000元
用途：品牌设计服务首期款
"""),
    ("03_项目沟通记录.txt", "沟通记录", """虚构演示材料｜项目沟通节选
2025年4月2日，服务方称已发送最终设计文件和交付清单。
2025年4月10日，委托方回复称部分门店应用稿与约定不一致，要求修改。
2025年4月18日，服务方称已完成一轮修改。当前材料未包含双方最终验收确认。
"""),
]

TRAFFIC_DOCUMENTS = [
    ("01_道路交通事故认定书.txt", "道路交通事故认定书", """完全虚构演示材料｜道路交通事故认定书
事故时间：2025年3月18日8时30分
事故地点：明州市海棠路与青云路交叉口（虚构）
当事人：陈某，驾驶小型轿车；林某，驾驶电动自行车。
材料记载：陈某承担事故主要责任，林某承担事故次要责任。
本文件仅为产品演示数据，不对应任何真实人员、车辆、机构或事故。
"""),
    ("02_住院病历摘要.txt", "住院病历", """完全虚构演示材料｜住院病历摘要
患者：林某（虚构）
入院日期：2025年3月18日
出院日期：2025年3月25日
入院诊断：右胫骨平台骨折、软组织挫伤。
治疗经过：住院治疗7日。
2025年4月20日复诊记录另载腰痛主诉，是否与本次事故相关需由律师结合医疗专业意见核查。
"""),
    ("03_医疗费用票据.txt", "医疗费用票据", """完全虚构演示材料｜医疗收费票据
票据号码：DEMO-MED-20250326
开票日期：2025年3月26日
医疗机构：明州市中心医院（虚构）
金额：人民币18,640.50元
提示：住院记录载明3月25日出院，开票日期为3月26日，需人工核实是否为正常结算日期。
"""),
    ("04_医疗费用清单.txt", "医疗费用清单", """完全虚构演示材料｜住院费用清单
费用期间：2025年3月18日至2025年3月25日
检查费、治疗费、药品费等合计：人民币18,640.50元。
本清单仅用于演示材料关联，不表示费用合理性判断。
"""),
    ("05_收入证明.txt", "收入及误工证明", """完全虚构演示材料｜收入证明
林某系明州远航商贸有限公司员工（公司为虚构），事故前月收入8,500元。
现有材料未附完整工资流水，也未确认实际停工期间。
"""),
    ("06_车辆保险信息页.txt", "车辆及保险材料", """完全虚构演示材料｜车辆保险信息页
保险人：明州安心财产保险公司（虚构）
保单号：DEMO-****-0318
当前仅有信息页，完整条款、保险期间和赔付记录尚待核验。
"""),
]


def _add_documents(db: Session, case: Case, items: list[tuple[str, str, str]]) -> None:
    for filename, category, text in items:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        doc = Document(case_id=case.id, filename=filename, mime_type="text/plain", sha256=digest,
                       category=category, classification_source="system", parse_status="parsed",
                       extracted_text=text, page_count=1, sensitive_level="synthetic")
        db.add(doc); db.flush()
        for index, (start, end, value) in enumerate(chunk_text(text)):
            db.add(DocumentChunk(document_id=doc.id, page_number=1, chunk_index=index,
                                 text=value, start_offset=start, end_offset=end, ocr_confidence=1.0))
        quality = assess_text_quality(text)
        db.add(DocumentQualityAssessment(
            document_id=doc.id, case_id=case.id, text_quality_score=quality.score,
            injection_risk=quality.injection_risk, security_flags=quality.flags,
            warnings=quality.warnings, requires_human_review=quality.requires_human_review,
            ocr_provider="synthetic",
        ))


def seed_demo_cases(db: Session) -> None:
    count = db.scalar(select(func.count(Case.id))) or 0
    if count:
        return
    contract = Case(title="青禾餐饮品牌设计服务合同纠纷（虚构）", case_type="contract", stage="协商前材料审查",
                    client_name="星图品牌设计工作室（虚构）", opposing_party="青禾餐饮管理有限公司（虚构）",
                    lead_lawyer="周律师（演示）", is_demo=True, status="active")
    traffic = Case(title="林某交通事故人伤案件（虚构）", case_type="traffic_injury", stage="诉前材料整理",
                   client_name="林某（虚构）", opposing_party="陈某（虚构）",
                   lead_lawyer="周律师（演示）", is_demo=True, status="active")
    db.add_all([contract, traffic]); db.flush()
    db.add_all([
        CaseParty(case_id=contract.id, name=contract.client_name, role="委托人", created_by_type="system"),
        CaseParty(case_id=contract.id, name=contract.opposing_party, role="对方当事人", party_type="organization", created_by_type="system"),
        CaseParty(case_id=traffic.id, name=traffic.client_name, role="伤者/委托人", created_by_type="system"),
        CaseParty(case_id=traffic.id, name=traffic.opposing_party, role="驾驶人/对方当事人", created_by_type="system"),
        CaseParty(case_id=traffic.id, name="明州安心财产保险公司（虚构）", role="保险公司", party_type="organization", created_by_type="system"),
        CaseParty(case_id=traffic.id, name="明州市中心医院（虚构）", role="医疗机构", party_type="organization", created_by_type="system"),
    ])
    _add_documents(db, contract, CONTRACT_DOCUMENTS)
    _add_documents(db, traffic, TRAFFIC_DOCUMENTS)
    db.commit()
    for case in (contract, traffic):
        run = WorkflowOrchestrator(db).create_run(case.id, "demo_seed")
        WorkflowOrchestrator(db).execute(run.id)


def backfill_document_quality(db: Session) -> None:
    assessed_ids = set(db.scalars(select(DocumentQualityAssessment.document_id)))
    for doc in db.scalars(select(Document).where(Document.id.not_in(assessed_ids or [""]))):
        quality = assess_text_quality(doc.extracted_text, doc.parse_warning)
        db.add(DocumentQualityAssessment(
            document_id=doc.id, case_id=doc.case_id, text_quality_score=quality.score,
            injection_risk=quality.injection_risk, security_flags=quality.flags,
            warnings=quality.warnings, requires_human_review=quality.requires_human_review,
            ocr_provider="legacy",
        ))
    db.commit()
