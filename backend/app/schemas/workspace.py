from datetime import datetime
from pydantic import Field

from app.schemas.base import ORMModel
from app.schemas.auth import UserRead


class WorkspaceMemberRead(ORMModel):
    id: int
    workspace_id: int
    user_id: int
    role: str
    created_at: datetime
    user: UserRead | None = None


class WorkspaceMemberCreate(ORMModel):
    user_email: str
    role: str = Field(default="MEMBER")


class WorkspaceRead(ORMModel):
    id: int
    name: str
    owner_id: int
    created_at: datetime
    updated_at: datetime
    members: list[WorkspaceMemberRead] = Field(default_factory=list)


class WorkspaceCreate(ORMModel):
    name: str = Field(..., min_length=1, max_length=255)


class WorkspaceUpdate(ORMModel):
    name: str | None = Field(None, min_length=1, max_length=255)


class WorkspaceMemberUpdate(ORMModel):
    role: str = Field(..., description="Target role (OWNER, ADMIN, MEMBER)")
