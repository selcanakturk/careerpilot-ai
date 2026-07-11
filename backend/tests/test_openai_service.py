import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-api-key")
os.environ.setdefault("OPENAI_MODEL", "gpt-5-mini")

from app.schemas.analysis import CVAnalysisResult
from app.services import openai_service


class FakeResponses:
    def __init__(self, response: object | None = None, error: Exception | None = None) -> None:
        self._response = response
        self._error = error
        self.parse_call: dict[str, object] | None = None

    def parse(self, **kwargs: object) -> object:
        self.parse_call = kwargs

        if self._error:
            raise self._error

        return self._response


class FakeOpenAIClient:
    def __init__(self, responses: FakeResponses) -> None:
        self.responses = responses


def test_analyze_cv_valid_structured_response_returns_result(monkeypatch) -> None:
    expected_result = CVAnalysisResult(
        overall_score=82,
        summary="Strong product experience with measurable delivery examples.",
        strengths=["Clear product ownership"],
        weaknesses=["Limited analytics evidence"],
        skill_gaps=["Experiment design"],
        cv_suggestions=["Add quantified launch outcomes"],
    )
    fake_responses = FakeResponses(response=SimpleNamespace(output_parsed=expected_result))
    monkeypatch.setattr(
        openai_service,
        "get_openai_client",
        lambda: FakeOpenAIClient(fake_responses),
    )

    result = openai_service.analyze_cv(
        cv_text="Led roadmap planning for a B2B SaaS product.",
        target_role="Product Manager",
        experience_level="Mid-level",
    )

    assert result == expected_result
    assert fake_responses.parse_call is not None
    assert fake_responses.parse_call["model"] == "gpt-5-mini"
    assert fake_responses.parse_call["text_format"] is CVAnalysisResult


def test_analyze_cv_empty_cv_text_raises_value_error() -> None:
    with pytest.raises(ValueError, match="cv_text is required."):
        openai_service.analyze_cv("", "Product Manager", "Mid-level")


def test_analyze_cv_empty_target_role_raises_value_error() -> None:
    with pytest.raises(ValueError, match="target_role is required."):
        openai_service.analyze_cv("CV text", " ", "Mid-level")


def test_analyze_cv_empty_experience_level_raises_value_error() -> None:
    with pytest.raises(ValueError, match="experience_level is required."):
        openai_service.analyze_cv("CV text", "Product Manager", "")


def test_analyze_cv_api_error_raises_safe_runtime_error(monkeypatch) -> None:
    fake_responses = FakeResponses(error=Exception("raw provider failure"))
    monkeypatch.setattr(
        openai_service,
        "get_openai_client",
        lambda: FakeOpenAIClient(fake_responses),
    )

    with pytest.raises(RuntimeError, match="Unable to complete AI analysis right now."):
        openai_service.analyze_cv("CV text", "Product Manager", "Mid-level")


def test_analyze_cv_invalid_model_output_raises_safe_runtime_error(monkeypatch) -> None:
    fake_responses = FakeResponses(response=SimpleNamespace(output_parsed={"overall_score": 101}))
    monkeypatch.setattr(
        openai_service,
        "get_openai_client",
        lambda: FakeOpenAIClient(fake_responses),
    )

    with pytest.raises(RuntimeError, match="The AI analysis response could not be validated."):
        openai_service.analyze_cv("CV text", "Product Manager", "Mid-level")
