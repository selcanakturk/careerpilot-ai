from typing import Protocol

from app.schemas.analysis import CVAnalysisResult
from app.schemas.job import JobMatchAIResult


class AIProvider(Protocol):
    def analyze_cv(
        self,
        cv_text: str,
        target_role: str,
        experience_level: str,
    ) -> CVAnalysisResult:
        ...

    def analyze_job_match(
        self,
        analysis: dict[str, object],
        job_posting: dict[str, object],
    ) -> JobMatchAIResult:
        ...
