import logging
from sqlalchemy.orm import Session, joinedload

from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember, WorkspaceRole

logger = logging.getLogger(__name__)


class WorkspaceService:
    """Service handling workspace management, membership, and authorization."""

    def get_user_memberships(self, db: Session, user_id: int) -> list[WorkspaceMember]:
        """Fetch all workspace memberships for a given user."""
        return (
            db.query(WorkspaceMember)
            .options(joinedload(WorkspaceMember.workspace))
            .filter(WorkspaceMember.user_id == user_id)
            .all()
        )

    def get_or_create_default_workspace(self, db: Session, user: User) -> Workspace:
        """Get existing user workspace or create a default personal workspace if none exists."""
        memberships = self.get_user_memberships(db, user.id)
        if memberships:
            return memberships[0].workspace

        # Create new default personal workspace
        workspace_name = f"{user.email}'s Workspace" if user.email else "Personal Workspace"
        workspace = Workspace(name=workspace_name, owner_id=user.id)
        db.add(workspace)
        db.flush()

        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=user.id,
            role=WorkspaceRole.OWNER,
        )
        db.add(member)
        db.commit()
        db.refresh(workspace)
        return workspace

    def get_member(self, db: Session, workspace_id: int, user_id: int) -> WorkspaceMember | None:
        """Get membership record for a specific user and workspace."""
        return (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
            .first()
        )

    def is_member(self, db: Session, workspace_id: int, user_id: int) -> bool:
        """Check if user is a member of a given workspace."""
        return self.get_member(db, workspace_id, user_id) is not None

    def verify_workspace_access(
        self,
        db: Session,
        user_id: int,
        workspace_id: int,
        required_roles: list[str] | None = None,
    ) -> WorkspaceMember:
        """Verify user is a member of workspace with optional required roles. Raises KeyError if unauthorized."""
        member = self.get_member(db, workspace_id, user_id)
        if not member:
            raise KeyError(f"User {user_id} is not a member of workspace {workspace_id}")

        if required_roles and member.role not in required_roles:
            raise PermissionError(
                f"Role '{member.role}' does not have required permissions ({required_roles}) in workspace {workspace_id}"
            )

        return member

    def create_workspace(self, db: Session, name: str, owner_id: int) -> Workspace:
        """Create a new workspace and assign owner membership."""
        workspace = Workspace(name=name.strip(), owner_id=owner_id)
        db.add(workspace)
        db.flush()

        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=owner_id,
            role=WorkspaceRole.OWNER,
        )
        db.add(member)
        db.commit()
        db.refresh(workspace)
        return workspace

    def update_workspace(self, db: Session, workspace_id: int, name: str) -> Workspace:
        """Update workspace details such as name."""
        workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not workspace:
            raise KeyError(f"Workspace {workspace_id} not found.")
        workspace.name = name.strip()
        db.commit()
        db.refresh(workspace)
        return workspace

    def list_members(self, db: Session, workspace_id: int) -> list[WorkspaceMember]:
        """Fetch all members of a workspace with joined User objects."""
        return (
            db.query(WorkspaceMember)
            .options(joinedload(WorkspaceMember.user))
            .filter(WorkspaceMember.workspace_id == workspace_id)
            .all()
        )

    def add_member(
        self, db: Session, workspace_id: int, user_email: str, role: str = WorkspaceRole.MEMBER
    ) -> WorkspaceMember:
        """Add a member to a workspace by email."""
        user = db.query(User).filter(User.email == user_email.strip().lower()).first()
        if not user:
            raise KeyError(f"User with email '{user_email}' not found.")

        existing = self.get_member(db, workspace_id, user.id)
        if existing:
            raise ValueError(f"User '{user_email}' is already a member of this workspace.")

        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user.id,
            role=role,
        )
        db.add(member)
        db.commit()
        db.refresh(member)
        return member

    def update_member_role(
        self, db: Session, workspace_id: int, member_id: int, target_role: str, actor_id: int
    ) -> WorkspaceMember:
        """Update a workspace member's role with role restrictions and sole-owner protections."""
        actor_member = self.verify_workspace_access(
            db, actor_id, workspace_id, required_roles=[WorkspaceRole.OWNER, WorkspaceRole.ADMIN]
        )

        target_member = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.id == member_id,
                WorkspaceMember.workspace_id == workspace_id,
            )
            .first()
        )
        if not target_member:
            raise KeyError(f"Member record {member_id} not found in workspace {workspace_id}")

        # ADMIN restrictions
        if actor_member.role == WorkspaceRole.ADMIN:
            if target_role == WorkspaceRole.OWNER or target_member.role in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
                raise PermissionError("Admins cannot modify roles of Owners or Admins.")

        # Sole owner protection
        if target_member.role == WorkspaceRole.OWNER and target_role != WorkspaceRole.OWNER:
            owner_count = (
                db.query(WorkspaceMember)
                .filter(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.role == WorkspaceRole.OWNER,
                )
                .count()
            )
            if owner_count <= 1:
                raise ValueError("Cannot demote the sole Owner of a workspace. Transfer ownership first.")

        target_member.role = target_role
        if target_role == WorkspaceRole.OWNER:
            workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
            if workspace:
                workspace.owner_id = target_member.user_id

        db.commit()
        db.refresh(target_member)
        return target_member

    def remove_member(
        self, db: Session, workspace_id: int, member_id: int, actor_id: int
    ) -> None:
        """Remove a member from a workspace with role checks and sole-owner protections."""
        actor_member = self.verify_workspace_access(db, actor_id, workspace_id)

        target_member = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.id == member_id,
                WorkspaceMember.workspace_id == workspace_id,
            )
            .first()
        )
        if not target_member:
            raise KeyError(f"Member record {member_id} not found in workspace {workspace_id}")

        is_self_removal = target_member.user_id == actor_id

        if not is_self_removal:
            if actor_member.role not in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
                raise PermissionError("Only Owners and Admins can remove members.")
            if actor_member.role == WorkspaceRole.ADMIN and target_member.role in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
                raise PermissionError("Admins cannot remove Owners or other Admins.")

        # Sole owner protection
        if target_member.role == WorkspaceRole.OWNER:
            owner_count = (
                db.query(WorkspaceMember)
                .filter(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.role == WorkspaceRole.OWNER,
                )
                .count()
            )
            if owner_count <= 1:
                raise ValueError("Sole Owner cannot leave or be removed from the workspace. Transfer ownership or delete workspace.")

        db.delete(target_member)
        db.commit()


workspace_service = WorkspaceService()
