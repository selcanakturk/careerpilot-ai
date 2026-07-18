from dataclasses import dataclass
import logging

from app.schemas.job import ExternalJobPosting, JobSearchCareerProfile, JobSearchResponse
from app.services import career_profile_service
from app.services.job_match_service import calculate_job_match
from app.services.jobs.job_aggregator import search_all_provider_queries, search_all_providers


logger = logging.getLogger(__name__)


class TargetRoleRequiredError(ValueError):
    """Raised when job discovery has no query or career context."""


@dataclass(frozen=True)
class JobSearchContext:
    resolved_query: str
    resolved_location: str | None
    profile_used: bool
    analysis_id: str | None
    queries_used: list[str]
    career_profile: career_profile_service.CareerProfile | None = None


def _to_response_career_profile(
    profile: career_profile_service.CareerProfile | None,
) -> JobSearchCareerProfile | None:
    if profile is None:
        return None

    return JobSearchCareerProfile(
        primary_role=profile.primary_role,
        experience_level=profile.experience_level,
        overall_score=profile.overall_score,
        skills=profile.skills,
        strengths=profile.strengths,
        weaknesses=profile.weaknesses,
    )


def _with_metadata(
    response: JobSearchResponse,
    *,
    context: JobSearchContext,
) -> JobSearchResponse:
    return JobSearchResponse.model_validate(
        {
            **response.model_dump(),
            "profile_used": context.profile_used,
            "analysis_id": context.analysis_id,
            "resolved_query": context.resolved_query,
            "resolved_location": context.resolved_location,
            "career_profile": _to_response_career_profile(context.career_profile),
            "queries_used": context.queries_used,
        }
    )


def _paginate_jobs(jobs: list[ExternalJobPosting], page: int, results_per_page: int) -> list[ExternalJobPosting]:
    start_index = max(page - 1, 0) * results_per_page
    end_index = start_index + results_per_page
    return jobs[start_index:end_index]


def _score_jobs(
    jobs: list[ExternalJobPosting],
    profile: career_profile_service.CareerProfile,
) -> list[ExternalJobPosting]:
    scored_jobs: list[ExternalJobPosting] = []

    for job in jobs:
        match = calculate_job_match(job=job, career_profile=profile)
        scored_jobs.append(
            job.model_copy(
                update={
                    "match_score": match.match_score,
                    "matched_skills": match.matched_skills,
                    "missing_skills": match.missing_skills,
                }
            )
        )

    return sorted(
        scored_jobs,
        key=lambda job: job.match_score if job.match_score is not None else -1,
        reverse=True,
    )


def resolve_job_search_context(
    user_id: str,
    query: str | None,
    location: str | None,
) -> JobSearchContext:
    normalized_query = query.strip() if query else ""
    normalized_location = location.strip() if location and location.strip() else None

    if normalized_query:
        return JobSearchContext(
            resolved_query=normalized_query,
            resolved_location=normalized_location,
            profile_used=False,
            analysis_id=None,
            queries_used=[normalized_query],
            career_profile=None,
        )

    profile = career_profile_service.get_latest_career_profile(user_id)

    if profile is not None:
        queries_used = career_profile_service.generate_search_queries(profile)

        return JobSearchContext(
            resolved_query=profile.primary_role,
            resolved_location=normalized_location or "Turkey",
            profile_used=True,
            analysis_id=profile.analysis_id,
            queries_used=queries_used,
            career_profile=profile,
        )

    raise TargetRoleRequiredError("A target role is required to discover jobs.")


def resolve_job_search_query(user_id: str, query: str | None) -> str:
    context = resolve_job_search_context(
        user_id=user_id,
        query=query,
        location=None,
    )
    return context.resolved_query


def discover_jobs(
    user_id: str,
    query: str | None,
    location: str | None,
    page: int,
    results_per_page: int,
) -> JobSearchResponse:
    context = resolve_job_search_context(
        user_id=user_id,
        query=query,
        location=location,
    )
    logger.info(
        "Job discovery context resolved.",
        extra={
            "profile_used": context.profile_used,
            "resolved_query": context.resolved_query,
            "resolved_location": context.resolved_location,
            "queries_used_count": len(context.queries_used),
            "page": page,
            "results_per_page": results_per_page,
        },
    )

    if context.profile_used:
        response = search_all_provider_queries(
            queries=context.queries_used,
            location=context.resolved_location,
            page=1,
            results_per_page=max(page * results_per_page, results_per_page),
        )
        if context.career_profile is not None:
            scored_jobs = _score_jobs(response.jobs, context.career_profile)
            response = response.model_copy(
                update={
                    "jobs": _paginate_jobs(scored_jobs, page, results_per_page),
                    "page": page,
                    "results_per_page": results_per_page,
                }
            )
    else:
        response = search_all_providers(
            query=context.resolved_query,
            location=context.resolved_location,
            page=page,
            results_per_page=results_per_page,
        )

    logger.info(
        "Job discovery response prepared.",
        extra={
            "profile_used": context.profile_used,
            "providers_used": response.providers_used,
            "providers_failed": response.providers_failed,
            "jobs_returned": len(response.jobs),
            "total_results": response.total_results,
            "page": response.page,
        },
    )

    return _with_metadata(
        response,
        context=context,
    )
