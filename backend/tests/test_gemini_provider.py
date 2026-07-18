import os

import pytest

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-api-key")
os.environ.setdefault("OPENAI_MODEL", "gpt-5-mini")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-api-key")
os.environ.setdefault("GEMINI_MODEL", "gemini-2.5-flash")

from app.schemas.analysis import CVAnalysisResult
from app.services.ai.providers.gemini_provider import GeminiProvider


VALID_GEMINI_JSON = """
{
  "overall_score": 86,
  "summary": "Strong product management CV with clear ownership examples.",
  "strengths": ["Roadmap ownership"],
  "weaknesses": ["Limited experimentation detail"],
  "skill_gaps": ["Experiment design"],
  "cv_suggestions": ["Add quantified launch outcomes"],
  "primary_role": "Product Manager",
  "alternative_roles": ["Product Owner", "Growth Product Manager"],
  "top_skills": ["Roadmapping", "Stakeholder management", "Product discovery"],
  "preferred_job_types": ["full_time"],
  "preferred_locations": ["Turkey"],
  "remote_preference": null
}
""".strip()


class FakeGeminiResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeGeminiModels:
    def __init__(
        self,
        response_text: str | None = None,
        error: Exception | None = None,
        failures: list[Exception] | None = None,
    ) -> None:
        self._response_text = response_text
        self._error = error
        self._failures = failures or []
        self.generate_call: dict[str, object] | None = None
        self.model_calls: list[str] = []

    def generate_content(self, **kwargs: object) -> FakeGeminiResponse:
        self.generate_call = kwargs
        self.model_calls.append(str(kwargs["model"]))

        if self._failures:
            raise self._failures.pop(0)

        if self._error:
            raise self._error

        return FakeGeminiResponse(self._response_text or VALID_GEMINI_JSON)


class FakeGeminiClient:
    def __init__(self, models: FakeGeminiModels) -> None:
        self.models = models


def test_gemini_provider_valid_structured_response_returns_result() -> None:
    models = FakeGeminiModels(response_text=VALID_GEMINI_JSON)
    provider = GeminiProvider(client=FakeGeminiClient(models))

    result = provider.analyze_cv(
        cv_text="Owned roadmap planning for a B2B SaaS platform.",
        target_role="Product Manager",
        experience_level="Mid-level",
    )

    assert isinstance(result, CVAnalysisResult)
    assert result.overall_score == 86
    assert result.strengths == ["Roadmap ownership"]
    assert result.primary_role == "Product Manager"
    assert result.alternative_roles == ["Product Owner", "Growth Product Manager"]
    assert result.top_skills == ["Roadmapping", "Stakeholder management", "Product discovery"]
    assert result.preferred_job_types == ["full_time"]
    assert result.preferred_locations == ["Turkey"]
    assert result.remote_preference is None
    assert models.generate_call is not None
    assert models.generate_call["model"] == "gemini-2.5-flash"
    assert models.model_calls == ["gemini-2.5-flash"]


def test_gemini_provider_filters_sentence_like_top_skills() -> None:
    response_json = """
    {
      "overall_score": 82,
      "summary": "Frontend and backend project experience.",
      "strengths": ["Project portfolio"],
      "weaknesses": [],
      "skill_gaps": [],
      "cv_suggestions": [],
      "primary_role": "Full Stack Developer",
      "alternative_roles": ["Frontend Developer"],
      "top_skills": [
        "Python",
        "Hands-on experience with modern frontend and mobile frameworks including React and Flutter",
        "Holds a formal Software Engineering degree from Altınbaş University",
        "python",
        "Node.js",
        "Strong project portfolio showcasing practical delivery"
      ],
      "preferred_job_types": ["full_time"],
      "preferred_locations": ["Turkey"],
      "remote_preference": null
    }
    """.strip()
    models = FakeGeminiModels(response_text=response_json)
    provider = GeminiProvider(client=FakeGeminiClient(models))

    result = provider.analyze_cv("Built apps with Python, React, Flutter, and Node.js.", "Developer", "junior")

    assert result.top_skills == ["Python", "React", "Flutter", "Node.js"]


def test_gemini_provider_limits_top_skills_to_eight_unique_values() -> None:
    response_json = """
    {
      "overall_score": 82,
      "summary": "Backend profile.",
      "strengths": [],
      "weaknesses": [],
      "skill_gaps": [],
      "cv_suggestions": [],
      "primary_role": "Backend Developer",
      "alternative_roles": [],
      "top_skills": [
        "Python",
        "Django",
        "React",
        "Flutter",
        "Node.js",
        "Express",
        "MongoDB",
        "REST API",
        "Docker",
        "python"
      ],
      "preferred_job_types": ["full_time"],
      "preferred_locations": ["Turkey"],
      "remote_preference": null
    }
    """.strip()
    models = FakeGeminiModels(response_text=response_json)
    provider = GeminiProvider(client=FakeGeminiClient(models))

    result = provider.analyze_cv("CV text", "Backend Developer", "mid")

    assert result.top_skills == [
        "Python",
        "Django",
        "React",
        "Flutter",
        "Node.js",
        "Express",
        "MongoDB",
        "REST API",
    ]


def test_gemini_provider_empty_cv_text_raises_value_error() -> None:
    provider = GeminiProvider(client=FakeGeminiClient(FakeGeminiModels()))

    with pytest.raises(ValueError, match="cv_text is required."):
        provider.analyze_cv("", "Product Manager", "Mid-level")


def test_gemini_provider_empty_target_role_raises_value_error() -> None:
    provider = GeminiProvider(client=FakeGeminiClient(FakeGeminiModels()))

    with pytest.raises(ValueError, match="target_role is required."):
        provider.analyze_cv("CV text", " ", "Mid-level")


def test_gemini_provider_empty_experience_level_raises_value_error() -> None:
    provider = GeminiProvider(client=FakeGeminiClient(FakeGeminiModels()))

    with pytest.raises(ValueError, match="experience_level is required."):
        provider.analyze_cv("CV text", "Product Manager", "")


def test_gemini_provider_api_error_raises_safe_runtime_error() -> None:
    provider = GeminiProvider(
        client=FakeGeminiClient(FakeGeminiModels(error=Exception("internal server failure")))
    )

    with pytest.raises(RuntimeError, match="Unable to complete AI analysis right now."):
        provider.analyze_cv("CV text", "Product Manager", "Mid-level")


def test_gemini_provider_rate_limit_raises_safe_runtime_error() -> None:
    provider = GeminiProvider(
        client=FakeGeminiClient(FakeGeminiModels(error=Exception("429 quota exceeded")))
    )

    with pytest.raises(RuntimeError, match="temporarily rate limited"):
        provider.analyze_cv("CV text", "Product Manager", "Mid-level")


def test_gemini_provider_primary_503_retries_then_fallback_succeeds(monkeypatch) -> None:
    models = FakeGeminiModels(
        failures=[
            Exception("503 UNAVAILABLE high demand"),
            Exception("503 UNAVAILABLE high demand"),
        ]
    )
    provider = GeminiProvider(client=FakeGeminiClient(models))
    monkeypatch.setattr(
        "app.services.ai.providers.gemini_provider._sleep_before_retry",
        lambda _attempt: None,
    )

    result = provider.analyze_cv("CV text", "Product Manager", "Mid-level")

    assert result.overall_score == 86
    assert models.model_calls == [
        "gemini-2.5-flash",
        "gemini-2.5-flash",
        "gemini-3.1-flash-lite",
    ]


def test_gemini_provider_primary_and_first_fallback_fail_then_preview_succeeds(monkeypatch) -> None:
    models = FakeGeminiModels(
        failures=[
            Exception("503 UNAVAILABLE high demand"),
            Exception("503 UNAVAILABLE high demand"),
            Exception("429 RESOURCE_EXHAUSTED"),
            Exception("429 RESOURCE_EXHAUSTED"),
            Exception("429 RESOURCE_EXHAUSTED"),
        ]
    )
    provider = GeminiProvider(client=FakeGeminiClient(models))
    monkeypatch.setattr(
        "app.services.ai.providers.gemini_provider._sleep_before_retry",
        lambda _attempt: None,
    )

    result = provider.analyze_cv("CV text", "Product Manager", "Mid-level")

    assert result.overall_score == 86
    assert models.model_calls == [
        "gemini-2.5-flash",
        "gemini-2.5-flash",
        "gemini-3.1-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3-flash-preview",
    ]


def test_gemini_provider_permanent_400_does_not_fallback(monkeypatch) -> None:
    models = FakeGeminiModels(error=Exception("400 INVALID_ARGUMENT"))
    provider = GeminiProvider(client=FakeGeminiClient(models))
    monkeypatch.setattr(
        "app.services.ai.providers.gemini_provider._sleep_before_retry",
        lambda _attempt: None,
    )

    with pytest.raises(RuntimeError, match="Unable to complete AI analysis right now."):
        provider.analyze_cv("CV text", "Product Manager", "Mid-level")

    assert models.model_calls == ["gemini-2.5-flash"]


def test_gemini_provider_invalid_json_raises_safe_runtime_error() -> None:
    provider = GeminiProvider(client=FakeGeminiClient(FakeGeminiModels(response_text="not json")))

    with pytest.raises(RuntimeError, match="The AI analysis response could not be validated."):
        provider.analyze_cv("CV text", "Product Manager", "Mid-level")


def test_gemini_provider_invalid_schema_raises_safe_runtime_error() -> None:
    invalid_schema_json = """
    {
      "overall_score": 120,
      "summary": "",
      "strengths": null,
      "weaknesses": [],
      "skill_gaps": [],
      "cv_suggestions": []
    }
    """.strip()
    provider = GeminiProvider(client=FakeGeminiClient(FakeGeminiModels(response_text=invalid_schema_json)))

    with pytest.raises(RuntimeError, match="The AI analysis response could not be validated."):
        provider.analyze_cv("CV text", "Product Manager", "Mid-level")
