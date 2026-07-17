from datetime import datetime
from hashlib import sha256
import logging
from typing import Any
from urllib.parse import urlparse

import httpx
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.job import ExternalJobPosting, JobSearchResponse
from app.services.jobs.providers.base import JobDiscoveryConfigurationError, TemporaryJobDiscoveryError


logger = logging.getLogger(__name__)

JSEARCH_API_URL = "https://jsearch.p.rapidapi.com/search-v2"
REQUEST_TIMEOUT_SECONDS = 12.0


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


def _is_safe_url(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False

    parsed_url = urlparse(value)
    return parsed_url.scheme in {"http", "https"} and bool(parsed_url.netloc)


def _select_apply_url(raw_job: dict[str, Any]) -> str | None:
    preferred_url = raw_job.get("job_apply_link")

    if _is_safe_url(preferred_url):
        return str(preferred_url)

    apply_options = raw_job.get("apply_options")

    if isinstance(apply_options, list):
        for option in apply_options:
            if not isinstance(option, dict):
                continue

            option_url = option.get("apply_link")

            if _is_safe_url(option_url):
                return str(option_url)

    google_url = raw_job.get("job_google_link")

    if _is_safe_url(google_url):
        return str(google_url)

    return None


def _stable_external_id(raw_job: dict[str, Any], source_url: str) -> str:
    raw_id = _to_text(raw_job.get("job_id"))

    if raw_id:
        return raw_id

    return sha256(source_url.encode("utf-8")).hexdigest()


def _build_search_query(query: str, location: str | None) -> str:
    normalized_query = query.strip()
    normalized_location = location.strip() if location and location.strip() else ""

    if normalized_location:
        return f"{normalized_query} in {normalized_location}, Turkey"

    return f"{normalized_query} in Turkey"


def _normalize_employment_type(value: object) -> str | None:
    if not isinstance(value, str):
        return None

    normalized_value = value.lower().strip()

    if "full" in normalized_value or normalized_value == "fulltime":
        return "full_time"

    if "part" in normalized_value or normalized_value == "parttime":
        return "part_time"

    if "intern" in normalized_value:
        return "internship"

    if "contract" in normalized_value:
        return "contract"

    if "freelance" in normalized_value:
        return "freelance"

    return None


def _build_location(raw_job: dict[str, Any]) -> str | None:
    location_parts = [
        _to_text(raw_job.get("job_city")),
        _to_text(raw_job.get("job_state")),
        _to_text(raw_job.get("job_country")),
    ]
    location = ", ".join(part for part in location_parts if part)

    return location or None


def _read_cursor(payload: dict[str, object]) -> str | None:
    cursor = payload.get("cursor") or payload.get("next_cursor")

    if isinstance(cursor, str | int):
        return str(cursor)

    return None


def _read_job_rows(payload: dict[str, object]) -> list[object]:
    for key in ("data", "jobs", "results"):
        rows = payload.get(key)

        if isinstance(rows, list):
            return rows

    return []


def _normalize_job(raw_job: dict[str, Any]) -> ExternalJobPosting | None:
    source_url = _select_apply_url(raw_job)
    title = _to_text(raw_job.get("job_title"))
    description = _to_text(raw_job.get("job_description"))

    if not source_url or not title or not description:
        return None

    try:
        return ExternalJobPosting(
            external_id=_stable_external_id(raw_job, source_url),
            source="jsearch",
            title=title,
            company_name=_to_text(raw_job.get("employer_name")) or "Unknown company",
            location=_build_location(raw_job),
            description=description,
            source_url=source_url,
            created_at=_parse_datetime(raw_job.get("job_posted_at_datetime_utc")),
            salary_min=_to_float(raw_job.get("job_min_salary")),
            salary_max=_to_float(raw_job.get("job_max_salary")),
            salary_currency=_to_text(raw_job.get("job_salary_currency")),
            employment_type=_normalize_employment_type(raw_job.get("job_employment_type")),
            work_mode="remote" if raw_job.get("job_is_remote") is True else None,
            category=_to_text(raw_job.get("job_publisher")),
        )
    except ValidationError:
        logger.exception("Unable to normalize JSearch job result.")
        return None


class JSearchJobProvider:
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

        if not settings.jsearch_api_key:
            raise JobDiscoveryConfigurationError("JSearch API key is missing.")

        if page > 1:
            return JobSearchResponse(
                jobs=[],
                page=page,
                results_per_page=results_per_page,
                total_results=None,
                query=query,
                location=location,
            )

        try:
            response = self._client.get(
                JSEARCH_API_URL,
                headers={
                    "X-RapidAPI-Key": settings.jsearch_api_key,
                    "X-RapidAPI-Host": settings.jsearch_api_host,
                },
                params={
                    "query": _build_search_query(query, location),
                    "country": "tr",
                    "language": "tr",
                    "date_posted": "all",
                },
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            logger.warning("JSearch job search timed out.")
            raise TemporaryJobDiscoveryError("Job discovery provider timed out.") from exc
        except httpx.RequestError as exc:
            logger.warning("JSearch job search request failed: %s", type(exc).__name__)
            raise TemporaryJobDiscoveryError("Job discovery provider request failed.") from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code

            if status_code in {401, 403}:
                logger.warning("JSearch job search credentials were rejected.", extra={"status_code": status_code})
                raise JobDiscoveryConfigurationError("JSearch API key is invalid.") from exc

            if status_code == 404:
                logger.warning("JSearch endpoint was not found.")
                raise TemporaryJobDiscoveryError("Job discovery provider endpoint was not found.") from exc

            if status_code == 429 or status_code >= 500:
                logger.warning("JSearch job search returned temporary status.", extra={"status_code": status_code})
                raise TemporaryJobDiscoveryError("Job discovery provider is unavailable.") from exc

            logger.error("JSearch job search returned non-retryable status.", extra={"status_code": status_code})
            raise RuntimeError("Unable to search jobs.") from exc

        payload = response.json()

        if not isinstance(payload, dict):
            raise RuntimeError("Unexpected job discovery response.")

        normalized_jobs: list[ExternalJobPosting] = []
        seen_external_ids: set[str] = set()
        seen_source_urls: set[str] = set()

        raw_jobs = _read_job_rows(payload)
        for raw_job in raw_jobs:
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

        logger.info(
            "JSearch response received: keys=%s, raw_jobs=%s, normalized_jobs=%s",
            sorted(payload.keys()),
            len(raw_jobs),
            len(normalized_jobs),
        )

        total_results = payload.get("estimated_count") or payload.get("total_count")
        _read_cursor(payload)

        return JobSearchResponse(
            jobs=normalized_jobs,
            page=page,
            results_per_page=results_per_page,
            total_results=total_results if isinstance(total_results, int) else None,
            query=query,
            location=location,
        )
