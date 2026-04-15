from database.connection import get_conn
from api.search import search_articles


def get_watchlists():
    sql = """
    SELECT
        w.id,
        w.name,
        w.query,
        w.category,
        w.created_at,
        w.last_viewed,
        (
            SELECT COUNT(*)
            FROM articles a
            WHERE lower(a.title) LIKE lower('%' || w.query || '%')
            AND (w.last_viewed IS NULL OR a.collected_at > w.last_viewed)
        ) AS new_articles
    FROM watchlists w
    ORDER BY w.created_at DESC
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
    return [dict(zip(cols, row)) for row in rows]


def create_watchlist(name: str, query: str, category: str = None):
    sql = """
    INSERT INTO watchlists (name, query, category)
    VALUES (%s, %s, %s)
    RETURNING id, name, query, category, created_at
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (name, query, category))
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
    return dict(zip(cols, row))


def delete_watchlist(watchlist_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM watchlists WHERE id = %s", (watchlist_id,))
    return {"deleted": True, "id": watchlist_id}


def get_watchlist_articles(watchlist_id: int, limit: int = 50):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, query, category FROM watchlists WHERE id = %s",
                (watchlist_id,)
            )
            row = cur.fetchone()
            if not row:
                return {"error": "Veille introuvable"}
            watchlist = dict(zip(["id", "name", "query", "category"], row))

            cur.execute(
                "UPDATE watchlists SET last_viewed = NOW() WHERE id = %s",
                (watchlist_id,)
            )

    results = search_articles(
        q=watchlist["query"],
        limit=limit,
        category=watchlist["category"],
        days=30,
    )

    return {
        "watchlist": watchlist,
        "articles": results["results"],
        "total": results["total"],
    }
