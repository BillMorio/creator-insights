"""Persist a scrape result ({profile, posts}) onto a Creator + its Posts."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models import Creator, Post


def _utcnow():
    return datetime.now(timezone.utc)


def ingest_result(db: Session, creator: Creator, result: dict) -> int:
    """Update creator profile fields and upsert posts. Views are RAISE-ONLY
    (a later scrape never lowers a play_count). Returns number of posts touched."""
    prof = result.get("profile", {}) or {}
    if prof.get("full_name"):
        creator.full_name = prof["full_name"]
    if prof.get("followers"):
        creator.followers = prof["followers"]
    if prof.get("media_count"):
        creator.media_count = prof["media_count"]
    if prof.get("profile_pic_url"):
        creator.profile_pic_url = prof["profile_pic_url"]
    if prof.get("ig_user_id"):
        creator.ig_user_id = str(prof["ig_user_id"])
    if prof.get("bio"):
        creator.bio = prof["bio"]
    creator.is_private = bool(prof.get("is_private", creator.is_private))

    existing = {p.shortcode: p for p in creator.posts}
    touched = 0
    for pd in result.get("posts", []) or []:
        sc = pd["shortcode"]
        p = existing.get(sc)
        if p is None:
            p = Post(creator_id=creator.id, shortcode=sc, url=pd["url"])
            db.add(p)
            existing[sc] = p
        p.url = pd.get("url") or p.url
        p.media_type = pd.get("media_type") or p.media_type
        # raise-only on views
        new_views = pd.get("views")
        if new_views is not None and (p.views is None or new_views > p.views):
            p.views = new_views
        p.likes = pd.get("likes", p.likes) or 0
        p.comments = pd.get("comments", p.comments) or 0
        if pd.get("caption"):
            p.caption = pd["caption"]
        if pd.get("thumbnail_url"):
            p.thumbnail_url = pd["thumbnail_url"]
        if pd.get("posted_at"):
            p.posted_at = pd["posted_at"]
        p.last_scraped_at = _utcnow()
        touched += 1

    creator.last_scraped_at = _utcnow()
    return touched
