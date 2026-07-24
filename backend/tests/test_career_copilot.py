import os
from types import SimpleNamespace
from uuid import uuid4

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-api-key")
os.environ.setdefault("GEMINI_MODEL", "gemini-2.5-flash")

from fastapi.testclient import TestClient

from app.core.security import CurrentUser, get_current_user
from app.main import app
from app.schemas.cv_optimizer import CVOptimizerResult
from app.services import career_copilot_service


OWNER_ID = "11111111-1111-1111-1111-111111111111"
ANALYSIS_ID = "22222222-2222-2222-2222-222222222222"


def override_current_user() -> CurrentUser:
    return CurrentUser(id=OWNER_ID, email="owner@example.com")


def make_analysis() -> dict[str, object]:
    return {
        "id": ANALYSIS_ID,
        "user_id": OWNER_ID,
        "cv_upload_id": "33333333-3333-3333-3333-333333333333",
        "target_role": "Backend Software Engineer",
        "primary_role": "Backend Developer",
        "status": "completed",
        "overall_score": 82,
        "summary": "Strong backend foundation with deployment gaps.",
        "strengths": ["Python", "FastAPI"],
        "weaknesses": ["Cloud deployment"],
        "skill_gaps": ["Docker", "AWS"],
        "top_skills": ["Python", "REST API"],
        "cv_suggestions": ["Quantify backend project impact"],
    }


def capture_copilot_prompt(monkeypatch, analysis: dict[str, object] | None = None) -> dict[str, str]:
    captured: dict[str, str] = {}

    monkeypatch.setattr(
        career_copilot_service,
        "_get_completed_analysis",
        lambda **_kwargs: analysis or make_analysis(),
    )
    monkeypatch.setattr(career_copilot_service, "_get_model_sequence", lambda _primary: ["test-model"])

    def generate_reply_with_retry(**kwargs: object) -> str:
        captured["prompt"] = str(kwargs["prompt"])
        return "Focus on Docker deployment practice next."

    monkeypatch.setattr(career_copilot_service, "_generate_reply_with_retry", generate_reply_with_retry)
    return captured


def test_career_copilot_success(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def chat_with_career_copilot(**kwargs: object):
        captured.update(kwargs)
        return career_copilot_service.CareerCopilotResponse(
            reply="Prioritize Python API projects, then prepare deployment examples.",
            suggested_action=career_copilot_service.suggest_action_for_message(str(kwargs["message"])),
            tool_result=None,
        )

    monkeypatch.setattr(career_copilot_service, "chat_with_career_copilot", chat_with_career_copilot)
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
        "job_external_id": None,
        "provider": None,
    }
    assert response.json() == {
        "reply": "Prioritize Python API projects, then prepare deployment examples.",
        "suggested_action": {
            "type": "open_roadmap",
            "label": "Open Roadmap",
            "target": "/dashboard",
        },
        "tool_result": None,
    }


def test_career_copilot_analysis_not_found_returns_404(monkeypatch) -> None:
    monkeypatch.setattr(
        career_copilot_service,
        "chat_with_career_copilot",
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
        "chat_with_career_copilot",
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
        "chat_with_career_copilot",
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


def test_career_copilot_cv_intent_with_job_context_runs_optimizer(monkeypatch) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(career_copilot_service, "_get_completed_analysis", lambda **_kwargs: make_analysis())

    def optimize_cv_for_job(**kwargs: object) -> CVOptimizerResult:
        calls.append(kwargs)
        return CVOptimizerResult(
            match_before=45,
            estimated_match_after=70,
            changes=["Highlighted Python APIs", "Reordered backend skills"],
            optimized_cv={
                "headline": "Backend Developer",
                "summary": "Python backend profile.",
                "experience": [],
                "projects": [],
                "skills": ["Python"],
                "education": [],
                "certifications": [],
                "additional_sections": {},
            },
        )

    monkeypatch.setattr(career_copilot_service.cv_optimizer_service, "optimize_cv_for_job", optimize_cv_for_job)

    response = career_copilot_service.chat_with_career_copilot(
        user_id=OWNER_ID,
        analysis_id=ANALYSIS_ID,
        message="Please optimize my CV for this job.",
        job_external_id="job-1",
        provider="jooble",
    )

    assert len(calls) == 1
    assert calls[0] == {
        "user_id": OWNER_ID,
        "analysis_id": ANALYSIS_ID,
        "job_external_id": "job-1",
        "provider": "jooble",
    }
    assert response.tool_result is not None
    assert response.tool_result.status == "completed"
    assert response.tool_result.data is not None
    assert response.tool_result.data["current_match"] == 45
    assert response.tool_result.data["estimated_match"] == 70
    assert response.tool_result.data["major_changes"] == [
        "Highlighted Python APIs",
        "Reordered backend skills",
    ]
    assert response.tool_result.data["before_professional_summary"] == "Strong backend foundation with deployment gaps."
    assert response.tool_result.data["optimized_professional_summary"] == "Python backend profile."
    assert response.tool_result.data["optimization_summary"] == "Python backend profile."
    assert response.tool_result.data["optimized_skills"] == ["Python"]
    assert response.tool_result.data["explanation"] == ""
    assert response.suggested_action is not None
    assert response.suggested_action.type == "open_cv_optimizer"


def test_career_copilot_cv_intent_without_job_context_requires_input(monkeypatch) -> None:
    monkeypatch.setattr(career_copilot_service, "_get_completed_analysis", lambda **_kwargs: make_analysis())

    response = career_copilot_service.chat_with_career_copilot(
        user_id=OWNER_ID,
        analysis_id=ANALYSIS_ID,
        message="How can I improve my CV?",
    )

    assert response.tool_result is not None
    assert response.tool_result.type == "cv_optimization"
    assert response.tool_result.status == "requires_input"
    assert response.tool_result.data is None
    assert response.suggested_action is not None
    assert response.suggested_action.type == "open_jobs"
    assert response.suggested_action.label == "Choose a Job"


def test_career_copilot_non_cv_intent_has_no_tool_result(monkeypatch) -> None:
    monkeypatch.setattr(career_copilot_service, "_get_completed_analysis", lambda **_kwargs: make_analysis())
    monkeypatch.setattr(career_copilot_service, "ask_career_copilot", lambda **_kwargs: "Study Docker next.")

    response = career_copilot_service.chat_with_career_copilot(
        user_id=OWNER_ID,
        analysis_id=ANALYSIS_ID,
        message="What should I learn next?",
    )

    assert response.reply == "Study Docker next."
    assert response.tool_result is None
    assert response.suggested_action is not None
    assert response.suggested_action.type == "open_roadmap"


def test_career_copilot_optimizer_failure_returns_failed_tool_result(monkeypatch) -> None:
    monkeypatch.setattr(career_copilot_service, "_get_completed_analysis", lambda **_kwargs: make_analysis())
    monkeypatch.setattr(
        career_copilot_service.cv_optimizer_service,
        "optimize_cv_for_job",
        lambda **_kwargs: (_ for _ in ()).throw(
            career_copilot_service.cv_optimizer_service.CVOptimizerAIError("provider failed")
        ),
    )

    response = career_copilot_service.chat_with_career_copilot(
        user_id=OWNER_ID,
        analysis_id=ANALYSIS_ID,
        message="Tailor my CV for this job.",
        job_external_id="job-1",
        provider="adzuna",
    )

    assert response.tool_result is not None
    assert response.tool_result.status == "failed"
    assert response.tool_result.data is None
    assert "temporarily unavailable" in response.reply


def test_career_copilot_invalid_job_returns_failed_tool_result(monkeypatch) -> None:
    monkeypatch.setattr(career_copilot_service, "_get_completed_analysis", lambda **_kwargs: make_analysis())
    monkeypatch.setattr(
        career_copilot_service.cv_optimizer_service,
        "optimize_cv_for_job",
        lambda **_kwargs: (_ for _ in ()).throw(
            career_copilot_service.cv_optimizer_service.CVOptimizerInputNotFoundError("missing")
        ),
    )

    response = career_copilot_service.chat_with_career_copilot(
        user_id=OWNER_ID,
        analysis_id=ANALYSIS_ID,
        message="Rewrite my CV for this job.",
        job_external_id="missing-job",
        provider="jsearch",
    )

    assert response.tool_result is not None
    assert response.tool_result.status == "failed"
    assert response.suggested_action is not None
    assert response.suggested_action.type == "open_jobs"


def test_career_copilot_prompt_works_with_analysis_only(monkeypatch) -> None:
    captured = capture_copilot_prompt(monkeypatch)
    monkeypatch.setattr(career_copilot_service, "_get_user_profile_context", lambda _user_id: None)
    monkeypatch.setattr(career_copilot_service, "_get_latest_job_match_context", lambda _user_id: None)
    monkeypatch.setattr(career_copilot_service, "_get_latest_optimizer_context", lambda *_args: None)
    monkeypatch.setattr(career_copilot_service.career_profile_service, "get_career_profile_for_analysis", lambda *_args: None)
    monkeypatch.setattr(career_copilot_service.roadmap_service, "get_active_roadmap", lambda **_kwargs: None)

    reply = career_copilot_service.ask_career_copilot(
        user_id=OWNER_ID,
        analysis_id=ANALYSIS_ID,
        message="What should I improve?",
    )

    assert reply == "Focus on Docker deployment practice next."
    assert "Target role: Backend Software Engineer" in captured["prompt"]
    assert "Strengths: ['Python', 'FastAPI']" in captured["prompt"]
    assert "Missing skills: ['Docker', 'AWS']" in captured["prompt"]


def test_career_copilot_prompt_includes_profile_context(monkeypatch) -> None:
    captured = capture_copilot_prompt(monkeypatch)
    monkeypatch.setattr(
        career_copilot_service,
        "_get_user_profile_context",
        lambda _user_id: {
            "full_name": "Selcan Aktürk",
            "headline": "Backend Developer",
            "location": "Istanbul",
        },
    )
    monkeypatch.setattr(career_copilot_service, "_get_latest_job_match_context", lambda _user_id: None)
    monkeypatch.setattr(career_copilot_service, "_get_latest_optimizer_context", lambda *_args: None)
    monkeypatch.setattr(career_copilot_service.career_profile_service, "get_career_profile_for_analysis", lambda *_args: None)
    monkeypatch.setattr(career_copilot_service.roadmap_service, "get_active_roadmap", lambda **_kwargs: None)

    career_copilot_service.ask_career_copilot(
        user_id=OWNER_ID,
        analysis_id=ANALYSIS_ID,
        message="How should I position myself?",
    )

    assert "User profile:" in captured["prompt"]
    assert "Full name: Selcan Aktürk" in captured["prompt"]
    assert "Headline: Backend Developer" in captured["prompt"]
    assert "Location: Istanbul" in captured["prompt"]


def test_career_copilot_prompt_includes_latest_match_context(monkeypatch) -> None:
    captured = capture_copilot_prompt(monkeypatch)
    monkeypatch.setattr(career_copilot_service, "_get_user_profile_context", lambda _user_id: None)
    monkeypatch.setattr(
        career_copilot_service,
        "_get_latest_job_match_context",
        lambda _user_id: {
            "match_score": 76,
            "matched_skills": ["Python", "FastAPI"],
            "missing_skills": ["Kubernetes"],
            "recommendations": ["Add one deployment story"],
            "summary": "Good backend match with infrastructure gaps.",
        },
    )
    monkeypatch.setattr(career_copilot_service, "_get_latest_optimizer_context", lambda *_args: None)
    monkeypatch.setattr(career_copilot_service.career_profile_service, "get_career_profile_for_analysis", lambda *_args: None)
    monkeypatch.setattr(career_copilot_service.roadmap_service, "get_active_roadmap", lambda **_kwargs: None)

    career_copilot_service.ask_career_copilot(
        user_id=OWNER_ID,
        analysis_id=ANALYSIS_ID,
        message="Can I apply now?",
    )

    assert "Latest job match:" in captured["prompt"]
    assert "Match score: 76" in captured["prompt"]
    assert "Strongest matching skills: ['Python', 'FastAPI']" in captured["prompt"]
    assert "Missing skills: ['Kubernetes']" in captured["prompt"]
    assert "Recommendations: ['Add one deployment story']" in captured["prompt"]


def test_career_copilot_prompt_includes_optimizer_context(monkeypatch) -> None:
    captured = capture_copilot_prompt(monkeypatch)
    monkeypatch.setattr(career_copilot_service, "_get_user_profile_context", lambda _user_id: None)
    monkeypatch.setattr(career_copilot_service, "_get_latest_job_match_context", lambda _user_id: None)
    monkeypatch.setattr(
        career_copilot_service,
        "_get_latest_optimizer_context",
        lambda *_args: {
            "match_before": 45,
            "estimated_match_after": 72,
            "summary": "CV can better emphasize API ownership.",
            "changes": ["Reordered backend skills", "Highlighted Python projects"],
        },
    )
    monkeypatch.setattr(career_copilot_service.career_profile_service, "get_career_profile_for_analysis", lambda *_args: None)
    monkeypatch.setattr(career_copilot_service.roadmap_service, "get_active_roadmap", lambda **_kwargs: None)

    career_copilot_service.ask_career_copilot(
        user_id=OWNER_ID,
        analysis_id=ANALYSIS_ID,
        message="What should I improve in my CV?",
    )

    assert "Latest CV optimizer result:" in captured["prompt"]
    assert "Current match: 45" in captured["prompt"]
    assert "Estimated match after optimization: 72" in captured["prompt"]
    assert "Optimization summary: CV can better emphasize API ownership." in captured["prompt"]
    assert "Major improvements: ['Reordered backend skills', 'Highlighted Python projects']" in captured["prompt"]


def test_career_copilot_missing_optional_context_does_not_fail(monkeypatch) -> None:
    captured = capture_copilot_prompt(monkeypatch)

    def raise_optional_error(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("optional context unavailable")

    monkeypatch.setattr(career_copilot_service, "_get_user_profile_context", raise_optional_error)
    monkeypatch.setattr(career_copilot_service, "_get_latest_job_match_context", raise_optional_error)
    monkeypatch.setattr(career_copilot_service, "_get_latest_optimizer_context", raise_optional_error)
    monkeypatch.setattr(career_copilot_service.career_profile_service, "get_career_profile_for_analysis", raise_optional_error)
    monkeypatch.setattr(career_copilot_service.roadmap_service, "get_active_roadmap", raise_optional_error)

    reply = career_copilot_service.ask_career_copilot(
        user_id=OWNER_ID,
        analysis_id=ANALYSIS_ID,
        message="What is next?",
    )

    assert reply == "Focus on Docker deployment practice next."
    assert "CV analysis context:" in captured["prompt"]
    assert "Target role: Backend Software Engineer" in captured["prompt"]


def test_latest_job_match_context_reads_newest_match(monkeypatch) -> None:
    class FakeQuery:
        def __init__(self) -> None:
            self.table_name = ""
            self.orders: list[tuple[str, bool]] = []
            self.filters: list[tuple[str, str]] = []

        def select(self, _columns: str) -> "FakeQuery":
            return self

        def eq(self, column: str, value: str) -> "FakeQuery":
            self.filters.append((column, value))
            return self

        def order(self, column: str, desc: bool = False) -> "FakeQuery":
            self.orders.append((column, desc))
            return self

        def limit(self, _value: int) -> "FakeQuery":
            return self

        def execute(self) -> SimpleNamespace:
            return SimpleNamespace(
                data=[
                    {
                        "match_score": 88,
                        "matched_skills": ["Python"],
                        "missing_skills": ["AWS"],
                        "recommendations": ["Add AWS proof"],
                        "summary": "Strong fit.",
                    }
                ]
            )

    class FakeClient:
        def __init__(self) -> None:
            self.query = FakeQuery()

        def table(self, table_name: str) -> FakeQuery:
            self.query.table_name = table_name
            return self.query

    fake_client = FakeClient()
    monkeypatch.setattr(career_copilot_service, "get_supabase_client", lambda: fake_client)

    context = career_copilot_service._get_latest_job_match_context(OWNER_ID)

    assert context is not None
    assert context["match_score"] == 88
    assert fake_client.query.table_name == "job_matches"
    assert ("user_id", OWNER_ID) in fake_client.query.filters
    assert ("updated_at", True) in fake_client.query.orders


def test_suggest_action_cv_intent() -> None:
    action = career_copilot_service.suggest_action_for_message("How can I improve my CV?")

    assert action is not None
    assert action.type == "open_cv_optimizer"
    assert action.label == "Open CV Optimizer"
    assert action.target == "/jobs"


def test_suggest_action_job_intent() -> None:
    action = career_copilot_service.suggest_action_for_message("Which job should I apply to?")

    assert action is not None
    assert action.type == "open_jobs"
    assert action.target == "/jobs"


def test_suggest_action_roadmap_intent() -> None:
    action = career_copilot_service.suggest_action_for_message("What should I learn next?")

    assert action is not None
    assert action.type == "open_roadmap"
    assert action.target == "/dashboard"


def test_suggest_action_profile_intent() -> None:
    action = career_copilot_service.suggest_action_for_message("Can you improve my headline?")

    assert action is not None
    assert action.type == "open_profile"
    assert action.target == "/profile"


def test_suggest_action_upload_intent() -> None:
    action = career_copilot_service.suggest_action_for_message("I want to upload a new CV.")

    assert action is not None
    assert action.type == "open_upload_cv"
    assert action.target == "/upload-cv"


def test_suggest_action_history_intent() -> None:
    action = career_copilot_service.suggest_action_for_message("Show my previous analysis history.")

    assert action is not None
    assert action.type == "open_history"
    assert action.target == "/history"


def test_suggest_action_unknown_intent_returns_none() -> None:
    assert career_copilot_service.suggest_action_for_message("Can you explain this in simpler terms?") is None
