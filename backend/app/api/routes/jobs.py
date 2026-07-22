import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import CurrentUser, get_current_user
from app.schemas.job import (
    CompletedAnalysisOptionsResponse,
    CreateJobPostingRequest,
    JobMatchResponse,
    JobPostingResponse,
    JobSearchResponse,
)
from app.services import job_discovery_service, job_service
from app.services.ai import ai_service
from app.services.ai.providers.gemini_provider import TemporaryAIServiceError
from app.services.jobs.providers.base import JobDiscoveryConfigurationError, TemporaryJobDiscoveryError


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("", response_model=JobPostingResponse, status_code=status.HTTP_201_CREATED)
def create_job_posting(
    payload: CreateJobPostingRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> JobPostingResponse:
    try:
        job_posting = job_service.create_job_posting(user_id=current_user.id, payload=payload)
    except Exception:
        logger.exception("Unable to create job posting.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create job posting.",
        )

    return JobPostingResponse.model_validate(job_posting)


@router.get("", response_model=list[JobPostingResponse])
def list_job_postings(
    current_user: CurrentUser = Depends(get_current_user),
) -> list[JobPostingResponse]:
    try:
        job_postings = job_service.list_job_postings(user_id=current_user.id)
    except Exception:
        logger.exception("Unable to list job postings.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load job postings.",
        )

    return [JobPostingResponse.model_validate(job_posting) for job_posting in job_postings]


@router.get("/discover", response_model=JobSearchResponse)
def discover_jobs(
    query: str | None = None,
    location: str | None = None,
    analysis_id: UUID | None = None,
    page: int = Query(default=1, ge=1),
    results_per_page: int = Query(default=20, ge=1, le=50),
    current_user: CurrentUser = Depends(get_current_user),
) -> JobSearchResponse:
    try:
        return job_discovery_service.discover_jobs(
            user_id=current_user.id,
            query=query,
            location=location,
            analysis_id=str(analysis_id) if analysis_id else None,
            page=page,
            results_per_page=results_per_page,
        )
    except job_discovery_service.TargetRoleRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A target role is required to discover jobs.",
        ) from exc
    except job_discovery_service.SelectedAnalysisNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Selected CV analysis not found.",
        ) from exc
    except JobDiscoveryConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Job recommendations are not connected yet. You can still analyze a job manually.",
        ) from exc
    except TemporaryJobDiscoveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The job discovery service is temporarily unavailable. Please try again shortly.",
        ) from exc
    except Exception:
        logger.exception("Unable to discover jobs.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to discover jobs.",
        )


@router.get("/cv-options", response_model=CompletedAnalysisOptionsResponse)
def list_completed_cv_options(
    current_user: CurrentUser = Depends(get_current_user),
) -> CompletedAnalysisOptionsResponse:
    try:
        return CompletedAnalysisOptionsResponse(
            items=job_service.list_completed_analysis_options(user_id=current_user.id)
        )
    except Exception:
        logger.exception("Unable to list completed CV analysis options.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load completed CV analyses.",
        )


@router.get("/{job_posting_id}", response_model=JobPostingResponse)
def get_job_posting(
    job_posting_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
) -> JobPostingResponse:
    try:
        job_posting = job_service.get_job_posting(
            job_posting_id=str(job_posting_id),
            user_id=current_user.id,
        )
    except Exception:
        logger.exception("Unable to load job posting.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load job posting.",
        )

    if job_posting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job posting not found.",
        )

    return JobPostingResponse.model_validate(job_posting)


@router.get("/{job_posting_id}/match/{analysis_id}", response_model=JobMatchResponse)
def get_existing_job_match(
    job_posting_id: UUID,
    analysis_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
) -> JobMatchResponse:
    try:
        existing_match = job_service.get_existing_job_match(
            job_posting_id=str(job_posting_id),
            analysis_id=str(analysis_id),
            user_id=current_user.id,
        )
    except Exception:
        logger.exception("Unable to load existing job match.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load job match.",
        )

    if existing_match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job match not found.",
        )

    return JobMatchResponse.model_validate(existing_match)


@router.post("/{job_posting_id}/match/{analysis_id}", response_model=JobMatchResponse)
def generate_job_match(
    job_posting_id: UUID,
    analysis_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
) -> JobMatchResponse:
    try:
        job_posting = job_service.get_job_posting(
            job_posting_id=str(job_posting_id),
            user_id=current_user.id,
        )
        analysis = job_service.get_completed_analysis(
            analysis_id=str(analysis_id),
            user_id=current_user.id,
        )
    except Exception:
        logger.exception("Unable to load job match inputs.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load job matching data.",
        )

    if job_posting is None or analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job posting or CV analysis not found.",
        )

    try:
        existing_match = job_service.get_existing_job_match(
            job_posting_id=str(job_posting_id),
            analysis_id=str(analysis_id),
            user_id=current_user.id,
        )
    except Exception:
        logger.exception("Unable to check existing job match.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load job match.",
        )

    if existing_match is not None:
        return JobMatchResponse.model_validate(existing_match)

    try:
        match_result = ai_service.analyze_job_match(
            analysis=analysis,
            job_posting=job_posting,
        )
    except TemporaryAIServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI job matching service is busy. Please try again shortly.",
        ) from exc
    except Exception:
        logger.exception("Unable to generate AI job match.")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to complete the job matching request.",
        )

    try:
        saved_match = job_service.save_job_match(
            user_id=current_user.id,
            job_posting_id=str(job_posting_id),
            analysis_id=str(analysis_id),
            result=match_result,
        )
        job_service.mark_job_posting_analyzed(
            job_posting_id=str(job_posting_id),
            user_id=current_user.id,
        )
    except Exception:
        logger.exception("Unable to save job match.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save job match.",
        )

    return JobMatchResponse.model_validate(saved_match)
