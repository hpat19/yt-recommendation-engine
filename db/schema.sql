-- db/schema.sql

CREATE TABLE IF NOT EXISTS channels (
    channel_id    TEXT PRIMARY KEY,
    channel_title TEXT
);

CREATE TABLE IF NOT EXISTS videos (
    video_id         TEXT PRIMARY KEY,
    channel_id       TEXT REFERENCES channels(channel_id),
    title            TEXT,
    published_at     TIMESTAMPTZ,
    category_id      TEXT,
    tags             TEXT[],
    view_count       BIGINT,          -- nullable: NULL = unknown, not zero
    like_count       BIGINT,
    comment_count    BIGINT,
    duration_seconds INT NOT NULL DEFAULT 0,   -- your 0 sentinel
    created_at       TIMESTAMPTZ DEFAULT now(),
    updated_at       TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_videos_channel_id ON videos (channel_id);
CREATE INDEX IF NOT EXISTS idx_videos_tags ON videos USING GIN (tags);