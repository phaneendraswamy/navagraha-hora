from backend.schemas import JobRead


def generate_resume_suggestions(job: JobRead, current_skills: list[str]) -> list[str]:
    """Conservative placeholder for MVP resume guidance.

    Suggestions are limited to wording and prioritization. This function should not invent
    experience, employers, metrics, or credentials.
    """
    insights = job.jd_insights or {}
    required = insights.get("required_skills", [])
    overlap = [skill for skill in required if skill in current_skills]
    missing = [skill for skill in required if skill not in current_skills]

    suggestions = []
    if overlap:
        suggestions.append(f"Prioritize proven experience with {', '.join(overlap[:5])}.")
    if missing:
        suggestions.append(f"Only mention {', '.join(missing[:5])} if you have real project exposure.")
    suggestions.append("Mirror the job title language in the resume summary when truthful.")
    suggestions.append("Keep ATS wording concrete: tools, project context, datasets, and measurable outcomes.")
    return suggestions

