import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import CurrentUser, get_current_user
from app.schemas.cv_optimizer import CVOptimizeRequest, CVOptimizeResponse
from app.services import cv_optimizer_service


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cv", tags=["CV"])


@router.post("/optimize", response_model=CVOptimizeResponse)
def optimize_cv(
    payload: CVOptimizeRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> CVOptimizeResponse:
    try:
        result = cv_optimizer_service.optimize_cv_for_job(
            user_id=current_user.id,
            analysis_id=payload.analysis_id,
            job_external_id=payload.job_external_id,
            provider=payload.provider,
        )
    except cv_optimizer_service.CVOptimizerInputNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The CV analysis or job posting could not be found.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except cv_optimizer_service.CVOptimizerAIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to optimize CV right now.",
        ) from exc
    except Exception:
        logger.exception("Unable to optimize CV.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to optimize CV.",
        )

    return CVOptimizeResponse(
        analysis_id=payload.analysis_id,
        job_external_id=payload.job_external_id,
        provider=payload.provider,
        match_before=result.match_before,
        estimated_match_after=result.estimated_match_after,
        changes=result.changes,
        optimized_cv=result.optimized_cv,
    )
