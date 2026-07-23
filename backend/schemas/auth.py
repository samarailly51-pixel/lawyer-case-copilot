from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    workspace_id: str | None = None


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,118}[a-z0-9]$")


class MemberCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=10, max_length=200)
    role: str = Field(pattern=r"^(viewer|assistant|lawyer|admin)$")


class MemberRoleUpdate(BaseModel):
    role: str = Field(pattern=r"^(viewer|assistant|lawyer|admin)$")

