from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.config import Settings, get_settings
from app.main import app
from app.schemas.core import Claim, Review


@pytest.fixture(params=["memory", "sqlite"])
def queue(request, tmp_path):
    settings = Settings(_env_file=None, storage_backend="sql" if request.param == "sqlite" else "memory",
                        database_url=f"sqlite:///{(tmp_path / 'queue.db').as_posix()}")
    app.dependency_overrides[get_settings] = lambda: settings
    repositories = deps._backend(settings)

    def add_review():
        now = datetime.now(UTC)
        claim = repositories.claims.save(Claim(id=uuid4(), employee_id="synthetic-reviewer", status="escalated",
                                              submitted_at=now, currency="IDR", created_at=now, updated_at=now))
        return repositories.reviews.save(Review(id=uuid4(), claim_id=claim.id, status="open", created_at=now))

    reviews = [add_review() for _ in range(3)]
    with TestClient(app) as client:
        yield client, repositories, reviews, add_review


def test_unchanged_queue_can_load_all_pages_with_one_version(queue):
    client, _, _, _ = queue
    first = client.get("/reviews?limit=2").json()
    assert len(first["snapshot"]) == 64
    second = client.get("/reviews", params={"limit": 2, "offset": 2, "snapshot": first["snapshot"]})
    assert second.status_code == 200
    assert second.json()["snapshot"] == first["snapshot"]
    ids = [item["review"]["id"] for item in first["items"] + second.json()["items"]]
    assert len(set(ids)) == first["total"] == 3


@pytest.mark.parametrize("replace", [False, True])
def test_changed_queue_rejects_next_page_even_if_total_is_unchanged(queue, replace):
    client, repositories, reviews, add_review = queue
    first = client.get("/reviews?limit=2").json()
    repositories.reviews.save(reviews[0].model_copy(update={"status": "decided"}))
    if replace:
        add_review()
    second = client.get("/reviews", params={"limit": 2, "offset": 2, "snapshot": first["snapshot"]})
    assert second.status_code == 409
    assert second.json()["code"] == "review_queue_changed"
    refreshed = client.get("/reviews?limit=200").json()
    assert refreshed["snapshot"] != first["snapshot"]
    assert len(refreshed["items"]) == refreshed["total"] == (3 if replace else 2)


def test_page_and_total_use_the_same_queue_read(queue, monkeypatch):
    client, repositories, _, _ = queue

    def separate_count_must_not_be_used():
        pytest.fail("page and total must come from the same queue read")

    monkeypatch.setattr(repositories.reviews, "count_open", separate_count_must_not_be_used)
    response = client.get("/reviews?limit=2")
    assert response.status_code == 200
    assert response.json()["total"] == 3
