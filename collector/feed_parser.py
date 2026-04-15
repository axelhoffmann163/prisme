import re
import hashlib
from datetime import datetime, timezone
from typing import Optional
from email.utils import parsedate_to_datetime

import feedparser
from bs4 import BeautifulSoup
from loguru import logger

from collector.feed_fetcher import FetchResult
from database.repository import ArticleRecord

_WHITESPACE_RE = re.compile(r"\s+")
_ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\ufeff]")

# ── Classification thématique pondérée ────────────────────────
# Format : { "mot-clé": poids }
# Poids 3 = très discriminant, 2 = discriminant, 1 = contextuel
TOPICS = {
    "Politique": {
        "élysée": 3, "matignon": 3, "assemblée nationale": 3, "sénat": 3,
        "premier ministre": 3, "macron": 3, "gouvernement": 2, "ministre": 2,
        "élection": 2, "législative": 2, "présidentielle": 2, "parti politique": 2,
        "opposition": 2, "majorité": 2, "motion de censure": 3, "dissolution": 3,
        "référendum": 3, "cohabitation": 3, "conseil des ministres": 3,
        "député": 2, "sénateur": 2, "vote": 1, "loi": 1, "décret": 1,
        "politique": 1, "réforme": 1, "discours": 1, "campagne": 1,
    },
    "Économie": {
        "bourse": 3, "cac 40": 3, "dow jones": 3, "nasdaq": 3, "action": 2,
        "banque centrale": 3, "taux directeur": 3, "inflation": 2, "récession": 3,
        "pib": 3, "croissance économique": 3, "faillite": 3, "liquidation": 3,
        "fusion-acquisition": 3, "ipo": 3, "chiffre d'affaires": 3, "bénéfice net": 3,
        "dette publique": 3, "déficit budgétaire": 3, "budget": 2, "impôt": 2,
        "taxe": 2, "pouvoir d'achat": 2, "commerce extérieur": 2, "exportation": 2,
        "investissement": 2, "startup": 2, "entreprise": 1, "économie": 1,
        "marché": 1, "industrie": 1, "emploi": 1, "salaire": 1,
    },
    "Social": {
        "grève": 3, "syndicat": 3, "cgt": 3, "cfdt": 3, "fo ": 3, "cfe-cgc": 3,
        "préavis de grève": 3, "manifestation sociale": 3, "retraite": 3,
        "âge de départ": 3, "pension": 2, "smic": 3, "salaire minimum": 3,
        "licenciement": 3, "plan social": 3, "chômage partiel": 3,
        "protection sociale": 3, "sécurité sociale": 3, "allocations": 2,
        "rsa": 3, "pauvreté": 2, "inégalité": 2, "précarité": 2,
        "convention collective": 3, "dialogue social": 3, "négociation salariale": 3,
        "conditions de travail": 2, "burn-out": 2, "télétravail": 2,
        "logement social": 2, "sans-abri": 2, "aide sociale": 2,
    },
    "Justice": {
        "tribunal": 3, "cour d'appel": 3, "cour de cassation": 3,
        "conseil d'état": 3, "cour pénale": 3, "procès": 3, "jugement": 3,
        "condamnation": 3, "acquittement": 3, "mis en examen": 3,
        "garde à vue": 3, "perquisition": 3, "mandat d'arrêt": 3,
        "instruction judiciaire": 3, "parquet": 3, "procureur": 3,
        "avocat": 2, "peine de prison": 3, "détention provisoire": 3,
        "liberté conditionnelle": 3, "appel": 2, "plainte": 2,
        "enquête judiciaire": 3, "crime": 2, "délit": 2, "police": 1,
        "gendarmerie": 1, "garde des sceaux": 3, "justice": 1,
    },
    "International": {
        "guerre en ukraine": 3, "conflit armé": 3, "cessez-le-feu": 3,
        "diplomatie": 3, "sommet": 2, "g7": 3, "g20": 3, "otan": 3,
        "onu": 3, "union européenne": 3, "commission européenne": 3,
        "sanctions internationales": 3, "traité": 2, "ambassade": 2,
        "coup d'état": 3, "élection présidentielle": 2, "kremlin": 3,
        "maison blanche": 3, "trump": 2, "biden": 2, "xi jinping": 3,
        "poutine": 3, "moyen-orient": 3, "gaza": 3, "israel": 2,
        "ukraine": 2, "russie": 2, "chine": 2, "géopolitique": 3,
        "migration": 2, "réfugiés": 2, "frontière": 1,
    },
    "Société": {
        "éducation nationale": 3, "baccalauréat": 3, "parcoursup": 3,
        "université": 2, "lycée": 2, "collège": 2, "école primaire": 2,
        "enseignant": 2, "professeur": 2, "natalité": 3, "démographie": 3,
        "immigration": 2, "intégration": 2, "racisme": 3, "antisémitisme": 3,
        "islamophobie": 3, "discrimination": 2, "féminisme": 2,
        "violences conjugales": 3, "lgbt": 3, "laïcité": 3,
        "religion": 2, "culte": 2, "jeunesse": 2, "retraité": 2,
        "handicap": 2, "exclusion sociale": 2, "société": 1,
    },
    "Santé": {
        "hôpital": 2, "chu": 3, "urgences": 2, "médecin généraliste": 3,
        "désert médical": 3, "cancer": 2, "tumor": 2, "chimiothérapie": 3,
        "vaccin": 3, "vaccination": 3, "épidémie": 3, "pandémie": 3,
        "covid": 3, "virus": 2, "bactérie": 2, "antibiotique": 2,
        "médicament": 2, "remboursement": 2, "sécurité sanitaire": 3,
        "oms": 3, "haute autorité de santé": 3, "has": 2,
        "santé mentale": 3, "dépression": 2, "anxiété": 2,
        "addiction": 2, "alcool": 2, "tabac": 2, "drogue": 2,
        "canicule": 3, "pollution": 2, "santé": 1,
    },
    "Environnement": {
        "réchauffement climatique": 3, "changement climatique": 3,
        "cop28": 3, "cop29": 3, "cop30": 3, "accord de paris": 3,
        "gaz à effet de serre": 3, "co2": 3, "empreinte carbone": 3,
        "transition énergétique": 3, "énergie renouvelable": 3,
        "solaire": 2, "éolien": 2, "hydraulique": 2, "nucléaire": 2,
        "biodiversité": 3, "extinction": 2, "déforestation": 3,
        "océan": 2, "pollution": 2, "plastique": 2, "recyclage": 2,
        "sécheresse": 3, "inondation": 3, "feux de forêt": 3,
        "écologie": 2, "vert": 1, "environnement": 1,
    },
    "Science & Tech": {
        "intelligence artificielle": 3, "ia générative": 3, "chatgpt": 3,
        "openai": 3, "anthropic": 3, "mistral": 3, "llm": 3,
        "deepfake": 3, "algorithme": 2, "données personnelles": 2,
        "cybersécurité": 3, "piratage": 3, "ransomware": 3,
        "fusée": 3, "satellite": 3, "iss": 3, "nasa": 3, "esa": 3,
        "découverte scientifique": 3, "génomique": 3, "adn": 2,
        "recherche médicale": 2, "physique quantique": 3,
        "5g": 3, "métavers": 3, "blockchain": 3, "cryptomonnaie": 3,
        "smartphone": 2, "apple": 2, "google": 2, "meta": 2, "microsoft": 2,
        "technologie": 1, "numérique": 1, "innovation": 1,
    },
    "Culture": {
        "festival de cannes": 3, "palme d'or": 3, "césar": 3, "molière": 3,
        "prix goncourt": 3, "prix renaudot": 3, "prix médicis": 3,
        "exposition": 2, "musée": 2, "galerie": 2, "patrimoine": 2,
        "concert": 2, "tournée": 2, "album": 2, "single": 2,
        "film": 2, "cinéma": 2, "série": 2, "streaming": 2,
        "roman": 2, "livre": 1, "auteur": 1, "théâtre": 2,
        "opéra": 2, "danse": 2, "art contemporain": 2,
        "audiences tv": 2, "tmc": 2, "tf1": 1, "france 2": 1,
        "culture": 1, "artiste": 1, "spectacle": 1,
    },
    "Sport": {
        "ligue 1": 3, "ligue 2": 3, "champions league": 3, "europa league": 3,
        "coupe de france": 3, "coupe du monde": 3, "euro 2024": 3,
        "ballon d'or": 3, "transfert": 3, "mercato": 3,
        "psg": 3, "om": 3, "ol": 3, "asse": 3, "ogcn": 2,
        "mbappé": 3, "benzema": 3, "griezmann": 3,
        "roland garros": 3, "wimbledon": 3, "us open": 3, "open d'australie": 3,
        "tour de france": 3, "tour d'espagne": 3,
        "jeux olympiques": 3, "jo 2024": 3, "jo paris": 3,
        "top 14": 3, "rugby": 2, "xv de france": 3,
        "formule 1": 3, "grand prix": 2, "verstappen": 3, "leclerc": 3,
        "nba": 3, "basketball": 2, "handball": 2, "natation": 2,
        "athlétisme": 2, "boxe": 2, "mma": 2, "ufc": 3,
        "match": 2, "but": 1, "victoire": 1, "défaite": 1, "score": 2,
        "entraîneur": 2, "sélectionneur": 2, "stade": 1, "sport": 1,
    },
    "Faits divers": {
        "accident de la route": 3, "carambolage": 3, "collision frontale": 3,
        "incendie criminel": 3, "explosion": 3, "effondrement": 3,
        "noyade": 3, "disparition inquiétante": 3, "corps retrouvé": 3,
        "meurtre": 3, "homicide": 3, "féminicide": 3, "viol": 3,
        "agression": 2, "coups et blessures": 3, "cambriolage": 3,
        "hold-up": 3, "braquage": 3, "prise d'otage": 3,
        "attentat": 3, "terrorisme": 3, "fusillade": 3,
        "tremblement de terre": 3, "séisme": 3, "tsunami": 3,
        "avalanche": 3, "tempête": 2, "inondation": 2,
        "victimes": 2, "blessés": 2, "drame": 2, "tragédie": 2,
    },
}

def classify_topic(title: str, summary: str = "") -> Optional[str]:
    """Classification pondérée : titre compte 3x plus que le résumé."""
    title_lower = title.lower()
    summary_lower = (summary or "").lower()
    scores = {}
    for topic, keywords in TOPICS.items():
        score = 0
        for kw, weight in keywords.items():
            if kw in title_lower:
                score += weight * 3  # titre = poids x3
            if kw in summary_lower:
                score += weight      # résumé = poids normal
        if score > 0:
            scores[topic] = score
    if not scores:
        return None
    # Retourne le topic avec le score le plus élevé
    best = max(scores, key=scores.get)
    # Seuil minimum : score >= 3 pour éviter les faux positifs
    return best if scores[best] >= 3 else None


def strip_html(text):
    if not text:
        return None
    soup = BeautifulSoup(text, "lxml")
    clean = soup.get_text(separator=" ")
    clean = _ZERO_WIDTH_RE.sub("", clean)
    clean = _WHITESPACE_RE.sub(" ", clean).strip()
    return clean or None


def truncate(text, max_chars=800):
    if not text or len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "\u2026"


def compute_hash(title, url):
    normalized = re.sub(r"\s+", " ", title.lower().strip()) + "|" + url.lower().strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]


def parse_date(entry):
    if entry.get("published_parsed"):
        try:
            import calendar
            ts = calendar.timegm(entry.published_parsed)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            pass
    if entry.get("updated_parsed"):
        try:
            import calendar
            ts = calendar.timegm(entry.updated_parsed)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            pass
    published_str = entry.get("published") or entry.get("updated")
    if published_str:
        try:
            return parsedate_to_datetime(published_str).astimezone(timezone.utc)
        except Exception:
            pass
    return None


def extract_image(entry):
    for media in entry.get("media_content", []):
        if media.get("url", "").endswith((".jpg", ".jpeg", ".png", ".webp")):
            return media.get("url")
    for enc in entry.get("enclosures", []):
        if enc.get("type", "").startswith("image/"):
            return enc.get("href") or enc.get("url")
    if entry.get("media_thumbnail"):
        return entry["media_thumbnail"][0].get("url")
    content = (
        entry.get("content", [{}])[0].get("value")
        or entry.get("summary", "")
    )
    if content:
        soup = BeautifulSoup(content, "lxml")
        img = soup.find("img")
        if img and img.get("src"):
            return img["src"]
    return None


def parse_feed(result, source_id, feed_id, source_category, tags):
    if not result.ok or not result.content:
        return []

    parsed = feedparser.parse(result.content)

    if parsed.bozo and not parsed.entries:
        logger.warning(f"Feed invalide → {result.url} : {getattr(parsed, 'bozo_exception', 'unknown')}")
        return []

    articles = []
    for entry in parsed.entries:
        try:
            url = entry.get("link") or entry.get("id") or ""
            if not url or not url.startswith("http"):
                continue

            title_raw = entry.get("title") or ""
            title = strip_html(title_raw) or ""
            if not title:
                continue

            summary_raw = (
                entry.get("summary")
                or (entry.get("content", [{}])[0].get("value") if entry.get("content") else None)
                or ""
            )
            summary = truncate(strip_html(summary_raw))
            author = strip_html(entry.get("author") or "")
            if author:
                author = author[:200]
            rss_tags = [t.get("term", "") for t in entry.get("tags", [])]
            all_tags = list(set(tags + [t for t in rss_tags if t]))
            content_hash = compute_hash(title, url)
            published_at = parse_date(entry)
            image_url = extract_image(entry)
            guid = entry.get("id") or url

            topic = classify_topic(title, summary or "")

            articles.append(ArticleRecord(
                source_id=source_id,
                feed_id=feed_id,
                content_hash=content_hash,
                guid=guid[:500] if guid else None,
                url=url[:1000],
                title=title[:500],
                summary=summary,
                full_text=None,
                author=author or None,
                image_url=image_url[:500] if image_url else None,
                category=source_category,
                topic=topic,
                tags=all_tags[:20],
                language="fr",
                published_at=published_at,
            ))
        except Exception as e:
            logger.warning(f"Erreur parsing entrée → {result.url} : {e}")
            continue

    return articles
