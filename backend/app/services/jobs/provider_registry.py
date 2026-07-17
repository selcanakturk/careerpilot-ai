from dataclasses import dataclass

from app.core.config import get_settings
from app.services.jobs.providers.adzuna_provider import AdzunaJobProvider
from app.services.jobs.providers.base import JobDiscoveryConfigurationError, JobSearchProvider
from app.services.jobs.providers.jsearch_provider import JSearchJobProvider
from app.services.jobs.providers.jooble_provider import JoobleJobProvider


ADZUNA_SUPPORTED_COUNTRIES = {
    "au",
    "at",
    "be",
    "br",
    "ca",
    "de",
    "fr",
    "gb",
    "in",
    "it",
    "mx",
    "nl",
    "nz",
    "pl",
    "sg",
    "za",
    "us",
}


@dataclass(frozen=True)
class ProviderRegistration:
    name: str
    provider: JobSearchProvider
    configured: bool
    priority: int
    supported_countries: tuple[str, ...]


def get_provider_registrations() -> list[ProviderRegistration]:
    settings = get_settings()
    adzuna_country = settings.adzuna_country.strip().lower()

    return [
        ProviderRegistration(
            name="jsearch",
            provider=JSearchJobProvider(),
            configured=bool(settings.jsearch_api_key.strip()),
            priority=5,
            supported_countries=("tr",),
        ),
        ProviderRegistration(
            name="jooble",
            provider=JoobleJobProvider(),
            configured=bool(settings.jooble_api_key.strip()),
            priority=10,
            supported_countries=("tr", "global"),
        ),
        ProviderRegistration(
            name="adzuna",
            provider=AdzunaJobProvider(),
            configured=bool(settings.adzuna_app_id.strip() and settings.adzuna_app_key.strip())
            and adzuna_country in ADZUNA_SUPPORTED_COUNTRIES,
            priority=20,
            supported_countries=(adzuna_country,) if adzuna_country in ADZUNA_SUPPORTED_COUNTRIES else (),
        ),
    ]


def select_provider_registrations() -> list[ProviderRegistration]:
    provider_mode = get_settings().job_discovery_provider.strip().lower()
    registrations = sorted(get_provider_registrations(), key=lambda registration: registration.priority)

    if provider_mode == "auto":
        return [registration for registration in registrations if registration.configured]

    if provider_mode in {"jsearch", "jooble", "adzuna"}:
        selected_registration = next(
            (registration for registration in registrations if registration.name == provider_mode),
            None,
        )

        if selected_registration is None:
            raise JobDiscoveryConfigurationError("Selected job provider is not available.")

        if not selected_registration.configured:
            if provider_mode == "adzuna":
                adzuna_country = get_settings().adzuna_country.strip().lower()

                if adzuna_country and adzuna_country not in ADZUNA_SUPPORTED_COUNTRIES:
                    raise JobDiscoveryConfigurationError("Selected job provider does not support this country.")

            raise JobDiscoveryConfigurationError("Job discovery provider is not configured.")

        return [selected_registration]

    raise JobDiscoveryConfigurationError("Unsupported job discovery provider.")
