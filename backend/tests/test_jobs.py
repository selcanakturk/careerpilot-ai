import os
from types import SimpleNamespace
from uuid import uuid4

import httpx

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-api-key")
os.environ.setdefault("OPENAI_MODEL", "gpt-5-mini")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-api-key")
os.environ.setdefault("GEMINI_MODEL", "gemini-2.5-flash")
os.environ.setdefault("JOOBLE_API_KEY", "test-jooble-key")
os.environ.setdefault("JSEARCH_API_KEY", "test-jsearch-key")

from fastapi.testclient import TestClient

from app.core.security import CurrentUser, get_current_user
from app.main import app
from app.schemas.job import ExternalJobPosting, JobMatchAIResult, JobSearchResponse
from app.services import career_profile_service
from app.services import job_service
from app.services import job_discovery_service
from app.services.ai import ai_service
from app.services.ai.providers.gemini_provider import TemporaryAIServiceError
from app.services.jobs.providers import adzuna_provider, jooble_provider, jsearch_provider
from app.services.jobs.providers.base import JobDiscoveryConfigurationError, TemporaryJobDiscoveryError
from app.services.jobs import job_aggregator, provider_registry


OWNER_ID = "11111111-1111-1111-1111-111111111111"


def override_current_user() -> CurrentUser:
    return CurrentUser(id=OWNER_ID, email="owner@example.com")


def make_job(job_id: str | None = None) -> dict[str, object]:
    return {
        "id": job_id or str(uuid4()),
        "user_id": OWNER_ID,
        "title": "Product Manager",
        "company_name": "Acme",
        "location": "Remote",
        "employment_type": "full_time",
        "work_mode": "remote",
        "source_url": "https://example.com/job",
        "description": "Own product discovery and analytics.",
        "status": "saved",
        "created_at": "2026-07-17T10:00:00Z",
        "updated_at": "2026-07-17T10:00:00Z",
    }


def make_analysis(analysis_id: str | None = None) -> dict[str, object]:
    return {
        "id": analysis_id or str(uuid4()),
        "user_id": OWNER_ID,
        "target_role": "Product Manager",
        "status": "completed",
        "overall_score": 82,
        "summary": "Strong PM profile.",
        "strengths": ["Roadmapping"],
        "weaknesses": ["Analytics depth"],
        "skill_gaps": ["SQL"],
        "cv_suggestions": ["Add metrics"],
    }


def make_match(job_id: str, analysis_id: str) -> dict[str, object]:
    return {
        "id": str(uuid4()),
        "user_id": OWNER_ID,
        "job_posting_id": job_id,
        "analysis_id": analysis_id,
        "match_score": 78,
        "summary": "Good fit with some analytics gaps.",
        "matched_skills": ["Roadmapping"],
        "missing_skills": ["SQL"],
        "strengths": ["Product discovery"],
        "risks": ["Analytics requirements"],
        "recommendations": ["Prepare one metrics story"],
        "application_readiness": "medium",
        "created_at": "2026-07-17T10:00:00Z",
        "updated_at": "2026-07-17T10:00:00Z",
    }


def make_external_job(
    external_id: str,
    source_url: str,
    description: str = "A product role.",
    title: str = "Product Manager",
    company_name: str = "Acme",
    location: str | None = "Remote",
    source: str = "jooble",
) -> ExternalJobPosting:
    return ExternalJobPosting(
        external_id=external_id,
        source=source,
        title=title,
        company_name=company_name,
        location=location,
        description=description,
        source_url=source_url,
    )


def test_create_job_posting_owner_returns_201(monkeypatch) -> None:
    monkeypatch.setattr(job_service, "create_job_posting", lambda **_kwargs: make_job())
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).post(
            "/api/jobs",
            json={
                "title": "Product Manager",
                "company_name": "Acme",
                "description": "Own product discovery.",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["title"] == "Product Manager"


def test_create_job_posting_empty_title_returns_422() -> None:
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).post(
            "/api/jobs",
            json={"title": " ", "company_name": "Acme", "description": "Description"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_list_job_postings_owner_returns_200(monkeypatch) -> None:
    monkeypatch.setattr(job_service, "list_job_postings", lambda **_kwargs: [make_job()])
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).get("/api/jobs")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_job_posting_not_found_returns_404(monkeypatch) -> None:
    monkeypatch.setattr(job_service, "get_job_posting", lambda **_kwargs: None)
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).get(f"/api/jobs/{uuid4()}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_generate_job_match_existing_match_skips_ai(monkeypatch) -> None:
    job_id = str(uuid4())
    analysis_id = str(uuid4())
    ai_called = False

    monkeypatch.setattr(job_service, "get_job_posting", lambda **_kwargs: make_job(job_id))
    monkeypatch.setattr(job_service, "get_completed_analysis", lambda **_kwargs: make_analysis(analysis_id))
    monkeypatch.setattr(job_service, "get_existing_job_match", lambda **_kwargs: make_match(job_id, analysis_id))

    def analyze_job_match(**_kwargs: object) -> JobMatchAIResult:
        nonlocal ai_called
        ai_called = True
        return JobMatchAIResult(
            match_score=1,
            summary="Unexpected",
            application_readiness="low",
        )

    monkeypatch.setattr(ai_service, "analyze_job_match", analyze_job_match)
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).post(f"/api/jobs/{job_id}/match/{analysis_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["match_score"] == 78
    assert ai_called is False


def test_generate_job_match_saves_ai_result(monkeypatch) -> None:
    job_id = str(uuid4())
    analysis_id = str(uuid4())
    saved_payloads: list[JobMatchAIResult] = []

    monkeypatch.setattr(job_service, "get_job_posting", lambda **_kwargs: make_job(job_id))
    monkeypatch.setattr(job_service, "get_completed_analysis", lambda **_kwargs: make_analysis(analysis_id))
    monkeypatch.setattr(job_service, "get_existing_job_match", lambda **_kwargs: None)
    monkeypatch.setattr(
        ai_service,
        "analyze_job_match",
        lambda **_kwargs: JobMatchAIResult(
            match_score=91,
            summary="Strong fit.",
            matched_skills=["Roadmapping"],
            missing_skills=["SQL"],
            strengths=["Discovery"],
            risks=["Analytics"],
            recommendations=["Add metrics"],
            application_readiness="high",
        ),
    )

    def save_job_match(**kwargs: object) -> dict[str, object]:
        result = kwargs["result"]
        assert isinstance(result, JobMatchAIResult)
        saved_payloads.append(result)
        return make_match(job_id, analysis_id) | {
            "match_score": result.match_score,
            "matched_skills": result.matched_skills,
            "missing_skills": result.missing_skills,
            "application_readiness": result.application_readiness,
        }

    monkeypatch.setattr(job_service, "save_job_match", save_job_match)
    monkeypatch.setattr(job_service, "mark_job_posting_analyzed", lambda **_kwargs: None)
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).post(f"/api/jobs/{job_id}/match/{analysis_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["match_score"] == 91
    assert response.json()["matched_skills"] == ["Roadmapping"]
    assert response.json()["missing_skills"] == ["SQL"]
    assert saved_payloads[0].application_readiness == "high"


def test_generate_job_match_temporary_ai_error_returns_503(monkeypatch) -> None:
    job_id = str(uuid4())
    analysis_id = str(uuid4())

    monkeypatch.setattr(job_service, "get_job_posting", lambda **_kwargs: make_job(job_id))
    monkeypatch.setattr(job_service, "get_completed_analysis", lambda **_kwargs: make_analysis(analysis_id))
    monkeypatch.setattr(job_service, "get_existing_job_match", lambda **_kwargs: None)
    monkeypatch.setattr(
        ai_service,
        "analyze_job_match",
        lambda **_kwargs: (_ for _ in ()).throw(TemporaryAIServiceError("busy")),
    )
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).post(f"/api/jobs/{job_id}/match/{analysis_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503


def test_generate_job_match_job_or_analysis_not_found_returns_404(monkeypatch) -> None:
    monkeypatch.setattr(job_service, "get_job_posting", lambda **_kwargs: None)
    monkeypatch.setattr(job_service, "get_completed_analysis", lambda **_kwargs: None)
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).post(f"/api/jobs/{uuid4()}/match/{uuid4()}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_jobs_auth_required() -> None:
    response = TestClient(app).get("/api/jobs")
    assert response.status_code == 401


def test_discover_jobs_query_calls_provider(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def discover_jobs(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {
            "jobs": [],
            "page": kwargs["page"],
            "results_per_page": kwargs["results_per_page"],
            "total_results": 0,
            "query": kwargs["query"],
            "location": kwargs["location"],
        }

    monkeypatch.setattr(job_discovery_service, "discover_jobs", discover_jobs)
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).get("/api/jobs/discover?query=Product%20Manager&location=Remote&page=2")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured["query"] == "Product Manager"
    assert captured["location"] == "Remote"
    assert captured["page"] == 2


def test_discover_jobs_target_role_required_returns_422(monkeypatch) -> None:
    monkeypatch.setattr(
        job_discovery_service,
        "discover_jobs",
        lambda **_kwargs: (_ for _ in ()).throw(job_discovery_service.TargetRoleRequiredError("missing")),
    )
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).get("/api/jobs/discover")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_discover_jobs_provider_temporary_error_returns_503(monkeypatch) -> None:
    monkeypatch.setattr(
        job_discovery_service,
        "discover_jobs",
        lambda **_kwargs: (_ for _ in ()).throw(TemporaryJobDiscoveryError("timeout")),
    )
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).get("/api/jobs/discover?query=Product")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"] == "The job discovery service is temporarily unavailable. Please try again shortly."


def test_discover_jobs_manual_provider_temporary_error_returns_empty_response(monkeypatch) -> None:
    monkeypatch.setattr(
        job_discovery_service,
        "search_all_providers",
        lambda **_kwargs: (_ for _ in ()).throw(TemporaryJobDiscoveryError("rate limited")),
    )

    result = job_discovery_service.discover_jobs(
        user_id=OWNER_ID,
        query=" Software Engineer ",
        location=None,
        page=1,
        results_per_page=10,
    )

    assert result.jobs == []
    assert result.total_results == 0
    assert result.profile_used is False
    assert result.resolved_query == "Software Engineer"
    assert result.queries_used == ["Software Engineer"]
    assert result.provider_unavailable is True


def test_discover_jobs_missing_config_returns_503(monkeypatch) -> None:
    monkeypatch.setattr(
        job_discovery_service,
        "discover_jobs",
        lambda **_kwargs: (_ for _ in ()).throw(JobDiscoveryConfigurationError("missing")),
    )
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).get("/api/jobs/discover?query=Product")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"] == "Job recommendations are not connected yet. You can still analyze a job manually."


def test_discovery_service_uses_explicit_query_without_career_profile(monkeypatch) -> None:
    calls: list[tuple[str, str | None]] = []
    profile_called = False
    multi_query_called = False

    class FakeProvider:
        def search_jobs(self, query: str, location: str | None, page: int, results_per_page: int) -> JobSearchResponse:
            calls.append((query, location))
            return JobSearchResponse(
                jobs=[make_external_job("manual-1", "https://example.com/manual")],
                page=page,
                results_per_page=results_per_page,
                total_results=0,
                query=query,
                location=location,
            )

    def get_latest_career_profile(_user_id: str) -> object:
        nonlocal profile_called
        profile_called = True
        raise AssertionError("Career profile should not be used for explicit queries.")

    def search_all_provider_queries(**_kwargs: object) -> JobSearchResponse:
        nonlocal multi_query_called
        multi_query_called = True
        raise AssertionError("Multi-query discovery should not be used for explicit queries.")

    monkeypatch.setattr(career_profile_service, "get_latest_career_profile", get_latest_career_profile)
    monkeypatch.setattr(job_discovery_service, "search_all_providers", FakeProvider().search_jobs)
    monkeypatch.setattr(job_discovery_service, "search_all_provider_queries", search_all_provider_queries)

    result = job_discovery_service.discover_jobs(
        user_id=OWNER_ID,
        query="Python Developer",
        location="Remote",
        page=1,
        results_per_page=10,
    )

    assert profile_called is False
    assert multi_query_called is False
    assert calls == [("Python Developer", "Remote")]
    assert len(result.jobs) == 1
    assert result.jobs[0].match_score is None
    assert result.jobs[0].matched_skills == []
    assert result.jobs[0].missing_skills == []
    assert result.jobs[0].match_reasons == []
    assert result.query == "Python Developer"
    assert result.location == "Remote"
    assert result.profile_used is False
    assert result.analysis_id is None
    assert result.resolved_query == "Python Developer"
    assert result.resolved_location == "Remote"
    assert result.career_profile is None
    assert result.queries_used == ["Python Developer"]


def test_discovery_service_uses_career_profile_when_query_empty(monkeypatch) -> None:
    captured: dict[str, object] = {}
    analysis_id = str(uuid4())

    def search_all_provider_queries(
        queries: list[str],
        location: str | None,
        page: int,
        results_per_page: int,
    ) -> JobSearchResponse:
        captured["queries"] = queries
        captured["location"] = location
        return JobSearchResponse(
            jobs=[],
            page=page,
            results_per_page=results_per_page,
            total_results=0,
            query=queries[0],
            location=location,
        )

    monkeypatch.setattr(
        career_profile_service,
        "get_latest_career_profile",
        lambda _user_id: career_profile_service.CareerProfile(
            user_id=OWNER_ID,
            analysis_id=analysis_id,
            primary_role="Backend Software Engineer",
            alternative_roles=[],
            experience_level="mid",
            skills=["API design", "Python backend development"],
            strengths=["API design", "Python backend development"],
            weaknesses=["Cloud deployment depth"],
            overall_score=84,
            preferred_locations=["Turkey"],
            remote_preference=None,
        ),
    )
    monkeypatch.setattr(job_discovery_service, "search_all_provider_queries", search_all_provider_queries)

    result = job_discovery_service.discover_jobs(
        user_id=OWNER_ID,
        query=None,
        location=None,
        page=1,
        results_per_page=10,
    )

    assert captured["queries"] == ["Backend Software Engineer", "Backend Developer", "Python Developer"]
    assert captured["location"] == "Turkey"
    assert result.profile_used is True
    assert str(result.analysis_id) == analysis_id
    assert result.resolved_query == "Backend Software Engineer"
    assert result.resolved_location == "Turkey"
    assert result.queries_used == ["Backend Software Engineer", "Backend Developer", "Python Developer"]
    assert result.career_profile is not None
    assert result.career_profile.primary_role == "Backend Software Engineer"
    assert result.career_profile.experience_level == "mid"
    assert result.career_profile.overall_score == 84
    assert result.career_profile.skills == ["API Design", "Python backend development"]
    assert result.career_profile.strengths == ["API design", "Python backend development"]
    assert result.career_profile.weaknesses == ["Cloud deployment depth"]


def test_discovery_service_scores_sorts_and_paginates_profile_results(monkeypatch) -> None:
    analysis_id = str(uuid4())

    def search_all_provider_queries(**_kwargs: object) -> JobSearchResponse:
        return JobSearchResponse(
            jobs=[
                make_external_job(
                    "low",
                    "https://example.com/low",
                    "General backend role.",
                    title="Backend Developer",
                ),
                make_external_job(
                    "high",
                    "https://example.com/high",
                    "Build Python services with FastAPI and PostgreSQL.",
                    title="Backend Software Engineer",
                ),
                make_external_job(
                    "medium",
                    "https://example.com/medium",
                    "Python APIs for internal tools.",
                    title="Python Developer",
                ),
            ],
            page=1,
            results_per_page=3,
            total_results=3,
            query="Backend Software Engineer",
            location="Turkey",
        )

    monkeypatch.setattr(
        career_profile_service,
        "get_latest_career_profile",
        lambda _user_id: career_profile_service.CareerProfile(
            user_id=OWNER_ID,
            analysis_id=analysis_id,
            primary_role="Backend Software Engineer",
            alternative_roles=["Python Developer"],
            experience_level="mid",
            skills=["Python", "FastAPI", "PostgreSQL"],
            strengths=["Python"],
            weaknesses=[],
            overall_score=84,
            preferred_locations=["Turkey"],
            remote_preference=None,
        ),
    )
    monkeypatch.setattr(job_discovery_service, "search_all_provider_queries", search_all_provider_queries)

    result = job_discovery_service.discover_jobs(
        user_id=OWNER_ID,
        query=None,
        location=None,
        page=1,
        results_per_page=2,
    )

    assert [job.external_id for job in result.jobs] == ["high", "medium"]
    assert result.jobs[0].match_score is not None
    assert result.jobs[0].match_score > (result.jobs[1].match_score or 0)
    assert result.jobs[0].matched_skills == ["Python", "FastAPI", "PostgreSQL"]
    assert result.jobs[0].match_reasons[:2] == [
        "This role matches your primary career goal.",
        "Your Python experience is relevant.",
    ]
    assert result.page == 1
    assert result.results_per_page == 2


def test_discovery_service_profile_provider_temporary_error_returns_empty_response(monkeypatch) -> None:
    analysis_id = str(uuid4())

    monkeypatch.setattr(
        career_profile_service,
        "get_latest_career_profile",
        lambda _user_id: career_profile_service.CareerProfile(
            user_id=OWNER_ID,
            analysis_id=analysis_id,
            primary_role="Backend Software Engineer",
            alternative_roles=["Python Developer"],
            experience_level="mid",
            skills=["Python"],
            strengths=["Python"],
            weaknesses=[],
            overall_score=84,
            preferred_locations=["Turkey"],
            remote_preference=None,
        ),
    )
    monkeypatch.setattr(
        job_discovery_service,
        "search_all_provider_queries",
        lambda **_kwargs: (_ for _ in ()).throw(TemporaryJobDiscoveryError("rate limited")),
    )

    result = job_discovery_service.discover_jobs(
        user_id=OWNER_ID,
        query=None,
        location=None,
        page=1,
        results_per_page=10,
    )

    assert result.jobs == []
    assert result.total_results == 0
    assert result.profile_used is True
    assert str(result.analysis_id) == analysis_id
    assert result.resolved_query == "Backend Software Engineer"
    assert result.resolved_location == "Turkey"
    assert result.provider_unavailable is True


def test_discovery_service_real_empty_result_is_not_provider_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        job_discovery_service,
        "search_all_providers",
        lambda **kwargs: JobSearchResponse(
            jobs=[],
            page=kwargs["page"],
            results_per_page=kwargs["results_per_page"],
            total_results=0,
            query=kwargs["query"],
            location=kwargs["location"],
        ),
    )

    result = job_discovery_service.discover_jobs(
        user_id=OWNER_ID,
        query="Software Engineer",
        location="Turkey",
        page=1,
        results_per_page=10,
    )

    assert result.jobs == []
    assert result.total_results == 0
    assert result.provider_unavailable is False


def test_discovery_service_manual_search_uses_selected_analysis_for_match(monkeypatch) -> None:
    analysis_id = str(uuid4())

    monkeypatch.setattr(
        career_profile_service,
        "get_career_profile_for_analysis",
        lambda **_kwargs: career_profile_service.CareerProfile(
            user_id=OWNER_ID,
            analysis_id=analysis_id,
            primary_role="Backend Developer",
            alternative_roles=[],
            experience_level="mid",
            skills=["Python", "FastAPI"],
            strengths=["Python"],
            weaknesses=[],
            overall_score=84,
            preferred_locations=["Turkey"],
            remote_preference=None,
        ),
    )
    monkeypatch.setattr(
        job_discovery_service,
        "search_all_providers",
        lambda **kwargs: JobSearchResponse(
            jobs=[
                make_external_job(
                    "python-job",
                    "https://example.com/python-job",
                    "Build APIs with Python and FastAPI.",
                    title="Software Engineer",
                )
            ],
            page=kwargs["page"],
            results_per_page=kwargs["results_per_page"],
            total_results=1,
            query=kwargs["query"],
            location=kwargs["location"],
        ),
    )

    result = job_discovery_service.discover_jobs(
        user_id=OWNER_ID,
        query="Software Engineer",
        location="Turkey",
        analysis_id=analysis_id,
        page=1,
        results_per_page=10,
    )

    assert result.profile_used is False
    assert str(result.analysis_id) == analysis_id
    assert result.jobs[0].matched_skills == ["Python", "FastAPI"]
    assert result.jobs[0].match_reasons


def test_discovery_service_selected_analysis_not_found_raises_before_provider(monkeypatch) -> None:
    provider_called = False

    def search_all_providers(**_kwargs: object) -> JobSearchResponse:
        nonlocal provider_called
        provider_called = True
        return JobSearchResponse(jobs=[], page=1, results_per_page=10, query="Software Engineer")

    monkeypatch.setattr(career_profile_service, "get_career_profile_for_analysis", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(job_discovery_service, "search_all_providers", search_all_providers)

    try:
        job_discovery_service.discover_jobs(
            user_id=OWNER_ID,
            query="Software Engineer",
            location=None,
            analysis_id=str(uuid4()),
            page=1,
            results_per_page=10,
        )
    except job_discovery_service.SelectedAnalysisNotFoundError:
        pass
    else:
        raise AssertionError("SelectedAnalysisNotFoundError was not raised.")

    assert provider_called is False


def test_list_completed_cv_options_returns_owner_items(monkeypatch) -> None:
    analysis_id = str(uuid4())
    upload_id = str(uuid4())

    monkeypatch.setattr(
        job_service,
        "list_completed_analysis_options",
        lambda **_kwargs: [
            {
                "upload_id": upload_id,
                "analysis_id": analysis_id,
                "filename": "selcan-backend-cv.pdf",
                "analyzed_at": "2026-07-17T10:00:00Z",
                "target_role": "Backend Developer",
                "overall_score": 84,
            }
        ],
    )
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).get("/api/jobs/cv-options")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["items"][0]["analysis_id"] == analysis_id
    assert response.json()["items"][0]["upload_id"] == upload_id


def test_discover_jobs_selected_analysis_not_found_returns_404(monkeypatch) -> None:
    monkeypatch.setattr(
        job_discovery_service,
        "discover_jobs",
        lambda **_kwargs: (_ for _ in ()).throw(
            job_discovery_service.SelectedAnalysisNotFoundError("missing")
        ),
    )
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        response = TestClient(app).get(f"/api/jobs/discover?query=Software&analysis_id={uuid4()}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Selected CV analysis not found."


def test_discovery_service_profile_missing_keeps_target_role_error(monkeypatch) -> None:
    provider_called = False

    def search_all_providers(**_kwargs: object) -> JobSearchResponse:
        nonlocal provider_called
        provider_called = True
        return JobSearchResponse(jobs=[], page=1, results_per_page=10, query="unused")

    monkeypatch.setattr(career_profile_service, "get_latest_career_profile", lambda _user_id: None)
    monkeypatch.setattr(job_discovery_service, "search_all_providers", search_all_providers)

    try:
        job_discovery_service.discover_jobs(
            user_id=OWNER_ID,
            query=None,
            location=None,
            page=1,
            results_per_page=10,
        )
    except job_discovery_service.TargetRoleRequiredError:
        pass
    else:
        raise AssertionError("TargetRoleRequiredError was not raised.")

    assert provider_called is False


def test_auto_mode_selects_only_configured_providers(monkeypatch) -> None:
    monkeypatch.setattr(
        provider_registry,
        "get_settings",
        lambda: SimpleNamespace(
            job_discovery_provider="auto",
            jsearch_api_key="",
            jooble_api_key="jooble-key",
            adzuna_app_id="",
            adzuna_app_key="",
            adzuna_country="gb",
        ),
    )

    registrations = provider_registry.select_provider_registrations()

    assert [registration.name for registration in registrations] == ["jooble"]


def test_auto_mode_keeps_configured_adzuna_with_market_fallback(monkeypatch) -> None:
    monkeypatch.setattr(
        provider_registry,
        "get_settings",
        lambda: SimpleNamespace(
            job_discovery_provider="auto",
            jsearch_api_key="",
            jooble_api_key="",
            adzuna_app_id="app",
            adzuna_app_key="key",
            adzuna_country="tr",
        ),
    )

    registrations = provider_registry.select_provider_registrations()

    assert [registration.name for registration in registrations] == ["adzuna"]
    assert registrations[0].supported_countries == ("gb",)


def test_explicit_adzuna_provider_option_still_works(monkeypatch) -> None:
    monkeypatch.setattr(
        provider_registry,
        "get_settings",
        lambda: SimpleNamespace(
            job_discovery_provider="adzuna",
            jsearch_api_key="",
            jooble_api_key="",
            adzuna_app_id="app",
            adzuna_app_key="key",
            adzuna_country="gb",
        ),
    )

    registrations = provider_registry.select_provider_registrations()

    assert len(registrations) == 1
    assert registrations[0].name == "adzuna"
    assert isinstance(registrations[0].provider, adzuna_provider.AdzunaJobProvider)


def test_explicit_jooble_without_key_raises_config(monkeypatch) -> None:
    monkeypatch.setattr(
        provider_registry,
        "get_settings",
        lambda: SimpleNamespace(
            job_discovery_provider="jooble",
            jsearch_api_key="",
            jooble_api_key="",
            adzuna_app_id="",
            adzuna_app_key="",
            adzuna_country="gb",
        ),
    )

    try:
        provider_registry.select_provider_registrations()
    except JobDiscoveryConfigurationError:
        return

    raise AssertionError("Expected JobDiscoveryConfigurationError")


def test_jsearch_has_highest_auto_priority(monkeypatch) -> None:
    monkeypatch.setattr(
        provider_registry,
        "get_settings",
        lambda: SimpleNamespace(
            job_discovery_provider="auto",
            jsearch_api_key="jsearch-key",
            jooble_api_key="jooble-key",
            adzuna_app_id="app",
            adzuna_app_key="key",
            adzuna_country="gb",
        ),
    )

    registrations = provider_registry.select_provider_registrations()

    assert [registration.name for registration in registrations] == ["jsearch", "adzuna", "jooble"]


def test_explicit_jsearch_uses_configured_fallback_providers(monkeypatch) -> None:
    monkeypatch.setattr(
        provider_registry,
        "get_settings",
        lambda: SimpleNamespace(
            job_discovery_provider="jsearch",
            jsearch_api_key="jsearch-key",
            jooble_api_key="jooble-key",
            adzuna_app_id="app",
            adzuna_app_key="key",
            adzuna_country="gb",
        ),
    )

    registrations = provider_registry.select_provider_registrations()

    assert [registration.name for registration in registrations] == ["jsearch", "adzuna", "jooble"]


def test_explicit_jooble_keeps_selected_provider_when_no_lower_priority_fallback_exists(monkeypatch) -> None:
    monkeypatch.setattr(
        provider_registry,
        "get_settings",
        lambda: SimpleNamespace(
            job_discovery_provider="jooble",
            jsearch_api_key="jsearch-key",
            jooble_api_key="jooble-key",
            adzuna_app_id="app",
            adzuna_app_key="key",
            adzuna_country="gb",
        ),
    )

    registrations = provider_registry.select_provider_registrations()

    assert [registration.name for registration in registrations] == ["jooble"]


def test_explicit_jsearch_without_key_raises_config(monkeypatch) -> None:
    monkeypatch.setattr(
        provider_registry,
        "get_settings",
        lambda: SimpleNamespace(
            job_discovery_provider="jsearch",
            jsearch_api_key="",
            jooble_api_key="",
            adzuna_app_id="",
            adzuna_app_key="",
            adzuna_country="gb",
        ),
    )

    try:
        provider_registry.select_provider_registrations()
    except JobDiscoveryConfigurationError:
        return

    raise AssertionError("Expected JobDiscoveryConfigurationError")


def test_aggregator_one_provider_fail_one_success_returns_success(monkeypatch) -> None:
    class FailingProvider:
        def search_jobs(self, **_kwargs: object) -> JobSearchResponse:
            raise TemporaryJobDiscoveryError("temporary")

    class SuccessfulProvider:
        def search_jobs(self, query: str, location: str | None, page: int, results_per_page: int) -> JobSearchResponse:
            return JobSearchResponse(
                jobs=[make_external_job("success-1", "https://example.com/success")],
                page=page,
                results_per_page=results_per_page,
                total_results=1,
                query=query,
                location=location,
                providers_used=["adzuna"],
            )

    monkeypatch.setattr(
        job_aggregator,
        "select_provider_registrations",
        lambda: [
            provider_registry.ProviderRegistration("jooble", FailingProvider(), True, 10, ("tr",)),
            provider_registry.ProviderRegistration("adzuna", SuccessfulProvider(), True, 20, ("gb",)),
        ],
    )

    result = job_aggregator.search_all_providers("Product", None, 1, 10)

    assert len(result.jobs) == 1
    assert result.providers_used == ["adzuna"]
    assert result.providers_failed == ["jooble"]


def test_aggregator_jsearch_429_falls_back_to_adzuna_and_stops(monkeypatch) -> None:
    calls: list[str] = []

    class RateLimitedProvider:
        def search_jobs(self, **_kwargs: object) -> JobSearchResponse:
            calls.append("jsearch")
            raise TemporaryJobDiscoveryError("rate limit")

    class SuccessfulProvider:
        def search_jobs(self, query: str, location: str | None, page: int, results_per_page: int) -> JobSearchResponse:
            calls.append("adzuna")
            return JobSearchResponse(
                jobs=[make_external_job("adzuna-1", "https://example.com/adzuna", source="adzuna")],
                page=page,
                results_per_page=results_per_page,
                total_results=1,
                query=query,
                location=location,
            )

    class ShouldNotRunProvider:
        def search_jobs(self, **_kwargs: object) -> JobSearchResponse:
            calls.append("jooble")
            return JobSearchResponse(jobs=[], page=1, results_per_page=10, query="unused")

    monkeypatch.setattr(
        job_aggregator,
        "select_provider_registrations",
        lambda: [
            provider_registry.ProviderRegistration("jsearch", RateLimitedProvider(), True, 5, ("tr",)),
            provider_registry.ProviderRegistration("adzuna", SuccessfulProvider(), True, 10, ("gb",)),
            provider_registry.ProviderRegistration("jooble", ShouldNotRunProvider(), True, 20, ("tr",)),
        ],
    )

    result = job_aggregator.search_all_providers("Backend Developer", "Turkey", 1, 10)

    assert calls == ["jsearch", "adzuna"]
    assert result.providers_used == ["adzuna"]
    assert result.providers_failed == ["jsearch"]
    assert len(result.jobs) == 1
    assert result.jobs[0].source == "adzuna"


def test_aggregator_adzuna_failure_falls_back_to_jooble(monkeypatch) -> None:
    calls: list[str] = []

    class FailingProvider:
        def __init__(self, name: str) -> None:
            self.name = name

        def search_jobs(self, **_kwargs: object) -> JobSearchResponse:
            calls.append(self.name)
            raise TemporaryJobDiscoveryError("temporary")

    class JoobleProvider:
        def search_jobs(self, query: str, location: str | None, page: int, results_per_page: int) -> JobSearchResponse:
            calls.append("jooble")
            return JobSearchResponse(
                jobs=[make_external_job("jooble-1", "https://example.com/jooble", source="jooble")],
                page=page,
                results_per_page=results_per_page,
                total_results=1,
                query=query,
                location=location,
            )

    monkeypatch.setattr(
        job_aggregator,
        "select_provider_registrations",
        lambda: [
            provider_registry.ProviderRegistration("jsearch", FailingProvider("jsearch"), True, 5, ("tr",)),
            provider_registry.ProviderRegistration("adzuna", FailingProvider("adzuna"), True, 10, ("gb",)),
            provider_registry.ProviderRegistration("jooble", JoobleProvider(), True, 20, ("tr",)),
        ],
    )

    result = job_aggregator.search_all_providers("Backend Developer", "Turkey", 1, 10)

    assert calls == ["jsearch", "adzuna", "jooble"]
    assert result.providers_used == ["jooble"]
    assert result.providers_failed == ["jsearch", "adzuna"]
    assert len(result.jobs) == 1


def test_aggregator_empty_success_continues_to_next_provider(monkeypatch) -> None:
    calls: list[str] = []

    class EmptyProvider:
        def search_jobs(self, query: str, location: str | None, page: int, results_per_page: int) -> JobSearchResponse:
            calls.append("jsearch")
            return JobSearchResponse(
                jobs=[],
                page=page,
                results_per_page=results_per_page,
                total_results=0,
                query=query,
                location=location,
            )

    class SuccessfulProvider:
        def search_jobs(self, query: str, location: str | None, page: int, results_per_page: int) -> JobSearchResponse:
            calls.append("adzuna")
            return JobSearchResponse(
                jobs=[make_external_job("adzuna-1", "https://example.com/adzuna", source="adzuna")],
                page=page,
                results_per_page=results_per_page,
                total_results=1,
                query=query,
                location=location,
            )

    monkeypatch.setattr(
        job_aggregator,
        "select_provider_registrations",
        lambda: [
            provider_registry.ProviderRegistration("jsearch", EmptyProvider(), True, 5, ("tr",)),
            provider_registry.ProviderRegistration("adzuna", SuccessfulProvider(), True, 10, ("gb",)),
        ],
    )

    result = job_aggregator.search_all_providers("Backend Developer", "Turkey", 1, 10)

    assert calls == ["jsearch", "adzuna"]
    assert result.providers_used == ["adzuna"]
    assert len(result.jobs) == 1


def test_aggregator_all_successful_providers_empty_returns_available_empty_response(monkeypatch) -> None:
    class EmptyProvider:
        def search_jobs(self, query: str, location: str | None, page: int, results_per_page: int) -> JobSearchResponse:
            return JobSearchResponse(
                jobs=[],
                page=page,
                results_per_page=results_per_page,
                total_results=0,
                query=query,
                location=location,
            )

    monkeypatch.setattr(
        job_aggregator,
        "select_provider_registrations",
        lambda: [
            provider_registry.ProviderRegistration("jsearch", EmptyProvider(), True, 5, ("tr",)),
            provider_registry.ProviderRegistration("adzuna", EmptyProvider(), True, 10, ("gb",)),
        ],
    )

    result = job_aggregator.search_all_providers("Backend Developer", "Turkey", 1, 10)

    assert result.jobs == []
    assert result.providers_used == ["jsearch", "adzuna"]
    assert result.providers_failed == []


def test_aggregator_all_providers_fail_returns_temporary(monkeypatch) -> None:
    class FailingProvider:
        def search_jobs(self, **_kwargs: object) -> JobSearchResponse:
            raise TemporaryJobDiscoveryError("temporary")

    monkeypatch.setattr(
        job_aggregator,
        "select_provider_registrations",
        lambda: [
            provider_registry.ProviderRegistration("jooble", FailingProvider(), True, 10, ("tr",)),
        ],
    )

    try:
        job_aggregator.search_all_providers("Product", None, 1, 10)
    except TemporaryJobDiscoveryError:
        return

    raise AssertionError("Expected TemporaryJobDiscoveryError")


def test_aggregator_deduplicates_by_source_url_and_keeps_longest_description(monkeypatch) -> None:
    class DuplicateProvider:
        def search_jobs(self, query: str, location: str | None, page: int, results_per_page: int) -> JobSearchResponse:
            return JobSearchResponse(
                jobs=[
                    make_external_job("short", "https://example.com/same", "Short."),
                    make_external_job("long", "https://example.com/same", "This is a much longer description."),
                ],
                page=page,
                results_per_page=results_per_page,
                total_results=2,
                query=query,
                location=location,
            )

    monkeypatch.setattr(
        job_aggregator,
        "select_provider_registrations",
        lambda: [provider_registry.ProviderRegistration("jooble", DuplicateProvider(), True, 10, ("tr",))],
    )

    result = job_aggregator.search_all_providers("Product", None, 1, 10)

    assert len(result.jobs) == 1
    assert result.jobs[0].external_id == "long"


def test_aggregator_deduplicates_by_title_company_location(monkeypatch) -> None:
    class DuplicateProvider:
        def search_jobs(self, query: str, location: str | None, page: int, results_per_page: int) -> JobSearchResponse:
            first_job = make_external_job(
                "first",
                "",
                "Short.",
                title="Product Manager",
                company_name="Acme",
                location="Istanbul",
            )
            second_job = make_external_job(
                "second",
                "",
                "Longer duplicate description.",
                title=" product   manager ",
                company_name="ACME",
                location=" istanbul ",
            )
            return JobSearchResponse(
                jobs=[first_job, second_job],
                page=page,
                results_per_page=results_per_page,
                total_results=2,
                query=query,
                location=location,
            )

    monkeypatch.setattr(
        job_aggregator,
        "select_provider_registrations",
        lambda: [provider_registry.ProviderRegistration("jooble", DuplicateProvider(), True, 10, ("tr",))],
    )

    result = job_aggregator.search_all_providers("Product", None, 1, 10)

    assert len(result.jobs) == 1
    assert result.jobs[0].external_id == "second"


def test_aggregator_searches_each_query_and_deduplicates_preserving_query_order(monkeypatch) -> None:
    calls: list[str] = []

    class MultiQueryProvider:
        def search_jobs(self, query: str, location: str | None, page: int, results_per_page: int) -> JobSearchResponse:
            calls.append(query)

            if query == "Backend Software Engineer":
                jobs = [
                    make_external_job(
                        "primary-1",
                        "https://example.com/primary",
                        "Primary role match.",
                        title="Backend Software Engineer",
                    ),
                    make_external_job(
                        "duplicate-short",
                        "https://example.com/duplicate",
                        "Short.",
                        title="Backend Developer",
                    ),
                ]
            elif query == "Backend Developer":
                jobs = [
                    make_external_job(
                        "duplicate-long",
                        "https://example.com/duplicate",
                        "Longer duplicate description for the same posting.",
                        title="Backend Developer",
                    ),
                    make_external_job(
                        "alternative-1",
                        "https://example.com/alternative",
                        "Alternative role match.",
                        title="Backend Platform Developer",
                    ),
                ]
            else:
                jobs = [make_external_job("python-1", "https://example.com/python", title="Python Developer")]

            return JobSearchResponse(
                jobs=jobs,
                page=page,
                results_per_page=results_per_page,
                total_results=len(jobs),
                query=query,
                location=location,
            )

    monkeypatch.setattr(
        job_aggregator,
        "select_provider_registrations",
        lambda: [provider_registry.ProviderRegistration("jooble", MultiQueryProvider(), True, 10, ("tr",))],
    )

    result = job_aggregator.search_all_provider_queries(
        queries=["Backend Software Engineer", "Backend Developer", "Python Developer"],
        location="Turkey",
        page=1,
        results_per_page=10,
    )

    assert calls == ["Backend Software Engineer", "Backend Developer", "Python Developer"]
    assert [job.external_id for job in result.jobs] == [
        "primary-1",
        "duplicate-long",
        "alternative-1",
        "python-1",
    ]
    assert result.query == "Backend Software Engineer"
    assert result.location == "Turkey"
    assert result.total_results == 5
    assert result.providers_used == ["jooble"]


def test_jooble_provider_posts_query_and_empty_location(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"jobs": [], "totalCount": 0}

    class FakeClient:
        def post(self, url: str, json: dict[str, object]) -> FakeResponse:
            captured["url"] = url
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr(
        jooble_provider,
        "get_settings",
        lambda: SimpleNamespace(jooble_api_key="secret-key"),
    )

    jooble_provider.JoobleJobProvider(client=FakeClient()).search_jobs(
        query="Software Engineer",
        location=None,
        page=2,
        results_per_page=10,
    )

    assert captured["url"] == "https://jooble.org/api/secret-key"
    assert captured["json"] == {"keywords": "Software Engineer", "location": "", "page": 2}


def test_jsearch_provider_gets_endpoint_with_headers_and_location_query(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "data": {
                    "jobs": [
                        {
                            "job_id": "endpoint-1",
                            "job_title": "Software Engineer",
                            "employer_name": "Acme",
                            "job_description": "Build APIs.",
                            "job_apply_link": "https://example.com/endpoint-1",
                        }
                    ]
                },
                "estimated_count": 1,
            }

    class FakeClient:
        def get(self, url: str, headers: dict[str, str], params: dict[str, object]) -> FakeResponse:
            captured["url"] = url
            captured["headers"] = headers
            captured["params"] = params
            return FakeResponse()

    monkeypatch.setattr(
        jsearch_provider,
        "get_settings",
        lambda: SimpleNamespace(jsearch_api_key="rapid-key", jsearch_api_host="jsearch.p.rapidapi.com"),
    )

    jsearch_provider.JSearchJobProvider(client=FakeClient()).search_jobs(
        query="Software Engineer",
        location="Istanbul",
        page=1,
        results_per_page=10,
    )

    assert captured["url"] == "https://jsearch.p.rapidapi.com/search-v2"
    assert captured["headers"] == {
        "X-RapidAPI-Key": "rapid-key",
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    }
    assert captured["params"] == {
        "query": "Software Engineer in Istanbul, Turkey",
        "date_posted": "all",
    }


def test_jsearch_provider_uses_plain_role_query_when_location_empty(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"data": []}

    class FakeClient:
        def get(self, *_args: object, **kwargs: object) -> FakeResponse:
            captured["params"] = kwargs["params"]
            return FakeResponse()

    monkeypatch.setattr(
        jsearch_provider,
        "get_settings",
        lambda: SimpleNamespace(jsearch_api_key="rapid-key", jsearch_api_host="jsearch.p.rapidapi.com"),
    )

    jsearch_provider.JSearchJobProvider(client=FakeClient()).search_jobs("Software Engineer", None, 1, 10)

    assert captured["params"]["query"] == "Software Engineer"
    assert "language" not in captured["params"]
    assert "country" not in captured["params"]


def test_jsearch_provider_does_not_duplicate_turkey_in_location(monkeypatch) -> None:
    captured_params: list[dict[str, object]] = []

    class FakeResponse:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "data": {
                    "jobs": [
                        {
                            "job_id": "location-1",
                            "job_title": "Backend Developer",
                            "employer_name": "Acme",
                            "job_description": "Build APIs.",
                            "job_apply_link": "https://example.com/location-1",
                        }
                    ]
                }
            }

    class FakeClient:
        def get(self, *_args: object, **kwargs: object) -> FakeResponse:
            captured_params.append(kwargs["params"])
            return FakeResponse()

    monkeypatch.setattr(
        jsearch_provider,
        "get_settings",
        lambda: SimpleNamespace(jsearch_api_key="rapid-key", jsearch_api_host="jsearch.p.rapidapi.com"),
    )

    provider = jsearch_provider.JSearchJobProvider(client=FakeClient())
    provider.search_jobs("Backend Developer", "Turkey", 1, 10)

    assert captured_params[-1]["query"] == "Backend Developer in Turkey"

    provider.search_jobs("Backend Developer", "Istanbul, Turkey", 1, 10)

    assert captured_params[-1]["query"] == "Backend Developer in Istanbul, Turkey"


def test_jsearch_provider_falls_back_to_broader_query_when_location_query_is_empty(monkeypatch) -> None:
    captured_params: list[dict[str, object]] = []

    class FakeResponse:
        status_code = 200

        def __init__(self, payload: dict[str, object]) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return self._payload

    class FakeClient:
        def get(self, *_args: object, **kwargs: object) -> FakeResponse:
            captured_params.append(kwargs["params"])

            if len(captured_params) == 1:
                return FakeResponse({"data": {"jobs": []}})

            return FakeResponse(
                {
                    "data": {
                        "jobs": [
                            {
                                "job_id": "broad-1",
                                "job_title": "Software Engineer",
                                "employer_name": "Acme",
                                "job_description": "Build backend APIs.",
                                "job_apply_link": "https://example.com/broad-1",
                            }
                        ]
                    }
                }
            )

    monkeypatch.setattr(
        jsearch_provider,
        "get_settings",
        lambda: SimpleNamespace(jsearch_api_key="rapid-key", jsearch_api_host="jsearch.p.rapidapi.com"),
    )

    result = jsearch_provider.JSearchJobProvider(client=FakeClient()).search_jobs(
        "Software Engineer",
        "Turkey",
        1,
        10,
    )

    assert [params["query"] for params in captured_params] == ["Software Engineer in Turkey", "Software Engineer"]
    assert len(result.jobs) == 1


def test_jsearch_provider_page_after_first_does_not_call_upstream(monkeypatch) -> None:
    class FakeClient:
        def get(self, *_args: object, **_kwargs: object) -> object:
            raise AssertionError("JSearch cursor pagination is not wired yet.")

    monkeypatch.setattr(
        jsearch_provider,
        "get_settings",
        lambda: SimpleNamespace(jsearch_api_key="rapid-key", jsearch_api_host="jsearch.p.rapidapi.com"),
    )

    result = jsearch_provider.JSearchJobProvider(client=FakeClient()).search_jobs("Software Engineer", None, 2, 10)

    assert result.jobs == []
    assert result.page == 2


def test_jsearch_provider_normalizes_apply_options_and_remote(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            job = {
                "job_id": "jsearch-1",
                "job_title": "Backend Developer",
                "employer_name": "Acme",
                "job_city": "Istanbul",
                "job_country": "TR",
                "job_description": "Build APIs.",
                "job_apply_link": "ftp://invalid.example.com",
                "job_google_link": "https://google.example.com/job",
                "job_posted_at_datetime_utc": "2026-07-17T10:00:00Z",
                "job_min_salary": 1000,
                "job_max_salary": 2000,
                "job_salary_currency": "TRY",
                "job_employment_type": "FULLTIME",
                "job_is_remote": True,
                "job_publisher": "Company career page",
                "apply_options": [
                    {"apply_link": "javascript:alert(1)"},
                    {"apply_link": "https://company.example.com/apply"},
                ],
            }
            duplicate = {**job}
            missing_url = {**job, "job_id": "bad", "job_apply_link": None, "apply_options": [], "job_google_link": None}
            return {"data": [job, duplicate, missing_url], "estimated_count": 3}

    class FakeClient:
        def get(self, *_args: object, **_kwargs: object) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr(
        jsearch_provider,
        "get_settings",
        lambda: SimpleNamespace(jsearch_api_key="rapid-key", jsearch_api_host="jsearch.p.rapidapi.com"),
    )

    result = jsearch_provider.JSearchJobProvider(client=FakeClient()).search_jobs("Developer", None, 1, 10)

    assert len(result.jobs) == 1
    assert result.jobs[0].source == "jsearch"
    assert result.jobs[0].source_url == "https://company.example.com/apply"
    assert result.jobs[0].work_mode == "remote"
    assert result.jobs[0].employment_type == "full_time"


def test_jsearch_provider_reads_jobs_fallback_field(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "jobs": [
                    {
                        "job_id": "jobs-1",
                        "job_title": "Yazılım Mühendisi",
                        "employer_name": "Acme",
                        "job_description": "Backend services.",
                        "job_apply_link": "https://example.com/jobs-1",
                    }
                ]
            }

    class FakeClient:
        def get(self, *_args: object, **_kwargs: object) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr(
        jsearch_provider,
        "get_settings",
        lambda: SimpleNamespace(jsearch_api_key="rapid-key", jsearch_api_host="jsearch.p.rapidapi.com"),
    )

    result = jsearch_provider.JSearchJobProvider(client=FakeClient()).search_jobs("Yazılım Mühendisi", None, 1, 10)

    assert len(result.jobs) == 1
    assert result.jobs[0].title == "Yazılım Mühendisi"


def test_jsearch_provider_reads_nested_data_jobs_and_cursor(monkeypatch, caplog) -> None:
    class FakeResponse:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "status": "OK",
                "data": {
                    "cursor": "next-page-token",
                    "jobs": [
                        {
                            "job_id": "nested-1",
                            "job_title": "Backend Software Engineer",
                            "employer_name": "Acme",
                            "job_description": "Build backend systems.",
                            "job_apply_link": "https://example.com/nested-1",
                        }
                    ],
                },
            }

    class FakeClient:
        def get(self, *_args: object, **_kwargs: object) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr(
        jsearch_provider,
        "get_settings",
        lambda: SimpleNamespace(jsearch_api_key="rapid-key", jsearch_api_host="jsearch.p.rapidapi.com"),
    )

    with caplog.at_level("INFO"):
        result = jsearch_provider.JSearchJobProvider(client=FakeClient()).search_jobs(
            "Software Engineer",
            "Istanbul",
            1,
            10,
        )

    assert len(result.jobs) == 1
    assert result.jobs[0].external_id == "nested-1"
    assert "JSearch status: 200" in caplog.text
    assert "Jobs returned: 1" in caplog.text
    assert "Cursor: present" in caplog.text
    assert "First title: Backend Software Engineer" in caplog.text
    assert "received=1, normalized=1, discarded=0" in caplog.text


def test_jsearch_provider_reads_results_fallback_field(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "results": [
                    {
                        "job_id": "results-1",
                        "job_title": "Software Engineer",
                        "employer_name": "Acme",
                        "job_description": "Backend services.",
                        "job_apply_link": "https://example.com/results-1",
                    }
                ]
            }

    class FakeClient:
        def get(self, *_args: object, **_kwargs: object) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr(
        jsearch_provider,
        "get_settings",
        lambda: SimpleNamespace(jsearch_api_key="rapid-key", jsearch_api_host="jsearch.p.rapidapi.com"),
    )

    result = jsearch_provider.JSearchJobProvider(client=FakeClient()).search_jobs("Software Engineer", None, 1, 10)

    assert len(result.jobs) == 1
    assert result.jobs[0].external_id == "results-1"


def test_jsearch_provider_empty_data_returns_empty_result(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"status": "OK", "data": []}

    class FakeClient:
        def get(self, *_args: object, **_kwargs: object) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr(
        jsearch_provider,
        "get_settings",
        lambda: SimpleNamespace(jsearch_api_key="rapid-key", jsearch_api_host="jsearch.p.rapidapi.com"),
    )

    result = jsearch_provider.JSearchJobProvider(client=FakeClient()).search_jobs("Software Engineer", None, 1, 10)

    assert result.jobs == []


def test_jsearch_provider_diagnostic_log_excludes_api_key_and_description(monkeypatch, caplog) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "status": "OK",
                "data": [
                    {
                        "job_id": "safe-log",
                        "job_title": "Software Engineer",
                        "employer_name": "Acme",
                        "job_description": "Sensitive description should not be logged.",
                        "job_apply_link": "https://example.com/safe-log",
                    }
                ],
            }

    class FakeClient:
        def get(self, *_args: object, **_kwargs: object) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr(
        jsearch_provider,
        "get_settings",
        lambda: SimpleNamespace(jsearch_api_key="rapid-secret-key", jsearch_api_host="jsearch.p.rapidapi.com"),
    )

    with caplog.at_level("INFO"):
        jsearch_provider.JSearchJobProvider(client=FakeClient()).search_jobs("Software Engineer", None, 1, 10)

    log_output = caplog.text

    assert "rapid-secret-key" not in log_output
    assert "Sensitive description" not in log_output
    assert "raw_jobs=1" in log_output
    assert "normalized_jobs=1" in log_output


def test_jsearch_provider_missing_key_raises(monkeypatch) -> None:
    monkeypatch.setattr(
        jsearch_provider,
        "get_settings",
        lambda: SimpleNamespace(jsearch_api_key="", jsearch_api_host="jsearch.p.rapidapi.com"),
    )

    try:
        jsearch_provider.JSearchJobProvider(client=object()).search_jobs("Product", None, 1, 10)
    except JobDiscoveryConfigurationError:
        return

    raise AssertionError("Expected JobDiscoveryConfigurationError")


def test_jsearch_provider_timeout_raises_temporary(monkeypatch) -> None:
    class FakeClient:
        def get(self, *_args: object, **_kwargs: object) -> object:
            raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(
        jsearch_provider,
        "get_settings",
        lambda: SimpleNamespace(jsearch_api_key="rapid-key", jsearch_api_host="jsearch.p.rapidapi.com"),
    )

    try:
        jsearch_provider.JSearchJobProvider(client=FakeClient()).search_jobs("Product", None, 1, 10)
    except TemporaryJobDiscoveryError:
        return

    raise AssertionError("Expected TemporaryJobDiscoveryError")


def test_jsearch_provider_429_raises_temporary(monkeypatch) -> None:
    request = httpx.Request("GET", "https://jsearch.p.rapidapi.com/search-v2")
    response = httpx.Response(429, request=request)

    class FakeClient:
        def get(self, *_args: object, **_kwargs: object) -> object:
            raise httpx.HTTPStatusError("too many requests", request=request, response=response)

    monkeypatch.setattr(
        jsearch_provider,
        "get_settings",
        lambda: SimpleNamespace(jsearch_api_key="rapid-key", jsearch_api_host="jsearch.p.rapidapi.com"),
    )

    try:
        jsearch_provider.JSearchJobProvider(client=FakeClient()).search_jobs("Product", None, 1, 10)
    except TemporaryJobDiscoveryError:
        return

    raise AssertionError("Expected TemporaryJobDiscoveryError")


def test_jsearch_provider_5xx_raises_temporary(monkeypatch) -> None:
    request = httpx.Request("GET", "https://jsearch.p.rapidapi.com/search-v2")
    response = httpx.Response(500, request=request)

    class FakeClient:
        def get(self, *_args: object, **_kwargs: object) -> object:
            raise httpx.HTTPStatusError("server error", request=request, response=response)

    monkeypatch.setattr(
        jsearch_provider,
        "get_settings",
        lambda: SimpleNamespace(jsearch_api_key="rapid-key", jsearch_api_host="jsearch.p.rapidapi.com"),
    )

    try:
        jsearch_provider.JSearchJobProvider(client=FakeClient()).search_jobs("Product", None, 1, 10)
    except TemporaryJobDiscoveryError:
        return

    raise AssertionError("Expected TemporaryJobDiscoveryError")


def test_jsearch_provider_invalid_key_raises_config(monkeypatch) -> None:
    request = httpx.Request("GET", "https://jsearch.p.rapidapi.com/search-v2")
    response = httpx.Response(403, request=request)

    class FakeClient:
        def get(self, *_args: object, **_kwargs: object) -> object:
            raise httpx.HTTPStatusError("forbidden", request=request, response=response)

    monkeypatch.setattr(
        jsearch_provider,
        "get_settings",
        lambda: SimpleNamespace(jsearch_api_key="rapid-key", jsearch_api_host="jsearch.p.rapidapi.com"),
    )

    try:
        jsearch_provider.JSearchJobProvider(client=FakeClient()).search_jobs("Product", None, 1, 10)
    except JobDiscoveryConfigurationError:
        return

    raise AssertionError("Expected JobDiscoveryConfigurationError")


def test_jsearch_provider_404_raises_temporary(monkeypatch) -> None:
    request = httpx.Request("GET", "https://jsearch.p.rapidapi.com/search-v2")
    response = httpx.Response(404, request=request)

    class FakeClient:
        def get(self, *_args: object, **_kwargs: object) -> object:
            raise httpx.HTTPStatusError("not found", request=request, response=response)

    monkeypatch.setattr(
        jsearch_provider,
        "get_settings",
        lambda: SimpleNamespace(jsearch_api_key="rapid-key", jsearch_api_host="jsearch.p.rapidapi.com"),
    )

    try:
        jsearch_provider.JSearchJobProvider(client=FakeClient()).search_jobs("Product", None, 1, 10)
    except TemporaryJobDiscoveryError:
        return

    raise AssertionError("Expected TemporaryJobDiscoveryError")


def test_jooble_provider_normalizes_and_deduplicates(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            job = {
                "id": "jooble-1",
                "title": "Software Engineer",
                "company": "Acme",
                "location": "Istanbul",
                "snippet": "Remote backend role.",
                "link": "https://example.com/jooble-job",
                "updated": "2026-07-17T10:00:00Z",
                "type": "full time",
                "source": "Jooble",
            }
            missing_url = {
                "id": "bad",
                "title": "Bad job",
                "company": "Acme",
                "snippet": "No link",
            }
            duplicate_url = {**job, "id": "jooble-2"}
            return {"jobs": [job, job, duplicate_url, missing_url], "totalCount": 4}

    class FakeClient:
        def post(self, *_args: object, **_kwargs: object) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr(
        jooble_provider,
        "get_settings",
        lambda: SimpleNamespace(jooble_api_key="secret-key"),
    )

    result = jooble_provider.JoobleJobProvider(client=FakeClient()).search_jobs(
        query="Software Engineer",
        location="Istanbul",
        page=1,
        results_per_page=10,
    )

    assert len(result.jobs) == 1
    assert result.jobs[0].source == "jooble"
    assert result.jobs[0].external_id == "jooble-1"
    assert result.jobs[0].employment_type == "full_time"
    assert result.jobs[0].work_mode == "remote"


def test_jooble_provider_missing_key_raises(monkeypatch) -> None:
    monkeypatch.setattr(
        jooble_provider,
        "get_settings",
        lambda: SimpleNamespace(jooble_api_key=""),
    )

    try:
        jooble_provider.JoobleJobProvider(client=object()).search_jobs("Product", None, 1, 10)
    except JobDiscoveryConfigurationError:
        return

    raise AssertionError("Expected JobDiscoveryConfigurationError")


def test_jooble_provider_timeout_raises_temporary(monkeypatch) -> None:
    class FakeClient:
        def post(self, *_args: object, **_kwargs: object) -> object:
            raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(
        jooble_provider,
        "get_settings",
        lambda: SimpleNamespace(jooble_api_key="secret-key"),
    )

    try:
        jooble_provider.JoobleJobProvider(client=FakeClient()).search_jobs("Product", None, 1, 10)
    except TemporaryJobDiscoveryError:
        return

    raise AssertionError("Expected TemporaryJobDiscoveryError")


def test_jooble_provider_429_raises_temporary(monkeypatch) -> None:
    request = httpx.Request("POST", "https://jooble.org/api/redacted")
    response = httpx.Response(429, request=request)

    class FakeClient:
        def post(self, *_args: object, **_kwargs: object) -> object:
            raise httpx.HTTPStatusError("too many requests", request=request, response=response)

    monkeypatch.setattr(
        jooble_provider,
        "get_settings",
        lambda: SimpleNamespace(jooble_api_key="secret-key"),
    )

    try:
        jooble_provider.JoobleJobProvider(client=FakeClient()).search_jobs("Product", None, 1, 10)
    except TemporaryJobDiscoveryError:
        return

    raise AssertionError("Expected TemporaryJobDiscoveryError")


def test_jooble_provider_invalid_key_raises_configuration(monkeypatch) -> None:
    request = httpx.Request("POST", "https://jooble.org/api/redacted")
    response = httpx.Response(401, request=request)

    class FakeClient:
        def post(self, *_args: object, **_kwargs: object) -> object:
            raise httpx.HTTPStatusError("unauthorized", request=request, response=response)

    monkeypatch.setattr(
        jooble_provider,
        "get_settings",
        lambda: SimpleNamespace(jooble_api_key="secret-key"),
    )

    try:
        jooble_provider.JoobleJobProvider(client=FakeClient()).search_jobs("Product", None, 1, 10)
    except JobDiscoveryConfigurationError:
        return

    raise AssertionError("Expected JobDiscoveryConfigurationError")


def test_adzuna_provider_normalizes_and_deduplicates(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            job = {
                "id": "external-1",
                "title": "Product Manager",
                "description": "Remote product analytics role.",
                "redirect_url": "https://example.com/job",
                "created": "2026-07-17T10:00:00Z",
                "company": {"display_name": "Acme"},
                "location": {"display_name": "Istanbul"},
                "category": {"label": "IT Jobs"},
                "contract_time": "full_time",
                "salary_min": 1000,
                "salary_max": 2000,
            }
            return {"results": [job, job], "count": 2}

    class FakeClient:
        def get(self, *_args: object, **_kwargs: object) -> FakeResponse:
            return FakeResponse()

    monkeypatch.setattr(
        adzuna_provider,
        "get_settings",
        lambda: SimpleNamespace(adzuna_app_id="app", adzuna_app_key="key", adzuna_country="tr"),
    )

    result = adzuna_provider.AdzunaJobProvider(client=FakeClient()).search_jobs(
        query="Product",
        location=None,
        page=1,
        results_per_page=10,
    )

    assert len(result.jobs) == 1
    assert result.jobs[0].external_id == "external-1"
    assert result.jobs[0].work_mode == "remote"


def test_adzuna_provider_uses_gb_market_when_country_unsupported(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"results": [], "count": 0}

    class FakeClient:
        def get(self, url: str, params: dict[str, object]) -> FakeResponse:
            captured["url"] = url
            captured["params"] = params
            return FakeResponse()

    monkeypatch.setattr(
        adzuna_provider,
        "get_settings",
        lambda: SimpleNamespace(adzuna_app_id="app", adzuna_app_key="key", adzuna_country="tr"),
    )

    result = adzuna_provider.AdzunaJobProvider(client=FakeClient()).search_jobs(
        query="Software Engineer",
        location="Turkey",
        page=1,
        results_per_page=10,
    )

    assert captured["url"] == "https://api.adzuna.com/v1/api/jobs/gb/search/1"
    assert captured["params"]["what"] == "Software Engineer"
    assert captured["params"]["where"] == "Turkey"
    assert result.jobs == []


def test_adzuna_provider_missing_config_raises(monkeypatch) -> None:
    monkeypatch.setattr(
        adzuna_provider,
        "get_settings",
        lambda: SimpleNamespace(adzuna_app_id="", adzuna_app_key="", adzuna_country="tr"),
    )

    try:
        adzuna_provider.AdzunaJobProvider(client=object()).search_jobs("Product", None, 1, 10)
    except JobDiscoveryConfigurationError:
        return

    raise AssertionError("Expected JobDiscoveryConfigurationError")
