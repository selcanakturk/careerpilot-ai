from functools import lru_cache
import logging

from google import genai
from google.genai import types
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.analysis import CVAnalysisResult


logger = logging.getLogger(__name__)

MAX_CV_TEXT_CHARACTERS = 24000

SYSTEM_INSTRUCTIONS = """
Act as an experienced technical recruiter and career coach.
Base the analysis only on the provided CV text.
Do not invent experience, achievements, skills, employers, education, or certifications.
Evaluate the CV for the target role and experience level.
Do not infer or evaluate discriminatory or sensitive personal attributes.
Keep the result concise, clear, and actionable.
Ensure overall_score is between 0 and 100.
Ensure list fields are arrays and never null.
""".strip()


def _validate_input(value: str, field_name: str) -> str:
    normalized_value = value.strip()

    if not normalized_value:
        raise ValueError(f"{field_name} is required.")

    return normalized_value


def _truncate_cv_text(cv_text: str) -> str:
    if len(cv_text) <= MAX_CV_TEXT_CHARACTERS:
        return cv_text

    logger.debug(
        "CV text exceeded maximum length and was truncated.",
        extra={
            "original_length": len(cv_text),
            "truncated_length": MAX_CV_TEXT_CHARACTERS,
        },
    )
    return cv_text[:MAX_CV_TEXT_CHARACTERS]


def _build_prompt(cv_text: str, target_role: str, experience_level: str) -> str:
    return "\n\n".join(
        [
            SYSTEM_INSTRUCTIONS,
            f"Target role: {target_role}",
            f"Experience level: {experience_level}",
            "Extracted CV text:",
            cv_text,
        ]
    )


def _extract_response_text(response: object) -> str:
    response_text = getattr(response, "text", None)

    if isinstance(response_text, str) and response_text.strip():
        return response_text

    logger.error("Gemini returned an empty or unsupported response text payload.")
    raise RuntimeError("The AI analysis response could not be validated.")


def _is_rate_limit_error(error: Exception) -> bool:
    message = str(error).lower()
    return "rate" in message or "quota" in message or "429" in message


def _is_auth_error(error: Exception) -> bool:
    message = str(error).lower()
    return "api key" in message or "unauthorized" in message or "permission" in message or "401" in message


def _is_timeout_or_network_error(error: Exception) -> bool:
    message = str(error).lower()
    return "timeout" in message or "timed out" in message or "connection" in message or "network" in message


@lru_cache
def get_gemini_client() -> genai.Client:
    settings = get_settings()
    return genai.Client(api_key=settings.gemini_api_key)


class GeminiProvider:
    def __init__(self, client: genai.Client | None = None) -> None:
        self._client = client or get_gemini_client()

    def analyze_cv(
        self,
        cv_text: str,
        target_role: str,
        experience_level: str,
    ) -> CVAnalysisResult:
        normalized_cv_text = _truncate_cv_text(_validate_input(cv_text, "cv_text"))
        normalized_target_role = _validate_input(target_role, "target_role")
        normalized_experience_level = _validate_input(experience_level, "experience_level")
        settings = get_settings()

        try:
            response = self._client.models.generate_content(
                model=settings.gemini_model,
                contents=_build_prompt(
                    normalized_cv_text,
                    normalized_target_role,
                    normalized_experience_level,
                ),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_json_schema=CVAnalysisResult.model_json_schema(),
                ),
            )
            return CVAnalysisResult.model_validate_json(_extract_response_text(response))
        except ValidationError as exc:
            logger.exception("Gemini returned an invalid structured analysis response.")
            raise RuntimeError("The AI analysis response could not be validated.") from exc
        except Exception as exc:
            if _is_auth_error(exc):
                logger.exception("Gemini authentication failed.")
                raise RuntimeError("Unable to authenticate with the AI analysis service.") from exc

            if _is_rate_limit_error(exc):
                logger.exception("Gemini rate limit or quota reached.")
                raise RuntimeError("The AI analysis service is temporarily rate limited.") from exc

            if _is_timeout_or_network_error(exc):
                logger.exception("Gemini request timed out or could not connect.")
                raise RuntimeError("The AI analysis service is temporarily unavailable.") from exc

            logger.exception("Gemini analysis request failed.")
            raise RuntimeError("Unable to complete AI analysis right now.") from exc
