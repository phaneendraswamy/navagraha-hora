import json
import re
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.ats_engine import ats_score, keyword_match, suggestions
from backend.config import get_settings
from backend.database import get_db, init_db
from backend.jd_parser import analyze_jd
from backend.llm_rewriter import generate_summary, rewrite_bullets
from backend.models import Certification, Education, Experience, JDHistory, Project, Resume, Skill, User
from backend.profile_parser import extract_profile
from backend.resume_generator import build_preview, export_docx, export_pdf
from backend.schemas import GenerateResumeRequest, GeneratedResumeResponse, MasterProfileIn, ProfileIngestResponse
from backend.security import sanitize_text, sanitize_text_preserve_lines, validate_upload
from backend.semantic_matcher import rank_items


app = FastAPI(title="AI Resume Intelligence System", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "openai_configured": bool(get_settings().openai_api_key)}


def _save_profile(profile: MasterProfileIn, db: Session) -> User:
    user = db.query(User).filter(User.email == profile.personal.email).one_or_none()
    if not user:
        user = User(**profile.personal.model_dump(mode="json"))
        db.add(user)
        db.flush()
    else:
        for key, value in profile.personal.model_dump(mode="json").items():
            setattr(user, key, value)
        db.query(Skill).filter_by(user_id=user.id).delete()
        db.query(Project).filter_by(user_id=user.id).delete()
        db.query(Experience).filter_by(user_id=user.id).delete()
        db.query(Certification).filter_by(user_id=user.id).delete()
        db.query(Education).filter_by(user_id=user.id).delete()

    for skill in profile.skills:
        db.add(Skill(user_id=user.id, **skill.model_dump()))
    for project in profile.projects:
        db.add(Project(
            user_id=user.id,
            name=project.name,
            domain=project.domain,
            description=project.description,
            technologies=", ".join(project.technologies),
            business_impact=project.business_impact,
            keywords=", ".join(project.keywords),
            role_tags=", ".join(project.role_tags),
        ))
    for exp in profile.experiences:
        db.add(Experience(
            user_id=user.id,
            company=exp.company,
            role=exp.role,
            duration=exp.duration,
            responsibilities="\n".join(exp.responsibilities),
            achievements="\n".join(exp.achievements),
            technologies=", ".join(exp.technologies),
        ))
    for cert in profile.certifications:
        db.add(Certification(user_id=user.id, name=cert.name, organization=cert.organization, skills_covered=", ".join(cert.skills_covered)))
    for edu in profile.education:
        db.add(Education(user_id=user.id, **edu.model_dump()))
    db.commit()
    db.refresh(user)
    return user


def _profile_payload(user: User) -> dict:
    return {
        "id": user.id,
        "personal": {
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "linkedin_url": user.linkedin_url,
            "github_url": user.github_url,
            "portfolio_url": user.portfolio_url,
            "location": user.location,
        },
        "skills": [{"category": s.category, "name": s.name, "proficiency": s.proficiency} for s in user.skills],
        "projects": [
            {
                "id": p.id,
                "name": p.name,
                "domain": p.domain,
                "description": p.description,
                "technologies": [t.strip() for t in p.technologies.split(",") if t.strip()],
                "business_impact": p.business_impact,
                "keywords": [k.strip() for k in p.keywords.split(",") if k.strip()],
                "role_tags": [r.strip() for r in p.role_tags.split(",") if r.strip()],
            }
            for p in user.projects
        ],
        "experiences": [
            {
                "id": e.id,
                "company": e.company,
                "role": e.role,
                "duration": e.duration,
                "responsibilities": [line for line in e.responsibilities.splitlines() if line.strip()],
                "achievements": [line for line in e.achievements.splitlines() if line.strip()],
                "technologies": [t.strip() for t in e.technologies.split(",") if t.strip()],
            }
            for e in user.experiences
        ],
        "certifications": [{"name": c.name, "organization": c.organization, "skills_covered": c.skills_covered} for c in user.certifications],
        "education": [{"degree": e.degree, "institution": e.institution, "duration": e.duration, "gpa": e.gpa} for e in user.education],
    }


@app.post("/profile")
def upsert_profile(profile: MasterProfileIn, db: Session = Depends(get_db)) -> dict:
    user = _save_profile(profile, db)
    return {"user_id": user.id, "message": "Profile saved"}


@app.get("/profile/{user_id}")
def get_profile(user_id: int, db: Session = Depends(get_db)) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User profile not found")
    return _profile_payload(user)


@app.post("/profile/ingest", response_model=ProfileIngestResponse)
def ingest_profile(payload: dict, db: Session = Depends(get_db)) -> ProfileIngestResponse:
    text = sanitize_text_preserve_lines(payload.get("profile_text", ""))
    if len(text) < 40:
        raise HTTPException(status_code=400, detail="Profile text is too short")
    profile = extract_profile(text)
    user = _save_profile(profile, db)
    counts = {
        "skills": len(profile.skills),
        "projects": len(profile.projects),
        "experiences": len(profile.experiences),
        "education": len(profile.education),
        "certifications": len(profile.certifications),
    }
    return ProfileIngestResponse(user_id=user.id, profile=profile, extracted_counts=counts, message="Profile knowledge base updated")


@app.post("/profile/upload", response_model=ProfileIngestResponse)
async def upload_profile(file: UploadFile = File(...), db: Session = Depends(get_db)) -> ProfileIngestResponse:
    content = await file.read()
    try:
        validate_upload(file.filename or "", len(content), get_settings().upload_max_mb)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    safe_name = Path(file.filename or "profile.txt").name
    temp = Path("exports") / f"profile_{safe_name}"
    temp.parent.mkdir(exist_ok=True)
    temp.write_bytes(content)
    from backend.jd_parser import extract_text_from_file

    text = sanitize_text_preserve_lines(extract_text_from_file(str(temp)))
    temp.unlink(missing_ok=True)
    profile = extract_profile(text)
    user = _save_profile(profile, db)
    counts = {
        "skills": len(profile.skills),
        "projects": len(profile.projects),
        "experiences": len(profile.experiences),
        "education": len(profile.education),
        "certifications": len(profile.certifications),
    }
    return ProfileIngestResponse(user_id=user.id, profile=profile, extracted_counts=counts, message="Profile knowledge base updated")


@app.post("/profile/upload-many", response_model=ProfileIngestResponse)
async def upload_many_profiles(
    files: list[UploadFile] = File(...),
    profile_text: str = Form(""),
    db: Session = Depends(get_db),
) -> ProfileIngestResponse:
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one profile file")
    from backend.jd_parser import extract_text_from_file

    extracted_parts: list[str] = []
    for file in files:
        content = await file.read()
        try:
            validate_upload(file.filename or "", len(content), get_settings().upload_max_mb)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        safe_name = Path(file.filename or "profile.txt").name
        temp = Path("exports") / f"profile_{safe_name}"
        temp.parent.mkdir(exist_ok=True)
        temp.write_bytes(content)
        extracted_parts.append(extract_text_from_file(str(temp)))
        temp.unlink(missing_ok=True)

    if profile_text.strip():
        extracted_parts.append(f"\n\nPASTED CANDIDATE NOTES\n{profile_text}")
    text = sanitize_text_preserve_lines("\n".join(extracted_parts))
    profile = extract_profile(text)
    user = _save_profile(profile, db)
    counts = {
        "skills": len(profile.skills),
        "projects": len(profile.projects),
        "experiences": len(profile.experiences),
        "education": len(profile.education),
        "certifications": len(profile.certifications),
    }
    return ProfileIngestResponse(user_id=user.id, profile=profile, extracted_counts=counts, message="Profile knowledge base updated")


@app.post("/jd/analyze")
def analyze_job_description(payload: dict) -> dict:
    text = sanitize_text(payload.get("jd_text", ""))
    if len(text) < 30:
        raise HTTPException(status_code=400, detail="JD text is too short")
    return analyze_jd(text).model_dump()


@app.post("/jd/upload")
async def upload_jd(file: UploadFile = File(...)) -> dict:
    content = await file.read()
    try:
        validate_upload(file.filename or "", len(content), get_settings().upload_max_mb)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    safe_name = Path(file.filename or "jd.txt").name
    temp = Path("exports") / f"upload_{safe_name}"
    temp.parent.mkdir(exist_ok=True)
    temp.write_bytes(content)
    from backend.jd_parser import extract_text_from_file

    text = sanitize_text(extract_text_from_file(str(temp)))
    temp.unlink(missing_ok=True)
    return {"text": text, "analysis": analyze_jd(text).model_dump()}


def _profile_to_resume_data(user: User, jd_text: str, template_name: str, target_role: str | None) -> tuple[dict, dict]:
    jd = analyze_jd(jd_text)
    role = target_role or jd.role_type
    candidate_keywords = [skill.name for skill in user.skills]
    for project in user.projects:
        candidate_keywords.extend((project.technologies + "," + project.keywords).split(","))
    for exp in user.experiences:
        candidate_keywords.extend(exp.technologies.split(","))

    keyword_percent, matched, missing = keyword_match(jd, candidate_keywords)
    project_items = [
        {
            "name": p.name,
            "text": " ".join([p.name, p.domain or "", p.description, p.technologies, p.business_impact or "", p.keywords, p.role_tags]),
            "source": p,
        }
        for p in user.projects
    ]
    exp_items = [
        {"name": e.company, "text": " ".join([e.role, e.company, e.responsibilities, e.achievements, e.technologies]), "source": e}
        for e in user.experiences
    ]
    role_project_items = [
        item for item in project_items
        if role != "Unknown" and role.lower() in item["source"].role_tags.lower()
    ]
    ranking_pool = role_project_items if role_project_items else project_items
    ranked_projects = rank_items(jd_text, ranking_pool, "text", top_k=3)
    if ranked_projects and any(item["relevance_score"] >= 0.25 for item in ranked_projects):
        ranked_projects = [item for item in ranked_projects if item["relevance_score"] >= 0.18] or ranked_projects[:1]
    ranked_exps = rank_items(jd_text, exp_items, "text", top_k=3)
    score = ats_score(keyword_percent, [p["relevance_score"] for p in ranked_projects], [e["relevance_score"] for e in ranked_exps])

    profile_facts = " ".join([p["text"] for p in project_items] + [e["text"] for e in exp_items])
    summary = generate_summary(profile_facts, role, jd.keywords) or _evidence_summary(user, role, matched)
    skills_ordered = _ordered_skills(user.skills, matched)

    resume_data = {
        "personal": {
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "linkedin_url": user.linkedin_url,
            "github_url": user.github_url,
            "portfolio_url": user.portfolio_url,
            "location": user.location,
        },
        "summary": summary,
        "skills": [skill["name"] for skill in skills_ordered[:32]],
        "skill_groups": _skill_groups(skills_ordered[:32]),
        "experiences": [],
        "projects": [],
        "certifications": [{"name": c.name, "organization": c.organization} for c in user.certifications],
        "education": [{"degree": e.degree, "institution": e.institution, "duration": e.duration} for e in user.education],
        "strengths": _strengths_for_resume(user, matched),
    }
    for item in ranked_exps:
        exp = item["source"]
        bullets = [b for b in (exp.achievements + "\n" + exp.responsibilities).splitlines() if b.strip()][:4]
        resume_data["experiences"].append({
            "company": exp.company,
            "role": exp.role,
            "duration": exp.duration,
            "bullets": rewrite_bullets(bullets, jd.keywords, jd_text),
        })
    for item in ranked_projects:
        project = item["source"]
        bullets = _project_bullets(project.description)
        if project.business_impact:
            bullets.append(project.business_impact)
        resume_data["projects"].append({
            "name": project.name,
            "technologies": [t.strip() for t in project.technologies.split(",") if t.strip()],
            "bullets": rewrite_bullets(bullets, jd.keywords, jd_text),
        })
    metadata = {
        "jd": jd,
        "score": score,
        "keyword_percent": keyword_percent,
        "matched": matched,
        "missing": missing,
        "selected_projects": [p["source"].name for p in ranked_projects],
        "selected_evidence": [
            {
                "type": "project",
                "name": p["source"].name,
                "relevance_score": p["relevance_score"],
                "evidence": p["text"][:700],
            }
            for p in ranked_projects
        ] + [
            {
                "type": "experience",
                "name": f"{e['source'].role} - {e['source'].company}",
                "relevance_score": e["relevance_score"],
                "evidence": e["text"][:700],
            }
            for e in ranked_exps
        ],
        "role": role,
    }
    return resume_data, metadata


def _ordered_skills(skills: list[Skill], matched: list[str]) -> list[dict]:
    seen: set[str] = set()
    ordered: list[dict] = []
    skill_lookup = {skill.name.lower(): skill for skill in skills}
    for matched_name in matched:
        skill = skill_lookup.get(matched_name.lower())
        if skill and skill.name.lower() not in seen:
            seen.add(skill.name.lower())
            ordered.append({"name": skill.name, "category": skill.category})
    for skill in skills:
        if skill.name.lower() not in seen:
            seen.add(skill.name.lower())
            ordered.append({"name": skill.name, "category": skill.category})
    return ordered


def _skill_groups(skills: list[dict]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for skill in skills:
        category = skill.get("category") or "Tools"
        groups.setdefault(category, [])
        if skill["name"] not in groups[category]:
            groups[category].append(skill["name"])
    preferred_order = ["Programming", "Databases", "Visualization", "AI/ML", "Cloud", "ETL Tools", "Frameworks", "Tools"]
    return {category: groups[category] for category in preferred_order if category in groups} | {
        category: values for category, values in groups.items() if category not in preferred_order
    }


def _project_bullets(description: str) -> list[str]:
    parts = [
        part.strip(" -*\t")
        for part in re.split(r"(?<=[.!?])\s+|;|\n", description)
        if len(part.strip(" -*\t")) > 18
    ]
    if not parts:
        return [description]
    return parts[:4]


def _evidence_summary(user: User, role: str, matched: list[str]) -> str:
    role_text = role if role and role != "Unknown" else (user.experiences[0].role if user.experiences else "Data professional")
    experience_bits = []
    if user.experiences:
        first = user.experiences[0]
        if first.company and first.company != "Not specified":
            experience_bits.append(f"{first.role} experience at {first.company}")
        else:
            experience_bits.append(f"{first.role} experience")
    if user.projects:
        project_names = ", ".join(project.name for project in user.projects[:2])
        experience_bits.append(f"project work including {project_names}")
    skills = matched[:6] or [skill.name for skill in user.skills[:6]]
    skill_text = ", ".join(skills)
    pieces = [f"{role_text} with " + " and ".join(experience_bits)] if experience_bits else [role_text]
    if skill_text:
        pieces.append(f"Skilled in {skill_text}")
    return ". ".join(pieces).strip() + "."


def _strengths_for_resume(user: User, matched: list[str]) -> list[str]:
    strengths: list[str] = []
    skill_names = matched[:5] or [skill.name for skill in user.skills[:5]]
    if skill_names:
        strengths.append("Hands-on skills: " + ", ".join(skill_names) + ".")
    if user.projects:
        project_domains = sorted({project.domain for project in user.projects if project.domain})
        if project_domains:
            strengths.append("Project exposure: " + ", ".join(project_domains[:4]) + ".")
        else:
            strengths.append("Project experience: " + ", ".join(project.name for project in user.projects[:3]) + ".")
    if user.experiences:
        tech = []
        for exp in user.experiences:
            tech.extend([item.strip() for item in exp.technologies.split(",") if item.strip()])
        if tech:
            strengths.append("Work experience tools: " + ", ".join(dict.fromkeys(tech).keys()) + ".")
    return strengths[:4]


@app.post("/resume/generate", response_model=GeneratedResumeResponse)
def generate_resume(request: GenerateResumeRequest, db: Session = Depends(get_db)) -> GeneratedResumeResponse:
    user = db.get(User, request.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User profile not found")
    jd_text = sanitize_text(request.jd_text)
    resume_data, meta = _profile_to_resume_data(user, jd_text, request.template_name, request.target_role)
    preview = build_preview(resume_data)
    docx_path = export_docx(resume_data, request.template_name)
    pdf_path = export_pdf(resume_data, request.template_name)
    jd_row = JDHistory(user_id=user.id, raw_text=jd_text, parsed_json=json.dumps(meta["jd"].model_dump()), role_type=meta["role"])
    db.add(jd_row)
    db.flush()
    db.add(Resume(user_id=user.id, jd_history_id=jd_row.id, target_role=meta["role"], template_name=request.template_name, ats_score=meta["score"], docx_path=docx_path, pdf_path=pdf_path))
    db.commit()
    base_suggestions = suggestions(meta["missing"], meta["score"])
    return GeneratedResumeResponse(
        ats_score=meta["score"],
        keyword_match_percent=meta["keyword_percent"],
        role_type=meta["role"],
        top_matching_skills=meta["matched"][:10],
        missing_keywords=meta["missing"][:12],
        selected_projects=meta["selected_projects"],
        selected_evidence=meta["selected_evidence"],
        suggestions=base_suggestions,
        preview_markdown=preview,
        docx_path=docx_path,
        pdf_path=pdf_path,
    )


@app.get("/exports/{filename}")
def download_export(filename: str) -> FileResponse:
    path = Path(get_settings().exports_dir) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Export not found")
    return FileResponse(path, filename=filename)
