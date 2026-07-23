import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import CurrentUser, get_current_user
from app.schemas.career_copilot import CareerCopilotRequest, CareerCopilotResponse
from app.services import career_copilot_service


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/career-copilot", tags=["Career Copilot"])


@router.post("/chat", response_model=CareerCopilotResponse)
def chat(
    payload: CareerCopilotRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> CareerCopilotResponse:
    try:
        reply = career_copilot_service.ask_career_copilot(
            user_id=current_user.id,
            analysis_id=str(payload.analysis_id),
            message=payload.message,
        )
    except career_copilot_service.CareerCopilotAnalysisNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV analysis not found.",
        ) from exc
    except career_copilot_service.CareerCopilotAIError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Career Copilot is temporarily unavailable. Please try again shortly.",
        ) from exc
    except Exception:
        logger.exception("Unable to complete Career Copilot request.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to complete Career Copilot request.",
        )

    return CareerCopilotResponse(reply=reply)
