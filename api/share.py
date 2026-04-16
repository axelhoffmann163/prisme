import uuid
from database.connection import get_conn


def generate_share_token(watchlist_id: int) -> str:
    """Génère ou récupère le token de partage d'une veille."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Vérifie si un token existe déjà
            cur.execute("SELECT share_token FROM watchlists WHERE id = %s", (watchlist_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Veille {watchlist_id} introuvable")
            if row[0]:
                return row[0]
            # Crée un nouveau token
            token = str(uuid.uuid4()).replace("-", "")[:16]
            cur.execute("UPDATE watchlists SET share_token = %s WHERE id = %s", (token, watchlist_id))
    return token


def revoke_share_token(watchlist_id: int) -> bool:
    """Révoque le token de partage."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE watchlists SET share_token = NULL WHERE id = %s", (watchlist_id,))
    return True


def get_watchlist_by_token(token: str) -> dict:
    """Récupère les données publiques d'une veille via son token."""
    from api.watchlist import get_watchlist_stats, get_watchlist_articles, build_entities, top_words
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, query, created_at, share_token FROM watchlists WHERE share_token = %s",
                (token,)
            )
            row = cur.fetchone()
            if not row:
                return None
            wl_id, wl_name, wl_query, wl_created, _ = row

    stats = get_watchlist_stats(wl_id, hours=24)
    arts = get_watchlist_articles(wl_id, limit=50)

    return {
        "id": wl_id,
        "name": wl_name,
        "query": wl_query,
        "stats": stats,
        "articles": arts.get("articles", []),
    }
