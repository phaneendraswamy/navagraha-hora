from pydantic import BaseModel, EmailStr, Field, HttpUrl


class PersonalDetails(BaseModel):
    full_name: str
    email: EmailStr
    phone: str | None = None
    linkedin_url: HttpUrl | None = None
    github_url: HttpUrl | None = None
    portfolio_url: HttpUrl | None = None
    location: str | None = None


class SkillIn(BaseModel):
    category: str
    name: str
    proficiency: str | None = None


class ProjectIn(BaseModel):
    name: str
    domain: str | None = None
    description: str
    technologies: list[str] = []
    business_impact: str | None = None
    keywords: list[str] = []
    role_tags: list[str] = []


class ExperienceIn(BaseModel):
    company: str
    role: str
    duration: str
    responsibilities: list[str] = []
    achievements: list[str] = []
    technologies: list[str] = []


class CertificationIn(BaseModel):
    name: str
    organization: str | None = None
    skills_covered: list[str] = []


class EducationIn(BaseModel):
    degree: str
    institution: str
    duration: str | None = None
    gpa: str | None = None


class MasterProfileIn(BaseModel):
    personal: PersonalDetails
    education: list[EducationIn] = []
    skills: list[SkillIn] = []
    experiences: list[ExperienceIn] = []
    projects: list[ProjectIn] = []
    certifications: list[CertificationIn] = []


class JDAnalysis(BaseModel):
    required_skills: list[str] = []
    responsibilities: list[str] = []
    tools: list[str] = []
    technologies: list[str] = []
    experience_level: str = "Not specified"
    role_type: str = "Unknown"
    keywords: list[str] = []


class GenerateResumeRequest(BaseModel):
    user_id: int = 1
    jd_text: str = Field(min_length=30)
    target_role: str | None = None
    template_name: str = "ATS Minimal"


class GeneratedResumeResponse(BaseModel):
    ats_score: float
    keyword_match_percent: float
    role_type: str
    top_matching_skills: list[str]
    missing_keywords: list[str]
    selected_projects: list[str]
    selected_evidence: list[dict] = []
    suggestions: list[str]
    preview_markdown: str
    docx_path: str
    pdf_path: str


class ProfileIngestResponse(BaseModel):
    user_id: int
    profile: MasterProfileIn
    extracted_counts: dict[str, int]
    message: str
