"""
pipeline/indexer.py

Stage 3 of the data pipeline: persist cleaned video records into PostgreSQL.

Takes the flat, typed records from the cleaner and writes them into the
channels and videos tables. Writes are idempotent -- re-running on videos
we've already stored updates their stats rather than erroring, which is what
lets the scheduler refresh trending data on a timer.
"""

import logging

from db.connection import get_connection

logger = logging.getLogger(__name__)


# The channel must exist before the video that references it (foreign key).
# DO NOTHING because channel_title rarely changes and we have nothing new
# to say about a channel we've already seen.
UPSERT_CHANNEL = """
    INSERT INTO channels (channel_id, channel_title)
    VALUES (%(channel_id)s, %(channel_title)s)
    ON CONFLICT (channel_id) DO NOTHING;
"""

# DO UPDATE (not DO NOTHING) because view/like/comment counts change over
# time -- re-indexing a trending video should refresh its stats.
UPSERT_VIDEO = """
    INSERT INTO videos (
        video_id, channel_id, title, published_at, category_id,
        tags, view_count, like_count, comment_count, duration_seconds
    )
    VALUES (
        %(video_id)s, %(channel_id)s, %(title)s, %(published_at)s,
        %(category_id)s, %(tags)s, %(view_count)s, %(like_count)s,
        %(comment_count)s, %(duration_seconds)s
    )
    ON CONFLICT (video_id) DO UPDATE SET
        title            = EXCLUDED.title,
        tags             = EXCLUDED.tags,
        view_count       = EXCLUDED.view_count,
        like_count       = EXCLUDED.like_count,
        comment_count    = EXCLUDED.comment_count,
        duration_seconds = EXCLUDED.duration_seconds,
        updated_at       = now();
"""


def index_videos(records: list[dict]) -> int:
    """
    Write cleaned video records to the database.

    Returns the number of records successfully indexed.
    """
    if not records:
        logger.info("No records to index")
        return 0

    indexed = 0

    with get_connection() as conn:
        with conn.cursor() as cur:
            for record in records:
                cur.execute(
                    UPSERT_CHANNEL,
                    {
                        "channel_id": record["channel_id"],
                        "channel_title": record["channel_title"],
                    },
                )
                cur.execute(UPSERT_VIDEO, record)
                indexed += 1

    logger.info("Indexed %d of %d videos", indexed, len(records))
    return indexed


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    from pipeline.fetcher import fetch_trending_videos
    from pipeline.cleaner import clean_videos

    raw = fetch_trending_videos(max_results=5)
    cleaned = clean_videos(raw)
    count = index_videos(cleaned)

    print(f"\nIndexed {count} videos into PostgreSQL.")