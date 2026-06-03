import json
import re
from pathlib import Path

import docx
import pdfplumber
from openai import OpenAI

from backend.config import get_settings
from backend.prompts import JD_ANALYSIS_SYSTEM
from backend.schemas import JDAnalysis
from backend.security import sanitize_text


SKILL_CATALOG = {
    "python", "sql", "r", "java", "scala", "spark", "airflow", "dbt", "snowflake",
    "postgresql", "mysql", "mongodb", "sql server", "oracle", "aws", "azure", "gcp", "docker", "kubernetes",
    "power bi", "tableau", "looker", "excel", "pandas", "numpy", "scikit-learn",
    "tensorflow", "pytorch", "nlp", "llm", "rag", "fastapi", "streamlit", "azure databricks",
    "databricks", "data factory", "power query", "dax", "matplotlib", "seaborn", "plotly",
    "machine learning", "deep learning", "generative ai", "openai", "langchain", "hugging face",
    "informatica",
}


ROLE_LABELS = ["Data Analyst", "Data Engineer", "AI Engineer", "ML Engineer", "NLP Engineer", "BI Developer"]


def extract_text_from_file(path: str) -> str:
    file_path = Path(path)
    if file_path.suffix.lower() == ".txt":
        return file_path.read_text(encoding="utf-8", errors="ignore")
    if file_path.suffix.lower() == ".docx":
        document = docx.Document(str(file_path))
        return "\n".join(p.text for p in document.paragraphs)
    if file_path.suffix.lower() == ".pdf":
        with pdfplumber.open(str(file_path)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    raise ValueError("Unsupported JD file type")


def regex_extract(text: str) -> JDAnalysis:
    normalized = sanitize_text(text).lower()
    skills = sorted(skill for skill in SKILL_CATALOG if re.search(rf"\b{re.escape(skill)}\b", normalized))
    years = re.search(r"(\d+\+?)\s*(?:years|yrs)", normalized)
    role = classify_role_by_keywords(normalized)
    responsibilities = re.findall(r"(?:responsibilities|requirements|you will)[:\-\s]+(.{20,220})", text, flags=re.I)
    return JDAnalysis(
        required_skills=skills,
        tools=skills,
        technologies=skills,
        experience_level=years.group(0) if years else "Not specified",
        role_type=role,
        responsibilities=[sanitize_text(item) for item in responsibilities[:6]],
        keywords=skills,
    )


def classify_role_by_keywords(text: str) -> str:
    scores = {
        "Data Analyst": ["dashboard", "visualization", "sql", "excel", "power bi", "tableau", "insights"],
        "Data Engineer": ["pipeline", "etl", "spark", "airflow", "warehouse", "dbt", "snowflake"],
        "AI Engineer": ["llm", "openai", "rag", "agent", "prompt", "generative ai"],
        "ML Engineer": ["model", "mlops", "tensorflow", "pytorch", "scikit-learn", "deployment"],
        "NLP Engineer": ["nlp", "text", "token", "semantic", "language model", "embedding"],
        "BI Developer": ["bi", "semantic model", "power bi", "dax", "looker", "reporting"],
    }
    best = max(scores.items(), key=lambda item: sum(term in text for term in item[1]))
    return best[0] if sum(term in text for term in best[1]) else "Unknown"


def analyze_jd(text: str) -> JDAnalysis:
    base = regex_extract(text)
    settings = get_settings()
    if not settings.openai_api_key:
        return base

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = (
        "Analyze this JD and return JSON with keys: required_skills, responsibilities, tools, "
        "technologies, experience_level, role_type, keywords.\n\nJD:\n"
        f"{sanitize_text(text)[:12000]}"
    )
    try:
        response = client.responses.create(
            model=settings.openai_model,
            input=[
                {"role": "system", "content": JD_ANALYSIS_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            text={"format": {"type": "json_object"}},
        )
        parsed = JDAnalysis.model_validate(json.loads(response.output_text))
        parsed.required_skills = sorted(set(parsed.required_skills + base.required_skills))
        parsed.keywords = sorted(set(parsed.keywords + parsed.required_skills + base.keywords))
        if parsed.role_type == "Unknown":
            parsed.role_type = base.role_type
        return parsed
    except Exception:
        return base
