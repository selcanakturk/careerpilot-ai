import os

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-api-key")
os.environ.setdefault("OPENAI_MODEL", "gpt-5-mini")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-api-key")
os.environ.setdefault("GEMINI_MODEL", "gemini-2.5-flash")

from app.schemas.job import ExternalJobPosting
from app.services.career_profile_service import CareerProfile
from app.services.job_match_service import calculate_job_match, display_skill_label, generate_match_reasons, normalize_text


OWNER_ID = "11111111-1111-1111-1111-111111111111"
ANALYSIS_ID = "22222222-2222-2222-2222-222222222222"


def make_profile(
    primary_role: str = "Backend Software Engineer",
    alternative_roles: list[str] | None = None,
    skills: list[str] | None = None,
    experience_level: str = "mid",
) -> CareerProfile:
    return CareerProfile(
        user_id=OWNER_ID,
        analysis_id=ANALYSIS_ID,
        primary_role=primary_role,
        alternative_roles=alternative_roles or ["Backend Developer"],
        experience_level=experience_level,
        skills=skills or ["Python", "FastAPI", "REST API"],
        strengths=[],
        weaknesses=[],
        overall_score=84,
        preferred_locations=["Turkey"],
        remote_preference=None,
    )


def make_job(
    title: str = "Backend Software Engineer",
    description: str = "Build Python services with FastAPI and REST APIs.",
) -> ExternalJobPosting:
    return ExternalJobPosting(
        external_id="job-1",
        source="jooble",
        title=title,
        company_name="Acme",
        location="Istanbul",
        description=description,
        source_url="https://example.com/job-1",
    )


def test_normalize_text_handles_case_punctuation_and_plural_forms() -> None:
    assert normalize_text(" REST APIs,  ") == "rest api"


def test_calculate_job_match_exact_skill_match() -> None:
    result = calculate_job_match(
        job=make_job(description="Python and FastAPI required."),
        career_profile=make_profile(skills=["Python"]),
    )

    assert result.matched_skills == ["Python"]
    assert "Your Python experience is relevant." in result.match_reasons
    assert 0 <= result.match_score <= 100


def test_calculate_job_match_case_insensitive_skill_match() -> None:
    result = calculate_job_match(
        job=make_job(description="Experience with rest api design is required."),
        career_profile=make_profile(skills=["REST API"]),
    )

    assert result.matched_skills == ["REST API"]


def test_calculate_job_match_partial_skill_match() -> None:
    result = calculate_job_match(
        job=make_job(description="We use Fast API services."),
        career_profile=make_profile(skills=["FastAPI"]),
    )

    assert result.matched_skills == ["FastAPI"]


def test_calculate_job_match_node_aliases_match() -> None:
    result = calculate_job_match(
        job=make_job(description="Nodejs services and APIs."),
        career_profile=make_profile(skills=["Node.js"]),
    )

    assert result.matched_skills == ["Node.js"]


def test_calculate_job_match_react_aliases_match() -> None:
    result = calculate_job_match(
        job=make_job(description="React.js frontend work."),
        career_profile=make_profile(skills=["React"]),
    )

    assert result.matched_skills == ["React"]


def test_calculate_job_match_rest_api_aliases_match() -> None:
    result = calculate_job_match(
        job=make_job(description="Build REST APIs for partner integrations."),
        career_profile=make_profile(skills=["REST API"]),
    )

    assert result.matched_skills == ["REST API"]


def test_calculate_job_match_javascript_and_typescript_aliases_match() -> None:
    result = calculate_job_match(
        job=make_job(description="JS and TS are used in the frontend stack."),
        career_profile=make_profile(skills=["JavaScript", "TypeScript"]),
    )

    assert result.matched_skills == ["JavaScript", "TypeScript"]


def test_calculate_job_match_postgres_aliases_match() -> None:
    result = calculate_job_match(
        job=make_job(description="Postgre SQL database experience required."),
        career_profile=make_profile(skills=["PostgreSQL"]),
    )

    assert result.matched_skills == ["PostgreSQL"]


def test_calculate_job_match_primary_role_title_match_scores_higher_than_alternative() -> None:
    primary_result = calculate_job_match(
        job=make_job(title="Backend Software Engineer"),
        career_profile=make_profile(),
    )
    alternative_result = calculate_job_match(
        job=make_job(title="Backend Developer"),
        career_profile=make_profile(),
    )

    assert primary_result.match_score > alternative_result.match_score


def test_calculate_job_match_experience_level_compatibility() -> None:
    senior_result = calculate_job_match(
        job=make_job(title="Senior Backend Software Engineer", description="Senior Python engineer."),
        career_profile=make_profile(experience_level="senior"),
    )
    junior_result = calculate_job_match(
        job=make_job(title="Senior Backend Software Engineer", description="Senior Python engineer."),
        career_profile=make_profile(experience_level="junior"),
    )

    assert senior_result.match_score > junior_result.match_score


def test_calculate_job_match_score_stays_between_zero_and_one_hundred() -> None:
    result = calculate_job_match(
        job=make_job(title="Unrelated Role", description="Unrelated work."),
        career_profile=make_profile(skills=["Python", "FastAPI"]),
    )

    assert 0 <= result.match_score <= 100


def test_calculate_job_match_deduplicates_skills_and_extracts_conservative_missing_skills() -> None:
    result = calculate_job_match(
        job=make_job(description="Python, Docker and AWS experience required."),
        career_profile=make_profile(skills=["Python", "python", "FastAPI"]),
    )

    assert result.matched_skills == ["Python"]
    assert "Docker" in result.missing_skills
    assert "AWS" in result.missing_skills
    assert len(result.missing_skills) == len(set(result.missing_skills))


def test_calculate_job_match_deduplicates_aliases_to_single_display_skill() -> None:
    result = calculate_job_match(
        job=make_job(description="Node.js, NodeJS, JavaScript, JS, React.js and REST APIs."),
        career_profile=make_profile(skills=["NodeJS", "node js", "Javascript", "JS", "ReactJS", "REST API"]),
    )

    assert result.matched_skills == ["Node.js", "JavaScript", "React", "REST API"]


def test_calculate_job_match_prevents_matched_and_missing_alias_overlap() -> None:
    result = calculate_job_match(
        job=make_job(description="NodeJS, React.js and Postgres required."),
        career_profile=make_profile(skills=["Node.js", "React", "PostgreSQL"]),
    )

    assert result.matched_skills == ["Node.js", "React", "PostgreSQL"]
    assert "Node.js" not in result.missing_skills
    assert "React" not in result.missing_skills
    assert "PostgreSQL" not in result.missing_skills


def test_display_skill_label_uses_canonical_alias_label() -> None:
    assert display_skill_label("node js") == "Node.js"
    assert display_skill_label("JS") == "JavaScript"
    assert display_skill_label("TS") == "TypeScript"
    assert display_skill_label("ReactJS") == "React"
    assert display_skill_label("REST APIs") == "REST API"
    assert display_skill_label("Postgre Sql") == "PostgreSQL"


def test_generate_match_reasons_includes_primary_role_reason() -> None:
    reasons = generate_match_reasons(
        job=make_job(title="Backend Software Engineer"),
        profile=make_profile(skills=[]),
    )

    assert reasons[0] == "This role matches your primary career goal."


def test_generate_match_reasons_includes_alternative_role_reason() -> None:
    reasons = generate_match_reasons(
        job=make_job(title="Backend Developer"),
        profile=make_profile(primary_role="Software Engineer", alternative_roles=["Backend Developer"], skills=["Ruby"]),
    )

    assert reasons == ["Matches one of your preferred roles."]


def test_generate_match_reasons_includes_skill_reason() -> None:
    reasons = generate_match_reasons(
        job=make_job(title="Unrelated Role", description="React and Django are required."),
        profile=make_profile(primary_role="Product Manager", alternative_roles=[], skills=["React", "Django"]),
    )

    assert reasons == ["Your React experience is relevant.", "Your Django experience is relevant."]


def test_generate_match_reasons_uses_clean_skill_display_label() -> None:
    reasons = generate_match_reasons(
        job=make_job(title="Unrelated Role", description="NodeJS and React.js are required."),
        profile=make_profile(primary_role="Product Manager", alternative_roles=[], skills=["node js", "ReactJS"]),
    )

    assert reasons == ["Your Node.js experience is relevant.", "Your React experience is relevant."]


def test_generate_match_reasons_includes_experience_reason() -> None:
    reasons = generate_match_reasons(
        job=make_job(title="Mid-level Platform Analyst", description="Mid-level role."),
        profile=make_profile(primary_role="Product Manager", alternative_roles=[], skills=[], experience_level="mid"),
    )

    assert reasons == ["This role fits your experience level."]


def test_generate_match_reasons_returns_empty_when_no_signal_matches() -> None:
    reasons = generate_match_reasons(
        job=make_job(title="Sales Manager", description="Sales operations role."),
        profile=make_profile(primary_role="Backend Engineer", alternative_roles=[], skills=["Python"], experience_level=""),
    )

    assert reasons == []


def test_generate_match_reasons_limits_to_three_items() -> None:
    reasons = generate_match_reasons(
        job=make_job(description="Python, FastAPI and REST API required for a mid-level backend role."),
        profile=make_profile(skills=["Python", "FastAPI", "REST API"], experience_level="mid"),
    )

    assert len(reasons) == 3
