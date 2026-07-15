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

from app.core.security import CurrentUser, get_current_user
from app.main import app
from app.schemas.roadmap import CareerRoadmap, RoadmapGenerateResponse
from app.services import roadmap_service


OWNER_ID = "11111111-1111-1111-1111-111111111111"


def override_current_user() -> CurrentUser:
    return CurrentUser(id=OWNER_ID, email="owner@example.com")


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
    assert fake_client.models.call["model"] == "gemini-2.5-flash"
    assert fake_client.models.model_calls == ["gemini-2.5-flash"]


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


class FakeTableQuery:
    def __init__(self, table_name: str, client: "FakeRoadmapClient") -> None:
        self.table_name = table_name
        self.client = client

    def insert(self, payload: object) -> "FakeTableQuery":
        self.client.operations.append((self.table_name, payload))
        self.payload = payload
        return self

    def execute(self) -> SimpleNamespace:
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
            return SimpleNamespace(data=payload)

        raise AssertionError(f"Unexpected table {self.table_name}")


class FakeRoadmapClient:
    def __init__(self) -> None:
        self.roadmap_id = str(uuid4())
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
