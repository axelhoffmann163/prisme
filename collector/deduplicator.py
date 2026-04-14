from collections import deque
from loguru import logger


class Deduplicator:
    def __init__(self, max_size=200000):
        self._seen = set()
        self._order = deque()
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    def is_seen(self, content_hash):
        if content_hash in self._seen:
            self._hits += 1
            return True
        self._misses += 1
        return False

    def mark_seen(self, content_hash):
        if content_hash in self._seen:
            return
        self._seen.add(content_hash)
        self._order.append(content_hash)
        if len(self._seen) > self._max_size:
            oldest = self._order.popleft()
            self._seen.discard(oldest)

    def mark_batch(self, hashes):
        for h in hashes:
            self.mark_seen(h)

    def filter_new(self, articles):
        new_articles = []
        for article in articles:
            if not self.is_seen(article.content_hash):
                new_articles.append(article)
                self.mark_seen(article.content_hash)
        return new_articles

    @property
    def stats(self):
        total = self._hits + self._misses
        rate = round(self._hits / total * 100, 1) if total else 0
        return {
            "cache_size": len(self._seen),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_pct": rate,
        }

    def log_stats(self):
        s = self.stats
        logger.info(
            f"Deduplicator — cache: {s['cache_size']:,} | "
            f"hit rate: {s['hit_rate_pct']}% "
            f"({s['hits']:,} hits / {s['misses']:,} misses)"
        )


deduplicator = Deduplicator(max_size=200000)
