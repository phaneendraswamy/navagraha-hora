from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.db.models import DecisionStatus, Job
from backend.db.session import get_db
from backend.schemas import (
    CollectGreenhouseRequest,
    CollectLinkedInRequest,
    CollectResponse,
    DecisionStatusSchema,
    DecisionUpdate,
    JobListResponse,
    JobRead,
)
from backend.services.jobs import JobIngestionService
from workflows.collection import collect_greenhouse, collect_linkedin

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/collect/greenhouse", response_model=CollectResponse)
async def collect_greenhouse_jobs(payload: CollectGreenhouseRequest, db: Session = Depends(get_db)) -> CollectResponse:
    if not payload.boards:
        raise HTTPException(status_code=400, detail="Provide at least one Greenhouse board token.")
    collected, normalized = await collect_greenhouse(db=db, boards=payload.boards)
    return CollectResponse(collected=collected, normalized=normalized, source="greenhouse")


@router.post("/collect/linkedin", response_model=CollectResponse)
async def collect_linkedin_jobs(payload: CollectLinkedInRequest, db: Session = Depends(get_db)) -> CollectResponse:
    collected, normalized = await collect_linkedin(
        db=db,
        query=payload.query,
        location=payload.location,
        max_pages=payload.max_pages,
    )
    return CollectResponse(collected=collected, normalized=normalized, source="linkedin")


@router.get("/jobs", response_model=JobListResponse)
def list_jobs(
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: DecisionStatusSchema | None = None,
    min_match: float | None = Query(default=None, ge=0, le=100),
    db: Session = Depends(get_db),
) -> JobListResponse:
    db_status = DecisionStatus(status.value) if status else None
    items, total = JobIngestionService(db).list_jobs(
        limit=limit,
        offset=offset,
        status=db_status,
        min_match=min_match,
    )
    return JobListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/jobs/{job_id}", response_model=JobRead)
def get_job(job_id: str, db: Session = Depends(get_db)) -> Job:
    job = db.query(Job).filter(Job.id == job_id).one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.patch("/jobs/{job_id}/decision", response_model=JobRead)
def update_decision(job_id: str, payload: DecisionUpdate, db: Session = Depends(get_db)) -> Job:
    job = db.query(Job).filter(Job.id == job_id).one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobIngestionService(db).update_decision(job_id, payload.decision_status, payload.notes)

