"""
pipeline/cleaner.py
 
Turns raw YouTube API video dicts into clean,
flat records that are ready for the database.
 
The fetcher file hands us nested dicts with values in awkward formats --
view counts as strings ("1452334"), durations as ISO 8601 ("PT4M13S"), and
some fields missing entirely. This module's job is to flatten that mess into
a predictable, typed shape, and to never crash on a missing field.
"""
 
import re
import logging
 
logger = logging.getLogger(__name__)
 
# Matches ISO 8601 durations like "PT4M13S", "PT1H2M", "PT45S".
# Each group is optional, so it handles any combination of H / M / S.
_DURATION_RE = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")
 
 
def clean_videos(raw_videos: list[dict]) -> list[dict]:
    """
    Clean a list of raw video dicts, skipping any that can't be cleaned.
 
    Returns a list of flat, typed records ready for the indexer.
    """
    cleaned: list[dict] = []
    for raw in raw_videos:
        record = clean_video(raw)
        if record is not None:
            cleaned.append(record)
 
    logger.info("Cleaned %d of %d videos", len(cleaned), len(raw_videos))
    return cleaned
 
 
def clean_video(raw: dict) -> dict | None:
    """
    Flatten a single raw video dict into a clean record.
 
    Returns None if the video is missing essential data,
    so the caller can skip it rather than store garbage.
    """
    video_id = raw.get("id")
    if not video_id:
        # Without an id we can't store or reference the video.
        return None
 
    # .get() with a default ({}) means a missing block won't raise an error.
    snippet = raw.get("snippet", {})
    statistics = raw.get("statistics", {})
    content_details = raw.get("contentDetails", {})
 
    return {
        "video_id": video_id,
        "title": snippet.get("title", ""),
        "channel_id": snippet.get("channelId", ""),
        "channel_title": snippet.get("channelTitle", ""),
        "published_at": snippet.get("publishedAt"),
        "category_id": snippet.get("categoryId"),
        "tags": snippet.get("tags", []),
        "view_count": _to_int(statistics.get("viewCount")),
        "like_count": _to_int(statistics.get("likeCount")),
        "comment_count": _to_int(statistics.get("commentCount")),
        "duration_seconds": _parse_duration(content_details.get("duration")),
    }
 
 
def _to_int(value: str | None) -> int | None:
    """
    Convert a count the API returns as a string ("1452334") into an int.

    Returns None if the value is missing (the API hid it), which is
    distinct from a real count of 0. Callers can then decide how to
    treat "unknown" versus "zero".
    """
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
 
 
def _parse_duration(iso_duration: str | None) -> int:
    """
    Convert an ISO 8601 duration ("PT4M13S") into total seconds (253).
 
    Returns 0 if the duration is missing or unparseable.
    """
    if not iso_duration:
        return 0
 
    match = _DURATION_RE.fullmatch(iso_duration)
    if not match:
        return 0
 
    # Each group is the number before H, M, or S -- or None if absent.
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds
 
 
if __name__ == "__main__":
    # Manual test: fetch a few real videos, then clean them.
    # Run from the project root with:  python -m pipeline.cleaner
    import json
    from pipeline.fetcher import fetch_trending_videos
 
    logging.basicConfig(level=logging.INFO)
    raw = fetch_trending_videos(region_code="US", max_results=5)
    cleaned = clean_videos(raw)
 
    print("\nFirst cleaned record:\n")
    print(json.dumps(cleaned[0], indent=2, ensure_ascii=False))