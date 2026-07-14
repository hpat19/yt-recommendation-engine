"""
db/connection.py

Shared database connection helper.

Reads DATABASE_URL from .env and hands out connections. Everything that
touches Postgres (indexer, recommender, API) goes through here, so the
connection logic lives in exactly one place.
"""

import os
import logging
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Add it to your .env file "
        "(see .env.example for the expected format)."
    )


@contextmanager
def get_connection():
    """
    Yield a database connection, committing on success and rolling back
    on error. Always closes the connection, even if something blows up.
    """
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("Database error -- rolling back transaction")
        raise
    finally:
        conn.close()