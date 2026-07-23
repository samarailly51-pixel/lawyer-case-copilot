from __future__ import annotations

import argparse

from sqlalchemy import select

from core.auth import hash_password
from core.database import SessionLocal, init_db
from models.entities import LawFirmWorkspace, User, WorkspaceMembership


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update the first workspace administrator.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--name", default="系统管理员")
    args = parser.parse_args()
    if len(args.password) < 10:
        raise SystemExit("密码至少 10 位")
    init_db()
    with SessionLocal() as db:
        workspace = db.scalar(select(LawFirmWorkspace).order_by(LawFirmWorkspace.created_at))
        if not workspace:
            workspace = LawFirmWorkspace(name="默认律师事务所", slug="default-workspace")
            db.add(workspace); db.flush()
        user = db.scalar(select(User).where(User.email == args.email.lower()))
        if user:
            user.password_hash = hash_password(args.password)
            user.display_name = args.name
        else:
            user = User(email=args.email.lower(), display_name=args.name, password_hash=hash_password(args.password))
            db.add(user); db.flush()
        membership = db.scalar(select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace.id, WorkspaceMembership.user_id == user.id
        ))
        if membership:
            membership.role = "admin"
        else:
            db.add(WorkspaceMembership(workspace_id=workspace.id, user_id=user.id, role="admin"))
        db.commit()
        print(f"管理员已配置：{user.email} / {workspace.name}")


if __name__ == "__main__":
    main()
