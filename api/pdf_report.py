import re
from collections import Counter
from datetime import datetime, timezone, timedelta

from database.connection import get_conn
from api.watchlist import get_watchlist_stats, get_watchlist_articles

STOPWORDS = {
    "le","la","les","un","une","des","de","du","en","et","est","au","aux",
    "ce","qui","que","se","sa","son","ses","sur","par","pour","dans","avec",
    "à","il","elle","ils","elles","on","nous","vous","je","tu","l","d","s",
    "plus","très","aussi","mais","ou","donc","or","ni","car","ne","pas","tout",
    "cette","ces","leur","leurs","avoir","être","fait","faire","bien","même",
    "après","avant","entre","selon","dont","lors","comme","contre","depuis",
    "sans","sous","chez","via","face","alors","ainsi","quand","cela","celui",
}

ENTITY_DB = {
    "CFDT":["Organisation"],"CGT":["Organisation"],"FO":["Organisation"],
    "CFE-CGC":["Organisation"],"CFTC":["Organisation"],"UNSA":["Organisation"],
    "MEDEF":["Organisation"],"CPME":["Organisation"],
    "Renaissance":["Organisation"],"RN":["Organisation"],"LFI":["Organisation"],
    "PS":["Organisation"],"LR":["Organisation"],"EELV":["Organisation"],
    "PCF":["Organisation"],"MoDem":["Organisation"],
    "Sénat":["Institution"],"Matignon":["Institution"],"Élysée":["Institution"],
    "Bercy":["Institution"],"Assemblée nationale":["Institution"],
    "SNCF":["Entreprise"],"RATP":["Entreprise"],"EDF":["Entreprise"],
    "Renault":["Entreprise"],"Michelin":["Entreprise"],"Air France":["Entreprise"],
    "TotalEnergies":["Entreprise"],"Orange":["Entreprise"],
    "Macron":["Personne"],"Emmanuel Macron":["Personne"],
    "François Bayrou":["Personne"],"Bayrou":["Personne"],
    "Marine Le Pen":["Personne"],"Jean-Luc Mélenchon":["Personne"],
    "Gabriel Attal":["Personne"],"Bruno Le Maire":["Personne"],
    "Sébastien Lecornu":["Personne"],"Michel Barnier":["Personne"],
    "Paris":["Lieu"],"Lyon":["Lieu"],"Marseille":["Lieu"],
    "Bruxelles":["Lieu"],"Berlin":["Lieu"],"Washington":["Lieu"],
    "Ukraine":["Lieu"],"Gaza":["Lieu"],
}


def _ago(dt) -> str:
    if not dt:
        return ""
    if hasattr(dt, "tzinfo") and dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    s = (datetime.now(timezone.utc) - dt).total_seconds()
    if s < 60: return "à l'instant"
    if s < 3600: return f"il y a {int(s/60)} min"
    if s < 86400: return f"il y a {int(s/3600)}h"
    return f"il y a {int(s/86400)}j"


def _build_entities(articles):
    counts, types = {}, {}
    all_text = " ".join((a.get("title") or "") + " " + (a.get("summary") or "") for a in articles)
    for name, (etype,) in ENTITY_DB.items():
        pat = re.compile(r'\b' + re.escape(name) + r'\b', re.IGNORECASE)
        n = len(pat.findall(all_text))
        if n >= 2:
            counts[name] = n
            types[name] = etype
    return sorted([{"name": n, "count": c, "type": types[n]} for n, c in counts.items()], key=lambda x: -x["count"])[:8]


def _top_words(articles):
    text = " ".join((a.get("title") or "") + " " + (a.get("summary") or "") for a in articles).lower()
    words = re.findall(r'\b[a-zàâäéèêëîïôùûüÿœæç]{4,}\b', text)
    wc = Counter(w for w in words if w not in STOPWORDS)
    return [{"word": w, "count": c} for w, c in wc.most_common(15)]


def _timeline_svg(timeline, timeline_prev, hours, bucket_min, width=520, height=90):
    if not timeline or all(t["count"] == 0 for t in timeline):
        return f'<svg width="{width}" height="30"><text x="10" y="20" font-family="Helvetica,sans-serif" font-size="11" fill="#9CA3AF">Pas de données pour cette période</text></svg>'

    n = len(timeline)
    max_val = max(
        max(t["count"] for t in timeline),
        max((t["count"] for t in timeline_prev), default=0),
        1
    )
    pad_l, pad_r, pad_t, pad_b = 32, 12, 8, 22

    # Calcul des points
    def pts(data):
        result = []
        for i, t in enumerate(data):
            x = pad_l + i * (width - pad_l - pad_r) / max(n - 1, 1)
            y = pad_t + (1 - t["count"] / max_val) * (height - pad_t - pad_b)
            result.append((x, y))
        return result

    def path_d(points):
        if len(points) < 2:
            return ""
        # Courbe de Bézier lissée
        d = f"M {points[0][0]:.1f},{points[0][1]:.1f}"
        for i in range(1, len(points)):
            px, py = points[i - 1]
            cx, cy = points[i]
            mx = (px + cx) / 2
            d += f" C {mx:.1f},{py:.1f} {mx:.1f},{cy:.1f} {cx:.1f},{cy:.1f}"
        return d

    # Labels axe X — heures réelles
    now = datetime.now()
    label_step = max(1, n // 6)
    x_labels = []
    for i, _ in enumerate(timeline):
        if i % label_step == 0 or i == n - 1:
            ms_ago = (n - 1 - i) * bucket_min * 60 * 1000
            dt = datetime.fromtimestamp((now.timestamp() * 1000 - ms_ago) / 1000)
            if hours <= 24:
                lbl = dt.strftime("%H:%M")
            elif hours <= 72:
                lbl = dt.strftime("%a %Hh")
            else:
                lbl = dt.strftime("%d/%m")
            x = pad_l + i * (width - pad_l - pad_r) / max(n - 1, 1)
            x_labels.append((x, lbl))

    # Labels axe Y
    y_labels = []
    for v in [0, max_val // 2, max_val]:
        y = pad_t + (1 - v / max_val) * (height - pad_t - pad_b)
        y_labels.append((y, str(int(v))))

    current_pts = pts(timeline)
    prev_pts = pts(timeline_prev) if timeline_prev else []

    # Zone de remplissage sous la courbe actuelle
    area_d = path_d(current_pts)
    if area_d:
        area_d += f" L {current_pts[-1][0]:.1f},{height - pad_b} L {current_pts[0][0]:.1f},{height - pad_b} Z"

    svg = [f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">']

    # Grille horizontale
    for y, lbl in y_labels:
        svg.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{width - pad_r}" y2="{y:.1f}" stroke="#F3F4F6" stroke-width="1"/>')
        svg.append(f'<text x="{pad_l - 4}" y="{y + 3:.1f}" text-anchor="end" font-family="Helvetica,sans-serif" font-size="8" fill="#9CA3AF">{lbl}</text>')

    # Ligne de base
    svg.append(f'<line x1="{pad_l}" y1="{height - pad_b}" x2="{width - pad_r}" y2="{height - pad_b}" stroke="#E5E7EB" stroke-width="1"/>')

    # Labels axe X
    for x, lbl in x_labels:
        svg.append(f'<text x="{x:.1f}" y="{height - 4}" text-anchor="middle" font-family="Helvetica,sans-serif" font-size="8" fill="#9CA3AF">{lbl}</text>')

    # Aire
    if area_d:
        svg.append(f'<path d="{area_d}" fill="#DBEAFE" opacity="0.4"/>')

    # Courbe précédente (pointillée)
    if prev_pts:
        prev_d = path_d(prev_pts)
        if prev_d:
            svg.append(f'<path d="{prev_d}" fill="none" stroke="#D1D5DB" stroke-width="1.2" stroke-dasharray="3,3"/>')

    # Courbe actuelle
    curr_d = path_d(current_pts)
    if curr_d:
        svg.append(f'<path d="{curr_d}" fill="none" stroke="#2563EB" stroke-width="2"/>')

    svg.append('</svg>')
    return "".join(svg)


def _donut_svg(by_type, size=110):
    COLORS = {"PQN": "#2563EB", "PQR": "#059669", "TV": "#C2410C",
              "Radio": "#9333EA", "Magazine": "#0369A1", "Agence": "#BE123C",
              "Natif": "#065F46", "International": "#475569"}
    import math
    total = sum(by_type.values())
    if not total:
        return ""
    cx = cy = size / 2
    r_out, r_in = size / 2 - 4, size / 4
    angle = -math.pi / 2
    paths = []
    for cat, val in sorted(by_type.items(), key=lambda x: -x[1]):
        sweep = 2 * math.pi * val / total
        x1o = cx + r_out * math.cos(angle); y1o = cy + r_out * math.sin(angle)
        x1i = cx + r_in * math.cos(angle);  y1i = cy + r_in * math.sin(angle)
        angle += sweep
        x2o = cx + r_out * math.cos(angle); y2o = cy + r_out * math.sin(angle)
        x2i = cx + r_in * math.cos(angle);  y2i = cy + r_in * math.sin(angle)
        large = 1 if sweep > math.pi else 0
        color = COLORS.get(cat, "#888")
        d = (f"M{x1o:.2f},{y1o:.2f} A{r_out},{r_out} 0 {large},1 {x2o:.2f},{y2o:.2f} "
             f"L{x2i:.2f},{y2i:.2f} A{r_in},{r_in} 0 {large},0 {x1i:.2f},{y1i:.2f} Z")
        paths.append(f'<path d="{d}" fill="{color}"/>')
    return f'<svg width="{size}" height="{size}" xmlns="http://www.w3.org/2000/svg">{"".join(paths)}</svg>'


def _hbars_svg(data, color="#2563EB", width=260, max_label=16):
    entries = sorted(data.items(), key=lambda x: -x[1])[:8]
    if not entries:
        return '<p style="font-size:11px;color:#9CA3AF">Pas de données</p>'
    max_v = entries[0][1] or 1
    bar_h = 14
    gap = 6
    label_w = 100
    rows = []
    for i, (name, val) in enumerate(entries):
        y = i * (bar_h + gap)
        bw = max(2, int((val / max_v) * (width - label_w - 30)))
        short = name[:max_label] + "…" if len(name) > max_label else name
        rows.append(
            f'<text x="{label_w - 5}" y="{y + bar_h - 2}" text-anchor="end" '
            f'font-family="Helvetica,sans-serif" font-size="9.5" fill="#6B7280">{short}</text>'
            f'<rect x="{label_w}" y="{y + 1}" width="{bw}" height="{bar_h - 2}" rx="2" fill="{color}" opacity="0.85"/>'
            f'<text x="{label_w + bw + 4}" y="{y + bar_h - 2}" font-family="Helvetica,sans-serif" '
            f'font-size="9.5" fill="#374151">{val}</text>'
        )
    total_h = len(entries) * (bar_h + gap)
    return f'<svg width="{width}" height="{total_h}" xmlns="http://www.w3.org/2000/svg">{"".join(rows)}</svg>'


def generate_watchlist_pdf(watchlist_id: int, hours: int = 24) -> bytes:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, query FROM watchlists WHERE id = %s", (watchlist_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Veille {watchlist_id} introuvable")
            wl_id, wl_name, wl_query = row

    stats = get_watchlist_stats(watchlist_id, hours=hours)
    arts_data = get_watchlist_articles(watchlist_id, limit=50)
    articles = arts_data.get("articles", [])

    entities = _build_entities(articles)
    top_words = _top_words(articles)

    now_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
    period_lbl = f"{hours}h" if hours <= 24 else f"{hours // 24} jours"

    diff = stats.get("total", 0) - stats.get("total_prev", 0)
    diff_str = (f"+{diff}" if diff > 0 else str(diff)) + " vs période préc."
    diff_color = "#059669" if diff > 0 else ("#DC2626" if diff < 0 else "#9CA3AF")

    TYPE_COLORS = {"PQN": "#2563EB", "PQR": "#059669", "TV": "#C2410C",
                   "Radio": "#9333EA", "Magazine": "#0369A1", "Agence": "#BE123C"}

    timeline_svg = _timeline_svg(
        stats.get("timeline", []), stats.get("timeline_prev", []),
        hours, stats.get("timeline_bucket_minutes", 60)
    )
    donut_svg = _donut_svg(stats.get("by_type", {}))
    source_bars = _hbars_svg(stats.get("by_source", {}), "#2563EB")
    region_bars = _hbars_svg(
        {r["region"]: r["count"] for r in stats.get("regional_coverage", [])},
        "#15803D"
    )

    # Légende donut inline
    donut_legend_rows = "".join(
        f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:5px">'
        f'<div style="width:10px;height:10px;border-radius:2px;background:{TYPE_COLORS.get(t,"#888")};flex-shrink:0"></div>'
        f'<span style="font-size:10px;color:#374151;font-weight:500">{t}</span>'
        f'<span style="font-size:10px;color:#9CA3AF;margin-left:auto">{c}</span>'
        f'</div>'
        for t, c in sorted(stats.get("by_type", {}).items(), key=lambda x: -x[1])
    )

    # Entités
    ent_rows = "".join(
        f'<tr style="border-bottom:1px solid #F9FAFB">'
        f'<td style="padding:6px 10px;font-size:10.5px;font-weight:500;color:#111827">{e["name"]}</td>'
        f'<td style="padding:6px 10px;font-size:10px;color:#6B7280">{e["type"]}</td>'
        f'<td style="padding:6px 10px;text-align:right;font-size:11px;font-weight:700;color:#111827">{e["count"]}</td>'
        f'</tr>'
        for e in entities
    ) or f'<tr><td colspan="3" style="padding:10px;font-size:10.5px;color:#9CA3AF;text-align:center">Pas assez de données</td></tr>'

    # Mots fréquents
    max_wc = top_words[0]["count"] if top_words else 1
    words_html = "".join(
        f'<span style="display:inline-block;margin:2px 3px;padding:4px 9px;border-radius:20px;'
        f'border:1px solid #E5E7EB;font-size:{9 + round(w["count"]/max_wc * 3)}px;'
        f'color:#374151;background:#F9FAFB;font-family:Helvetica,sans-serif">'
        f'{w["word"]} <span style="color:#9CA3AF;font-size:8px">{w["count"]}</span></span>'
        for w in top_words
    )

    # Premier signal / dernière mention
    sorted_arts = sorted(articles, key=lambda a: a.get("collected_at") or "")
    first = sorted_arts[0] if sorted_arts else None
    last = sorted_arts[-1] if sorted_arts else None

    def signal_box(label, article):
        if not article:
            return f'<div style="background:#F9FAFB;border-radius:6px;padding:8px 10px"><div style="font-size:9px;font-weight:700;color:#9CA3AF;text-transform:uppercase;letter-spacing:.5px;margin-bottom:3px">{label}</div><div style="font-size:10.5px;color:#9CA3AF">—</div></div>'
        return (
            f'<div style="background:#EFF6FF;border:1px solid #DBEAFE;border-radius:6px;padding:8px 10px">'
            f'<div style="font-size:9px;font-weight:700;color:#1D4ED8;text-transform:uppercase;letter-spacing:.5px;margin-bottom:3px">{label}</div>'
            f'<div style="font-size:11px;font-weight:600;color:#1E40AF">{_ago(article.get("collected_at"))}</div>'
            f'<div style="font-size:9.5px;color:#6B7280;margin-top:2px;line-height:1.3">'
            f'{article.get("source_name","")} · {(article.get("title") or "")[:70]}…</div>'
            f'</div>'
        )

    # Articles
    badge_colors = {
        "PQN": ("#EFF6FF","#1D4ED8"), "PQR": ("#F0FDF4","#15803D"),
        "TV": ("#FFF7ED","#C2410C"), "Radio": ("#FDF4FF","#9333EA"),
        "Magazine": ("#F0F9FF","#0369A1"), "Agence": ("#FFF1F2","#BE123C"),
    }
    art_rows = ""
    for a in articles[:50]:
        cat = a.get("source_category") or a.get("category") or "PQN"
        bg, fg = badge_colors.get(cat, ("#F3F4F6","#374151"))
        topic = a.get("topic") or ""
        art_rows += (
            f'<tr style="border-bottom:1px solid #F9FAFB;page-break-inside:avoid">'
            f'<td style="padding:7px 8px;font-size:9.5px;color:#6B7280;white-space:nowrap;vertical-align:top">{_ago(a.get("collected_at"))}</td>'
            f'<td style="padding:7px 8px;vertical-align:top">'
            f'<span style="background:{bg};color:{fg};font-size:8.5px;font-weight:700;padding:2px 6px;border-radius:4px;text-transform:uppercase">{cat}</span>'
            f'<br><span style="font-size:9.5px;font-weight:600;color:#374151">{a.get("source_name","")}</span>'
            f'</td>'
            f'<td style="padding:7px 8px;font-size:10px;color:#111827;line-height:1.45;vertical-align:top">{(a.get("title") or "")[:130]}</td>'
            f'<td style="padding:7px 8px;font-size:9px;color:#6B7280;vertical-align:top;white-space:nowrap">{topic}</td>'
            f'</tr>'
        )

    html = f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8">
<style>
@page {{ size: A4; margin: 14mm 14mm 12mm; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: Helvetica, Arial, sans-serif; color: #111827; background: white; font-size: 11px; line-height: 1.5; }}
</style>
</head><body>

<!-- EN-TÊTE -->
<table width="100%" style="border-bottom:2px solid #2563EB;padding-bottom:10px;margin-bottom:16px">
  <tr>
    <td width="50%">
      <table><tr>
        <td style="background:#2563EB;width:26px;height:26px;border-radius:6px;text-align:center;vertical-align:middle">
          <span style="color:white;font-size:14px;font-weight:900">P</span>
        </td>
        <td style="padding-left:8px">
          <div style="font-size:15px;font-weight:700;color:#111827;letter-spacing:-0.3px">Prisme</div>
          <div style="font-size:8.5px;color:#9CA3AF;text-transform:uppercase;letter-spacing:.5px">Veille presse</div>
        </td>
      </tr></table>
    </td>
    <td style="text-align:right;font-size:9.5px;color:#6B7280;vertical-align:bottom">
      Rapport généré le {now_str}<br>
      Ministère du Travail et des Solidarités
    </td>
  </tr>
</table>

<!-- TITRE VEILLE -->
<div style="margin-bottom:14px">
  <div style="font-size:21px;font-weight:700;color:#111827;letter-spacing:-0.5px;margin-bottom:5px">{wl_name}</div>
  <div style="display:inline-flex;gap:8px">
    <span style="background:#F3F4F6;color:#374151;font-size:10px;padding:3px 10px;border-radius:10px">Requête : {wl_query}</span>
    <span style="background:#EFF6FF;color:#1D4ED8;font-size:10px;padding:3px 10px;border-radius:10px">Période : {period_lbl}</span>
  </div>
</div>

<!-- MÉTRIQUES -->
<table width="100%" style="border-collapse:separate;border-spacing:8px 0;margin-bottom:16px">
  <tr>
    <td style="background:#F9FAFB;border:1px solid #F3F4F6;border-radius:8px;padding:12px 14px;width:25%">
      <div style="font-size:26px;font-weight:700;color:#111827">{stats.get("total",0)}</div>
      <div style="font-size:9px;color:#9CA3AF;text-transform:uppercase;letter-spacing:.5px;margin-top:1px">Articles</div>
      <div style="font-size:10px;font-weight:600;color:{diff_color};margin-top:3px">{diff_str}</div>
    </td>
    <td style="background:#F9FAFB;border:1px solid #F3F4F6;border-radius:8px;padding:12px 14px;width:25%">
      <div style="font-size:26px;font-weight:700;color:#111827">{stats.get("distinct_sources",0)}</div>
      <div style="font-size:9px;color:#9CA3AF;text-transform:uppercase;letter-spacing:.5px;margin-top:1px">Médias distincts</div>
    </td>
    <td style="background:#EFF6FF;border:1px solid #DBEAFE;border-radius:8px;padding:12px 14px;width:25%">
      <div style="font-size:9px;font-weight:700;color:#1D4ED8;text-transform:uppercase;letter-spacing:.5px;margin-bottom:3px">Premier signal</div>
      <div style="font-size:10.5px;font-weight:600;color:#1E40AF">{_ago(first.get("collected_at")) if first else "—"}</div>
      <div style="font-size:8.5px;color:#6B7280;margin-top:2px;line-height:1.3">{(first.get("source_name","") + " · " + (first.get("title") or "")[:45] + "…") if first else ""}</div>
    </td>
    <td style="background:#EFF6FF;border:1px solid #DBEAFE;border-radius:8px;padding:12px 14px;width:25%">
      <div style="font-size:9px;font-weight:700;color:#1D4ED8;text-transform:uppercase;letter-spacing:.5px;margin-bottom:3px">Dernière mention</div>
      <div style="font-size:10.5px;font-weight:600;color:#1E40AF">{_ago(last.get("collected_at")) if last else "—"}</div>
      <div style="font-size:8.5px;color:#6B7280;margin-top:2px;line-height:1.3">{(last.get("source_name","") + " · " + (last.get("title") or "")[:45] + "…") if last else ""}</div>
    </td>
  </tr>
</table>

<!-- TIMELINE -->
<div style="background:white;border:1px solid #F3F4F6;border-radius:8px;padding:12px 14px;margin-bottom:12px">
  <div style="font-size:9px;font-weight:700;color:#9CA3AF;text-transform:uppercase;letter-spacing:.6px;margin-bottom:10px">
    Occurrences dans le temps
    <span style="font-weight:400;margin-left:10px">— — — Période précédente</span>
  </div>
  {timeline_svg}
</div>

<!-- RÉPARTITION + MÉDIAS -->
<table width="100%" style="border-collapse:separate;border-spacing:8px 0;margin-bottom:12px">
  <tr valign="top">
    <td width="40%" style="background:white;border:1px solid #F3F4F6;border-radius:8px;padding:12px 14px">
      <div style="font-size:9px;font-weight:700;color:#9CA3AF;text-transform:uppercase;letter-spacing:.6px;margin-bottom:10px">Répartition par type</div>
      <table><tr>
        <td style="padding-right:14px">{donut_svg}</td>
        <td style="vertical-align:middle">{donut_legend_rows}</td>
      </tr></table>
    </td>
    <td width="60%" style="background:white;border:1px solid #F3F4F6;border-radius:8px;padding:12px 14px">
      <div style="font-size:9px;font-weight:700;color:#9CA3AF;text-transform:uppercase;letter-spacing:.6px;margin-bottom:10px">Par média</div>
      {source_bars}
    </td>
  </tr>
</table>

<!-- MOTS + ENTITÉS -->
<table width="100%" style="border-collapse:separate;border-spacing:8px 0;margin-bottom:12px">
  <tr valign="top">
    <td width="55%" style="background:white;border:1px solid #F3F4F6;border-radius:8px;padding:12px 14px">
      <div style="font-size:9px;font-weight:700;color:#9CA3AF;text-transform:uppercase;letter-spacing:.6px;margin-bottom:8px">Mots les plus fréquents</div>
      {words_html}
    </td>
    <td width="45%" style="background:white;border:1px solid #F3F4F6;border-radius:8px;padding:12px 14px">
      <div style="font-size:9px;font-weight:700;color:#9CA3AF;text-transform:uppercase;letter-spacing:.6px;margin-bottom:8px">Entités co-citées</div>
      <table width="100%" style="border-collapse:collapse">
        <thead>
          <tr style="border-bottom:1px solid #F3F4F6">
            <th style="text-align:left;font-size:8.5px;font-weight:700;color:#9CA3AF;text-transform:uppercase;padding:0 10px 6px">Entité</th>
            <th style="text-align:left;font-size:8.5px;font-weight:700;color:#9CA3AF;text-transform:uppercase;padding:0 10px 6px">Type</th>
            <th style="text-align:right;font-size:8.5px;font-weight:700;color:#9CA3AF;text-transform:uppercase;padding:0 10px 6px">Cit.</th>
          </tr>
        </thead>
        <tbody>{ent_rows}</tbody>
      </table>
    </td>
  </tr>
</table>

<!-- COUVERTURE RÉGIONALE -->
<div style="background:white;border:1px solid #F3F4F6;border-radius:8px;padding:12px 14px;margin-bottom:12px">
  <div style="font-size:9px;font-weight:700;color:#9CA3AF;text-transform:uppercase;letter-spacing:.6px;margin-bottom:10px">Couverture régionale (PQR)</div>
  {region_bars if stats.get("regional_coverage") else '<p style="font-size:10.5px;color:#9CA3AF">Aucune source PQR pour cette veille</p>'}
</div>

<!-- ARTICLES -->
<div style="background:white;border:1px solid #F3F4F6;border-radius:8px;padding:12px 14px">
  <div style="font-size:9px;font-weight:700;color:#9CA3AF;text-transform:uppercase;letter-spacing:.6px;margin-bottom:10px">Articles · {len(articles)} résultats</div>
  <table width="100%" style="border-collapse:collapse">
    <thead>
      <tr style="border-bottom:1px solid #E5E7EB;background:#F9FAFB">
        <th style="text-align:left;font-size:8.5px;font-weight:700;color:#9CA3AF;text-transform:uppercase;padding:6px 8px;width:60px">Heure</th>
        <th style="text-align:left;font-size:8.5px;font-weight:700;color:#9CA3AF;text-transform:uppercase;padding:6px 8px;width:90px">Source</th>
        <th style="text-align:left;font-size:8.5px;font-weight:700;color:#9CA3AF;text-transform:uppercase;padding:6px 8px">Titre</th>
        <th style="text-align:left;font-size:8.5px;font-weight:700;color:#9CA3AF;text-transform:uppercase;padding:6px 8px;width:70px">Thème</th>
      </tr>
    </thead>
    <tbody>{art_rows}</tbody>
  </table>
</div>

<!-- PIED DE PAGE -->
<div style="margin-top:14px;padding-top:8px;border-top:1px solid #F3F4F6;display:flex;justify-content:space-between;font-size:8.5px;color:#9CA3AF">
  <span>Prisme · Veille presse · Ministère du Travail et des Solidarités</span>
  <span>Rapport confidentiel · {now_str}</span>
</div>

</body></html>"""

    try:
        from weasyprint import HTML
        return HTML(string=html, base_url=None).write_pdf()
    except ImportError:
        raise ImportError("WeasyPrint non installé")
