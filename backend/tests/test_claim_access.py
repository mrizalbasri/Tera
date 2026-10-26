from uuid import UUID, uuid4

from app.api import deps
from app.config import get_settings
from app.main import app

import pytest

from test_auth import USER, auth_client as auth_client


@pytest.fixture(params=["memory", "sql"])
def claims_client(auth_client, request, tmp_path):
    client, settings, token = auth_client
    settings.storage_backend = request.param
    settings.database_url = f"sqlite:///{tmp_path / 'ownership.db'}"
    return client, token


def headers(token, user):
    return {"Authorization": f"Bearer {token(sub=user)}"}


def create(client, token, user, marker="first", key=None, amount="60000"):
    auth_headers = headers(token, user)
    if key:
        auth_headers["Idempotency-Key"] = key
    return client.post(
        "/claims", headers=auth_headers,
        data={"employee_id": "impersonated-employee", "declared_amount": amount},
        files={"files": ("receipt.pdf", f"%PDF-1.7\n{marker}\n%%EOF".encode(), "application/pdf")},
    )


def test_creation_and_listing_use_verified_identity(claims_client):
    client, token = claims_client
    first = create(client, token, "user_alice").json()["claim"]
    second = create(client, token, "user_bob", "second").json()["claim"]
    assert first["employee_id"] == "user_alice"
    assert second["employee_id"] == "user_bob"
    for query in ("", "?employee_id=user_bob", "?employee_id=impersonated-employee"):
        result = client.get(f"/claims{query}", headers=headers(token, "user_alice")).json()
        assert [item["id"] for item in result["items"]] == [first["id"]]
    assert client.get("/claims", headers=headers(token, USER)).json()["total"] == 2
    assert client.get("/claims?employee_id=user_bob", headers=headers(token, USER)).json()["total"] == 1


def test_every_claim_operation_requires_session(claims_client):
    client, _ = claims_client
    claim_id = uuid4()
    for path in ("/claims", f"/claims/{claim_id}", f"/claims/{claim_id}/timeline", f"/claims/{claim_id}/clarifications"):
        assert client.get(path).status_code == 401
    assert client.post("/claims", files={"files": ("a.pdf", b"%PDF-1.7", "application/pdf")}).status_code == 401
    assert client.post(f"/claims/{claim_id}/process").status_code == 401
    assert client.post(f"/claims/{claim_id}/receipts", files={"file": ("a.pdf", b"%PDF-1.7", "application/pdf")}).status_code == 401
    assert client.post(f"/claims/{claim_id}/clarifications/{uuid4()}/answer", json={"answer": "4"}).status_code == 401


def test_foreign_claim_reads_and_mutations_are_hidden(claims_client):
    client, token = claims_client
    claim_id = create(client, token, "user_alice").json()["claim"]["id"]
    bob = headers(token, "user_bob")
    for suffix in ("", "/timeline", "/clarifications"):
        assert client.get(f"/claims/{claim_id}{suffix}", headers=bob).status_code == 404
        assert client.get(f"/claims/{claim_id}{suffix}", headers=headers(token, "user_alice")).status_code == 200
        assert client.get(f"/claims/{claim_id}{suffix}", headers=headers(token, USER)).status_code == 200
    assert client.post(f"/claims/{claim_id}/process", headers=bob).status_code == 404
    assert client.post(f"/claims/{claim_id}/receipts", headers=bob, files={"file": ("replacement.pdf", b"%PDF-1.7\nnew", "application/pdf")}).status_code == 404
    assert client.post(f"/claims/{claim_id}/clarifications/{uuid4()}/answer", headers=bob, json={"answer": "4"}).status_code == 404
    detail = client.get(f"/claims/{claim_id}", headers=headers(token, "user_alice")).json()
    assert detail["claim"]["status"] == "received"
    assert len(detail["receipts"]) == 1
    assert detail["attempts"] == []
    assert client.post(f"/claims/{claim_id}/process", headers=headers(token, USER)).status_code == 200


def test_idempotency_cannot_replay_another_users_claim(claims_client):
    client, token = claims_client
    first = create(client, token, "user_alice", key="shared-key").json()
    second = create(client, token, "user_bob", "second", key="shared-key").json()
    replay = create(client, token, "user_alice", key="shared-key").json()
    assert first["claim"]["id"] != second["claim"]["id"]
    assert second["claim"]["employee_id"] == "user_bob"
    assert replay["claim"]["id"] == first["claim"]["id"]
    assert replay["idempotent_replay"] is True


def test_duplicate_receipt_does_not_disclose_foreign_claim(claims_client):
    client, token = claims_client
    claim_id = create(client, token, "user_alice").json()["claim"]["id"]
    response = create(client, token, "user_bob")
    assert response.status_code == 409
    assert claim_id not in response.text


def test_answer_records_signed_in_identity(claims_client):
    client, token = claims_client
    claim_id = create(client, token, "user_alice", "CATEGORY:MEALS shared", amount="240000").json()["claim"]["id"]
    alice = headers(token, "user_alice")
    response = client.post(f"/claims/{claim_id}/process", headers=alice)
    assert response.status_code == 200, response.text
    questions = client.get(f"/claims/{claim_id}/clarifications", headers=alice).json()["items"]
    assert questions
    response = client.post(f"/claims/{claim_id}/clarifications/{questions[-1]['id']}/answer", headers=alice,
                           json={"answer": "4", "answered_by": "user_bob"})
    assert response.status_code == 200, response.text
    answered = client.get(f"/claims/{claim_id}/clarifications", headers=alice).json()["items"][-1]
    assert answered["status"] == "answered"
    settings = app.dependency_overrides[get_settings]()
    entries = deps._backend(settings).context.list_for_claim(UUID(claim_id))
    assert [entry.content for entry in entries if entry.role == "employee"] == ["user_alice: 4"]


def test_cross_origin_claim_mutation_is_rejected(claims_client):
    client, token = claims_client
    response = client.post("/claims", headers={**headers(token, "user_alice"), "Origin": "https://evil.example"},
                           files={"files": ("receipt.pdf", b"%PDF-1.7", "application/pdf")})
    assert response.status_code == 403


def test_duplicate_evidence_is_only_visible_to_admin(claims_client):
    client, token = claims_client
    first_id = create(client, token, "user_alice", "ordinary-a").json()["claim"]["id"]
    assert client.post(f"/claims/{first_id}/process", headers=headers(token, "user_alice")).status_code == 200
    second_id = create(client, token, "user_bob", "ordinary-b").json()["claim"]["id"]
    bob = headers(token, "user_bob")
    processed = client.post(f"/claims/{second_id}/process", headers=bob)
    assert processed.status_code == 200
    assert first_id not in processed.text
    detail = client.get(f"/claims/{second_id}", headers=bob)
    assert first_id not in detail.text
    assert any(signal["signal_type"] == "duplicate" for signal in detail.json()["signals"])
    assert first_id not in client.get(f"/claims/{second_id}/timeline", headers=bob).text
    assert first_id in client.get(f"/claims/{second_id}", headers=headers(token, USER)).text
