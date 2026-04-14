import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from loguru import logger
from config.settings import settings

_http_cache = {}

@dataclass
class FetchResult:
    url:          str
    status_code:  int
    content:      Optional[bytes] = None
    encoding:     str = "utf-8"
    etag:         Optional[str] = None
    last_modified: Optional[str] = None
    latency_ms:   int = 0
    error:        Optional[str] = None
    not_modified: bool = False

    @property
    def ok(self):
        return self.status_code in (200, 301, 302) and self.content is not None

    @property
    def text(self):
        if self.content is None:
            return None
        return self.content.decode(self.encoding, errors="replace")


def _make_session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": settings.USER_AGENT,
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
    })
    retry_strategy = Retry(
        total=2, backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"], raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

_session = _make_session()


def fetch_feed(url):
    headers = {}
    cached = _http_cache.get(url, {})
    if cached.get("etag"):
        headers["If-None-Match"] = cached["etag"]
    if cached.get("last_modified"):
        headers["If-Modified-Since"] = cached["last_modified"]

    start = time.monotonic()
    try:
        resp = _session.get(url, headers=headers, timeout=settings.FETCH_TIMEOUT, allow_redirects=True)
        latency_ms = int((time.monotonic() - start) * 1000)

        if resp.status_code == 304:
            return FetchResult(url=url, status_code=304, latency_ms=latency_ms, not_modified=True)

        if resp.status_code not in (200, 301, 302):
            logger.warning(f"HTTP {resp.status_code} → {url}")
            return FetchResult(url=url, status_code=resp.status_code, latency_ms=latency_ms, error=f"HTTP {resp.status_code}")

        etag = resp.headers.get("ETag")
        last_modified = resp.headers.get("Last-Modified")
        if etag or last_modified:
            _http_cache[url] = {"etag": etag, "last_modified": last_modified}

        return FetchResult(
            url=url, status_code=resp.status_code,
            content=resp.content, encoding=resp.encoding or "utf-8",
            etag=etag, last_modified=last_modified, latency_ms=latency_ms,
        )

    except requests.Timeout:
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.warning(f"Timeout → {url}")
        return FetchResult(url=url, status_code=0, latency_ms=latency_ms, error="Timeout")

    except requests.ConnectionError as e:
        latency_ms = int((time.monotonic() - start) * 1000)
        domain = urlparse(url).netloc
        logger.warning(f"ConnectionError → {domain}")
        return FetchResult(url=url, status_code=0, latency_ms=latency_ms, error=str(e)[:120])

    except Exception as e:
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.error(f"Erreur → {url} : {e}")
        return FetchResult(url=url, status_code=0, latency_ms=latency_ms, error=str(e)[:120])
