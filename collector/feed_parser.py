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


def parse_feed(result, source_id, feed_id, category, tags):
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

            articles.append(ArticleRecord(
                source_id=source_id, feed_id=feed_id,
                content_hash=content_hash, guid=guid[:500] if guid else None,
                url=url[:1000], title=title[:500], summary=summary,
                full_text=None, author=author or None,
                image_url=image_url[:500] if image_url else None,
                category=category, tags=all_tags[:20],
                language="fr", published_at=published_at,
            ))
        except Exception as e:
            logger.warning(f"Erreur parsing entrée → {result.url} : {e}")
            continue

    return articles
