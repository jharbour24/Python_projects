"""Base scraper class — wire together session, cache, rate limiter, and DB."""
import sqlite3
from datetime import datetime
from typing import Optional

from db import get_connection
from utils import HtmlCache, RateLimiter, fetch, get_logger, get_session


class BaseScraper:
    source: str = "base"

    def __init__(
        self,
        db_path=None,
        force_refresh: bool = False,
        max_age_days: Optional[int] = None,
    ):
        from config import DB_PATH, HTML_CACHE_MAX_AGE_DAYS
        self.db_path = db_path or DB_PATH
        self.force_refresh = force_refresh
        self.logger = get_logger(self.source, log_file=f"{self.source}.log")
        self.session = get_session()
        self.rate = RateLimiter()
        self.cache = HtmlCache(
            self.source,
            max_age_days=max_age_days or HTML_CACHE_MAX_AGE_DAYS,
        )
        self._run_id: Optional[int] = None

    # ── DB helpers ───────────────────────────────────────────────────────────

    def conn(self) -> sqlite3.Connection:
        return get_connection(self.db_path)

    def start_run(self) -> int:
        with self.conn() as c:
            cur = c.execute(
                "INSERT INTO scrape_runs(source) VALUES(?)", (self.source,)
            )
            self._run_id = cur.lastrowid
        return self._run_id

    def finish_run(self, added: int, updated: int, errors: int, notes: str = "") -> None:
        if self._run_id is None:
            return
        with self.conn() as c:
            c.execute(
                """UPDATE scrape_runs
                   SET finished_at=?, records_added=?, records_updated=?, errors=?, notes=?
                   WHERE run_id=?""",
                (datetime.utcnow().isoformat(), added, updated, errors, notes, self._run_id),
            )

    # ── Fetch helper ─────────────────────────────────────────────────────────

    def fetch(self, url: str, force: bool = False) -> Optional[str]:
        return fetch(
            url,
            self.session,
            self.cache,
            self.rate,
            self.logger,
            force_refresh=force or self.force_refresh,
        )
