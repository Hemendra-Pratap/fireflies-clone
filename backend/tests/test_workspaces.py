import pytest

from app.core.security import create_access_token
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember, WorkspaceRole
from app.services.auth_service import auth_service
from app.services.workspace_service import workspace_service


def test_create_workspace(db_session):
    """Test creating a workspace and auto-assigning owner."""
    user = auth_service.register_user(db_session, "owner@example.com", "password123")
    workspace = workspace_service.create_workspace(db_session, "Engineering Team", user.id)

    assert workspace.name == "Engineering Team"
    assert workspace.owner_id == user.id

    member = workspace_service.get_member(db_session, workspace.id, user.id)
    assert member is not None
    assert member.role == WorkspaceRole.OWNER


def test_get_or_create_default_workspace(db_session):
    """Test getting or auto-creating default personal workspace for user."""
    user = auth_service.register_user(db_session, "user1@example.com", "password123")
    w1 = workspace_service.get_or_create_default_workspace(db_session, user)

    assert w1 is not None
    assert "user1@example.com" in w1.name

    # Calling again should return existing default workspace
    w2 = workspace_service.get_or_create_default_workspace(db_session, user)
    assert w1.id == w2.id


def test_add_workspace_member(db_session):
    """Test adding member to workspace."""
    owner = auth_service.register_user(db_session, "owner2@example.com", "password123")
    member_user = auth_service.register_user(db_session, "member@example.com", "password123")
    workspace = workspace_service.create_workspace(db_session, "Product Team", owner.id)

    new_member = workspace_service.add_member(
        db_session, workspace.id, member_user.email, role=WorkspaceRole.MEMBER
    )
    assert new_member.user_id == member_user.id
    assert new_member.role == WorkspaceRole.MEMBER


def test_verify_workspace_access_success(db_session):
    """Test verifying authorized workspace access."""
    owner = auth_service.register_user(db_session, "owner3@example.com", "password123")
    workspace = workspace_service.create_workspace(db_session, "Design Team", owner.id)

    member = workspace_service.verify_workspace_access(db_session, owner.id, workspace.id)
    assert member.user_id == owner.id


def test_verify_workspace_access_unauthorized(db_session):
    """Test verify_workspace_access raises KeyError for non-member."""
    owner = auth_service.register_user(db_session, "owner4@example.com", "password123")
    other_user = auth_service.register_user(db_session, "other@example.com", "password123")
    workspace = workspace_service.create_workspace(db_session, "Secret Team", owner.id)

    with pytest.raises(KeyError):
        workspace_service.verify_workspace_access(db_session, other_user.id, workspace.id)


def test_workspace_role_permission_check(db_session):
    """Test verifying workspace role permissions."""
    owner = auth_service.register_user(db_session, "owner5@example.com", "password123")
    member_user = auth_service.register_user(db_session, "regular@example.com", "password123")
    workspace = workspace_service.create_workspace(db_session, "DevOps Team", owner.id)

    workspace_service.add_member(db_session, workspace.id, member_user.email, role=WorkspaceRole.MEMBER)

    # Regular member should fail OWNER requirement check
    with pytest.raises(PermissionError):
        workspace_service.verify_workspace_access(
            db_session, member_user.id, workspace.id, required_roles=[WorkspaceRole.OWNER]
        )


def test_list_user_workspaces_endpoint(unauth_client, db_session):
    """Test API endpoint listing user workspaces."""
    user = auth_service.register_user(db_session, "apiuser@example.com", "password123")
    token, _ = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}

    res = unauth_client.get("/api/v1/workspaces", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert data[0]["owner_id"] == user.id


def test_create_workspace_endpoint(unauth_client, db_session):
    """Test API endpoint creating new workspace."""
    user = auth_service.register_user(db_session, "creator@example.com", "password123")
    token, _ = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}

    res = unauth_client.post("/api/v1/workspaces", json={"name": "Marketing Hub"}, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Marketing Hub"
    assert data["owner_id"] == user.id


def test_get_workspace_endpoint_idor_protection(unauth_client, db_session):
    """Test getting workspace details prevents IDOR access for non-members."""
    owner = auth_service.register_user(db_session, "wsowner@example.com", "password123")
    attacker = auth_service.register_user(db_session, "attacker@example.com", "password123")
    workspace = workspace_service.create_workspace(db_session, "Private Vault", owner.id)

    attacker_token, _ = create_access_token(str(attacker.id))
    headers = {"Authorization": f"Bearer {attacker_token}"}

    res = unauth_client.get(f"/api/v1/workspaces/{workspace.id}", headers=headers)
    assert res.status_code == 404
    assert res.json()["detail"] == "Workspace not found"


def test_add_workspace_member_endpoint(unauth_client, db_session):
    """Test API endpoint adding a member to workspace."""
    owner = auth_service.register_user(db_session, "owner_add@example.com", "password123")
    invitee = auth_service.register_user(db_session, "invitee@example.com", "password123")
    workspace = workspace_service.get_or_create_default_workspace(db_session, owner)

    owner_token, _ = create_access_token(str(owner.id))
    headers = {"Authorization": f"Bearer {owner_token}"}

    res = unauth_client.post(
        f"/api/v1/workspaces/{workspace.id}/members",
        json={"user_email": invitee.email, "role": "MEMBER"},
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["user_id"] == invitee.id
    assert data["role"] == "MEMBER"
