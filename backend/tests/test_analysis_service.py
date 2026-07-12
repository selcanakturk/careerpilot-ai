import os
from types import SimpleNamespace
from uuid import uuid4

import pytest

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-api-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-api-key")
os.environ.setdefault("GEMINI_MODEL", "gemini-2.5-flash")

from app.services import analysis_service


class FakeExecuteQuery:
    def __init__(self, execute_result: object) -> None:
        self._execute_result = execute_result

    def select(self, _columns: str) -> "FakeExecuteQuery":
        return self

    def insert(self, _payload: dict[str, object]) -> "FakeExecuteQuery":
        return self

    def update(self, _payload: dict[str, object]) -> "FakeExecuteQuery":
        return self

    def eq(self, _column: str, _value: str) -> "FakeExecuteQuery":
        return self

    def order(self, _column: str, desc: bool = False) -> "FakeExecuteQuery":
        return self

    def limit(self, _value: int) -> "FakeExecuteQuery":
        return self

    def maybe_single(self) -> "FakeExecuteQuery":
        return self

    def execute(self) -> object:
        return self._execute_result


class FakeAnalysisClient:
    def __init__(self, execute_result: object) -> None:
        self.query = FakeExecuteQuery(execute_result)

    def table(self, table_name: str) -> FakeExecuteQuery:
        assert table_name == "cv_analyses"
        return self.query


def make_analysis_record() -> dict[str, object]:
    upload_id = str(uuid4())

    return {
        "id": str(uuid4()),
        "user_id": "11111111-1111-1111-1111-111111111111",
        "cv_upload_id": upload_id,
        "target_role": "Product Manager",
        "status": "completed",
        "overall_score": 88,
        "summary": "Strong CV for the target role.",
        "strengths": [],
        "weaknesses": [],
        "skill_gaps": [],
        "cv_suggestions": [],
        "created_at": "2026-07-11T12:00:00Z",
        "updated_at": "2026-07-11T12:10:00Z",
    }


def test_get_completed_analysis_execute_none_returns_none(monkeypatch) -> None:
    monkeypatch.setattr(
        analysis_service,
        "get_supabase_client",
        lambda: FakeAnalysisClient(None),
    )

    result = analysis_service.get_completed_analysis(
        user_id="11111111-1111-1111-1111-111111111111",
        cv_upload_id=str(uuid4()),
    )

    assert result is None


def test_get_completed_analysis_empty_list_returns_none(monkeypatch) -> None:
    monkeypatch.setattr(
        analysis_service,
        "get_supabase_client",
        lambda: FakeAnalysisClient(SimpleNamespace(data=[])),
    )

    result = analysis_service.get_completed_analysis(
        user_id="11111111-1111-1111-1111-111111111111",
        cv_upload_id=str(uuid4()),
    )

    assert result is None


def test_get_completed_analysis_dict_data_returns_record(monkeypatch) -> None:
    record = make_analysis_record()
    monkeypatch.setattr(
        analysis_service,
        "get_supabase_client",
        lambda: FakeAnalysisClient(SimpleNamespace(data=record)),
    )

    result = analysis_service.get_completed_analysis(
        user_id=str(record["user_id"]),
        cv_upload_id=str(record["cv_upload_id"]),
    )

    assert result is not None
    assert str(result.id) == record["id"]


def test_get_completed_analysis_list_data_returns_first_record(monkeypatch) -> None:
    first_record = make_analysis_record()
    second_record = make_analysis_record()
    monkeypatch.setattr(
        analysis_service,
        "get_supabase_client",
        lambda: FakeAnalysisClient(SimpleNamespace(data=[first_record, second_record])),
    )

    result = analysis_service.get_completed_analysis(
        user_id=str(first_record["user_id"]),
        cv_upload_id=str(first_record["cv_upload_id"]),
    )

    assert result is not None
    assert str(result.id) == first_record["id"]


def test_get_completed_analysis_unexpected_data_type_raises_runtime_error(monkeypatch) -> None:
    monkeypatch.setattr(
        analysis_service,
        "get_supabase_client",
        lambda: FakeAnalysisClient(SimpleNamespace(data="unexpected")),
    )

    with pytest.raises(RuntimeError, match="Unexpected analysis database response."):
        analysis_service.get_completed_analysis(
            user_id="11111111-1111-1111-1111-111111111111",
            cv_upload_id=str(uuid4()),
        )


def test_create_processing_analysis_insert_list_returns_first_record(monkeypatch) -> None:
    record = {"id": str(uuid4()), "status": "processing"}
    monkeypatch.setattr(
        analysis_service,
        "get_supabase_client",
        lambda: FakeAnalysisClient(SimpleNamespace(data=[record])),
    )

    result = analysis_service.create_processing_analysis(
        user_id="11111111-1111-1111-1111-111111111111",
        cv_upload_id=str(uuid4()),
        target_role="Product Manager",
    )

    assert result == record


def test_create_processing_analysis_insert_dict_returns_record(monkeypatch) -> None:
    record = {"id": str(uuid4()), "status": "processing"}
    monkeypatch.setattr(
        analysis_service,
        "get_supabase_client",
        lambda: FakeAnalysisClient(SimpleNamespace(data=record)),
    )

    result = analysis_service.create_processing_analysis(
        user_id="11111111-1111-1111-1111-111111111111",
        cv_upload_id=str(uuid4()),
        target_role="Product Manager",
    )

    assert result == record


def test_create_processing_analysis_response_none_raises_runtime_error(monkeypatch) -> None:
    monkeypatch.setattr(
        analysis_service,
        "get_supabase_client",
        lambda: FakeAnalysisClient(None),
    )

    with pytest.raises(RuntimeError, match="Unable to create analysis record."):
        analysis_service.create_processing_analysis(
            user_id="11111111-1111-1111-1111-111111111111",
            cv_upload_id=str(uuid4()),
            target_role="Product Manager",
        )


def test_create_processing_analysis_empty_list_raises_runtime_error(monkeypatch) -> None:
    monkeypatch.setattr(
        analysis_service,
        "get_supabase_client",
        lambda: FakeAnalysisClient(SimpleNamespace(data=[])),
    )

    with pytest.raises(RuntimeError, match="Unable to create analysis record."):
        analysis_service.create_processing_analysis(
            user_id="11111111-1111-1111-1111-111111111111",
            cv_upload_id=str(uuid4()),
            target_role="Product Manager",
        )


def test_complete_analysis_update_list_returns_first_record(monkeypatch) -> None:
    record = make_analysis_record()
    monkeypatch.setattr(
        analysis_service,
        "get_supabase_client",
        lambda: FakeAnalysisClient(SimpleNamespace(data=[record])),
    )

    result = analysis_service.complete_analysis(
        analysis_id=str(record["id"]),
        result=analysis_service.CVAnalysisResult(
            overall_score=88,
            summary="Strong CV for the target role.",
            strengths=[],
            weaknesses=[],
            skill_gaps=[],
            cv_suggestions=[],
        ),
    )

    assert str(result.id) == record["id"]
