from fastapi import FastAPI, Query, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import Optional
import io

from database.connection import init_pool, close_pool
from database.repository import get_recent_articles, get_stats
from api.search import search_articles
from api.sources import (
    get_sources_status, add_source, update_source,
    toggle_source, delete_source, test_feed_url, get_trends
)
from api.watchlist import (
    get_watchlists, create_watchlist, delete_watchlist,
    get_watchlist_articles, get_watchlist_stats,
    get_folders, create_folder, delete_folder, update_folder,
    add_watchlist_to_folder, remove_watchlist_from_folder, get_folder_watchlists,
)
from api.share import generate_share_token, revoke_share_token, get_watchlist_by_token
from api.pdf_report import generate_watchlist_pdf

app = FastAPI(title="PressWatch API", version="2.1")

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
    return {"status": "ok", "app": "PressWatch API v2.1"}

@app.get("/stats")
def stats():
    return get_stats()

@app.get("/articles")
def articles(limit: int = Query(50, ge=1, le=200), category: Optional[str] = None, topic: Optional[str] = None):
    return get_recent_articles(limit=limit, category=category, topic=topic)

@app.get("/search")
def search(q: str = Query(..., min_length=1), limit: int = Query(50, ge=1, le=200),
           category: Optional[str] = None, topic: Optional[str] = None,
           days: int = Query(7, ge=1, le=60), source_id: Optional[str] = None):
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
def edit_source(source_id: str, name: Optional[str] = None, url: Optional[str] = None,
                category: Optional[str] = None, interval_min: Optional[int] = None):
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

@app.patch("/watchlists/{watchlist_id}/rename")
def rename_watchlist(watchlist_id: int, name: str):
    from database.connection import get_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE watchlists SET name = %s WHERE id = %s", (name, watchlist_id))
    return {"id": watchlist_id, "name": name}

# ── PDF ───────────────────────────────────────────────────────
@app.get("/watchlists/{watchlist_id}/pdf")
def watchlist_pdf(watchlist_id: int, hours: int = Query(24, ge=1, le=336)):
    try:
        pdf_bytes = generate_watchlist_pdf(watchlist_id=watchlist_id, hours=hours)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=prisme-veille-{watchlist_id}.pdf"}
        )
    except ImportError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/watchlists/{watchlist_id}/googlenews")
def get_googlenews(watchlist_id: int):
    from database.connection import get_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            source_id = f"googlenews_{watchlist_id}"
            cur.execute("SELECT active FROM sources WHERE id = %s", (source_id,))
            row = cur.fetchone()
    return {"active": bool(row and row[0])}

@app.post("/watchlists/{watchlist_id}/googlenews")
def enable_googlenews(watchlist_id: int):
    from database.connection import get_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name, query FROM watchlists WHERE id = %s", (watchlist_id,))
            row = cur.fetchone()
            if not row:
                return {"error": "Veille introuvable"}
            wl_name, wl_query = row
            # Encode la requête pour Google News
            import urllib.parse
            q = urllib.parse.quote(wl_query.split()[0])
            rss_url = f"https://news.google.com/rss/search?q={q}&hl=fr&gl=FR&ceid=FR:fr"
            source_id = f"googlenews_{watchlist_id}"
            cur.execute("""
                INSERT INTO sources (id, name, category, subcategory, url, interval_min, active, tags)
                VALUES (%s, %s, 'Natif', 'Google News', %s, 30, true, '{google-news}')
                ON CONFLICT (id) DO UPDATE SET active = true, url = EXCLUDED.url
            """, (source_id, f"Google News · {wl_name}", rss_url))
    return {"ok": True, "source_id": source_id, "url": rss_url}

@app.delete("/watchlists/{watchlist_id}/googlenews")
def disable_googlenews(watchlist_id: int):
    from database.connection import get_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE sources SET active = false WHERE id = %s", (f"googlenews_{watchlist_id}",))
    return {"ok": True}

@app.get("/trends/stats")
def trends_stats():
    from database.connection import get_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM articles")
            total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM articles WHERE collected_at >= NOW() - INTERVAL '24 hours'")
            today = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM sources WHERE active = true")
            active_sources = cur.fetchone()[0]
            # Moy./jour = articles des 30 derniers jours ÷ nombre de jours réellement actifs
            cur.execute("""
                SELECT COUNT(*) as cnt,
                       COUNT(DISTINCT DATE(collected_at AT TIME ZONE 'Europe/Paris')) as active_days
                FROM articles
                WHERE collected_at >= NOW() - INTERVAL '30 days'
            """)
            row = cur.fetchone()
            last30, active_days = row[0], max(row[1], 1)
    avg_day = round(last30 / active_days) if last30 else 0
    return {"total": total, "today": today, "active_sources": active_sources, "avg_day": avg_day, "active_days": active_days}

@app.get("/trends/topics")
def trends_topics(hours: int = Query(168, ge=1, le=2160)):
    from database.connection import get_conn
    import math
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT topic, COUNT(*) as cnt
                FROM articles
                WHERE topic IS NOT NULL AND collected_at >= NOW() - (%s || ' hours')::INTERVAL
                GROUP BY topic ORDER BY cnt DESC
            """, (str(hours),))
            current = {r[0]: r[1] for r in cur.fetchall()}
            cur.execute("""
                SELECT topic, COUNT(*) as cnt
                FROM articles
                WHERE topic IS NOT NULL
                  AND collected_at >= NOW() - (%s || ' hours')::INTERVAL * 2
                  AND collected_at < NOW() - (%s || ' hours')::INTERVAL
                GROUP BY topic
            """, (str(hours), str(hours)))
            previous = {r[0]: r[1] for r in cur.fetchall()}
    result = []
    for topic, cnt in sorted(current.items(), key=lambda x: -x[1]):
        prev = previous.get(topic, 0)
        diff = round((cnt - prev) / max(prev, 1) * 100) if prev > 0 else 100
        result.append({"topic": topic, "count": cnt, "prev": prev, "diff": diff})
    return result

@app.get("/trends/sources")
def trends_sources(hours: int = Query(168, ge=1, le=2160)):
    from database.connection import get_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.name, s.category, COUNT(a.id) as cnt
                FROM articles a JOIN sources s ON s.id = a.source_id
                WHERE a.collected_at >= NOW() - (%s || ' hours')::INTERVAL
                GROUP BY s.name, s.category ORDER BY cnt DESC LIMIT 15
            """, (str(hours),))
            return [{"name": r[0], "category": r[1], "count": r[2]} for r in cur.fetchall()]

@app.get("/trends/volume")
def trends_volume(days: int = Query(30, ge=7, le=90)):
    from database.connection import get_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DATE(collected_at AT TIME ZONE 'Europe/Paris') as d, COUNT(*) as cnt
                FROM articles
                WHERE collected_at >= NOW() - (%s || ' days')::INTERVAL
                GROUP BY d ORDER BY d ASC
            """, (str(days),))
            return [{"date": str(r[0]), "count": r[1]} for r in cur.fetchall()]

@app.get("/trends/words")
def trends_words(hours: int = Query(24, ge=1, le=168)):
    from database.connection import get_conn
    from collections import Counter, defaultdict
    import re, math
    STOPWORDS = {
        'le','la','les','un','une','des','de','du','en','et','est','au','aux',
        'ce','qui','que','se','sa','son','ses','sur','par','pour','dans','avec',
        'à','il','elle','ils','elles','on','l','d','s','plus','très','aussi',
        'mais','ou','donc','car','ne','pas','tout','cette','ces','leur','leurs',
        'après','avant','entre','selon','dont','lors','même','comme','contre',
        'depuis','sans','sous','chez','via','alors','ainsi','quand','cela',
        'avoir','être','fait','faire','bien','non','oui','mise','nouveau',
        'nouvelle','premier','première','france','français','française',
        'gouvernement','ministre','président','paris','national','police',
        'selon','celui','celle','ceux','celles','autre','autres','tout','tous',
        'toutes','toute','lors','lequel','laquelle','dont',
        'monde','figaro','libération','express','point','nouvel','humanité',
        'croix','ouest','voix','nord','alsace','républicain','progrès','dauphiné',
        'provence','méridional','dépêche','midi','bretagne','normandie',
        'berry','canard','enchaîné','rugbyrama','franceantilles','martinique',
        'réunion','guadeloupe','montagne','lorrain','républicaine','populaire',
        'journal','presse','quotidien','hebdomadaire','revue','gazette',
        'info','news','actu','media','radio','télé','tele','bfm',
        'cnews','lci','itele','rmc','europe','rtl','inter','culture','bleu',
        'huffpost','franceinfo','lefigaro','lemonde','leparisien',
    }
    ref_hours = min(hours * 6, 55 * 24)  # cap à 55j (rétention 60j)
    word_re = re.compile(r'\b[a-zàâäéèêëîïôùûüÿœæç]{4,}\b')

    with get_conn() as conn:
        with conn.cursor() as cur:
            # Une seule requête — on charge tout en mémoire en une passe
            cur.execute("""
                SELECT a.title, a.summary, a.source_id,
                    (a.collected_at >= NOW() - (%s || ' hours')::INTERVAL) AS is_current
                FROM articles a
                WHERE a.collected_at >= NOW() - (%s || ' hours')::INTERVAL
            """, (str(hours), str(ref_hours)))
            rows = cur.fetchall()
            cur.execute("SELECT id, name FROM sources WHERE active = true")
            source_names = {r[0]: r[1] for r in cur.fetchall()}
            cur.execute("SELECT COUNT(*) FROM sources WHERE active = true")
            total_active_sources = cur.fetchone()[0]

    # Seuils adaptatifs : % du nombre de sources actives
    viral_pct  = 0.20  # 20% des sources actives → VIRAL
    chaud_pct  = 0.12  # 12% → CHAUD
    hausse_pct = 0.06  # 6%  → HAUSSE

    # Comptage en une seule passe
    curr_counts  = Counter()
    curr_sources = defaultdict(set)    # mot → sources distinctes (période actuelle)
    curr_src_cnt = defaultdict(Counter) # mot → {source: count}
    ref_counts   = Counter()
    n_curr = n_ref = 0

    for title, summary, src_id, is_current in rows:
        text = f"{title or ''} {summary or ''}"
        words = set(w for w in word_re.findall(text.lower()) if w not in STOPWORDS)
        if is_current:
            n_curr += 1
            for w in words:
                curr_counts[w] += 1
                curr_sources[w].add(src_id)
                curr_src_cnt[w][src_id] += 1
        else:
            n_ref += 1
            ref_counts.update(words)  # une fois par doc pour fréquence documentaire

    n_curr = max(n_curr, 1)
    n_ref  = max(n_ref, 1)

    results = []
    for word, cnt in curr_counts.most_common(300):
        if cnt < 3:
            continue
        n_src = len(curr_sources[word])
        if n_src < 2:
            continue

        freq_curr = cnt / n_curr
        freq_ref  = (ref_counts.get(word, 0) + 0.5) / n_ref
        ratio     = freq_curr / freq_ref
        score     = ratio * math.log(cnt + 1)

        # Seuils adaptatifs
        src_ratio = n_src / max(total_active_sources, 1)
        if src_ratio >= viral_pct:
            heat = 'VIRAL'
        elif src_ratio >= chaud_pct:
            heat = 'CHAUD'
        elif src_ratio >= hausse_pct:
            heat = 'HAUSSE'
        else:
            heat = 'STABLE'

        direction = 'emergence' if ratio >= 2.0 else 'retombee' if ratio < 0.8 else 'plateau'

        # Top sources déjà calculées dans curr_src_cnt
        top_sources = [
            source_names.get(s, s)
            for s, _ in curr_src_cnt[word].most_common(4)
        ]

        results.append({
            "word": word, "count": cnt, "sources": n_src,
            "ratio": round(ratio, 1), "score": round(score, 1),
            "heat": heat, "direction": direction,
            "top_sources": top_sources, "ref_hours": ref_hours,
        })

    results.sort(key=lambda x: -x["score"])
    return results[:20]

# ── Partage ───────────────────────────────────────────────────
@app.post("/watchlists/{watchlist_id}/share")
def share_watchlist(watchlist_id: int, expire_days: int = 30):
    from api.share import generate_share_token
    result = generate_share_token(watchlist_id=watchlist_id, expire_days=expire_days)
    return result

@app.delete("/watchlists/{watchlist_id}/share")
def revoke_share(watchlist_id: int):
    return {"revoked": revoke_share_token(watchlist_id=watchlist_id)}

@app.get("/share/{token}")
def get_shared(token: str):
    data = get_watchlist_by_token(token=token)
    if not data:
        raise HTTPException(status_code=404, detail="Lien invalide ou expiré")
    return data
