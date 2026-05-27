"""
NYT Critics Pick Spotlight Scraper — Playwright version

Uses a real headless Chromium browser to load and scroll the NYT Critics Pick
spotlight page, intercepting every GraphQL batch as the page loads more items.

Requires:
  - playwright installed:  python3 -m playwright install chromium
  - NYT-S session cookie:  export NYT_S_COOKIE="<your NYT-S cookie value>"
    (Get it: Log in to nytimes.com → DevTools → Application → Cookies → NYT-S)

What this does:
  1. Loads https://www.nytimes.com/spotlight/theater-critics-picks in headless Chrome
  2. Scrolls to the bottom repeatedly, intercepting GraphQL responses (10 items/batch)
  3. Collects all Critics Pick article URLs
  4. Saves them to data/nyt_critics_pick_urls.txt  (one URL per line)
  5. Matches each URL to a Broadway show in the DB (source_bww=1 only)
  6. Sets is_nyt_critics_pick=1 on the matching NYT review row

Run via:
  python3 __main__.py scrape nyt-spotlight
  or standalone:
  python3 scrapers/nyt_spotlight_scraper.py
"""
import os
import re
import time
import json
from pathlib import Path
from typing import Set

from config import DB_PATH
from db import get_connection, upsert_publication, upsert_critic
from utils import normalize_title
from config import OPENING_WINDOW_DAYS
from datetime import date

THEATER_URL_RE = re.compile(
    r"https://www\.nytimes\.com/\d{4}/\d{2}/\d{2}/theater/[^\s\"'<>]+\.html"
)
SPOTLIGHT_URL = "https://www.nytimes.com/spotlight/theater-critics-picks"
CACHE_FILE    = Path(__file__).parent.parent / "data" / "nyt_critics_pick_urls.txt"


# ── URL collection via Playwright ─────────────────────────────────────────────

def collect_all_pick_urls(nyt_s_cookie: str,
                          max_stalls: int = 5,
                          scroll_pause_ms: int = 2500,
                          verbose: bool = True) -> Set[str]:
    """
    Scroll the NYT Critics Picks spotlight page in headless Chrome, intercepting
    every GraphQL batch response to collect all Critics Pick article URLs.

    Returns a set of fully-qualified nytimes.com article URLs.
    """
    from playwright.sync_api import sync_playwright

    all_urls: Set[str] = set()

    def find_urls_in_obj(obj) -> Set[str]:
        found: Set[str] = set()
        if isinstance(obj, dict):
            u = obj.get("url", "")
            if isinstance(u, str) and "nytimes.com" in u and "/theater/" in u and u.endswith(".html"):
                found.add(u.rstrip("/"))
            for v in obj.values():
                found |= find_urls_in_obj(v)
        elif isinstance(obj, list):
            for item in obj:
                found |= find_urls_in_obj(item)
        return found

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        )
        context.add_cookies([{
            "name": "NYT-S", "value": nyt_s_cookie,
            "domain": ".nytimes.com", "path": "/",
            "httpOnly": False, "secure": True, "sameSite": "None",
        }])

        page = context.new_page()

        def on_response(response):
            if "samizdat-graphql" not in response.url:
                return
            try:
                urls = find_urls_in_obj(response.json())
                new = urls - all_urls
                if new:
                    all_urls.update(new)
                    if verbose:
                        print(f"  +{len(new):3d} new  (total={len(all_urls)})")
            except Exception:
                pass

        page.on("response", on_response)

        if verbose:
            print(f"Loading {SPOTLIGHT_URL} ...")
        page.goto(SPOTLIGHT_URL, timeout=30000)
        page.wait_for_timeout(4000)

        stall_count  = 0
        scroll_count = 0
        prev_count   = -1

        while stall_count < max_stalls:
            scroll_count += 1
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(scroll_pause_ms)

            if len(all_urls) == prev_count:
                stall_count += 1
                if verbose:
                    print(f"  Scroll {scroll_count:3d}: {len(all_urls)} total  (stall {stall_count}/{max_stalls})")
            else:
                stall_count = 0
                prev_count  = len(all_urls)
                if verbose and scroll_count % 10 == 0:
                    print(f"  Scroll {scroll_count:3d}: {len(all_urls)} total")

        browser.close()

    return all_urls


# ── Cache helpers ─────────────────────────────────────────────────────────────

def load_cached_urls() -> Set[str]:
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            return {line.strip() for line in f if line.strip()}
    return set()


def save_cached_urls(urls: Set[str]) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        for u in sorted(urls):
            f.write(u + "\n")


# ── DB matching & flagging ────────────────────────────────────────────────────

def _best_match(query: str, choices: dict, pub_year: int, all_shows_by_id: dict,
                score_cutoff: int = 72):
    """
    Fuzzy-match query against choices, breaking score ties by:
      1. Preferring the show whose opening_date is closest to pub_year
      2. Then preferring the show with the longer normalized_title (more specific)
    """
    from rapidfuzz import process, fuzz

    results = process.extract(
        query, choices,
        scorer=fuzz.token_set_ratio,
        limit=10,
        score_cutoff=score_cutoff,
    )
    if not results:
        return None

    top_score = results[0][1]
    # All matches with the top score
    tied = [(name, score, sid) for name, score, sid in results if score >= top_score - 0.01]

    if len(tied) == 1:
        return tied[0]

    # Tie-break 1: prefer show whose opening year is closest to pub_year
    def year_dist(sid):
        od = all_shows_by_id.get(sid, {}).get("opening_date", "")
        try:
            return abs(int(str(od)[:4]) - pub_year)
        except (ValueError, TypeError):
            return 99

    # Tie-break 2: prefer longer (more specific) title
    def title_len(sid):
        return len(all_shows_by_id.get(sid, {}).get("normalized_title", ""))

    best = min(tied, key=lambda t: (year_dist(t[2]), -title_len(t[2])))
    return best


def match_urls_to_db(pick_urls: Set[str], verbose: bool = True) -> dict:
    """
    For each Critics Pick URL:
      1. Extract slug and date
      2. Fuzzy-match to a Broadway show (source_bww=1, year ±3)
      3. Set is_nyt_critics_pick=1 on the matching NYT review row

    Returns {"flagged": n, "no_match": n, "already_set": n}
    """
    flagged    = 0
    no_match   = 0
    already    = 0
    slug_re    = re.compile(
        r"https://www\.nytimes\.com/(\d{4})/(\d{2})/(\d{2})/theater/([^/]+)\.html"
    )

    with get_connection(DB_PATH) as conn:
        # Load all BWW-matched shows once
        all_shows = conn.execute(
            "SELECT show_id, title, normalized_title, opening_date "
            "FROM shows WHERE source_bww=1"
        ).fetchall()
        all_shows_by_id = {row["show_id"]: dict(row) for row in all_shows}

        for url in pick_urls:
            m = slug_re.match(url.rstrip("/"))
            if not m:
                continue
            year, month, day, slug = m.groups()
            pub_date = f"{year}-{month}-{day}"
            pub_year = int(year)

            # Build clean search term from URL slug.
            # Truncate at "-review-" first: slugs like
            #   "sweeney-todd-broadway-review-josh-groban" include actor/director
            #   names after "review" that dilute fuzzy match scores.
            if "-review-" in slug:
                slug = slug[:slug.index("-review-")]
            elif slug.endswith("-review"):
                slug = slug[:-7]
            clean = re.sub(r"\b(review|broadway|musical|play|theater|theatre)\b", "", slug)
            clean = clean.replace("-", " ").strip()
            if not clean:
                continue

            # Filter candidates to ±3 years of pub_date (wider window handles
            # shows like Hadestown where Off-Broadway → Broadway spans years)
            choices = {
                row["show_id"]: row["normalized_title"]
                for row in all_shows
                if _year_matches(row["opening_date"], pub_year, window=3)
            }
            if not choices:
                no_match += 1
                continue

            match = _best_match(
                normalize_title(clean), choices,
                pub_year=pub_year,
                all_shows_by_id=all_shows_by_id,
                score_cutoff=72,
            )
            if not match:
                no_match += 1
                continue

            show_id = match[2]

            # Check / update existing NYT review
            n = conn.execute(
                """UPDATE reviews
                   SET is_nyt_critics_pick = 1,
                       source_url = COALESCE(NULLIF(?, ''), source_url)
                   WHERE show_id = ?
                     AND publication_id IN (
                         SELECT publication_id FROM publications
                         WHERE normalized_name LIKE '%new york times%'
                     )
                     AND (is_nyt_critics_pick IS NULL OR is_nyt_critics_pick = 0)""",
                (url, show_id)
            ).rowcount

            if n > 0:
                flagged += n
            else:
                # Either already flagged or no NYT review row yet
                existing = conn.execute(
                    """SELECT r.is_nyt_critics_pick FROM reviews r
                       JOIN publications p ON p.publication_id = r.publication_id
                       WHERE r.show_id=? AND p.normalized_name LIKE '%new york times%'""",
                    (show_id,)
                ).fetchone()

                if existing and existing["is_nyt_critics_pick"] == 1:
                    already += 1
                else:
                    # Insert a stub NYT review row with the Critics Pick flag
                    pub_id    = upsert_publication(conn, "New York Times")
                    critic_id = upsert_critic(conn, "NYT Critic", pub_id)
                    open_row  = conn.execute(
                        "SELECT opening_date FROM shows WHERE show_id=?", (show_id,)
                    ).fetchone()
                    opening   = open_row["opening_date"] if open_row else None
                    days      = None
                    in_window = 0
                    if opening and pub_date:
                        try:
                            days = (
                                date.fromisoformat(pub_date) - date.fromisoformat(opening)
                            ).days
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
                         in_window, days, url),
                    )
                    flagged += 1

        conn.commit()

    return {"flagged": flagged, "no_match": no_match, "already_set": already}


# ── Main entry point ──────────────────────────────────────────────────────────

def run(force_rescrape: bool = False, verbose: bool = True) -> dict:
    """
    Full pipeline:
      1. Load cached URLs from disk (if any)
      2. Scrape spotlight page via Playwright (if no cache or force)
      3. Save new URLs to cache
      4. Match URLs to DB shows and flag is_nyt_critics_pick
    """
    nyt_s = os.getenv("NYT_S_COOKIE", "")
    if not nyt_s:
        print("ERROR: NYT_S_COOKIE not set.")
        print("  Log in to nytimes.com → DevTools → Application → Cookies → copy NYT-S value")
        print("  Then: export NYT_S_COOKIE='<value>'")
        return {"error": "NYT_S_COOKIE not set"}

    # Load cached URLs
    cached = load_cached_urls()
    if verbose and cached:
        print(f"Loaded {len(cached)} cached Critics Pick URLs from disk")

    if force_rescrape or not cached:
        if verbose:
            print("Scraping spotlight page (this takes ~10 minutes for the full archive)...")
        scraped = collect_all_pick_urls(nyt_s, verbose=verbose)
        new_urls = scraped - cached
        all_urls = cached | scraped
        if verbose:
            print(f"\nScraped {len(scraped)} URLs  ({len(new_urls)} new vs cache)")
        save_cached_urls(all_urls)
        if verbose:
            print(f"Saved {len(all_urls)} URLs to {CACHE_FILE}")
    else:
        all_urls = cached

    # Match to DB
    if verbose:
        print(f"\nMatching {len(all_urls)} Critics Pick URLs to Broadway shows...")
    result = match_urls_to_db(all_urls, verbose=verbose)
    total_flagged = 0
    with get_connection(DB_PATH) as conn:
        total_flagged = conn.execute(
            "SELECT COUNT(*) FROM reviews WHERE is_nyt_critics_pick=1"
        ).fetchone()[0]

    result["total_in_db"] = total_flagged
    if verbose:
        print(f"\nDone: {result['flagged']} newly flagged  |  "
              f"{result['no_match']} unmatched  |  "
              f"{result['already_set']} already set  |  "
              f"{total_flagged} total Critics Picks in DB")
    return result


def _year_matches(opening_date, pub_year: int, window: int = 2) -> bool:
    if not opening_date:
        return True
    try:
        return abs(int(str(opening_date)[:4]) - pub_year) <= window
    except (ValueError, TypeError):
        return True


if __name__ == "__main__":
    run(force_rescrape=True, verbose=True)
