import json

from openai import OpenAI

from backend.config import get_settings
from backend.prompts import RESUME_REWRITE_SYSTEM, SUGGESTIONS_SYSTEM
from backend.security import sanitize_text


def _client() -> OpenAI | None:
    settings = get_settings()
    if not settings.openai_api_key:
        return None
    return OpenAI(api_key=settings.openai_api_key)


def rewrite_bullets(source_bullets: list[str], jd_keywords: list[str], context: str) -> list[str]:
    if not get_settings().use_openai_resume_rewrite:
        return source_bullets
    client = _client()
    if not client or not source_bullets:
        return source_bullets
    prompt = {
        "candidate_facts": source_bullets,
        "jd_keywords": jd_keywords[:30],
        "context": sanitize_text(context)[:4000],
        "task": "Rewrite each candidate fact as a truthful resume bullet. Return JSON: {\"bullets\": [..]}",
    }
    try:
        response = client.responses.create(
            model=get_settings().openai_model,
            input=[
                {"role": "system", "content": RESUME_REWRITE_SYSTEM},
                {"role": "user", "content": json.dumps(prompt)},
            ],
            text={"format": {"type": "json_object"}},
        )
        bullets = json.loads(response.output_text).get("bullets", [])
        return [str(item).strip() for item in bullets if str(item).strip()][: len(source_bullets)]
    except Exception:
        return source_bullets


def generate_summary(profile_facts: str, role: str, jd_keywords: list[str]) -> str:
    if not get_settings().use_openai_resume_rewrite:
        return ""
    client = _client()
    fallback = f"{role} professional with experience across {', '.join(jd_keywords[:6])} and a record of delivering practical, business-focused solutions."
    if not client:
        return fallback
    prompt = (
        "Create a 2-line resume summary using only these candidate facts. "
        f"Target role: {role}. JD keywords: {jd_keywords[:25]}. Facts: {sanitize_text(profile_facts)[:5000]}"
    )
    try:
        response = client.responses.create(
            model=get_settings().openai_model,
            input=[
                {"role": "system", "content": RESUME_REWRITE_SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
        return sanitize_text(response.output_text)[:700]
    except Exception:
        return fallback


def ai_suggestions(payload: dict) -> list[str]:
    client = _client()
    if not client:
        return []
    try:
        response = client.responses.create(
            model=get_settings().openai_model,
            input=[
                {"role": "system", "content": SUGGESTIONS_SYSTEM},
                {"role": "user", "content": json.dumps(payload)[:8000]},
            ],
            text={"format": {"type": "json_object"}},
        )
        return json.loads(response.output_text).get("suggestions", [])[:5]
    except Exception:
        return []
