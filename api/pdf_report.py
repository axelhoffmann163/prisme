import io
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Optional

from database.connection import get_conn
from api.watchlist import get_watchlist_stats, get_watchlist_articles

STOPWORDS = {
    "le","la","les","un","une","des","de","du","en","et","est","au","aux",
    "ce","qui","que","se","sa","son","ses","sur","par","pour","dans","avec",
    "à","il","elle","ils","elles","on","nous","vous","je","tu","l","d","s",
    "plus","très","aussi","mais","ou","donc","or","ni","car","ne","pas","tout",
    "cette","ces","leur","leurs","avoir","être","fait","faire","tout","bien",
    "après","avant","entre","selon","dont","lors","même","comme","contre",
    "depuis","sans","sous","chez","via","face","alors","ainsi","dont","quand",
}

ENTITY_DB = {
    "CFDT": ["Organisation","syndicat"], "CGT": ["Organisation","syndicat"],
    "FO": ["Organisation","syndicat"], "CFE-CGC": ["Organisation","syndicat"],
    "MEDEF": ["Organisation","patronat"], "CPME": ["Organisation","patronat"],
    "Renaissance": ["Organisation","parti"], "RN": ["Organisation","parti"],
    "LFI": ["Organisation","parti"], "PS": ["Organisation","parti"],
    "LR": ["Organisation","parti"], "EELV": ["Organisation","parti"],
    "Sénat": ["Institution",""], "Matignon": ["Institution",""],
    "Élysée": ["Institution",""], "Bercy": ["Institution",""],
    "SNCF": ["Entreprise",""], "RATP": ["Entreprise",""],
    "EDF": ["Entreprise",""], "Renault": ["Entreprise",""],
    "Michelin": ["Entreprise",""], "Air France": ["Entreprise",""],
    "Macron": ["Personne","politique"], "Emmanuel Macron": ["Personne","politique"],
    "François Bayrou": ["Personne","politique"], "Bayrou": ["Personne","politique"],
    "Marine Le Pen": ["Personne","politique"],
    "Paris": ["Lieu",""], "Lyon": ["Lieu",""], "Marseille": ["Lieu",""],
    "Bruxelles": ["Lieu",""], "Berlin": ["Lieu",""], "Washington": ["Lieu",""],
}


def _ago(dt) -> str:
    if not dt:
        return ""
    if hasattr(dt, "tzinfo") and dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    s = (datetime.now(timezone.utc) - dt).total_seconds()
    if s < 60:
        return "à l'instant"
    if s < 3600:
        return f"il y a {int(s/60)} min"
    if s < 86400:
        return f"il y a {int(s/3600)}h"
    return f"il y a {int(s/86400)}j"


def _build_entities(articles: list) -> list:
    counts = {}
    types = {}
    all_text = " ".join((a.get("title") or "") + " " + (a.get("summary") or "") for a in articles)
    for name, (etype, _) in ENTITY_DB.items():
        pat = re.compile(r'\b' + re.escape(name) + r'\b')
        found = pat.findall(all_text)
        if len(found) >= 2:
            counts[name] = len(found)
            types[name] = etype
    return sorted([{"name": n, "count": c, "type": types[n]} for n, c in counts.items()], key=lambda x: -x["count"])[:8]


def _top_words(articles: list) -> list:
    text = " ".join((a.get("title") or "") + " " + (a.get("summary") or "") for a in articles).lower()
    words = re.findall(r'\b[a-zàâäéèêëîïôùûüÿœæç]{4,}\b', text)
    wc = Counter(w for w in words if w not in STOPWORDS)
    return [{"word": w, "count": c} for w, c in wc.most_common(15)]


def _bar_svg(data: dict, colors: dict, width=340, height=140) -> str:
    """Génère un SVG de barres horizontales."""
    if not data:
        return '<text x="10" y="20" font-family="sans-serif" font-size="11" fill="#9CA3AF">Pas de données</text>'
    entries = sorted(data.items(), key=lambda x: -x[1])[:8]
    max_val = entries[0][1] if entries else 1
    bar_h = min(18, (height - 10) // max(len(entries), 1))
    gap = 4
    label_w = 110
    svg_parts = []
    for i, (name, val) in enumerate(entries):
        y = i * (bar_h + gap)
        bar_w = int((val / max_val) * (width - label_w - 40))
        color = colors.get(name, "#2563EB")
        short = name[:16] + "…" if len(name) > 16 else name
        svg_parts.append(
            f'<text x="{label_w - 4}" y="{y + bar_h - 4}" text-anchor="end" font-family="sans-serif" font-size="10" fill="#6B7280">{short}</text>'
            f'<rect x="{label_w}" y="{y}" width="{bar_w}" height="{bar_h}" rx="3" fill="{color}" opacity="0.85"/>'
            f'<text x="{label_w + bar_w + 5}" y="{y + bar_h - 4}" font-family="sans-serif" font-size="10" fill="#374151">{val}</text>'
        )
    total_h = len(entries) * (bar_h + gap)
    return f'<svg width="{width}" height="{total_h}" xmlns="http://www.w3.org/2000/svg">{"".join(svg_parts)}</svg>'


def _timeline_svg(timeline: list, timeline_prev: list, width=560, height=100) -> str:
    """Génère un SVG de courbe temporelle."""
    if not timeline or all(t["count"] == 0 for t in timeline):
        return '<text x="10" y="20" font-family="sans-serif" font-size="11" fill="#9CA3AF">Pas de données</text>'
    n = len(timeline)
    max_val = max(max(t["count"] for t in timeline), max((t["count"] for t in timeline_prev), default=0), 1)
    pad = 20

    def pts(data):
        points = []
        for i, t in enumerate(data):
            x = pad + i * (width - 2 * pad) / max(n - 1, 1)
            y = height - pad - t["count"] / max_val * (height - 2 * pad)
            points.append(f"{x:.1f},{y:.1f}")
        return " ".join(points)

    svg = [f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">']
    # Grille
    for i in range(4):
        y = pad + i * (height - 2 * pad) / 3
        svg.append(f'<line x1="{pad}" y1="{y:.1f}" x2="{width-pad}" y2="{y:.1f}" stroke="#F3F4F6" stroke-width="1"/>')
    # Courbe précédente
    if timeline_prev:
        svg.append(f'<polyline points="{pts(timeline_prev)}" fill="none" stroke="#D1D5DB" stroke-width="1.5" stroke-dasharray="4,3"/>')
    # Aire sous la courbe actuelle
    first_x = pad
    last_x = pad + (n - 1) * (width - 2 * pad) / max(n - 1, 1)
    area_pts = pts(timeline)
    svg.append(f'<polygon points="{first_x},{height-pad} {area_pts} {last_x:.1f},{height-pad}" fill="#DBEAFE" opacity="0.5"/>')
    # Courbe actuelle
    svg.append(f'<polyline points="{pts(timeline)}" fill="none" stroke="#2563EB" stroke-width="2"/>')
    svg.append('</svg>')
    return "".join(svg)


def _type_donut_svg(by_type: dict, size=120) -> str:
    """Génère un SVG donut pour la répartition par type."""
    COLORS = {"PQN": "#2563EB", "PQR": "#059669", "TV": "#C2410C", "Radio": "#9333EA",
              "Magazine": "#0369A1", "Agence": "#BE123C", "Natif": "#065F46", "International": "#475569"}
    total = sum(by_type.values())
    if not total:
        return ""
    cx = cy = size / 2
    r_outer, r_inner = size / 2 - 4, size / 4
    import math
    svg = [f'<svg width="{size}" height="{size}" xmlns="http://www.w3.org/2000/svg">']
    angle = -math.pi / 2
    for cat, val in sorted(by_type.items(), key=lambda x: -x[1]):
        sweep = 2 * math.pi * val / total
        x1o = cx + r_outer * math.cos(angle)
        y1o = cy + r_outer * math.sin(angle)
        x1i = cx + r_inner * math.cos(angle)
        y1i = cy + r_inner * math.sin(angle)
        angle += sweep
        x2o = cx + r_outer * math.cos(angle)
        y2o = cy + r_outer * math.sin(angle)
        x2i = cx + r_inner * math.cos(angle)
        y2i = cy + r_inner * math.sin(angle)
        large = 1 if sweep > math.pi else 0
        color = COLORS.get(cat, "#888")
        d = (f"M {x1o:.2f},{y1o:.2f} A {r_outer},{r_outer} 0 {large},1 {x2o:.2f},{y2o:.2f} "
             f"L {x2i:.2f},{y2i:.2f} A {r_inner},{r_inner} 0 {large},0 {x1i:.2f},{y1i:.2f} Z")
        svg.append(f'<path d="{d}" fill="{color}"/>')
    svg.append('</svg>')
    return "".join(svg)


def generate_watchlist_pdf(watchlist_id: int, hours: int = 24) -> bytes:
    """Génère un PDF complet pour une veille."""
    # Récupère les données
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, query, created_at FROM watchlists WHERE id = %s", (watchlist_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Veille {watchlist_id} introuvable")
            wl_id, wl_name, wl_query, wl_created = row

    stats = get_watchlist_stats(watchlist_id, hours=hours)
    arts_data = get_watchlist_articles(watchlist_id, limit=50)
    articles = arts_data.get("articles", [])

    entities = _build_entities(articles)
    top_words = _top_words(articles)

    TYPE_COLORS = {"PQN": "#2563EB", "PQR": "#059669", "TV": "#C2410C",
                   "Radio": "#9333EA", "Magazine": "#0369A1", "Agence": "#BE123C"}

    period_lbl = f"{hours}h" if hours <= 24 else f"{hours//24}j"
    now_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
    diff = stats.get("total", 0) - stats.get("total_prev", 0)
    diff_color = "#059669" if diff > 0 else ("#DC2626" if diff < 0 else "#9CA3AF")
    diff_str = f"+{diff}" if diff > 0 else str(diff)

    # Graphiques SVG
    timeline_svg = _timeline_svg(stats.get("timeline", []), stats.get("timeline_prev", []))
    type_donut = _type_donut_svg(stats.get("by_type", {}))
    source_bars = _bar_svg(stats.get("by_source", {}), {}, width=300, height=160)
    region_bars = _bar_svg(
        {r["region"]: r["count"] for r in stats.get("regional_coverage", [])},
        {}, width=280, height=130
    )

    # Légende donut
    donut_legend = "".join(
        f'<div style="display:flex;align-items:center;gap:5px;margin-bottom:3px">'
        f'<div style="width:10px;height:10px;border-radius:2px;background:{TYPE_COLORS.get(t, "#888")};flex-shrink:0"></div>'
        f'<span style="font-size:10px;color:#6B7280">{t} — {c}</span></div>'
        for t, c in sorted(stats.get("by_type", {}).items(), key=lambda x: -x[1])
    )

    # Entités
    ent_rows = "".join(
        f'<tr><td style="padding:6px 8px;font-size:11px;font-weight:500;color:#111827">{e["name"]}</td>'
        f'<td style="padding:6px 8px;font-size:10px;color:#6B7280">{e["type"]}</td>'
        f'<td style="padding:6px 8px;text-align:right;font-size:11px;font-weight:600;color:#111827">{e["count"]}</td></tr>'
        for e in entities[:8]
    ) or '<tr><td colspan="3" style="padding:8px;font-size:11px;color:#9CA3AF">Pas assez de données</td></tr>'

    # Mots fréquents
    max_wc = top_words[0]["count"] if top_words else 1
    words_html = "".join(
        f'<span style="display:inline-block;padding:3px 9px;margin:3px;border-radius:20px;border:1px solid #E5E7EB;'
        f'font-size:{10 + int(w["count"]/max_wc*4)}px;color:#374151;background:#F9FAFB">'
        f'{w["word"]} <span style="color:#9CA3AF;font-size:9px">{w["count"]}</span></span>'
        for w in top_words
    )

    # Articles
    articles_rows = "".join(
        f'<tr style="border-bottom:1px solid #F3F4F6">'
        f'<td style="padding:8px;font-size:10px;color:#6B7280;white-space:nowrap">{_ago(a.get("collected_at"))}</td>'
        f'<td style="padding:8px;font-size:10px;font-weight:600;color:#1E40AF">{a.get("source_name","")}</td>'
        f'<td style="padding:8px;font-size:11px;color:#111827;line-height:1.4">{a.get("title","")[:120]}</td>'
        f'<td style="padding:8px;font-size:10px;color:#6B7280">{a.get("topic","") or ""}</td>'
        f'</tr>'
        for a in articles[:40]
    )

    # ── HTML du rapport ──────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<style>
  @page {{ size: A4; margin: 16mm 14mm; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif; color: #111827; background: white; font-size: 12px; line-height: 1.5; }}
  .header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; padding-bottom: 14px; border-bottom: 2px solid #2563EB; }}
  .logo {{ display: flex; align-items: center; gap: 8px; }}
  .logo-icon {{ width: 28px; height: 28px; background: #2563EB; border-radius: 7px; display: flex; align-items: center; justify-content: center; color: white; font-size: 14px; font-weight: 700; }}
  .logo-text {{ font-size: 15px; font-weight: 700; color: #111827; letter-spacing: -0.3px; }}
  .logo-sub {{ font-size: 9px; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.5px; }}
  .header-right {{ text-align: right; font-size: 10px; color: #6B7280; }}
  .watch-title {{ font-size: 22px; font-weight: 700; color: #111827; letter-spacing: -0.5px; margin-bottom: 4px; }}
  .watch-meta {{ font-size: 11px; color: #6B7280; margin-bottom: 20px; }}
  .watch-meta span {{ background: #F3F4F6; padding: 2px 8px; border-radius: 10px; margin-right: 6px; }}
  .metrics {{ display: flex; gap: 10px; margin-bottom: 20px; }}
  .metric {{ flex: 1; background: #F9FAFB; border-radius: 8px; padding: 12px 14px; border: 1px solid #F3F4F6; }}
  .metric-v {{ font-size: 22px; font-weight: 700; color: #111827; }}
  .metric-l {{ font-size: 10px; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.4px; margin-top: 2px; }}
  .metric-d {{ font-size: 11px; font-weight: 600; margin-top: 3px; }}
  .section {{ margin-bottom: 20px; }}
  .section-title {{ font-size: 10px; font-weight: 700; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 10px; padding-bottom: 4px; border-bottom: 1px solid #F3F4F6; }}
  .two-col {{ display: flex; gap: 16px; }}
  .col {{ flex: 1; min-width: 0; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ padding: 6px 8px; text-align: left; font-size: 9px; font-weight: 700; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.5px; background: #F9FAFB; border-bottom: 1px solid #F3F4F6; }}
  .art-table td {{ vertical-align: top; }}
  .signal-box {{ background: #EFF6FF; border: 1px solid #DBEAFE; border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; }}
  .signal-label {{ font-size: 9px; font-weight: 700; color: #2563EB; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 3px; }}
  .signal-time {{ font-size: 11px; font-weight: 600; color: #1E40AF; }}
  .signal-src {{ font-size: 10px; color: #6B7280; margin-top: 1px; }}
  .footer {{ margin-top: 20px; padding-top: 10px; border-top: 1px solid #F3F4F6; font-size: 9px; color: #9CA3AF; display: flex; justify-content: space-between; }}
</style>
</head>
<body>

<div class="header">
  <div class="logo">
    <div class="logo-icon">P</div>
    <div>
      <div class="logo-text">Prisme</div>
      <div class="logo-sub">Veille presse</div>
    </div>
  </div>
  <div class="header-right">
    Rapport généré le {now_str}<br>
    Période analysée : {period_lbl}
  </div>
</div>

<div class="watch-title">{wl_name}</div>
<div class="watch-meta">
  <span>Requête : {wl_query}</span>
  <span>Période : {period_lbl}</span>
</div>

<div class="metrics">
  <div class="metric">
    <div class="metric-v">{stats.get("total", 0)}</div>
    <div class="metric-l">Articles</div>
    <div class="metric-d" style="color:{diff_color}">{diff_str} vs période préc.</div>
  </div>
  <div class="metric">
    <div class="metric-v">{stats.get("distinct_sources", 0)}</div>
    <div class="metric-l">Médias distincts</div>
  </div>
  <div class="metric">
    <div class="metric-v">{stats.get("regions_covered", 0)}</div>
    <div class="metric-l">Régions couvertes</div>
  </div>
  <div class="metric">
    <div class="metric-v">{stats.get("distinct_source_types", 0)}</div>
    <div class="metric-l">Types de sources</div>
  </div>
</div>

<div class="section">
  <div class="section-title">Occurrences dans le temps</div>
  {timeline_svg}
</div>

<div class="two-col" style="margin-bottom:20px">
  <div class="col">
    <div class="section-title">Répartition par type</div>
    <div style="display:flex;align-items:center;gap:14px">
      {type_donut}
      <div>{donut_legend}</div>
    </div>
  </div>
  <div class="col">
    <div class="section-title">Par média</div>
    {source_bars}
  </div>
</div>

<div class="two-col" style="margin-bottom:20px">
  <div class="col">
    <div class="section-title">Mots les plus fréquents</div>
    <div>{words_html}</div>
  </div>
  <div class="col">
    <div class="section-title">Entités co-citées</div>
    <table>
      <thead><tr><th>Entité</th><th>Type</th><th style="text-align:right">Citations</th></tr></thead>
      <tbody>{ent_rows}</tbody>
    </table>
  </div>
</div>

<div class="section">
  <div class="section-title">Couverture régionale (PQR)</div>
  {region_bars}
</div>

<div class="section">
  <div class="section-title">Articles ({len(articles)} résultats)</div>
  <table class="art-table">
    <thead><tr><th style="width:70px">Heure</th><th style="width:90px">Source</th><th>Titre</th><th style="width:80px">Thème</th></tr></thead>
    <tbody>{articles_rows}</tbody>
  </table>
</div>

<div class="footer">
  <span>Prisme — Veille presse · Ministère du Travail et des Solidarités</span>
  <span>Rapport confidentiel · {now_str}</span>
</div>

</body>
</html>"""

    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html, base_url=None).write_pdf()
        return pdf_bytes
    except ImportError:
        raise ImportError("WeasyPrint non installé — pip install weasyprint")
