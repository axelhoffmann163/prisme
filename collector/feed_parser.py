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

# ── Classification thématique ─────────────────────────────────
TOPICS = {
    "Politique": [
        "gouvernement", "ministre", "président", "parlement", "assemblée",
        "sénat", "élection", "parti", "député", "macron", "premier ministre",
        "politique", "élysée", "matignon", "vote", "loi", "réforme", "décret",
        "cohabitation", "majorité", "opposition", "législatif", "exécutif",
        "municipales", "régionales", "législatives", "présidentielle", "mairie",
    ],
    "Économie": [
        "économie", "croissance", "inflation", "pib", "budget", "dette",
        "entreprise", "marché", "bourse", "cac 40", "banque", "finance",
        "investissement", "industrie", "commerce", "exportation", "importation",
        "startup", "faillite", "bénéfice", "chiffre d'affaires", "taux",
        "euro", "fiscal", "impôt", "taxe", "déficit", "recession", "relance",
        "pme", "crise économique", "consommation", "pouvoir d'achat",
    ],
    "Social": [
        "social", "syndicat", "grève", "manifestation", "retraite",
        "protection sociale", "sécurité sociale", "allocations", "rsa",
        "précarité", "pauvreté", "inégalité", "logement", "aide sociale",
        "travail", "smic", "négociation", "accord", "convention collective",
        "licenciement", "chômage", "dialogue social", "cgt", "cfdt",
        "fo", "patronat", "medef", "conditions de travail", "emploi",
    ],
    "Justice": [
        "justice", "tribunal", "procès", "jugement", "condamnation",
        "acquittement", "prison", "garde à vue", "enquête", "parquet",
        "magistrat", "avocat", "cour d'appel", "cassation", "peine",
        "crime", "délit", "police", "gendarmerie", "garde des sceaux",
        "perquisition", "arrestation", "mis en examen", "instruction",
        "verdict", "détention", "liberté conditionnelle",
    ],
    "International": [
        "international", "europe", "union européenne", "otan", "onu",
        "diplomatie", "guerre", "conflit", "russie", "ukraine", "états-unis",
        "chine", "moyen-orient", "israel", "palestine", "iran", "syrie",
        "afrique", "asie", "accord", "sommet", "ambassade", "sanctions",
        "traité", "immigration", "réfugiés", "frontière",
        "géopolitique", "brexit", "allemagne", "italie", "espagne",
    ],
    "Société": [
        "société", "éducation", "école", "université", "lycée", "collège",
        "enseignement", "étudiant", "famille", "natalité", "démographie",
        "immigration", "intégration", "racisme", "discrimination", "féminisme",
        "égalité", "laïcité", "religion", "islam", "catholicisme", "jeunesse",
        "retraité", "senior", "handicap", "violence", "insécurité",
    ],
    "Santé": [
        "santé", "maladie", "hôpital", "médecin", "vaccin", "épidémie",
        "pandémie", "cancer", "traitement", "médicament", "pharmacie",
        "chirurgie", "urgences", "soin", "patient", "infirmier",
        "psychiatrie", "obésité", "diabète", "alzheimer", "vih", "sida",
        "alcool", "tabac", "drogue", "addiction", "santé mentale",
        "covid", "grippe", "canicule", "oms",
    ],
    "Environnement": [
        "environnement", "climat", "réchauffement", "co2", "carbone",
        "écologie", "énergie", "nucléaire", "renouvelable", "solaire",
        "éolien", "biodiversité", "pollution", "déforestation", "mer",
        "océan", "sécheresse", "inondation", "catastrophe naturelle",
        "cop", "accord de paris", "transition", "électrique",
        "hydrogène", "recyclage", "déchets", "eau", "air",
    ],
    "Science & Tech": [
        "intelligence artificielle", "ia", "numérique", "technologie",
        "innovation", "recherche", "scientifique", "espace", "nasa",
        "fusée", "satellite", "robot", "algorithme", "data", "cybersécurité",
        "hacker", "5g", "quantum", "génomique", "biotechnologie",
        "découverte", "laboratoire", "smartphone", "réseaux sociaux",
        "meta", "google", "apple", "microsoft", "openai", "chatgpt",
    ],
    "Culture": [
        "culture", "cinéma", "film", "festival", "cannes", "césar",
        "musique", "concert", "album", "exposition", "musée", "art",
        "théâtre", "littérature", "livre", "roman", "prix littéraire",
        "télévision", "série", "streaming", "netflix", "média", "presse",
        "journaliste", "radio", "podcast", "patrimoine", "monument",
        "architecture", "mode", "luxe",
    ],
    "Sport": [
        "sport", "football", "psg", "ligue 1", "champions league",
        "tennis", "roland garros", "wimbledon", "rugby", "top 14",
        "cyclisme", "tour de france", "basketball", "nba", "athlétisme",
        "jeux olympiques", "jo", "coupe du monde", "euro", "formule 1",
        "natation", "handball", "boxe", "golf", "équipe de france",
        "transfert", "entraîneur", "stade", "arbitre",
    ],
    "Faits divers": [
        "accident", "incendie", "explosion", "noyade", "collision",
        "catastrophe", "tempête", "tremblement de terre", "séisme",
        "avalanche", "disparition", "enlèvement", "meurtre",
        "assassinat", "agression", "cambriolage", "hold-up", "terrorisme",
        "attentat", "fusillade", "drame", "tragédie", "victime",
        "blessé", "décès", "corps",
    ],
}

def classify_topic(title: str, summary: str = "") -> Optional[str]:
    text = (title + " " + (summary or "")).lower()
    scores = {}
    for topic, keywords in TOPICS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[topic] = score
    if not scores:
        return None
    return max(scores, key=scores.get)


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

            # Classification thématique indépendante de la catégorie source
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
