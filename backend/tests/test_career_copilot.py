import os
from uuid import uuid4

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-api-key")
os.environ.setdefault("GEMINI_MODEL", "gemini-2.5-flash")

from fastapi.testclient import TestClient

from app.core.security import CurrentUser, get_current_user
from app.main import app
from app.services import career_copilot_service


OWNER_ID = "11111111-1111-1111-1111-111111111111"


def override_current_user() -> CurrentUser:
    return CurrentUser(id=OWNER_ID, email="owner@example.com")


def test_career_copilot_success(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def ask_career_copilot(**kwargs: object) -> str:
        captured.update(kwargs)
        return "Prioritize Python API projects, then prepare deployment examples."

    monkeypatch.setattr(career_copilot_service, "ask_career_copilot", ask_career_copilot)
    app.dependency_overrides[get_current_user] = override_current_user
    analysis_id = str(uuid4())

    try:
        response = TestClient(app).post(
            "/api/career-copilot/chat",
            json={
                "analysis_id": analysis_id,
                "message": "What should I learn next?",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured == {
        "user_id": OWNER_ID,
        "analysis_id": analysis_id,
        "message": "What should I learn next?",
    }
    assert response.json() == {
        "reply": "Prioritize Python API projects, then prepare deployment examples."
    }


def test_career_copilot_analysis_not_found_returns_404(monkeypatch) -> None:
    monkeypatch.setattr(
        career_copilot_service,
        "ask_career_copilot",
        lambda **_kwargs: (_ for _ in ()).throw(
            career_copilot_service.CareerCopilotAnalysisNotFoundError("missing")
        ),
    )
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).post(
            "/api/career-copilot/chat",
            json={"analysis_id": str(uuid4()), "message": "Help me focus."},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "CV analysis not found."


def test_career_copilot_other_user_analysis_returns_404(monkeypatch) -> None:
    monkeypatch.setattr(
        career_copilot_service,
        "ask_career_copilot",
        lambda **_kwargs: (_ for _ in ()).throw(
            career_copilot_service.CareerCopilotAnalysisNotFoundError("missing")
        ),
    )
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).post(
            "/api/career-copilot/chat",
            json={"analysis_id": str(uuid4()), "message": "Can I apply to this role?"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_career_copilot_empty_message_returns_422() -> None:
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).post(
            "/api/career-copilot/chat",
            json={"analysis_id": str(uuid4()), "message": "   "},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_career_copilot_gemini_error_returns_503(monkeypatch) -> None:
    monkeypatch.setattr(
        career_copilot_service,
        "ask_career_copilot",
        lambda **_kwargs: (_ for _ in ()).throw(
            career_copilot_service.CareerCopilotAIError("provider failed")
        ),
    )
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).post(
            "/api/career-copilot/chat",
            json={"analysis_id": str(uuid4()), "message": "What should I improve?"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"] == "Career Copilot is temporarily unavailable. Please try again shortly."
