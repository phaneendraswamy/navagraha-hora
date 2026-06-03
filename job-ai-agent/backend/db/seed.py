from sqlalchemy.orm import Session

from backend.db.models import UserProfile


DEFAULT_PROFILE = {
    "name": "Target User",
    "skills": [
        "Python",
        "SQL",
        "Machine Learning",
        "AI",
        "Streamlit",
        "Snowflake",
        "Power BI",
        "Go",
        "Data Warehousing",
        "NLP",
        "Dashboarding",
    ],
    "preferred_roles": [
        "Data Analyst",
        "AI Engineer",
        "Junior ML Engineer",
        "Prompt Engineer",
        "Analytics Engineer",
    ],
    "preferred_locations": ["Remote", "Hyderabad"],
    "experience_years": 1.0,
    "tooling": ["Streamlit", "Snowflake", "Power BI", "Go", "SQL", "Python"],
}


def ensure_default_profile(db: Session) -> UserProfile:
    profile = db.query(UserProfile).first()
    if profile:
        return profile

    profile = UserProfile(**DEFAULT_PROFILE)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile
