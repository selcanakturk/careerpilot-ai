import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.core.security import CurrentUser, get_current_user
from app.core.supabase import get_supabase_client
from app.schemas.upload import CVUploadResponse
from app.services.storage_service import download_cv


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uploads", tags=["Uploads"])


def _load_owned_upload(upload_id: UUID, user_id: str, supabase_client: Client) -> dict[str, object]:
    try:
        response = (
            supabase_client.table("cv_uploads")
            .select(
                "id,user_id,file_name,file_path,file_type,file_size,target_role,experience_level,created_at"
            )
            .eq("id", str(upload_id))
            .eq("user_id", user_id)
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

    return response.data


def _get_content_type(file_type: str) -> str:
    normalized_type = file_type.lower()

    if normalized_type == "pdf":
        return "application/pdf"

    if normalized_type == "doc":
        return "application/msword"

    if normalized_type == "docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    return "application/octet-stream"


@router.get("/{upload_id}", response_model=CVUploadResponse)
def get_upload(
    upload_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    supabase_client: Client = Depends(get_supabase_client),
) -> CVUploadResponse:
    upload = _load_owned_upload(upload_id, current_user.id, supabase_client)

    return CVUploadResponse.model_validate(upload)


@router.get("/{upload_id}/download")
def download_upload(
    upload_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    supabase_client: Client = Depends(get_supabase_client),
) -> dict[str, str | int]:
    upload = _load_owned_upload(upload_id, current_user.id, supabase_client)

    try:
        content = download_cv(str(upload["file_path"]))
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV file not found.",
        )
    except Exception:
        logger.exception("Unable to download CV file.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to download CV file.",
        )

    return {
        "file_name": str(upload["file_name"]),
        "size": len(content),
        "content_type": _get_content_type(str(upload["file_type"])),
        "message": "CV downloaded successfully.",
    }
