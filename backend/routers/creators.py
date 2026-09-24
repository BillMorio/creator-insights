"""Creator endpoints: add (single + bulk), list, detail, refresh, CSV export."""
import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import Creator, Post, ScrapeJob
from schemas import BulkCreatorCreate, CreatorCreate, CreatorDetail, CreatorOut, PostOut
from services.scraper import username_from_link

router = APIRouter(prefix="/api/creators", tags=["creators"])


def _aggregates(db: Session, creator_ids: list[int]) -> dict[int, tuple[int, int]]:
    """{creator_id: (post_count, total_views)} in one query."""
    if not creator_ids:
        return {}
    rows = (
        db.query(Post.creator_id, func.count(Post.id), func.coalesce(func.sum(Post.views), 0))
        .filter(Post.creator_id.in_(creator_ids))
        .group_by(Post.creator_id)
        .all()
    )
    return {cid: (cnt, int(views or 0)) for cid, cnt, views in rows}


def _creator_out(c: Creator, agg: dict) -> CreatorOut:
    post_count, total_views = agg.get(c.id, (0, 0))
    out = CreatorOut.model_validate(c)
    out.post_count = post_count
    out.total_views = total_views
    return out


def _enqueue(db: Session, creator: Creator) -> ScrapeJob:
    creator.scrape_status = "scraping"
    job = ScrapeJob(creator_id=creator.id, status="pending")
    db.add(job)
    return job


def _add_one(db: Session, link: str) -> Creator:
    username = username_from_link(link)
    if not username:
        raise HTTPException(status_code=400, detail=f"Could not parse a username from: {link}")
    creator = db.query(Creator).filter(func.lower(Creator.username) == username.lower()).first()
    if creator is None:
        creator = Creator(username=username, profile_url=f"https://www.instagram.com/{username}")
        db.add(creator)
        db.flush()
    _enqueue(db, creator)
    return creator


@router.post("", response_model=CreatorOut, status_code=201)
def add_creator(body: CreatorCreate, db: Session = Depends(get_db)):
    creator = _add_one(db, body.link)
    db.commit()
    db.refresh(creator)
    return _creator_out(creator, _aggregates(db, [creator.id]))


@router.post("/bulk", response_model=list[CreatorOut], status_code=201)
def add_creators_bulk(body: BulkCreatorCreate, db: Session = Depends(get_db)):
    created = []
    for link in body.links:
        link = (link or "").strip()
        if not link:
            continue
        try:
            created.append(_add_one(db, link))
        except HTTPException:
            continue
    db.commit()
    ids = [c.id for c in created]
    agg = _aggregates(db, ids)
    return [_creator_out(db.query(Creator).get(cid), agg) for cid in ids]


@router.get("", response_model=list[CreatorOut])
def list_creators(db: Session = Depends(get_db)):
    creators = db.query(Creator).order_by(Creator.created_at.desc()).all()
    agg = _aggregates(db, [c.id for c in creators])
    return [_creator_out(c, agg) for c in creators]


@router.get("/export-all")
def export_all_csv(db: Session = Depends(get_db)):
    """Every post across every creator, with the creator column."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["creator", "link", "views", "likes", "comments"])
    for c in db.query(Creator).order_by(Creator.username).all():
        for p in sorted(c.posts, key=lambda p: (p.views or 0), reverse=True):
            w.writerow([c.username, p.url, p.views if p.views is not None else "", p.likes, p.comments])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="all_creators_posts.csv"'},
    )


@router.get("/{creator_id}", response_model=CreatorDetail)
def get_creator(creator_id: int, db: Session = Depends(get_db)):
    c = db.query(Creator).get(creator_id)
    if not c:
        raise HTTPException(status_code=404, detail="Creator not found")
    agg = _aggregates(db, [c.id])
    out = CreatorDetail.model_validate(c)
    out.post_count, out.total_views = agg.get(c.id, (0, 0))
    posts = sorted(c.posts, key=lambda p: (p.views or 0), reverse=True)
    out.posts = [PostOut.model_validate(p) for p in posts]
    return out


@router.post("/{creator_id}/refresh", response_model=CreatorOut)
def refresh_creator(creator_id: int, db: Session = Depends(get_db)):
    c = db.query(Creator).get(creator_id)
    if not c:
        raise HTTPException(status_code=404, detail="Creator not found")
    _enqueue(db, c)
    db.commit()
    db.refresh(c)
    return _creator_out(c, _aggregates(db, [c.id]))


@router.delete("/{creator_id}", status_code=204)
def delete_creator(creator_id: int, db: Session = Depends(get_db)):
    c = db.query(Creator).get(creator_id)
    if not c:
        raise HTTPException(status_code=404, detail="Creator not found")
    db.delete(c)
    db.commit()


@router.get("/{creator_id}/export")
def export_creator_csv(creator_id: int, db: Session = Depends(get_db)):
    c = db.query(Creator).get(creator_id)
    if not c:
        raise HTTPException(status_code=404, detail="Creator not found")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["creator", "link", "views", "likes", "comments"])
    for p in sorted(c.posts, key=lambda p: (p.views or 0), reverse=True):
        w.writerow([c.username, p.url, p.views if p.views is not None else "", p.likes, p.comments])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{c.username}_posts.csv"'},
    )
