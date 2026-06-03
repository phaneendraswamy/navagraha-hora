from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


JSONType = JSONB().with_variant(Text, "sqlite")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(60))
    linkedin_url: Mapped[str | None] = mapped_column(String(255))
    github_url: Mapped[str | None] = mapped_column(String(255))
    portfolio_url: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    skills: Mapped[list["Skill"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    projects: Mapped[list["Project"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    experiences: Mapped[list["Experience"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    certifications: Mapped[list["Certification"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    education: Mapped[list["Education"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    category: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    proficiency: Mapped[str | None] = mapped_column(String(80))
    user: Mapped[User] = relationship(back_populates="skills")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(180))
    domain: Mapped[str | None] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    technologies: Mapped[str] = mapped_column(Text, default="")
    business_impact: Mapped[str | None] = mapped_column(Text)
    keywords: Mapped[str] = mapped_column(Text, default="")
    role_tags: Mapped[str] = mapped_column(Text, default="")
    user: Mapped[User] = relationship(back_populates="projects")


class Experience(Base):
    __tablename__ = "experiences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    company: Mapped[str] = mapped_column(String(180))
    role: Mapped[str] = mapped_column(String(180))
    duration: Mapped[str] = mapped_column(String(120))
    responsibilities: Mapped[str] = mapped_column(Text)
    achievements: Mapped[str] = mapped_column(Text, default="")
    technologies: Mapped[str] = mapped_column(Text, default="")
    user: Mapped[User] = relationship(back_populates="experiences")


class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(180))
    organization: Mapped[str | None] = mapped_column(String(180))
    skills_covered: Mapped[str] = mapped_column(Text, default="")
    user: Mapped[User] = relationship(back_populates="certifications")


class Education(Base):
    __tablename__ = "education"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    degree: Mapped[str] = mapped_column(String(180))
    institution: Mapped[str] = mapped_column(String(180))
    duration: Mapped[str | None] = mapped_column(String(120))
    gpa: Mapped[str | None] = mapped_column(String(40))
    user: Mapped[User] = relationship(back_populates="education")


class JDHistory(Base):
    __tablename__ = "jd_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text)
    parsed_json: Mapped[str] = mapped_column(Text, default="{}")
    role_type: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    jd_history_id: Mapped[int | None] = mapped_column(ForeignKey("jd_history.id"), nullable=True)
    target_role: Mapped[str] = mapped_column(String(80))
    template_name: Mapped[str] = mapped_column(String(80))
    ats_score: Mapped[float] = mapped_column(Float, default=0)
    docx_path: Mapped[str | None] = mapped_column(String(255))
    pdf_path: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
