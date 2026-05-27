#!/usr/bin/env python3
"""
Off-Broadway-aware NYT Critics Pick matcher.

The existing nyt_critics_pick.py scraper deliberately filters matches to
Broadway-only shows (`source_bww = 1`). This script lifts that restriction
and matches the existing seed URL list (data/nyt_critics_pick_urls.txt)
against the full shows table — Broadway *and* Off-Broadway.

Workflow
--------
  1. Optionally refresh the seed URL list from the live spotlight page.
  2. Parse every URL → (pub_date, slug).
  3. For each URL, look up candidate shows opening within ±90 days of the
     review date. Score candidates by (a) dtli_slug similarity and (b)
     normalized-title token-set ratio. Accept the best match above
     SCORE_CUTOFF.
  4. For each matched show, set `is_nyt_critics_pick = 1` on any existing
     NYT opening-window review row, or insert a new NYT review row tagged
     as CP if none exists.
  5. Print a per-year diff (how many *new* OB shows were flagged in each
     year).
"""

from __future__ import annotations

import re
import sqlite3
import sys
import time
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cloudscraper
from bs4 import BeautifulSoup
from rapidfuzz import fuzz

DB_PATH      = ROOT / "data" / "critics_impact.db"
URLS_FILE    = ROOT / "data" / "nyt_critics_pick_urls.txt"
SPOTLIGHT_URL = "https://www.nytimes.com/spotlight/theater-critics-picks"
DATE_WINDOW_DAYS = 90      # review can be ±90 days from official opening
SCORE_CUTOFF     = 75      # fuzzy-match cutoff

THEATER_URL_RE = re.compile(
    r"https://www\.nytimes\.com/(\d{4})/(\d{2})/(\d{2})/theater/([^\"'\s]+\.html)"
)

# -----------------------------------------------------------------------------
# (Optional) spotlight refresh
# -----------------------------------------------------------------------------
def refresh_spotlight(existing: set[str]) -> set[str]:
    """Try to fetch fresh CP URLs from the live spotlight page (~30 most recent).
    Falls back to existing if request fails."""
    scraper = cloudscraper.create_scraper()
    scraper.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nytimes.com/",
    })
    new = set()
    for page in range(1, 6):           # first 5 pages (~150 most recent picks)
        url = f"{SPOTLIGHT_URL}?page={page}"
        try:
            time.sleep(2)
            r = scraper.get(url, timeout=20)
            if r.status_code != 200:
                print(f"  page {page}: HTTP {r.status_code}")
                continue
            soup = BeautifulSoup(r.text, "lxml")
            # JSON-LD payload
            for ld in soup.find_all("script", type="application/ld+json"):
                try:
                    import json
                    data = json.loads(ld.string or "{}")
                    items = (data.get("mainEntity") or {}).get("itemListElement", [])
                    for it in items:
                        u = (it.get("url") or "").rstrip("/")
                        if u and "nytimes.com" in u: new.add(u)
                except Exception:
                    continue
            # Raw URL grep as backup
            for m in THEATER_URL_RE.finditer(r.text):
                new.add(m.group(0).rstrip("/"))
        except Exception as e:
            print(f"  page {page}: error {e}")
    fresh = new - existing
    print(f"  Spotlight returned {len(new)} URLs ({len(fresh)} new vs. seed file)")
    return new


# -----------------------------------------------------------------------------
# Slug → show matcher
# -----------------------------------------------------------------------------
def normalize_slug(s: str) -> str:
    s = re.sub(r"\b(review|reviews|broadway|off-broadway|musical|play|critics|pick)\b", "", s.lower())
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s


def fetch_candidates(conn, year: int) -> list[dict]:
    """Pull shows whose opening_date is plausibly within ±a few years of the review."""
    start = f"{year-1}-01-01"
    end   = f"{year+1}-12-31"
    cur = conn.execute(
        """SELECT show_id, title, normalized_title, dtli_slug, opening_date, show_type, source_bww
           FROM shows
           WHERE opening_date BETWEEN ? AND ?""",
        (start, end))
    return [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]


def best_match(url_slug: str, pub_date: datetime, candidates: list[dict]) -> Optional[dict]:
    """Pick the highest-scoring candidate, respecting the date window."""
    if not candidates: return None
    cleaned = normalize_slug(url_slug)
    if not cleaned: return None
    best = None; best_score = 0
    for c in candidates:
        if not c["opening_date"]: continue
        try:
            opening = datetime.strptime(c["opening_date"][:10], "%Y-%m-%d")
        except Exception:
            continue
        if abs((pub_date - opening).days) > DATE_WINDOW_DAYS: continue
        # score against dtli_slug
        slug_score  = fuzz.token_set_ratio(cleaned, normalize_slug(c["dtli_slug"] or "")) if c["dtli_slug"] else 0
        title_score = fuzz.token_set_ratio(cleaned, normalize_slug(c["normalized_title"] or "")) if c["normalized_title"] else 0
        score = max(slug_score, title_score)
        if score > best_score:
            best_score = score; best = c
    if best_score >= SCORE_CUTOFF:
        best["match_score"] = best_score
        return best
    return None


# -----------------------------------------------------------------------------
# Flag insertion
# -----------------------------------------------------------------------------
def flag_show(conn, show_id: int, pub_date: str, source_url: str) -> tuple[int, bool]:
    """Set is_nyt_critics_pick=1 on the show's NYT review row.
    Returns (rows_updated, created_new_row)."""
    n = conn.execute(
        """UPDATE reviews
           SET is_nyt_critics_pick = 1,
               source_url = COALESCE(NULLIF(?, ''), source_url)
           WHERE show_id = ?
             AND publication_id IN (
                 SELECT publication_id FROM publications
                 WHERE normalized_name LIKE '%new york times%' OR normalized_name LIKE '%ny times%' OR normalized_name LIKE '%nytimes%'
             )
             AND is_nyt_critics_pick IS NOT 1""",
        (source_url, show_id),
    ).rowcount
    if n > 0:
        return (n, False)

    # No NYT review on file — create one
    pub_id = conn.execute(
        "SELECT publication_id FROM publications WHERE normalized_name LIKE '%new york times%' LIMIT 1"
    ).fetchone()
    if not pub_id:
        pub_id = conn.execute(
            "INSERT INTO publications (name, normalized_name) VALUES ('New York Times', 'new york times') RETURNING publication_id"
        ).fetchone()
    pub_id = pub_id[0]

    crit_id = conn.execute(
        "SELECT critic_id FROM critics WHERE primary_publication_id=? LIMIT 1", (pub_id,)
    ).fetchone()
    if not crit_id:
        crit_id = conn.execute(
            "INSERT INTO critics (name, normalized_name, primary_publication_id) "
            "VALUES ('NYT Critic', 'nyt critic', ?) RETURNING critic_id",
            (pub_id,)
        ).fetchone()
    crit_id = crit_id[0]

    open_row = conn.execute("SELECT opening_date FROM shows WHERE show_id=?", (show_id,)).fetchone()
    open_date = open_row[0] if open_row and open_row[0] else pub_date
    try:
        days_from = (datetime.strptime(pub_date, "%Y-%m-%d") - datetime.strptime(open_date[:10], "%Y-%m-%d")).days
    except Exception:
        days_from = 0

    conn.execute(
        """INSERT OR IGNORE INTO reviews
           (show_id, critic_id, publication_id, sentiment, review_date,
            is_opening_window, days_from_opening, is_nyt_critics_pick, source, source_url)
           VALUES (?, ?, ?, 'up', ?, 1, ?, 1, 'nyt', ?)""",
        (show_id, crit_id, pub_id, pub_date, days_from, source_url),
    )
    return (1, True)


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
def main():
    print(f"Loading seed URLs from {URLS_FILE} ...")
    existing = set(URLS_FILE.read_text().strip().split("\n"))
    print(f"  {len(existing)} URLs in seed file")

    print("\nAttempting to refresh from NYT spotlight (live)...")
    try:
        live = refresh_spotlight(existing)
        if live:
            combined = existing | live
            if len(combined) > len(existing):
                URLS_FILE.write_text("\n".join(sorted(combined)) + "\n")
                print(f"  Wrote {len(combined)} URLs ({len(combined)-len(existing)} new)")
                existing = combined
        else:
            print("  Spotlight returned nothing (likely paywall/blocking); proceeding with seed file")
    except Exception as e:
        print(f"  Spotlight refresh failed: {e}; proceeding with seed file")

    # Parse all URLs
    records = []
    for url in existing:
        m = THEATER_URL_RE.search(url)
        if not m: continue
        y, mo, d, slug = m.groups()
        try:
            pub_date = datetime(int(y), int(mo), int(d))
        except Exception:
            continue
        records.append((pub_date, slug.replace(".html", ""), url))
    print(f"\nParsed {len(records)} URLs with valid theater pattern")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    matched_total = 0
    matched_new   = 0
    created_rows  = 0
    by_year       = Counter()
    bway_year     = Counter()
    ob_year       = Counter()
    unmatched     = []

    print(f"\nMatching (date window ±{DATE_WINDOW_DAYS} days, fuzzy cutoff ≥{SCORE_CUTOFF})...")
    cand_cache: dict[int, list[dict]] = {}

    for pub_date, slug, url in records:
        year = pub_date.year
        if year not in cand_cache:
            cand_cache[year] = fetch_candidates(conn, year)
        match = best_match(slug, pub_date, cand_cache[year])
        if not match:
            unmatched.append((pub_date.date(), slug, url))
            continue
        n, created = flag_show(conn, match["show_id"], pub_date.strftime("%Y-%m-%d"), url)
        if n > 0:
            matched_total += 1
            by_year[year] += 1
            if match.get("source_bww") == 1 or match.get("show_type") in ("M","P"):
                bway_year[year] += 1
            else:
                ob_year[year] += 1
            if created: created_rows += 1
    conn.commit()
    conn.close()

    print(f"\n=== MATCHING SUMMARY ===")
    print(f"  Total flagged: {matched_total}")
    print(f"  New review rows created: {created_rows}")
    print(f"  Unmatched URLs: {len(unmatched)}")

    print(f"\n  Per-year matches (Broadway / Off-Broadway):")
    for y in sorted(set(bway_year) | set(ob_year)):
        print(f"    {y}: Broadway={bway_year[y]:3d}  Off-Broadway={ob_year[y]:3d}")

    print(f"\n  Sample unmatched (first 15):")
    for pd_, slug, url in unmatched[:15]:
        print(f"    {pd_}  {slug[:60]}")

    # Final DB state
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("""
        SELECT COUNT(DISTINCT r.show_id)
        FROM reviews r JOIN shows s ON s.show_id=r.show_id
        WHERE r.is_nyt_critics_pick=1
          AND (s.show_type IS NULL OR s.show_type NOT IN ('M','P'))
    """)
    ob_flagged = cur.fetchone()[0]
    cur = conn.execute("""
        SELECT COUNT(DISTINCT r.show_id)
        FROM reviews r JOIN shows s ON s.show_id=r.show_id
        WHERE r.is_nyt_critics_pick=1
          AND s.show_type IN ('M','P')
    """)
    bway_flagged = cur.fetchone()[0]
    print(f"\n  Final DB state:")
    print(f"    Broadway shows with CP flag: {bway_flagged}")
    print(f"    Off-Broadway shows with CP flag: {ob_flagged}")
    conn.close()


if __name__ == "__main__":
    main()
