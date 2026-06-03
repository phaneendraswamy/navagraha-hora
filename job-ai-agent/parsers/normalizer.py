from datetime import datetime, timezone
from typing import Any

from ai_engine.matcher import MatchingEngine
from backend.schemas import StandardJob


class JobNormalizer:
    def __init__(self) -> None:
        self.matcher = MatchingEngine()

    def normalize(self, source: str, payload: dict[str, Any]) -> StandardJob:
        if source == "greenhouse":
            return self._normalize_greenhouse(payload)
        if source == "linkedin":
            return self._normalize_linkedin(payload)
        return self._normalize_generic(source, payload)

    def _normalize_greenhouse(self, payload: dict[str, Any]) -> StandardJob:
        offices = payload.get("offices") or []
        location = ", ".join(
            office.get("name", "") for office in offices if isinstance(office, dict) and office.get("name")
        )
        departments = payload.get("departments") or []
        department_text = ", ".join(
            dept.get("name", "") for dept in departments if isinstance(dept, dict) and dept.get("name")
        )
        jd_text = self._clean_text(payload.get("content") or payload.get("absolute_url") or "")
        title = payload.get("title") or ""

        return StandardJob(
            job_id=str(payload.get("id") or payload.get("internal_job_id") or payload.get("absolute_url") or title),
            source="greenhouse",
            title=title,
            company=payload.get("company") or payload.get("board_token") or "",
            location=location,
            employment_type=department_text,
            salary=self._extract_salary(jd_text),
            skills=sorted(self.matcher.extract_skills(f"{title} {jd_text}")),
            experience_required=self.matcher.extract_experience(jd_text),
            jd_text=jd_text,
            url=payload.get("absolute_url") or "",
            posted_date=str(payload.get("updated_at") or ""),
            collected_at=datetime.now(timezone.utc),
        )

    def _normalize_linkedin(self, payload: dict[str, Any]) -> StandardJob:
        title = payload.get("title") or ""
        jd_text = self._clean_text(payload.get("description") or payload.get("summary") or "")
        return StandardJob(
            job_id=str(payload.get("job_id") or payload.get("url") or f"{payload.get('company', '')}:{title}"),
            source="linkedin",
            title=title,
            company=payload.get("company") or "",
            location=payload.get("location") or "",
            employment_type=payload.get("employment_type") or "",
            salary=self._extract_salary(jd_text),
            skills=sorted(self.matcher.extract_skills(f"{title} {jd_text}")),
            experience_required=payload.get("experience_required") or self.matcher.extract_experience(jd_text),
            jd_text=jd_text,
            url=payload.get("url") or "",
            posted_date=payload.get("posted_date") or "",
            collected_at=datetime.now(timezone.utc),
        )

    def _normalize_generic(self, source: str, payload: dict[str, Any]) -> StandardJob:
        title = payload.get("title") or payload.get("job_title") or ""
        jd_text = self._clean_text(payload.get("jd_text") or payload.get("description") or "")
        return StandardJob(
            job_id=str(payload.get("job_id") or payload.get("id") or payload.get("url") or title),
            source=source,
            title=title,
            company=payload.get("company") or "",
            location=payload.get("location") or "",
            employment_type=payload.get("employment_type") or "",
            salary=payload.get("salary") or self._extract_salary(jd_text),
            skills=payload.get("skills") or sorted(self.matcher.extract_skills(f"{title} {jd_text}")),
            experience_required=payload.get("experience_required") or self.matcher.extract_experience(jd_text),
            jd_text=jd_text,
            url=payload.get("url") or "",
            posted_date=str(payload.get("posted_date") or ""),
            collected_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _clean_text(text: str) -> str:
        return " ".join(str(text or "").replace("\xa0", " ").split())

    @staticmethod
    def _extract_salary(text: str) -> str:
        lowered = text.lower()
        markers = ["salary", "compensation", "ctc"]
        for marker in markers:
            index = lowered.find(marker)
            if index >= 0:
                return text[index : index + 180].split(".")[0].strip()
        return ""

