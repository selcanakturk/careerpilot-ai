from uuid import UUID

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.cv_optimizer import JobProvider


CareerCopilotActionType = Literal[
    "open_cv_optimizer",
    "open_jobs",
    "open_roadmap",
    "open_profile",
    "open_upload_cv",
    "open_history",
]


class CareerCopilotRequest(BaseModel):
    analysis_id: UUID
    message: str = Field(min_length=1, max_length=2000)
    job_external_id: str | None = None
    provider: JobProvider | None = None

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError("Message is required.")

        return normalized_value

    @field_validator("job_external_id")
    @classmethod
    def normalize_optional_job_external_id(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None


class CareerCopilotSuggestedAction(BaseModel):
    type: CareerCopilotActionType
    label: str
    target: str


class CareerCopilotToolResult(BaseModel):
    type: Literal["cv_optimization"]
    status: Literal["completed", "requires_input", "failed"]
    data: dict[str, Any] | None = None


class CareerCopilotResponse(BaseModel):
    reply: str
    suggested_action: CareerCopilotSuggestedAction | None = None
    tool_result: CareerCopilotToolResult | None = None
