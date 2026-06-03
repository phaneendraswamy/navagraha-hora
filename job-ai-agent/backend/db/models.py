from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from sqlalchemy import DateTime, Enum as SAEnum, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from backend.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DecisionStatus(str, Enum):
    NEW = "new"
    SAVED = "saved"
    SKIPPED = "skipped"
    APPROVED = "approved"


json_type = JSON().with_variant(JSONB, "postgresql")


class RawJob(Base):
    __tablename__ = "raw_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    source: Mapped[str] = mapped_column(String(80), index=True)
    source_job_id: Mapped[str | None] = mapped_column(String(255), index=True)
    url: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(MutableDict.as_mutable(json_type), default=dict)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    job: Mapped["Job | None"] = relationship(back_populates="raw_job")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    raw_job_id: Mapped[str | None] = mapped_column(ForeignKey("raw_jobs.id"), nullable=True)
    job_id: Mapped[str] = mapped_column(String(255), index=True)
    source: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    company: Mapped[str] = mapped_column(String(255), index=True)
    location: Mapped[str] = mapped_column(String(255), default="")
    employment_type: Mapped[str] = mapped_column(String(120), default="")
    salary: Mapped[str] = mapped_column(String(255), default="")
    skills: Mapped[list[str]] = mapped_column(MutableList.as_mutable(json_type), default=list)
    experience_required: Mapped[str] = mapped_column(String(255), default="")
    jd_text: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(Text, default="")
    posted_date: Mapped[str] = mapped_column(String(80), default="")
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    match_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    match_details: Mapped[dict] = mapped_column(MutableDict.as_mutable(json_type), default=dict)
    jd_insights: Mapped[dict] = mapped_column(MutableDict.as_mutable(json_type), default=dict)
    decision_status: Mapped[DecisionStatus] = mapped_column(
        SAEnum(DecisionStatus), default=DecisionStatus.NEW, index=True
    )

    raw_job: Mapped[RawJob | None] = relationship(back_populates="job")
    application: Mapped["Application | None"] = relationship(back_populates="job")

    __table_args__ = (
        Index("ix_jobs_source_job_id", "source", "job_id", unique=True),
    )


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), default="Target User")
    skills: Mapped[list[str]] = mapped_column(MutableList.as_mutable(json_type), default=list)
    preferred_roles: Mapped[list[str]] = mapped_column(MutableList.as_mutable(json_type), default=list)
    preferred_locations: Mapped[list[str]] = mapped_column(MutableList.as_mutable(json_type), default=list)
    experience_years: Mapped[float] = mapped_column(Float, default=1.0)
    tooling: Mapped[list[str]] = mapped_column(MutableList.as_mutable(json_type), default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    status: Mapped[str] = mapped_column(String(80), default="approved")
    notes: Mapped[str] = mapped_column(Text, default="")
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    job: Mapped[Job] = relationship(back_populates="application")

