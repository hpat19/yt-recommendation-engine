"""
pipeline/run.py

The pipeline as a single callable: fetch -> clean -> index.

This exists so anything -- the scheduler, a CLI run, a future admin endpoint
-- can trigger one refresh by calling one function, without knowing how the
stages fit together.
"""

import logging

from pipeline.fetcher import fetch_trending_videos
from pipeline.cleaner import clean_videos
from pipeline.indexer import index_videos

logger = logging.getLogger(__name__)


def run_pipeline(max_results: int = 50) -> int:
    """
    Run one full ingestion pass: fetch trending, clean, store.

    Returns the number of videos indexed.
    """
    logger.info("Pipeline run starting")

    raw = fetch_trending_videos(max_results=max_results)
    cleaned = clean_videos(raw)
    count = index_videos(cleaned)

    logger.info("Pipeline run finished: %d videos indexed", count)
    return count


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_pipeline()