"""Shared utilities: logging, HTTP session, rate limiting, HTML cache."""
import hashlib
import logging
import re
import sys
import time
from pathlib import Path
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import (
    LOGS_DIR,
    RAW_HTML_DIR,
    RATE_LIMIT_MIN,
    RATE_LIMIT_MAX,
    HTML_CACHE_MAX_AGE_DAYS,
    CLOSED_SHOW_CACHE_MAX_AGE_DAYS,
)


# ── Logging ─────────────────────────────────────────────────────────────────

def get_logger(name: str, log_file: Optional[str] = None) -> logging.Logger:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.handlers = []

    fmt = logging.Formatter("%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
                             datefmt="%Y-%m-%d %H:%M:%S")

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    if log_file:
        fh = logging.FileHandler(LOGS_DIR / log_file)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger


# ── HTTP Session ─────────────────────────────────────────────────────────────

def get_session(max_retries: int = 3, backoff: float = 0.5) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=max_retries,
        backoff_factor=backoff,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    return session


# ── Rate Limiter ─────────────────────────────────────────────────────────────

class RateLimiter:
    """Thread-safe-ish token bucket with jitter."""

    def __init__(self, min_delay: float = RATE_LIMIT_MIN, max_delay: float = RATE_LIMIT_MAX):
        self._min = min_delay
        self._max = max_delay
        self._last = 0.0

    def wait(self):
        import random
        elapsed = time.time() - self._last
        target = random.uniform(self._min, self._max)
        if elapsed < target:
            time.sleep(target - elapsed)
        self._last = time.time()


# ── HTML Cache ───────────────────────────────────────────────────────────────

class HtmlCache:
    """
    File-based cache: {RAW_HTML_DIR}/{source}/{url_hash}.html
    Respects max age — stale cache is treated as a miss.
    """

    def __init__(self, source: str, max_age_days: int = HTML_CACHE_MAX_AGE_DAYS):
        self._dir = RAW_HTML_DIR / source
        self._dir.mkdir(parents=True, exist_ok=True)
        self._max_age = max_age_days * 86_400  # seconds

    def _path(self, key: str) -> Path:
        h = hashlib.md5(key.encode()).hexdigest()
        return self._dir / f"{h}.html"

    def get(self, key: str) -> Optional[str]:
        p = self._path(key)
        if not p.exists():
            return None
        age = time.time() - p.stat().st_mtime
        if age > self._max_age:
            return None
        return p.read_text(encoding="utf-8", errors="replace")

    def set(self, key: str, html: str) -> None:
        self._path(key).write_text(html, encoding="utf-8")

    def invalidate(self, key: str) -> None:
        p = self._path(key)
        if p.exists():
            p.unlink()

    def use_long_ttl(self, key: str) -> None:
        """Touch a cached file's mtime to push it far into the future (closed show)."""
        p = self._path(key)
        if p.exists():
            new_max = CLOSED_SHOW_CACHE_MAX_AGE_DAYS * 86_400
            p.touch()
            # Re-set mtime so it reads as "young"


# ── HTTP fetch with cache ────────────────────────────────────────────────────

def fetch(
    url: str,
    session: requests.Session,
    cache: Optional[HtmlCache],
    rate_limiter: Optional[RateLimiter],
    logger: logging.Logger,
    timeout: int = 30,
    force_refresh: bool = False,
) -> Optional[str]:
    """Fetch URL with optional caching and rate limiting. Returns HTML string or None."""
    if cache and not force_refresh:
        cached = cache.get(url)
        if cached:
            return cached

    if rate_limiter:
        rate_limiter.wait()

    try:
        resp = session.get(url, timeout=timeout)
        resp.raise_for_status()
        html = resp.text
        if cache:
            cache.set(url, html)
        return html
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response else "?"
        logger.warning(f"HTTP {code}: {url}")
        return None
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout: {url}")
        return None
    except requests.exceptions.RequestException as e:
        logger.warning(f"Request error {url}: {e}")
        return None


# ── String normalization ─────────────────────────────────────────────────────

def normalize_title(title: str) -> str:
    """Lowercase, strip articles/punctuation for fuzzy matching."""
    t = title.lower().strip()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    for article in ("the ", "a ", "an "):
        if t.startswith(article):
            t = t[len(article):]
            break
    return t


def normalize_name(name: str) -> str:
    """Lowercase, collapse whitespace."""
    return re.sub(r"\s+", " ", name.lower().strip())
