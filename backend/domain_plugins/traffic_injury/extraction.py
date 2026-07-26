from __future__ import annotations

import re
from datetime import date

from models.entities import Document
from schemas.traffic_injury import (
    AccidentInfoPayload,
    DisabilityAppraisalPayload,
    InjuryPayload,
    InsurancePayload,
    MedicalExpensePayload,
    TrafficInjuryExtractionPayload,
    TreatmentPayload,
)


DATE_PATTERN = re.compile(
    r"(?P<year>20\d{2})\s*(?:年|[-/.])\s*(?P<month>\d{1,2})\s*(?:月|[-/.])\s*(?P<day>\d{1,2})\s*日?"
)
AMOUNT_PATTERN = re.compile(r"(?:金额|合计|费用|人民币)?\s*[¥￥]?\s*([0-9][0-9,]*(?:\.\d{1,2})?)\s*元")
INVOICE_PATTERN = re.compile(r"(?:票据号|发票号|号码)\s*[:：]?\s*([A-Za-z0-9-]{4,})")
POLICY_PATTERN = re.compile(r"(?:保单号|保险单号)\s*[:：]?\s*([A-Za-z0-9-]{4,})")


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _matching_line(document: Document, patterns: tuple[str, ...]) -> str:
    return next((line for line in _lines(document.extracted_text) if any(pattern in line for pattern in patterns)), "")


def _date_from(text: str) -> date | None:
    match = DATE_PATTERN.search(text)
    if not match:
        return None
    try:
        return date(int(match.group("year")), int(match.group("month")), int(match.group("day")))
    except ValueError:
        return None


def _dates_from(text: str) -> list[date]:
    values: list[date] = []
    for match in DATE_PATTERN.finditer(text):
        try:
            values.append(date(int(match.group("year")), int(match.group("month")), int(match.group("day"))))
        except ValueError:
            continue
    return values


def _location_from(text: str) -> str:
    explicit = re.search(r"(?:事故地点|地点)\s*[:：]\s*([^\n，。；;]{2,120})", text)
    if explicit:
        return explicit.group(1).strip()
    occurred_at = re.search(r"(?:事故)?发生于([^\n，。；;]{2,100})", text)
    if occurred_at:
        return occurred_at.group(1).strip()
    occurred = re.search(r"于([^，。；;\n]{2,100})(?:发生|与.+?相撞)", text)
    return occurred.group(1).strip() if occurred else ""


def _institution_from(text: str) -> str:
    explicit = re.search(
        r"(?:医疗机构|医院|就诊机构|鉴定机构|保险人|保险公司|承保机构)"
        r"\s*[:：]\s*([^\n，。；;]{2,100})",
        text,
    )
    if explicit:
        return explicit.group(1).strip()
    named = re.search(r"([\u4e00-\u9fff]{2,30}(?:医院|卫生院|诊所|鉴定中心|鉴定所|保险公司))", text)
    return named.group(1) if named else ""


def _body_part_from(text: str) -> str:
    patterns = (
        r"[左右双]?(?:胫骨|腓骨|股骨|髌骨|膝关节|踝关节|足部|下肢)",
        r"[左右双]?(?:肱骨|尺骨|桡骨|肩关节|腕关节|手部|上肢)",
        r"(?:头部|颈部|胸部|腹部|腰部|腰背部|脊柱|骨盆)",
    )
    values: list[str] = []
    for pattern in patterns:
        values.extend(re.findall(pattern, text))
    unique = list(dict.fromkeys(value for value in values if value))
    return "、".join(unique[:5]) or "待律师核对"


def _mask_number(value: str) -> str:
    if len(value) <= 4:
        return "*" * len(value)
    return f"{value[:2]}{'*' * max(4, len(value) - 4)}{value[-2:]}"


def extract_locally(documents: list[Document]) -> TrafficInjuryExtractionPayload:
    """Conservative local extraction.

    It only emits values directly found in the uploaded text. Missing or ambiguous
    fields stay empty and must be reviewed; no demo facts or legal conclusions are
    used as fallbacks.
    """

    payload = TrafficInjuryExtractionPayload()
    categories = {document.category for document in documents}

    accident_document = next(
        (document for document in documents if document.category == "道路交通事故认定书"), None
    )
    if accident_document:
        quote = _matching_line(accident_document, ("事故", "责任", "道路交通"))
        responsibility = _matching_line(accident_document, ("责任", "承担", "认定"))
        anchor = responsibility or quote
        if anchor:
            flags = [
                flag for flag in ("逃逸", "酒驾", "醉驾", "无证驾驶")
                if flag in accident_document.extracted_text
            ]
            payload.accident_info = AccidentInfoPayload(
                document_id=accident_document.id,
                quote=anchor,
                confidence=0.78,
                accident_date=_date_from(accident_document.extracted_text),
                location=_location_from(accident_document.extracted_text),
                responsibility_text=responsibility,
                police_handling="已提供事故认定材料，具体处理情况待律师核对",
                special_flags=flags,
            )

    medical_documents = [
        document for document in documents
        if document.category in {"门诊病历", "住院病历", "出院记录", "检查报告", "病历及医疗材料"}
    ]
    for document in medical_documents:
        diagnosis = _matching_line(document, ("诊断", "骨折", "损伤", "挫伤", "疼痛"))
        if diagnosis:
            payload.injuries.append(InjuryPayload(
                document_id=document.id,
                quote=diagnosis,
                confidence=0.72,
                body_part=_body_part_from(diagnosis),
                diagnosis_text=diagnosis,
                diagnosis_date=_date_from(document.extracted_text),
                has_conflict=any(flag in diagnosis for flag in ("不一致", "待查", "既往", "因果关系")),
            ))
        treatment = _matching_line(document, ("住院", "入院", "出院", "手术", "治疗", "复查"))
        if treatment:
            dates = _dates_from(document.extracted_text)
            payload.treatments.append(TreatmentPayload(
                document_id=document.id,
                quote=treatment,
                confidence=0.7,
                institution=_institution_from(document.extracted_text),
                treatment_type=(
                    "住院" if "住院" in document.extracted_text or "入院" in document.extracted_text
                    else "门诊/复查"
                ),
                start_date=dates[0] if dates else None,
                end_date=dates[-1] if len(dates) > 1 else None,
                description=treatment,
            ))

    expense_documents = [
        document for document in documents
        if document.category in {"医疗费用票据", "医疗费用清单"}
    ]
    seen_invoice_numbers: set[str] = set()
    for document in expense_documents:
        amount_match = AMOUNT_PATTERN.search(document.extracted_text)
        if not amount_match:
            continue
        quote = _matching_line(document, ("金额", "合计", "费用", "元"))
        if not quote:
            quote = amount_match.group(0)
        invoice_match = INVOICE_PATTERN.search(document.extracted_text)
        invoice_number = invoice_match.group(1) if invoice_match else ""
        duplicate = bool(invoice_number and invoice_number in seen_invoice_numbers)
        if invoice_number:
            seen_invoice_numbers.add(invoice_number)
        explicit_conflict = _matching_line(document, ("不一致", "冲突", "重复", "异常"))
        payload.medical_expenses.append(MedicalExpensePayload(
            document_id=document.id,
            quote=quote,
            confidence=0.82,
            invoice_number=invoice_number,
            expense_date=_date_from(document.extracted_text),
            amount=float(amount_match.group(1).replace(",", "")),
            institution=_institution_from(document.extracted_text),
            linked_statement="医疗费用清单" in categories,
            duplicate_warning=duplicate,
            conflict_note=explicit_conflict,
        ))

    for document in (item for item in documents if item.category == "车辆及保险材料"):
        quote = _matching_line(document, ("保险", "保单", "承保", "责任限额"))
        if not quote:
            continue
        policy_match = POLICY_PATTERN.search(document.extracted_text)
        policy = policy_match.group(1) if policy_match else ""
        payload.insurance.append(InsurancePayload(
            document_id=document.id,
            quote=quote,
            confidence=0.74,
            insurer=_institution_from(document.extracted_text) or "待律师核对",
            insurance_type=_matching_line(document, ("交强险", "商业险", "保险类型")) or "待核实",
            policy_number_masked=_mask_number(policy),
            coverage_text=_matching_line(document, ("保险责任", "责任限额", "赔偿限额")),
            materials_complete=bool(policy and ("保险责任" in document.extracted_text or "责任限额" in document.extracted_text)),
        ))

    for document in (item for item in documents if item.category == "伤残鉴定材料"):
        quote = _matching_line(document, ("鉴定意见", "鉴定结论", "鉴定"))
        if not quote:
            continue
        payload.disability_appraisals.append(DisabilityAppraisalPayload(
            document_id=document.id,
            quote=quote,
            confidence=0.72,
            institution=_institution_from(document.extracted_text),
            appraisal_date=_date_from(document.extracted_text),
            opinion_text=quote,
            materials_complete="鉴定意见" in document.extracted_text or "鉴定结论" in document.extracted_text,
        ))

    if not payload.accident_info:
        payload.warnings.append("未从事故认定材料中提取到可验证的事故基本信息。")
    if not payload.injuries:
        payload.warnings.append("未从医疗材料中提取到可验证的伤情记录。")
    if not payload.medical_expenses:
        payload.warnings.append("未从票据材料中提取到可验证的医疗费用。")
    return payload
