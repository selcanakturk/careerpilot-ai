from datetime import datetime
import logging

import httpx
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.job import ExternalJobPosting, JobSearchResponse
from app.services.jobs.providers.base import JobDiscoveryConfigurationError, TemporaryJobDiscoveryError


logger = logging.getLogger(__name__)

ADZUNA_API_BASE_URL = "https://api.adzuna.com/v1/api/jobs"
REQUEST_TIMEOUT_SECONDS = 12.0
MAX_ERROR_SUMMARY_CHARACTERS = 240
ADZUNA_FALLBACK_COUNTRY = "gb"
ADZUNA_SUPPORTED_COUNTRIES = {
    "au",
    "at",
    "be",
    "br",
    "ca",
    "de",
    "fr",
    "gb",
    "in",
    "it",
    "mx",
    "nl",
    "nz",
    "pl",
    "sg",
    "za",
    "us",
}


def _to_text(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _to_float(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)

    return None


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _normalize_employment_type(value: object) -> str | None:
    if not isinstance(value, str):
        return None

    normalized_value = value.lower().strip()

    if normalized_value in {"full_time", "full time", "permanent"}:
        return "full_time"

    if normalized_value in {"part_time", "part time"}:
        return "part_time"

    if normalized_value in {"internship", "intern"}:
        return "internship"

    if normalized_value in {"contract"}:
        return "contract"

    if normalized_value in {"freelance"}:
        return "freelance"

    return None


def _infer_work_mode(description: str, location: str | None) -> str | None:
    combined_text = f"{description} {location or ''}".lower()

    if "remote" in combined_text or "uzaktan" in combined_text:
        return "remote"

    if "hybrid" in combined_text or "hibrit" in combined_text:
        return "hybrid"

    if location:
        return "onsite"

    return None


def _normalize_job(raw_job: dict[str, object]) -> ExternalJobPosting | None:
    external_id = _to_text(raw_job.get("id"))
    title = _to_text(raw_job.get("title"))
    description = _to_text(raw_job.get("description"))
    source_url = _to_text(raw_job.get("redirect_url"))

    if not external_id or not title or not description or not source_url:
        return None

    company = raw_job.get("company")
    location = raw_job.get("location")
    category = raw_job.get("category")

    company_name = "Unknown company"
    location_name: str | None = None
    category_name: str | None = None

    if isinstance(company, dict):
        company_name = _to_text(company.get("display_name")) or company_name

    if isinstance(location, dict):
        location_name = _to_text(location.get("display_name"))

    if isinstance(category, dict):
        category_name = _to_text(category.get("label"))

    try:
        return ExternalJobPosting(
            external_id=external_id,
            source="adzuna",
            title=title,
            company_name=company_name,
            location=location_name,
            description=description,
            source_url=source_url,
            created_at=_parse_datetime(raw_job.get("created")),
            salary_min=_to_float(raw_job.get("salary_min")),
            salary_max=_to_float(raw_job.get("salary_max")),
            salary_currency=_to_text(raw_job.get("salary_currency")),
            employment_type=_normalize_employment_type(raw_job.get("contract_time")),
            work_mode=_infer_work_mode(description, location_name),
            category=category_name,
        )
    except ValidationError:
        logger.exception("Unable to normalize Adzuna job result.")
        return None


def _safe_error_body_summary(response: httpx.Response) -> dict[str, object]:
    try:
        payload = response.json()
    except ValueError:
        return {"body_preview": response.text[:MAX_ERROR_SUMMARY_CHARACTERS]}

    if not isinstance(payload, dict):
        return {"body_type": type(payload).__name__}

    summary: dict[str, object] = {"keys": sorted(payload.keys())}

    for key in ("status", "message", "error", "detail"):
        value = payload.get(key)

        if isinstance(value, str):
            summary[key] = value[:MAX_ERROR_SUMMARY_CHARACTERS]

    return summary


def _effective_country(country: str) -> str:
    normalized_country = country.strip().lower()

    if normalized_country in ADZUNA_SUPPORTED_COUNTRIES:
        return normalized_country

    logger.warning("Adzuna market fallback: %s", ADZUNA_FALLBACK_COUNTRY)
    return ADZUNA_FALLBACK_COUNTRY


class AdzunaJobProvider:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS)

    def search_jobs(
        self,
        query: str,
        location: str | None,
        page: int,
        results_per_page: int,
    ) -> JobSearchResponse:
        settings = get_settings()

        if not settings.adzuna_app_id or not settings.adzuna_app_key:
            raise JobDiscoveryConfigurationError("Adzuna credentials are missing.")

        try:
            country = _effective_country(settings.adzuna_country)
            url = f"{ADZUNA_API_BASE_URL}/{country}/search/{page}"
            logger.info(
                "Calling job provider.",
                extra={
                    "provider": "adzuna",
                    "url": url,
                    "query": query,
                    "has_location": bool(location),
                    "page": page,
                    "country": country,
                },
            )
            response = self._client.get(
                url,
                params={
                    "app_id": settings.adzuna_app_id,
                    "app_key": settings.adzuna_app_key,
                    "what": query,
                    "where": location,
                    "results_per_page": results_per_page,
                    "sort_by": "date",
                    "content-type": "application/json",
                },
            )
            logger.info(
                "Job provider HTTP response received.",
                extra={"provider": "adzuna", "status_code": getattr(response, "status_code", "unknown")},
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            logger.warning("Adzuna job search timed out.", extra={"provider": "adzuna"})
            raise TemporaryJobDiscoveryError("Job discovery provider timed out.") from exc
        except httpx.RequestError as exc:
            logger.warning(
                "Adzuna job search request failed: %s",
                type(exc).__name__,
                extra={"provider": "adzuna"},
            )
            raise TemporaryJobDiscoveryError("Job discovery provider request failed.") from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            error_summary = _safe_error_body_summary(exc.response)

            if status_code == 429 or status_code >= 500:
                logger.warning(
                    "Adzuna job search returned temporary status.",
                    extra={"provider": "adzuna", "status_code": status_code, "response_summary": error_summary},
                )
                raise TemporaryJobDiscoveryError("Job discovery provider is unavailable.") from exc

            logger.exception(
                "Adzuna job search returned non-retryable status.",
                extra={"provider": "adzuna", "status_code": status_code, "response_summary": error_summary},
            )
            raise RuntimeError("Unable to search jobs.") from exc

        payload = response.json()

        if not isinstance(payload, dict):
            raise RuntimeError("Unexpected job discovery response.")

        normalized_jobs: list[ExternalJobPosting] = []
        seen_external_ids: set[str] = set()

        results = payload.get("results")
        if isinstance(results, list):
            for raw_job in results:
                if not isinstance(raw_job, dict):
                    continue

                normalized_job = _normalize_job(raw_job)

                if normalized_job is None or normalized_job.external_id in seen_external_ids:
                    continue

                seen_external_ids.add(normalized_job.external_id)
                normalized_jobs.append(normalized_job)

        total_results = payload.get("count")

        return JobSearchResponse(
            jobs=normalized_jobs,
            page=page,
            results_per_page=results_per_page,
            total_results=total_results if isinstance(total_results, int) else None,
            query=query,
            location=location,
        )
