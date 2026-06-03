import os
from typing import Any

import requests
import streamlit as st


API_URL = os.getenv("API_URL", "http://localhost:8000/api").rstrip("/")


st.set_page_config(page_title="AI Job Hunter", page_icon="briefcase", layout="wide")


def api_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.get(f"{API_URL}{path}", params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(f"{API_URL}{path}", json=payload, timeout=120)
    response.raise_for_status()
    return response.json()


def api_patch(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.patch(f"{API_URL}{path}", json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def decision_button(job_id: str, status: str, label: str) -> None:
    if st.button(label, key=f"{status}-{job_id}", use_container_width=True):
        api_patch(f"/jobs/{job_id}/decision", {"decision_status": status})
        st.toast(f"Marked as {status}")
        st.rerun()


st.title("AI Job Hunter")

with st.sidebar:
    st.header("Collectors")
    st.caption("Run small, polite collection batches. Raw jobs are stored before normalization.")

    with st.form("greenhouse_form"):
        boards_text = st.text_area("Greenhouse boards", value="openai, stripe", help="Comma-separated board tokens.")
        greenhouse_submit = st.form_submit_button("Collect Greenhouse", use_container_width=True)
        if greenhouse_submit:
            boards = [item.strip() for item in boards_text.split(",") if item.strip()]
            with st.spinner("Collecting Greenhouse jobs..."):
                result = api_post("/collect/greenhouse", {"boards": boards})
            st.success(f"Collected {result['collected']} raw jobs, normalized {result['normalized']}.")

    with st.form("linkedin_form"):
        query = st.text_input("LinkedIn query", value="Data Analyst OR AI Engineer OR Prompt Engineer")
        location = st.text_input("LinkedIn location", value="Remote OR Hyderabad")
        max_pages = st.number_input("Max pages", min_value=1, max_value=2, value=1)
        linkedin_submit = st.form_submit_button("Collect LinkedIn", use_container_width=True)
        if linkedin_submit:
            with st.spinner("Collecting LinkedIn jobs..."):
                result = api_post(
                    "/collect/linkedin",
                    {"query": query, "location": location, "max_pages": int(max_pages)},
                )
            st.success(f"Collected {result['collected']} raw jobs, normalized {result['normalized']}.")

    st.header("Filters")
    status_filter = st.selectbox("Decision", ["all", "new", "saved", "approved", "skipped"])
    min_match = st.slider("Minimum match", min_value=0, max_value=100, value=0)


params: dict[str, Any] = {"limit": 50, "offset": 0, "min_match": min_match}
if status_filter != "all":
    params["status"] = status_filter

try:
    jobs_response = api_get("/jobs", params=params)
except requests.RequestException as exc:
    st.error(f"Backend is not reachable at {API_URL}. Start FastAPI first. Details: {exc}")
    st.stop()

jobs = jobs_response["items"]
top = st.columns([1, 1, 1, 1])
top[0].metric("Visible jobs", len(jobs))
top[1].metric("Total matching filter", jobs_response["total"])
top[2].metric("Min match", f"{min_match}%")
top[3].metric("API", API_URL.replace("http://", ""))

if not jobs:
    st.info("No jobs yet. Run Greenhouse collection from the sidebar to seed the dashboard.")
    st.stop()

for job in jobs:
    match = int(job["match_percentage"])
    insights = job.get("jd_insights") or {}
    match_details = job.get("match_details") or {}
    component_scores = match_details.get("component_scores", {})

    with st.container(border=True):
        header_cols = st.columns([5, 2, 2])
        with header_cols[0]:
            st.subheader(f"{job['title']} · {job['company']}")
            st.caption(f"{job['source']} · {job.get('location') or 'Location not listed'} · {job['decision_status']}")
        with header_cols[1]:
            st.metric("Match", f"{match}%")
        with header_cols[2]:
            if job.get("url"):
                st.link_button("Open job", job["url"], use_container_width=True)

        st.progress(match / 100)
        st.write(insights.get("summary") or match_details.get("fit_reasoning") or "No summary available.")

        score_cols = st.columns(4)
        score_cols[0].metric("Skills", f"{component_scores.get('skill_overlap', 0):.0f}%")
        score_cols[1].metric("Experience", f"{component_scores.get('experience_relevance', 0):.0f}%")
        score_cols[2].metric("Location", f"{component_scores.get('location_relevance', 0):.0f}%")
        score_cols[3].metric("Tooling", f"{component_scores.get('tooling_overlap', 0):.0f}%")

        with st.expander("JD intelligence"):
            col_a, col_b = st.columns(2)
            col_a.write("Required skills")
            col_a.write(", ".join(insights.get("required_skills") or job.get("skills") or []) or "Not detected")
            col_b.write("Potential gaps")
            col_b.write(", ".join(match_details.get("missing_skills") or []) or "None detected")

            st.write("Hidden expectations")
            st.write(", ".join(insights.get("hidden_expectations") or []) or "None detected")
            st.write("Interview focus areas")
            st.write(", ".join(insights.get("interview_focus_areas") or []) or "Not enough signal")
            red_flags = insights.get("red_flags") or []
            if red_flags:
                st.warning(", ".join(red_flags))

        with st.expander("View full JD"):
            st.write(job.get("jd_text") or "Full JD was not available from this source.")

        action_cols = st.columns(4)
        with action_cols[0]:
            decision_button(job["id"], "approved", "Apply")
        with action_cols[1]:
            decision_button(job["id"], "saved", "Save")
        with action_cols[2]:
            decision_button(job["id"], "skipped", "Skip")
        with action_cols[3]:
            decision_button(job["id"], "new", "Reset")

