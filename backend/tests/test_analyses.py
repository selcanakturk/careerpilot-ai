import os
from uuid import uuid4

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-api-key")
os.environ.setdefault("OPENAI_MODEL", "gpt-5-mini")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-api-key")
os.environ.setdefault("GEMINI_MODEL", "gemini-2.5-flash")

from fastapi.testclient import TestClient

from app.core.security import CurrentUser, get_current_user
from app.main import app
from app.services import analysis_service
from app.services import storage_service


OWNER_ID = "11111111-1111-1111-1111-111111111111"


def override_current_user() -> CurrentUser:
    return CurrentUser(id=OWNER_ID, email="owner@example.com")


def test_delete_analysis_authenticated_owner_returns_200(monkeypatch) -> None:
    analysis_id = str(uuid4())
    upload_id = str(uuid4())
    calls: dict[str, object] = {}

    def delete_analysis(analysis_id: str, user_id: str) -> dict[str, object]:
        calls["analysis_id"] = analysis_id
        calls["user_id"] = user_id
        return {"id": analysis_id, "cv_upload_id": upload_id}

    def fail_if_storage_called(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Storage should not be touched when deleting an analysis.")

    monkeypatch.setattr(analysis_service, "delete_analysis", delete_analysis)
    monkeypatch.setattr(storage_service, "download_cv", fail_if_storage_called)
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).delete(f"/api/analyses/{analysis_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "id": analysis_id,
        "cv_upload_id": upload_id,
        "message": "Analysis deleted successfully.",
    }
    assert calls == {"analysis_id": analysis_id, "user_id": OWNER_ID}


def test_delete_analysis_not_found_returns_404(monkeypatch) -> None:
    analysis_id = str(uuid4())
    monkeypatch.setattr(analysis_service, "delete_analysis", lambda **_kwargs: None)
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).delete(f"/api/analyses/{analysis_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Analysis not found."


def test_delete_analysis_other_user_record_returns_404(monkeypatch) -> None:
    analysis_id = str(uuid4())

    def delete_analysis(analysis_id: str, user_id: str) -> None:
        assert user_id == OWNER_ID
        return None

    monkeypatch.setattr(analysis_service, "delete_analysis", delete_analysis)
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).delete(f"/api/analyses/{analysis_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Analysis not found."


def test_delete_analysis_without_auth_returns_401(monkeypatch) -> None:
    analysis_id = str(uuid4())

    def fail_if_called(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Delete service should not be called without authentication.")

    monkeypatch.setattr(analysis_service, "delete_analysis", fail_if_called)

    try:
        response = TestClient(app).delete(f"/api/analyses/{analysis_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401


def test_delete_analysis_supabase_error_returns_safe_500(monkeypatch) -> None:
    analysis_id = str(uuid4())

    def raise_database_error(**_kwargs: object) -> None:
        raise RuntimeError("raw Supabase delete failure")

    monkeypatch.setattr(analysis_service, "delete_analysis", raise_database_error)
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).delete(f"/api/analyses/{analysis_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json()["detail"] == "Unable to delete analysis."
