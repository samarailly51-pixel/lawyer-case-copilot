from __future__ import annotations

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from models.entities import (
    CaseWorkspaceLink, LawFirmWorkspace, User, WorkspaceMembership,
)


ROLE_LEVELS = {"viewer": 10, "assistant": 20, "lawyer": 30, "admin": 40}


@dataclass(frozen=True)
class Actor:
    user_id: str
    email: str
    display_name: str
    workspace_id: str
    workspace_name: str
    role: str
    auth_disabled: bool = False


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=64)
    return f"scrypt${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(derived).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt_value, digest_value = encoded.split("$", 2)
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_value)
        expected = base64.urlsafe_b64decode(digest_value)
        actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=64)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: str, workspace_id: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": user_id, "workspace_id": workspace_id, "iat": now, "exp": now + timedelta(minutes=settings.jwt_expire_minutes)},
        settings.jwt_secret,
        algorithm="HS256",
    )


def bootstrap_access(db: Session) -> None:
    if settings.auth_mode != "disabled" and (len(settings.jwt_secret) < 32 or settings.jwt_secret == "development-only-secret-change-me"):
        raise RuntimeError("AUTH_MODE=enabled 时必须配置至少 32 字符的 JWT_SECRET")
    if settings.auth_mode != "disabled" and settings.bootstrap_admin_password and len(settings.bootstrap_admin_password) < 10:
        raise RuntimeError("BOOTSTRAP_ADMIN_PASSWORD 至少 10 位")
    workspace = db.scalar(select(LawFirmWorkspace).order_by(LawFirmWorkspace.created_at))
    if not workspace:
        workspace = LawFirmWorkspace(name=settings.bootstrap_workspace_name, slug="default-workspace")
        db.add(workspace); db.flush()
    user = db.scalar(select(User).where(User.email == settings.bootstrap_admin_email.lower()))
    if not user and (settings.bootstrap_admin_password or settings.auth_mode == "disabled"):
        password = settings.bootstrap_admin_password or base64.urlsafe_b64encode(os.urandom(24)).decode()
        user = User(email=settings.bootstrap_admin_email.lower(), display_name="系统管理员", password_hash=hash_password(password))
        db.add(user); db.flush()
    if user:
        membership = db.scalar(select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace.id, WorkspaceMembership.user_id == user.id
        ))
        if not membership:
            db.add(WorkspaceMembership(workspace_id=workspace.id, user_id=user.id, role="admin"))
    linked_case_ids = set(db.scalars(select(CaseWorkspaceLink.case_id)))
    from models.entities import Case, KnowledgeSource, KnowledgeWorkspaceLink
    for case_id in db.scalars(select(Case.id).where(Case.id.not_in(linked_case_ids or [""]))):
        db.add(CaseWorkspaceLink(case_id=case_id, workspace_id=workspace.id))
    linked_knowledge_ids = set(db.scalars(select(KnowledgeWorkspaceLink.knowledge_source_id)))
    for knowledge_id in db.scalars(select(KnowledgeSource.id).where(KnowledgeSource.id.not_in(linked_knowledge_ids or [""]))):
        db.add(KnowledgeWorkspaceLink(knowledge_source_id=knowledge_id, workspace_id=workspace.id))
    db.commit()


def _actor_from_membership(db: Session, user: User, workspace_id: str | None, disabled: bool = False) -> Actor:
    query = select(WorkspaceMembership).where(
        WorkspaceMembership.user_id == user.id, WorkspaceMembership.status == "active"
    )
    if workspace_id:
        query = query.where(WorkspaceMembership.workspace_id == workspace_id)
    membership = db.scalar(query.order_by(WorkspaceMembership.created_at))
    if not membership:
        raise HTTPException(403, "当前用户不属于所选律所工作空间")
    workspace = db.get(LawFirmWorkspace, membership.workspace_id)
    if not workspace or workspace.status != "active":
        raise HTTPException(403, "律所工作空间不可用")
    return Actor(user.id, user.email, user.display_name, workspace.id, workspace.name, membership.role, disabled)


def get_current_actor(
    authorization: str | None = Header(default=None),
    x_workspace_id: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Actor:
    if settings.auth_mode == "disabled":
        user = db.scalar(select(User).order_by(User.created_at))
        if not user:
            bootstrap_access(db)
            user = db.scalar(select(User).order_by(User.created_at))
        return _actor_from_membership(db, user, x_workspace_id, True)
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "请先登录", headers={"WWW-Authenticate": "Bearer"})
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(401, "登录凭证无效或已过期") from exc
    user = db.get(User, payload.get("sub"))
    if not user or user.status != "active":
        raise HTTPException(401, "用户不可用")
    return _actor_from_membership(db, user, x_workspace_id or payload.get("workspace_id"))


def require_role(actor: Actor, minimum: str) -> None:
    if ROLE_LEVELS.get(actor.role, 0) < ROLE_LEVELS[minimum]:
        raise HTTPException(403, f"该操作需要 {minimum} 或更高角色")


def require_case_access(db: Session, actor: Actor, case_id: str, minimum: str = "viewer") -> None:
    require_role(actor, minimum)
    link = db.scalar(select(CaseWorkspaceLink).where(
        CaseWorkspaceLink.case_id == case_id, CaseWorkspaceLink.workspace_id == actor.workspace_id
    ))
    if not link:
        raise HTTPException(404, "案件不存在或不属于当前工作空间")
