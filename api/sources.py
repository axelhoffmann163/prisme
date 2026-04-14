from database.connection import get_conn


def get_sources_status():
    """
    Retourne la liste des sources avec leur statut de santé.
    """
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
        ROUND(
            100.0 * SUM(f.error_count) / NULLIF(SUM(f.fetch_count), 0),
            1
        ) AS error_rate_pct,
        (
            SELECT COUNT(*)
            FROM articles a
            WHERE a.source_id = s.id
            AND a.collected_at >= NOW() - INTERVAL '24 hours'
        ) AS articles_today
    FROM sources s
    LEFT JOIN feeds f ON f.source_id = s.id
    WHERE s.active = TRUE
    GROUP BY s.id, s.name, s.category, s.subcategory, s.url, s.interval_min, s.active, s.tags
    ORDER BY s.category, s.name
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()

    sources = [dict(zip(cols, row)) for row in rows]

    return {
        "total": len(sources),
        "sources": sources,
    }


def get_trends(hours: int = 6, limit: int = 10):
    """
    Retourne les mots les plus fréquents dans les titres récents.
    """
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
            'leur','leurs','dont','où','car','ni','ne','pas','tout','bien'
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
