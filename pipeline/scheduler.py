"""
pipeline/scheduler.py

Run the ingestion pipeline on a timer.

A BlockingScheduler owns this process -- it exists only to refresh trending
data every REFRESH_HOURS hours. One failed run logs the error and the
scheduler keeps ticking; a transient API or network failure must never kill
the worker.
"""

import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from pipeline.run import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

REFRESH_HOURS = 6 

def refresh_job():
    """One scheduled refresh. Catches everything: log and survive."""
    try:
        run_pipeline()
    except Exception:
        logger.exception("Scheduled pipeline run failed -- will retry next tick")


def main():
    scheduler = BlockingScheduler()

    scheduler.add_job(
        refresh_job,
        trigger="interval",
        hours=REFRESH_HOURS,
        id="refresh_trending",
    )

    logger.info("Running initial pipeline pass before starting scheduler")
    refresh_job()

    logger.info("Starting scheduler: refreshing every %d hours", REFRESH_HOURS)
    scheduler.start()  # blocks forever; Ctrl+C to stop


if __name__ == "__main__":
    main()