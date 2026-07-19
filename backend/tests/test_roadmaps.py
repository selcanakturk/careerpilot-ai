import json
import os
from types import SimpleNamespace
from uuid import uuid4

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-api-key")
os.environ.setdefault("OPENAI_MODEL", "gpt-5-mini")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-api-key")
os.environ.setdefault("GEMINI_MODEL", "gemini-2.5-flash")

from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.security import CurrentUser, get_current_user
from app.main import app
from app.schemas.roadmap import CareerRoadmap, RoadmapGenerateResponse
from app.services import roadmap_service


OWNER_ID = "11111111-1111-1111-1111-111111111111"


def override_current_user() -> CurrentUser:
    return CurrentUser(id=OWNER_ID, email="owner@example.com")


def make_days(week_number: int) -> list[dict[str, object]]:
    return [
        {
            "day_name": "Monday",
            "tasks": [
                {
                    "title": f"Review week {week_number} learning objective",
                    "estimated_minutes": 45,
                }
            ],
        },
        {
            "day_name": "Wednesday",
            "tasks": [
                {
                    "title": f"Practice week {week_number} core skill",
                    "estimated_minutes": 60,
                }
            ],
        },
        {
            "day_name": "Friday",
            "tasks": [
                {
                    "title": f"Document week {week_number} project evidence",
                    "estimated_minutes": 75,
                }
            ],
        },
    ]


def make_roadmap_payload() -> dict[str, object]:
    return {
        "summary": "A focused roadmap to close analytics and execution gaps for product roles.",
        "duration_weeks": 4,
        "estimated_job_readiness_before": 62,
        "estimated_job_readiness_after": 82,
        "steps": [
            {
                "week_number": 1,
                "title": "Map core product analytics gaps",
                "description": "Review product metrics, funnels, and activation concepts.",
                "reason": "Analytics proof was the highest-impact gap in the CV analysis.",
                "estimated_hours": 6,
                "priority": "critical",
                "resources": [{"title": "Product Analytics Guide", "url": "https://example.com/analytics"}],
                "mini_project": "Create a metric tree for a SaaS onboarding flow.",
                "days": make_days(1),
            },
            {
                "week_number": 2,
                "title": "Build experimentation evidence",
                "description": "Learn experiment design and write clear hypotheses.",
                "reason": "The target role expects structured product decision-making.",
                "estimated_hours": 5,
                "priority": "high",
                "resources": [{"title": "Experiment Design", "url": "https://example.com/experiments"}],
                "mini_project": "Draft an A/B test plan for activation.",
                "days": make_days(2),
            },
            {
                "week_number": 3,
                "title": "Strengthen roadmap storytelling",
                "description": "Turn existing work into outcome-focused product stories.",
                "reason": "The analysis found strengths but limited quantified impact.",
                "estimated_hours": 4,
                "priority": "medium",
                "resources": [{"title": "STAR Stories", "url": "https://example.com/star"}],
                "mini_project": "Rewrite three bullets with metrics and tradeoffs.",
                "days": make_days(3),
            },
            {
                "week_number": 4,
                "title": "Package the role-fit narrative",
                "description": "Prepare interview examples and CV updates for the target role.",
                "reason": "A final packaging week improves readiness before applying.",
                "estimated_hours": 5,
                "priority": "high",
                "resources": [{"title": "PM Interview Prep", "url": "https://example.com/interview"}],
                "mini_project": "Create a one-page product portfolio case summary.",
                "days": make_days(4),
            },
        ],
    }


def make_roadmap_response(analysis_id: str | None = None) -> RoadmapGenerateResponse:
    return RoadmapGenerateResponse(
        id=str(uuid4()),
        user_id=OWNER_ID,
        analysis_id=analysis_id or str(uuid4()),
        target_role="Product Manager",
        status="active",
        roadmap=CareerRoadmap.model_validate(make_roadmap_payload()),
        created_at="2026-07-13T10:00:00Z",
        updated_at="2026-07-13T10:00:00Z",
    )


def make_analysis_context(analysis_id: str) -> dict[str, object]:
    return {
        "id": analysis_id,
        "user_id": OWNER_ID,
        "cv_upload_id": str(uuid4()),
        "target_role": "Product Manager",
        "status": "completed",
        "overall_score": 62,
        "summary": "Strong roadmap experience with analytics gaps.",
        "strengths": ["Roadmap ownership"],
        "weaknesses": ["Limited metrics"],
        "skill_gaps": ["Product analytics"],
        "cv_suggestions": ["Add quantified outcomes"],
        "experience_level": "mid",
    }


def make_step_update_response(
    roadmap_id: str,
    step_id: str,
    status: str = "completed",
) -> dict[str, object]:
    return {
        "id": step_id,
        "roadmap_id": roadmap_id,
        "week_number": 2,
        "status": status,
        "updated_at": "2026-07-15T10:00:00Z",
    }


def make_task_update_response(
    roadmap_id: str,
    task_id: str,
    step_id: str,
    status: str = "completed",
    step_status: str = "in_progress",
) -> dict[str, object]:
    return {
        "id": task_id,
        "roadmap_id": roadmap_id,
        "step_id": step_id,
        "day_name": "Monday",
        "task_order": 1,
        "title": "Practice product analytics",
        "estimated_minutes": 45,
        "status": status,
        "step_status": step_status,
        "updated_at": "2026-07-15T10:00:00Z",
    }


def test_update_roadmap_step_owner_returns_200(monkeypatch) -> None:
    roadmap_id = str(uuid4())
    step_id = str(uuid4())

    monkeypatch.setattr(
        roadmap_service,
        "get_owned_roadmap",
        lambda **_kwargs: {"id": roadmap_id, "user_id": OWNER_ID},
    )
    monkeypatch.setattr(
        roadmap_service,
        "update_step_status",
        lambda **_kwargs: make_step_update_response(roadmap_id, step_id, "completed"),
    )
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).patch(
            f"/api/roadmaps/{roadmap_id}/steps/{step_id}",
            json={"status": "completed"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["id"] == step_id
    assert response.json()["roadmap_id"] == roadmap_id
    assert response.json()["status"] == "completed"


def test_update_roadmap_task_owner_returns_200(monkeypatch) -> None:
    roadmap_id = str(uuid4())
    task_id = str(uuid4())
    step_id = str(uuid4())

    monkeypatch.setattr(
        roadmap_service,
        "get_owned_roadmap",
        lambda **_kwargs: {"id": roadmap_id, "user_id": OWNER_ID},
    )
    monkeypatch.setattr(
        roadmap_service,
        "update_task_status",
        lambda **_kwargs: make_task_update_response(roadmap_id, task_id, step_id, "completed", "in_progress"),
    )
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).patch(
            f"/api/roadmaps/{roadmap_id}/tasks/{task_id}",
            json={"status": "completed"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["id"] == task_id
    assert response.json()["status"] == "completed"
    assert response.json()["step_status"] == "in_progress"


def test_update_roadmap_task_accepts_not_started(monkeypatch) -> None:
    roadmap_id = str(uuid4())
    task_id = str(uuid4())
    step_id = str(uuid4())
    saved_statuses: list[str] = []

    monkeypatch.setattr(
        roadmap_service,
        "get_owned_roadmap",
        lambda **_kwargs: {"id": roadmap_id, "user_id": OWNER_ID},
    )

    def update_task_status(**kwargs: object) -> dict[str, object]:
        status = str(kwargs["status"])
        saved_statuses.append(status)
        return make_task_update_response(roadmap_id, task_id, step_id, status, "not_started")

    monkeypatch.setattr(roadmap_service, "update_task_status", update_task_status)
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).patch(
            f"/api/roadmaps/{roadmap_id}/tasks/{task_id}",
            json={"status": "not_started"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "not_started"
    assert saved_statuses == ["not_started"]


def test_update_roadmap_task_roadmap_not_found_returns_404(monkeypatch) -> None:
    monkeypatch.setattr(roadmap_service, "get_owned_roadmap", lambda **_kwargs: None)
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).patch(
            f"/api/roadmaps/{uuid4()}/tasks/{uuid4()}",
            json={"status": "completed"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_update_roadmap_task_without_auth_returns_401() -> None:
    response = TestClient(app).patch(
        f"/api/roadmaps/{uuid4()}/tasks/{uuid4()}",
        json={"status": "completed"},
    )

    assert response.status_code == 401


def test_update_roadmap_task_invalid_status_returns_422(monkeypatch) -> None:
    monkeypatch.setattr(
        roadmap_service,
        "get_owned_roadmap",
        lambda **_kwargs: {"id": str(uuid4()), "user_id": OWNER_ID},
    )
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).patch(
            f"/api/roadmaps/{uuid4()}/tasks/{uuid4()}",
            json={"status": "in_progress"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_update_roadmap_task_not_found_returns_404(monkeypatch) -> None:
    monkeypatch.setattr(
        roadmap_service,
        "get_owned_roadmap",
        lambda **_kwargs: {"id": str(uuid4()), "user_id": OWNER_ID},
    )
    monkeypatch.setattr(roadmap_service, "update_task_status", lambda **_kwargs: None)
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).patch(
            f"/api/roadmaps/{uuid4()}/tasks/{uuid4()}",
            json={"status": "completed"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_update_roadmap_task_supabase_error_returns_500(monkeypatch) -> None:
    monkeypatch.setattr(
        roadmap_service,
        "get_owned_roadmap",
        lambda **_kwargs: {"id": str(uuid4()), "user_id": OWNER_ID},
    )

    def raise_update_error(**_kwargs: object) -> None:
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(roadmap_service, "update_task_status", raise_update_error)
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).patch(
            f"/api/roadmaps/{uuid4()}/tasks/{uuid4()}",
            json={"status": "completed"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json()["detail"] == "Unable to update roadmap task."


def test_update_roadmap_step_accepts_all_valid_statuses(monkeypatch) -> None:
    roadmap_id = str(uuid4())
    step_id = str(uuid4())
    saved_statuses: list[str] = []

    monkeypatch.setattr(
        roadmap_service,
        "get_owned_roadmap",
        lambda **_kwargs: {"id": roadmap_id, "user_id": OWNER_ID},
    )

    def update_step_status(**kwargs: object) -> dict[str, object]:
        status = str(kwargs["status"])
        saved_statuses.append(status)
        return make_step_update_response(roadmap_id, step_id, status)

    monkeypatch.setattr(roadmap_service, "update_step_status", update_step_status)
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        client = TestClient(app)
        responses = [
            client.patch(f"/api/roadmaps/{roadmap_id}/steps/{step_id}", json={"status": status})
            for status in ["not_started", "in_progress", "completed"]
        ]
    finally:
        app.dependency_overrides.clear()

    assert [response.status_code for response in responses] == [200, 200, 200]
    assert saved_statuses == ["not_started", "in_progress", "completed"]


def test_update_roadmap_step_roadmap_not_found_returns_404(monkeypatch) -> None:
    roadmap_id = str(uuid4())
    step_id = str(uuid4())
    monkeypatch.setattr(roadmap_service, "get_owned_roadmap", lambda **_kwargs: None)
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).patch(
            f"/api/roadmaps/{roadmap_id}/steps/{step_id}",
            json={"status": "completed"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_update_roadmap_step_other_user_roadmap_returns_404(monkeypatch) -> None:
    roadmap_id = str(uuid4())
    step_id = str(uuid4())
    monkeypatch.setattr(roadmap_service, "get_owned_roadmap", lambda **_kwargs: None)
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).patch(
            f"/api/roadmaps/{roadmap_id}/steps/{step_id}",
            json={"status": "completed"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_update_roadmap_step_without_auth_returns_401() -> None:
    response = TestClient(app).patch(
        f"/api/roadmaps/{uuid4()}/steps/{uuid4()}",
        json={"status": "completed"},
    )

    assert response.status_code == 401


def test_update_roadmap_step_invalid_status_returns_422(monkeypatch) -> None:
    monkeypatch.setattr(
        roadmap_service,
        "get_owned_roadmap",
        lambda **_kwargs: {"id": str(uuid4()), "user_id": OWNER_ID},
    )
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).patch(
            f"/api/roadmaps/{uuid4()}/steps/{uuid4()}",
            json={"status": "done"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_update_roadmap_step_not_found_returns_404(monkeypatch) -> None:
    roadmap_id = str(uuid4())
    step_id = str(uuid4())
    monkeypatch.setattr(
        roadmap_service,
        "get_owned_roadmap",
        lambda **_kwargs: {"id": roadmap_id, "user_id": OWNER_ID},
    )
    monkeypatch.setattr(roadmap_service, "update_step_status", lambda **_kwargs: None)
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).patch(
            f"/api/roadmaps/{roadmap_id}/steps/{step_id}",
            json={"status": "completed"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_update_roadmap_step_from_different_roadmap_returns_404(monkeypatch) -> None:
    roadmap_id = str(uuid4())
    step_id = str(uuid4())
    monkeypatch.setattr(
        roadmap_service,
        "get_owned_roadmap",
        lambda **_kwargs: {"id": roadmap_id, "user_id": OWNER_ID},
    )
    monkeypatch.setattr(roadmap_service, "update_step_status", lambda **_kwargs: None)
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).patch(
            f"/api/roadmaps/{roadmap_id}/steps/{step_id}",
            json={"status": "completed"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_update_roadmap_step_supabase_error_returns_500(monkeypatch) -> None:
    roadmap_id = str(uuid4())
    step_id = str(uuid4())
    monkeypatch.setattr(
        roadmap_service,
        "get_owned_roadmap",
        lambda **_kwargs: {"id": roadmap_id, "user_id": OWNER_ID},
    )

    def raise_update_error(**_kwargs: object) -> None:
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(roadmap_service, "update_step_status", raise_update_error)
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).patch(
            f"/api/roadmaps/{roadmap_id}/steps/{step_id}",
            json={"status": "completed"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert response.json()["detail"] == "Unable to update roadmap step."


def test_generate_roadmap_owner_returns_200(monkeypatch) -> None:
    analysis_id = str(uuid4())
    calls: dict[str, int] = {"generate": 0, "save": 0}

    monkeypatch.setattr(
        roadmap_service,
        "get_analysis_context",
        lambda **_kwargs: make_analysis_context(analysis_id),
    )
    monkeypatch.setattr(roadmap_service, "get_active_roadmap", lambda **_kwargs: None)

    def generate_career_roadmap(_analysis: dict[str, object]) -> CareerRoadmap:
        calls["generate"] += 1
        return CareerRoadmap.model_validate(make_roadmap_payload())

    def save_roadmap(**_kwargs: object) -> RoadmapGenerateResponse:
        calls["save"] += 1
        return make_roadmap_response(analysis_id)

    monkeypatch.setattr(roadmap_service, "generate_career_roadmap", generate_career_roadmap)
    monkeypatch.setattr(roadmap_service, "save_roadmap", save_roadmap)
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).post(f"/api/roadmaps/generate/{analysis_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["analysis_id"] == analysis_id
    assert response.json()["roadmap"]["duration_weeks"] == 4
    assert calls == {"generate": 1, "save": 1}


def test_generate_roadmap_without_auth_returns_401(monkeypatch) -> None:
    analysis_id = str(uuid4())

    def fail_if_called(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Roadmap service should not be called without auth.")

    monkeypatch.setattr(roadmap_service, "get_analysis_context", fail_if_called)

    try:
        response = TestClient(app).post(f"/api/roadmaps/generate/{analysis_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401


def test_generate_roadmap_analysis_not_found_returns_404(monkeypatch) -> None:
    analysis_id = str(uuid4())
    monkeypatch.setattr(roadmap_service, "get_analysis_context", lambda **_kwargs: None)
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).post(f"/api/roadmaps/generate/{analysis_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Analysis not found."


def test_generate_roadmap_existing_active_returns_existing_without_regeneration(monkeypatch) -> None:
    analysis_id = str(uuid4())
    existing = make_roadmap_response(analysis_id)
    calls: dict[str, int] = {"generate": 0, "save": 0}

    monkeypatch.setattr(
        roadmap_service,
        "get_analysis_context",
        lambda **_kwargs: make_analysis_context(analysis_id),
    )
    monkeypatch.setattr(roadmap_service, "get_active_roadmap", lambda **_kwargs: existing)

    def fail_if_generate(*_args: object, **_kwargs: object) -> None:
        calls["generate"] += 1
        raise AssertionError("Gemini should not be called when an active roadmap exists.")

    def fail_if_save(*_args: object, **_kwargs: object) -> None:
        calls["save"] += 1
        raise AssertionError("Roadmap should not be saved when an active roadmap exists.")

    monkeypatch.setattr(roadmap_service, "generate_career_roadmap", fail_if_generate)
    monkeypatch.setattr(roadmap_service, "save_roadmap", fail_if_save)
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).post(f"/api/roadmaps/generate/{analysis_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["id"] == str(existing.id)
    assert calls == {"generate": 0, "save": 0}


class FakeGeminiResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeGeminiModels:
    def __init__(self, failures: list[Exception] | None = None, response_text: str | None = None) -> None:
        self.call: dict[str, object] = {}
        self.model_calls: list[str] = []
        self.calls = 0
        self.failures = failures or []
        self.response_text = response_text or json.dumps(make_roadmap_payload())

    def generate_content(self, **kwargs: object) -> FakeGeminiResponse:
        self.call = kwargs
        self.model_calls.append(str(kwargs["model"]))
        self.calls += 1

        if self.failures:
            raise self.failures.pop(0)

        return FakeGeminiResponse(self.response_text)


class FakeGeminiClient:
    def __init__(self, models: FakeGeminiModels | None = None) -> None:
        self.models = models or FakeGeminiModels()


def test_generate_career_roadmap_uses_mock_gemini(monkeypatch) -> None:
    fake_client = FakeGeminiClient()
    monkeypatch.setattr(roadmap_service, "get_gemini_client", lambda: fake_client)

    result = roadmap_service.generate_career_roadmap(make_analysis_context(str(uuid4())))

    assert result.duration_weeks == 4
    assert len(result.steps) == 4
    assert result.steps[0].days[0].day_name == "Monday"
    assert result.steps[0].days[0].tasks[0].estimated_minutes == 45
    assert fake_client.models.call["model"] == "gemini-2.5-flash"
    assert fake_client.models.model_calls == ["gemini-2.5-flash"]


def test_career_roadmap_requires_days() -> None:
    payload = make_roadmap_payload()
    step = payload["steps"][0]
    assert isinstance(step, dict)
    step.pop("days")

    try:
        CareerRoadmap.model_validate(payload)
    except ValidationError:
        return

    raise AssertionError("Roadmap validation should fail when a step has no days.")


def test_career_roadmap_rejects_empty_day_tasks() -> None:
    payload = make_roadmap_payload()
    step = payload["steps"][0]
    assert isinstance(step, dict)
    days = step["days"]
    assert isinstance(days, list)
    first_day = days[0]
    assert isinstance(first_day, dict)
    first_day["tasks"] = []

    try:
        CareerRoadmap.model_validate(payload)
    except ValidationError:
        return

    raise AssertionError("Roadmap validation should fail when a day has no tasks.")


def test_career_roadmap_rejects_invalid_task_values() -> None:
    payload = make_roadmap_payload()
    step = payload["steps"][0]
    assert isinstance(step, dict)
    days = step["days"]
    assert isinstance(days, list)
    first_day = days[0]
    assert isinstance(first_day, dict)
    tasks = first_day["tasks"]
    assert isinstance(tasks, list)
    first_task = tasks[0]
    assert isinstance(first_task, dict)
    first_task["title"] = ""
    first_task["estimated_minutes"] = -10

    try:
        CareerRoadmap.model_validate(payload)
    except ValidationError:
        return

    raise AssertionError("Roadmap validation should fail for blank title and negative duration.")


def _collect_schema_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = set(value)
        for nested_value in value.values():
            keys.update(_collect_schema_keys(nested_value))
        return keys

    if isinstance(value, list):
        keys: set[str] = set()
        for nested_value in value:
            keys.update(_collect_schema_keys(nested_value))
        return keys

    return set()


def _collect_schema_keyword_keys(value: object, parent_key: str | None = None) -> set[str]:
    if isinstance(value, dict):
        keys: set[str] = set()

        for key, nested_value in value.items():
            if parent_key != "properties":
                keys.add(key)
            keys.update(_collect_schema_keyword_keys(nested_value, key))

        return keys

    if isinstance(value, list):
        keys: set[str] = set()
        for nested_value in value:
            keys.update(_collect_schema_keyword_keys(nested_value, parent_key))
        return keys

    return set()


def _collect_schema_types(value: object) -> set[str]:
    if isinstance(value, dict):
        types = {value["type"]} if isinstance(value.get("type"), str) else set()
        for nested_value in value.values():
            types.update(_collect_schema_types(nested_value))
        return types

    if isinstance(value, list):
        types: set[str] = set()
        for nested_value in value:
            types.update(_collect_schema_types(nested_value))
        return types

    return set()


def test_gemini_roadmap_schema_avoids_unsupported_json_schema_features() -> None:
    schema = roadmap_service.build_gemini_roadmap_schema()
    keys = _collect_schema_keyword_keys(schema)

    assert "$defs" not in keys
    assert "$ref" not in keys
    assert "anyOf" not in keys
    assert "oneOf" not in keys
    assert "allOf" not in keys
    assert "pattern" not in keys
    assert "minLength" not in keys
    assert "maxLength" not in keys
    assert "exclusiveMinimum" not in keys
    assert "exclusiveMaximum" not in keys
    assert "const" not in keys
    assert "default" not in keys
    assert "examples" not in keys
    assert "title" not in keys


def test_gemini_roadmap_schema_uses_only_supported_basic_types() -> None:
    schema = roadmap_service.build_gemini_roadmap_schema()
    keys = _collect_schema_keys(schema)

    assert _collect_schema_types(schema) <= {"object", "array", "string", "integer"}
    assert keys <= {
        "type",
        "properties",
        "array",
        "string",
        "integer",
        "object",
        "minimum",
        "maximum",
        "enum",
        "required",
        "items",
        "summary",
        "duration_weeks",
        "estimated_job_readiness_before",
        "estimated_job_readiness_after",
        "steps",
        "week_number",
        "title",
        "description",
        "reason",
        "estimated_hours",
        "priority",
        "resources",
        "url",
        "mini_project",
        "days",
        "day_name",
        "tasks",
        "estimated_minutes",
    }


def test_generate_career_roadmap_sends_simplified_schema_to_gemini(monkeypatch) -> None:
    fake_client = FakeGeminiClient()
    monkeypatch.setattr(roadmap_service, "get_gemini_client", lambda: fake_client)

    result = roadmap_service.generate_career_roadmap(make_analysis_context(str(uuid4())))
    config = fake_client.models.call["config"]

    assert result.duration_weeks == 4
    assert getattr(config, "response_json_schema") == roadmap_service.build_gemini_roadmap_schema()


def test_generate_career_roadmap_primary_503_retries_then_succeeds_without_fallback(monkeypatch) -> None:
    models = FakeGeminiModels(failures=[RuntimeError("503 UNAVAILABLE high demand")])
    fake_client = FakeGeminiClient(models)
    monkeypatch.setattr(roadmap_service, "get_gemini_client", lambda: fake_client)
    monkeypatch.setattr(roadmap_service, "_sleep_before_retry", lambda _attempt: None)

    result = roadmap_service.generate_career_roadmap(make_analysis_context(str(uuid4())))

    assert result.duration_weeks == 4
    assert models.calls == 2
    assert models.model_calls == ["gemini-2.5-flash", "gemini-2.5-flash"]


def test_generate_career_roadmap_primary_503_retries_then_fallback_succeeds(monkeypatch) -> None:
    models = FakeGeminiModels(
        failures=[
            RuntimeError("503 UNAVAILABLE high demand"),
            RuntimeError("503 UNAVAILABLE high demand"),
        ]
    )
    fake_client = FakeGeminiClient(models)
    monkeypatch.setattr(roadmap_service, "get_gemini_client", lambda: fake_client)
    monkeypatch.setattr(roadmap_service, "_sleep_before_retry", lambda _attempt: None)

    result = roadmap_service.generate_career_roadmap(make_analysis_context(str(uuid4())))

    assert models.calls == 3
    assert result.duration_weeks == 4
    assert models.model_calls == [
        "gemini-2.5-flash",
        "gemini-2.5-flash",
        "gemini-3.1-flash-lite",
    ]


def test_generate_career_roadmap_primary_daily_quota_goes_directly_to_fallback(monkeypatch) -> None:
    models = FakeGeminiModels(
        failures=[
            RuntimeError(
                "429 RESOURCE_EXHAUSTED GenerateRequestsPerDayPerProjectPerModel-FreeTier current quota exceeded"
            ),
        ]
    )
    fake_client = FakeGeminiClient(models)
    sleeps: list[int] = []
    monkeypatch.setattr(roadmap_service, "get_gemini_client", lambda: fake_client)
    monkeypatch.setattr(roadmap_service, "_sleep_before_retry", lambda attempt: sleeps.append(attempt))

    result = roadmap_service.generate_career_roadmap(make_analysis_context(str(uuid4())))

    assert result.duration_weeks == 4
    assert models.calls == 2
    assert models.model_calls == ["gemini-2.5-flash", "gemini-3.1-flash-lite"]
    assert getattr(models.call["config"], "response_json_schema") == roadmap_service.build_gemini_roadmap_schema()
    assert sleeps == []


def test_generate_career_roadmap_retries_429(monkeypatch) -> None:
    models = FakeGeminiModels(failures=[RuntimeError("429 RESOURCE_EXHAUSTED quota")])
    fake_client = FakeGeminiClient(models)
    monkeypatch.setattr(roadmap_service, "get_gemini_client", lambda: fake_client)
    monkeypatch.setattr(roadmap_service, "_sleep_before_retry", lambda _attempt: None)

    result = roadmap_service.generate_career_roadmap(make_analysis_context(str(uuid4())))

    assert result.duration_weeks == 4
    assert models.calls == 2
    assert models.model_calls == ["gemini-2.5-flash", "gemini-2.5-flash"]


def test_generate_career_roadmap_primary_400_does_not_retry_or_fallback(monkeypatch) -> None:
    models = FakeGeminiModels(failures=[RuntimeError("400 INVALID_ARGUMENT unsupported schema")])
    fake_client = FakeGeminiClient(models)
    sleeps: list[int] = []
    monkeypatch.setattr(roadmap_service, "get_gemini_client", lambda: fake_client)
    monkeypatch.setattr(roadmap_service, "_sleep_before_retry", lambda attempt: sleeps.append(attempt))

    try:
        roadmap_service.generate_career_roadmap(make_analysis_context(str(uuid4())))
    except RuntimeError as exc:
        assert "Unable to generate AI roadmap right now." in str(exc)
    else:
        raise AssertionError("Expected RuntimeError.")

    assert models.calls == 1
    assert models.model_calls == ["gemini-2.5-flash"]
    assert sleeps == []


def test_generate_career_roadmap_primary_and_fallback_temporary_errors_raise(monkeypatch) -> None:
    models = FakeGeminiModels(
        failures=[
            RuntimeError("503 UNAVAILABLE high demand"),
            RuntimeError("503 UNAVAILABLE high demand"),
            RuntimeError("429 RESOURCE_EXHAUSTED quota"),
            RuntimeError("429 RESOURCE_EXHAUSTED quota"),
            RuntimeError("429 RESOURCE_EXHAUSTED quota"),
        ]
    )
    fake_client = FakeGeminiClient(models)
    monkeypatch.setattr(roadmap_service, "get_gemini_client", lambda: fake_client)
    monkeypatch.setattr(roadmap_service, "_sleep_before_retry", lambda _attempt: None)

    try:
        roadmap_service.generate_career_roadmap(make_analysis_context(str(uuid4())))
    except roadmap_service.TemporaryAIServiceError:
        pass
    else:
        raise AssertionError("Expected TemporaryAIServiceError.")

    assert models.model_calls == [
        "gemini-2.5-flash",
        "gemini-2.5-flash",
        "gemini-3.1-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.1-flash-lite",
    ]


def test_generate_career_roadmap_validation_error_is_not_retried(monkeypatch) -> None:
    models = FakeGeminiModels(response_text="not json")
    fake_client = FakeGeminiClient(models)
    sleeps: list[int] = []
    monkeypatch.setattr(roadmap_service, "get_gemini_client", lambda: fake_client)
    monkeypatch.setattr(roadmap_service, "_sleep_before_retry", lambda attempt: sleeps.append(attempt))

    try:
        roadmap_service.generate_career_roadmap(make_analysis_context(str(uuid4())))
    except RuntimeError as exc:
        assert "validated" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError.")

    assert models.calls == 1
    assert models.model_calls == ["gemini-2.5-flash"]
    assert sleeps == []


def test_generate_roadmap_three_503_errors_returns_503_and_does_not_save(monkeypatch) -> None:
    analysis_id = str(uuid4())
    calls: dict[str, int] = {"save": 0}
    monkeypatch.setattr(
        roadmap_service,
        "get_analysis_context",
        lambda **_kwargs: make_analysis_context(analysis_id),
    )
    monkeypatch.setattr(roadmap_service, "get_active_roadmap", lambda **_kwargs: None)

    def raise_temporary_error(_analysis: dict[str, object]) -> CareerRoadmap:
        raise roadmap_service.TemporaryAIServiceError(
            "The AI roadmap service is busy. Please try again shortly."
        )

    def save_roadmap(**_kwargs: object) -> RoadmapGenerateResponse:
        calls["save"] += 1
        raise AssertionError("Roadmap should not be saved after failed provider calls.")

    monkeypatch.setattr(roadmap_service, "generate_career_roadmap", raise_temporary_error)
    monkeypatch.setattr(roadmap_service, "save_roadmap", save_roadmap)
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).post(f"/api/roadmaps/generate/{analysis_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"] == "The AI roadmap service is busy. Please try again shortly."
    assert calls["save"] == 0


def test_generate_roadmap_primary_quota_fallback_success_returns_200(monkeypatch) -> None:
    analysis_id = str(uuid4())
    models = FakeGeminiModels(
        failures=[
            RuntimeError(
                "429 RESOURCE_EXHAUSTED generate_content_free_tier_requests exceeded your current quota"
            ),
        ]
    )
    fake_client = FakeGeminiClient(models)
    calls: dict[str, int] = {"save": 0}
    monkeypatch.setattr(
        roadmap_service,
        "get_analysis_context",
        lambda **_kwargs: make_analysis_context(analysis_id),
    )
    monkeypatch.setattr(roadmap_service, "get_active_roadmap", lambda **_kwargs: None)
    monkeypatch.setattr(roadmap_service, "get_gemini_client", lambda: fake_client)
    monkeypatch.setattr(roadmap_service, "_sleep_before_retry", lambda _attempt: None)

    def save_roadmap(**_kwargs: object) -> RoadmapGenerateResponse:
        calls["save"] += 1
        return make_roadmap_response(analysis_id)

    monkeypatch.setattr(roadmap_service, "save_roadmap", save_roadmap)
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).post(f"/api/roadmaps/generate/{analysis_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["analysis_id"] == analysis_id
    assert calls["save"] == 1
    assert models.model_calls == ["gemini-2.5-flash", "gemini-3.1-flash-lite"]


def test_group_tasks_by_day_orders_days_and_tasks() -> None:
    step_id = str(uuid4())
    rows = [
        {
            "id": str(uuid4()),
            "step_id": step_id,
            "day_name": "Wednesday",
            "task_order": 2,
            "title": "Second Wednesday task",
            "estimated_minutes": 30,
            "status": "not_started",
        },
        {
            "id": str(uuid4()),
            "step_id": step_id,
            "day_name": "Monday",
            "task_order": 1,
            "title": "First Monday task",
            "estimated_minutes": 45,
            "status": "completed",
        },
        {
            "id": str(uuid4()),
            "step_id": step_id,
            "day_name": "Wednesday",
            "task_order": 1,
            "title": "First Wednesday task",
            "estimated_minutes": 60,
            "status": "not_started",
        },
    ]

    grouped = roadmap_service.group_tasks_by_day(rows)

    assert list(grouped) == [step_id]
    assert [day.day_name for day in grouped[step_id]] == ["Monday", "Wednesday"]
    assert [task.title for task in grouped[step_id][1].tasks] == [
        "First Wednesday task",
        "Second Wednesday task",
    ]
    assert grouped[step_id][0].tasks[0].status == "completed"


def test_build_roadmap_phases_splits_steps_into_three_groups() -> None:
    roadmap = CareerRoadmap.model_validate(make_roadmap_payload())

    phases = roadmap_service.build_roadmap_phases(roadmap.steps)

    assert [phase["title"] for phase in phases] == ["Phase 1", "Phase 2", "Phase 3"]
    assert phases[0]["skills"] == [
        "Map core product analytics gaps",
        "Product Analytics Guide",
        "Build experimentation evidence",
        "Experiment Design",
    ]
    assert phases[1]["skills"] == ["Strengthen roadmap storytelling", "STAR Stories"]
    assert phases[2]["skills"] == ["Package the role-fit narrative", "PM Interview Prep"]


def test_build_roadmap_phases_marks_current_phase() -> None:
    roadmap = CareerRoadmap.model_validate(make_roadmap_payload())
    roadmap.steps[0].status = "completed"
    roadmap.steps[1].status = "completed"

    phases = roadmap_service.build_roadmap_phases(roadmap.steps)

    assert [phase["status"] for phase in phases] == ["completed", "current", "locked"]


def test_build_roadmap_response_includes_smart_phase_fields() -> None:
    roadmap_id = str(uuid4())
    step_ids = [str(uuid4()) for _step in range(4)]
    roadmap_row = {
        "id": roadmap_id,
        "user_id": OWNER_ID,
        "analysis_id": str(uuid4()),
        "target_role": "Backend Developer",
        "duration_weeks": 4,
        "summary": "Build backend readiness.",
        "status": "active",
        "estimated_job_readiness_before": 70,
        "estimated_job_readiness_after": 92,
        "created_at": "2026-07-13T10:00:00Z",
        "updated_at": "2026-07-13T10:00:00Z",
    }
    step_rows = [
        {
            "id": step_ids[index],
            "week_number": index + 1,
            "title": f"Backend skill {index + 1}",
            "description": f"Practice backend skill {index + 1}.",
            "reason": "This closes a core backend gap.",
            "estimated_hours": 5,
            "priority": "high",
            "status": "completed" if index == 0 else "not_started",
            "resources": [],
            "mini_project": "Build a small API.",
            "updated_at": "2026-07-13T10:00:00Z",
        }
        for index in range(4)
    ]
    task_rows = [
        {
            "id": str(uuid4()),
            "step_id": step_id,
            "roadmap_id": roadmap_id,
            "day_name": "Monday",
            "task_order": 1,
            "title": "Practice one task",
            "estimated_minutes": 45,
            "status": "completed" if index == 0 else "not_started",
            "updated_at": "2026-07-13T10:00:00Z",
        }
        for index, step_id in enumerate(step_ids)
    ]

    response = roadmap_service._build_response_from_rows(roadmap_row, step_rows, task_rows)

    assert response.goal == "Backend Developer"
    assert response.estimated_months == "1"
    assert response.overall_progress == 25
    assert [phase.status for phase in response.phases] == ["current", "locked", "locked"]
    assert response.phases[0].skills == ["Backend skill 1", "Backend skill 2"]


class FakeLoadTasksQuery:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows

    def select(self, _columns: str) -> "FakeLoadTasksQuery":
        return self

    def eq(self, _column: str, _value: str) -> "FakeLoadTasksQuery":
        return self

    def execute(self) -> SimpleNamespace:
        return SimpleNamespace(data=self.rows)


class FakeLoadTasksClient:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows

    def table(self, table_name: str) -> FakeLoadTasksQuery:
        assert table_name == "roadmap_tasks"
        return FakeLoadTasksQuery(self.rows)


def test_load_tasks_returns_tasks_sorted_by_day_and_order(monkeypatch) -> None:
    roadmap_id = str(uuid4())
    step_id = str(uuid4())
    rows = [
        {
            "id": str(uuid4()),
            "step_id": step_id,
            "roadmap_id": roadmap_id,
            "day_name": "Friday",
            "task_order": 1,
            "title": "Friday task",
            "estimated_minutes": 30,
            "status": "not_started",
            "updated_at": "2026-07-15T10:00:00Z",
        },
        {
            "id": str(uuid4()),
            "step_id": step_id,
            "roadmap_id": roadmap_id,
            "day_name": "Monday",
            "task_order": 1,
            "title": "Monday task",
            "estimated_minutes": 30,
            "status": "not_started",
            "updated_at": "2026-07-15T10:00:00Z",
        },
    ]
    monkeypatch.setattr(roadmap_service, "get_supabase_client", lambda: FakeLoadTasksClient(rows))

    loaded = roadmap_service.load_tasks(roadmap_id)

    assert [task["day_name"] for task in loaded] == ["Monday", "Friday"]


class FakeTaskStatusQuery:
    def __init__(self, table_name: str, client: "FakeTaskStatusClient") -> None:
        self.table_name = table_name
        self.client = client
        self.update_payload: dict[str, object] | None = None
        self.filters: dict[str, str] = {}

    def select(self, _columns: str) -> "FakeTaskStatusQuery":
        return self

    def update(self, payload: dict[str, object]) -> "FakeTaskStatusQuery":
        self.update_payload = payload
        return self

    def eq(self, column: str, value: str) -> "FakeTaskStatusQuery":
        self.filters[column] = value
        return self

    def limit(self, _count: int) -> "FakeTaskStatusQuery":
        return self

    def execute(self) -> SimpleNamespace:
        if self.client.raise_on_update and self.update_payload is not None:
            raise RuntimeError("update failed")

        if self.table_name == "roadmap_tasks" and self.update_payload is None:
            if self.filters.get("id") == self.client.task_id:
                return SimpleNamespace(
                    data=[
                        {
                            "id": self.client.task_id,
                            "roadmap_id": self.client.roadmap_id,
                            "step_id": self.client.step_id,
                        }
                    ]
                )

            return SimpleNamespace(data=self.client.step_tasks)

        if self.table_name == "roadmap_tasks" and self.update_payload is not None:
            return SimpleNamespace(
                data=[
                    {
                        "id": self.client.task_id,
                        "roadmap_id": self.client.roadmap_id,
                        "step_id": self.client.step_id,
                        "day_name": "Monday",
                        "task_order": 1,
                        "title": "Practice task",
                        "estimated_minutes": 45,
                        "status": self.update_payload["status"],
                        "updated_at": "2026-07-15T10:00:00Z",
                    }
                ]
            )

        if self.table_name == "roadmap_steps":
            assert self.update_payload is not None
            self.client.synced_step_status = str(self.update_payload["status"])
            return SimpleNamespace(
                data=[
                    {
                        "id": self.client.step_id,
                        "roadmap_id": self.client.roadmap_id,
                        "week_number": 1,
                        "status": self.client.synced_step_status,
                        "updated_at": "2026-07-15T10:00:00Z",
                    }
                ]
            )

        raise AssertionError(f"Unexpected table {self.table_name}")


class FakeTaskStatusClient:
    def __init__(
        self,
        step_tasks: list[dict[str, object]],
        raise_on_update: bool = False,
    ) -> None:
        self.roadmap_id = str(uuid4())
        self.step_id = str(uuid4())
        self.task_id = str(uuid4())
        self.step_tasks = step_tasks
        self.raise_on_update = raise_on_update
        self.synced_step_status = ""

    def table(self, table_name: str) -> FakeTaskStatusQuery:
        return FakeTaskStatusQuery(table_name, self)


def test_update_task_status_syncs_step_completed(monkeypatch) -> None:
    fake_client = FakeTaskStatusClient(
        step_tasks=[
            {"id": str(uuid4()), "status": "completed"},
            {"id": str(uuid4()), "status": "completed"},
        ]
    )
    monkeypatch.setattr(roadmap_service, "get_supabase_client", lambda: fake_client)

    result = roadmap_service.update_task_status(fake_client.roadmap_id, fake_client.task_id, "completed")

    assert result is not None
    assert result["step_status"] == "completed"
    assert fake_client.synced_step_status == "completed"


def test_update_task_status_syncs_step_in_progress(monkeypatch) -> None:
    fake_client = FakeTaskStatusClient(
        step_tasks=[
            {"id": str(uuid4()), "status": "completed"},
            {"id": str(uuid4()), "status": "not_started"},
        ]
    )
    monkeypatch.setattr(roadmap_service, "get_supabase_client", lambda: fake_client)

    result = roadmap_service.update_task_status(fake_client.roadmap_id, fake_client.task_id, "completed")

    assert result is not None
    assert result["step_status"] == "in_progress"


def test_update_task_status_syncs_step_not_started(monkeypatch) -> None:
    fake_client = FakeTaskStatusClient(
        step_tasks=[
            {"id": str(uuid4()), "status": "not_started"},
            {"id": str(uuid4()), "status": "not_started"},
        ]
    )
    monkeypatch.setattr(roadmap_service, "get_supabase_client", lambda: fake_client)

    result = roadmap_service.update_task_status(fake_client.roadmap_id, fake_client.task_id, "not_started")

    assert result is not None
    assert result["step_status"] == "not_started"


def test_update_task_status_different_roadmap_returns_none(monkeypatch) -> None:
    fake_client = FakeTaskStatusClient(step_tasks=[])
    monkeypatch.setattr(roadmap_service, "get_supabase_client", lambda: fake_client)

    result = roadmap_service.update_task_status(fake_client.roadmap_id, str(uuid4()), "completed")

    assert result is None


class FakeTableQuery:
    def __init__(self, table_name: str, client: "FakeRoadmapClient") -> None:
        self.table_name = table_name
        self.client = client

    def insert(self, payload: object) -> "FakeTableQuery":
        self.client.operations.append((self.table_name, payload))
        self.payload = payload
        return self

    def delete(self) -> "FakeTableQuery":
        self.client.operations.append((self.table_name, "delete"))
        self.is_delete = True
        return self

    def eq(self, _column: str, _value: str) -> "FakeTableQuery":
        return self

    def execute(self) -> SimpleNamespace:
        if getattr(self, "is_delete", False):
            if self.client.raise_on_delete:
                raise RuntimeError("delete failed")
            return SimpleNamespace(data=[{"id": self.client.roadmap_id}])

        if self.table_name in self.client.raise_on_insert_tables:
            raise RuntimeError(f"{self.table_name} insert failed")

        if self.table_name == "career_roadmaps":
            payload = self.payload
            assert isinstance(payload, dict)
            return SimpleNamespace(
                data=[
                    {
                        **payload,
                        "id": self.client.roadmap_id,
                        "created_at": "2026-07-13T10:00:00Z",
                        "updated_at": "2026-07-13T10:00:00Z",
                    }
                ]
            )

        if self.table_name == "roadmap_steps":
            payload = self.payload
            assert isinstance(payload, list)
            return SimpleNamespace(
                data=[
                    {
                        **step,
                        "id": self.client.step_ids[index],
                        "status": "not_started",
                        "updated_at": "2026-07-13T10:00:00Z",
                    }
                    for index, step in enumerate(payload)
                ]
            )

        if self.table_name == "roadmap_tasks":
            payload = self.payload
            assert isinstance(payload, list)
            return SimpleNamespace(
                data=[
                    {
                        **task,
                        "id": str(uuid4()),
                        "updated_at": "2026-07-13T10:00:00Z",
                    }
                    for task in payload
                ]
            )

        raise AssertionError(f"Unexpected table {self.table_name}")


class FakeRoadmapClient:
    def __init__(
        self,
        raise_on_insert_tables: set[str] | None = None,
        raise_on_delete: bool = False,
    ) -> None:
        self.roadmap_id = str(uuid4())
        self.step_ids = [str(uuid4()) for _ in range(4)]
        self.raise_on_insert_tables = raise_on_insert_tables or set()
        self.raise_on_delete = raise_on_delete
        self.operations: list[tuple[str, object]] = []

    def table(self, table_name: str) -> FakeTableQuery:
        return FakeTableQuery(table_name, self)


def test_save_roadmap_persists_roadmap_and_steps(monkeypatch) -> None:
    analysis_id = str(uuid4())
    fake_client = FakeRoadmapClient()
    analysis = make_analysis_context(analysis_id)
    generated = CareerRoadmap.model_validate(make_roadmap_payload())
    monkeypatch.setattr(roadmap_service, "get_supabase_client", lambda: fake_client)

    result = roadmap_service.save_roadmap(
        user_id=OWNER_ID,
        analysis=analysis,
        roadmap=generated,
    )

    assert str(result.analysis_id) == analysis_id
    assert result.roadmap.duration_weeks == 4
    assert [operation[0] for operation in fake_client.operations] == [
        "career_roadmaps",
        "roadmap_steps",
        "roadmap_tasks",
    ]

    roadmap_payload = fake_client.operations[0][1]
    assert isinstance(roadmap_payload, dict)
    assert roadmap_payload["user_id"] == OWNER_ID
    assert roadmap_payload["analysis_id"] == analysis_id
    assert roadmap_payload["status"] == "active"

    step_payload = fake_client.operations[1][1]
    assert isinstance(step_payload, list)
    assert len(step_payload) == 4
    assert step_payload[0]["roadmap_id"] == fake_client.roadmap_id
    assert "analysis_id" not in step_payload[0]
    assert "user_id" not in step_payload[0]
    assert step_payload[0]["resources"] == [{"title": "Product Analytics Guide", "url": "https://example.com/analytics"}]

    task_payload = fake_client.operations[2][1]
    assert isinstance(task_payload, list)
    assert len(task_payload) == 12
    assert task_payload[0]["roadmap_id"] == fake_client.roadmap_id
    assert task_payload[0]["step_id"] == fake_client.step_ids[0]
    assert task_payload[0]["analysis_id"] == analysis_id
    assert task_payload[0]["user_id"] == OWNER_ID
    assert task_payload[0]["day_name"] == "Monday"
    assert task_payload[0]["task_order"] == 1
    assert task_payload[0]["status"] == "not_started"
    assert result.roadmap.steps[0].days[0].tasks[0].status == "not_started"


def test_save_roadmap_rolls_back_when_step_save_fails(monkeypatch) -> None:
    analysis_id = str(uuid4())
    fake_client = FakeRoadmapClient(raise_on_insert_tables={"roadmap_steps"})
    monkeypatch.setattr(roadmap_service, "get_supabase_client", lambda: fake_client)

    try:
        roadmap_service.save_roadmap(
            user_id=OWNER_ID,
            analysis=make_analysis_context(analysis_id),
            roadmap=CareerRoadmap.model_validate(make_roadmap_payload()),
        )
    except RuntimeError as exc:
        assert "Unable to save roadmap steps." in str(exc)
    else:
        raise AssertionError("Expected roadmap save to fail.")

    assert fake_client.operations[-1] == ("career_roadmaps", "delete")


def test_save_roadmap_rolls_back_when_task_save_fails(monkeypatch) -> None:
    analysis_id = str(uuid4())
    fake_client = FakeRoadmapClient(raise_on_insert_tables={"roadmap_tasks"})
    monkeypatch.setattr(roadmap_service, "get_supabase_client", lambda: fake_client)

    try:
        roadmap_service.save_roadmap(
            user_id=OWNER_ID,
            analysis=make_analysis_context(analysis_id),
            roadmap=CareerRoadmap.model_validate(make_roadmap_payload()),
        )
    except RuntimeError as exc:
        assert "Unable to save roadmap tasks." in str(exc)
    else:
        raise AssertionError("Expected roadmap save to fail.")

    assert fake_client.operations[-1] == ("career_roadmaps", "delete")


def test_save_roadmap_rollback_error_does_not_hide_original_error(monkeypatch) -> None:
    analysis_id = str(uuid4())
    fake_client = FakeRoadmapClient(
        raise_on_insert_tables={"roadmap_tasks"},
        raise_on_delete=True,
    )
    monkeypatch.setattr(roadmap_service, "get_supabase_client", lambda: fake_client)

    try:
        roadmap_service.save_roadmap(
            user_id=OWNER_ID,
            analysis=make_analysis_context(analysis_id),
            roadmap=CareerRoadmap.model_validate(make_roadmap_payload()),
        )
    except RuntimeError as exc:
        assert "Unable to save roadmap tasks." in str(exc)
    else:
        raise AssertionError("Expected roadmap save to fail.")

    assert fake_client.operations[-1] == ("career_roadmaps", "delete")


def test_get_active_roadmap_returns_none_and_deletes_incomplete_roadmap(monkeypatch) -> None:
    roadmap_id = str(uuid4())
    step_id = str(uuid4())
    deletes: list[str] = []

    monkeypatch.setattr(
        roadmap_service,
        "_load_steps",
        lambda _roadmap_id: [
            {
                "id": step_id,
                "week_number": 1,
                "title": "Week one",
                "description": "Description",
                "reason": "Reason",
                "estimated_hours": 3,
                "priority": "high",
                "status": "not_started",
                "resources": [],
                "mini_project": "Mini project",
                "updated_at": "2026-07-15T10:00:00Z",
            }
        ],
    )
    monkeypatch.setattr(roadmap_service, "load_tasks", lambda _roadmap_id: [])
    monkeypatch.setattr(roadmap_service, "delete_partial_roadmap", lambda roadmap_id: deletes.append(roadmap_id))

    class ActiveRoadmapQuery:
        def select(self, _columns: str) -> "ActiveRoadmapQuery":
            return self

        def eq(self, _column: str, _value: str) -> "ActiveRoadmapQuery":
            return self

        def order(self, _column: str, desc: bool) -> "ActiveRoadmapQuery":
            return self

        def limit(self, _count: int) -> "ActiveRoadmapQuery":
            return self

        def execute(self) -> SimpleNamespace:
            return SimpleNamespace(
                data=[
                    {
                        "id": roadmap_id,
                        "user_id": OWNER_ID,
                        "analysis_id": str(uuid4()),
                        "target_role": "Product Manager",
                        "duration_weeks": 4,
                        "summary": "Summary",
                        "status": "active",
                        "estimated_job_readiness_before": 60,
                        "estimated_job_readiness_after": 80,
                    }
                ]
            )

    class ActiveRoadmapClient:
        def table(self, table_name: str) -> ActiveRoadmapQuery:
            assert table_name == "career_roadmaps"
            return ActiveRoadmapQuery()

    monkeypatch.setattr(roadmap_service, "get_supabase_client", lambda: ActiveRoadmapClient())

    result = roadmap_service.get_active_roadmap(str(uuid4()), OWNER_ID)

    assert result is None
    assert deletes == [roadmap_id]


def test_get_active_roadmap_with_tasks_returns_roadmap(monkeypatch) -> None:
    roadmap_id = str(uuid4())
    step_ids = [str(uuid4()) for _ in range(4)]

    monkeypatch.setattr(
        roadmap_service,
        "_load_steps",
        lambda _roadmap_id: [
            {
                "id": step_id,
                "week_number": index + 1,
                "title": f"Week {index + 1}",
                "description": "Description",
                "reason": "Reason",
                "estimated_hours": 3,
                "priority": "high",
                "status": "not_started",
                "resources": [],
                "mini_project": "Mini project",
                "updated_at": "2026-07-15T10:00:00Z",
            }
            for index, step_id in enumerate(step_ids)
        ],
    )
    monkeypatch.setattr(
        roadmap_service,
        "load_tasks",
        lambda _roadmap_id: [
            {
                "id": str(uuid4()),
                "step_id": step_id,
                "roadmap_id": roadmap_id,
                "day_name": "Monday",
                "task_order": 1,
                "title": f"Do task {index + 1}",
                "estimated_minutes": 30,
                "status": "not_started",
                "updated_at": "2026-07-15T10:00:00Z",
            }
            for index, step_id in enumerate(step_ids)
        ],
    )

    class ActiveRoadmapQuery:
        def select(self, _columns: str) -> "ActiveRoadmapQuery":
            return self

        def eq(self, _column: str, _value: str) -> "ActiveRoadmapQuery":
            return self

        def order(self, _column: str, desc: bool) -> "ActiveRoadmapQuery":
            return self

        def limit(self, _count: int) -> "ActiveRoadmapQuery":
            return self

        def execute(self) -> SimpleNamespace:
            return SimpleNamespace(
                data=[
                    {
                        "id": roadmap_id,
                        "user_id": OWNER_ID,
                        "analysis_id": str(uuid4()),
                        "target_role": "Product Manager",
                        "duration_weeks": 4,
                        "summary": "Summary",
                        "status": "active",
                        "estimated_job_readiness_before": 60,
                        "estimated_job_readiness_after": 80,
                    }
                ]
            )

    class ActiveRoadmapClient:
        def table(self, table_name: str) -> ActiveRoadmapQuery:
            assert table_name == "career_roadmaps"
            return ActiveRoadmapQuery()

    monkeypatch.setattr(roadmap_service, "get_supabase_client", lambda: ActiveRoadmapClient())

    result = roadmap_service.get_active_roadmap(str(uuid4()), OWNER_ID)

    assert result is not None
    assert result.roadmap.steps[0].days[0].tasks[0].title == "Do task 1"
