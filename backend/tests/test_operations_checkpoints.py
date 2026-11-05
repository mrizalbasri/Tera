from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from app.api.auth import require_admin
from app.config import Settings, get_settings
from app.main import app
from app.services.auth import create_session_token


@pytest.fixture
def test_env():
    settings = Settings(
        _env_file=None,
        storage_backend="memory",
        provider_mode="mock",
        secret_key="a" * 32,
        admin_users="admin_tester",
        demo_mode=False,
    )
    # Pop require_admin so real auth runs
    app.dependency_overrides.pop(require_admin, None)
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as client:
        yield client, settings
    app.dependency_overrides.pop(get_settings, None)


def auth_headers(settings, username="admin_tester", role="admin"):
    token = create_session_token(username, role, settings)
    return {"Authorization": f"Bearer {token}"}


def test_checkpoints_require_admin(test_env):
    client, settings = test_env
    # Unauthenticated
    assert client.get("/operations/checkpoints").status_code in (401, 403)
    # Non-admin
    user_token = create_session_token("normal_user", "member", settings)
    assert client.get("/operations/checkpoints", headers={"Authorization": f"Bearer {user_token}"}).status_code == 403


def test_list_and_inspect_checkpoints(test_env):
    client, settings = test_env
    headers = auth_headers(settings)

    # Create and process a claim that escalates to wait_review
    create_res = client.post(
        "/claims",
        data={"employee_id": "test_emp@example.test", "declared_amount": "700000"},
        files={"files": ("receipt.pdf", BytesIO(b"%PDF-1.7\nhotel-review\n%%EOF"), "application/pdf")},
    )
    assert create_res.status_code == 201
    claim_id = create_res.json()["claim"]["id"]

    process_res = client.post(f"/claims/{claim_id}/process")
    assert process_res.status_code == 200
    assert process_res.json()["claim"]["status"] == "escalated"

    # List checkpoints
    list_res = client.get("/operations/checkpoints", headers=headers)
    assert list_res.status_code == 200
    items = list_res.json()
    assert any(item["claim_id"] == claim_id for item in items)
    target_item = next(item for item in items if item["claim_id"] == claim_id)
    assert target_item["stage"] == "wait_review"
    assert "wait_review" in target_item["next_nodes"]

    # Filter by stage
    filter_res = client.get("/operations/checkpoints?stage=wait_review", headers=headers)
    assert filter_res.status_code == 200
    assert all(item["stage"] == "wait_review" for item in filter_res.json())

    # Inspect checkpoint detail
    detail_res = client.get(f"/operations/checkpoints/{claim_id}", headers=headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["claim_id"] == claim_id
    assert detail["stage"] == "wait_review"
    assert "wait_review" in detail["next_nodes"]
    assert detail["values"]["stage"] == "wait_review"
    assert len(detail["history"]) >= 1

    # Resume checkpoint on waiting review (noop because review input is needed from reviewer)
    resume_res = client.post(f"/operations/checkpoints/{claim_id}/resume", headers=headers)
    assert resume_res.status_code == 200
    assert resume_res.json()["status"] in ("resumed", "noop")
