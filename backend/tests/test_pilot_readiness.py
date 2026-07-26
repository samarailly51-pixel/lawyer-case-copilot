from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from core.database import SessionLocal
from core.malware import scan_upload
from main import app
from models.entities import Case, Document
from nodes.mvp import _persist_traffic_payload
from schemas.traffic_injury import AccidentInfoPayload, TrafficInjuryExtractionPayload
from services.rules import validate_rule_file


def test_bundled_rule_files_are_valid():
    root = Path(__file__).resolve().parents[1] / "rules" / "traffic_injury"
    evidence = validate_rule_file(root / "evidence_completeness.yaml")
    personal = validate_rule_file(root / "personal_experience_rules.yaml")
    assert evidence.valid is True
    assert evidence.enabled_rule_count >= 1
    assert personal.valid is True
    assert personal.enabled_rule_count == 0


def test_invalid_high_risk_rule_is_rejected(tmp_path):
    path = tmp_path / "invalid.yaml"
    path.write_text(
        """
version: 1
rules:
  - id: personal.invalid
    enabled: true
    description: 测试规则
    severity: high
    output_type: risk
    requires_human_review: false
""",
        encoding="utf-8",
    )
    validation = validate_rule_file(path)
    assert validation.valid is False
    assert any("requires_human_review=true" in error for error in validation.errors)


def test_required_malware_scan_fails_closed(monkeypatch):
    import core.malware as malware_module

    monkeypatch.setattr(
        malware_module,
        "settings",
        SimpleNamespace(
            malware_scan_provider="disabled",
            malware_scan_required=True,
            app_env="production",
        ),
    )
    with pytest.raises(ValueError, match="MALWARE_SCAN_PROVIDER"):
        scan_upload(b"synthetic test")


def test_readiness_endpoint_exposes_blocking_configuration():
    with TestClient(app) as client:
        response = client.get("/api/system/readiness")
        assert response.status_code == 200
        report = response.json()
        assert report["ready"] is False
        check_ids = {item["id"] for item in report["checks"]}
        assert {"auth", "database", "object_storage", "malware_scan", "retention"} <= check_ids


def test_specialist_output_with_unverifiable_quote_is_rejected():
    with TestClient(app) as client:
        case = client.post("/api/cases", json={
            "title": "专业引用拒绝测试",
            "case_type": "traffic_injury",
            "client_name": "测试委托人",
        }).json()
        uploaded = client.post(
            f"/api/cases/{case['id']}/documents",
            files={"file": (
                "事故认定书.txt",
                "事故时间：2026年1月2日\n责任认定：测试原文。\n".encode("utf-8"),
                "text/plain",
            )},
        ).json()

    payload = TrafficInjuryExtractionPayload(
        accident_info=AccidentInfoPayload(
            document_id=uploaded["id"],
            quote="这段文字并不存在于材料中",
            confidence=0.9,
            responsibility_text="不得落库的模型输出",
        )
    )
    with SessionLocal() as db:
        persisted_case = db.scalar(select(Case).where(Case.id == case["id"]))
        documents = list(db.scalars(select(Document).where(Document.case_id == case["id"])))
        created, rejected = _persist_traffic_payload(
            db,
            persisted_case,
            "test-run",
            payload,
            documents,
        )
        assert created == 0
        assert rejected == 1
        db.rollback()


def test_specialist_output_with_exact_quote_but_invented_field_is_rejected():
    with TestClient(app) as client:
        case = client.post("/api/cases", json={
            "title": "专业字段忠实性测试",
            "case_type": "traffic_injury",
            "client_name": "测试委托人",
        }).json()
        source_text = "事故时间：2026年1月2日\n责任认定：测试原文。\n"
        uploaded = client.post(
            f"/api/cases/{case['id']}/documents",
            files={"file": ("事故认定书.txt", source_text.encode("utf-8"), "text/plain")},
        ).json()

    payload = TrafficInjuryExtractionPayload(
        accident_info=AccidentInfoPayload(
            document_id=uploaded["id"],
            quote="责任认定：测试原文。",
            confidence=0.9,
            location="材料中不存在的虚构地点",
            responsibility_text="责任认定：测试原文。",
        )
    )
    with SessionLocal() as db:
        persisted_case = db.scalar(select(Case).where(Case.id == case["id"]))
        documents = list(db.scalars(select(Document).where(Document.case_id == case["id"])))
        created, rejected = _persist_traffic_payload(
            db,
            persisted_case,
            "test-run",
            payload,
            documents,
        )
        assert created == 0
        assert rejected == 1
        db.rollback()
