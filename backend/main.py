"""FastAPI app: schema bootstrap + routers. No Alembic — create_all at boot
(add idempotent ADD COLUMN calls to _add_columns as the schema evolves)."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from database import Base, engine
import models  # noqa: F401 — register tables on Base
from routers import creators, jobs

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("main")

app = FastAPI(title="Creator Insights API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # unlisted internal tool; tighten later if needed
    allow_methods=["*"],
    allow_headers=["*"],
)


def _add_columns():
    """Idempotent ADD COLUMN migrations for existing tables. Append as needed."""
    stmts: list[str] = [
        # ("ALTER TABLE creators ADD COLUMN IF NOT EXISTS new_col TEXT DEFAULT ''"),
    ]
    if not stmts:
        return
    with engine.begin() as conn:
        for s in stmts:
            conn.execute(text(s))


@app.on_event("startup")
def _startup():
    Base.metadata.create_all(bind=engine)
    _add_columns()
    log.info("schema ready")


app.include_router(creators.router)
app.include_router(jobs.router)


@app.get("/health")
def health():
    return {"status": "healthy"}
