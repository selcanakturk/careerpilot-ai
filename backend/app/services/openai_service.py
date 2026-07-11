from functools import lru_cache
import logging

from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    OpenAIError,
    RateLimitError,
)
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.analysis import CVAnalysisResult


logger = logging.getLogger(__name__)

MAX_CV_TEXT_CHARACTERS = 24000

SYSTEM_INSTRUCTIONS = """
Act as an experienced technical recruiter and career coach.
Base the analysis only on the provided CV text.
Do not invent experience, skills, achievements, employers, education, or certifications.
Evaluate the CV for the target role and experience level.
Do not use personal contact details as scoring criteria.
Do not infer or evaluate sensitive personal attributes.
Keep the result concise, concrete, and actionable.
""".strip()


@lru_cache
def get_openai_client() -> OpenAI:
    settings = get_settings()
    return OpenAI(api_key=settings.openai_api_key)


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


def _build_user_prompt(cv_text: str, target_role: str, experience_level: str) -> str:
    return "\n\n".join(
        [
            f"Target role: {target_role}",
            f"Experience level: {experience_level}",
            "Extracted CV text:",
            cv_text,
        ]
    )


def _extract_parsed_response(response: object) -> CVAnalysisResult:
    parsed = getattr(response, "output_parsed", None)

    if isinstance(parsed, CVAnalysisResult):
        return parsed

    if isinstance(parsed, dict):
        return CVAnalysisResult.model_validate(parsed)

    raise RuntimeError("The model response did not match the expected analysis schema.")


def analyze_cv(cv_text: str, target_role: str, experience_level: str) -> CVAnalysisResult:
    normalized_cv_text = _truncate_cv_text(_validate_input(cv_text, "cv_text"))
    normalized_target_role = _validate_input(target_role, "target_role")
    normalized_experience_level = _validate_input(experience_level, "experience_level")
    settings = get_settings()
    client = get_openai_client()

    try:
        response = client.responses.parse(
            model=settings.openai_model,
            input=[
                {
                    "role": "system",
                    "content": SYSTEM_INSTRUCTIONS,
                },
                {
                    "role": "user",
                    "content": _build_user_prompt(
                        normalized_cv_text,
                        normalized_target_role,
                        normalized_experience_level,
                    ),
                },
            ],
            text_format=CVAnalysisResult,
        )
        return _extract_parsed_response(response)
    except (AuthenticationError, PermissionError) as exc:
        logger.exception("OpenAI authentication failed.")
        raise RuntimeError("Unable to authenticate with the AI analysis service.") from exc
    except RateLimitError as exc:
        logger.exception("OpenAI rate limit reached.")
        raise RuntimeError("The AI analysis service is temporarily rate limited.") from exc
    except (APITimeoutError, TimeoutError, APIConnectionError) as exc:
        logger.exception("OpenAI request timed out or could not connect.")
        raise RuntimeError("The AI analysis service is temporarily unavailable.") from exc
    except (ValidationError, RuntimeError) as exc:
        logger.exception("OpenAI returned an invalid structured analysis response.")
        raise RuntimeError("The AI analysis response could not be validated.") from exc
    except OpenAIError as exc:
        logger.exception("OpenAI API request failed.")
        raise RuntimeError("Unable to complete AI analysis right now.") from exc
    except Exception as exc:
        logger.exception("Unexpected OpenAI analysis error.")
        raise RuntimeError("Unable to complete AI analysis right now.") from exc
