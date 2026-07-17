from app.schemas.job import JobSearchResponse
from app.services import job_service
from app.services.jobs.job_aggregator import search_all_providers


class TargetRoleRequiredError(ValueError):
    """Raised when job discovery has no query or career context."""


def resolve_job_search_query(user_id: str, query: str | None) -> str:
    normalized_query = query.strip() if query else ""

    if normalized_query:
        return normalized_query

    active_roadmap_target_role = job_service.get_active_roadmap_target_role(user_id)

    if active_roadmap_target_role:
        return active_roadmap_target_role

    latest_analysis_target_role = job_service.get_latest_analysis_target_role(user_id)

    if latest_analysis_target_role:
        return latest_analysis_target_role

    raise TargetRoleRequiredError("A target role is required to discover jobs.")


def discover_jobs(
    user_id: str,
    query: str | None,
    location: str | None,
    page: int,
    results_per_page: int,
) -> JobSearchResponse:
    resolved_query = resolve_job_search_query(user_id=user_id, query=query)
    normalized_location = location.strip() if location and location.strip() else None

    return search_all_providers(
        query=resolved_query,
        location=normalized_location,
        page=page,
        results_per_page=results_per_page,
    )
