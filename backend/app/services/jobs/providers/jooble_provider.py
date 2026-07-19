from datetime import datetime
from hashlib import sha256
import logging
from typing import Any

import httpx
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.job import ExternalJobPosting, JobSearchResponse
from app.services.jobs.providers.base import JobDiscoveryConfigurationError, TemporaryJobDiscoveryError


logger = logging.getLogger(__name__)

JOOBLE_API_BASE_URL = "https://jooble.org/api"
REQUEST_TIMEOUT_SECONDS = 12.0
MAX_ERROR_SUMMARY_CHARACTERS = 240


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


def _stable_external_id(raw_job: dict[str, Any], source_url: str) -> str:
    raw_id = _to_text(raw_job.get("id"))

    if raw_id:
        return raw_id

    return sha256(source_url.encode("utf-8")).hexdigest()


def _normalize_employment_type(value: object) -> str | None:
    if not isinstance(value, str):
        return None

    normalized_value = value.lower().strip()

    if any(marker in normalized_value for marker in ("full", "tam zaman")):
        return "full_time"

    if any(marker in normalized_value for marker in ("part", "yarı zaman")):
        return "part_time"

    if any(marker in normalized_value for marker in ("intern", "staj")):
        return "internship"

    if "contract" in normalized_value or "sözleş" in normalized_value:
        return "contract"

    if "freelance" in normalized_value:
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


def _normalize_job(raw_job: dict[str, Any]) -> ExternalJobPosting | None:
    source_url = _to_text(raw_job.get("link"))
    title = _to_text(raw_job.get("title"))
    description = _to_text(raw_job.get("snippet")) or _to_text(raw_job.get("description"))

    if not source_url or not title or not description:
        return None

    company_name = _to_text(raw_job.get("company")) or "Unknown company"
    location = _to_text(raw_job.get("location"))
    employment_type = _normalize_employment_type(raw_job.get("type"))
    salary = _to_text(raw_job.get("salary"))

    try:
        return ExternalJobPosting(
            external_id=_stable_external_id(raw_job, source_url),
            source="jooble",
            title=title,
            company_name=company_name,
            location=location,
            description=description,
            source_url=source_url,
            created_at=_parse_datetime(raw_job.get("updated")),
            salary_min=_to_float(raw_job.get("salary_min")),
            salary_max=_to_float(raw_job.get("salary_max")),
            salary_currency="TRY" if salary else None,
            employment_type=employment_type,
            work_mode=_infer_work_mode(description, location),
            category=_to_text(raw_job.get("source")) or _to_text(raw_job.get("category")),
        )
    except ValidationError:
        logger.exception("Unable to normalize Jooble job result.")
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


class JoobleJobProvider:
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

        if not settings.jooble_api_key:
            raise JobDiscoveryConfigurationError("Jooble API key is missing.")

        try:
            logger.info(
                "Calling job provider.",
                extra={
                    "provider": "jooble",
                    "url": JOOBLE_API_BASE_URL,
                    "query": query,
                    "has_location": bool(location),
                    "page": page,
                },
            )
            response = self._client.post(
                f"{JOOBLE_API_BASE_URL}/{settings.jooble_api_key}",
                json={
                    "keywords": query,
                    "location": location or "",
                    "page": page,
                },
            )
            logger.info(
                "Job provider HTTP response received.",
                extra={"provider": "jooble", "status_code": getattr(response, "status_code", "unknown")},
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            logger.warning("Jooble job search timed out.", extra={"provider": "jooble", "url": JOOBLE_API_BASE_URL})
            raise TemporaryJobDiscoveryError("Job discovery provider timed out.") from exc
        except httpx.RequestError as exc:
            logger.warning(
                "Jooble job search request failed: %s",
                type(exc).__name__,
                extra={"provider": "jooble", "url": JOOBLE_API_BASE_URL},
            )
            raise TemporaryJobDiscoveryError("Job discovery provider request failed.") from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            error_summary = _safe_error_body_summary(exc.response)

            if status_code in {401, 403}:
                logger.warning(
                    "Jooble job search credentials were rejected.",
                    extra={"provider": "jooble", "status_code": status_code, "response_summary": error_summary},
                )
                raise JobDiscoveryConfigurationError("Jooble API key is invalid.") from exc

            if status_code == 429 or status_code >= 500:
                logger.warning(
                    "Jooble job search returned temporary status.",
                    extra={"provider": "jooble", "status_code": status_code, "response_summary": error_summary},
                )
                raise TemporaryJobDiscoveryError("Job discovery provider is unavailable.") from exc

            logger.error(
                "Jooble job search returned non-retryable status.",
                extra={"provider": "jooble", "status_code": status_code, "response_summary": error_summary},
            )
            raise RuntimeError("Unable to search jobs.") from exc

        payload = response.json()

        if not isinstance(payload, dict):
            raise RuntimeError("Unexpected job discovery response.")

        normalized_jobs: list[ExternalJobPosting] = []
        seen_external_ids: set[str] = set()
        seen_source_urls: set[str] = set()

        jobs = payload.get("jobs")
        if isinstance(jobs, list):
            for raw_job in jobs:
                if not isinstance(raw_job, dict):
                    continue

                normalized_job = _normalize_job(raw_job)

                if normalized_job is None:
                    continue

                if normalized_job.external_id in seen_external_ids or normalized_job.source_url in seen_source_urls:
                    continue

                seen_external_ids.add(normalized_job.external_id)
                seen_source_urls.add(normalized_job.source_url)
                normalized_jobs.append(normalized_job)

        total_results = payload.get("totalCount") or payload.get("total_count")

        return JobSearchResponse(
            jobs=normalized_jobs,
            page=page,
            results_per_page=results_per_page,
            total_results=total_results if isinstance(total_results, int) else None,
            query=query,
            location=location,
        )
