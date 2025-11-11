"""
Base scraper utilities for Broadway data pipeline.
Provides caching, rate limiting, and common HTTP utilities.
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import random


class BaseScraper:
    """Base class for all scrapers with caching and rate limiting."""

    def __init__(
        self,
        cache_dir: Path,
        rate_limit: float = 1.0,
        cache_expiry_days: int = 7,
        user_agents: Optional[list] = None,
    ):
        """
        Initialize base scraper.

        Args:
            cache_dir: Directory for caching raw responses
            rate_limit: Minimum seconds between requests
            cache_expiry_days: Days before cache entries expire
            user_agents: List of user agent strings to rotate
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limit = rate_limit
        self.cache_expiry_days = cache_expiry_days
        self.last_request_time = 0.0

        self.user_agents = user_agents or [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]

        self.session = requests.Session()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Generate cache file path from cache key."""
        cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
        return self.cache_dir / f"{cache_hash}.json"

    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cache file exists and is not expired."""
        if not cache_path.exists():
            return False

        cache_age = datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)
        return cache_age < timedelta(days=self.cache_expiry_days)

    def _read_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Read data from cache if valid."""
        cache_path = self._get_cache_path(cache_key)

        if not self._is_cache_valid(cache_path):
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def _write_cache(self, cache_key: str, data: Dict[str, Any]) -> None:
        """Write data to cache."""
        cache_path = self._get_cache_path(cache_key)

        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _rate_limit_wait(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request_time = time.time()

    def _get_random_user_agent(self) -> str:
        """Return a random user agent string."""
        return random.choice(self.user_agents)

    def fetch_url(
        self,
        url: str,
        cache_key: Optional[str] = None,
        force_refresh: bool = False,
        headers: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        """
        Fetch URL with caching and rate limiting.

        Args:
            url: URL to fetch
            cache_key: Key for caching (defaults to URL)
            force_refresh: Skip cache and fetch fresh data
            headers: Additional headers to include

        Returns:
            HTML content or None if fetch fails
        """
        cache_key = cache_key or url

        # Check cache unless forcing refresh
        if not force_refresh:
            cached = self._read_cache(cache_key)
            if cached is not None:
                return cached.get("html")

        # Enforce rate limiting
        self._rate_limit_wait()

        # Prepare headers
        request_headers = {"User-Agent": self._get_random_user_agent()}
        if headers:
            request_headers.update(headers)

        try:
            response = self.session.get(url, headers=request_headers, timeout=30)
            response.raise_for_status()

            # Cache the response
            self._write_cache(
                cache_key,
                {
                    "url": url,
                    "html": response.text,
                    "status_code": response.status_code,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            return response.text

        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None

    def fetch_json(
        self,
        url: str,
        cache_key: Optional[str] = None,
        force_refresh: bool = False,
        headers: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch JSON endpoint with caching and rate limiting.

        Args:
            url: URL to fetch
            cache_key: Key for caching (defaults to URL)
            force_refresh: Skip cache and fetch fresh data
            headers: Additional headers to include

        Returns:
            Parsed JSON data or None if fetch fails
        """
        cache_key = cache_key or url

        # Check cache unless forcing refresh
        if not force_refresh:
            cached = self._read_cache(cache_key)
            if cached is not None:
                return cached.get("data")

        # Enforce rate limiting
        self._rate_limit_wait()

        # Prepare headers
        request_headers = {
            "User-Agent": self._get_random_user_agent(),
            "Accept": "application/json",
        }
        if headers:
            request_headers.update(headers)

        try:
            response = self.session.get(url, headers=request_headers, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Cache the response
            self._write_cache(
                cache_key,
                {
                    "url": url,
                    "data": data,
                    "status_code": response.status_code,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            return data

        except (requests.RequestException, json.JSONDecodeError) as e:
            print(f"Error fetching JSON from {url}: {e}")
            return None

    def parse_html(self, html: str) -> Optional[BeautifulSoup]:
        """Parse HTML content with BeautifulSoup."""
        try:
            return BeautifulSoup(html, "html.parser")
        except Exception as e:
            print(f"Error parsing HTML: {e}")
            return None


def load_config(config_path: Path = Path("config/shows.yaml")) -> Dict[str, Any]:
    """Load shows configuration from YAML file."""
    import yaml

    with open(config_path, "r") as f:
        return yaml.safe_load(f)
