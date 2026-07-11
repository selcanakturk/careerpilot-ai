import os
from types import SimpleNamespace
from uuid import uuid4

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")

from fastapi.testclient import TestClient

from app.core.security import CurrentUser, get_current_user
from app.core.supabase import get_supabase_client
from app.main import app


class FakeSingleQuery:
    def __init__(self, data: dict[str, object] | None) -> None:
        self._data = data

    def execute(self) -> SimpleNamespace:
        return SimpleNamespace(data=self._data)


class FakeQuery:
    def __init__(self, data: dict[str, object] | None) -> None:
        self._data = data
        self.filters: list[tuple[str, str]] = []

    def select(self, _columns: str) -> "FakeQuery":
        return self

    def eq(self, column: str, value: str) -> "FakeQuery":
        self.filters.append((column, value))
        return self

    def maybe_single(self) -> FakeSingleQuery:
        return FakeSingleQuery(self._data)


class FakeSupabaseClient:
    def __init__(self, data: dict[str, object] | None) -> None:
        self.query = FakeQuery(data)

    def table(self, table_name: str) -> FakeQuery:
        assert table_name == "cv_uploads"
        return self.query


def override_current_user() -> CurrentUser:
    return CurrentUser(id="11111111-1111-1111-1111-111111111111", email="owner@example.com")


def make_upload_record(upload_id: str) -> dict[str, object]:
    return {
        "id": upload_id,
        "user_id": "11111111-1111-1111-1111-111111111111",
        "file_name": "selcan-cv.pdf",
        "file_path": "11111111-1111-1111-1111-111111111111/20260711-120000-selcan-cv.pdf",
        "file_type": "PDF",
        "file_size": 245760,
        "target_role": "Product Manager",
        "experience_level": "mid",
        "created_at": "2026-07-11T12:00:00Z",
    }


def test_get_upload_authenticated_owner_returns_200() -> None:
    upload_id = str(uuid4())
    fake_client = FakeSupabaseClient(make_upload_record(upload_id))
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_supabase_client] = lambda: fake_client

    try:
        response = TestClient(app).get(f"/api/uploads/{upload_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["id"] == upload_id
    assert response.json()["target_role"] == "Product Manager"
    assert ("id", upload_id) in fake_client.query.filters
    assert ("user_id", "11111111-1111-1111-1111-111111111111") in fake_client.query.filters


def test_get_upload_not_found_returns_404() -> None:
    upload_id = str(uuid4())
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_supabase_client] = lambda: FakeSupabaseClient(None)

    try:
        response = TestClient(app).get(f"/api/uploads/{upload_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "CV upload not found."


def test_get_upload_without_auth_returns_401() -> None:
    upload_id = str(uuid4())
    app.dependency_overrides[get_supabase_client] = lambda: FakeSupabaseClient(None)

    try:
        response = TestClient(app).get(f"/api/uploads/{upload_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
