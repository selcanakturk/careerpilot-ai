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


def _dedupe_jobs_preserving_order(jobs: list[ExternalJobPosting]) -> list[ExternalJobPosting]:
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

    return [deduped_jobs[index] for index in sorted(deduped_jobs)]


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def search_all_providers(
    query: str,
    location: str | None,
    page: int,
    results_per_page: int,
) -> JobSearchResponse:
    registrations = select_provider_registrations()

    if not registrations:
        raise JobDiscoveryConfigurationError("No configured job discovery providers are available.")

    providers_used: list[str] = []
    providers_failed: list[str] = []
    empty_success_response: JobSearchResponse | None = None

    for registration in registrations:
        logger.info(
            "Trying job provider.",
            extra={"provider": registration.name, "query": query, "location": location},
        )

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
        logger.info(
            "Job provider result received.",
            extra={
                "provider": registration.name,
                "query": query,
                "location": location,
                "jobs_returned": len(result.jobs),
                "total_results": result.total_results,
            },
        )

        if result.jobs:
            deduped_jobs = _dedupe_jobs(result.jobs)
            logger.info(
                "Job provider selected.",
                extra={
                    "provider": registration.name,
                    "query": query,
                    "location": location,
                    "raw_jobs": len(result.jobs),
                    "deduped_jobs": len(deduped_jobs),
                    "providers_failed": providers_failed,
                },
            )
            return JobSearchResponse(
                jobs=deduped_jobs,
                page=page,
                results_per_page=results_per_page,
                total_results=result.total_results,
                query=query,
                location=location,
                providers_used=[registration.name],
                providers_failed=providers_failed,
            )

        if empty_success_response is None:
            empty_success_response = result

    if empty_success_response is None:
        raise TemporaryJobDiscoveryError("All job discovery providers failed.")

    return JobSearchResponse(
        jobs=[],
        page=page,
        results_per_page=results_per_page,
        total_results=empty_success_response.total_results,
        query=query,
        location=location,
        providers_used=providers_used,
        providers_failed=providers_failed,
    )


def search_all_provider_queries(
    queries: list[str],
    location: str | None,
    page: int,
    results_per_page: int,
) -> JobSearchResponse:
    normalized_queries: list[str] = []

    for query in queries:
        normalized_query = query.strip()

        if normalized_query and normalized_query not in normalized_queries:
            normalized_queries.append(normalized_query)

    if not normalized_queries:
        raise JobDiscoveryConfigurationError("No job discovery queries are available.")

    registrations = select_provider_registrations()

    if not registrations:
        raise JobDiscoveryConfigurationError("No configured job discovery providers are available.")

    providers_used: list[str] = []
    providers_failed: list[str] = []
    empty_provider_used: list[str] = []
    empty_success_response: JobSearchResponse | None = None

    for registration in registrations:
        provider_jobs: list[ExternalJobPosting] = []
        provider_total_results = 0
        provider_has_total_results = False
        provider_had_success = False

        logger.info(
            "Trying job provider for multi-query search.",
            extra={"provider": registration.name, "queries": normalized_queries, "location": location},
        )

        for query in normalized_queries:
            try:
                result = registration.provider.search_jobs(
                    query=query,
                    location=location,
                    page=page,
                    results_per_page=results_per_page,
                )
            except (JobDiscoveryConfigurationError, TemporaryJobDiscoveryError):
                _append_unique(providers_failed, registration.name)
                logger.warning("Job discovery provider failed safely.", extra={"provider": registration.name})
                continue
            except Exception:
                _append_unique(providers_failed, registration.name)
                logger.exception("Job discovery provider failed unexpectedly.", extra={"provider": registration.name})
                continue

            provider_had_success = True
            provider_jobs.extend(result.jobs)
            logger.info(
                "Job provider query result received.",
                extra={
                    "provider": registration.name,
                    "query": query,
                    "location": location,
                    "jobs_returned": len(result.jobs),
                    "total_results": result.total_results,
                },
            )

            if result.total_results is not None:
                provider_total_results += result.total_results
                provider_has_total_results = True

            if empty_success_response is None:
                empty_success_response = result

        if not provider_had_success:
            continue

        _append_unique(empty_provider_used, registration.name)

        if provider_jobs:
            deduped_jobs = _dedupe_jobs_preserving_order(provider_jobs)
            logger.info(
                "Multi-query job provider selected.",
                extra={
                    "provider": registration.name,
                    "queries": normalized_queries,
                    "location": location,
                    "raw_jobs": len(provider_jobs),
                    "deduped_jobs": len(deduped_jobs),
                    "providers_failed": providers_failed,
                },
            )
            return JobSearchResponse(
                jobs=deduped_jobs,
                page=page,
                results_per_page=results_per_page,
                total_results=provider_total_results if provider_has_total_results else None,
                query=normalized_queries[0],
                location=location,
                providers_used=[registration.name],
                providers_failed=providers_failed,
            )

    if empty_success_response is None:
        raise TemporaryJobDiscoveryError("All job discovery providers failed.")

    return JobSearchResponse(
        jobs=[],
        page=page,
        results_per_page=results_per_page,
        total_results=empty_success_response.total_results,
        query=normalized_queries[0],
        location=location,
        providers_used=empty_provider_used,
        providers_failed=providers_failed,
    )
