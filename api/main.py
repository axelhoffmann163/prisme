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
from api.watchlist import get_watchlists, create_watchlist, delete_watchlist, get_watchlist_articles

app = FastAPI(title="PressWatch API", version="1.0")

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
    return {"status": "ok", "app": "PressWatch API v1.0"}

@app.get("/stats")
def stats():
    return get_stats()

@app.get("/articles")
def articles(
    limit: int = Query(50, ge=1, le=200),
    category: Optional[str] = None,
):
    return get_recent_articles(limit=limit, category=category)

@app.get("/search")
def search(
    q: str = Query(..., min_length=2),
    limit: int = Query(50, ge=1, le=200),
    category: Optional[str] = None,
    days: int = Query(7, ge=1, le=90),
):
    return search_articles(q=q, limit=limit, category=category, days=days)

@app.get("/trends")
def trends(hours: int = Query(6, ge=1, le=48), limit: int = Query(10, ge=1, le=50)):
    return get_trends(hours=hours, limit=limit)

# Sources
@app.get("/sources")
def sources():
    return get_sources_status()

@app.post("/sources")
def create_source(
    name: str,
    url: str,
    category: str,
    subcategory: Optional[str] = None,
    interval_min: int = 30,
):
    return add_source(name=name, url=url, category=category,
                      subcategory=subcategory, interval_min=interval_min)

@app.put("/sources/{source_id}")
def edit_source(
    source_id: str,
    name: Optional[str] = None,
    url: Optional[str] = None,
    category: Optional[str] = None,
    interval_min: Optional[int] = None,
):
    return update_source(source_id=source_id, name=name, url=url,
                         category=category, interval_min=interval_min)

@app.patch("/sources/{source_id}/toggle")
def toggle(source_id: str, active: bool):
    return toggle_source(source_id=source_id, active=active)

@app.delete("/sources/{source_id}")
def remove_source(source_id: str):
    return delete_source(source_id=source_id)

@app.get("/sources/test")
def test_url(url: str):
    return test_feed_url(url=url)

# Watchlists
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
