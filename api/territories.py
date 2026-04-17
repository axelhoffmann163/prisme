from database.connection import get_conn


def get_territories(type_filter: str = None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            if type_filter:
                cur.execute("""
                    SELECT t.id, t.name, t.type, t.code, t.region_id,
                           t.dept_id, t.keywords, t.source_ids,
                           r.name AS region_name
                    FROM territories t
                    LEFT JOIN territories r ON r.id = t.region_id
                    WHERE t.type = %s
                    ORDER BY t.name
                """, (type_filter,))
            else:
                cur.execute("""
                    SELECT t.id, t.name, t.type, t.code, t.region_id,
                           t.dept_id, t.keywords, t.source_ids,
                           r.name AS region_name
                    FROM territories t
                    LEFT JOIN territories r ON r.id = t.region_id
                    ORDER BY t.type, t.name
                """)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]


def get_territory(territory_id: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT t.id, t.name, t.type, t.code, t.region_id,
                       t.dept_id, t.keywords, t.source_ids,
                       r.name AS region_name
                FROM territories t
                LEFT JOIN territories r ON r.id = t.region_id
                WHERE t.id = %s
            """, (territory_id,))
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
            return dict(zip(cols, row)) if row else None


def get_territory_stats(territory_id: str, hours: int = 24):
    t = get_territory(territory_id)
    if not t:
        return None

    keywords = t.get('keywords') or []
    source_ids = t.get('source_ids') or []

    with get_conn() as conn:
        with conn.cursor() as cur:
            # Construction de la clause WHERE
            conditions = ["a.collected_at >= NOW() - (%s || ' hours')::INTERVAL"]
            params = [str(hours)]

            source_cond = ""
            kw_cond = ""

            if source_ids:
                placeholders = ','.join(['%s'] * len(source_ids))
                source_cond = f"a.source_id IN ({placeholders})"
                params_src = source_ids[:]
            else:
                params_src = []

            if keywords:
                kw_parts = []
                params_kw = []
                for kw in keywords[:10]:  # limite pour perf
                    kw_parts.append("(lower(a.title) LIKE lower(%s) OR lower(coalesce(a.summary,'')) LIKE lower(%s))")
                    params_kw.extend([f'%{kw}%', f'%{kw}%'])
                kw_cond = '(' + ' OR '.join(kw_parts) + ')'

            # Combinaison source OU mots-clés
            if source_cond and kw_cond:
                conditions.append(f"({source_cond} OR {kw_cond})")
                params = params + params_src + params_kw
            elif source_cond:
                conditions.append(source_cond)
                params = params + params_src
            elif kw_cond:
                conditions.append(kw_cond)
                params = params + params_kw

            where = ' AND '.join(conditions)

            # Total articles
            cur.execute(f"SELECT COUNT(*) FROM articles a WHERE {where}", params)
            total = cur.fetchone()[0]

            # Sources distinctes
            cur.execute(f"""
                SELECT COUNT(DISTINCT a.source_id)
                FROM articles a WHERE {where}
            """, params)
            distinct_sources = cur.fetchone()[0]

            # Thème dominant
            cur.execute(f"""
                SELECT topic, COUNT(*) as cnt
                FROM articles a
                WHERE {where} AND topic IS NOT NULL
                GROUP BY topic ORDER BY cnt DESC LIMIT 1
            """, params)
            row = cur.fetchone()
            top_topic = row[0] if row else None

            # Thèmes
            cur.execute(f"""
                SELECT topic, COUNT(*) as cnt
                FROM articles a
                WHERE {where} AND topic IS NOT NULL
                GROUP BY topic ORDER BY cnt DESC
            """, params)
            topics = [{'topic': r[0], 'count': r[1]} for r in cur.fetchall()]

            # Top sources
            cur.execute(f"""
                SELECT s.name, s.category, COUNT(a.id) as cnt
                FROM articles a JOIN sources s ON s.id = a.source_id
                WHERE {where}
                GROUP BY s.name, s.category ORDER BY cnt DESC LIMIT 8
            """, params)
            top_sources = [{'name': r[0], 'category': r[1], 'count': r[2]} for r in cur.fetchall()]

            # Comparaison période précédente
            prev_params = [str(hours * 2), str(hours)] + params[1:]
            cur.execute(f"""
                SELECT COUNT(*) FROM articles a
                WHERE a.collected_at >= NOW() - (%s || ' hours')::INTERVAL
                  AND a.collected_at < NOW() - (%s || ' hours')::INTERVAL
                  AND ({' AND '.join(conditions[1:])})
            """, prev_params) if len(conditions) > 1 else None
            try:
                prev_total = cur.fetchone()[0]
            except Exception:
                prev_total = 0

    diff = round((total - prev_total) / max(prev_total, 1) * 100) if prev_total else 0

    return {
        'territory': t,
        'total': total,
        'total_prev': prev_total,
        'diff': diff,
        'distinct_sources': distinct_sources,
        'top_topic': top_topic,
        'topics': topics,
        'top_sources': top_sources,
    }


def get_territory_articles(territory_id: str, hours: int = 24, limit: int = 50):
    t = get_territory(territory_id)
    if not t:
        return []

    keywords = t.get('keywords') or []
    source_ids = t.get('source_ids') or []

    with get_conn() as conn:
        with conn.cursor() as cur:
            conditions = ["a.collected_at >= NOW() - (%s || ' hours')::INTERVAL"]
            params = [str(hours)]
            params_src, params_kw = [], []

            if source_ids:
                placeholders = ','.join(['%s'] * len(source_ids))
                source_cond = f"a.source_id IN ({placeholders})"
                params_src = source_ids[:]
            else:
                source_cond = ""

            if keywords:
                kw_parts = []
                for kw in keywords[:10]:
                    kw_parts.append("(lower(a.title) LIKE lower(%s) OR lower(coalesce(a.summary,'')) LIKE lower(%s))")
                    params_kw.extend([f'%{kw}%', f'%{kw}%'])
                kw_cond = '(' + ' OR '.join(kw_parts) + ')'
            else:
                kw_cond = ""

            if source_cond and kw_cond:
                conditions.append(f"({source_cond} OR {kw_cond})")
                params = params + params_src + params_kw
            elif source_cond:
                conditions.append(source_cond)
                params = params + params_src
            elif kw_cond:
                conditions.append(kw_cond)
                params = params + params_kw

            where = ' AND '.join(conditions)

            cur.execute(f"""
                SELECT a.id, a.title, a.url, a.summary,
                       a.published_at, a.collected_at, a.topic,
                       s.name AS source_name, s.category AS source_category
                FROM articles a JOIN sources s ON s.id = a.source_id
                WHERE {where}
                ORDER BY a.collected_at DESC
                LIMIT %s
            """, params + [limit])
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]


def create_commune_territory(name: str, keywords: list, source_ids: list = None,
                              dept_id: str = None, region_id: str = None):
    import re
    tid = 'commune-' + re.sub(r'[^a-z0-9]', '-', name.lower())
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO territories (id, name, type, keywords, source_ids, dept_id, region_id)
                VALUES (%s, %s, 'commune', %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    keywords = EXCLUDED.keywords,
                    source_ids = EXCLUDED.source_ids,
                    dept_id = EXCLUDED.dept_id,
                    region_id = EXCLUDED.region_id
                RETURNING id, name, type
            """, (tid, name, keywords, source_ids or [], dept_id, region_id))
            row = cur.fetchone()
    return {'id': row[0], 'name': row[1], 'type': row[2]}


def delete_territory(territory_id: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM territories WHERE id = %s AND type = 'commune'", (territory_id,))
    return {'deleted': territory_id}


def get_territories_overview(hours: int = 24, type_filter: str = 'region'):
    """Compte rapide d'articles par territoire pour la vue d'ensemble."""
    territories = get_territories(type_filter)
    result = []
    with get_conn() as conn:
        with conn.cursor() as cur:
            for t in territories:
                source_ids = t.get('source_ids') or []
                keywords = t.get('keywords') or []
                params = [str(hours)]
                parts = []

                if source_ids:
                    ph = ','.join(['%s'] * len(source_ids))
                    parts.append(f"source_id IN ({ph})")
                    params += source_ids

                if keywords:
                    kw_parts = [f"lower(title) LIKE lower(%s)" for kw in keywords[:6]]
                    parts.append('(' + ' OR '.join(kw_parts) + ')')
                    params += [f'%{kw}%' for kw in keywords[:6]]

                if not parts:
                    result.append({**t, 'count': 0})
                    continue

                where = f"collected_at >= NOW() - (%s || ' hours')::INTERVAL AND ({' OR '.join(parts)})"
                cur.execute(f"SELECT COUNT(*) FROM articles WHERE {where}", params)
                count = cur.fetchone()[0]
                result.append({**t, 'count': count})

    result.sort(key=lambda x: -x['count'])
    return result
