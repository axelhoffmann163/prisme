import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from database.connection import init_pool, close_pool, get_conn
from database.models import CREATE_SCHEMA
from database.repository import upsert_source, upsert_feed
from config.sources import SOURCES


def create_schema():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_SCHEMA)
            logger.success("Schéma créé / mis à jour.")


def import_sources():
    logger.info(f"Import de {len(SOURCES)} sources…")
    total_feeds = 0
    for source in SOURCES:
        upsert_source(source)
        upsert_feed(source["id"], "une", source["url"])
        total_feeds += 1
        for label, url in (source.get("extra_feeds") or {}).items():
            upsert_feed(source["id"], label, url)
            total_feeds += 1
    logger.success(f"{len(SOURCES)} sources importées → {total_feeds} flux configurés.")


def print_summary():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            SELECT s.category, COUNT(DISTINCT s.id), COUNT(f.id)
            FROM sources s LEFT JOIN feeds f ON f.source_id=s.id
            GROUP BY s.category ORDER BY s.category
            """)
            rows = cur.fetchall()

    print("\n┌─────────────────────┬───────────┬──────────┐")
    print("│ Catégorie           │  Sources  │   Flux   │")
    print("├─────────────────────┼───────────┼──────────┤")
    for cat, nb_src, nb_feed in rows:
        print(f"│ {cat:<19} │ {nb_src:>9} │ {nb_feed:>8} │")
    total_src = sum(r[1] for r in rows)
    total_feed = sum(r[2] for r in rows)
    print("├─────────────────────┼───────────┼──────────┤")
    print(f"│ {'TOTAL':<19} │ {total_src:>9} │ {total_feed:>8} │")
    print("└─────────────────────┴───────────┴──────────┘\n")


def main():
    logger.info("Connexion à PostgreSQL…")
    init_pool()
    try:
        create_schema()
        import_sources()
        print_summary()
        logger.success("✅ Base de données prête.")
    finally:
        close_pool()


if __name__ == "__main__":
    main()
