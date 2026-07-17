from functools import lru_cache

from app.schemas.analysis import CVAnalysisResult
from app.schemas.job import JobMatchAIResult
from app.services.ai.base import AIProvider
from app.services.ai.providers.gemini_provider import GeminiProvider


@lru_cache
def get_ai_provider() -> AIProvider:
    return GeminiProvider()


def analyze_cv(
    cv_text: str,
    target_role: str,
    experience_level: str,
) -> CVAnalysisResult:
    return get_ai_provider().analyze_cv(
        cv_text=cv_text,
        target_role=target_role,
        experience_level=experience_level,
    )


def analyze_job_match(
    analysis: dict[str, object],
    job_posting: dict[str, object],
) -> JobMatchAIResult:
    return get_ai_provider().analyze_job_match(
        analysis=analysis,
        job_posting=job_posting,
    )
