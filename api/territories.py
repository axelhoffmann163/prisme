import re
from collections import Counter
from datetime import datetime, timezone, timedelta

from database.connection import get_conn

STOPWORDS = {
    'le','la','les','un','une','des','de','du','en','et','est','au','aux',
    'ce','qui','que','se','sa','son','ses','sur','par','pour','dans','avec',
    'à','il','elle','ils','elles','on','l','d','s','plus','très','aussi',
    'mais','ou','donc','car','ne','pas','tout','cette','ces','leur','leurs',
    'après','avant','entre','selon','dont','lors','même','comme','contre',
    'depuis','sans','sous','chez','via','alors','ainsi','quand','cela',
    'avoir','être','fait','faire','bien','non','oui','nouveau','nouvelle',
    'premier','première','france','français','française','national','police',
    'selon','celui','celle','ceux','celles','autre','autres','tous','toutes',
    'monde','figaro','libération','express','point','humanité','croix',
    'journal','presse','quotidien','info','news','actu','media','radio',
    'télé','bfm','cnews','lci','rmc','europe','rtl','inter','bleu',
}

ENTITY_DB = {
    'CFDT':'Organisation','CGT':'Organisation','FO':'Organisation',
    'MEDEF':'Organisation','CPME':'Organisation',
    'Renaissance':'Organisation','RN':'Organisation','LFI':'Organisation',
    'PS':'Organisation','LR':'Organisation',
    'Sénat':'Institution','Matignon':'Institution','Élysée':'Institution',
    'SNCF':'Entreprise','RATP':'Entreprise','EDF':'Entreprise',
    'Macron':'Personne','Bayrou':'Personne','Marine Le Pen':'Personne',
}


def _build_where(keywords, hours, extra_conds=None):
    """Construit la clause WHERE pour filtrer les articles d'un territoire."""
    params = [str(hours)]
    kw_parts = []
    for kw in keywords[:15]:
        kw_parts.append("(lower(a.title) LIKE lower(%s) OR lower(coalesce(a.summary,'')) LIKE lower(%s))")
        params.extend([f'%{kw}%', f'%{kw}%'])
    where = "a.collected_at >= NOW() - (%s || ' hours')::INTERVAL"
    if kw_parts:
        where += " AND (" + " OR ".join(kw_parts) + ")"
    return where, params


def get_all_territories():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, type, keywords, created_at, last_viewed FROM territories ORDER BY created_at DESC")
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]


def create_territory(name: str, type: str, keywords: list):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO territories (name, type, keywords) VALUES (%s, %s, %s) RETURNING id, name, type, keywords, created_at",
                (name, type, keywords)
            )
            cols = [d[0] for d in cur.description]
            return dict(zip(cols, cur.fetchone()))


def delete_territory(territory_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM territories WHERE id = %s", (territory_id,))
    return {'deleted': territory_id}


def get_territory_stats(territory_id: int, hours: int = 168):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, type, keywords FROM territories WHERE id = %s", (territory_id,))
            row = cur.fetchone()
            if not row:
                return None
            tid, name, ttype, keywords = row

            where, params = _build_where(keywords, hours)

            # Total actuel
            cur.execute(f"SELECT COUNT(*) FROM articles a WHERE {where}", params)
            total = cur.fetchone()[0]

            # Total période précédente
            where_prev, params_prev = _build_where(keywords, hours * 2)
            params_prev_trimmed = params_prev[:1]
            params_prev_trimmed[0] = str(hours)
            cur.execute(f"""
                SELECT COUNT(*) FROM articles a
                WHERE a.collected_at >= NOW() - (%s || ' hours')::INTERVAL * 2
                  AND a.collected_at < NOW() - (%s || ' hours')::INTERVAL
                  AND ({' OR '.join(
                      ["(lower(a.title) LIKE lower(%s) OR lower(coalesce(a.summary,'')) LIKE lower(%s))" for _ in keywords[:15]]
                  )})
            """, [str(hours), str(hours)] + [x for kw in keywords[:15] for x in [f'%{kw}%', f'%{kw}%']])
            total_prev = cur.fetchone()[0]

            # Sources distinctes
            cur.execute(f"SELECT COUNT(DISTINCT a.source_id) FROM articles a WHERE {where}", params)
            distinct_sources = cur.fetchone()[0]

            # Timeline 7j par tranches de 6h
            cur.execute(f"""
                SELECT DATE_TRUNC('day', a.collected_at AT TIME ZONE 'Europe/Paris') as day,
                       COUNT(*) as cnt
                FROM articles a WHERE {where}
                GROUP BY day ORDER BY day ASC
            """, params)
            timeline = [{'date': str(r[0].date()) if r[0] else '', 'count': r[1]} for r in cur.fetchall()]

            # Top sources
            cur.execute(f"""
                SELECT s.name, s.category, COUNT(a.id) as cnt
                FROM articles a JOIN sources s ON s.id = a.source_id
                WHERE {where}
                GROUP BY s.name, s.category ORDER BY cnt DESC LIMIT 8
            """, params)
            top_sources = [{'name': r[0], 'category': r[1], 'count': r[2]} for r in cur.fetchall()]

            # Articles pour mots + entités
            cur.execute(f"""
                SELECT a.title, a.summary, a.url, a.collected_at, a.topic,
                       s.name as source_name, s.category as source_category
                FROM articles a JOIN sources s ON s.id = a.source_id
                WHERE {where}
                ORDER BY a.collected_at DESC LIMIT 100
            """, params)
            cols2 = [d[0] for d in cur.description]
            articles = [dict(zip(cols2, r)) for r in cur.fetchall()]

    # Mots fréquents
    text = ' '.join((a['title'] or '') + ' ' + (a['summary'] or '') for a in articles).lower()
    words = re.findall(r'\b[a-zàâäéèêëîïôùûüÿœæç]{4,}\b', text)
    top_words = [{'word': w, 'count': c} for w, c in Counter(w for w in words if w not in STOPWORDS).most_common(20)]

    # Entités
    entities = []
    counts, types = {}, {}
    for name_e, etype in ENTITY_DB.items():
        pat = re.compile(r'\b' + re.escape(name_e) + r'\b', re.IGNORECASE)
        n = len(pat.findall(text))
        if n >= 2:
            counts[name_e] = n
            types[name_e] = etype
    entities = sorted([{'name': n, 'count': c, 'type': types[n]} for n, c in counts.items()], key=lambda x: -x['count'])[:8]

    # Premier / dernier signal
    sorted_arts = sorted(articles, key=lambda a: str(a.get('collected_at') or ''))
    first = sorted_arts[0] if sorted_arts else None
    last = sorted_arts[-1] if sorted_arts else None

    diff = round((total - total_prev) / max(total_prev, 1) * 100) if total_prev else 0

    return {
        'id': tid,
        'name': name,
        'type': ttype,
        'keywords': keywords,
        'total': total,
        'total_prev': total_prev,
        'diff': diff,
        'distinct_sources': distinct_sources,
        'timeline': timeline,
        'top_sources': top_sources,
        'top_words': top_words,
        'entities': entities,
        'first_signal': first,
        'last_signal': last,
        'articles': articles[:50],
    }
