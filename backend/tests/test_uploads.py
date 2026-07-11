import os
from types import SimpleNamespace
from uuid import uuid4

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")

from fastapi.testclient import TestClient

from app.core.security import CurrentUser, get_current_user
from app.core.supabase import get_supabase_client
from app.main import app
from app.services import storage_service


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


class FakeStorageBucket:
    def __init__(self, content: bytes | None) -> None:
        self._content = content
        self.downloaded_path = ""

    def download(self, file_path: str) -> bytes:
        self.downloaded_path = file_path

        if self._content is None:
            raise Exception("404 not found")

        return self._content


class FakeStorage:
    def __init__(self, content: bytes | None) -> None:
        self.bucket = FakeStorageBucket(content)
        self.bucket_name = ""

    def from_(self, bucket_name: str) -> FakeStorageBucket:
        self.bucket_name = bucket_name
        return self.bucket


class FakeStorageClient:
    def __init__(self, content: bytes | None) -> None:
        self.storage = FakeStorage(content)


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


def test_download_upload_authenticated_owner_returns_200(monkeypatch) -> None:
    upload_id = str(uuid4())
    fake_db_client = FakeSupabaseClient(make_upload_record(upload_id))
    fake_storage_client = FakeStorageClient(b"%PDF-1.4 test content")
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_supabase_client] = lambda: fake_db_client
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: fake_storage_client)

    try:
        response = TestClient(app).get(f"/api/uploads/{upload_id}/download")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "file_name": "selcan-cv.pdf",
        "size": len(b"%PDF-1.4 test content"),
        "content_type": "application/pdf",
        "message": "CV downloaded successfully.",
    }
    assert fake_storage_client.storage.bucket_name == "cv-files"
    assert (
        fake_storage_client.storage.bucket.downloaded_path
        == "11111111-1111-1111-1111-111111111111/20260711-120000-selcan-cv.pdf"
    )


def test_download_upload_not_found_returns_404(monkeypatch) -> None:
    upload_id = str(uuid4())
    fake_storage_client = FakeStorageClient(b"unused")
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_supabase_client] = lambda: FakeSupabaseClient(None)
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: fake_storage_client)

    try:
        response = TestClient(app).get(f"/api/uploads/{upload_id}/download")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "CV upload not found."
    assert fake_storage_client.storage.bucket.downloaded_path == ""


def test_download_upload_missing_storage_file_returns_404(monkeypatch) -> None:
    upload_id = str(uuid4())
    fake_db_client = FakeSupabaseClient(make_upload_record(upload_id))
    fake_storage_client = FakeStorageClient(None)
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_supabase_client] = lambda: fake_db_client
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: fake_storage_client)

    try:
        response = TestClient(app).get(f"/api/uploads/{upload_id}/download")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "CV file not found."


def test_download_upload_without_auth_returns_401(monkeypatch) -> None:
    upload_id = str(uuid4())
    fake_storage_client = FakeStorageClient(b"unused")
    app.dependency_overrides[get_supabase_client] = lambda: FakeSupabaseClient(make_upload_record(upload_id))
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: fake_storage_client)

    try:
        response = TestClient(app).get(f"/api/uploads/{upload_id}/download")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert fake_storage_client.storage.bucket.downloaded_path == ""
