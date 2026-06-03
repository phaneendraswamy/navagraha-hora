from collections.abc import Iterable
from typing import Any

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ai_engine.matcher import MatchingEngine, UserProfileData
from backend.db.models import Application, DecisionStatus, Job, RawJob, UserProfile
from backend.db.seed import ensure_default_profile
from backend.schemas import DecisionStatusSchema, RawJobCreate
from parsers.normalizer import JobNormalizer


class JobIngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.normalizer = JobNormalizer()
        self.matcher = MatchingEngine()

    def ingest_raw_jobs(self, raw_jobs: Iterable[RawJobCreate]) -> tuple[int, int]:
        collected = 0
        normalized = 0
        profile = ensure_default_profile(self.db)
        profile_data = self._profile_data(profile)

        for raw_job_create in raw_jobs:
            raw_job = RawJob(
                source=raw_job_create.source,
                source_job_id=raw_job_create.source_job_id,
                url=raw_job_create.url,
                payload=raw_job_create.payload,
            )
            self.db.add(raw_job)
            self.db.commit()
            self.db.refresh(raw_job)
            collected += 1

            standard = self.normalizer.normalize(raw_job.source, raw_job.payload)
            if not standard.title or not standard.company:
                continue

            match = self.matcher.score(standard, profile_data)
            insights = self.matcher.analyze_jd(standard)
            job = Job(
                raw_job_id=raw_job.id,
                job_id=standard.job_id,
                source=standard.source,
                title=standard.title,
                company=standard.company,
                location=standard.location,
                employment_type=standard.employment_type,
                salary=standard.salary,
                skills=standard.skills,
                experience_required=standard.experience_required,
                jd_text=standard.jd_text,
                url=standard.url,
                posted_date=standard.posted_date,
                collected_at=standard.collected_at,
                match_percentage=match.match_percentage,
                match_details=match.model_dump(),
                jd_insights=insights.model_dump(),
            )
            self.db.add(job)
            try:
                self.db.commit()
                normalized += 1
            except IntegrityError:
                self.db.rollback()
                existing = (
                    self.db.query(Job)
                    .filter(Job.source == standard.source, Job.job_id == standard.job_id)
                    .one_or_none()
                )
                if existing:
                    self._refresh_existing(existing, standard, match.model_dump(), insights.model_dump())
                    self.db.commit()

        return collected, normalized

    def list_jobs(
        self,
        limit: int = 25,
        offset: int = 0,
        status: DecisionStatus | None = None,
        min_match: float | None = None,
    ) -> tuple[list[Job], int]:
        query = self.db.query(Job)
        if status:
            query = query.filter(Job.decision_status == status)
        if min_match is not None:
            query = query.filter(Job.match_percentage >= min_match)
        total = query.with_entities(func.count(Job.id)).scalar() or 0
        items = (
            query.order_by(Job.match_percentage.desc(), Job.collected_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return items, total

    def update_decision(self, job_id: str, status: DecisionStatusSchema, notes: str = "") -> Job:
        job = self.db.query(Job).filter(Job.id == job_id).one()
        job.decision_status = DecisionStatus(status.value)

        if job.decision_status == DecisionStatus.APPROVED:
            application = self.db.query(Application).filter(Application.job_id == job.id).one_or_none()
            if application:
                application.status = "approved"
                application.notes = notes
            else:
                self.db.add(Application(job_id=job.id, status="approved", notes=notes))

        self.db.commit()
        self.db.refresh(job)
        return job

    def _profile_data(self, profile: UserProfile) -> UserProfileData:
        return UserProfileData(
            skills=profile.skills,
            preferred_roles=profile.preferred_roles,
            preferred_locations=profile.preferred_locations,
            experience_years=profile.experience_years,
            tooling=profile.tooling,
        )

    def _refresh_existing(
        self,
        existing: Job,
        standard: Any,
        match_details: dict[str, Any],
        jd_insights: dict[str, Any],
    ) -> None:
        existing.title = standard.title
        existing.company = standard.company
        existing.location = standard.location
        existing.employment_type = standard.employment_type
        existing.salary = standard.salary
        existing.skills = standard.skills
        existing.experience_required = standard.experience_required
        existing.jd_text = standard.jd_text
        existing.url = standard.url
        existing.posted_date = standard.posted_date
        existing.match_percentage = match_details["match_percentage"]
        existing.match_details = match_details
        existing.jd_insights = jd_insights
