import time
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt.exceptions import PyJWKClientConnectionError

from app.api.auth import require_admin
from app.api.claim_access import get_claim_actor
from app.config import get_settings
from app.main import app
from app.services import auth

ISSUER = "https://synthetic.clerk.accounts.dev"
USER = "user_synthetic_admin"


@pytest.fixture
def auth_client(monkeypatch):
    app.dependency_overrides.pop(require_admin, None)
    app.dependency_overrides.pop(get_claim_actor, None)
    settings = app.dependency_overrides[get_settings]()
    settings.clerk_issuer = ISSUER
    settings.clerk_admin_user_ids = USER
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(auth, "signing_keys", lambda issuer: SimpleNamespace(
        get_signing_key_from_jwt=lambda token: SimpleNamespace(key=private_key.public_key())
    ))
    def token(**overrides):
        now = int(time.time())
        claims = {"sub": USER, "sid": "sess_synthetic", "iss": ISSUER, "azp": settings.frontend_origin,
                  "iat": now, "nbf": now, "exp": now + 60, "sts": "active"}
        claims.update(overrides)
        return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "synthetic-key"})
    with TestClient(app) as client:
        yield client, settings, token


@pytest.mark.parametrize("path", ["/reviews", "/reports/summary", "/reports/claims.csv", "/auth/session", "/policies", "/notifications"])
def test_admin_endpoints_require_session(auth_client, path):
    client, _, _ = auth_client
    assert client.get(path).status_code == 401
    assert client.post(f"/reviews/{uuid4()}/decision", json={"action": "approve", "reason": "test"}).status_code == 401


def test_verified_admin_cookie_and_bearer_access(auth_client):
    client, _, token = auth_client
    client.cookies.set("__session", token())
    assert client.get("/auth/session").json() == {"username": USER, "role": "admin"}
    assert client.get("/reviews").status_code == 200
    client.cookies.clear()
    for path in ("/reports/summary", "/reports/claims.csv", "/reviews"):
        assert client.get(path, headers={"Authorization": f"Bearer {token()}"}).status_code == 200


def test_signed_in_user_does_not_automatically_become_admin(auth_client):
    client, settings, token = auth_client
    settings.clerk_admin_user_ids = ""
    client.cookies.set("__session", token(public_metadata={"role": "admin"}))
    assert client.get("/auth/session").json()["role"] == "member"
    assert client.get("/reviews").status_code == 403
    assert client.get("/reports/claims.csv").status_code == 403
    assert client.get("/policies").status_code == 403
    assert client.post("/policies/import-baseline").status_code == 403
    assert client.get("/notifications").status_code == 200
    assert client.post(f"/reviews/{uuid4()}/decision", json={"action": "approve", "reason": "test"}).status_code == 403


@pytest.mark.parametrize("claims", [
    {"exp": 1}, {"nbf": 9999999999}, {"iat": 9999999999},
    {"iss": "https://another.clerk.accounts.dev"}, {"azp": "https://evil.example"},
    {"sub": "machine_client"}, {"sid": "m2m_token"}, {"sts": "pending"}, {"sub": 123},
])
def test_invalid_claims_rejected(auth_client, claims):
    client, _, token = auth_client
    assert client.get("/auth/session", headers={"Authorization": f"Bearer {token(**claims)}"}).status_code == 401


def test_forged_signature_missing_claims_and_wrong_algorithm_rejected(auth_client):
    client, _, token = auth_client
    valid = jwt.decode(token(), options={"verify_signature": False})
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    forged = jwt.encode(valid, other_key, algorithm="RS256")
    wrong_algorithm = jwt.encode(valid, "synthetic-test-secret-long-enough-for-hmac", algorithm="HS256")
    for value in (forged, wrong_algorithm, "invalid-token"):
        assert client.get("/auth/session", headers={"Authorization": f"Bearer {value}"}).status_code == 401
    assert client.get("/auth/session", headers={"Authorization": f"Bearer {token(azp=None)}"}).status_code == 401


def test_invalid_authorization_does_not_fall_back_to_valid_cookie(auth_client):
    client, _, token = auth_client
    client.cookies.set("__session", token())
    assert client.get("/auth/session", headers={"Authorization": "Basic abc"}).status_code == 401
    assert client.get("/auth/session", headers={"Authorization": "Bearer "}).status_code == 401


def test_old_local_login_and_cookie_are_not_accepted(auth_client):
    client, _, _ = auth_client
    client.cookies.set("tera_admin_session", "legacy-local-session")
    assert client.get("/reviews").status_code == 401
    assert client.post("/auth/login", json={"username": "admin", "password": "old"}).status_code == 404


def test_unconfigured_auth_fails_closed(auth_client):
    client, settings, token = auth_client
    settings.clerk_issuer = ""
    assert client.get("/reviews", headers={"Authorization": f"Bearer {token()}"}).status_code == 503


def test_jwks_outage_is_retryable(auth_client, monkeypatch):
    client, _, token = auth_client
    def unavailable(issuer):
        raise PyJWKClientConnectionError("synthetic outage")
    monkeypatch.setattr(auth, "signing_keys", unavailable)
    assert client.get("/auth/session", headers={"Authorization": f"Bearer {token()}"}).status_code == 503


def test_cross_origin_decision_rejected(auth_client):
    client, _, token = auth_client
    response = client.post(f"/reviews/{uuid4()}/decision", json={"action": "approve", "reason": "test"}, headers={"Authorization": f"Bearer {token()}", "Origin": "https://evil.example"})
    assert response.status_code == 403


def test_review_uses_verified_clerk_identity(auth_client):
    client, _, token = auth_client
    client.cookies.set("__session", token())
    response = client.post("/claims", data={"employee_id": "synthetic", "declared_amount": "700000"}, files={"files": ("receipt.pdf", BytesIO(b"%PDF-1.7\nauth-review\n%%EOF"), "application/pdf")})
    claim_id = response.json()["claim"]["id"]
    assert client.post(f"/claims/{claim_id}/process").status_code == 200
    response = client.post(f"/reviews/{claim_id}/decision", json={"action": "approve", "reason": "Synthetic evidence checked", "reviewer_reference": "impersonated-user"})
    assert response.status_code == 200, response.text
    assert response.json()["review"]["reviewer_reference"] == USER
