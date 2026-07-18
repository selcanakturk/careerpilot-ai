import os
from types import SimpleNamespace

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-api-key")
os.environ.setdefault("OPENAI_MODEL", "gpt-5-mini")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-api-key")
os.environ.setdefault("GEMINI_MODEL", "gemini-2.5-flash")

from app.services import career_profile_service


OWNER_ID = "11111111-1111-1111-1111-111111111111"
ANALYSIS_ID = "22222222-2222-2222-2222-222222222222"
UPLOAD_ID = "33333333-3333-3333-3333-333333333333"


def make_analysis() -> dict[str, object]:
    return {
        "id": ANALYSIS_ID,
        "user_id": OWNER_ID,
        "cv_upload_id": UPLOAD_ID,
        "target_role": "Backend Software Engineer",
        "status": "completed",
        "overall_score": 84,
        "strengths": [
            " API design ",
            "Python backend development",
            "api design",
            "",
            42,
        ],
        "weaknesses": ["Cloud deployment depth"],
        "created_at": "2026-07-18T10:00:00Z",
        "updated_at": "2026-07-18T10:00:00Z",
    }


class FakeCareerProfileQuery:
    def __init__(self, table_name: str, client: "FakeCareerProfileClient") -> None:
        self.table_name = table_name
        self.client = client

    def select(self, columns: str) -> "FakeCareerProfileQuery":
        self.client.selects.append((self.table_name, columns))
        return self

    def eq(self, column: str, value: str) -> "FakeCareerProfileQuery":
        self.client.filters.append((self.table_name, column, value))
        return self

    def order(self, column: str, desc: bool = False) -> "FakeCareerProfileQuery":
        self.client.orders.append((self.table_name, column, desc))
        return self

    def limit(self, value: int) -> "FakeCareerProfileQuery":
        self.client.limits.append((self.table_name, value))
        return self

    def execute(self) -> SimpleNamespace:
        if self.client.should_raise:
            raise RuntimeError("database unavailable")

        self.client.executed_tables.append(self.table_name)

        if self.table_name == "cv_analyses":
            return SimpleNamespace(data=self.client.analysis_data)

        if self.table_name == "cv_uploads":
            return SimpleNamespace(data=self.client.upload_data)

        raise AssertionError(f"Unexpected table: {self.table_name}")


class FakeCareerProfileClient:
    def __init__(
        self,
        analysis_data: object,
        upload_data: object = None,
        should_raise: bool = False,
    ) -> None:
        self.analysis_data = analysis_data
        self.upload_data = upload_data
        self.should_raise = should_raise
        self.selects: list[tuple[str, str]] = []
        self.filters: list[tuple[str, str, str]] = []
        self.orders: list[tuple[str, str, bool]] = []
        self.limits: list[tuple[str, int]] = []
        self.executed_tables: list[str] = []

    def table(self, table_name: str) -> FakeCareerProfileQuery:
        return FakeCareerProfileQuery(table_name, self)


def test_get_latest_career_profile_returns_none_without_completed_analysis(monkeypatch) -> None:
    fake_client = FakeCareerProfileClient(analysis_data=[])
    monkeypatch.setattr(career_profile_service, "get_supabase_client", lambda: fake_client)

    profile = career_profile_service.get_latest_career_profile(OWNER_ID)

    assert profile is None
    assert fake_client.executed_tables == ["cv_analyses"]


def test_get_latest_career_profile_builds_runtime_profile(monkeypatch) -> None:
    fake_client = FakeCareerProfileClient(
        analysis_data=[make_analysis()],
        upload_data=[{"id": UPLOAD_ID, "experience_level": "mid"}],
    )
    monkeypatch.setattr(career_profile_service, "get_supabase_client", lambda: fake_client)

    profile = career_profile_service.get_latest_career_profile(OWNER_ID)

    assert profile is not None
    assert profile.user_id == OWNER_ID
    assert profile.analysis_id == ANALYSIS_ID
    assert profile.primary_role == "Backend Software Engineer"
    assert profile.alternative_roles == []
    assert profile.experience_level == "mid"
    assert profile.skills == ["API Design", "Python backend development"]
    assert profile.strengths == ["API design", "Python backend development", "api design"]
    assert profile.weaknesses == ["Cloud deployment depth"]
    assert profile.overall_score == 84
    assert profile.preferred_locations == ["Turkey"]
    assert profile.remote_preference is None
    assert ("cv_analyses", "user_id", OWNER_ID) in fake_client.filters
    assert ("cv_analyses", "status", "completed") in fake_client.filters
    assert ("cv_uploads", "id", UPLOAD_ID) in fake_client.filters
    assert ("cv_uploads", "user_id", OWNER_ID) in fake_client.filters


def test_get_latest_career_profile_prefers_enriched_analysis_fields(monkeypatch) -> None:
    enriched_analysis = {
        **make_analysis(),
        "primary_role": "Python Backend Engineer",
        "alternative_roles": ["Backend Developer", "Software Engineer", "API Engineer", "Extra Role"],
        "top_skills": ["Python", "FastAPI", "PostgreSQL"],
        "preferred_locations": ["Istanbul", "Remote Turkey"],
        "remote_preference": True,
    }
    fake_client = FakeCareerProfileClient(
        analysis_data=[enriched_analysis],
        upload_data=[{"id": UPLOAD_ID, "experience_level": "senior"}],
    )
    monkeypatch.setattr(career_profile_service, "get_supabase_client", lambda: fake_client)

    profile = career_profile_service.get_latest_career_profile(OWNER_ID)

    assert profile is not None
    assert profile.primary_role == "Python Backend Engineer"
    assert profile.alternative_roles == ["Backend Developer", "Software Engineer", "API Engineer"]
    assert profile.skills == ["Python", "FastAPI", "PostgreSQL"]
    assert profile.preferred_locations == ["Istanbul", "Remote Turkey"]
    assert profile.remote_preference is True
    assert profile.experience_level == "senior"


def test_get_latest_career_profile_filters_invalid_top_skills_and_falls_back_safely(monkeypatch) -> None:
    dirty_analysis = {
        **make_analysis(),
        "top_skills": [
            "Hands-on experience with modern frontend and mobile frameworks including React and Flutter",
            "Holds a formal Software Engineering degree from Altınbaş University",
            "Strong project portfolio showcasing practical delivery",
            "React",
        ],
        "strengths": [
            "Hands-on experience with Python and Django",
            "Strong project portfolio showcasing practical delivery",
        ],
    }
    fake_client = FakeCareerProfileClient(
        analysis_data=[dirty_analysis],
        upload_data=[{"id": UPLOAD_ID, "experience_level": "mid"}],
    )
    monkeypatch.setattr(career_profile_service, "get_supabase_client", lambda: fake_client)

    profile = career_profile_service.get_latest_career_profile(OWNER_ID)

    assert profile is not None
    assert profile.skills == ["React", "Flutter"]


def test_get_latest_career_profile_fallback_does_not_use_long_strength_sentences(monkeypatch) -> None:
    dirty_analysis = {
        **make_analysis(),
        "top_skills": [],
        "strengths": [
            "Hands-on experience with modern frontend and mobile frameworks including React and Flutter",
            "Holds a formal Software Engineering degree from Altınbaş University",
        ],
    }
    fake_client = FakeCareerProfileClient(
        analysis_data=[dirty_analysis],
        upload_data=[{"id": UPLOAD_ID, "experience_level": "mid"}],
    )
    monkeypatch.setattr(career_profile_service, "get_supabase_client", lambda: fake_client)

    profile = career_profile_service.get_latest_career_profile(OWNER_ID)

    assert profile is not None
    assert profile.skills == ["React", "Flutter"]


def test_get_latest_career_profile_uses_default_experience_when_upload_missing(monkeypatch) -> None:
    fake_client = FakeCareerProfileClient(analysis_data=make_analysis(), upload_data=[])
    monkeypatch.setattr(career_profile_service, "get_supabase_client", lambda: fake_client)

    profile = career_profile_service.get_latest_career_profile(OWNER_ID)

    assert profile is not None
    assert profile.experience_level == "Not specified"


def test_get_latest_career_profile_returns_none_on_database_error(monkeypatch) -> None:
    fake_client = FakeCareerProfileClient(analysis_data=None, should_raise=True)
    monkeypatch.setattr(career_profile_service, "get_supabase_client", lambda: fake_client)

    profile = career_profile_service.get_latest_career_profile(OWNER_ID)

    assert profile is None


def test_get_latest_career_profile_returns_none_for_blank_user_id() -> None:
    assert career_profile_service.get_latest_career_profile(" ") is None


def test_generate_search_queries_uses_primary_and_deterministic_variations() -> None:
    profile = career_profile_service.CareerProfile(
        user_id=OWNER_ID,
        analysis_id=ANALYSIS_ID,
        primary_role="Backend Software Engineer",
        alternative_roles=[],
        experience_level="mid",
        skills=["Python backend development", "API design"],
        strengths=["Python backend development"],
        weaknesses=[],
        overall_score=84,
        preferred_locations=["Turkey"],
        remote_preference=None,
    )

    queries = career_profile_service.generate_search_queries(profile)

    assert queries == ["Backend Software Engineer", "Backend Developer", "Python Developer"]


def test_generate_search_queries_uses_alternative_roles_before_variations() -> None:
    profile = career_profile_service.CareerProfile(
        user_id=OWNER_ID,
        analysis_id=ANALYSIS_ID,
        primary_role="Product Manager",
        alternative_roles=["Product Owner", "Growth Product Manager", "Product Owner"],
        experience_level="mid",
        skills=[],
        strengths=[],
        weaknesses=[],
        overall_score=84,
        preferred_locations=["Turkey"],
        remote_preference=None,
    )

    queries = career_profile_service.generate_search_queries(profile)

    assert queries == ["Product Manager", "Product Owner", "Growth Product Manager"]
