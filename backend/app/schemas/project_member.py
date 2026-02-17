from __future__ import annotations
from uuid import UUID
from pydantic import BaseModel, ConfigDict

from app.models.enums import ProjectMemberRole, ProjectMemberStatus
from app.schemas.common import UserSummaryOut


class ProjectMemberInvite(BaseModel):
    username: str
    role: ProjectMemberRole = ProjectMemberRole.CONTRIBUTOR


class ProjectMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: UUID
    user_id: UUID
    role: ProjectMemberRole
    status: ProjectMemberStatus


class ProjectMemberListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: UUID
    role: ProjectMemberRole
    status: ProjectMemberStatus
    user: UserSummaryOut
