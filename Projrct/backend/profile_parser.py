import json
import re

from openai import OpenAI

from backend.config import get_settings
from backend.jd_parser import SKILL_CATALOG
from backend.prompts import PROFILE_EXTRACTION_SYSTEM
from backend.schemas import (
    CertificationIn,
    EducationIn,
    ExperienceIn,
    MasterProfileIn,
    PersonalDetails,
    ProjectIn,
    SkillIn,
)
from backend.security import sanitize_text


def _find_first(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.I)
    return match.group(0).strip() if match else None


def _name_from_text(text: str, email: str | None) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines[:8]:
        if "@" not in line and len(line.split()) in {2, 3} and len(line) < 80:
            return line
    if email:
        return email.split("@")[0].replace(".", " ").replace("_", " ").title()
    return "Candidate"


def fallback_extract_profile(text: str) -> MasterProfileIn:
    cleaned = sanitize_text(text)
    email = _find_first(r"[\w.\-+]+@[\w.\-]+\.\w+", cleaned)
    phone = _find_first(r"(?:\+?\d[\d\s().-]{8,}\d)", cleaned)
    linkedin = _find_first(r"https?://(?:www\.)?linkedin\.com/[^\s,)]+", cleaned)
    github = _find_first(r"https?://(?:www\.)?github\.com/[^\s,)]+", cleaned)
    portfolio = _find_first(r"https?://(?!.*(?:linkedin|github))[^\s,)]+", cleaned)
    name = _name_from_text(text, email)

    normalized = cleaned.lower()
    found_skills = sorted(skill for skill in SKILL_CATALOG if re.search(rf"\b{re.escape(skill)}\b", normalized))
    skills = [SkillIn(category=_skill_category(skill), name=_format_skill(skill)) for skill in found_skills]

    return MasterProfileIn(
        personal=PersonalDetails(
            full_name=name,
            email=email or "candidate@example.com",
            phone=phone,
            linkedin_url=linkedin,
            github_url=github,
            portfolio_url=portfolio,
            location=None,
        ),
        education=_fallback_education(text),
        skills=skills,
        experiences=_fallback_experiences(text, found_skills),
        projects=_fallback_projects(text, found_skills),
        certifications=_fallback_certifications(text),
    )


def _skill_category(skill: str) -> str:
    if skill in {"python", "r", "java", "scala", "sql"}:
        return "Programming"
    if skill in {"postgresql", "mysql", "mongodb", "snowflake", "sql server", "oracle"}:
        return "Databases"
    if skill in {"aws", "azure", "gcp", "docker", "kubernetes"}:
        return "Cloud"
    if skill in {"pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "nlp", "llm", "rag", "machine learning", "deep learning", "generative ai", "openai", "langchain", "hugging face"}:
        return "AI/ML"
    if skill in {"power bi", "tableau", "looker", "excel", "power query", "dax", "matplotlib", "seaborn", "plotly"}:
        return "Visualization"
    if skill in {"azure databricks", "databricks", "data factory", "informatica"}:
        return "ETL Tools"
    return "Frameworks"


def _format_skill(skill: str) -> str:
    names = {
        "sql": "SQL",
        "r": "R",
        "aws": "AWS",
        "gcp": "GCP",
        "nlp": "NLP",
        "llm": "LLM",
        "rag": "RAG",
        "power bi": "Power BI",
        "dax": "DAX",
        "openai": "OpenAI",
        "fastapi": "FastAPI",
        "postgresql": "PostgreSQL",
        "numpy": "NumPy",
        "pandas": "Pandas",
        "scikit-learn": "scikit-learn",
    }
    return names.get(skill, skill.title())


def _clean_block(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" -:*•\t")


def _section_lines(text: str, headers: set[str], stops: set[str]) -> list[str]:
    lines = [line.strip(" -*\t") for line in text.splitlines() if line.strip()]
    captured: list[str] = []
    active = False
    for line in lines:
        lower = line.lower().strip(":")
        if lower in headers:
            active = True
            continue
        if active and lower in stops:
            break
        if active:
            captured.append(line)
    return captured


def _fallback_projects(text: str, skills: list[str]) -> list[ProjectIn]:
    project_blocks = _project_blocks(text)
    if not project_blocks:
        lines = [line.strip(" -*\t") for line in text.splitlines() if len(line.strip()) > 20]
        project_blocks = [
            line for line in lines
            if re.search(r"\b(project|built|developed|created|designed|implemented|dashboard|pipeline|chatbot|model|analysis|forecast|classification|etl)\b", line, flags=re.I)
        ]
    projects: list[ProjectIn] = []
    for index, block in enumerate(project_blocks[:8], start=1):
        tech = [skill for skill in skills if skill in block.lower()]
        projects.append(ProjectIn(
            name=_project_name(block, index),
            domain=_domain_from_text(block),
            description=_clean_block(block)[:1400],
            technologies=[_format_skill(skill) for skill in tech],
            business_impact=None,
            keywords=tech,
            role_tags=_role_tags_from_text(block),
        ))
    return projects


def _project_blocks(text: str) -> list[str]:
    lines = _section_lines(
        text,
        {"projects", "academic projects", "personal projects", "project experience"},
        {"experience", "work experience", "professional experience", "education", "skills", "certifications", "summary", "profile", "strengths"},
    )
    if not lines:
        return []
    blocks: list[str] = []
    current: list[str] = []
    for line in lines:
        starts_new = _looks_like_project_title(line)
        if current and starts_new:
            blocks.append(" ".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append(" ".join(current))
    return _dedupe_blocks(blocks)


def _looks_like_project_title(line: str) -> bool:
    clean = line.strip()
    if re.search(r"^project\s*\d+", clean, flags=re.I) or re.search(r"^\d+[\).]\s+", clean):
        return True
    if len(clean) > 95 or clean.endswith((".", ";")):
        return False
    title_terms = ["system", "dashboard", "analysis", "detection", "analytics", "pipeline", "chatbot", "model"]
    return any(term in clean.lower() for term in title_terms)


def _dedupe_blocks(blocks: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for block in blocks:
        clean = _clean_block(block)
        key = clean.lower()
        if len(clean) > 25 and key not in seen:
            seen.add(key)
            output.append(clean)
    return output


def _project_name(text: str, index: int) -> str:
    clean = _clean_block(text)
    if ":" in clean and len(clean.split(":")[0]) < 70:
        return clean.split(":")[0].strip()
    action_split = re.search(r"\b(Designed|Built|Created|Developed|Implemented|Utilized)\b", clean)
    if action_split and action_split.start() > 8:
        return clean[: action_split.start()].strip(" -")
    title = re.sub(r"^(project\s*\d+[\).:-]*|built|developed|created|designed|implemented)\s+", "", clean, flags=re.I)
    return " ".join(title.split()[:7]).strip(",.") or f"Project {index}"


def _domain_from_text(text: str) -> str:
    lower = text.lower()
    if any(term in lower for term in ["llm", "rag", "chatbot", "openai", "nlp", "generative ai"]):
        return "AI/NLP"
    if any(term in lower for term in ["dashboard", "power bi", "tableau", "looker", "excel"]):
        return "Business Intelligence"
    if any(term in lower for term in ["pipeline", "etl", "spark", "airflow", "warehouse", "informatica", "databricks"]):
        return "Data Engineering"
    if any(term in lower for term in ["model", "prediction", "classification", "machine learning"]):
        return "Machine Learning"
    return "Data Analytics"


def _role_tags_from_text(text: str) -> list[str]:
    lower = text.lower()
    tags: list[str] = []
    if any(term in lower for term in ["dashboard", "sql", "excel", "analytics", "insight"]):
        tags.append("Data Analyst")
    if any(term in lower for term in ["pipeline", "etl", "warehouse", "spark", "airflow", "informatica", "databricks"]):
        tags.append("Data Engineer")
    if any(term in lower for term in ["llm", "rag", "openai", "chatbot", "agent", "generative ai"]):
        tags.append("AI Engineer")
    if any(term in lower for term in ["model", "prediction", "scikit-learn", "tensorflow", "pytorch"]):
        tags.append("ML Engineer")
    if any(term in lower for term in ["nlp", "semantic", "embedding", "language"]):
        tags.append("NLP Engineer")
    if any(term in lower for term in ["power bi", "tableau", "looker", "dax", "report"]):
        tags.append("BI Developer")
    return tags or ["Data Analyst"]


def _fallback_experiences(text: str, skills: list[str]) -> list[ExperienceIn]:
    experiences: list[ExperienceIn] = []
    for block in _experience_blocks(text)[:5]:
        role, company, duration, details = _parse_experience_block(block)
        if not role and not company:
            continue
        experiences.append(ExperienceIn(
            company=company or "Not specified",
            role=role or "Professional Experience",
            duration=duration,
            responsibilities=details[:7],
            achievements=[],
            technologies=[_format_skill(skill) for skill in skills[:14]],
        ))
    return experiences


def _experience_blocks(text: str) -> list[str]:
    section = _section_lines(
        text,
        {"experience", "internship experience", "work experience", "professional experience", "employment", "employment history"},
        {"projects", "academic projects", "personal projects", "education", "skills", "certifications", "summary", "profile", "strengths"},
    )
    lines = section or [line.strip(" -*\t") for line in text.splitlines() if line.strip()]
    blocks: list[str] = []
    current: list[str] = []
    role_pattern = re.compile(r"\b(analyst|engineer|developer|intern|associate|consultant|specialist|manager)\b", flags=re.I)
    for line in lines:
        starts_new_role = bool(role_pattern.search(line) and re.search(r"\s[-–|@]\s| at ", line, flags=re.I))
        if starts_new_role and current:
            blocks.append(" ".join(current))
            current = [line]
        elif starts_new_role:
            current = [line]
        elif current:
            current.append(line)
    if current:
        blocks.append(" ".join(current))
    return _dedupe_blocks(blocks)


def _parse_experience_block(block: str) -> tuple[str, str, str, list[str]]:
    clean = _clean_block(block)
    duration_match = re.search(
        r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{2,4}\s*[-–]\s*(?:Present|Current|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{2,4}|\d{2,4})|\d{4}\s*[-–]\s*(?:Present|Current|\d{4}))",
        clean,
        flags=re.I,
    )
    duration = duration_match.group(1) if duration_match else ""
    without_duration = clean.replace(duration, "").strip(" -–|") if duration else clean
    first_sentence = re.split(r"(?<=[.!?])\s+", without_duration, maxsplit=1)[0]
    role = ""
    company = ""
    for separator in [" – ", " - ", " | ", " @ "]:
        if separator in first_sentence:
            role, company = [part.strip() for part in first_sentence.split(separator, 1)]
            break
    role_terms = re.compile(r"\b(analyst|engineer|developer|intern|associate|consultant|specialist|manager)\b", flags=re.I)
    if role and company and not role_terms.search(role) and role_terms.search(company):
        role, company = company, role
    if not role and re.search(r"\bat\b", first_sentence, flags=re.I):
        role, company = [part.strip() for part in re.split(r"\bat\b", first_sentence, maxsplit=1, flags=re.I)]
    company_tail = ""
    if company:
        company, company_tail = _split_company_tail(company)
    role_tail = ""
    if role:
        role, role_tail = _split_company_tail(role)
    details_text = without_duration
    if role and company:
        details_text = details_text.replace(first_sentence, "", 1).strip()
        details_text = " ".join(part for part in [role_tail, company_tail, details_text] if part).strip()
    details = [
        part.strip(" -*•\t")
        for part in re.split(r"(?<=[.!?])\s+|;|\n", details_text)
        if len(part.strip(" -*•\t")) > 12
    ]
    if not details and details_text and details_text != first_sentence:
        details = [details_text]
    return role[:120], company[:120], duration, details[:8]


def _split_company_tail(company_text: str) -> tuple[str, str]:
    action_match = re.search(
        r"\b(Worked|Built|Developed|Created|Designed|Implemented|Managed|Automated|Analyzed|Handled|Supported|Collaborated)\b",
        company_text,
        flags=re.I,
    )
    if not action_match:
        return company_text.strip(" -–|"), ""
    company = company_text[: action_match.start()].strip(" -–|•")
    tail = company_text[action_match.start():].strip()
    return company, tail


def _fallback_education(text: str) -> list[EducationIn]:
    lines = [line.strip(" -*\t") for line in text.splitlines() if line.strip()]
    education_lines = [
        line for line in lines
            if re.search(r"\b(bachelor|master|b\.?tech|m\.?s\.?|degree|university|college|school|academic profile|post graduate|diploma|engineering)\b", line, flags=re.I)
    ]
    education: list[EducationIn] = []
    for line in education_lines[:4]:
        clean = _clean_block(line)
        clean = re.sub(r"^academic profile\s*", "", clean, flags=re.I).strip(" -•")
        if not clean:
            continue
        degree = clean
        institution = ""
        for separator in [" – ", " - ", " | "]:
            if separator in clean:
                degree, institution = [part.strip() for part in clean.split(separator, 1)]
                break
        education.append(EducationIn(degree=degree.strip(" -•")[:170], institution=institution.strip(" -•")[:170] or ""))
    return education


def _fallback_certifications(text: str) -> list[CertificationIn]:
    lines = [line.strip(" -*\t") for line in text.splitlines() if line.strip()]
    cert_lines = [line for line in lines if re.search(r"\b(certification|certified|certificate)\b", line, flags=re.I)]
    return [CertificationIn(name=line[:170]) for line in cert_lines[:5]]


def extract_profile(text: str) -> MasterProfileIn:
    fallback = fallback_extract_profile(text)
    settings = get_settings()
    if not settings.openai_api_key or not settings.use_openai_profile_extraction:
        return fallback

    client = OpenAI(api_key=settings.openai_api_key)
    schema_hint = {
        "personal": {
            "full_name": "",
            "email": "",
            "phone": "",
            "linkedin_url": None,
            "github_url": None,
            "portfolio_url": None,
            "location": None,
        },
        "education": [{"degree": "", "institution": "", "duration": None, "gpa": None}],
        "skills": [{"category": "", "name": "", "proficiency": None}],
        "experiences": [{"company": "", "role": "", "duration": "", "responsibilities": [], "achievements": [], "technologies": []}],
        "projects": [{"name": "", "domain": "", "description": "", "technologies": [], "business_impact": None, "keywords": [], "role_tags": []}],
        "certifications": [{"name": "", "organization": None, "skills_covered": []}],
    }
    prompt = {
        "task": "Extract a truthful master profile from this raw candidate content.",
        "schema": schema_hint,
        "candidate_content": sanitize_text(text)[:18000],
    }
    try:
        response = client.responses.create(
            model=settings.openai_model,
            input=[
                {"role": "system", "content": PROFILE_EXTRACTION_SYSTEM},
                {"role": "user", "content": json.dumps(prompt)},
            ],
            text={"format": {"type": "json_object"}},
        )
        extracted = MasterProfileIn.model_validate(json.loads(response.output_text))
        if not extracted.personal.email:
            extracted.personal.email = fallback.personal.email
        if not extracted.personal.full_name or extracted.personal.full_name == "Candidate":
            extracted.personal.full_name = fallback.personal.full_name
        if not extracted.experiences and fallback.experiences:
            extracted.experiences = fallback.experiences
        if len(extracted.projects) < len(fallback.projects):
            extracted.projects = fallback.projects
        if not extracted.skills and fallback.skills:
            extracted.skills = fallback.skills
        return extracted
    except Exception:
        return fallback
