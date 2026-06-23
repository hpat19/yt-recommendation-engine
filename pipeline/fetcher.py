
"""
pipeline/fetcher.py
  
This module's job is to get data from YouTube and return it as raw
Python dictionaries. It does not clean, validate, or store anything,
that is the job of the cleaner and indexer modules. Keeping this file
focused on one responsibility means YouTube API changes only ever affect
this file.
"""
 
import os
import time
import logging
 
import httpx
from dotenv import load_dotenv
 
# Load variables from the project's .env file (YOUTUBE_API_KEY lives there).
load_dotenv()
 
logger = logging.getLogger(__name__)
 
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
BASE_URL = "https://www.googleapis.com/youtube/v3"
 
 
class YouTubeFetchError(Exception):
    """Raised when the YouTube API returns an error we cannot recover from."""
 
 
def fetch_trending_videos(region_code: str = "US", max_results: int = 50,
    category_id: str | None = None,) -> list[dict]:
    """
    Fetch the most popular ("trending") videos for a region.
 
    Args:
        region_code: ISO country code, e.g. "US".
        max_results: total number of videos to return across all pages.
        category_id: optional YouTube category id to filter by.
 
    Returns:
        A list of raw video items (dicts) exactly as the API returns them.
    """
    if not YOUTUBE_API_KEY:
        raise YouTubeFetchError(
            "YOUTUBE_API_KEY is not set. Check that your .env file exists and "
            "contains a valid key."
        )
 
    collected: list[dict] = []
    page_token: str | None = None
 
    # The API returns at most 50 items per page, so we loop through pages
    # until we have collected max_results videos (or run out of pages).
    while len(collected) < max_results:
        params = {
            "part": "snippet,statistics,contentDetails",
            "chart": "mostPopular",
            "regionCode": region_code,
            "maxResults": min(50, max_results - len(collected)),
            "key": YOUTUBE_API_KEY,
        }
        if category_id:
            params["videoCategoryId"] = category_id
        if page_token:
            params["pageToken"] = page_token
 
        data = _get(f"{BASE_URL}/videos", params)
        collected.extend(data.get("items", []))
 
        page_token = data.get("nextPageToken")
        if not page_token:
            break  # No more pages available.
 
    logger.info(
        "Fetched %d trending videos for region %s", len(collected), region_code
    )
    return collected[:max_results]
 
 
def _get(url: str, params: dict, max_retries: int = 3) -> dict:
    """
    Make a GET request with basic retry handling, returning parsed JSON.
 
    Retries transient failures (rate limits and server errors) with
    exponential backoff. Fails loudly on errors that retrying won't fix.
    """
    for attempt in range(1, max_retries + 1):
        response = httpx.get(url, params=params, timeout=10.0)
 
        if response.status_code == 200:
            return response.json()
 
        # 429 (too many requests) and 5xx (server hiccup) are usually
        # temporary, so wait and try again: 2s, then 4s, then 8s.
        if response.status_code == 429 or response.status_code >= 500:
            wait = 2 ** attempt
            logger.warning(
                "Transient error %s (attempt %d/%d). Retrying in %ds...",
                response.status_code, attempt, max_retries, wait,
            )
            time.sleep(wait)
            continue
 
        # 403 is almost always a daily quota exhaustion or a key restriction.
        # Retrying won't help, so surface a clear message instead.
        if response.status_code == 403:
            raise YouTubeFetchError(
                "403 Forbidden -- likely your daily quota is exceeded or the "
                f"API key is restricted. Details: {response.text}"
            )
 
        # Anything else (e.g. 400 bad request) is a bug in our request.
        raise YouTubeFetchError(
            f"YouTube API error {response.status_code}: {response.text}"
        )
 
    raise YouTubeFetchError(f"Failed after {max_retries} retries: {url}")
 
 
if __name__ == "__main__":
    # Manual test. Run from the project root with:  python -m pipeline.fetcher
    logging.basicConfig(level=logging.INFO)
    videos = fetch_trending_videos(region_code="US", max_results=10)
    print(f"\nFetched {len(videos)} videos:\n")
    for i, video in enumerate(videos, start=1):
        title = video["snippet"]["title"]
        channel = video["snippet"]["channelTitle"]
        print(f"{i}. {title} — {channel}")