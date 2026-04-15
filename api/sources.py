from database.connection import get_conn


def get_sources_status():
    sql = """
    SELECT
        s.id,
        s.name,
        s.category,
        s.subcategory,
        s.url,
        s.interval_min,
        s.active,
        s.tags,
        COUNT(DISTINCT f.id) AS nb_feeds,
        SUM(f.fetch_count) AS total_fetches,
        SUM(f.error_count) AS total_errors,
        MAX(f.last_fetched_at) AS last_fetched_at,
        MAX(f.last_status) AS last_status,
        MAX(f.last_error) AS last_error,
        ROUND(
            100.0 * SUM(f.error_count) / NULLIF(SUM(f.fetch_count), 0), 1
        ) AS error_rate_pct,
        (
            SELECT COUNT(*)
            FROM articles a
            WHERE a.source_id = s.id
            AND a.collected_at >= NOW() - INTERVAL '24 hours'
        ) AS articles_today
    FROM sources s
    LEFT JOIN feeds f ON f.source_id = s.id
    GROUP BY s.id, s.name, s.category, s.subcategory, s.url, s.interval_min, s.active, s.tags
    ORDER BY s.category, s.name
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
    sources = [dict(zip(cols, row)) for row in rows]
    return {"total": len(sources), "sources": sources}


def add_source(name: str, url: str, category: str, subcategory: str = None, interval_min: int = 30):
    source_id = name.lower().replace(" ", "_").replace("'", "").replace("-", "_")
    source_id = ''.join(c for c in source_id if c.isalnum() or c == '_')

    sql_source = """
    INSERT INTO sources (id, name, category, subcategory, url, interval_min, active, tags)
    VALUES (%s, %s, %s, %s, %s, %s, TRUE, '{}')
    ON CONFLICT (id) DO UPDATE SET
        name=EXCLUDED.name, category=EXCLUDED.category,
        url=EXCLUDED.url, interval_min=EXCLUDED.interval_min,
        active=TRUE, updated_at=NOW()
    RETURNING id, name, category, url, active
    """
    sql_feed = """
    INSERT INTO feeds (source_id, label, url)
    VALUES (%s, 'une', %s)
    ON CONFLICT (source_id, label) DO UPDATE SET url=EXCLUDED.url
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_source, (source_id, name, category, subcategory, url, interval_min))
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
            cur.execute(sql_feed, (source_id, url))
    return dict(zip(cols, row))


def update_source(source_id: str, name: str = None, url: str = None,
                  category: str = None, interval_min: int = None):
    fields = []
    params = []
    if name:
        fields.append("name=%s"); params.append(name)
    if url:
        fields.append("url=%s"); params.append(url)
    if category:
        fields.append("category=%s"); params.append(category)
    if interval_min:
        fields.append("interval_min=%s"); params.append(interval_min)
    if not fields:
        return {"error": "Aucun champ à modifier"}
    fields.append("updated_at=NOW()")
    params.append(source_id)
    sql = f"UPDATE sources SET {', '.join(fields)} WHERE id=%s RETURNING id, name, category, url, active"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
    if not row:
        return {"error": "Source introuvable"}
    if url:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE feeds SET url=%s WHERE source_id=%s AND label='une'",
                    (url, source_id)
                )
    return dict(zip(cols, row))


def toggle_source(source_id: str, active: bool):
    sql = "UPDATE sources SET active=%s, updated_at=NOW() WHERE id=%s RETURNING id, name, active"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (active, source_id))
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
    if not row:
        return {"error": "Source introuvable"}
    return dict(zip(cols, row))


def delete_source(source_id: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sources WHERE id=%s", (source_id,))
    return {"deleted": True, "id": source_id}


def test_feed_url(url: str):
    import requests
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "PressWatch/1.0"})
        if resp.status_code == 200:
            import feedparser
            parsed = feedparser.parse(resp.content)
            count = len(parsed.entries)
            return {
                "ok": True,
                "status": resp.status_code,
                "articles_found": count,
                "message": f"Flux valide — {count} articles trouvés"
            }
        return {"ok": False, "status": resp.status_code, "message": f"Erreur HTTP {resp.status_code}"}
    except Exception as e:
        return {"ok": False, "status": 0, "message": str(e)[:100]}


def get_trends(hours: int = 6, limit: int = 10):
    sql = """
    WITH words AS (
        SELECT regexp_split_to_table(
            lower(regexp_replace(title, '[^a-z ]', ' ', 'g')),
            '\\s+'
        ) AS word
        FROM articles
        WHERE collected_at >= NOW() - (%s || ' hours')::INTERVAL
    ),
    stopwords AS (
        SELECT unnest(ARRAY[
            'le','la','les','un','une','des','de','du','et','en','au','aux',
            'a','est','sont','par','sur','avec','dans','pour','qui','que',
            'se','sa','son','ses','ce','cette','ces','il','elle','ils','elles',
            'plus','mais','ou','si','car','l','d','j','n','s','m','c','y',
            'leur','leurs','dont','car','ni','ne','pas','tout','bien'
        ]) AS word
    )
    SELECT word, COUNT(*) AS freq
    FROM words
    WHERE length(word) > 4
      AND word NOT IN (SELECT word FROM stopwords)
    GROUP BY word
    ORDER BY freq DESC
    LIMIT %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (str(hours), limit))
            rows = cur.fetchall()
    return [{"word": r[0], "count": r[1]} for r in rows]
