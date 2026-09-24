"""Instagram creator scraper.

Runs an Apify actor that scrapes a profile + its Reels/posts grid and returns
per-post engagement. IMPORTANT: a reel's view count (play_count) is only
reliably available via the profile Reels-GRID JSON — the standard per-post
media-info endpoint no longer returns it. So the actor MUST be a grid/profile
scraper, not a per-post one. Configure the actor id via APIFY_IG_ACTOR.

This module is transport-agnostic about which actor: it normalizes several
common Apify IG output shapes into our {profile, posts} structure.
"""
import os
import re
import time
from datetime import datetime, timezone

import httpx

APIFY_TOKEN = os.getenv("APIFY_TOKEN", "")
# Actor that scrapes a profile's posts and returns them WITH view counts.
# Validated: apify~instagram-scraper returns videoPlayCount/videoViewCount for
# reels/videos (run ASYNC + poll — run-sync returns empty on slower profiles).
APIFY_IG_ACTOR = os.getenv("APIFY_IG_ACTOR", "apify~instagram-scraper")
POSTS_LIMIT = int(os.getenv("POSTS_LIMIT", "100"))
RUN_POLL_SECONDS = int(os.getenv("RUN_POLL_SECONDS", "6"))
RUN_MAX_WAIT = int(os.getenv("RUN_MAX_WAIT", "600"))

APIFY_BASE = "https://api.apify.com/v2"


def username_from_link(link: str) -> str:
    """Extract a bare username from a profile URL / @handle / plain username."""
    s = (link or "").strip()
    s = s.split("?")[0].rstrip("/")
    m = re.search(r"instagram\.com/([^/]+)", s, re.I)
    if m:
        return m.group(1).lstrip("@")
    return s.lstrip("@")


def _to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _first(d: dict, *keys, default=None):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default


def _parse_ts(v):
    if v is None:
        return None
    try:
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v, tz=timezone.utc)
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except (ValueError, OSError):
        return None


def _normalize_post(item: dict) -> dict | None:
    shortcode = _first(item, "shortCode", "shortcode", "code")
    if not shortcode:
        url = _first(item, "url", "postUrl", default="")
        m = re.search(r"/(?:reel|reels|p|tv)/([^/?]+)", url)
        shortcode = m.group(1) if m else None
    if not shortcode:
        return None
    mtype = (_first(item, "type", "productType", "mediaType", default="") or "").lower()
    if "clips" in mtype or "reel" in mtype:
        mtype = "reel"
    return {
        "shortcode": shortcode,
        "url": _first(item, "url", "postUrl", default=f"https://www.instagram.com/reel/{shortcode}"),
        "media_type": mtype,
        "views": _to_int(_first(item, "videoPlayCount", "playCount", "videoViewCount", "views", "ig_play_count")),
        "likes": _to_int(_first(item, "likesCount", "likes", default=0)) or 0,
        "comments": _to_int(_first(item, "commentsCount", "comments", default=0)) or 0,
        "caption": _first(item, "caption", "text", default="") or "",
        "thumbnail_url": _first(item, "displayUrl", "thumbnailUrl", "imageUrl", default="") or "",
        "posted_at": _parse_ts(_first(item, "timestamp", "takenAt", "taken_at")),
    }


def _normalize_dataset(items: list[dict], username: str) -> dict:
    """Turn Apify dataset items into {profile, posts}. Handles both shapes:
    a single profile object with a nested `latestPosts`/`posts` array, or a flat
    list of post objects."""
    profile = {"username": username, "full_name": "", "followers": 0,
               "media_count": 0, "profile_pic_url": "", "is_private": False,
               "ig_user_id": None, "bio": ""}
    posts_raw: list[dict] = []
    for it in items:
        if any(k in it for k in ("username", "followersCount", "postsCount")):
            profile["username"] = _first(it, "username", default=username) or username
            profile["full_name"] = _first(it, "fullName", "full_name", default="") or ""
            profile["followers"] = _to_int(_first(it, "followersCount", "followers")) or 0
            profile["media_count"] = _to_int(_first(it, "postsCount", "mediaCount", "posts_count")) or 0
            profile["profile_pic_url"] = _first(it, "profilePicUrl", "profilePicUrlHD", default="") or ""
            profile["is_private"] = bool(_first(it, "private", "isPrivate", default=False))
            profile["ig_user_id"] = _first(it, "id", "pk", "userId")
            profile["bio"] = _first(it, "biography", "bio", default="") or ""
            nested = _first(it, "latestPosts", "posts", "reels", default=None)
            if isinstance(nested, list):
                posts_raw.extend(nested)
        elif any(k in it for k in ("shortCode", "shortcode", "playCount", "videoPlayCount")):
            posts_raw.append(it)
            # apify~instagram-scraper attaches owner info on each post
            if not profile["full_name"] and it.get("ownerFullName"):
                profile["full_name"] = it.get("ownerFullName") or ""
            if not profile["ig_user_id"] and it.get("ownerId"):
                profile["ig_user_id"] = it.get("ownerId")
            if it.get("ownerUsername"):
                profile["username"] = it["ownerUsername"]
    posts = [p for p in (_normalize_post(x) for x in posts_raw) if p]
    # de-dupe by shortcode, keep first
    seen, uniq = set(), []
    for p in posts:
        if p["shortcode"] in seen:
            continue
        seen.add(p["shortcode"])
        uniq.append(p)
    if not profile["media_count"]:
        profile["media_count"] = len(uniq)
    return {"profile": profile, "posts": uniq}


def scrape_creator(username: str, limit: int | None = None) -> dict:
    """Run the Apify actor for one username (async run -> poll -> dataset).
    Returns {profile, posts, run_id}. Raises on hard failure so the worker can
    mark the job failed. run-sync is avoided: it returns empty on slower runs."""
    if not APIFY_TOKEN:
        raise RuntimeError("APIFY_TOKEN must be set")
    limit = limit or POSTS_LIMIT
    run_input = {
        "directUrls": [f"https://www.instagram.com/{username}/"],
        "resultsType": "posts",
        "resultsLimit": limit,
        "addParentData": True,          # attaches owner/profile info to items
    }
    with httpx.Client(timeout=60) as client:
        started = client.post(
            f"{APIFY_BASE}/acts/{APIFY_IG_ACTOR}/runs?token={APIFY_TOKEN}", json=run_input
        )
        started.raise_for_status()
        run = started.json().get("data", {})
        run_id = run.get("id")
        dataset_id = run.get("defaultDatasetId")

        waited = 0
        status = run.get("status")
        while status not in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            if waited >= RUN_MAX_WAIT:
                raise RuntimeError(f"Apify run {run_id} timed out after {waited}s")
            time.sleep(RUN_POLL_SECONDS)
            waited += RUN_POLL_SECONDS
            d = client.get(f"{APIFY_BASE}/actor-runs/{run_id}?token={APIFY_TOKEN}").json().get("data", {})
            status = d.get("status")
            dataset_id = d.get("defaultDatasetId", dataset_id)

        if status != "SUCCEEDED":
            raise RuntimeError(f"Apify run {run_id} ended {status}")

        items = client.get(
            f"{APIFY_BASE}/datasets/{dataset_id}/items?token={APIFY_TOKEN}&clean=true&limit={limit}",
            timeout=120,
        ).json()

    if not isinstance(items, list):
        items = []
    result = _normalize_dataset(items, username)
    result["run_id"] = run_id
    return result
