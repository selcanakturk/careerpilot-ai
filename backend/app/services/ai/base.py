from typing import Protocol

from app.schemas.analysis import CVAnalysisResult


class AIProvider(Protocol):
    def analyze_cv(
        self,
        cv_text: str,
        target_role: str,
        experience_level: str,
    ) -> CVAnalysisResult:
        ...

