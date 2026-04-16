from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from database.connection import init_pool, close_pool
from database.repository import get_recent_articles, get_stats
from api.search import search_articles
from api.sources import (
    get_sources_status, add_source, update_source,
    toggle_source, delete_source, test_feed_url, get_trends
)
from api.watchlist import (
    get_watchlists, create_watchlist, delete_watchlist, get_watchlist_articles,
    get_watchlist_stats,
    get_folders, create_folder, delete_folder, update_folder,
    add_watchlist_to_folder, remove_watchlist_from_folder, get_folder_watchlists,
)

app = FastAPI(title="PressWatch API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_pool()

@app.on_event("shutdown")
def shutdown():
    close_pool()

@app.get("/")
def root():
    return {"status": "ok", "app": "PressWatch API v2.0"}

@app.get("/stats")
def stats():
    return get_stats()

@app.get("/articles")
def articles(
    limit: int = Query(50, ge=1, le=200),
    category: Optional[str] = None,
    topic: Optional[str] = None,
):
    return get_recent_articles(limit=limit, category=category, topic=topic)

@app.get("/search")
def search(
    q: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=200),
    category: Optional[str] = None,
    topic: Optional[str] = None,
    days: int = Query(7, ge=1, le=60),
    source_id: Optional[str] = None,
):
    return search_articles(q=q, limit=limit, category=category, topic=topic, days=days, source_id=source_id)

@app.get("/trends")
def trends(hours: int = Query(6, ge=1, le=48), limit: int = Query(10, ge=1, le=50)):
    return get_trends(hours=hours, limit=limit)

# ── Sources ───────────────────────────────────────────────────
@app.get("/sources")
def sources():
    return get_sources_status()

@app.post("/sources")
def create_source(name: str, url: str, category: str, subcategory: Optional[str] = None, interval_min: int = 30):
    return add_source(name=name, url=url, category=category, subcategory=subcategory, interval_min=interval_min)

@app.put("/sources/{source_id}")
def edit_source(source_id: str, name: Optional[str] = None, url: Optional[str] = None, category: Optional[str] = None, interval_min: Optional[int] = None):
    return update_source(source_id=source_id, name=name, url=url, category=category, interval_min=interval_min)

@app.patch("/sources/{source_id}/toggle")
def toggle(source_id: str, active: bool):
    return toggle_source(source_id=source_id, active=active)

@app.delete("/sources/{source_id}")
def remove_source(source_id: str):
    return delete_source(source_id=source_id)

@app.get("/sources/test")
def test_url(url: str):
    return test_feed_url(url=url)

# ── Dossiers ──────────────────────────────────────────────────
@app.get("/folders")
def folders():
    return get_folders()

@app.post("/folders")
def create_fold(name: str, color: str = "#2563EB"):
    return create_folder(name=name, color=color)

@app.put("/folders/{folder_id}")
def update_fold(folder_id: int, name: Optional[str] = None, color: Optional[str] = None):
    return update_folder(folder_id=folder_id, name=name, color=color)

@app.delete("/folders/{folder_id}")
def delete_fold(folder_id: int):
    return delete_folder(folder_id=folder_id)

@app.get("/folders/{folder_id}/watchlists")
def folder_watchlists(folder_id: int):
    return get_folder_watchlists(folder_id=folder_id)

@app.post("/folders/{folder_id}/watchlists/{watchlist_id}")
def add_to_folder(folder_id: int, watchlist_id: int):
    return add_watchlist_to_folder(folder_id=folder_id, watchlist_id=watchlist_id)

@app.delete("/folders/{folder_id}/watchlists/{watchlist_id}")
def remove_from_folder(folder_id: int, watchlist_id: int):
    return remove_watchlist_from_folder(folder_id=folder_id, watchlist_id=watchlist_id)

# ── Watchlists ────────────────────────────────────────────────
@app.get("/watchlists")
def watchlists():
    return get_watchlists()

@app.post("/watchlists")
def add_watchlist(name: str, query: str, category: Optional[str] = None):
    return create_watchlist(name=name, query=query, category=category)

@app.delete("/watchlists/{watchlist_id}")
def remove_watchlist(watchlist_id: int):
    return delete_watchlist(watchlist_id=watchlist_id)

@app.get("/watchlists/{watchlist_id}/articles")
def watchlist_articles(watchlist_id: int, limit: int = Query(50, ge=1, le=200)):
    return get_watchlist_articles(watchlist_id=watchlist_id, limit=limit)

@app.get("/watchlists/{watchlist_id}/stats")
def watchlist_stats(watchlist_id: int, hours: int = Query(24, ge=1, le=336)):
    return get_watchlist_stats(watchlist_id=watchlist_id, hours=hours)
