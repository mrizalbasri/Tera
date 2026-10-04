import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.config import Settings, get_settings
from app.main import app


@pytest.fixture(autouse=True)
def isolated_stores():
    """Give every test a fresh in-memory backend so tests stay order-independent."""
    deps._repositories.cache_clear()
    deps._file_storage.cache_clear()
    yield
    deps._repositories.cache_clear()
    deps._file_storage.cache_clear()


@pytest.fixture
def limited_size_client() -> TestClient:
    """Client whose receipt size limit is small enough to test cheaply."""
    settings = Settings(_env_file=None, max_receipt_size_bytes=64)
    app.dependency_overrides[get_settings] = lambda: settings
    yield TestClient(app)
    app.dependency_overrides.pop(get_settings, None)
