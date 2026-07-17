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
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_fallback_model: str = "gemini-3.1-flash-lite"
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    adzuna_country: str = "gb"
    jsearch_api_key: str = ""
    jsearch_api_host: str = "jsearch.p.rapidapi.com"
    jooble_api_key: str = ""
    job_discovery_provider: str = "auto"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def validate_required_secrets(self) -> "Settings":
        missing_values = []

        if not self.supabase_url:
            missing_values.append("SUPABASE_URL")

        if not self.supabase_service_role_key:
            missing_values.append("SUPABASE_SERVICE_ROLE_KEY")

        if not self.gemini_api_key:
            missing_values.append("GEMINI_API_KEY")

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
