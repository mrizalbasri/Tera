from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.auth import require_admin
from app.api.claim_access import get_claim_actor
from app.api.deps import _backend
from app.agent.runtime import graph_resources
from app.config import Settings, get_settings
from app.main import app


def test_demo_refuses_production():
    with pytest.raises(ValidationError, match="demo_mode is not allowed in production"):
        Settings(_env_file=None, environment="production", demo_mode=True)


def test_demo_forces_isolated_storage_and_mock_providers():
    settings = Settings(_env_file=None, demo_mode=True, storage_backend="sql", provider_mode="live", policy_mode="rag", anomaly_mode="ml", graph_checkpoint_path="./real-checkpoints.db")
    assert settings.storage_backend == "memory"
    assert settings.provider_mode == "mock"
    assert settings.policy_mode == "local"
    assert settings.anomaly_mode == "rules"
    assert graph_resources(_backend(settings), settings).connection is None


def test_demo_needs_no_clerk_and_disabled_demo_restores_auth(monkeypatch):
    app.dependency_overrides.pop(require_admin, None)
    app.dependency_overrides.pop(get_claim_actor, None)
    settings = Settings(_env_file=None, demo_mode=True)
    app.dependency_overrides[get_settings] = lambda: settings
    def no_clerk(*args):
        pytest.fail("demo must not contact Clerk")
    monkeypatch.setattr("app.api.auth.verify_session", no_clerk)
    with TestClient(app) as client:
        assert client.get("/auth/session").json() == {"username": "demo-reviewer", "role": "admin", "demo_mode": True}
        for path in ("/reviews", "/reports/summary", "/reports/claims.csv"):
            assert client.get(path).status_code == 200
        settings.demo_mode = False
        assert client.get("/reviews", headers={"x-demo-mode": "true"}).status_code == 401
        assert client.get("/auth/session").status_code == 401


def test_demo_review_records_demo_identity(tmp_path):
    app.dependency_overrides.pop(require_admin, None)
    app.dependency_overrides.pop(get_claim_actor, None)
    settings = Settings(_env_file=None, demo_mode=True)
    settings.graph_checkpoint_path = str(tmp_path / "demo-checkpoints.db")
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        created = client.post("/claims", data={"employee_id": "synthetic-demo", "declared_amount": "700000"}, files={"files": ("receipt.pdf", BytesIO(b"%PDF-1.7\ndemo-review\n%%EOF"), "application/pdf")})
        claim_id = created.json()["claim"]["id"]
        assert client.post(f"/claims/{claim_id}/process").status_code == 200
        decision = client.post(f"/reviews/{claim_id}/decision", json={"action": "approve", "reason": "Synthetic demo evidence checked", "reviewer_reference": "impersonated-user"})
        assert decision.status_code == 200, decision.text
        assert decision.json()["review"]["reviewer_reference"] == "demo-reviewer"
