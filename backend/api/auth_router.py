from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.auth import Actor, create_access_token, get_current_actor, hash_password, require_role, verify_password
from core.config import settings
from core.database import get_db
from models.entities import LawFirmWorkspace, User, WorkspaceMembership
from schemas.auth import LoginRequest, MemberCreate, MemberRoleUpdate, WorkspaceCreate


auth_router = APIRouter(prefix="/api")


@auth_router.get("/auth/status")
def auth_status(db: Session = Depends(get_db)):
    return {
        "mode": settings.auth_mode,
        "login_required": settings.auth_mode != "disabled",
        "bootstrap_required": settings.auth_mode != "disabled" and db.scalar(select(User.id).limit(1)) is None,
        "public_demo": settings.public_demo_mode,
        "read_only": settings.public_demo_read_only,
    }


@auth_router.post("/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or user.status != "active" or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "邮箱或密码错误")
    query = select(WorkspaceMembership).where(
        WorkspaceMembership.user_id == user.id, WorkspaceMembership.status == "active"
    )
    if payload.workspace_id:
        query = query.where(WorkspaceMembership.workspace_id == payload.workspace_id)
    membership = db.scalar(query.order_by(WorkspaceMembership.created_at))
    if not membership:
        raise HTTPException(403, "用户没有可用的律所工作空间")
    workspace = db.get(LawFirmWorkspace, membership.workspace_id)
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    return {
        "access_token": create_access_token(user.id, membership.workspace_id),
        "token_type": "bearer",
        "expires_in": settings.jwt_expire_minutes * 60,
        "user": {"id": user.id, "email": user.email, "display_name": user.display_name},
        "workspace": {"id": workspace.id, "name": workspace.name, "role": membership.role},
    }


@auth_router.get("/auth/me")
def me(actor: Actor = Depends(get_current_actor)):
    return {
        "user": {"id": actor.user_id, "email": actor.email, "display_name": actor.display_name},
        "workspace": {"id": actor.workspace_id, "name": actor.workspace_name, "role": actor.role},
        "auth_disabled": actor.auth_disabled,
    }


@auth_router.get("/workspaces")
def list_workspaces(actor: Actor = Depends(get_current_actor), db: Session = Depends(get_db)):
    memberships = db.scalars(select(WorkspaceMembership).where(
        WorkspaceMembership.user_id == actor.user_id, WorkspaceMembership.status == "active"
    ))
    result = []
    for membership in memberships:
        workspace = db.get(LawFirmWorkspace, membership.workspace_id)
        if workspace:
            result.append({"id": workspace.id, "name": workspace.name, "slug": workspace.slug, "role": membership.role})
    return result


@auth_router.post("/workspaces", status_code=201)
def create_workspace(payload: WorkspaceCreate, actor: Actor = Depends(get_current_actor), db: Session = Depends(get_db)):
    require_role(actor, "admin")
    if db.scalar(select(LawFirmWorkspace).where(LawFirmWorkspace.slug == payload.slug)):
        raise HTTPException(409, "工作空间标识已存在")
    workspace = LawFirmWorkspace(**payload.model_dump())
    db.add(workspace); db.flush()
    db.add(WorkspaceMembership(workspace_id=workspace.id, user_id=actor.user_id, role="admin"))
    db.commit(); db.refresh(workspace)
    return {"id": workspace.id, "name": workspace.name, "slug": workspace.slug, "role": "admin"}


@auth_router.get("/workspaces/{workspace_id}/members")
def list_members(workspace_id: str, actor: Actor = Depends(get_current_actor), db: Session = Depends(get_db)):
    if actor.workspace_id != workspace_id:
        raise HTTPException(403, "请先切换到该工作空间")
    require_role(actor, "lawyer")
    result = []
    for membership in db.scalars(select(WorkspaceMembership).where(WorkspaceMembership.workspace_id == workspace_id)):
        user = db.get(User, membership.user_id)
        result.append({"id": user.id, "email": user.email, "display_name": user.display_name,
                       "role": membership.role, "status": membership.status})
    return result


@auth_router.post("/workspaces/{workspace_id}/members", status_code=201)
def add_member(payload: MemberCreate, workspace_id: str, actor: Actor = Depends(get_current_actor), db: Session = Depends(get_db)):
    if actor.workspace_id != workspace_id:
        raise HTTPException(403, "请先切换到该工作空间")
    require_role(actor, "admin")
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user:
        user = User(email=payload.email.lower(), display_name=payload.display_name,
                    password_hash=hash_password(payload.password))
        db.add(user); db.flush()
    membership = db.scalar(select(WorkspaceMembership).where(
        WorkspaceMembership.workspace_id == workspace_id, WorkspaceMembership.user_id == user.id
    ))
    if membership:
        raise HTTPException(409, "该用户已是工作空间成员")
    membership = WorkspaceMembership(workspace_id=workspace_id, user_id=user.id, role=payload.role)
    db.add(membership); db.commit()
    return {"id": user.id, "email": user.email, "display_name": user.display_name, "role": membership.role}


@auth_router.patch("/workspaces/{workspace_id}/members/{user_id}")
def update_member_role(payload: MemberRoleUpdate, workspace_id: str, user_id: str,
                       actor: Actor = Depends(get_current_actor), db: Session = Depends(get_db)):
    if actor.workspace_id != workspace_id:
        raise HTTPException(403, "请先切换到该工作空间")
    require_role(actor, "admin")
    membership = db.scalar(select(WorkspaceMembership).where(
        WorkspaceMembership.workspace_id == workspace_id, WorkspaceMembership.user_id == user_id
    ))
    if not membership:
        raise HTTPException(404, "成员不存在")
    if user_id == actor.user_id and payload.role != "admin":
        raise HTTPException(400, "管理员不能降低自己的角色")
    membership.role = payload.role
    db.commit()
    return {"user_id": user_id, "role": membership.role}
