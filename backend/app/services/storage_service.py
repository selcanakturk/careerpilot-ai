import logging

from supabase import Client

from app.core.supabase import get_supabase_client


logger = logging.getLogger(__name__)

CV_STORAGE_BUCKET = "cv-files"


def _is_not_found_error(error: Exception) -> bool:
    message = str(error).lower()
    return "not found" in message or "404" in message


def download_cv(file_path: str) -> bytes:
    normalized_path = file_path.strip().lstrip("/")

    if not normalized_path:
        raise FileNotFoundError("CV file path is empty.")

    supabase_client: Client = get_supabase_client()

    try:
        file_content = supabase_client.storage.from_(CV_STORAGE_BUCKET).download(normalized_path)
    except Exception as exc:
        if _is_not_found_error(exc):
            raise FileNotFoundError("CV file was not found in storage.") from exc

        logger.exception("Unable to download CV from Supabase Storage.")
        raise RuntimeError("Unable to download CV from storage.") from exc

    if file_content is None:
        raise FileNotFoundError("CV file was not found in storage.")

    if isinstance(file_content, bytes):
        return file_content

    try:
        return bytes(file_content)
    except TypeError as exc:
        logger.exception("Supabase Storage returned an unexpected download payload.")
        raise RuntimeError("Unable to read CV download payload.") from exc
