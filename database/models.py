CREATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id              TEXT        PRIMARY KEY,
    name            TEXT        NOT NULL,
    category        TEXT        NOT NULL,
    subcategory     TEXT,
    url             TEXT        NOT NULL,
    interval_min    INTEGER     NOT NULL DEFAULT 30,
    active          BOOLEAN     NOT NULL DEFAULT TRUE,
    tags            TEXT[]      DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS feeds (
    id              SERIAL      PRIMARY KEY,
    source_id       TEXT        NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    label           TEXT        NOT NULL DEFAULT 'une',
    url             TEXT        NOT NULL,
    active          BOOLEAN     NOT NULL DEFAULT TRUE,
    last_fetched_at TIMESTAMPTZ,
    last_status     SMALLINT,
    last_error      TEXT,
    fetch_count     INTEGER     NOT NULL DEFAULT 0,
    error_count     INTEGER     NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source_id, label)
);

CREATE TABLE IF NOT EXISTS articles (
    id              BIGSERIAL   PRIMARY KEY,
    source_id       TEXT        NOT NULL REFERENCES sources(id),
    feed_id         INTEGER     REFERENCES feeds(id),
    content_hash    TEXT        NOT NULL UNIQUE,
    guid            TEXT,
    url             TEXT        NOT NULL,
    title           TEXT        NOT NULL,
    summary         TEXT,
    full_text       TEXT,
    author          TEXT,
    image_url       TEXT,
    category        TEXT,
    tags            TEXT[]      DEFAULT '{}',
    language        TEXT        DEFAULT 'fr',
    published_at    TIMESTAMPTZ,
    collected_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    nlp_summary     TEXT,
    nlp_sentiment   TEXT,
    nlp_entities    JSONB       DEFAULT '[]',
    nlp_topics      TEXT[]      DEFAULT '{}',
    nlp_processed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS source_health (
    id          BIGSERIAL   PRIMARY KEY,
    source_id   TEXT        NOT NULL REFERENCES sources(id),
    feed_url    TEXT        NOT NULL,
    checked_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status      SMALLINT,
    latency_ms  INTEGER,
    articles_found INTEGER  DEFAULT 0,
    error       TEXT
);

CREATE INDEX IF NOT EXISTS idx_articles_source_id ON articles(source_id);
CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_collected_at ON articles(collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);
CREATE INDEX IF NOT EXISTS idx_articles_content_hash ON articles(content_hash);
CREATE INDEX IF NOT EXISTS idx_articles_title_fts ON articles USING gin(to_tsvector('french', coalesce(title, '')));

CREATE OR REPLACE VIEW articles_recent AS
SELECT a.*, s.name AS source_name, s.category AS source_category
FROM articles a
JOIN sources s ON s.id = a.source_id
WHERE a.collected_at >= NOW() - INTERVAL '24 hours'
ORDER BY a.collected_at DESC;

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sources_updated_at ON sources;
CREATE TRIGGER trg_sources_updated_at
    BEFORE UPDATE ON sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
"""
