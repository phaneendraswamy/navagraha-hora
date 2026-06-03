from ai_engine.matcher import MatchingEngine, UserProfileData
from backend.schemas import StandardJob


def test_matcher_scores_preferred_remote_ai_role_highly() -> None:
    engine = MatchingEngine()
    job = StandardJob(
        job_id="1",
        source="test",
        title="Junior AI Engineer",
        company="Example",
        location="Remote",
        skills=["Python", "SQL", "Machine Learning", "NLP", "Streamlit"],
        experience_required="1+ years",
        jd_text="Build NLP dashboards with Python, SQL, Streamlit and machine learning.",
    )
    profile = UserProfileData(
        skills=["Python", "SQL", "Machine Learning", "AI", "Streamlit", "NLP"],
        preferred_roles=["AI Engineer"],
        preferred_locations=["Remote", "Hyderabad"],
        experience_years=1,
        tooling=["Python", "SQL", "Streamlit"],
    )

    result = engine.score(job, profile)

    assert result.match_percentage >= 80
    assert "Python" in result.strong_matches
    assert result.component_scores["location_relevance"] == 100


def test_jd_intelligence_flags_shift_red_flag() -> None:
    engine = MatchingEngine()
    job = StandardJob(
        job_id="2",
        source="test",
        title="Data Analyst",
        company="Example",
        location="Hyderabad",
        jd_text="Required SQL and Power BI. This is a night shift role.",
    )

    insights = engine.analyze_jd(job)

    assert "SQL" in insights.required_skills
    assert insights.red_flags

