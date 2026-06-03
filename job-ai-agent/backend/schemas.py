from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DecisionStatusSchema(str, Enum):
    NEW = "new"
    SAVED = "saved"
    SKIPPED = "skipped"
    APPROVED = "approved"


class StandardJob(BaseModel):
    job_id: str = ""
    source: str = ""
    title: str = ""
    company: str = ""
    location: str = ""
    employment_type: str = ""
    salary: str = ""
    skills: list[str] = Field(default_factory=list)
    experience_required: str = ""
    jd_text: str = ""
    url: str = ""
    posted_date: str = ""
    collected_at: datetime | None = None


class RawJobCreate(BaseModel):
    source: str
    source_job_id: str | None = None
    url: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class MatchOutput(BaseModel):
    match_percentage: int
    strong_matches: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    fit_reasoning: str = ""
    confidence: str = "medium"
    component_scores: dict[str, float] = Field(default_factory=dict)


class JDInsights(BaseModel):
    required_skills: list[str] = Field(default_factory=list)
    optional_skills: list[str] = Field(default_factory=list)
    hidden_expectations: list[str] = Field(default_factory=list)
    experience_requirements: str = ""
    interview_focus_areas: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    summary: str = ""


class JobRead(StandardJob):
    id: str
    match_percentage: float
    match_details: dict[str, Any] = Field(default_factory=dict)
    jd_insights: dict[str, Any] = Field(default_factory=dict)
    decision_status: DecisionStatusSchema

    model_config = ConfigDict(from_attributes=True)


class JobListResponse(BaseModel):
    items: list[JobRead]
    total: int
    limit: int
    offset: int


class DecisionUpdate(BaseModel):
    decision_status: DecisionStatusSchema
    notes: str = ""


class CollectLinkedInRequest(BaseModel):
    query: str = "Data Analyst OR AI Engineer OR Prompt Engineer"
    location: str = "Remote OR Hyderabad"
    max_pages: int = 1


class CollectGreenhouseRequest(BaseModel):
    boards: list[str] = Field(default_factory=list, description="Greenhouse board tokens, e.g. stripe")


class CollectResponse(BaseModel):
    collected: int
    normalized: int
    source: str

