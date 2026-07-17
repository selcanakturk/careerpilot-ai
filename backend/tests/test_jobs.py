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


def test_discovery_service_uses_roadmap_before_analysis(monkeypatch) -> None:
    calls: list[tuple[str, str | None]] = []

    class FakeProvider:
        def search_jobs(self, query: str, location: str | None, page: int, results_per_page: int) -> dict[str, object]:
            calls.append((query, location))
            return {
                "jobs": [],
                "page": page,
                "results_per_page": results_per_page,
                "total_results": 0,
                "query": query,
                "location": location,
            }

    monkeypatch.setattr(job_service, "get_active_roadmap_target_role", lambda _user_id: "Product Manager")
    monkeypatch.setattr(job_service, "get_latest_analysis_target_role", lambda _user_id: "Data Analyst")
    monkeypatch.setattr(job_discovery_service, "search_all_providers", FakeProvider().search_jobs)

    result = job_discovery_service.discover_jobs(
        user_id=OWNER_ID,
        query=None,
        location=None,
        page=1,
        results_per_page=10,
    )

    assert calls == [("Product Manager", None)]
    assert result["query"] == "Product Manager"


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


def test_auto_mode_skips_unsupported_adzuna_country(monkeypatch) -> None:
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

    assert registrations == []


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

    assert [registration.name for registration in registrations] == ["jsearch", "jooble", "adzuna"]


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
            return {"data": [], "estimated_count": 0}

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
        "country": "tr",
        "language": "tr",
        "date_posted": "all",
    }


def test_jsearch_provider_uses_turkey_query_when_location_empty(monkeypatch) -> None:
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

    assert captured["params"]["query"] == "Software Engineer in Turkey"
    assert captured["params"]["language"] == "tr"


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
