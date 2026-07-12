import os
from types import SimpleNamespace
from uuid import uuid4

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-api-key")
os.environ.setdefault("OPENAI_MODEL", "gpt-5-mini")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-api-key")
os.environ.setdefault("GEMINI_MODEL", "gemini-2.5-flash")

from fastapi.testclient import TestClient

from app.core.security import CurrentUser, get_current_user
from app.core.supabase import get_supabase_client
from app.main import app
from app.schemas.analysis import CVAnalysisResult, CVAnalysisResponse
from app.services import analysis_service
from app.services import pdf_service
from app.services import storage_service
from app.services.ai import ai_service


class FakeSingleQuery:
    def __init__(self, data: dict[str, object] | None) -> None:
        self._data = data

    def execute(self) -> SimpleNamespace:
        return SimpleNamespace(data=self._data)


class FakeQuery:
    def __init__(self, data: dict[str, object] | None) -> None:
        self._data = data
        self.filters: list[tuple[str, str]] = []

    def select(self, _columns: str) -> "FakeQuery":
        return self

    def eq(self, column: str, value: str) -> "FakeQuery":
        self.filters.append((column, value))
        return self

    def maybe_single(self) -> FakeSingleQuery:
        return FakeSingleQuery(self._data)


class FakeSupabaseClient:
    def __init__(self, data: dict[str, object] | None) -> None:
        self.query = FakeQuery(data)

    def table(self, table_name: str) -> FakeQuery:
        assert table_name == "cv_uploads"
        return self.query


class FakeStorageBucket:
    def __init__(self, content: bytes | None) -> None:
        self._content = content
        self.downloaded_path = ""

    def download(self, file_path: str) -> bytes:
        self.downloaded_path = file_path

        if self._content is None:
            raise Exception("404 not found")

        return self._content


class FakeStorage:
    def __init__(self, content: bytes | None) -> None:
        self.bucket = FakeStorageBucket(content)
        self.bucket_name = ""

    def from_(self, bucket_name: str) -> FakeStorageBucket:
        self.bucket_name = bucket_name
        return self.bucket


class FakeStorageClient:
    def __init__(self, content: bytes | None) -> None:
        self.storage = FakeStorage(content)


def override_current_user() -> CurrentUser:
    return CurrentUser(id="11111111-1111-1111-1111-111111111111", email="owner@example.com")


def make_upload_record(upload_id: str) -> dict[str, object]:
    return {
        "id": upload_id,
        "user_id": "11111111-1111-1111-1111-111111111111",
        "file_name": "selcan-cv.pdf",
        "file_path": "11111111-1111-1111-1111-111111111111/20260711-120000-selcan-cv.pdf",
        "file_type": "PDF",
        "file_size": 245760,
        "target_role": "Product Manager",
        "experience_level": "mid",
        "created_at": "2026-07-11T12:00:00Z",
    }


def make_non_pdf_upload_record(upload_id: str) -> dict[str, object]:
    record = make_upload_record(upload_id)
    record["file_name"] = "selcan-cv.docx"
    record["file_path"] = "11111111-1111-1111-1111-111111111111/20260711-120000-selcan-cv.docx"
    record["file_type"] = "DOCX"
    return record


def make_analysis_response(upload_id: str, analysis_id: str | None = None) -> CVAnalysisResponse:
    return CVAnalysisResponse(
        id=analysis_id or str(uuid4()),
        user_id="11111111-1111-1111-1111-111111111111",
        cv_upload_id=upload_id,
        target_role="Product Manager",
        status="completed",
        overall_score=84,
        summary="Strong product execution profile with clear roadmap ownership.",
        strengths=["Roadmap ownership"],
        weaknesses=["Limited analytics proof"],
        skill_gaps=["Experiment design"],
        cv_suggestions=["Add measurable launch outcomes"],
        created_at="2026-07-11T12:00:00Z",
        updated_at="2026-07-11T12:05:00Z",
    )


def install_successful_analysis_mocks(monkeypatch, upload_id: str) -> dict[str, object]:
    calls: dict[str, object] = {
        "create_processing": 0,
        "complete": 0,
        "failures": [],
        "openai": 0,
    }
    processing_id = str(uuid4())

    monkeypatch.setattr(analysis_service, "get_completed_analysis", lambda **_kwargs: None)

    def create_processing_analysis(**_kwargs: object) -> dict[str, object]:
        calls["create_processing"] = int(calls["create_processing"]) + 1
        return {"id": processing_id}

    def complete_analysis(analysis_id: str, result: CVAnalysisResult) -> CVAnalysisResponse:
        calls["complete"] = int(calls["complete"]) + 1
        assert analysis_id == processing_id
        assert result.overall_score == 84
        return make_analysis_response(upload_id, processing_id)

    def fail_analysis(_analysis_id: str, safe_error_message: str) -> None:
        failures = calls["failures"]
        assert isinstance(failures, list)
        failures.append(safe_error_message)

    def analyze_cv(**_kwargs: object) -> CVAnalysisResult:
        calls["openai"] = int(calls["openai"]) + 1
        return CVAnalysisResult(
            overall_score=84,
            summary="Strong product execution profile with clear roadmap ownership.",
            strengths=["Roadmap ownership"],
            weaknesses=["Limited analytics proof"],
            skill_gaps=["Experiment design"],
            cv_suggestions=["Add measurable launch outcomes"],
        )

    monkeypatch.setattr(analysis_service, "create_processing_analysis", create_processing_analysis)
    monkeypatch.setattr(analysis_service, "complete_analysis", complete_analysis)
    monkeypatch.setattr(analysis_service, "fail_analysis", fail_analysis)
    monkeypatch.setattr(ai_service, "analyze_cv", analyze_cv)
    monkeypatch.setattr(
        pdf_service,
        "extract_text_from_pdf",
        lambda _content: pdf_service.ExtractedPDFText(
            text="Product roadmap and launch ownership.",
            page_count=1,
        ),
    )

    return calls


def test_get_upload_authenticated_owner_returns_200() -> None:
    upload_id = str(uuid4())
    fake_client = FakeSupabaseClient(make_upload_record(upload_id))
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_supabase_client] = lambda: fake_client

    try:
        response = TestClient(app).get(f"/api/uploads/{upload_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["id"] == upload_id
    assert response.json()["target_role"] == "Product Manager"
    assert ("id", upload_id) in fake_client.query.filters
    assert ("user_id", "11111111-1111-1111-1111-111111111111") in fake_client.query.filters


def test_get_upload_not_found_returns_404() -> None:
    upload_id = str(uuid4())
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_supabase_client] = lambda: FakeSupabaseClient(None)

    try:
        response = TestClient(app).get(f"/api/uploads/{upload_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "CV upload not found."


def test_get_upload_without_auth_returns_401() -> None:
    upload_id = str(uuid4())
    app.dependency_overrides[get_supabase_client] = lambda: FakeSupabaseClient(None)

    try:
        response = TestClient(app).get(f"/api/uploads/{upload_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401


def test_download_upload_authenticated_owner_returns_200(monkeypatch) -> None:
    upload_id = str(uuid4())
    fake_db_client = FakeSupabaseClient(make_upload_record(upload_id))
    fake_storage_client = FakeStorageClient(b"%PDF-1.4 test content")
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_supabase_client] = lambda: fake_db_client
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: fake_storage_client)

    try:
        response = TestClient(app).get(f"/api/uploads/{upload_id}/download")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "file_name": "selcan-cv.pdf",
        "size": len(b"%PDF-1.4 test content"),
        "content_type": "application/pdf",
        "message": "CV downloaded successfully.",
    }
    assert fake_storage_client.storage.bucket_name == "cv-files"
    assert (
        fake_storage_client.storage.bucket.downloaded_path
        == "11111111-1111-1111-1111-111111111111/20260711-120000-selcan-cv.pdf"
    )


def test_download_upload_not_found_returns_404(monkeypatch) -> None:
    upload_id = str(uuid4())
    fake_storage_client = FakeStorageClient(b"unused")
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_supabase_client] = lambda: FakeSupabaseClient(None)
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: fake_storage_client)

    try:
        response = TestClient(app).get(f"/api/uploads/{upload_id}/download")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "CV upload not found."
    assert fake_storage_client.storage.bucket.downloaded_path == ""


def test_download_upload_missing_storage_file_returns_404(monkeypatch) -> None:
    upload_id = str(uuid4())
    fake_db_client = FakeSupabaseClient(make_upload_record(upload_id))
    fake_storage_client = FakeStorageClient(None)
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_supabase_client] = lambda: fake_db_client
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: fake_storage_client)

    try:
        response = TestClient(app).get(f"/api/uploads/{upload_id}/download")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "CV file not found."


def test_download_upload_without_auth_returns_401(monkeypatch) -> None:
    upload_id = str(uuid4())
    fake_storage_client = FakeStorageClient(b"unused")
    app.dependency_overrides[get_supabase_client] = lambda: FakeSupabaseClient(make_upload_record(upload_id))
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: fake_storage_client)

    try:
        response = TestClient(app).get(f"/api/uploads/{upload_id}/download")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert fake_storage_client.storage.bucket.downloaded_path == ""


def test_extract_upload_text_authenticated_owner_returns_200(monkeypatch) -> None:
    upload_id = str(uuid4())
    fake_db_client = FakeSupabaseClient(make_upload_record(upload_id))
    fake_storage_client = FakeStorageClient(b"%PDF-1.4 test content")
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_supabase_client] = lambda: fake_db_client
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: fake_storage_client)
    monkeypatch.setattr(
        pdf_service,
        "extract_text_from_pdf",
        lambda _content: pdf_service.ExtractedPDFText(
            text="Selcan Akturk\nProduct manager profile",
            page_count=1,
        ),
    )

    try:
        response = TestClient(app).get(f"/api/uploads/{upload_id}/text")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "upload_id": upload_id,
        "file_name": "selcan-cv.pdf",
        "page_count": 1,
        "character_count": len("Selcan Akturk\nProduct manager profile"),
        "text_preview": "Selcan Akturk\nProduct manager profile",
        "message": "PDF text extracted successfully.",
    }


def test_extract_upload_text_not_found_returns_404(monkeypatch) -> None:
    upload_id = str(uuid4())
    fake_storage_client = FakeStorageClient(b"unused")
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_supabase_client] = lambda: FakeSupabaseClient(None)
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: fake_storage_client)

    try:
        response = TestClient(app).get(f"/api/uploads/{upload_id}/text")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "CV upload not found."
    assert fake_storage_client.storage.bucket.downloaded_path == ""


def test_extract_upload_text_without_auth_returns_401(monkeypatch) -> None:
    upload_id = str(uuid4())
    fake_storage_client = FakeStorageClient(b"unused")
    app.dependency_overrides[get_supabase_client] = lambda: FakeSupabaseClient(make_upload_record(upload_id))
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: fake_storage_client)

    try:
        response = TestClient(app).get(f"/api/uploads/{upload_id}/text")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert fake_storage_client.storage.bucket.downloaded_path == ""


def test_extract_upload_text_non_pdf_returns_415(monkeypatch) -> None:
    upload_id = str(uuid4())
    fake_storage_client = FakeStorageClient(b"unused")
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_supabase_client] = lambda: FakeSupabaseClient(
        make_non_pdf_upload_record(upload_id)
    )
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: fake_storage_client)

    try:
        response = TestClient(app).get(f"/api/uploads/{upload_id}/text")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 415
    assert response.json()["detail"] == "Only PDF uploads are supported for text extraction."
    assert fake_storage_client.storage.bucket.downloaded_path == ""


def test_extract_upload_text_invalid_pdf_returns_422(monkeypatch) -> None:
    upload_id = str(uuid4())
    fake_db_client = FakeSupabaseClient(make_upload_record(upload_id))
    fake_storage_client = FakeStorageClient(b"not a pdf")
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_supabase_client] = lambda: fake_db_client
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: fake_storage_client)

    def raise_invalid_pdf(_content: bytes) -> pdf_service.ExtractedPDFText:
        raise ValueError("The uploaded file could not be read as a valid PDF.")

    monkeypatch.setattr(pdf_service, "extract_text_from_pdf", raise_invalid_pdf)

    try:
        response = TestClient(app).get(f"/api/uploads/{upload_id}/text")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"] == "The uploaded file could not be read as a valid PDF."


def test_extract_upload_text_no_readable_text_returns_422(monkeypatch) -> None:
    upload_id = str(uuid4())
    fake_db_client = FakeSupabaseClient(make_upload_record(upload_id))
    fake_storage_client = FakeStorageClient(b"%PDF image only")
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_supabase_client] = lambda: fake_db_client
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: fake_storage_client)

    def raise_no_text(_content: bytes) -> pdf_service.ExtractedPDFText:
        raise ValueError("No readable text was found in the PDF.")

    monkeypatch.setattr(pdf_service, "extract_text_from_pdf", raise_no_text)

    try:
        response = TestClient(app).get(f"/api/uploads/{upload_id}/text")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"] == "No readable text was found in the PDF."


def test_analyze_upload_authenticated_owner_success_returns_200(monkeypatch) -> None:
    upload_id = str(uuid4())
    fake_db_client = FakeSupabaseClient(make_upload_record(upload_id))
    fake_storage_client = FakeStorageClient(b"%PDF-1.4 test content")
    calls = install_successful_analysis_mocks(monkeypatch, upload_id)
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_supabase_client] = lambda: fake_db_client
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: fake_storage_client)

    try:
        response = TestClient(app).post(f"/api/uploads/{upload_id}/analyze")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["cv_upload_id"] == upload_id
    assert response.json()["status"] == "completed"
    assert response.json()["overall_score"] == 84
    assert calls["create_processing"] == 1
    assert calls["complete"] == 1
    assert calls["openai"] == 1
    assert calls["failures"] == []


def test_analyze_upload_existing_completed_skips_openai(monkeypatch) -> None:
    upload_id = str(uuid4())
    fake_db_client = FakeSupabaseClient(make_upload_record(upload_id))
    fake_storage_client = FakeStorageClient(b"unused")
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_supabase_client] = lambda: fake_db_client
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: fake_storage_client)
    monkeypatch.setattr(
        analysis_service,
        "get_completed_analysis",
        lambda **_kwargs: make_analysis_response(upload_id),
    )

    def fail_if_called(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("AI provider should not be called when a completed analysis exists.")

    monkeypatch.setattr(ai_service, "analyze_cv", fail_if_called)
    monkeypatch.setattr(analysis_service, "create_processing_analysis", fail_if_called)

    try:
        response = TestClient(app).post(f"/api/uploads/{upload_id}/analyze")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["cv_upload_id"] == upload_id
    assert response.json()["status"] == "completed"
    assert fake_storage_client.storage.bucket.downloaded_path == ""


def test_analyze_upload_not_found_returns_404(monkeypatch) -> None:
    upload_id = str(uuid4())
    fake_storage_client = FakeStorageClient(b"unused")
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_supabase_client] = lambda: FakeSupabaseClient(None)
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: fake_storage_client)

    try:
        response = TestClient(app).post(f"/api/uploads/{upload_id}/analyze")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "CV upload not found."


def test_analyze_upload_without_auth_returns_401(monkeypatch) -> None:
    upload_id = str(uuid4())
    fake_storage_client = FakeStorageClient(b"unused")
    app.dependency_overrides[get_supabase_client] = lambda: FakeSupabaseClient(make_upload_record(upload_id))
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: fake_storage_client)

    try:
        response = TestClient(app).post(f"/api/uploads/{upload_id}/analyze")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert fake_storage_client.storage.bucket.downloaded_path == ""


def test_analyze_upload_non_pdf_returns_415(monkeypatch) -> None:
    upload_id = str(uuid4())
    fake_storage_client = FakeStorageClient(b"unused")
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_supabase_client] = lambda: FakeSupabaseClient(
        make_non_pdf_upload_record(upload_id)
    )
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: fake_storage_client)

    try:
        response = TestClient(app).post(f"/api/uploads/{upload_id}/analyze")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 415
    assert response.json()["detail"] == "Only PDF uploads can be analyzed."
    assert fake_storage_client.storage.bucket.downloaded_path == ""


def test_analyze_upload_missing_storage_file_returns_404_and_marks_failed(monkeypatch) -> None:
    upload_id = str(uuid4())
    fake_db_client = FakeSupabaseClient(make_upload_record(upload_id))
    fake_storage_client = FakeStorageClient(None)
    calls = install_successful_analysis_mocks(monkeypatch, upload_id)
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_supabase_client] = lambda: fake_db_client
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: fake_storage_client)

    try:
        response = TestClient(app).post(f"/api/uploads/{upload_id}/analyze")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "CV file not found."
    assert calls["failures"] == ["The CV file could not be processed."]
    assert calls["openai"] == 0


def test_analyze_upload_pdf_parse_error_returns_422_and_marks_failed(monkeypatch) -> None:
    upload_id = str(uuid4())
    fake_db_client = FakeSupabaseClient(make_upload_record(upload_id))
    fake_storage_client = FakeStorageClient(b"%PDF invalid")
    calls = install_successful_analysis_mocks(monkeypatch, upload_id)
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_supabase_client] = lambda: fake_db_client
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: fake_storage_client)

    def raise_parse_error(_content: bytes) -> pdf_service.ExtractedPDFText:
        raise ValueError("The uploaded file could not be read as a valid PDF.")

    monkeypatch.setattr(pdf_service, "extract_text_from_pdf", raise_parse_error)

    try:
        response = TestClient(app).post(f"/api/uploads/{upload_id}/analyze")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"] == "The uploaded file could not be read as a valid PDF."
    assert calls["failures"] == ["The CV file could not be processed."]
    assert calls["openai"] == 0


def test_analyze_upload_ai_provider_error_returns_502_and_marks_failed(monkeypatch) -> None:
    upload_id = str(uuid4())
    fake_db_client = FakeSupabaseClient(make_upload_record(upload_id))
    fake_storage_client = FakeStorageClient(b"%PDF-1.4 test content")
    calls = install_successful_analysis_mocks(monkeypatch, upload_id)
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_supabase_client] = lambda: fake_db_client
    monkeypatch.setattr(storage_service, "get_supabase_client", lambda: fake_storage_client)

    def raise_ai_provider_error(**_kwargs: object) -> CVAnalysisResult:
        calls["openai"] = int(calls["openai"]) + 1
        raise RuntimeError("raw Gemini failure")

    monkeypatch.setattr(ai_service, "analyze_cv", raise_ai_provider_error)

    try:
        response = TestClient(app).post(f"/api/uploads/{upload_id}/analyze")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json()["detail"] == "The AI analysis service is temporarily unavailable."
    assert calls["failures"] == ["The AI analysis service is temporarily unavailable."]
    assert calls["openai"] == 1
    assert calls["complete"] == 0
