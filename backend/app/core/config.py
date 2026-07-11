from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CareerPilot AI API"
    app_version: str = "0.1.0"
    frontend_url: str = "http://localhost:5173"
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-5-mini"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def validate_required_secrets(self) -> "Settings":
        missing_values = []

        if not self.supabase_url:
            missing_values.append("SUPABASE_URL")

        if not self.supabase_service_role_key:
            missing_values.append("SUPABASE_SERVICE_ROLE_KEY")

        if not self.openai_api_key:
            missing_values.append("OPENAI_API_KEY")

        if missing_values:
            missing_names = ", ".join(missing_values)
            raise ValueError(
                f"Missing backend configuration: {missing_names}. "
                "Define these values in backend/.env before starting the API."
            )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
