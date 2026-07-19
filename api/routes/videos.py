"""
api/routes/videos.py

The API's three endpoints:

  GET  /trending            -- most-viewed videos from the database
  GET  /recommend/{id}      -- content-based recommendations for a video
  POST /refresh             -- rebuild the recommender's in-memory model

The API is a pure READ layer over what the pipeline maintains: it never
calls YouTube and never writes video data. The one "write" here, /refresh,
only touches in-process state (the cached TF-IDF model), not the database.
"""

import logging

from fastapi import APIRouter, HTTPException, Query

from db.connection import get_connection
from recommender.content_based import get_similar_videos, _get_model
from api.models.schemas import Video, Recommendation, RefreshResult

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/trending", response_model=list[Video])
def trending(limit: int = Query(default=10, ge=1, le=100)):
    """Most-viewed videos currently in the corpus."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT v.video_id, v.title, v.channel_id, c.channel_title,
                       v.published_at, v.category_id, v.tags,
                       v.view_count, v.like_count, v.comment_count,
                       v.duration_seconds
                FROM videos v
                LEFT JOIN channels c ON v.channel_id = c.channel_id
                ORDER BY v.view_count DESC NULLS LAST
                LIMIT %(limit)s;
                """,
                {"limit": limit},
            )
            rows = cur.fetchall()
    return rows


@router.get("/recommend/{video_id}", response_model=list[Recommendation])
def recommend(video_id: str, limit: int = Query(default=10, ge=1, le=50)):
    """Videos most similar to the given video, ranked by cosine similarity."""
    try:
        return get_similar_videos(video_id, limit=limit)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Video {video_id!r} not found in corpus",
        )


@router.post("/refresh", response_model=RefreshResult)
def refresh():
    """
    Rebuild the recommender model from the current database contents.

    The scheduler updates Postgres every 6 hours in a separate process; this
    API process caches the TF-IDF model in memory, so without this endpoint
    a long-running API would serve recommendations from a stale corpus.
    """
    model = _get_model(refresh=True)
    corpus_size = len(model["ids"])
    logger.info("Recommender model refreshed: %d videos in corpus", corpus_size)
    return {"corpus_size": corpus_size}