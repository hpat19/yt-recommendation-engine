"""
recommender/content_based.py

Content-based recommender: find videos similar to a given video using
TF-IDF over each video's tags and title, compared with cosine similarity.

This is the first stage that READS from the database instead of writing to
it. It loads the corpus, turns each video into a text document, fits a
TF-IDF vectorizer over the whole corpus, and answers "what's similar to
video X?" by ranking cosine similarities.

The fitted model is cached in memory per process. At trending-corpus scale
(tens to low thousands of videos) fitting takes milliseconds, so we rebuild
on demand rather than precomputing scores into the database.
"""

import logging

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from db.connection import get_connection

logger = logging.getLogger(__name__)

# Module-level cache: built on first use, reused for the life of the process.
_model = None


def _load_corpus() -> list[dict]:
    """
    Load every video's id, title, and tags from the database.

    Returns a list of row dicts (RealDictCursor gives us dicts, not tuples).
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT video_id, title, tags FROM videos ORDER BY video_id;"
            )
            rows = cur.fetchall()

    logger.info("Loaded %d videos from database", len(rows))
    return rows


def _build_document(row: dict) -> str:
    """
    Turn one video row into the text document TF-IDF will vectorize.

    Tags carry the strongest topical signal; the title is always present,
    so no video ends up with an empty document even when tags are missing.
    """
    tags = row["tags"] or []
    title = row["title"] or ""
    return " ".join(tags) + " " + title


def _build_model() -> dict:
    """
    Load the corpus, fit TF-IDF, and precompute the similarity matrix.

    Returns everything lookups need, bundled in one dict:
      - ids:        video_id per matrix row
      - id_to_row:  reverse lookup, video_id -> matrix row index
      - titles:     video_id -> title, for human-readable output
      - similarity: NxN matrix of cosine similarities between all videos
    """
    rows = _load_corpus()
    if not rows:
        raise RuntimeError(
            "No videos in database -- run the pipeline first "
            "(python -m pipeline.run)."
        )

    documents = [_build_document(row) for row in rows]

    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
    )
    tfidf_matrix = vectorizer.fit_transform(documents)
    similarity = cosine_similarity(tfidf_matrix)

    ids = [row["video_id"] for row in rows]
    return {
        "ids": ids,
        "id_to_row": {vid: i for i, vid in enumerate(ids)},
        "titles": {row["video_id"]: row["title"] for row in rows},
        "similarity": similarity,
    }


def _get_model(refresh: bool = False) -> dict:
    """Return the cached model, building it on first use (or on refresh)."""
    global _model
    if _model is None or refresh:
        _model = _build_model()
    return _model


def get_similar_videos(video_id: str, limit: int = 10) -> list[dict]:
    """
    Return the `limit` videos most similar to `video_id`, ranked by
    cosine similarity, excluding the video itself.

    Each result: {"video_id": ..., "title": ..., "score": ...}
    Raises KeyError if the video isn't in the corpus.
    """
    model = _get_model()

    row_index = model["id_to_row"].get(video_id)
    if row_index is None:
        raise KeyError(f"Video {video_id!r} not found in corpus")

    scores = model["similarity"][row_index]

    # Rank all videos by similarity, best first; skip the video itself.
    ranked = scores.argsort()[::-1]
    results = []
    for i in ranked:
        if i == row_index:
            continue
        results.append(
            {
                "video_id": model["ids"][i],
                "title": model["titles"][model["ids"][i]],
                "score": round(float(scores[i]), 4),
            }
        )
        if len(results) == limit:
            break

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    model = _get_model()
    sample_id = model["ids"][0]
    print(f"\nVideos similar to: {model['titles'][sample_id]!r}\n")
    for r in get_similar_videos(sample_id, limit=5):
        print(f"  {r['score']:.4f}  {r['title']}")