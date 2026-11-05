import time
from io import BytesIO
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from app.api.auth import require_admin
from app.api.claim_access import get_claim_actor
from app.config import get_settings
from app.main import app

USER = "admin_user"
ADMIN_USER = USER
MEMBER_USER = "member_user"
SECRET = "test-secret-key-for-unit-testing-32-chars-minimum"


@pytest.fixture
def auth_client():
    app.dependency_overrides.pop(require_admin, None)
    app.dependency_overrides.pop(get_claim_actor, None)
    settings = app.dependency_overrides[get_settings]()
    settings.secret_key = SECRET
    settings.admin_users = ADMIN_USER
    settings.demo_mode = False

    def token(user=ADMIN_USER, role="admin", **overrides):
        now = int(time.time())
        claims = {"sub": user, "role": role, "iat": now, "exp": now + 60}
        claims.update(overrides)
        return jwt.encode(claims, settings.secret_key, algorithm="HS256")

    with TestClient(app) as client:
        yield client, settings, token


@pytest.mark.parametrize("path", ["/reviews", "/reports/summary", "/reports/claims.csv", "/auth/session", "/policies", "/notifications"])
def test_admin_endpoints_require_session(auth_client, path):
    client, _, _ = auth_client
    assert client.get(path).status_code == 401
    assert client.post(f"/reviews/{uuid4()}/decision", json={"action": "approve", "reason": "test"}).status_code == 401


def test_login_and_logout_flow(auth_client):
    client, _, _ = auth_client
    response = client.post("/auth/login", json={"username": ADMIN_USER, "password": "any", "role": "admin"})
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == ADMIN_USER
    assert data["role"] == "admin"
    assert "token" in data

    # Verify session via cookie set by login
    session_res = client.get("/auth/session")
    assert session_res.status_code == 200
    assert session_res.json() == {"username": ADMIN_USER, "role": "admin"}

    # Logout clears session
    logout_res = client.post("/auth/logout")
    assert logout_res.status_code == 200
    assert client.get("/auth/session").status_code == 401


def test_verified_admin_cookie_and_bearer_access(auth_client):
    client, _, token = auth_client
    client.cookies.set("__session", token())
    assert client.get("/auth/session").json() == {"username": ADMIN_USER, "role": "admin"}
    assert client.get("/reviews").status_code == 200
    client.cookies.clear()
    for path in ("/reports/summary", "/reports/claims.csv", "/reviews"):
        assert client.get(path, headers={"Authorization": f"Bearer {token()}"}).status_code == 200


def test_signed_in_member_does_not_automatically_become_admin(auth_client):
    client, _, token = auth_client
    client.cookies.set("__session", token(user=MEMBER_USER, role="member"))
    assert client.get("/auth/session").json()["role"] == "member"
    assert client.get("/reviews").status_code == 403
    assert client.get("/reports/claims.csv").status_code == 403
    assert client.get("/policies").status_code == 403
    assert client.post("/policies/import-baseline").status_code == 403
    assert client.get("/notifications").status_code == 200
    assert client.post(f"/reviews/{uuid4()}/decision", json={"action": "approve", "reason": "test"}).status_code == 403


@pytest.mark.parametrize("claims", [
    {"exp": 1}, {"iat": 9999999999}, {"sub": ""}, {"sub": "   "},
])
def test_invalid_claims_rejected(auth_client, claims):
    client, _, token = auth_client
    assert client.get("/auth/session", headers={"Authorization": f"Bearer {token(**claims)}"}).status_code == 401


def test_forged_signature_and_wrong_key_rejected(auth_client):
    client, _, token = auth_client
    valid = jwt.decode(token(), options={"verify_signature": False})
    forged = jwt.encode(valid, "different-secret-key-1234567890-minimum-32-chars", algorithm="HS256")
    for value in (forged, "invalid-token", ""):
        assert client.get("/auth/session", headers={"Authorization": f"Bearer {value}"}).status_code == 401


def test_invalid_authorization_does_not_fall_back_to_valid_cookie(auth_client):
    client, _, token = auth_client
    client.cookies.set("__session", token())
    assert client.get("/auth/session", headers={"Authorization": "Basic abc"}).status_code == 401
    assert client.get("/auth/session", headers={"Authorization": "Bearer "}).status_code == 401


def test_unconfigured_auth_fails_closed(auth_client):
    client, settings, token = auth_client
    sample_token = token()
    settings.secret_key = ""
    assert client.get("/reviews", headers={"Authorization": f"Bearer {sample_token}"}).status_code == 503


def test_cross_origin_decision_rejected(auth_client):
    client, _, token = auth_client
    response = client.post(f"/reviews/{uuid4()}/decision", json={"action": "approve", "reason": "test"}, headers={"Authorization": f"Bearer {token()}", "Origin": "https://evil.example"})
    assert response.status_code == 403


def test_review_uses_verified_identity(auth_client):
    client, _, token = auth_client
    client.cookies.set("__session", token())
    response = client.post("/claims", data={"employee_id": "synthetic", "declared_amount": "700000"}, files={"files": ("receipt.pdf", BytesIO(b"%PDF-1.7\nauth-review\n%%EOF"), "application/pdf")})
    claim_id = response.json()["claim"]["id"]
    assert client.post(f"/claims/{claim_id}/process").status_code == 200
    response = client.post(f"/reviews/{claim_id}/decision", json={"action": "approve", "reason": "Synthetic evidence checked", "reviewer_reference": "impersonated-user"})
    assert response.status_code == 200, response.text
    assert response.json()["review"]["reviewer_reference"] == ADMIN_USER


def test_login_invalid_password_rejected(auth_client):
    client, _, _ = auth_client
    res = client.post("/auth/login", json={"username": ADMIN_USER, "password": "wrongpassword"})
    assert res.status_code == 401
    assert res.json()["code"] == "invalid_credentials"

    res_empty = client.post("/auth/login", json={"username": ADMIN_USER, "password": ""})
    assert res_empty.status_code == 401


def test_login_cannot_self_assign_admin(auth_client):
    client, _, _ = auth_client
    # Non-admin user attempts to claim role=admin
    res = client.post("/auth/login", json={"username": MEMBER_USER, "password": "demo123", "role": "admin"})
    assert res.status_code == 200
    assert res.json()["role"] == "member"


def test_prefix_username_not_admin(auth_client):
    client, settings, _ = auth_client
    settings.admin_users = "admin,reviewer,finance"
    # User starting with 'admin' or 'finance' prefix but not exact match
    res = client.post("/auth/login", json={"username": "administrator_imposter", "password": "demo123"})
    assert res.status_code == 200
    assert res.json()["role"] == "member"


def test_login_production_credentials_check(auth_client):
    client, settings, _ = auth_client
    settings.environment = "production"
    # Valid demo credentials in production
    res = client.post("/auth/login", json={"username": "admin", "password": "demo123"})
    assert res.status_code == 200
    assert res.json()["username"] == "admin"

    # Invalid password in production
    res_bad = client.post("/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert res_bad.status_code == 401
    assert res_bad.json()["code"] == "invalid_credentials"

    # Unknown user in production
    res_unknown = client.post("/auth/login", json={"username": "unknown_user", "password": "demo123"})
    assert res_unknown.status_code == 401
    assert res_unknown.json()["code"] == "invalid_credentials"

