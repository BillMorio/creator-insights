"""Data model: a Creator (IG account) has many Posts; ScrapeJobs track work."""
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text, BigInteger, Index,
)
from sqlalchemy.orm import relationship

from database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Creator(Base):
    __tablename__ = "creators"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False, index=True)
    profile_url = Column(String, nullable=False)
    ig_user_id = Column(String, nullable=True)          # IG numeric pk (stable across renames)
    full_name = Column(String, default="")
    followers = Column(BigInteger, default=0)
    media_count = Column(Integer, default=0)            # their total posts on IG ("submissions")
    profile_pic_url = Column(Text, default="")
    is_private = Column(Boolean, default=False)
    bio = Column(Text, default="")

    scrape_status = Column(String, default="pending")   # pending | scraping | ready | failed
    scrape_error = Column(Text, default="")
    last_scraped_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    posts = relationship("Post", back_populates="creator", cascade="all, delete-orphan")


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    creator_id = Column(Integer, ForeignKey("creators.id", ondelete="CASCADE"), nullable=False, index=True)
    shortcode = Column(String, nullable=False, index=True)
    url = Column(String, nullable=False)
    media_type = Column(String, default="")             # reel | video | photo | carousel
    views = Column(BigInteger, nullable=True)           # play_count — reels/videos only
    likes = Column(BigInteger, default=0)
    comments = Column(BigInteger, default=0)
    caption = Column(Text, default="")
    thumbnail_url = Column(Text, default="")
    posted_at = Column(DateTime, nullable=True)
    last_scraped_at = Column(DateTime, default=_utcnow)

    creator = relationship("Creator", back_populates="posts")

    __table_args__ = (Index("ix_posts_creator_shortcode", "creator_id", "shortcode", unique=True),)


class ScrapeJob(Base):
    __tablename__ = "scrape_jobs"

    id = Column(Integer, primary_key=True)
    creator_id = Column(Integer, ForeignKey("creators.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, default="pending")          # pending | running | done | failed
    apify_run_id = Column(String, nullable=True)
    posts_scraped = Column(Integer, default=0)
    error = Column(Text, default="")
    created_at = Column(DateTime, default=_utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
