from backend.schemas import JDAnalysis


def normalize_keyword(keyword: str) -> str:
    return keyword.lower().strip()


def keyword_match(jd: JDAnalysis, candidate_keywords: list[str]) -> tuple[float, list[str], list[str]]:
    required = sorted({normalize_keyword(k) for k in jd.keywords + jd.required_skills if k})
    owned = {normalize_keyword(k) for k in candidate_keywords if k}
    if not required:
        return 0.0, [], []
    matched = sorted(k for k in required if k in owned)
    missing = sorted(k for k in required if k not in owned)
    return round((len(matched) / len(required)) * 100, 2), matched, missing


def ats_score(keyword_percent: float, project_scores: list[float], experience_scores: list[float]) -> float:
    project_component = (sum(project_scores[:3]) / max(len(project_scores[:3]), 1)) * 100 if project_scores else 0
    exp_component = (sum(experience_scores[:3]) / max(len(experience_scores[:3]), 1)) * 100 if experience_scores else 0
    return round((keyword_percent * 0.5) + (project_component * 0.25) + (exp_component * 0.25), 2)


def suggestions(missing_keywords: list[str], ats: float) -> list[str]:
    output: list[str] = []
    if missing_keywords:
        output.append("Missing from stored profile evidence: " + ", ".join(missing_keywords[:8]) + ". Do not add these unless they are truly in your background.")
    if ats < 75:
        output.append("Prioritize the most relevant projects and move matching technologies into the first half of the resume.")
    output.append("Keep bullets accomplishment-focused and avoid adding tools that are not supported by your master profile.")
    return output
