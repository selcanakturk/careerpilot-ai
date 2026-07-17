import logging
import re

from app.schemas.job import ExternalJobPosting, JobSearchResponse
from app.services.jobs.provider_registry import select_provider_registrations
from app.services.jobs.providers.base import JobDiscoveryConfigurationError, TemporaryJobDiscoveryError


logger = logging.getLogger(__name__)


def _normalize_key(value: str | None) -> str:
    if not value:
        return ""

    return re.sub(r"\s+", " ", value.strip().lower())


def _dedupe_keys(job: ExternalJobPosting) -> list[tuple[str, str]]:
    keys: list[tuple[str, str]] = []
    normalized_url = _normalize_key(job.source_url)

    if normalized_url:
        keys.append(("url", normalized_url))

    normalized_external_id = _normalize_key(job.external_id)

    if normalized_external_id:
        keys.append(("external", f"{job.source}:{normalized_external_id}"))

    identity_key = "|".join(
        [
            _normalize_key(job.title),
            _normalize_key(job.company_name),
            _normalize_key(job.location),
        ]
    )

    if identity_key != "||":
        keys.append(("identity", identity_key))

    return keys


def _job_time(job: ExternalJobPosting) -> float:
    if job.created_at is None:
        return 0

    return job.created_at.timestamp()


def _dedupe_jobs(jobs: list[ExternalJobPosting]) -> list[ExternalJobPosting]:
    deduped_jobs: dict[int, ExternalJobPosting] = {}
    key_to_job_index: dict[tuple[str, str], int] = {}

    for index, job in enumerate(jobs):
        keys = _dedupe_keys(job)
        existing_index = next((key_to_job_index[key] for key in keys if key in key_to_job_index), None)

        if existing_index is None:
            deduped_jobs[index] = job
            for key in keys:
                key_to_job_index[key] = index
            continue

        existing_job = deduped_jobs[existing_index]

        if len(job.description) > len(existing_job.description):
            deduped_jobs[existing_index] = job

        for key in keys:
            key_to_job_index[key] = existing_index

    return sorted(deduped_jobs.values(), key=_job_time, reverse=True)


def search_all_providers(
    query: str,
    location: str | None,
    page: int,
    results_per_page: int,
) -> JobSearchResponse:
    registrations = select_provider_registrations()

    if not registrations:
        raise JobDiscoveryConfigurationError("No configured job discovery providers are available.")

    all_jobs: list[ExternalJobPosting] = []
    providers_used: list[str] = []
    providers_failed: list[str] = []
    total_results = 0
    has_total_results = False

    for registration in registrations:
        try:
            result = registration.provider.search_jobs(
                query=query,
                location=location,
                page=page,
                results_per_page=results_per_page,
            )
        except (JobDiscoveryConfigurationError, TemporaryJobDiscoveryError):
            providers_failed.append(registration.name)
            logger.warning("Job discovery provider failed safely.", extra={"provider": registration.name})
            continue
        except Exception:
            providers_failed.append(registration.name)
            logger.exception("Job discovery provider failed unexpectedly.", extra={"provider": registration.name})
            continue

        providers_used.append(registration.name)
        all_jobs.extend(result.jobs)

        if result.total_results is not None:
            total_results += result.total_results
            has_total_results = True

    if not providers_used:
        raise TemporaryJobDiscoveryError("All job discovery providers failed.")

    deduped_jobs = _dedupe_jobs(all_jobs)

    return JobSearchResponse(
        jobs=deduped_jobs,
        page=page,
        results_per_page=results_per_page,
        total_results=total_results if has_total_results else None,
        query=query,
        location=location,
        providers_used=providers_used,
        providers_failed=providers_failed,
    )
