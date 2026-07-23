from __future__ import annotations

import base64
import os
from dataclasses import replace
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

import core.auth as auth_module
import api.auth_router as auth_router_module
import main as main_module
import storage_backends.local as local_storage_module
from core.auth import create_access_token, hash_password, verify_password
from core.config import settings
from core.database import SessionLocal
from core.privacy import redact_text
from main import app
from models.entities import LawFirmWorkspace, User, WorkspaceMembership
from models.entities import Case, AgentRun
from services.worker import claim_next_run
from storage_backends.local import LocalStorageBackend
from workflows import WorkflowOrchestrator


def test_password_hash_and_sensitive_text_redaction():
    encoded = hash_password("Secure-Test-Password-2026")
    assert verify_password("Secure-Test-Password-2026", encoded)
    assert not verify_password("wrong-password", encoded)
    result = redact_text("联系 13812345678，身份证 11010519900101123X，邮箱 user@example.com")
    assert result.replacements == 3
    assert "13812345678" not in result.text
    assert "11010519900101123X" not in result.text


def test_encrypted_local_storage_round_trip(tmp_path, monkeypatch):
    key = base64.urlsafe_b64encode(os.urandom(32)).decode()
    isolated = replace(settings, upload_dir=tmp_path, encrypt_uploads=True, storage_encryption_key=key)
    monkeypatch.setattr(local_storage_module, "settings", isolated)
    backend = LocalStorageBackend()
    original = "完全虚构的案件材料".encode("utf-8")
    stored = backend.put("case-test", "材料.txt", original)
    assert stored.encrypted is True
    assert (tmp_path / stored.key).read_bytes() != original
    assert backend.get(stored.key) == original


def test_workspace_isolation_and_viewer_permissions(monkeypatch):
    with TestClient(app) as client:
        with SessionLocal() as db:
            suffix = uuid4().hex[:10]
            workspace = LawFirmWorkspace(name="隔离测试律所", slug=f"isolation-{suffix}")
            user = User(email=f"viewer-{suffix}@example.local", display_name="只读成员",
                        password_hash=hash_password("Viewer-Test-Password-2026"))
            db.add_all([workspace, user]); db.flush()
            db.add(WorkspaceMembership(workspace_id=workspace.id, user_id=user.id, role="viewer"))
            db.commit(); workspace_id, user_id = workspace.id, user.id
        secured_settings = replace(settings, auth_mode="enabled", jwt_secret="test-jwt-secret-that-is-longer-than-32-bytes")
        monkeypatch.setattr(auth_module, "settings", secured_settings)
        token = create_access_token(user_id, workspace_id)
        headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": workspace_id}
        cases = client.get("/api/cases", headers=headers)
        assert cases.status_code == 200
        assert cases.json() == []
        create = client.post("/api/cases", headers=headers, json={
            "title": "无权创建的案件", "case_type": "contract", "stage": "intake",
            "client_name": "", "opposing_party": "", "lead_lawyer": "只读成员",
        })
        assert create.status_code == 403
        knowledge = client.post("/api/knowledge/search", headers=headers,
                                json={"query": "合同证据", "scopes": ["general"], "limit": 5})
        assert knowledge.status_code == 200
        assert knowledge.json() == []


def test_report_exports_docx_and_markdown():
    with TestClient(app) as client:
        case = next(item for item in client.get("/api/cases").json() if item["case_type"] == "traffic_injury")
        workspace = client.get(f"/api/cases/{case['id']}/workspace").json()
        report = workspace["reports"][0]
        docx = client.get(f"/api/cases/{case['id']}/reports/{report['id']}/export?format=docx")
        assert docx.status_code == 200
        assert docx.content.startswith(b"PK")
        markdown = client.get(f"/api/cases/{case['id']}/reports/{report['id']}/export?format=md")
        assert markdown.status_code == 200
        assert "不构成正式法律意见" in markdown.content.decode("utf-8")


def test_database_queue_claim_and_execution():
    with TestClient(app):
        with SessionLocal() as db:
            case = db.scalar(select(Case).order_by(Case.created_at))
            run = WorkflowOrchestrator(db).create_run(case.id, "queue_test")
            run_id = run.id
        assert claim_next_run() == run_id
        with SessionLocal() as db:
            assert db.get(AgentRun, run_id).status == "claimed"
            WorkflowOrchestrator(db).execute(run_id)
            assert db.get(AgentRun, run_id).status == "awaiting_review"


def test_public_demo_is_server_side_read_only(monkeypatch):
    demo_settings = replace(settings, public_demo_mode=True, public_demo_read_only=True)
    monkeypatch.setattr(main_module, "settings", demo_settings)
    monkeypatch.setattr(auth_router_module, "settings", demo_settings)
    with TestClient(app) as client:
        status = client.get("/api/auth/status")
        assert status.status_code == 200
        assert status.json()["public_demo"] is True
        assert status.json()["read_only"] is True
        cases = client.get("/api/cases")
        assert cases.status_code == 200
        blocked = client.post("/api/cases", json={
            "title": "不应创建的公网案件", "case_type": "contract", "stage": "intake",
            "client_name": "", "opposing_party": "", "lead_lawyer": "访客",
        })
        assert blocked.status_code == 403
        assert blocked.json()["code"] == "PUBLIC_DEMO_READ_ONLY"
        traffic = next(item for item in cases.json() if item["case_type"] == "traffic_injury")
        scenario = client.post(f"/api/cases/{traffic['id']}/compensation-scenario", json={
            "parameters": {"medical_expense": 100}
        })
        assert scenario.status_code == 200
