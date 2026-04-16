import uuid
from datetime import datetime, timezone, timedelta
from database.connection import get_conn


def generate_share_token(watchlist_id: int, expire_days: int = 30) -> dict:
    expires_at = None if expire_days == 0 else (datetime.now(timezone.utc) + timedelta(days=expire_days))
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT share_token FROM watchlists WHERE id = %s", (watchlist_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Veille {watchlist_id} introuvable")
            # Génère toujours un nouveau token (renouvellement)
            token = str(uuid.uuid4()).replace("-", "")[:16]
            cur.execute(
                "UPDATE watchlists SET share_token = %s, share_expires_at = %s WHERE id = %s",
                (token, expires_at, watchlist_id)
            )
    return {"token": token, "expires_at": expires_at.isoformat() if expires_at else None}


def revoke_share_token(watchlist_id: int) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE watchlists SET share_token = NULL, share_expires_at = NULL WHERE id = %s", (watchlist_id,))
    return True


def get_watchlist_by_token(token: str):
    from api.watchlist import get_watchlist_stats, get_watchlist_articles
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, query, share_expires_at FROM watchlists WHERE share_token = %s",
                (token,)
            )
            row = cur.fetchone()
            if not row:
                return None
            wl_id, wl_name, wl_query, expires_at = row
            # Vérifie l'expiration
            if expires_at:
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) > expires_at:
                    return None

    stats = get_watchlist_stats(wl_id, hours=24)
    arts = get_watchlist_articles(wl_id, limit=50)

    return {
        "id": wl_id,
        "name": wl_name,
        "query": wl_query,
        "stats": stats,
        "articles": arts.get("articles", []),
    }
