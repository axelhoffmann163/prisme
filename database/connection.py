import psycopg2
from psycopg2 import pool
from contextlib import contextmanager
from loguru import logger
from config.settings import settings

_pool = None

def init_pool():
    global _pool
    _pool = pool.ThreadedConnectionPool(
        minconn=2,
        maxconn=settings.DB_POOL_SIZE + settings.DB_MAX_OVERFLOW,
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        connect_timeout=10,
    )
    logger.info(f"Pool PostgreSQL initialisé → {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")

def close_pool():
    global _pool
    if _pool:
        _pool.closeall()
        logger.info("Pool PostgreSQL fermé.")

@contextmanager
def get_conn():
    if _pool is None:
        raise RuntimeError("Pool non initialisé.")
    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)
