#!/usr/bin/env python
import sys
import signal
import argparse
import time
from pathlib import Path

from loguru import logger
from rich.console import Console

from config.settings import settings
from database.connection import init_pool, close_pool
from collector.scheduler import PressWatchScheduler

console = Console()

def setup_logging():
    Path("logs").mkdir(exist_ok=True)
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        colorize=True,
    )
    logger.add(
        settings.LOG_FILE,
        level="DEBUG",
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        encoding="utf-8",
    )

_scheduler = None

def handle_shutdown(signum, frame):
    logger.info("Arrêt en cours...")
    if _scheduler:
        _scheduler.stop()
    close_pool()
    sys.exit(0)

signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)

def main():
    global _scheduler

    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=int, metavar="MIN")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        settings.DRY_RUN = True

    setup_logging()

    console.print()
    console.print("[bold cyan]╔══════════════════════════════════════╗[/bold cyan]")
    console.print("[bold cyan]║      🗞  PressWatch Collector v1.0    ║[/bold cyan]")
    console.print("[bold cyan]╚══════════════════════════════════════╝[/bold cyan]")
    console.print()

    if settings.DRY_RUN:
        logger.warning("Mode DRY RUN activé.")

    logger.info(f"Connexion PostgreSQL → {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    init_pool()
    logger.success("Connexion établie.")

    _scheduler = PressWatchScheduler()
    _scheduler.start()

    if args.once:
        logger.info("Mode --once : collecte complète en cours…")
        _scheduler.run_now(interval_min=args.interval)
        logger.success("Collecte terminée.")
        _scheduler.stop()
        close_pool()
        return

    logger.info("Collecte initiale au démarrage…")
    _scheduler.run_now(interval_min=args.interval)
    logger.success("Scheduler actif. Ctrl+C pour arrêter.")

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        handle_shutdown(None, None)

if __name__ == "__main__":
    main()
