from app.core.security import verify_password
from app.models.user import User


def test_register_user_success(client, db_session):
    """Verify successful user registration returns 201 Created and user metadata."""
    payload = {
        "email": "newuser@example.com",
        "password": "StrongPassword123!",
    }

    response = client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 201
    data = response.json()

    assert data["id"] is not None
    assert data["email"] == "newuser@example.com"
    assert "created_at" in data
    assert "updated_at" in data
    assert "password" not in data
    assert "password_hash" not in data
    assert "StrongPassword123!" not in response.text

    # Verify database persistence & password hashing
    user = db_session.query(User).filter(User.email == "newuser@example.com").first()
    assert user is not None
    assert user.email == "newuser@example.com"
    assert user.password_hash.startswith("$argon2id$")
    assert verify_password("StrongPassword123!", user.password_hash) is True


def test_register_user_duplicate_email_409(client):
    """Verify duplicate email registration returns 409 Conflict."""
    payload = {
        "email": "duplicate@example.com",
        "password": "StrongPassword123!",
    }

    resp1 = client.post("/api/v1/auth/register", json=payload)
    assert resp1.status_code == 201

    resp2 = client.post("/api/v1/auth/register", json=payload)
    assert resp2.status_code == 409
    assert "already exists" in resp2.json()["detail"]


def test_register_user_email_normalization(client, db_session):
    """Verify email with uppercase letters and surrounding whitespace is normalized."""
    payload = {
        "email": "  TEST.USER@Example.COM  ",
        "password": "StrongPassword123!",
    }

    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    assert response.json()["email"] == "test.user@example.com"

    user = db_session.query(User).filter(User.email == "test.user@example.com").first()
    assert user is not None


def test_register_user_short_password_422(client):
    """Verify password shorter than 8 characters returns 422 Unprocessable Entity."""
    payload = {
        "email": "shortpass@example.com",
        "password": "short",  # 5 characters (< 8)
    }

    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


def test_register_user_invalid_email_422(client):
    """Verify invalid email format returns 422 Unprocessable Entity."""
    payload = {
        "email": "not_an_email",
        "password": "StrongPassword123!",
    }

    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


def test_login_success_and_jwt_claims(client, db_session):
    """Verify successful login returns HTTP 200, valid JWT bearer token, and claims."""
    from app.core.security import decode_access_token

    # 1. Register user
    reg_payload = {"email": "loginuser@example.com", "password": "MySecretPassword123!"}
    reg_resp = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201
    user_id = reg_resp.json()["id"]

    # 2. Login
    login_payload = {"email": "loginuser@example.com", "password": "MySecretPassword123!"}
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0

    # 3. Decode & verify JWT claims
    claims = decode_access_token(data["access_token"])
    assert claims["sub"] == str(user_id)
    assert "exp" in claims
    assert "iat" in claims
    assert "password" not in claims
    assert "password_hash" not in claims


def test_login_email_normalization(client):
    """Verify login accepts uppercase and whitespace-padded email."""
    reg_payload = {"email": "normuser@example.com", "password": "MySecretPassword123!"}
    client.post("/api/v1/auth/register", json=reg_payload)

    login_payload = {"email": "  NORMUSER@Example.COM  ", "password": "MySecretPassword123!"}
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_incorrect_password_401(client):
    """Verify login with incorrect password returns HTTP 401 Unauthorized with generic detail."""
    reg_payload = {"email": "wrongpass@example.com", "password": "CorrectPassword123!"}
    client.post("/api/v1/auth/register", json=reg_payload)

    login_payload = {"email": "wrongpass@example.com", "password": "WrongPassword123!"}
    response = client.post("/api/v1/auth/login", json=login_payload)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_nonexistent_email_401(client):
    """Verify login with nonexistent email returns identical HTTP 401 Unauthorized."""
    login_payload = {"email": "nonexistent@example.com", "password": "AnyPassword123!"}
    response = client.post("/api/v1/auth/login", json=login_payload)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_invalid_email_format_422(client):
    """Verify login with invalid email format returns HTTP 422 Unprocessable Entity."""
    login_payload = {"email": "not_an_email_at_all", "password": "SomePassword123!"}
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 422


def test_login_missing_password_422(client):
    """Verify login with missing password returns HTTP 422 Unprocessable Entity."""
    login_payload = {"email": "user@example.com"}
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 422


def test_get_current_user_valid_jwt_success(unauth_client):
    """Verify valid JWT Bearer header resolves current user via GET /api/v1/auth/me."""
    reg_payload = {"email": "me_test@example.com", "password": "MySecretPassword123!"}
    reg_resp = unauth_client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201
    user_id = reg_resp.json()["id"]

    login_resp = unauth_client.post("/api/v1/auth/login", json=reg_payload)
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    me_resp = unauth_client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    data = me_resp.json()
    assert data["id"] == user_id
    assert data["email"] == "me_test@example.com"


def test_get_current_user_missing_header_401(unauth_client):
    """Verify missing Authorization header returns HTTP 401 Unauthorized."""
    me_resp = unauth_client.get("/api/v1/auth/me")
    assert me_resp.status_code == 401
    assert me_resp.headers.get("WWW-Authenticate") == "Bearer"


def test_get_current_user_malformed_header_401(unauth_client):
    """Verify malformed Authorization header returns HTTP 401 Unauthorized."""
    headers = {"Authorization": "Bearer not_a_valid_jwt_token"}
    me_resp = unauth_client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 401


def test_get_current_user_invalid_signature_401(unauth_client):
    """Verify JWT signed with different secret key returns HTTP 401 Unauthorized."""
    import jwt
    bad_token = jwt.encode({"sub": "1"}, "wrong_secret_key_32_bytes_long_123456", algorithm="HS256")
    headers = {"Authorization": f"Bearer {bad_token}"}
    me_resp = unauth_client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 401


def test_get_current_user_expired_jwt_401(unauth_client):
    """Verify expired JWT token returns HTTP 401 Unauthorized."""
    from datetime import datetime, timedelta, timezone
    from app.core.config import settings
    import jwt

    expired_payload = {
        "sub": "1",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=10),
    }
    expired_token = jwt.encode(expired_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    headers = {"Authorization": f"Bearer {expired_token}"}
    me_resp = unauth_client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 401


def test_get_current_user_missing_sub_401(unauth_client):
    """Verify JWT token missing 'sub' claim returns HTTP 401 Unauthorized."""
    from datetime import datetime, timedelta, timezone
    from app.core.config import settings
    import jwt

    payload = {"exp": datetime.now(timezone.utc) + timedelta(minutes=30)}
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    headers = {"Authorization": f"Bearer {token}"}
    me_resp = unauth_client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 401


def test_get_current_user_nonexistent_user_id_401(unauth_client):
    """Verify valid JWT with nonexistent user ID returns HTTP 401 Unauthorized."""
    from app.core.security import create_access_token

    token, _ = create_access_token(subject=999999)
    headers = {"Authorization": f"Bearer {token}"}
    me_resp = unauth_client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 401


def test_get_current_user_dependency_direct(db_session):
    """Verify direct call to get_current_user returns actual SQLAlchemy User instance."""
    from fastapi.security import HTTPAuthorizationCredentials
    from app.api.deps import get_current_user
    from app.core.security import create_access_token
    from app.models.user import User

    user = User(email="direct_dep@example.com", password_hash="hash")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token, _ = create_access_token(subject=user.id)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    resolved_user = get_current_user(credentials=credentials, db=db_session)
    assert resolved_user.id == user.id
    assert resolved_user.email == "direct_dep@example.com"


def test_unauthenticated_meeting_endpoints_401(unauth_client):
    """Verify unauthenticated requests to meeting endpoints return 401 Unauthorized."""
    endpoints = [
        ("GET", "/api/v1/meetings"),
        ("POST", "/api/v1/meetings"),
        ("GET", "/api/v1/meetings/search?q=test"),
        ("GET", "/api/v1/meetings/1"),
        ("PATCH", "/api/v1/meetings/1"),
        ("DELETE", "/api/v1/meetings/1"),
        ("GET", "/api/v1/meetings/1/status"),
        ("POST", "/api/v1/meetings/1/transcribe"),
        ("POST", "/api/v1/meetings/1/analyze"),
        ("GET", "/api/v1/meetings/1/summary"),
        ("GET", "/api/v1/meetings/1/action-items"),
        ("GET", "/api/v1/meetings/1/chapters"),
        ("GET", "/api/v1/meetings/1/transcript"),
        ("GET", "/api/v1/meetings/1/intelligence"),
        ("PATCH", "/api/v1/action-items/1"),
    ]

    for method, path in endpoints:
        if method == "GET":
            res = unauth_client.get(path)
        elif method == "POST":
            res = unauth_client.post(path, json={"title": "Test", "recorded_at": "2026-08-13T12:00:00Z"})
        elif method == "PATCH":
            res = unauth_client.patch(path, json={"title": "Updated"})
        elif method == "DELETE":
            res = unauth_client.delete(path)
        
        assert res.status_code == 401, f"Endpoint {method} {path} should return 401, got {res.status_code}"
        assert res.headers.get("WWW-Authenticate") == "Bearer"


def test_authenticated_meeting_creation_assigns_user_id(unauth_client, db_session):
    """Verify POST /api/v1/meetings automatically assigns the authenticated user's ID."""
    # Register and login to get a real token
    reg_payload = {"email": "user_a_creation@example.com", "password": "StrongPassword123!"}
    reg_resp = unauth_client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201
    user_id = reg_resp.json()["id"]

    login_resp = unauth_client.post("/api/v1/auth/login", json=reg_payload)
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    res = unauth_client.post(
        "/api/v1/meetings",
        json={"title": "User A Meeting", "recorded_at": "2026-08-13T12:00:00Z"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["user_id"] == user_id
    assert data["title"] == "User A Meeting"


def test_meeting_ownership_isolation_cross_user_access_404(unauth_client, db_session):
    """Verify IDOR protection: User B cannot access User A's meeting (returns 404)."""
    from datetime import datetime, timezone
    from app.core.security import create_access_token
    from app.models.meeting import Meeting
    from app.models.user import User

    user_a = User(email="usera_idor@example.com", password_hash="hash")
    user_b = User(email="userb_idor@example.com", password_hash="hash")
    db_session.add_all([user_a, user_b])
    db_session.commit()

    meeting_a = Meeting(
        title="User A Private Meeting",
        recorded_at=datetime.now(timezone.utc),
        user_id=user_a.id,
    )
    db_session.add(meeting_a)
    db_session.commit()
    db_session.refresh(meeting_a)

    token_b, _ = create_access_token(subject=user_b.id)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # GET User A's meeting as User B -> 404
    get_res = unauth_client.get(f"/api/v1/meetings/{meeting_a.id}", headers=headers_b)
    assert get_res.status_code == 404
    assert get_res.json()["detail"] == "Meeting not found"

    # GET User A's meeting status as User B -> 404
    status_res = unauth_client.get(f"/api/v1/meetings/{meeting_a.id}/status", headers=headers_b)
    assert status_res.status_code == 404

    # GET User A's intelligence as User B -> 404
    intel_res = unauth_client.get(f"/api/v1/meetings/{meeting_a.id}/intelligence", headers=headers_b)
    assert intel_res.status_code == 404


def test_meeting_cross_user_patch_and_delete_404(unauth_client, db_session):
    """Verify User B cannot update or delete User A's meeting (returns 404)."""
    from datetime import datetime, timezone
    from app.core.security import create_access_token
    from app.models.meeting import Meeting
    from app.models.user import User

    user_a = User(email="usera_patch@example.com", password_hash="hash")
    user_b = User(email="userb_patch@example.com", password_hash="hash")
    db_session.add_all([user_a, user_b])
    db_session.commit()

    meeting_a = Meeting(
        title="Original Title",
        recorded_at=datetime.now(timezone.utc),
        user_id=user_a.id,
    )
    db_session.add(meeting_a)
    db_session.commit()
    db_session.refresh(meeting_a)

    token_b, _ = create_access_token(subject=user_b.id)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # PATCH -> 404
    patch_res = unauth_client.patch(
        f"/api/v1/meetings/{meeting_a.id}",
        json={"title": "Hacked Title"},
        headers=headers_b,
    )
    assert patch_res.status_code == 404

    # DELETE -> 404
    del_res = unauth_client.delete(f"/api/v1/meetings/{meeting_a.id}", headers=headers_b)
    assert del_res.status_code == 404

    # Verify meeting A still exists in DB
    refreshed_meeting = db_session.query(Meeting).filter(Meeting.id == meeting_a.id).first()
    assert refreshed_meeting is not None
    assert refreshed_meeting.title == "Original Title"


def test_meeting_cross_user_search_isolated(unauth_client, db_session):
    """Verify search only returns meetings belonging to the authenticated user."""
    from datetime import datetime, timezone
    from app.core.security import create_access_token
    from app.models.meeting import Meeting
    from app.models.user import User

    user_a = User(email="search_a@example.com", password_hash="hash")
    user_b = User(email="search_b@example.com", password_hash="hash")
    db_session.add_all([user_a, user_b])
    db_session.commit()

    m_a = Meeting(
        title="Secret Q3 Financials",
        recorded_at=datetime.now(timezone.utc),
        user_id=user_a.id,
    )
    m_b = Meeting(
        title="Public Q3 Financials",
        recorded_at=datetime.now(timezone.utc),
        user_id=user_b.id,
    )
    db_session.add_all([m_a, m_b])
    db_session.commit()

    token_b, _ = create_access_token(subject=user_b.id)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    search_res = unauth_client.get("/api/v1/meetings/search?q=Financials", headers=headers_b)
    assert search_res.status_code == 200
    items = search_res.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == m_b.id
    assert items[0]["title"] == "Public Q3 Financials"


def test_action_item_cross_user_patch_404(unauth_client, db_session):
    """Verify User B cannot update an action item belonging to User A's meeting (returns 404)."""
    from datetime import datetime, timezone
    from app.core.security import create_access_token
    from app.models.action_item import ActionItem
    from app.models.meeting import Meeting
    from app.models.user import User

    user_a = User(email="action_a@example.com", password_hash="hash")
    user_b = User(email="action_b@example.com", password_hash="hash")
    db_session.add_all([user_a, user_b])
    db_session.commit()

    meeting_a = Meeting(
        title="Meeting A",
        recorded_at=datetime.now(timezone.utc),
        user_id=user_a.id,
    )
    db_session.add(meeting_a)
    db_session.commit()

    item_a = ActionItem(meeting_id=meeting_a.id, description="User A action item", is_completed=False)
    db_session.add(item_a)
    db_session.commit()

    token_b, _ = create_access_token(subject=user_b.id)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    res = unauth_client.patch(
        f"/api/v1/action-items/{item_a.id}",
        json={"is_completed": True},
        headers=headers_b,
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "Action item not found"

    # Verify action item was not modified
    refreshed_item = db_session.query(ActionItem).filter(ActionItem.id == item_a.id).first()
    assert refreshed_item.is_completed is False


def test_cross_user_audio_upload_transcript_analyze_404(unauth_client, db_session):
    """Verify User B cannot upload audio, trigger transcription, or AI analysis on User A's meeting."""
    from datetime import datetime, timezone
    from app.core.security import create_access_token
    from app.models.meeting import Meeting, MeetingStatus
    from app.models.user import User

    user_a = User(email="upload_a@example.com", password_hash="hash")
    user_b = User(email="upload_b@example.com", password_hash="hash")
    db_session.add_all([user_a, user_b])
    db_session.commit()

    meeting_a = Meeting(
        title="User A Audio Meeting",
        recorded_at=datetime.now(timezone.utc),
        status=MeetingStatus.UPLOADED,
        audio_file_path="storage/fake.mp3",
        user_id=user_a.id,
    )
    db_session.add(meeting_a)
    db_session.commit()
    db_session.refresh(meeting_a)

    token_b, _ = create_access_token(subject=user_b.id)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    mid = meeting_a.id

    # Audio upload -> 404
    dummy_audio = b"ID3 dummy"
    files = {"file": ("test.mp3", dummy_audio, "audio/mpeg")}
    audio_res = unauth_client.post(f"/api/v1/meetings/{mid}/audio", files=files, headers=headers_b)
    assert audio_res.status_code == 404

    # Transcription -> 404
    transcribe_res = unauth_client.post(f"/api/v1/meetings/{mid}/transcribe", headers=headers_b)
    assert transcribe_res.status_code == 404

    # Analyze -> 404
    analyze_res = unauth_client.post(f"/api/v1/meetings/{mid}/analyze", headers=headers_b)
    assert analyze_res.status_code == 404

    # Intelligence/transcript/summary/action-items/chapters -> 404
    assert unauth_client.get(f"/api/v1/meetings/{mid}/intelligence", headers=headers_b).status_code == 404
    assert unauth_client.get(f"/api/v1/meetings/{mid}/transcript", headers=headers_b).status_code == 404
    assert unauth_client.get(f"/api/v1/meetings/{mid}/summary", headers=headers_b).status_code == 404
    assert unauth_client.get(f"/api/v1/meetings/{mid}/action-items", headers=headers_b).status_code == 404
    assert unauth_client.get(f"/api/v1/meetings/{mid}/chapters", headers=headers_b).status_code == 404
