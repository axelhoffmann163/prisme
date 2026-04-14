from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from database.connection import init_pool, close_pool
from database.repository import (
    get_recent_articles,
    get_stats,
)
from api.search import search_articles
from api.sources import get_sources_status

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
    source_id: Optional[str] = None,
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

@app.get("/sources")
def sources():
    return get_sources_status()
