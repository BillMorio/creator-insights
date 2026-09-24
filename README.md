# Creator Insights

Standalone dashboard to track Instagram **creators**: paste an account link, a
background job scrapes their profile + recent posts, and you get per-post
engagement (views/likes/comments). Grid⇄table dashboard → click a creator →
posts table → CSV export (`creator, link, views, likes, comments`).

**Isolated from lumina-clippers** — own repo, own Render services, own DB.

## Stack
- **Backend:** FastAPI + SQLAlchemy + Postgres (Render). Schema at boot (no Alembic).
- **Worker:** polls a `scrape_job` queue → Apify grid actor → ingest.
- **Frontend:** Next.js (Vercel).
- **Scraping:** Apify **grid actor** — reel view counts (`play_count`) come only
  from the profile Reels-grid, so a per-post scraper is NOT enough.

## Data model
`creator` (IG account) 1─* `post`; `scrape_job` tracks work.

## Backend — run locally
```bash
cd backend
python -m venv .venv && .venv/Scripts/activate   # (Windows) or source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # fill DATABASE_URL (external), APIFY_TOKEN, APIFY_IG_ACTOR
uvicorn main:app --reload      # API on :8000
python worker.py               # queue worker (separate shell)
```

## Key endpoints
- `POST /api/creators` `{link}` — add one (enqueues a scrape)
- `POST /api/creators/bulk` `{links:[...]}` — add many
- `GET  /api/creators` — dashboard list (+ post_count, total_views)
- `GET  /api/creators/{id}` — detail + posts
- `POST /api/creators/{id}/refresh` — re-scrape
- `GET  /api/creators/{id}/export` — CSV
- `GET  /api/jobs/{id}` — poll a scrape job (drives the "Scraping…" pill)

## Deploy
- API + worker → Render (Docker); DB = `creator-insights-db`.
- Frontend → Vercel.
