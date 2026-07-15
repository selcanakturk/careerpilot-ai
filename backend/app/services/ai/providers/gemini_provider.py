from functools import lru_cache
import logging
import random
import time

from google import genai
from google.genai import types
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.analysis import CVAnalysisResult


logger = logging.getLogger(__name__)

MAX_CV_TEXT_CHARACTERS = 24000
PRIMARY_TEMPORARY_ATTEMPTS = 2
FALLBACK_TEMPORARY_ATTEMPTS = 3
BACKOFF_SECONDS = (1.0, 2.0, 4.0)
FALLBACK_MODELS = ("gemini-3.1-flash-lite", "gemini-3-flash-preview")

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


class TemporaryAIServiceError(RuntimeError):
    """Raised when the AI provider is temporarily unavailable after retries."""


class DailyQuotaExceededError(TemporaryAIServiceError):
    """Raised when the selected AI model has exhausted its daily quota."""


class PermanentAIServiceError(RuntimeError):
    """Raised when the AI provider response or request is not retryable."""


def _is_temporary_ai_error(error: Exception) -> bool:
    message = str(error).lower()
    error_name = type(error).__name__.lower()

    temporary_markers = (
        "503",
        "unavailable",
        "high demand",
        "429",
        "resource_exhausted",
        "rate limit",
        "quota",
        "timeout",
        "timed out",
        "connection",
        "network",
    )

    return any(marker in message or marker in error_name for marker in temporary_markers)


def _is_daily_quota_error(error: Exception) -> bool:
    message = str(error).lower()
    quota_markers = (
        "generaterequestsperdayperprojectpermodel-freetier",
        "quota exceeded",
        "current quota",
        "exceeded your current quota",
        "generate_content_free_tier_requests",
    )

    return any(marker in message for marker in quota_markers)


def _is_auth_error(error: Exception) -> bool:
    message = str(error).lower()
    return "api key" in message or "unauthorized" in message or "permission" in message or "401" in message


def _sleep_before_retry(attempt_index: int) -> None:
    delay = BACKOFF_SECONDS[min(attempt_index, len(BACKOFF_SECONDS) - 1)]
    jitter = random.uniform(0, 0.2)
    time.sleep(delay + jitter)


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
        prompt = _build_prompt(
            normalized_cv_text,
            normalized_target_role,
            normalized_experience_level,
        )

        for model_index, model_name in enumerate(_get_model_sequence(settings.gemini_model)):
            max_attempts = PRIMARY_TEMPORARY_ATTEMPTS if model_index == 0 else FALLBACK_TEMPORARY_ATTEMPTS

            try:
                return self._generate_with_retry(
                    model_name=model_name,
                    prompt=prompt,
                    max_attempts=max_attempts,
                )
            except DailyQuotaExceededError:
                logger.warning(
                    "Gemini CV analysis model quota exhausted; trying next model.",
                    extra={"model": model_name},
                )
                continue
            except TemporaryAIServiceError:
                logger.warning(
                    "Gemini CV analysis model unavailable; trying next model.",
                    extra={"model": model_name},
                )
                continue

        raise RuntimeError("The AI analysis service is temporarily rate limited or unavailable.")

    def _generate_with_model(self, model_name: str, prompt: str) -> CVAnalysisResult:
        logger.info("Attempting Gemini CV analysis model.", extra={"model": model_name})

        response = self._client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=CVAnalysisResult.model_json_schema(),
            ),
        )

        try:
            return CVAnalysisResult.model_validate_json(_extract_response_text(response))
        except ValidationError as exc:
            logger.exception("Gemini returned an invalid structured analysis response.")
            raise PermanentAIServiceError("The AI analysis response could not be validated.") from exc
        except RuntimeError as exc:
            raise PermanentAIServiceError(str(exc)) from exc

    def _generate_with_retry(
        self,
        model_name: str,
        prompt: str,
        max_attempts: int,
    ) -> CVAnalysisResult:
        for attempt in range(max_attempts):
            try:
                return self._generate_with_model(model_name, prompt)
            except PermanentAIServiceError as exc:
                raise RuntimeError(str(exc)) from exc
            except Exception as exc:
                if _is_auth_error(exc):
                    logger.exception("Gemini authentication failed.", extra={"model": model_name})
                    raise RuntimeError("Unable to authenticate with the AI analysis service.") from exc

                if _is_daily_quota_error(exc):
                    raise DailyQuotaExceededError("The AI analysis model daily quota is exhausted.") from exc

                if not _is_temporary_ai_error(exc):
                    logger.exception("Gemini analysis request failed.", extra={"model": model_name})
                    raise RuntimeError("Unable to complete AI analysis right now.") from exc

                if attempt == max_attempts - 1:
                    raise TemporaryAIServiceError(
                        "The AI analysis service is temporarily unavailable."
                    ) from exc

                logger.warning(
                    "Temporary Gemini CV analysis error; retrying request.",
                    extra={"attempt": attempt + 1, "max_attempts": max_attempts, "model": model_name},
                )
                _sleep_before_retry(attempt)

        raise TemporaryAIServiceError("The AI analysis service is temporarily unavailable.")


def _get_model_sequence(primary_model: str) -> list[str]:
    model_sequence: list[str] = []

    for model_name in (primary_model, *FALLBACK_MODELS):
        normalized_model_name = model_name.strip()

        if normalized_model_name and normalized_model_name not in model_sequence:
            model_sequence.append(normalized_model_name)

    return model_sequence
