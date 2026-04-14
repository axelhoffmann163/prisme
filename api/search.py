from database.connection import get_conn


def search_articles(q: str, limit: int = 50, category: str = None, days: int = 7):
    """
    Recherche full-text dans les articles via PostgreSQL.
    Cherche dans le titre et le résumé.
    """
    where_clauses = [
        "a.collected_at >= NOW() - (%s || ' days')::INTERVAL",
        "(to_tsvector('french', coalesce(a.title, '')) @@ plainto_tsquery('french', %s) OR to_tsvector('french', coalesce(a.summary, '')) @@ plainto_tsquery('french', %s) OR lower(a.title) LIKE lower(%s))"
    ]
    params = [str(days), q, q, f"%{q}%", q, limit]

    if category:
        where_clauses.append("s.category = %s")
        params.append(category)

    where = " AND ".join(where_clauses)

    sql = f"""
    SELECT
        a.id,
        a.title,
        a.url,
        a.summary,
        a.published_at,
        a.collected_at,
        a.author,
        a.tags,
        a.nlp_sentiment,
        s.id AS source_id,
        s.name AS source_name,
        s.category,
        ts_rank(
            to_tsvector('french', coalesce(a.title, '') || ' ' || coalesce(a.summary, '')),
            plainto_tsquery('french', %s)
        ) AS relevance
    FROM articles a
    JOIN sources s ON s.id = a.source_id
    WHERE {where}
    ORDER BY relevance DESC, a.published_at DESC
    LIMIT %s
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()

    results = [dict(zip(cols, row)) for row in rows]

    return {
        "query": q,
        "total": len(results),
        "days": days,
        "results": results,
    }
