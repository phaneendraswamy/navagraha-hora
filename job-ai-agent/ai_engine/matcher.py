import re
from dataclasses import dataclass

from backend.schemas import JDInsights, MatchOutput, StandardJob


CANONICAL_SKILLS = {
    "python": "Python",
    "sql": "SQL",
    "machine learning": "Machine Learning",
    "ml": "Machine Learning",
    "artificial intelligence": "AI",
    "ai": "AI",
    "streamlit": "Streamlit",
    "snowflake": "Snowflake",
    "power bi": "Power BI",
    "powerbi": "Power BI",
    "golang": "Go",
    "go": "Go",
    "data warehousing": "Data Warehousing",
    "nlp": "NLP",
    "natural language processing": "NLP",
    "dashboard": "Dashboarding",
    "dashboarding": "Dashboarding",
    "analytics engineering": "Analytics Engineering",
    "dbt": "dbt",
    "airflow": "Airflow",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "llm": "LLM",
    "prompt engineering": "Prompt Engineering",
    "tableau": "Tableau",
    "excel": "Excel",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
}

REMOTE_TERMS = {"remote", "work from home", "wfh", "anywhere"}
ROLE_TERMS = {
    "data analyst",
    "ai engineer",
    "junior ml engineer",
    "junior machine learning engineer",
    "prompt engineer",
    "analytics engineer",
    "machine learning engineer",
}


@dataclass(frozen=True)
class UserProfileData:
    skills: list[str]
    preferred_roles: list[str]
    preferred_locations: list[str]
    experience_years: float = 1.0
    tooling: list[str] | None = None


class MatchingEngine:
    skill_weight = 0.50
    experience_weight = 0.25
    location_weight = 0.15
    tooling_weight = 0.10

    def score(self, job: StandardJob, profile: UserProfileData) -> MatchOutput:
        job_skills = set(job.skills) or self.extract_skills(job.jd_text + " " + job.title)
        profile_skills = {self._normalize_name(skill) for skill in profile.skills}
        normalized_job_skills = {self._normalize_name(skill) for skill in job_skills}

        strong_matches = sorted(profile_skills.intersection(normalized_job_skills))
        missing_skills = sorted(normalized_job_skills.difference(profile_skills))

        skill_score = self._ratio(len(strong_matches), max(len(normalized_job_skills), 1))
        experience_score = self._experience_score(job.experience_required, profile.experience_years)
        location_score = self._location_score(job.location, profile.preferred_locations)
        tooling_score = self._tooling_score(job, profile.tooling or profile.skills)

        weighted_score = (
            skill_score * self.skill_weight
            + experience_score * self.experience_weight
            + location_score * self.location_weight
            + tooling_score * self.tooling_weight
        )
        match_percentage = int(round(weighted_score * 100))

        confidence = "high" if normalized_job_skills and job.jd_text else "medium"
        if not normalized_job_skills:
            confidence = "low"

        return MatchOutput(
            match_percentage=max(0, min(match_percentage, 100)),
            strong_matches=strong_matches,
            missing_skills=missing_skills[:12],
            fit_reasoning=self._reasoning(
                job=job,
                strong_matches=strong_matches,
                missing_skills=missing_skills,
                location_score=location_score,
                experience_score=experience_score,
            ),
            confidence=confidence,
            component_scores={
                "skill_overlap": round(skill_score * 100, 2),
                "experience_relevance": round(experience_score * 100, 2),
                "location_relevance": round(location_score * 100, 2),
                "tooling_overlap": round(tooling_score * 100, 2),
            },
        )

    def analyze_jd(self, job: StandardJob) -> JDInsights:
        text = job.jd_text or ""
        skills = sorted(self.extract_skills(text + " " + job.title))
        required = self._skills_near_keywords(text, {"required", "must", "experience with", "proficient"})
        optional = self._skills_near_keywords(text, {"nice to have", "preferred", "bonus", "good to have"})

        hidden_expectations = []
        lower = text.lower()
        if any(term in lower for term in ["startup", "fast-paced", "ambiguity", "ownership"]):
            hidden_expectations.append("Comfort with ambiguity, ownership, and fast-moving teams")
        if any(term in lower for term in ["stakeholder", "cross-functional", "business teams"]):
            hidden_expectations.append("Strong stakeholder communication and requirements discovery")
        if any(term in lower for term in ["production", "deploy", "monitoring", "pipeline"]):
            hidden_expectations.append("Practical delivery beyond notebooks or one-off analysis")

        interview_focus = sorted(set(required or skills[:6]))
        red_flags = self._red_flags(text)

        return JDInsights(
            required_skills=sorted(required or skills),
            optional_skills=sorted(optional.difference(required)),
            hidden_expectations=hidden_expectations,
            experience_requirements=job.experience_required or self.extract_experience(text),
            interview_focus_areas=interview_focus[:8],
            red_flags=red_flags,
            summary=self._summary(job, skills, hidden_expectations),
        )

    def extract_skills(self, text: str) -> set[str]:
        lower = f" {text.lower()} "
        found = set()
        for needle, label in CANONICAL_SKILLS.items():
            pattern = r"(?<![a-z0-9])" + re.escape(needle) + r"(?![a-z0-9])"
            if re.search(pattern, lower):
                found.add(label)
        return found

    def extract_experience(self, text: str) -> str:
        patterns = [
            r"(\d+\+?\s*(?:-\s*\d+\s*)?years?[^.,;\n]*)",
            r"(\d+\+?\s*yrs?[^.,;\n]*)",
            r"(freshers?[^.,;\n]*)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    def _skills_near_keywords(self, text: str, keywords: set[str]) -> set[str]:
        matches = set()
        sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
        for sentence in sentences:
            lower = sentence.lower()
            if any(keyword in lower for keyword in keywords):
                matches.update(self.extract_skills(sentence))
        return matches

    def _experience_score(self, experience_required: str, user_years: float) -> float:
        if not experience_required:
            return 0.70
        numbers = [float(item) for item in re.findall(r"\d+(?:\.\d+)?", experience_required)]
        if not numbers:
            lower = experience_required.lower()
            return 1.0 if "fresh" in lower or "entry" in lower or "junior" in lower else 0.70
        required_min = min(numbers)
        if user_years >= required_min:
            return 1.0
        if required_min <= 2 and user_years >= 1:
            return 0.85
        if required_min <= 3 and user_years >= 1:
            return 0.60
        return 0.35

    def _location_score(self, location: str, preferred_locations: list[str]) -> float:
        lower_location = location.lower()
        preferred = [item.lower() for item in preferred_locations]
        if any(term in lower_location for term in REMOTE_TERMS):
            return 1.0
        if any(item and item in lower_location for item in preferred):
            return 1.0
        if "india" in lower_location:
            return 0.70
        if not location:
            return 0.50
        return 0.20

    def _tooling_score(self, job: StandardJob, tooling: list[str]) -> float:
        text = f"{job.title} {job.jd_text} {' '.join(job.skills)}".lower()
        normalized_tooling = {self._normalize_name(item) for item in tooling}
        hits = [tool for tool in normalized_tooling if tool.lower() in text]
        return self._ratio(len(hits), max(len(normalized_tooling), 1))

    def _reasoning(
        self,
        job: StandardJob,
        strong_matches: list[str],
        missing_skills: list[str],
        location_score: float,
        experience_score: float,
    ) -> str:
        role_fit = any(term in job.title.lower() for term in ROLE_TERMS)
        pieces = []
        if role_fit:
            pieces.append("Role title aligns with preferred AI, ML, analytics, or data roles.")
        if strong_matches:
            pieces.append(f"Strong overlap on {', '.join(strong_matches[:6])}.")
        if missing_skills:
            pieces.append(f"Potential gaps include {', '.join(missing_skills[:5])}.")
        if location_score >= 1:
            pieces.append("Location matches Remote or Hyderabad preference.")
        if experience_score < 0.7:
            pieces.append("Experience requirement may be above the current target profile.")
        return " ".join(pieces) or "Limited structured data was available, so this score is conservative."

    def _red_flags(self, text: str) -> list[str]:
        lower = text.lower()
        flags = []
        if "unpaid" in lower:
            flags.append("Mentions unpaid work")
        if "night shift" in lower or "rotational shift" in lower:
            flags.append("Mentions night or rotational shifts")
        if "bond" in lower:
            flags.append("Mentions employment bond")
        if "commission only" in lower:
            flags.append("Mentions commission-only compensation")
        return flags

    def _summary(self, job: StandardJob, skills: list[str], hidden_expectations: list[str]) -> str:
        skill_text = ", ".join(skills[:6]) if skills else "general role requirements"
        expectation_text = f" Expect emphasis on {hidden_expectations[0].lower()}." if hidden_expectations else ""
        return f"{job.company} is hiring for {job.title}. Core signals include {skill_text}.{expectation_text}"

    @staticmethod
    def _normalize_name(value: str) -> str:
        value_lower = value.strip().lower()
        return CANONICAL_SKILLS.get(value_lower, value.strip())

    @staticmethod
    def _ratio(numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return max(0.0, min(numerator / denominator, 1.0))

