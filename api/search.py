from database.connection import get_conn


def search_articles(q: str, limit: int = 50, category: str = None, days: int = 7):
    where_clauses = []
    params = []

    # Filtre par date
    where_clauses.append("a.collected_at >= NOW() - INTERVAL '7 days'")

    # Filtre par mot-clé
    where_clauses.append(
        "(lower(a.title) LIKE lower(%s) OR lower(coalesce(a.summary,'')) LIKE lower(%s))"
    )
    params.extend([f"%{q}%", f"%{q}%"])

    # Filtre par catégorie
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
        s.id AS source_id,
        s.name AS source_name,
        s.category
    FROM articles a
    JOIN sources s ON s.id = a.source_id
    WHERE {where}
    ORDER BY a.published_at DESC
    LIMIT %s
    """
    params.append(limit)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()

    return {
        "query": q,
        "total": len(rows),
        "results": [dict(zip(cols, row)) for row in rows],
    }
