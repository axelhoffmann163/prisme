import re
from collections import Counter
from database.connection import get_conn


# ── Dossiers ──────────────────────────────────────────────────

def get_folders():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT f.id, f.name, f.color, f.created_at,
                    COUNT(DISTINCT fw.watchlist_id) AS watchlist_count
                FROM folders f
                LEFT JOIN folder_watchlists fw ON fw.folder_id = f.id
                GROUP BY f.id ORDER BY f.name
            """)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
    return [dict(zip(cols, r)) for r in rows]


def create_folder(name: str, color: str = "#2563EB"):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO folders (name, color) VALUES (%s, %s) RETURNING id, name, color, created_at",
                (name, color)
            )
            row = cur.fetchone()
    return dict(zip(["id", "name", "color", "created_at"], row))


def delete_folder(folder_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM folders WHERE id = %s", (folder_id,))
    return {"deleted": folder_id}


def update_folder(folder_id: int, name: str = None, color: str = None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            if name:
                cur.execute("UPDATE folders SET name = %s WHERE id = %s", (name, folder_id))
            if color:
                cur.execute("UPDATE folders SET color = %s WHERE id = %s", (color, folder_id))
    return {"updated": folder_id}


def add_watchlist_to_folder(folder_id: int, watchlist_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO folder_watchlists (folder_id, watchlist_id)
                VALUES (%s, %s) ON CONFLICT DO NOTHING
            """, (folder_id, watchlist_id))
    return {"ok": True}


def remove_watchlist_from_folder(folder_id: int, watchlist_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM folder_watchlists WHERE folder_id = %s AND watchlist_id = %s",
                (folder_id, watchlist_id)
            )
    return {"ok": True}


def get_folder_watchlists(folder_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT w.id, w.name, w.query, w.created_at, w.last_viewed,
                    (SELECT COUNT(*) FROM articles a
                     JOIN sources s ON s.id = a.source_id
                     WHERE a.collected_at >= NOW() - INTERVAL '24 hours'
                     AND (lower(a.title) LIKE lower('%%' || split_part(w.query,' ',1) || '%%')
                          OR lower(coalesce(a.summary,'')) LIKE lower('%%' || split_part(w.query,' ',1) || '%%'))
                    ) AS articles_today,
                    (SELECT COUNT(*) FROM articles a
                     WHERE a.collected_at > COALESCE(w.last_viewed, w.created_at)
                     AND (lower(a.title) LIKE lower('%%' || split_part(w.query,' ',1) || '%%'))
                    ) AS new_articles
                FROM watchlists w
                JOIN folder_watchlists fw ON fw.watchlist_id = w.id
                WHERE fw.folder_id = %s
                ORDER BY w.name
            """, (folder_id,))
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
    return [dict(zip(cols, r)) for r in rows]


# ── Watchlists ────────────────────────────────────────────────

def get_watchlists():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT w.id, w.name, w.query, w.category, w.created_at, w.last_viewed,
                    (SELECT COUNT(*) FROM articles a
                     WHERE a.collected_at > COALESCE(w.last_viewed, w.created_at)
                     AND lower(a.title) LIKE lower('%%' || split_part(w.query,' ',1) || '%%')
                    ) AS new_articles,
                    ARRAY(SELECT fw.folder_id FROM folder_watchlists fw WHERE fw.watchlist_id = w.id) AS folder_ids
                FROM watchlists w
                ORDER BY w.created_at DESC
            """)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
    return [dict(zip(cols, r)) for r in rows]


def create_watchlist(name: str, query: str, category: str = None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO watchlists (name, query, category) VALUES (%s, %s, %s) RETURNING id, name, query, category, created_at",
                (name, query, category)
            )
            row = cur.fetchone()
    return dict(zip(["id", "name", "query", "category", "created_at"], row))


def delete_watchlist(watchlist_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM watchlists WHERE id = %s", (watchlist_id,))
    return {"deleted": watchlist_id}


def get_watchlist_articles(watchlist_id: int, limit: int = 50):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT query FROM watchlists WHERE id = %s", (watchlist_id,))
            row = cur.fetchone()
            if not row:
                return {"total": 0, "articles": []}
            query = row[0]
            keyword = query.split()[0].strip('"').lower()
            cur.execute("""
                UPDATE watchlists SET last_viewed = NOW() WHERE id = %s
            """, (watchlist_id,))
            cur.execute("""
                SELECT a.id, a.title, a.url, a.summary, a.published_at, a.collected_at,
                    a.author, a.category, a.topic, s.id AS source_id,
                    s.name AS source_name, s.category AS source_category
                FROM articles a
                JOIN sources s ON s.id = a.source_id
                WHERE lower(a.title) LIKE lower(%s)
                   OR lower(coalesce(a.summary,'')) LIKE lower(%s)
                ORDER BY a.collected_at DESC
                LIMIT %s
            """, (f"%{keyword}%", f"%{keyword}%", limit))
            cols = [d[0] for d in cur.description]
            articles = [dict(zip(cols, r)) for r in cur.fetchall()]
    return {"total": len(articles), "articles": articles}


# ── Stats analytiques ─────────────────────────────────────────

STOPWORDS = {
    "le","la","les","un","une","des","de","du","en","et","est","au","aux",
    "ce","qui","que","se","sa","son","ses","sur","par","pour","dans","avec",
    "à","il","elle","ils","elles","on","nous","vous","je","tu","l","d","s",
    "plus","très","aussi","mais","ou","donc","or","ni","car","ne","pas","tout",
    "cette","ces","leur","leurs","avoir","être","fait","faire","tout","bien",
    "après","avant","entre","selon","dont","lors","lors","même","comme",
    "contre","depuis","sans","sous","chez","lors","après","via","face"
}

REGION_MAP = {
    "ile-de-france": ["paris", "île-de-france", "val-de-marne", "hauts-de-seine", "seine-saint-denis"],
    "hauts-de-france": ["nord", "pas-de-calais", "somme", "oise", "aisne", "lille", "amiens"],
    "grand-est": ["alsace", "lorraine", "champagne", "strasbourg", "nancy", "reims", "metz"],
    "normandie": ["seine-maritime", "calvados", "manche", "rouen", "caen", "cherbourg"],
    "bretagne": ["finistère", "morbihan", "ille-et-vilaine", "rennes", "brest", "quimper"],
    "pays-de-la-loire": ["loire-atlantique", "maine-et-loire", "nantes", "angers", "le mans"],
    "centre-val-de-loire": ["loiret", "loir-et-cher", "indre", "orléans", "tours", "bourges"],
    "bourgogne-franche-comté": ["côte-d'or", "saône-et-loire", "yonne", "doubs", "dijon", "besançon"],
    "auvergne-rhône-alpes": ["rhône", "isère", "puy-de-dôme", "lyon", "grenoble", "clermont"],
    "nouvelle-aquitaine": ["gironde", "dordogne", "charente", "bordeaux", "limoges", "poitiers"],
    "occitanie": ["hérault", "haute-garonne", "gard", "toulouse", "montpellier", "nîmes"],
    "paca": ["bouches-du-rhône", "var", "alpes-maritimes", "marseille", "nice", "toulon"],
    "corse": ["corse", "ajaccio", "bastia"],
}

SOURCE_REGION_MAP = {
    "ouest_france": "bretagne", "le_telegramme": "bretagne",
    "la_voix_du_nord": "hauts-de-france", "courrier_picard": "hauts-de-france",
    "l_est_republicain": "grand-est", "l_alsace": "grand-est",
    "dna": "grand-est", "republicain_lorrain": "grand-est", "vosges_matin": "grand-est",
    "l_union_ardennais": "grand-est",
    "paris_normandie": "normandie", "la_manche_libre": "normandie",
    "presse_ocean": "pays-de-la-loire", "courrier_de_l_ouest": "pays-de-la-loire",
    "la_nouvelle_republique": "centre-val-de-loire", "la_republique_du_centre": "centre-val-de-loire",
    "le_journal_du_centre": "centre-val-de-loire", "le_berry_republicain": "centre-val-de-loire",
    "l_echo_republicain": "centre-val-de-loire", "l_yonne_republicaine": "bourgogne-franche-comté",
    "journal_saone_et_loire": "bourgogne-franche-comté",
    "le_progres": "auvergne-rhône-alpes", "le_dauphine": "auvergne-rhône-alpes",
    "la_montagne": "auvergne-rhône-alpes",
    "sud_ouest": "nouvelle-aquitaine", "charente_libre": "nouvelle-aquitaine",
    "le_populaire_du_centre": "nouvelle-aquitaine",
    "la_depeche": "occitanie", "midi_libre": "occitanie",
    "la_provence": "paca", "nice_matin": "paca", "var_matin": "paca",
    "corse_matin": "corse",
    "le_maine_libre": "pays-de-la-loire",
}

REGION_LABELS = {
    "ile-de-france": "Île-de-France",
    "hauts-de-france": "Hauts-de-France",
    "grand-est": "Grand Est",
    "normandie": "Normandie",
    "bretagne": "Bretagne",
    "pays-de-la-loire": "Pays de la Loire",
    "centre-val-de-loire": "Centre-Val de Loire",
    "bourgogne-franche-comté": "Bourgogne-FC",
    "auvergne-rhône-alpes": "Auvergne-RA",
    "nouvelle-aquitaine": "Nouvelle-Aquitaine",
    "occitanie": "Occitanie",
    "paca": "PACA",
    "corse": "Corse",
}


def get_watchlist_stats(watchlist_id: int, hours: int = 24):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT query FROM watchlists WHERE id = %s", (watchlist_id,))
            row = cur.fetchone()
            if not row:
                return {}
            query = row[0]
            keyword = query.split()[0].strip('"').lower()

            cur.execute("""
                SELECT a.id, a.title, a.summary, a.collected_at, a.topic,
                    s.id AS source_id, s.name AS source_name,
                    s.category AS source_category, s.subcategory
                FROM articles a
                JOIN sources s ON s.id = a.source_id
                WHERE a.collected_at >= NOW() - (%s || ' hours')::INTERVAL
                  AND (lower(a.title) LIKE lower(%s)
                       OR lower(coalesce(a.summary,'')) LIKE lower(%s))
                ORDER BY a.collected_at ASC
            """, (str(hours), f"%{keyword}%", f"%{keyword}%"))
            cols = [d[0] for d in cur.description]
            articles = [dict(zip(cols, r)) for r in cur.fetchall()]

    if not articles:
        return {
            "total": 0, "total_prev": 0, "distinct_sources": 0, "distinct_source_types": 0,
            "by_type": {}, "by_source": {}, "top_words": [],
            "timeline": [], "timeline_prev": [], "regional_coverage": {}, "topics": {}
        }

    # Métriques de base
    total = len(articles)
    sources_seen = {}
    type_counts = Counter()
    topic_counts = Counter()

    for a in articles:
        sid = a["source_id"]
        if sid not in sources_seen:
            sources_seen[sid] = {"name": a["source_name"], "category": a["source_category"], "count": 0}
        sources_seen[sid]["count"] += 1
        type_counts[a["source_category"]] += 1
        if a["topic"]:
            topic_counts[a["topic"]] += 1

    # Mots fréquents
    all_text = " ".join(
        (a["title"] or "") + " " + (a["summary"] or "")
        for a in articles
    ).lower()
    words = re.findall(r'\b[a-zàâäéèêëîïôùûüÿœæç]{4,}\b', all_text)
    word_counts = Counter(w for w in words if w not in STOPWORDS)
    top_words = [{"word": w, "count": c} for w, c in word_counts.most_common(20)]

    # Timeline — découpage en tranches
    if hours <= 6:
        bucket_minutes = 30
    elif hours <= 24:
        bucket_minutes = 60
    elif hours <= 72:
        bucket_minutes = 180
    else:
        bucket_minutes = 360

    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=hours)
    n_buckets = max(1, int(hours * 60 / bucket_minutes))
    buckets = [0] * n_buckets
    for a in articles:
        ts = a["collected_at"]
        if hasattr(ts, "tzinfo") and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        elif not hasattr(ts, "tzinfo"):
            continue
        idx = int((ts - start).total_seconds() / (bucket_minutes * 60))
        if 0 <= idx < n_buckets:
            buckets[idx] += 1
    timeline = [{"bucket": i, "count": buckets[i]} for i in range(n_buckets)]

    # Couverture régionale
    region_counts = Counter()
    for a in articles:
        sid = a["source_id"]
        if sid in SOURCE_REGION_MAP:
            region_counts[SOURCE_REGION_MAP[sid]] += 1

    regional_coverage = [
        {"region": REGION_LABELS.get(r, r), "key": r, "count": c}
        for r, c in region_counts.most_common()
    ]

    # Période précédente (même durée, décalée dans le passé)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM articles a
                WHERE a.collected_at >= NOW() - (%s || ' hours')::INTERVAL * 2
                  AND a.collected_at < NOW() - (%s || ' hours')::INTERVAL
                  AND (lower(a.title) LIKE lower(%s)
                       OR lower(coalesce(a.summary,'')) LIKE lower(%s))
            """, (str(hours), str(hours), f"%{keyword}%", f"%{keyword}%"))
            total_prev = cur.fetchone()[0]

            cur.execute("""
                SELECT a.collected_at
                FROM articles a
                WHERE a.collected_at >= NOW() - (%s || ' hours')::INTERVAL * 2
                  AND a.collected_at < NOW() - (%s || ' hours')::INTERVAL
                  AND (lower(a.title) LIKE lower(%s)
                       OR lower(coalesce(a.summary,'')) LIKE lower(%s))
                ORDER BY a.collected_at ASC
            """, (str(hours), str(hours), f"%{keyword}%", f"%{keyword}%"))
            prev_timestamps = [r[0] for r in cur.fetchall()]

    # Timeline période précédente — mêmes buckets
    buckets_prev = [0] * n_buckets
    start_prev = start - timedelta(hours=hours)
    for ts in prev_timestamps:
        if hasattr(ts, "tzinfo") and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        idx = int((ts - start_prev).total_seconds() / (bucket_minutes * 60))
        if 0 <= idx < n_buckets:
            buckets_prev[idx] += 1
    timeline_prev = [{"bucket": i, "count": buckets_prev[i]} for i in range(n_buckets)]

    return {
        "total": total,
        "total_prev": int(total_prev),
        "distinct_sources": len(sources_seen),
        "distinct_source_types": len(type_counts),
        "regions_covered": len(region_counts),
        "by_type": dict(type_counts.most_common()),
        "by_source": {v["name"]: v["count"] for v in sorted(sources_seen.values(), key=lambda x: -x["count"])[:10]},
        "top_words": top_words,
        "timeline": timeline,
        "timeline_prev": timeline_prev,
        "timeline_bucket_minutes": bucket_minutes,
        "regional_coverage": regional_coverage,
        "topics": dict(topic_counts.most_common()),
    }
