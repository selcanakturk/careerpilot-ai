import logging

from app.core.supabase import get_supabase_client


logger = logging.getLogger(__name__)

UPLOADS_TABLE = "cv_uploads"


def _extract_response_data(response: object, action: str) -> object | None:
    if response is None:
        return None

    data = getattr(response, "data", None)

    if data is None or data == []:
        return None

    if isinstance(data, list):
        first_item = data[0] if data else None

        if first_item is None:
            return None

        if isinstance(first_item, dict):
            return first_item

        logger.error("Unexpected cv_uploads %s list item type: %s", action, type(first_item).__name__)
        raise RuntimeError("Unexpected upload database response.")

    if isinstance(data, dict):
        return data

    logger.error("Unexpected cv_uploads %s response type: %s", action, type(data).__name__)
    raise RuntimeError("Unexpected upload database response.")


def delete_upload_record(upload_id: str, user_id: str) -> dict[str, object] | None:
    try:
        existing_response = (
            get_supabase_client()
            .table(UPLOADS_TABLE)
            .select("id,file_name")
            .eq("id", upload_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to load upload before deletion.")
        raise RuntimeError("Unable to load upload record.") from exc

    existing = _extract_response_data(existing_response, "select before delete")

    if existing is None:
        return None

    if not isinstance(existing, dict):
        logger.error("Unexpected normalized cv_uploads delete lookup response.")
        raise RuntimeError("Unexpected upload database response.")

    try:
        delete_response = (
            get_supabase_client()
            .table(UPLOADS_TABLE)
            .delete()
            .eq("id", upload_id)
            .eq("user_id", user_id)
            .execute()
        )
    except Exception as exc:
        logger.exception("Unable to delete upload.")
        raise RuntimeError("Unable to delete upload record.") from exc

    deleted = _extract_response_data(delete_response, "delete upload record")

    if deleted is None:
        deleted = existing

    if not isinstance(deleted, dict):
        logger.error("Unexpected normalized cv_uploads delete response.")
        raise RuntimeError("Unexpected upload database response.")

    return {
        "id": deleted.get("id", existing.get("id")),
        "file_name": deleted.get("file_name", existing.get("file_name")),
    }
