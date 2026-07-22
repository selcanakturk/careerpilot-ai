import os

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-api-key")
os.environ.setdefault("GEMINI_MODEL", "gemini-2.5-flash")

from fastapi.testclient import TestClient

from app.core.security import CurrentUser, get_current_user
from app.main import app
from app.schemas.cv_optimizer import CVOptimizerResult
from app.services import cv_optimizer_service


OWNER_ID = "11111111-1111-1111-1111-111111111111"

VALID_OPTIMIZER_JSON = """
{
  "match_before": 76,
  "estimated_match_after": 89,
  "changes": [
    "Highlighted backend API experience.",
    "Reordered Python and REST API skills."
  ],
  "optimized_cv": {
    "headline": "Backend Developer",
    "summary": "Backend developer with Python API experience.",
    "skills": ["Python", "REST API"],
    "experience": [],
    "projects": [],
    "education": [],
    "certifications": [],
    "additional_sections": {}
  }
}
""".strip()


class FakeGeminiResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeGeminiModels:
    def __init__(
        self,
        response_text: str = VALID_OPTIMIZER_JSON,
        failures: list[Exception] | None = None,
    ) -> None:
        self._response_text = response_text
        self._failures = failures or []
        self.model_calls: list[str] = []
        self.generate_call: dict[str, object] | None = None

    def generate_content(self, **kwargs: object) -> FakeGeminiResponse:
        self.generate_call = kwargs
        self.model_calls.append(str(kwargs["model"]))

        if self._failures:
            raise self._failures.pop(0)

        return FakeGeminiResponse(self._response_text)


class FakeGeminiClient:
    def __init__(self, models: FakeGeminiModels) -> None:
        self.models = models


def override_current_user() -> CurrentUser:
    return CurrentUser(id=OWNER_ID, email="owner@example.com")


def test_optimize_cv_success(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def optimize_cv_for_job(**kwargs: object) -> CVOptimizerResult:
        captured.update(kwargs)
        return CVOptimizerResult(
            match_before=76,
            estimated_match_after=89,
            changes=[
                "Reordered backend API experience near the top.",
                "Strengthened ATS wording for Python and REST API work.",
            ],
            optimized_cv={
                "headline": "Backend Developer",
                "summary": "Backend developer with Python API experience.",
                "skills": ["Python", "REST API"],
                "experience": [],
            },
        )

    monkeypatch.setattr(cv_optimizer_service, "optimize_cv_for_job", optimize_cv_for_job)
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).post(
            "/api/cv/optimize",
            json={
                "analysis_id": "analysis-1",
                "job_external_id": "job-1",
                "provider": "jooble",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured == {
        "user_id": OWNER_ID,
        "analysis_id": "analysis-1",
        "job_external_id": "job-1",
        "provider": "jooble",
    }
    assert response.json()["match_before"] == 76
    assert response.json()["estimated_match_after"] == 89
    assert response.json()["optimized_cv"]["headline"] == "Backend Developer"


def test_optimize_cv_invalid_analysis_returns_404(monkeypatch) -> None:
    monkeypatch.setattr(
        cv_optimizer_service,
        "optimize_cv_for_job",
        lambda **_kwargs: (_ for _ in ()).throw(
            cv_optimizer_service.CVOptimizerInputNotFoundError("analysis missing")
        ),
    )
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).post(
            "/api/cv/optimize",
            json={
                "analysis_id": "missing-analysis",
                "job_external_id": "job-1",
                "provider": "jooble",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "The CV analysis or job posting could not be found."


def test_optimize_cv_invalid_job_external_id_returns_404(monkeypatch) -> None:
    monkeypatch.setattr(
        cv_optimizer_service,
        "optimize_cv_for_job",
        lambda **_kwargs: (_ for _ in ()).throw(
            cv_optimizer_service.CVOptimizerInputNotFoundError("job missing")
        ),
    )
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).post(
            "/api/cv/optimize",
            json={
                "analysis_id": "analysis-1",
                "job_external_id": "missing-job",
                "provider": "adzuna",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_optimize_cv_ai_failure_returns_502(monkeypatch) -> None:
    monkeypatch.setattr(
        cv_optimizer_service,
        "optimize_cv_for_job",
        lambda **_kwargs: (_ for _ in ()).throw(
            cv_optimizer_service.CVOptimizerAIError("provider failed")
        ),
    )
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).post(
            "/api/cv/optimize",
            json={
                "analysis_id": "analysis-1",
                "job_external_id": "job-1",
                "provider": "jsearch",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json()["detail"] == "Unable to optimize CV right now."


def test_optimize_with_gemini_valid_structured_response_returns_result(monkeypatch) -> None:
    models = FakeGeminiModels()
    monkeypatch.setattr(
        cv_optimizer_service,
        "get_gemini_client",
        lambda: FakeGeminiClient(models),
    )

    result = cv_optimizer_service._optimize_with_gemini(
        cv_text="Built Python APIs and REST services.",
        analysis={
            "target_role": "Backend Developer",
            "overall_score": 76,
            "summary": "Backend API profile.",
            "strengths": ["Python"],
            "weaknesses": [],
            "skill_gaps": ["Cloud deployment"],
            "cv_suggestions": ["Highlight API work."],
        },
        job_posting={
            "title": "Backend Developer",
            "company_name": "Acme",
            "location": "Istanbul",
            "employment_type": "full_time",
            "work_mode": "remote",
            "description": "Python and REST API role.",
        },
    )

    assert result.match_before == 76
    assert result.estimated_match_after == 89
    assert result.optimized_cv.headline == "Backend Developer"
    assert result.optimized_cv.projects == []
    assert result.optimized_cv.education == []
    assert models.generate_call is not None
    assert models.generate_call["model"] == "gemini-2.5-flash"
    assert models.model_calls == ["gemini-2.5-flash"]


def test_optimize_with_gemini_primary_unavailable_uses_fallback(monkeypatch) -> None:
    models = FakeGeminiModels(
        failures=[
            Exception("503 UNAVAILABLE high demand"),
            Exception("503 UNAVAILABLE high demand"),
        ]
    )
    monkeypatch.setattr(
        cv_optimizer_service,
        "get_gemini_client",
        lambda: FakeGeminiClient(models),
    )
    monkeypatch.setattr(cv_optimizer_service, "_sleep_before_retry", lambda _attempt: None)

    result = cv_optimizer_service._optimize_with_gemini(
        cv_text="Built Python APIs.",
        analysis={"target_role": "Backend Developer"},
        job_posting={"title": "Backend Developer", "description": "Python role."},
    )

    assert result.estimated_match_after == 89
    assert models.model_calls == [
        "gemini-2.5-flash",
        "gemini-2.5-flash",
        "gemini-3.1-flash-lite",
    ]


def test_optimize_with_gemini_invalid_structured_response_raises_safe_error(monkeypatch) -> None:
    models = FakeGeminiModels(response_text='{"match_before": 76}')
    monkeypatch.setattr(
        cv_optimizer_service,
        "get_gemini_client",
        lambda: FakeGeminiClient(models),
    )

    try:
        cv_optimizer_service._optimize_with_gemini(
            cv_text="Built Python APIs.",
            analysis={"target_role": "Backend Developer"},
            job_posting={"title": "Backend Developer", "description": "Python role."},
        )
    except cv_optimizer_service.CVOptimizerAIError as exc:
        assert "validated" in str(exc)
    else:
        raise AssertionError("Expected CVOptimizerAIError")


def test_optimize_with_gemini_empty_optimized_cv_raises_safe_error(monkeypatch) -> None:
    models = FakeGeminiModels(
        response_text="""
        {
          "match_before": 76,
          "estimated_match_after": 89,
          "changes": [],
          "optimized_cv": {}
        }
        """.strip()
    )
    monkeypatch.setattr(
        cv_optimizer_service,
        "get_gemini_client",
        lambda: FakeGeminiClient(models),
    )

    try:
        cv_optimizer_service._optimize_with_gemini(
            cv_text="Built Python APIs.",
            analysis={"target_role": "Backend Developer"},
            job_posting={"title": "Backend Developer", "description": "Python role."},
        )
    except cv_optimizer_service.CVOptimizerAIError as exc:
        assert "validated" in str(exc)
    else:
        raise AssertionError("Expected CVOptimizerAIError")


def test_gemini_optimizer_schema_requires_core_cv_sections() -> None:
    optimized_cv_schema = cv_optimizer_service.build_gemini_cv_optimizer_schema()["properties"][
        "optimized_cv"
    ]

    assert optimized_cv_schema["required"] == [
        "headline",
        "summary",
        "experience",
        "projects",
        "skills",
        "education",
        "certifications",
        "additional_sections",
    ]


def test_resolve_match_before_uses_existing_job_match_score(monkeypatch) -> None:
    monkeypatch.setattr(
        cv_optimizer_service,
        "_get_saved_job_posting_by_source_url",
        lambda _source_url, _user_id: {"id": "saved-job-1"},
    )
    monkeypatch.setattr(
        cv_optimizer_service,
        "_get_existing_job_match_score",
        lambda **_kwargs: 10,
    )
    monkeypatch.setattr(
        cv_optimizer_service,
        "_calculate_deterministic_match_before",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("fallback should not be used")),
    )

    score = cv_optimizer_service._resolve_match_before(
        analysis={"id": "analysis-1"},
        user_id=OWNER_ID,
        job_posting={"source_url": "https://example.com/job"},
    )

    assert score == 10


def test_apply_backend_match_scores_overrides_ai_score_and_clamps_estimate() -> None:
    result = CVOptimizerResult.model_validate_json(
        """
        {
          "match_before": 45,
          "estimated_match_after": 8,
          "changes": [],
          "optimized_cv": {
            "headline": "Backend Developer",
            "summary": "",
            "experience": [],
            "projects": [],
            "skills": [],
            "education": [],
            "certifications": [],
            "additional_sections": {}
          }
        }
        """.strip()
    )

    updated_result = cv_optimizer_service._apply_backend_match_scores(result, 10)

    assert updated_result.match_before == 10
    assert updated_result.estimated_match_after == 10


def test_optimize_cv_for_job_overrides_gemini_match_before_with_existing_score(monkeypatch) -> None:
    monkeypatch.setattr(
        cv_optimizer_service,
        "_get_completed_analysis",
        lambda **_kwargs: {"id": "analysis-1", "cv_upload_id": "upload-1"},
    )
    monkeypatch.setattr(
        cv_optimizer_service,
        "_get_cv_upload",
        lambda *_args, **_kwargs: {"id": "upload-1", "file_path": "user/cv.pdf", "file_type": "application/pdf"},
    )
    monkeypatch.setattr(
        cv_optimizer_service,
        "_find_external_job",
        lambda **_kwargs: {
            "external_id": "job-1",
            "provider": "jooble",
            "title": "Backend Developer",
            "description": "Python role.",
            "source_url": "https://example.com/job",
        },
    )
    monkeypatch.setattr(cv_optimizer_service, "_extract_cv_text", lambda _upload: "Built Python APIs.")
    monkeypatch.setattr(cv_optimizer_service, "_resolve_match_before", lambda **_kwargs: 10)
    monkeypatch.setattr(
        cv_optimizer_service,
        "_optimize_with_gemini",
        lambda **_kwargs: CVOptimizerResult(
            match_before=45,
            estimated_match_after=89,
            changes=["Improved ATS keywords."],
            optimized_cv={
                "headline": "Backend Developer",
                "summary": "Python backend developer.",
                "experience": [],
                "projects": [],
                "skills": ["Python"],
                "education": [],
                "certifications": [],
                "additional_sections": {},
            },
        ),
    )

    result = cv_optimizer_service.optimize_cv_for_job(
        user_id=OWNER_ID,
        analysis_id="analysis-1",
        job_external_id="job-1",
        provider="jooble",
    )

    assert result.match_before == 10
    assert result.estimated_match_after == 89


def test_optimize_with_gemini_temporary_failures_raise_safe_error(monkeypatch) -> None:
    models = FakeGeminiModels(
        failures=[
            Exception("429 RESOURCE_EXHAUSTED"),
            Exception("429 RESOURCE_EXHAUSTED"),
            Exception("429 RESOURCE_EXHAUSTED"),
            Exception("429 RESOURCE_EXHAUSTED"),
            Exception("429 RESOURCE_EXHAUSTED"),
            Exception("429 RESOURCE_EXHAUSTED"),
            Exception("429 RESOURCE_EXHAUSTED"),
            Exception("429 RESOURCE_EXHAUSTED"),
        ]
    )
    monkeypatch.setattr(
        cv_optimizer_service,
        "get_gemini_client",
        lambda: FakeGeminiClient(models),
    )
    monkeypatch.setattr(cv_optimizer_service, "_sleep_before_retry", lambda _attempt: None)

    try:
        cv_optimizer_service._optimize_with_gemini(
            cv_text="Built Python APIs.",
            analysis={"target_role": "Backend Developer"},
            job_posting={"title": "Backend Developer", "description": "Python role."},
        )
    except cv_optimizer_service.CVOptimizerAIError as exc:
        assert "temporarily" in str(exc)
    else:
        raise AssertionError("Expected CVOptimizerAIError")
