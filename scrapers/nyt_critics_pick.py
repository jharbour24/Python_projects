"""
NYT Critics Pick scraper — v3

Strategy:
  The NYT article pages are behind a paywall (403), so we cannot check for
  the Critics Pick badge directly.  Instead we use two complementary sources:

  SOURCE 1 — NYT Spotlight page (live):
    https://www.nytimes.com/spotlight/theater-critics-picks?page=3
    Returns the 30 most-recent Critics Pick article URLs in a JSON-LD block.
    No auth required; works with cloudscraper.
    Broadway-only filter: matched show must have source_bww=1 in our DB.

  SOURCE 2 — NYT Article Search API (historical sweep):
    Search for theater reviews by year + show title.
    The API returns web_url for each article.
    We cross-reference those URLs against the known Critics Pick URL set
    collected from Source 1.

  This combination lets us:
    - Immediately flag any show whose review URL appears in the spotlight list.
    - Catch shows even if their URL is not in the current 30 by doing a
      targeted API search (matching URL slugs).

Rate limits:
  NYT Article Search API: 5 requests/minute → sleep 13s between calls.
  Spotlight page: no stated limit; we use 3s courtesy delay.
"""
import json
import re
import time
import urllib.parse
from datetime import datetime, date
from typing import Optional, Iterator, Set

import cloudscraper
from bs4 import BeautifulSoup

from config import OPENING_WINDOW_DAYS
from db import get_connection
from scrapers.base import BaseScraper
from utils import normalize_title


# ── Spotlight scraping ────────────────────────────────────────────────────────

SPOTLIGHT_URL = "https://www.nytimes.com/spotlight/theater-critics-picks?page=3"
THEATER_URL_RE = re.compile(
    r"https://www\.nytimes\.com/(\d{4})/(\d{2})/(\d{2})/theater/([^\"'\s]+\.html)"
)


def fetch_spotlight_urls(scraper: cloudscraper.CloudScraper) -> Set[str]:
    """
    Fetch the NYT Critics Picks spotlight page and return the set of
    article URLs listed there.  The page contains up to 30 of the most-recent
    Critics Picks in a JSON-LD <script> block.
    """
    urls: Set[str] = set()
    try:
        resp = scraper.get(SPOTLIGHT_URL, timeout=20)
        if resp.status_code != 200:
            return urls
        soup = BeautifulSoup(resp.text, "lxml")
        ld = soup.find("script", type="application/ld+json")
        if ld:
            data = json.loads(ld.string)
            items = data.get("mainEntity", {}).get("itemListElement", [])
            for item in items:
                url = item.get("url", "")
                if url and "nytimes.com" in url:
                    urls.add(url.rstrip("/"))
        # Also grep for any theater URLs embedded directly in the HTML
        for m in THEATER_URL_RE.finditer(resp.text):
            urls.add(m.group(0).rstrip("/"))
    except Exception:
        pass
    return urls


def url_to_slug(url: str) -> str:
    """Extract the article slug from an NYT URL for fuzzy matching."""
    m = THEATER_URL_RE.search(url)
    if m:
        return m.group(4).replace(".html", "")
    return ""


# ── Main scraper class ────────────────────────────────────────────────────────

class NYTCriticsPickScraper(BaseScraper):
    source = "nyt"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._scraper = cloudscraper.create_scraper()
        self._scraper.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nytimes.com/",
        })
        import os
        self._api_key = os.getenv("NYT_API_KEY", "")

    # ── Public entry point ────────────────────────────────────────────────────

    def run(self, start_year: int = 2010, end_year: Optional[int] = None) -> dict:
        """
        Three-pass strategy:
          Pass 1: Collect Critics Pick URLs from the live spotlight page.
          Pass 2: For every show in our DB with a NYT opening-window review,
                  search the API and check if the returned URL is a known pick.
          Pass 3: Broad year sweep to catch shows not yet matched.
        """
        self.start_run()
        end_year = end_year or datetime.now().year
        flagged = errors = 0

        # ── Pass 1: collect known Critics Pick URLs from spotlight ─────────
        self.logger.info("Pass 1: Fetching Critics Pick URLs from spotlight page...")
        time.sleep(3)
        pick_urls = fetch_spotlight_urls(self._scraper)
        self.logger.info(f"  {len(pick_urls)} Critics Pick URLs collected from spotlight")

        if pick_urls:
            # Immediately flag any shows in DB whose review URL we already know
            n = self._flag_from_url_set(pick_urls)
            flagged += n
            self.logger.info(f"  {n} shows flagged from spotlight URL set")

        # ── Pass 2: targeted show-by-show API search ──────────────────────
        if self._api_key:
            self.logger.info("Pass 2: Targeted API search for shows with NYT reviews...")
            n, e = self._pass_targeted(pick_urls)
            flagged += n; errors += e
            self.logger.info(f"  Pass 2 done: {n} flagged, {e} errors")

            # ── Pass 3: broad year sweep ──────────────────────────────────
            self.logger.info(f"Pass 3: Broad year sweep {start_year}–{end_year}...")
            for year in range(start_year, end_year + 1):
                n, e = self._sweep_year(year, pick_urls)
                flagged += n; errors += e
        else:
            self.logger.warning(
                "NYT_API_KEY not set — skipping API passes. "
                "Only spotlight-based flagging is active."
            )

        total_flagged = self._count_flagged()
        self.logger.info(
            f"NYT Critics Pick scrape done: {flagged} newly flagged, "
            f"{total_flagged} total in DB, {errors} errors"
        )
        self.finish_run(flagged, 0, errors)
        return {"flagged": flagged, "total": total_flagged, "errors": errors}

    # ── Pass 1 helper: flag shows from known URL set ──────────────────────────

    def _flag_from_url_set(self, pick_urls: Set[str]) -> int:
        """
        For each review in our DB that has a stored source_url matching a
        known Critics Pick URL, set is_nyt_critics_pick=1.
        Also attempts slug-based matching via the API search results.
        """
        flagged = 0
        # Build slug → URL map for matching
        slug_to_url = {url_to_slug(u): u for u in pick_urls if url_to_slug(u)}

        with get_connection(self.db_path) as conn:
            # Direct URL match (if reviews have source_url stored)
            for pick_url in pick_urls:
                rows = conn.execute(
                    """UPDATE reviews
                       SET is_nyt_critics_pick = 1
                       WHERE source_url = ?
                         AND is_nyt_critics_pick IS NOT 1""",
                    (pick_url,)
                )
                flagged += rows.rowcount

            # Slug match: compare article slug to normalized show title
            for slug, url in slug_to_url.items():
                # Extract date from URL
                m = THEATER_URL_RE.search(url)
                if not m:
                    continue
                pub_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
                year = int(m.group(1))

                # Find shows that opened around this date
                show_id = self._slug_match_show(conn, slug, year)
                if show_id:
                    n = self._flag_show(conn, show_id, pub_date, url)
                    flagged += n
            conn.commit()
        return flagged

    def _slug_match_show(self, conn, slug: str, year: int) -> Optional[int]:
        """
        Try to match an article URL slug to a show in the DB.
        e.g. 'hadestown-review' → show titled 'Hadestown'
        """
        from rapidfuzz import process, fuzz

        # Clean slug: remove 'review', 'broadway', dashes → spaces
        clean = re.sub(r'\b(review|broadway|musical|play)\b', '', slug)
        clean = clean.replace("-", " ").strip()
        if not clean:
            return None

        candidates = conn.execute(
            """SELECT show_id, normalized_title, opening_date
               FROM shows WHERE source_bww = 1"""
        ).fetchall()

        choices = {
            row["show_id"]: row["normalized_title"]
            for row in candidates
            if _year_matches(row["opening_date"], year, window=2)
        }
        if not choices:
            return None

        match = process.extractOne(
            normalize_title(clean), choices,
            scorer=fuzz.token_set_ratio,
            score_cutoff=75,
        )
        return match[2] if match else None

    def _flag_show(self, conn, show_id: int, pub_date: str,
                   source_url: str = "") -> int:
        """Set is_nyt_critics_pick=1 on NYT opening-window reviews for this show."""
        n = conn.execute(
            """UPDATE reviews
               SET is_nyt_critics_pick = 1,
                   source_url = COALESCE(NULLIF(?, ''), source_url)
               WHERE show_id = ?
                 AND publication_id IN (
                     SELECT publication_id FROM publications
                     WHERE normalized_name LIKE '%new york times%'
                 )
                 AND is_nyt_critics_pick IS NOT 1""",
            (source_url, show_id)
        ).rowcount

        if n == 0:
            # No existing NYT review — insert one
            from db import upsert_publication, upsert_critic
            pub_id    = upsert_publication(conn, "New York Times")
            critic_id = upsert_critic(conn, "NYT Critic", pub_id)

            open_row = conn.execute(
                "SELECT opening_date FROM shows WHERE show_id=?", (show_id,)
            ).fetchone()
            opening = open_row["opening_date"] if open_row else None
            days = None
            in_window = 0
            if opening and pub_date:
                try:
                    days = (date.fromisoformat(pub_date) - date.fromisoformat(opening)).days
                    in_window = 1 if abs(days) <= OPENING_WINDOW_DAYS else 0
                except ValueError:
                    pass

            conn.execute(
                """INSERT OR IGNORE INTO reviews
                   (show_id, critic_id, publication_id, sentiment, review_date,
                    is_opening_window, days_from_opening, is_nyt_critics_pick,
                    source, source_url)
                   VALUES (?, ?, ?, 'up', ?, ?, ?, 1, 'nyt', ?)""",
                (show_id, critic_id, pub_id, pub_date,
                 in_window, days, source_url),
            )
            n = 1
        return n

    # ── Pass 2: targeted API search ───────────────────────────────────────────

    def _pass_targeted(self, pick_urls: Set[str]) -> tuple[int, int]:
        """For each show with a NYT review, search the API and check the URL."""
        with get_connection(self.db_path) as conn:
            shows = conn.execute(
                """SELECT DISTINCT s.show_id, s.title, s.opening_date
                   FROM shows s
                   JOIN reviews r ON r.show_id = s.show_id
                   JOIN publications p ON p.publication_id = r.publication_id
                   WHERE p.normalized_name LIKE '%new york times%'
                     AND r.is_opening_window = 1
                     AND (r.is_nyt_critics_pick IS NULL OR r.is_nyt_critics_pick = 0)
                     AND s.source_bww = 1
                   ORDER BY s.opening_date"""
            ).fetchall()

        self.logger.info(f"  {len(shows)} shows to check via API")
        flagged = errors = 0

        for show in shows:
            title   = show["title"]
            opening = show["opening_date"]
            year    = int(opening[:4]) if opening and len(opening) >= 4 else None
            if not year:
                continue

            for article in self._search_nyt_for_show(title, opening):
                article_url = article.get("url", "").rstrip("/")
                if article_url in pick_urls:
                    with get_connection(self.db_path) as conn:
                        n = self._flag_show(conn, show["show_id"],
                                            article.get("pub_date", ""),
                                            article_url)
                        conn.commit()
                    flagged += n
                    break  # found it, move on

        return flagged, errors

    # ── Pass 3: broad year sweep ──────────────────────────────────────────────

    def _sweep_year(self, year: int, pick_urls: Set[str]) -> tuple[int, int]:
        """Search all theater reviews for a year; flag any whose URL is a known pick."""
        flagged = errors = 0
        for article in self._search_theater_reviews(year):
            article_url = article.get("url", "").rstrip("/")
            if article_url in pick_urls:
                with get_connection(self.db_path) as conn:
                    show_id = self._find_show(conn, article)
                    if show_id:
                        n = self._flag_show(conn, show_id,
                                            article.get("pub_date", ""),
                                            article_url)
                        conn.commit()
                        flagged += n
        return flagged, errors

    # ── NYT Article Search API ────────────────────────────────────────────────

    def _search_nyt_for_show(self, title: str, opening_date: Optional[str]) -> Iterator[dict]:
        """Search the API for a specific show title near its opening date."""
        if not self._api_key:
            return
        year = int(opening_date[:4]) if opening_date and len(opening_date) >= 4 else None
        if not year:
            return

        q = re.sub(r"[\"']", "", title)[:60]
        params = {
            "q": q,
            "begin_date": f"{year}0101",
            "end_date":   f"{year + 1}0630",
            "api-key":    self._api_key,
        }
        url = ("https://api.nytimes.com/svc/search/v2/articlesearch.json?"
               + urllib.parse.urlencode(params))
        time.sleep(13)
        try:
            resp = self._scraper.get(url, timeout=20)
            if resp.status_code == 429:
                self.logger.warning("Rate limited — waiting 60s")
                time.sleep(60)
                resp = self._scraper.get(url, timeout=20)
            resp.raise_for_status()
            docs = (resp.json().get("response") or {}).get("docs") or []
        except Exception as e:
            self.logger.warning(f"API error for '{title}': {e}")
            return

        for doc in docs:
            if (doc.get("section_name") == "Theater"
                    and doc.get("type_of_material") == "Review"):
                yield {
                    "title":    doc.get("headline", {}).get("main", ""),
                    "pub_date": doc.get("pub_date", "")[:10],
                    "url":      doc.get("web_url", ""),
                    "critic":   _extract_nyt_byline(doc.get("byline", {}).get("original", "")),
                }

    def _search_theater_reviews(self, year: int) -> Iterator[dict]:
        """Broad sweep: search 'theater review' for a given year."""
        if not self._api_key:
            return
        page = 0
        while page <= 2:
            params = {
                "q":          "theater review",
                "begin_date": f"{year}0101",
                "end_date":   f"{year}1231",
                "sort":       "oldest",
                "page":       page,
                "api-key":    self._api_key,
            }
            url = ("https://api.nytimes.com/svc/search/v2/articlesearch.json?"
                   + urllib.parse.urlencode(params))
            time.sleep(13)
            try:
                resp = self._scraper.get(url, timeout=20)
                if resp.status_code == 429:
                    time.sleep(60)
                    resp = self._scraper.get(url, timeout=20)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                self.logger.warning(f"API error year={year} page={page}: {e}")
                break
            docs = (data.get("response") or {}).get("docs") or []
            if not docs:
                break
            for doc in docs:
                if (doc.get("section_name") == "Theater"
                        and doc.get("type_of_material") == "Review"):
                    yield {
                        "title":    doc.get("headline", {}).get("main", ""),
                        "pub_date": doc.get("pub_date", "")[:10],
                        "url":      doc.get("web_url", ""),
                        "critic":   _extract_nyt_byline(doc.get("byline", {}).get("original", "")),
                    }
            meta = (data.get("response") or {}).get("metadata") or {}
            if (page + 1) * 10 >= meta.get("hits", 0):
                break
            page += 1

    # ── DB helpers ────────────────────────────────────────────────────────────

    def _find_show(self, conn, article: dict) -> Optional[int]:
        """Fuzzy-match article headline to a show in the DB."""
        from rapidfuzz import process, fuzz

        title    = article.get("title", "")
        pub_date = article.get("pub_date", "")
        year     = int(pub_date[:4]) if pub_date and len(pub_date) >= 4 else None

        norm = normalize_title(title)
        candidates = conn.execute(
            "SELECT show_id, normalized_title, opening_date FROM shows WHERE source_bww=1"
        ).fetchall()
        choices = {
            row["show_id"]: row["normalized_title"]
            for row in candidates
            if not year or _year_matches(row["opening_date"], year)
        }
        if not choices:
            return None
        match = process.extractOne(
            norm, choices, scorer=fuzz.token_set_ratio, score_cutoff=80
        )
        return match[2] if match else None

    def _count_flagged(self) -> int:
        with get_connection(self.db_path) as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM reviews WHERE is_nyt_critics_pick=1"
            ).fetchone()[0]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_nyt_byline(byline: str) -> str:
    return re.sub(r"^[Bb]y\s+", "", byline).strip() or "NYT Critic"


def _year_matches(opening_date: Optional[str], pub_year: int, window: int = 1) -> bool:
    if not opening_date:
        return True
    try:
        return abs(int(opening_date[:4]) - pub_year) <= window
    except (ValueError, TypeError):
        return True
