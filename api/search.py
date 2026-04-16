from database.connection import get_conn


def parse_advanced_query(q: str):
    """
    Parse la syntaxe avancée et retourne une condition SQL + params.
    Supporte : ET/AND, OU/OR, -mot (exclusion), "phrase exacte", (groupes)
    """
    # Normalise ET/OU en opérateurs internes
    q = q.replace(' ET ', ' ').replace(' AND ', ' ')
    q = q.replace(' OU ', ' ||| ').replace(' OR ', ' ||| ')

    parts = q.split(' ||| ')
    or_conditions = []
    or_params = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        and_conditions = []
        and_params = []
        tokens = []

        # Extrait les phrases entre guillemets
        import re
        exact_phrases = re.findall(r'"([^"]+)"', part)
        part_clean = re.sub(r'"[^"]+"', '', part)

        # Ajoute les phrases exactes comme conditions LIKE
        for phrase in exact_phrases:
            and_conditions.append(
                "(lower(a.title) LIKE lower(%s) OR lower(coalesce(a.summary,'')) LIKE lower(%s))"
            )
            and_params.extend([f"%{phrase}%", f"%{phrase}%"])

        # Traite les mots normaux et les exclusions
        words = part_clean.split()
        for word in words:
            if not word:
                continue
            if word.startswith('-') and len(word) > 1:
                # Exclusion
                excluded = word[1:]
                and_conditions.append(
                    "lower(a.title) NOT LIKE lower(%s) AND lower(coalesce(a.summary,'')) NOT LIKE lower(%s)"
                )
                and_params.extend([f"%{excluded}%", f"%{excluded}%"])
            elif len(word) >= 2:
                # Inclusion normale
                and_conditions.append(
                    "(lower(a.title) LIKE lower(%s) OR lower(coalesce(a.summary,'')) LIKE lower(%s))"
                )
                and_params.extend([f"%{word}%", f"%{word}%"])

        if and_conditions:
            or_conditions.append(f"({' AND '.join(and_conditions)})")
            or_params.extend(and_params)

    if not or_conditions:
        return "1=1", []

    return f"({' OR '.join(or_conditions)})", or_params


def search_articles(
    q: str,
    limit: int = 50,
    category: str = None,
    topic: str = None,
    days: int = 7,
    source_id: str = None,
):
    where_clauses = []
    params = []

    # Filtre par date
    where_clauses.append("a.collected_at >= NOW() - (%s || ' days')::INTERVAL")
    params.append(str(days))

    # Filtre par syntaxe avancée
    query_condition, query_params = parse_advanced_query(q)
    where_clauses.append(query_condition)
    params.extend(query_params)

    # Filtre par catégorie source
    if category:
        where_clauses.append("s.category = %s")
        params.append(category)

    # Filtre par topic thématique
    if topic:
        where_clauses.append("a.topic = %s")
        params.append(topic)

    # Filtre par source spécifique
    if source_id:
        where_clauses.append("a.source_id = %s")
        params.append(source_id)

    where = " AND ".join(where_clauses)

    sql = f"""
    SELECT
        a.id,
        a.title,
        a.url,
        a.summary,
        a.published_at,
        a.collected_at,
        a.author,
        a.tags,
        a.category,
        a.topic,
        s.id AS source_id,
        s.name AS source_name,
        s.category AS source_category
    FROM articles a
    JOIN sources s ON s.id = a.source_id
    WHERE {where}
    ORDER BY a.published_at DESC NULLS LAST
    LIMIT %s
    """
    params.append(limit)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()

    results = [dict(zip(cols, row)) for row in rows]

    return {
        "query": q,
        "total": len(results),
        "days": days,
        "results": results,
    }
