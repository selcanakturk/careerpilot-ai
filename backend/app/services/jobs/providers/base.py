from typing import Protocol

from app.schemas.job import JobSearchResponse


class JobDiscoveryConfigurationError(RuntimeError):
    """Raised when job discovery provider credentials are missing."""


class TemporaryJobDiscoveryError(RuntimeError):
    """Raised when the job discovery provider is temporarily unavailable."""


class JobSearchProvider(Protocol):
    def search_jobs(
        self,
        query: str,
        location: str | None,
        page: int,
        results_per_page: int,
    ) -> JobSearchResponse:
        ...
