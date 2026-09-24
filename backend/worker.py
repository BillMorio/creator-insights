"""Background worker: drains the scrape_job queue.

pending job -> mark running -> Apify grid scrape -> ingest posts -> done.
Runs as its own Render service (Dockerfile.worker). Polls every POLL_SECONDS.
"""
import logging
import os
import time
from datetime import datetime, timezone

from database import SessionLocal
from models import Creator, ScrapeJob
from services.ingest import ingest_result
from services.scraper import scrape_creator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [WORKER] %(levelname)s %(message)s")
log = logging.getLogger("worker")

POLL_SECONDS = int(os.getenv("POLL_SECONDS", "5"))


def _utcnow():
    return datetime.now(timezone.utc)


def process_one() -> bool:
    """Claim + process a single pending job. Returns True if one was handled."""
    db = SessionLocal()
    try:
        job = (
            db.query(ScrapeJob)
            .filter(ScrapeJob.status == "pending")
            .order_by(ScrapeJob.created_at.asc())
            .first()
        )
        if not job:
            return False
        job.status = "running"
        job.started_at = _utcnow()
        db.commit()

        creator = db.query(Creator).get(job.creator_id)
        if not creator:
            job.status = "failed"
            job.error = "creator missing"
            job.finished_at = _utcnow()
            db.commit()
            return True

        try:
            log.info("scraping @%s (job %s)", creator.username, job.id)
            result = scrape_creator(creator.username)
            touched = ingest_result(db, creator, result)
            creator.scrape_status = "ready"
            creator.scrape_error = ""
            job.status = "done"
            job.posts_scraped = touched
            job.finished_at = _utcnow()
            db.commit()
            log.info("done @%s: %d posts", creator.username, touched)
        except Exception as e:  # noqa: BLE001
            db.rollback()
            creator = db.query(Creator).get(job.creator_id)
            if creator:
                creator.scrape_status = "failed"
                creator.scrape_error = str(e)[:500]
            job.status = "failed"
            job.error = str(e)[:500]
            job.finished_at = _utcnow()
            db.commit()
            log.error("failed @%s: %s", job.creator_id, e)
        return True
    finally:
        db.close()


def main():
    log.info("worker up — polling every %ss", POLL_SECONDS)
    while True:
        try:
            worked = process_one()
        except Exception as e:  # noqa: BLE001 — never let the loop die
            log.error("loop error: %s", e)
            worked = False
        if not worked:
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
