from uuid import UUID

from pydantic import BaseModel, Field, field_validator
from typing import Literal


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

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError("Message is required.")

        return normalized_value


class CareerCopilotSuggestedAction(BaseModel):
    type: CareerCopilotActionType
    label: str
    target: str


class CareerCopilotResponse(BaseModel):
    reply: str
    suggested_action: CareerCopilotSuggestedAction | None = None
