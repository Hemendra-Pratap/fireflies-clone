import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.workspace_member import WorkspaceRole
from app.services.auth_service import auth_service
from app.services.workspace_service import workspace_service


def setup_users_and_workspaces(db_session: Session):
    u1 = auth_service.register_user(db_session, "settings_user1@example.com", "Password123!")
    u2 = auth_service.register_user(db_session, "settings_user2@example.com", "Password123!")

    ws1 = workspace_service.get_or_create_default_workspace(db_session, u1)
    ws2 = workspace_service.get_or_create_default_workspace(db_session, u2)

    token1, _ = create_access_token(str(u1.id))
    token2, _ = create_access_token(str(u2.id))

    headers1 = {"Authorization": f"Bearer {token1}"}
    headers2 = {"Authorization": f"Bearer {token2}"}

    return u1, u2, ws1, ws2, headers1, headers2


def test_user_profile_update(unauth_client: TestClient, db_session: Session):
    u1, u2, ws1, ws2, h1, h2 = setup_users_and_workspaces(db_session)

    res = unauth_client.patch(
        "/api/v1/auth/me",
        json={"full_name": "Jane Doe"},
        headers=h1,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["full_name"] == "Jane Doe"
    assert data["email"] == "settings_user1@example.com"

    # Verify persistence
    res_me = unauth_client.get("/api/v1/auth/me", headers=h1)
    assert res_me.json()["full_name"] == "Jane Doe"


def test_password_change_success(unauth_client: TestClient, db_session: Session):
    u1, u2, ws1, ws2, h1, h2 = setup_users_and_workspaces(db_session)

    # Change password
    res = unauth_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "Password123!", "new_password": "NewSecretPassword456!"},
        headers=h1,
    )
    assert res.status_code == 200
    assert "Password updated" in res.json()["message"]

    # Verify old password fails
    res_old = unauth_client.post(
        "/api/v1/auth/login",
        json={"email": "settings_user1@example.com", "password": "Password123!"},
    )
    assert res_old.status_code == 401

    # Verify new password succeeds
    res_new = unauth_client.post(
        "/api/v1/auth/login",
        json={"email": "settings_user1@example.com", "password": "NewSecretPassword456!"},
    )
    assert res_new.status_code == 200
    assert "access_token" in res_new.json()


def test_password_change_invalid_current_password(unauth_client: TestClient, db_session: Session):
    u1, u2, ws1, ws2, h1, h2 = setup_users_and_workspaces(db_session)

    res = unauth_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "WrongPassword!", "new_password": "NewSecretPassword456!"},
        headers=h1,
    )
    assert res.status_code == 400
    assert "Incorrect current password" in res.json()["detail"]


def test_workspace_rename(unauth_client: TestClient, db_session: Session):
    u1, u2, ws1, ws2, h1, h2 = setup_users_and_workspaces(db_session)

    # Owner renames workspace
    res = unauth_client.patch(
        f"/api/v1/workspaces/{ws1.id}",
        json={"name": "Engineering Team Workspace"},
        headers=h1,
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Engineering Team Workspace"

    # Non-member (User 2) attempts to rename User 1's workspace -> 404/403 IDOR protected
    res_unauth = unauth_client.patch(
        f"/api/v1/workspaces/{ws1.id}",
        json={"name": "Hacked Name"},
        headers=h2,
    )
    assert res_unauth.status_code in [403, 404]


def test_workspace_member_listing_and_invitation(unauth_client: TestClient, db_session: Session):
    u1, u2, ws1, ws2, h1, h2 = setup_users_and_workspaces(db_session)

    # List members (initial owner member)
    res_list = unauth_client.get(f"/api/v1/workspaces/{ws1.id}/members", headers=h1)
    assert res_list.status_code == 200
    assert len(res_list.json()) == 1
    assert res_list.json()[0]["role"] == WorkspaceRole.OWNER

    # Invite User 2 as MEMBER
    res_add = unauth_client.post(
        f"/api/v1/workspaces/{ws1.id}/members",
        json={"user_email": "settings_user2@example.com", "role": "MEMBER"},
        headers=h1,
    )
    assert res_add.status_code == 201
    assert res_add.json()["role"] == "MEMBER"

    # Attempt duplicate invitation -> 409 Conflict
    res_dup = unauth_client.post(
        f"/api/v1/workspaces/{ws1.id}/members",
        json={"user_email": "settings_user2@example.com", "role": "MEMBER"},
        headers=h1,
    )
    assert res_dup.status_code == 409


def test_workspace_member_role_update_and_restrictions(unauth_client: TestClient, db_session: Session):
    u1, u2, ws1, ws2, h1, h2 = setup_users_and_workspaces(db_session)

    # Add User 2 to Workspace 1
    m2 = workspace_service.add_member(db_session, workspace_id=ws1.id, user_email=u2.email, role=WorkspaceRole.MEMBER)

    # Owner promotes User 2 to ADMIN
    res_promote = unauth_client.patch(
        f"/api/v1/workspaces/{ws1.id}/members/{m2.id}",
        json={"role": "ADMIN"},
        headers=h1,
    )
    assert res_promote.status_code == 200
    assert res_promote.json()["role"] == "ADMIN"

    # Admin (User 2) attempts to demote Owner (User 1) -> 403 Forbidden
    m1 = workspace_service.get_member(db_session, ws1.id, u1.id)
    res_demote = unauth_client.patch(
        f"/api/v1/workspaces/{ws1.id}/members/{m1.id}",
        json={"role": "MEMBER"},
        headers=h2,
    )
    assert res_demote.status_code == 403


def test_sole_owner_protection(unauth_client: TestClient, db_session: Session):
    u1, u2, ws1, ws2, h1, h2 = setup_users_and_workspaces(db_session)

    m1 = workspace_service.get_member(db_session, ws1.id, u1.id)

    # Attempt to demote sole Owner -> 400 Bad Request
    res_demote = unauth_client.patch(
        f"/api/v1/workspaces/{ws1.id}/members/{m1.id}",
        json={"role": "MEMBER"},
        headers=h1,
    )
    assert res_demote.status_code == 400
    assert "sole Owner" in res_demote.json()["detail"]

    # Attempt to remove sole Owner -> 400 Bad Request
    res_remove = unauth_client.delete(
        f"/api/v1/workspaces/{ws1.id}/members/{m1.id}",
        headers=h1,
    )
    assert res_remove.status_code == 400
    assert "Sole Owner" in res_remove.json()["detail"]


def test_workspace_member_removal_and_access_revocation(unauth_client: TestClient, db_session: Session):
    u1, u2, ws1, ws2, h1, h2 = setup_users_and_workspaces(db_session)

    # Add User 2 to Workspace 1
    m2 = workspace_service.add_member(db_session, workspace_id=ws1.id, user_email=u2.email, role=WorkspaceRole.MEMBER)

    # Verify User 2 can list members in Workspace 1
    res_access1 = unauth_client.get(f"/api/v1/workspaces/{ws1.id}/members", headers=h2)
    assert res_access1.status_code == 200

    # Owner removes User 2
    res_remove = unauth_client.delete(f"/api/v1/workspaces/{ws1.id}/members/{m2.id}", headers=h1)
    assert res_remove.status_code == 204

    # Immediate access revocation: User 2 can no longer access Workspace 1 -> 404/403
    res_access2 = unauth_client.get(f"/api/v1/workspaces/{ws1.id}/members", headers=h2)
    assert res_access2.status_code in [403, 404]
