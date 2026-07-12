import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import CurrentUser, get_current_user
from app.schemas.analysis import DeleteAnalysisResponse
from app.services import analysis_service


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyses", tags=["Analyses"])


@router.delete("/{analysis_id}", response_model=DeleteAnalysisResponse)
def delete_analysis(
    analysis_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
) -> DeleteAnalysisResponse:
    try:
        deleted = analysis_service.delete_analysis(
            analysis_id=str(analysis_id),
            user_id=current_user.id,
        )
    except Exception:
        logger.exception("Unable to delete analysis.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to delete analysis.",
        )

    if deleted is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found.",
        )

    return DeleteAnalysisResponse(
        id=deleted["id"],
        cv_upload_id=deleted["cv_upload_id"],
        message="Analysis deleted successfully.",
    )
