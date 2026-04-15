import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich import box

from config.sources import get_all_feeds, SOURCES
from collector.feed_fetcher import fetch_feed
from collector.feed_parser import parse_feed
from collector.deduplicator import deduplicator
from database.repository import upsert_feed, update_feed_status, bulk_insert_articles
from database.connection import get_conn
from config.settings import settings

console = Console()

RETENTION_DAYS = 60


def purge_old_articles():
    """Supprime les articles de plus de 60 jours."""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM articles
                    WHERE collected_at < NOW() - INTERVAL '%s days'
                """, (RETENTION_DAYS,))
                deleted = cur.rowcount
        logger.info(f"Purge nocturne — {deleted:,} articles supprimés (>{RETENTION_DAYS}j)")
    except Exception as e:
        logger.error(f"Erreur purge articles : {e}")


def collect_feed(feed):
    url = feed["url"]
    source_id = feed["source_id"]
    label = feed["label"]
    category = feed["category"]
    tags = feed.get("tags", [])

    summary = {"source_id": source_id, "label": label, "url": url,
               "status": 0, "fetched": 0, "inserted": 0, "deduplicated": 0,
               "latency_ms": 0, "error": None}

    try:
        feed_id = upsert_feed(source_id, label, url)
        result = fetch_feed(url)
        summary["status"] = result.status_code
        summary["latency_ms"] = result.latency_ms

        if result.not_modified:
            update_feed_status(feed_id, 304, articles_found=0, latency_ms=result.latency_ms)
            return summary

        if not result.ok:
            summary["error"] = result.error
            update_feed_status(feed_id, result.status_code, error=result.error, latency_ms=result.latency_ms)
            return summary

        articles = parse_feed(result, source_id, feed_id, category, tags)
        summary["fetched"] = len(articles)

        if not articles:
            update_feed_status(feed_id, result.status_code, articles_found=0, latency_ms=result.latency_ms)
            return summary

        new_articles = deduplicator.filter_new(articles)
        summary["deduplicated"] = len(articles) - len(new_articles)

        if not new_articles:
            update_feed_status(feed_id, result.status_code, articles_found=0, latency_ms=result.latency_ms)
            return summary

        if not settings.DRY_RUN:
            inserted = bulk_insert_articles(new_articles)
        else:
            inserted = len(new_articles)

        summary["inserted"] = inserted
        deduplicator.mark_batch([a.content_hash for a in new_articles])
        update_feed_status(feed_id, result.status_code, articles_found=inserted, latency_ms=result.latency_ms)

        if inserted > 0:
            logger.info(f"✓ {source_id}/{label} → {inserted} nouveaux articles ({summary['deduplicated']} dédupliqués, {result.latency_ms}ms)")

    except Exception as e:
        summary["error"] = str(e)[:200]
        logger.error(f"✗ Erreur collecte {source_id}/{label} : {e}")

    return summary


def collect_group(interval_min, feeds):
    start = time.monotonic()
    label = f"[{interval_min}min]"
    logger.info(f"{label} Démarrage collecte → {len(feeds)} flux")

    results = {"ok": 0, "new": 0, "errors": 0, "skipped": 0}

    with ThreadPoolExecutor(max_workers=min(settings.FETCH_WORKERS, len(feeds))) as pool:
        futures = {pool.submit(collect_feed, feed): feed for feed in feeds}
        for future in as_completed(futures):
            try:
                summary = future.result(timeout=settings.FETCH_TIMEOUT + 5)
                if summary["error"]:
                    results["errors"] += 1
                elif summary["status"] == 304:
                    results["skipped"] += 1
                else:
                    results["ok"] += 1
                results["new"] += summary.get("inserted", 0)
            except Exception:
                results["errors"] += 1

    elapsed = round(time.monotonic() - start, 1)
    logger.info(
        f"{label} Terminé en {elapsed}s → "
        f"{results['ok']} OK | {results['new']} nouveaux | "
        f"{results['skipped']} inchangés | {results['errors']} erreurs"
    )


class PressWatchScheduler:
    def __init__(self):
        self._scheduler = BackgroundScheduler(
            job_defaults={"coalesce": True, "max_instances": 1},
            timezone="Europe/Paris",
        )
        self._feeds_by_interval = {}

    def _build_feed_groups(self):
        self._feeds_by_interval.clear()
        source_map = {s["id"]: s for s in SOURCES}
        for feed in get_all_feeds():
            interval = feed["interval"]
            source = source_map.get(feed["source_id"], {})
            feed["tags"] = source.get("tags", [])
            if interval not in self._feeds_by_interval:
                self._feeds_by_interval[interval] = []
            self._feeds_by_interval[interval].append(feed)

    def start(self):
        self._build_feed_groups()

        # Jobs de collecte RSS
        for interval_min, feeds in sorted(self._feeds_by_interval.items()):
            self._scheduler.add_job(
                func=collect_group,
                trigger=IntervalTrigger(minutes=interval_min),
                args=[interval_min, feeds],
                id=f"collect_{interval_min}min",
                name=f"Collecte {interval_min}min ({len(feeds)} flux)",
                replace_existing=True,
            )
            logger.info(f"Job planifié toutes les {interval_min}min → {len(feeds)} flux")

        # Job de purge nocturne — chaque nuit à 2h00
        self._scheduler.add_job(
            func=purge_old_articles,
            trigger=CronTrigger(hour=2, minute=0, timezone="Europe/Paris"),
            id="purge_old_articles",
            name=f"Purge articles >{RETENTION_DAYS}j",
            replace_existing=True,
        )
        logger.info(f"Job purge planifié chaque nuit à 2h00 (rétention {RETENTION_DAYS}j)")

        self._scheduler.start()
        logger.success("PressWatch Scheduler démarré.")
        self._print_summary()

    def _print_summary(self):
        table = Table(title="📡 PressWatch — Jobs de collecte", box=box.ROUNDED,
                      show_header=True, header_style="bold cyan")
        table.add_column("Intervalle", style="cyan", justify="right")
        table.add_column("Flux", style="white", justify="right")
        table.add_column("Sources", style="green")
        for interval, feeds in sorted(self._feeds_by_interval.items()):
            sources = ", ".join(sorted({f["source_id"] for f in feeds})[:5])
            if len({f["source_id"] for f in feeds}) > 5:
                sources += f" + {len({f['source_id'] for f in feeds}) - 5} autres"
            table.add_row(f"{interval} min", str(len(feeds)), sources)
        table.add_row("2h00 (cron)", "—", f"Purge articles >{RETENTION_DAYS}j")
        console.print(table)

    def run_now(self, interval_min=None):
        if interval_min:
            feeds = self._feeds_by_interval.get(interval_min, [])
            if feeds:
                collect_group(interval_min, feeds)
        else:
            for interval, feeds in sorted(self._feeds_by_interval.items()):
                collect_group(interval, feeds)

    def stop(self):
        self._scheduler.shutdown(wait=True)
        logger.info("PressWatch Scheduler arrêté.")
        deduplicator.log_stats()
