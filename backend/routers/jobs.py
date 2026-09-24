"""Scrape-job status — the frontend polls these for the 'Scraping…' pill."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import ScrapeJob
from schemas import ScrapeJobOut

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=ScrapeJobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(ScrapeJob).get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/creator/{creator_id}/latest", response_model=ScrapeJobOut)
def latest_job(creator_id: int, db: Session = Depends(get_db)):
    job = (
        db.query(ScrapeJob)
        .filter(ScrapeJob.creator_id == creator_id)
        .order_by(ScrapeJob.created_at.desc())
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="No jobs for this creator")
    return job
