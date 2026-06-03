import os
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
ROLES = ["Auto classify", "Data Analyst", "Data Engineer", "AI Engineer", "ML Engineer", "NLP Engineer", "BI Developer"]
TEMPLATES = ["ATS Minimal", "Modern Professional", "AI/Tech Style"]

st.set_page_config(page_title="AI Resume Builder", layout="wide", initial_sidebar_state="collapsed")
st.markdown(
    """
    <style>
    .stApp { background: #f7f9fc; color: #0f172a; }
    header[data-testid="stHeader"] { background: #f7f9fc; height: 2.5rem; }
    div.block-container { padding: 1.4rem 2rem 2rem; max-width: 1800px; }
    label, p, span, .stMarkdown { color: #0f172a !important; }
    textarea, input, div[data-baseweb="select"] > div {
        background: #ffffff !important;
        color: #0f172a !important;
        border-color: #bfcee3 !important;
        border-radius: 8px !important;
    }
    .shell {
        border: 2px solid #2563eb;
        border-radius: 18px;
        padding: 20px;
        background: #ffffff;
    }
    .title-pill {
        width: fit-content;
        margin: 0 auto 18px;
        border: 2px solid #2563eb;
        border-radius: 10px;
        padding: 8px 24px;
        color: #1d4ed8;
        font-size: 1.35rem;
        font-weight: 800;
        letter-spacing: 0;
    }
    .panel {
        border: 1.5px solid #2f6fd2;
        border-radius: 14px;
        background: #ffffff;
        padding: 16px;
        min-height: 120px;
    }
    .panel-title {
        color: #1d4ed8;
        text-align: center;
        font-size: 0.92rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0;
        margin-bottom: 8px;
    }
    .resume-list {
        border: 1px solid #bfcee3;
        border-radius: 12px;
        padding: 10px;
        min-height: 248px;
        background: #fbfdff;
    }
    .resume-item {
        border: 1px solid #2f6fd2;
        border-radius: 8px;
        padding: 8px 10px;
        margin-bottom: 9px;
        font-weight: 700;
        color: #1d4ed8;
        background: #ffffff;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .metric-box {
        border: 1px solid #d4dfed;
        border-radius: 8px;
        padding: 12px;
        background: #f8fbff;
        margin-bottom: 12px;
    }
    .metric-label { color: #475569; font-size: 0.82rem; font-weight: 700; }
    .metric-value { color: #0f172a; font-size: 1.55rem; font-weight: 850; }
    .chip {
        display: inline-block;
        border: 1px solid #b7c9e5;
        background: #eef6ff;
        color: #164e63;
        border-radius: 999px;
        padding: 5px 9px;
        margin: 3px 3px 3px 0;
        font-size: 0.78rem;
        font-weight: 700;
    }
    .danger-chip { background: #fff7ed; color: #9a3412; border-color: #fed7aa; }
    .resume-preview {
        border: 1px solid #d4dfed;
        border-radius: 10px;
        padding: 20px 26px;
        background: #ffffff;
        height: 520px;
        overflow: auto;
    }
    .small-note { color: #64748b; font-size: 0.82rem; }
    div.stButton > button, div.stDownloadButton > button {
        border-radius: 8px;
        background: #2563eb;
        border: 1px solid #1d4ed8;
        color: white;
        font-weight: 800;
    }
    div.stButton > button:hover, div.stDownloadButton > button:hover {
        background: #1e40af;
        color: white;
        border-color: #1e40af;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def api_get(path: str) -> dict:
    response = requests.get(f"{BACKEND_URL}{path}", timeout=60)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict) -> dict:
    response = requests.post(f"{BACKEND_URL}{path}", json=payload, timeout=240)
    response.raise_for_status()
    return response.json()


def api_upload(path: str, file) -> dict:
    response = requests.post(f"{BACKEND_URL}{path}", files={"file": (file.name, file.getvalue())}, timeout=240)
    response.raise_for_status()
    return response.json()


def api_upload_many(path: str, files, profile_text: str = "") -> dict:
    upload_parts = [("files", (file.name, file.getvalue())) for file in files]
    response = requests.post(f"{BACKEND_URL}{path}", files=upload_parts, data={"profile_text": profile_text}, timeout=240)
    response.raise_for_status()
    return response.json()


def api_upload_many_profile(files, pasted_text: str) -> dict:
    last_result: dict | None = None
    source_summary: list[str] = []
    if files:
        result = api_upload_many("/profile/upload-many", files, pasted_text)
        last_result = result
        profile = result.get("profile", {})
        extra = " + pasted notes" if pasted_text.strip() else ""
        source_summary.append(f"{len(files)} uploaded file(s){extra}: {len(profile.get('projects', []))} projects, {len(profile.get('skills', []))} skills")
    elif pasted_text.strip():
        result = api_post("/profile/ingest", {"profile_text": pasted_text})
        last_result = result
        profile = result.get("profile", {})
        source_summary.append(f"pasted text: {len(profile.get('projects', []))} projects, {len(profile.get('skills', []))} skills")
    if not last_result:
        raise ValueError("Upload at least one resume/profile file or paste candidate text.")
    last_result["source_summary"] = source_summary
    return last_result


def chips(items: list[str], danger: bool = False) -> None:
    if not items:
        st.caption("None")
        return
    class_name = "chip danger-chip" if danger else "chip"
    st.markdown("".join(f'<span class="{class_name}">{item}</span>' for item in items), unsafe_allow_html=True)


def metric_box(label: str, value: str) -> None:
    st.markdown(
        f'<div class="metric-box"><div class="metric-label">{label}</div><div class="metric-value">{value}</div></div>',
        unsafe_allow_html=True,
    )


def skill_category_counts(profile: dict | None) -> pd.DataFrame:
    counts: dict[str, int] = {}
    for skill in (profile or {}).get("skills", []):
        category = skill.get("category") or "Tools"
        counts[category] = counts.get(category, 0) + 1
    if not counts:
        return pd.DataFrame({"category": [], "count": []})
    return pd.DataFrame([{"category": key, "count": value} for key, value in counts.items()])


def match_matrix(result: dict | None) -> pd.DataFrame:
    if not result:
        return pd.DataFrame({"bucket": [], "count": []})
    return pd.DataFrame([
        {"bucket": "Matched", "count": len(result.get("top_matching_skills", []))},
        {"bucket": "Missing", "count": len(result.get("missing_keywords", []))},
        {"bucket": "Projects", "count": len(result.get("selected_projects", []))},
    ])


def load_profile(user_id: int) -> dict | None:
    try:
        return api_get(f"/profile/{user_id}")
    except Exception:
        return None


st.markdown('<div class="shell">', unsafe_allow_html=True)
st.markdown('<div class="title-pill">AI RESUME BUILDER</div>', unsafe_allow_html=True)

try:
    health = api_get("/health")
    status = "Connected"
    openai_status = "OpenAI on" if health.get("openai_configured") else "OpenAI off"
except Exception:
    status = "Backend offline"
    openai_status = "Start API first"

top_status_left, top_status_right = st.columns([0.75, 0.25])
with top_status_left:
    st.caption(f"{status} | {openai_status}")
with top_status_right:
    user_id = st.number_input("Profile ID", min_value=1, value=int(st.session_state.get("user_id", 1)), step=1, label_visibility="collapsed")

left, center, right = st.columns([0.32, 0.43, 0.25], gap="large")

with left:
    st.markdown('<div class="panel"><div class="panel-title">Upload User Sample Resumes</div>', unsafe_allow_html=True)
    profile_files = st.file_uploader(
        "Upload user sample resumes",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    inner_left, inner_right = st.columns([0.48, 0.52], gap="medium")
    with inner_left:
        st.markdown('<div class="resume-list">', unsafe_allow_html=True)
        if profile_files:
            for index, file in enumerate(profile_files, start=1):
                st.markdown(f'<div class="resume-item">RESUME_{index}<br><span class="small-note">{file.name}</span></div>', unsafe_allow_html=True)
        else:
            for index in range(1, 5):
                st.markdown(f'<div class="resume-item">RESUME_{index}</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with inner_right:
        target_role = st.selectbox("Target role", ROLES)
        template = st.selectbox("Resume template", TEMPLATES, index=2)
        profile_text = st.text_area(
            "Paste everything you know about the candidate",
            height=142,
            placeholder="Bio, skills, projects, education, achievements...",
        )

    save_profile = st.button("Analyze Candidate Profile", type="primary", use_container_width=True)
    if save_profile:
        with st.spinner("Capturing candidate data..."):
            try:
                result = api_upload_many_profile(profile_files or [], profile_text)
                st.session_state["user_id"] = result["user_id"]
                st.session_state["profile"] = result["profile"]
                st.success(f"Profile #{result['user_id']} saved")
            except Exception as exc:
                st.error(f"Could not capture profile: {exc}")

    profile = st.session_state.get("profile") or load_profile(int(user_id))
    if profile:
        st.session_state["profile"] = profile
        st.markdown("**Captured Skills**")
        chips([skill["name"] for skill in profile.get("skills", [])[:18]])
        st.markdown("**Captured Projects**")
        for project in profile.get("projects", [])[:4]:
            st.caption(f"{project.get('name')} | {project.get('domain') or 'General'}")

with center:
    st.markdown('<div class="panel"><div class="panel-title">Upload Job Description</div>', unsafe_allow_html=True)
    jd_file = st.file_uploader("Upload job description", type=["pdf", "docx", "txt"], label_visibility="collapsed")
    jd_text = st.text_area(
        "Job description",
        value=st.session_state.get("jd_text", ""),
        height=210,
        label_visibility="collapsed",
        placeholder="Paste or upload the JD here...",
    )
    col_a, col_b = st.columns([0.5, 0.5])
    with col_a:
        analyze_jd = st.button("Analyze JD", use_container_width=True)
    with col_b:
        generate = st.button("Generate Resume", type="primary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if jd_file and not jd_text.strip():
        with st.spinner("Extracting JD..."):
            try:
                uploaded = api_upload("/jd/upload", jd_file)
                jd_text = uploaded["text"]
                st.session_state["jd_text"] = jd_text
                st.session_state["jd_analysis"] = uploaded["analysis"]
                st.success("JD uploaded and analyzed")
            except Exception as exc:
                st.error(f"Could not read JD: {exc}")

    if analyze_jd:
        if len(jd_text.strip()) < 30:
            st.warning("Paste or upload a complete JD.")
        else:
            with st.spinner("Analyzing JD..."):
                try:
                    st.session_state["jd_text"] = jd_text
                    st.session_state["jd_analysis"] = api_post("/jd/analyze", {"jd_text": jd_text})
                    st.success("JD analyzed")
                except Exception as exc:
                    st.error(f"JD analysis failed: {exc}")

    if generate:
        final_jd = jd_text or st.session_state.get("jd_text", "")
        if len(final_jd.strip()) < 30:
            st.warning("Upload or paste a JD first.")
        elif not st.session_state.get("profile") and not load_profile(int(user_id)):
            st.warning("Analyze candidate profile first.")
        else:
            with st.spinner("Building resume from captured evidence..."):
                try:
                    st.session_state["jd_text"] = final_jd
                    result = api_post(
                        "/resume/generate",
                        {
                            "user_id": int(st.session_state.get("user_id", user_id)),
                            "jd_text": final_jd,
                            "target_role": None if target_role == "Auto classify" else target_role,
                            "template_name": template,
                        },
                    )
                    st.session_state["last_result"] = result
                    st.success("Resume generated")
                except Exception as exc:
                    st.error(f"Resume generation failed: {exc}")

    st.markdown('<div class="panel" style="margin-top:18px;"><div class="panel-title">Automated Resume</div>', unsafe_allow_html=True)
    result = st.session_state.get("last_result")
    if result:
        st.markdown('<div class="resume-preview">', unsafe_allow_html=True)
        st.markdown(result["preview_markdown"])
        st.markdown("</div>", unsafe_allow_html=True)
        dl1, dl2 = st.columns(2)
        docx_path = Path(result["docx_path"])
        pdf_path = Path(result["pdf_path"])
        if docx_path.exists():
            dl1.download_button("Download DOCX", docx_path.read_bytes(), file_name=docx_path.name, mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
        if pdf_path.exists():
            dl2.download_button("Download PDF", pdf_path.read_bytes(), file_name=pdf_path.name, mime="application/pdf", use_container_width=True)
    else:
        st.info("Generated resume appears here after profile + JD are processed.")
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="panel" style="min-height:690px;"><div class="panel-title">Resume Intelligence</div>', unsafe_allow_html=True)
    result = st.session_state.get("last_result")
    analysis = st.session_state.get("jd_analysis")
    profile = st.session_state.get("profile") or load_profile(int(user_id))
    profile_skill_count = len((profile or {}).get("skills", []))
    profile_project_count = len((profile or {}).get("projects", []))
    profile_exp_count = len((profile or {}).get("experiences", []))
    if result:
        metric_box("Job Match Score", f"{result['ats_score']}%")
        metric_box("Keyword Match", f"{result['keyword_match_percent']}%")
        metric_box("Detected Role", result["role_type"])
        st.progress(min(float(result["ats_score"]) / 100, 1.0))
        matrix = match_matrix(result)
        if not matrix.empty:
            st.bar_chart(matrix, x="bucket", y="count", height=180)
        st.markdown("**Matched skills**")
        chips(result.get("top_matching_skills", []))
        st.markdown("**Missing keywords**")
        chips(result.get("missing_keywords", []), danger=True)
        category_df = skill_category_counts(profile)
        if not category_df.empty:
            st.markdown("**Candidate skill categories**")
            st.bar_chart(category_df, x="category", y="count", height=190)
        st.markdown("**Selected evidence**")
        for item in result.get("selected_evidence", [])[:5]:
            st.caption(f"{item.get('type')}: {item.get('name')} ({item.get('relevance_score')})")
    elif analysis:
        metric_box("Detected Role", analysis.get("role_type", "Unknown"))
        metric_box("Experience", analysis.get("experience_level", "Not specified"))
        metric_box("Profile Skills", str(profile_skill_count))
        metric_box("Profile Projects", str(profile_project_count))
        st.markdown("**JD skills**")
        chips(sorted(set(analysis.get("required_skills", []) + analysis.get("tools", []))))
        category_df = skill_category_counts(profile)
        if not category_df.empty:
            st.markdown("**Captured skill categories**")
            st.bar_chart(category_df, x="category", y="count", height=190)
    else:
        metric_box("Profile Skills", str(profile_skill_count))
        metric_box("Profile Projects", str(profile_project_count))
        metric_box("Experience Items", str(profile_exp_count))
        category_df = skill_category_counts(profile)
        if not category_df.empty:
            st.markdown("**Captured skill categories**")
            st.bar_chart(category_df, x="category", y="count", height=190)
        else:
            st.caption("Upload the resume and analyze the JD to populate resume intelligence.")
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
