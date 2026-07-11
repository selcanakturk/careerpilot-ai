import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.core.security import CurrentUser, get_current_user
from app.core.supabase import get_supabase_client
from app.schemas.upload import CVUploadResponse


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uploads", tags=["Uploads"])


@router.get("/{upload_id}", response_model=CVUploadResponse)
def get_upload(
    upload_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    supabase_client: Client = Depends(get_supabase_client),
) -> CVUploadResponse:
    try:
        response = (
            supabase_client.table("cv_uploads")
            .select(
                "id,user_id,file_name,file_path,file_type,file_size,target_role,experience_level,created_at"
            )
            .eq("id", str(upload_id))
            .eq("user_id", current_user.id)
            .maybe_single()
            .execute()
        )
    except Exception:
        logger.exception("Unable to load CV upload metadata.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load CV upload.",
        )

    if response.data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV upload not found.",
        )

    return CVUploadResponse.model_validate(response.data)
