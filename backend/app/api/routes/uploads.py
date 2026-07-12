import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.core.security import CurrentUser, get_current_user
from app.core.supabase import get_supabase_client
from app.schemas.analysis import CVAnalysisResponse
from app.schemas.upload import CVUploadResponse, DeleteUploadResponse, PDFTextPreviewResponse
from app.services import analysis_service
from app.services import pdf_service
from app.services import upload_service
from app.services.ai import ai_service
from app.services.storage_service import delete_cv, download_cv


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


def _is_pdf_upload(file_type: str) -> bool:
    return file_type.lower() == "pdf"


@router.get("/{upload_id}", response_model=CVUploadResponse)
def get_upload(
    upload_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    supabase_client: Client = Depends(get_supabase_client),
) -> CVUploadResponse:
    upload = _load_owned_upload(upload_id, current_user.id, supabase_client)

    return CVUploadResponse.model_validate(upload)


@router.delete("/{upload_id}", response_model=DeleteUploadResponse)
def delete_upload(
    upload_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    supabase_client: Client = Depends(get_supabase_client),
) -> DeleteUploadResponse:
    upload = _load_owned_upload(upload_id, current_user.id, supabase_client)

    try:
        logger.info("Deleting analysis records for upload %s.", upload_id)
        analysis_service.delete_analyses_for_upload(
            upload_id=str(upload_id),
            user_id=current_user.id,
        )
    except Exception:
        logger.exception("Unable to delete analysis records for upload.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to delete related analysis data.",
        )

    try:
        logger.info("Deleting Storage file for upload %s.", upload_id)
        delete_cv(str(upload["file_path"]))
    except FileNotFoundError:
        logger.warning("Storage file for upload %s was already missing.", upload_id)
    except Exception:
        logger.exception("Unable to delete CV file from storage.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to delete stored CV file.",
        )

    try:
        logger.info("Deleting upload record %s.", upload_id)
        deleted_upload = upload_service.delete_upload_record(
            upload_id=str(upload_id),
            user_id=current_user.id,
        )
    except Exception:
        logger.exception("Unable to delete CV upload record.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to delete CV upload.",
        )

    if deleted_upload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV upload not found.",
        )

    return DeleteUploadResponse(
        id=deleted_upload["id"],
        file_name=str(deleted_upload["file_name"]),
        message="CV and related analysis data deleted successfully.",
    )


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


@router.get("/{upload_id}/text", response_model=PDFTextPreviewResponse)
def extract_upload_text(
    upload_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    supabase_client: Client = Depends(get_supabase_client),
) -> PDFTextPreviewResponse:
    upload = _load_owned_upload(upload_id, current_user.id, supabase_client)

    if not _is_pdf_upload(str(upload["file_type"])):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF uploads are supported for text extraction.",
        )

    try:
        content = download_cv(str(upload["file_path"]))
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV file not found.",
        )
    except Exception:
        logger.exception("Unable to download CV file for text extraction.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to download CV file.",
        )

    try:
        extracted_text = pdf_service.extract_text_from_pdf(content)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except Exception:
        logger.exception("Unexpected PDF text extraction error.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to extract PDF text.",
        )

    return PDFTextPreviewResponse(
        upload_id=upload_id,
        file_name=str(upload["file_name"]),
        page_count=extracted_text.page_count,
        character_count=len(extracted_text.text),
        text_preview=extracted_text.text[:1500],
        message="PDF text extracted successfully.",
    )


def _mark_analysis_failed(processing_analysis: dict[str, object] | None, safe_message: str) -> None:
    if not processing_analysis:
        return

    analysis_id = processing_analysis.get("id")

    if analysis_id:
        analysis_service.fail_analysis(str(analysis_id), safe_message)


@router.post("/{upload_id}/analyze", response_model=CVAnalysisResponse, tags=["Analyses"])
def analyze_upload(
    upload_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    supabase_client: Client = Depends(get_supabase_client),
) -> CVAnalysisResponse:
    upload = _load_owned_upload(upload_id, current_user.id, supabase_client)

    if not _is_pdf_upload(str(upload["file_type"])):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF uploads can be analyzed.",
        )

    try:
        existing_analysis = analysis_service.get_completed_analysis(
            user_id=current_user.id,
            cv_upload_id=str(upload_id),
        )
    except Exception:
        logger.exception("Unable to check existing analysis.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load analysis.",
        )

    if existing_analysis is not None:
        return existing_analysis

    processing_analysis: dict[str, object] | None = None

    try:
        processing_analysis = analysis_service.create_processing_analysis(
            user_id=current_user.id,
            cv_upload_id=str(upload_id),
            target_role=str(upload["target_role"]),
        )
    except Exception:
        logger.exception("Unable to create processing analysis.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to start analysis.",
        )

    try:
        file_bytes = download_cv(str(upload["file_path"]))
    except FileNotFoundError:
        _mark_analysis_failed(processing_analysis, "The CV file could not be processed.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV file not found.",
        )
    except Exception:
        logger.exception("Unable to download CV for analysis.")
        _mark_analysis_failed(processing_analysis, "The CV file could not be processed.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to download CV file.",
        )

    try:
        extracted = pdf_service.extract_text_from_pdf(file_bytes)
    except ValueError as exc:
        _mark_analysis_failed(processing_analysis, "The CV file could not be processed.")
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        logger.exception("Unexpected PDF parsing error during analysis.")
        _mark_analysis_failed(processing_analysis, "The CV file could not be processed.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to process CV file.",
        )

    try:
        analysis_result = ai_service.analyze_cv(
            cv_text=extracted.text,
            target_role=str(upload["target_role"]),
            experience_level=str(upload["experience_level"]),
        )
    except Exception:
        logger.exception("AI analysis service failed.")
        _mark_analysis_failed(
            processing_analysis,
            "The AI analysis service is temporarily unavailable.",
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI analysis service is temporarily unavailable.",
        )

    try:
        return analysis_service.complete_analysis(
            analysis_id=str(processing_analysis["id"]),
            result=analysis_result,
        )
    except Exception:
        logger.exception("Unable to save completed analysis.")
        _mark_analysis_failed(processing_analysis, "The analysis could not be completed.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The analysis could not be completed.",
        )
