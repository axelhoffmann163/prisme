from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from loguru import logger
from database.connection import get_conn


@dataclass
class ArticleRecord:
    source_id:    str
    feed_id:      Optional[int]
    content_hash: str
    guid:         Optional[str]
    url:          str
    title:        str
    summary:      Optional[str]
    full_text:    Optional[str]
    author:       Optional[str]
    image_url:    Optional[str]
    category:     Optional[str]
    tags:         list
    language:     str
    published_at: Optional[datetime]


def upsert_source(source):
    sql = """
    INSERT INTO sources (id, name, category, subcategory, url, interval_min, active, tags)
    VALUES (%(id)s, %(name)s, %(category)s, %(subcategory)s, %(url)s, %(interval)s, %(active)s, %(tags)s)
    ON CONFLICT (id) DO UPDATE SET
        name=EXCLUDED.name, category=EXCLUDED.category,
        subcategory=EXCLUDED.subcategory, url=EXCLUDED.url,
        interval_min=EXCLUDED.interval_min, active=EXCLUDED.active,
        tags=EXCLUDED.tags, updated_at=NOW()
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {
                "id": source["id"], "name": source["name"],
                "category": source["category"], "subcategory": source.get("subcategory"),
                "url": source["url"], "interval": source["interval"],
                "active": source["active"], "tags": source.get("tags", []),
            })


def upsert_feed(source_id, label, url):
    sql = """
    INSERT INTO feeds (source_id, label, url)
    VALUES (%s, %s, %s)
    ON CONFLICT (source_id, label) DO UPDATE SET url=EXCLUDED.url
    RETURNING id
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (source_id, label, url))
            return cur.fetchone()[0]


def update_feed_status(feed_id, status, error=None, articles_found=0, latency_ms=0):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE feeds SET
                    last_fetched_at=NOW(), last_status=%s, last_error=%s,
                    fetch_count=fetch_count+1,
                    error_count=error_count+CASE WHEN %s IS NOT NULL THEN 1 ELSE 0 END
                WHERE id=%s
            """, (status, error, error, feed_id))
            cur.execute("""
                INSERT INTO source_health (source_id, feed_url, status, latency_ms, articles_found, error)
                SELECT s.id, f.url, %s, %s, %s, %s
                FROM feeds f JOIN sources s ON s.id=f.source_id
                WHERE f.id=%s
            """, (status, latency_ms, articles_found, error, feed_id))


def bulk_insert_articles(articles):
    if not articles:
        return 0
    from psycopg2.extras import execute_values
    values = [(
        a.source_id, a.feed_id, a.content_hash, a.guid, a.url,
        a.title, a.summary, a.full_text, a.author, a.image_url,
        a.category, a.tags, a.language, a.published_at,
    ) for a in articles]
    sql = """
    INSERT INTO articles (
        source_id, feed_id, content_hash, guid, url,
        title, summary, full_text, author, image_url,
        category, tags, language, published_at
    ) VALUES %s ON CONFLICT (content_hash) DO NOTHING
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            execute_values(cur, sql, values)
            return cur.rowcount


def get_recent_articles(limit=50, category=None):
    where = "WHERE a.collected_at >= NOW() - INTERVAL '24 hours'"
    params = []
    if category:
        where += " AND s.category = %s"
        params.append(category)
    sql = f"""
    SELECT a.id, a.title, a.url, a.summary, a.published_at, a.collected_at,
           a.author, a.tags, a.nlp_sentiment,
           s.id AS source_id, s.name AS source_name, s.category
    FROM articles a JOIN sources s ON s.id=a.source_id
    {where} ORDER BY a.collected_at DESC LIMIT %s
    """
    params.append(limit)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_stats():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            SELECT
                (SELECT COUNT(*) FROM articles WHERE collected_at >= NOW() - INTERVAL '24 hours'),
                (SELECT COUNT(*) FROM articles),
                (SELECT COUNT(*) FROM sources WHERE active=TRUE),
                (SELECT COUNT(*) FROM feeds WHERE last_status NOT IN (200,301,302) AND last_fetched_at IS NOT NULL)
            """)
            row = cur.fetchone()
            return {
                "articles_today": row[0],
                "articles_total": row[1],
                "sources_active": row[2],
                "feeds_in_error": row[3],
            }
