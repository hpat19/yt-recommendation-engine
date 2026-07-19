"""
api/models/schemas.py

Pydantic models: the declared shapes of everything the API returns.

FastAPI uses these to validate and serialize responses and to generate the
interactive docs at /docs. Field types are honest about the data: count
fields are `int | None` because the pipeline stores NULL for counts the
YouTube API withheld -- unknown is not zero, all the way out to the JSON.
"""

from datetime import datetime

from pydantic import BaseModel


class Video(BaseModel):
    video_id: str
    title: str
    channel_id: str | None = None
    channel_title: str | None = None
    published_at: datetime | None = None
    category_id: str | None = None
    tags: list[str] = []
    view_count: int | None = None
    like_count: int | None = None
    comment_count: int | None = None
    duration_seconds: int


class Recommendation(BaseModel):
    video_id: str
    title: str
    score: float


class RefreshResult(BaseModel):
    corpus_size: int