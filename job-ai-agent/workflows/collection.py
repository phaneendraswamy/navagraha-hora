from sqlalchemy.orm import Session

from backend.services.jobs import JobIngestionService
from collectors.greenhouse import GreenhouseCollector
from collectors.linkedin import LinkedInCollector


async def collect_greenhouse(db: Session, boards: list[str]) -> tuple[int, int]:
    raw_jobs = await GreenhouseCollector().collect(boards=boards)
    return JobIngestionService(db).ingest_raw_jobs(raw_jobs)


async def collect_linkedin(db: Session, query: str, location: str, max_pages: int) -> tuple[int, int]:
    raw_jobs = await LinkedInCollector().collect(query=query, location=location, max_pages=max_pages)
    return JobIngestionService(db).ingest_raw_jobs(raw_jobs)

