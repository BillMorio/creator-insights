"""Pydantic response/request models."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CreatorCreate(BaseModel):
    # Accepts a profile URL OR a bare @username / username.
    link: str


class BulkCreatorCreate(BaseModel):
    links: list[str]


class PostOut(BaseModel):
    id: int
    shortcode: str
    url: str
    media_type: str
    views: Optional[int] = None
    likes: int = 0
    comments: int = 0
    caption: str = ""
    thumbnail_url: str = ""
    posted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CreatorOut(BaseModel):
    id: int
    username: str
    profile_url: str
    full_name: str = ""
    followers: int = 0
    media_count: int = 0
    profile_pic_url: str = ""
    is_private: bool = False
    scrape_status: str
    scrape_error: str = ""
    last_scraped_at: Optional[datetime] = None
    created_at: datetime
    # aggregates for the dashboard card
    post_count: int = 0          # posts we actually scraped
    total_views: int = 0

    class Config:
        from_attributes = True


class CreatorDetail(CreatorOut):
    posts: list[PostOut] = []


class ScrapeJobOut(BaseModel):
    id: int
    creator_id: int
    status: str
    posts_scraped: int = 0
    error: str = ""
    created_at: datetime
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True
