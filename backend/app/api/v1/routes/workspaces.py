from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.workspace_member import WorkspaceRole
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceMemberCreate,
    WorkspaceMemberRead,
    WorkspaceMemberUpdate,
    WorkspaceRead,
    WorkspaceUpdate,
)
from app.services.workspace_service import workspace_service

router = APIRouter()


@router.get(
    "",
    response_model=list[WorkspaceRead],
    status_code=status.HTTP_200_OK,
    summary="List current user workspaces",
)
def list_user_workspaces(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WorkspaceRead]:
    """Retrieve all workspaces where current user is a member."""
    workspace_service.get_or_create_default_workspace(db, current_user)

    memberships = workspace_service.get_user_memberships(db, current_user.id)
    workspaces = [m.workspace for m in memberships if m.workspace]
    return [WorkspaceRead.model_validate(w) for w in workspaces]


@router.post(
    "",
    response_model=WorkspaceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workspace",
)
def create_workspace(
    obj_in: WorkspaceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkspaceRead:
    """Create a new workspace owned by current user."""
    workspace = workspace_service.create_workspace(db, name=obj_in.name, owner_id=current_user.id)
    return WorkspaceRead.model_validate(workspace)


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceRead,
    status_code=status.HTTP_200_OK,
    summary="Get workspace details",
)
def get_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkspaceRead:
    """Retrieve details for a workspace if user is a member (IDOR protected)."""
    try:
        member = workspace_service.verify_workspace_access(db, current_user.id, workspace_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    return WorkspaceRead.model_validate(member.workspace)


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceRead,
    status_code=status.HTTP_200_OK,
    summary="Update workspace details",
)
def update_workspace(
    workspace_id: int,
    obj_in: WorkspaceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkspaceRead:
    """Rename workspace (requires OWNER or ADMIN role)."""
    try:
        workspace_service.verify_workspace_access(
            db, current_user.id, workspace_id, required_roles=[WorkspaceRole.OWNER, WorkspaceRole.ADMIN]
        )
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    except PermissionError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))

    if not obj_in.name or not obj_in.name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workspace name cannot be empty.")

    updated_ws = workspace_service.update_workspace(db, workspace_id=workspace_id, name=obj_in.name)
    return WorkspaceRead.model_validate(updated_ws)


@router.get(
    "/{workspace_id}/members",
    response_model=list[WorkspaceMemberRead],
    status_code=status.HTTP_200_OK,
    summary="List workspace members",
)
def list_workspace_members(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WorkspaceMemberRead]:
    """Retrieve all members of a workspace if user is a member."""
    try:
        workspace_service.verify_workspace_access(db, current_user.id, workspace_id)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    members = workspace_service.list_members(db, workspace_id)
    return [WorkspaceMemberRead.model_validate(m) for m in members]


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add member to workspace",
)
def add_workspace_member(
    workspace_id: int,
    obj_in: WorkspaceMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkspaceMemberRead:
    """Add a member to workspace (requires OWNER or ADMIN role)."""
    try:
        workspace_service.verify_workspace_access(
            db, current_user.id, workspace_id, required_roles=[WorkspaceRole.OWNER, WorkspaceRole.ADMIN]
        )
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    except PermissionError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err))

    try:
        member = workspace_service.add_member(
            db, workspace_id=workspace_id, user_email=obj_in.user_email, role=obj_in.role
        )
    except KeyError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(val_err))

    return WorkspaceMemberRead.model_validate(member)


@router.patch(
    "/{workspace_id}/members/{member_id}",
    response_model=WorkspaceMemberRead,
    status_code=status.HTTP_200_OK,
    summary="Update workspace member role",
)
def update_workspace_member_role(
    workspace_id: int,
    member_id: int,
    obj_in: WorkspaceMemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkspaceMemberRead:
    """Update role of a workspace member."""
    try:
        updated_member = workspace_service.update_member_role(
            db,
            workspace_id=workspace_id,
            member_id=member_id,
            target_role=obj_in.role,
            actor_id=current_user.id,
        )
    except KeyError as key_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(key_err))
    except PermissionError as perm_err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(perm_err))
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))

    return WorkspaceMemberRead.model_validate(updated_member)


@router.delete(
    "/{workspace_id}/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove member from workspace",
)
def remove_workspace_member(
    workspace_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Remove member from workspace or self-leave."""
    try:
        workspace_service.remove_member(
            db,
            workspace_id=workspace_id,
            member_id=member_id,
            actor_id=current_user.id,
        )
    except KeyError as key_err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(key_err))
    except PermissionError as perm_err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(perm_err))
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
