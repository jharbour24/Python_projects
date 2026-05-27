"""
Wikipedia Tony Award scraper.

Scrapes each major Tony Award category page on Wikipedia to extract:
  - Show title
  - Ceremony year
  - Category name
  - Whether the show won (winner) or was only nominated

This replaces/supplements the existing tony_outcomes_with_performances.csv
which only had 50 Tony winners from 2010+. Wikipedia gives us winners AND
nominees going back to 1947 across all major categories.

Winner detection: rows with style containing 'B0C4DE' (light blue) = winner.

Categories scraped (show-level — no individual performer categories):
  - Best Musical (1949+)
  - Best Play (1947+)
  - Best Revival of a Musical (1977+, split from "Best Revival" in 1994)
  - Best Revival of a Play (1977+, split in 1994)
  - Best Book of a Musical (1949+)
  - Best Original Score (1949+)
  - Best Choreography (1956+)
  - Best Direction of a Musical (1960+)
  - Best Direction of a Play (1960+)
"""
import re
import time
from typing import Iterator, Optional

import requests
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from db import get_connection
from normalize.titles import find_best_match, build_candidate_map
from utils import get_logger

WIKI_BASE = "https://en.wikipedia.org/wiki"

TONY_CATEGORIES = [
    ("Best Musical",                   f"{WIKI_BASE}/Tony_Award_for_Best_Musical"),
    ("Best Play",                      f"{WIKI_BASE}/Tony_Award_for_Best_Play"),
    ("Best Revival of a Musical",      f"{WIKI_BASE}/Tony_Award_for_Best_Revival_of_a_Musical"),
    ("Best Revival of a Play",         f"{WIKI_BASE}/Tony_Award_for_Best_Revival_of_a_Play"),
    ("Best Revival",                   f"{WIKI_BASE}/Tony_Award_for_Best_Revival"),
    ("Best Book of a Musical",         f"{WIKI_BASE}/Tony_Award_for_Best_Book_of_a_Musical"),
    ("Best Original Score",            f"{WIKI_BASE}/Tony_Award_for_Best_Original_Score"),
    ("Best Choreography",              f"{WIKI_BASE}/Tony_Award_for_Best_Choreography"),
    ("Best Direction of a Musical",    f"{WIKI_BASE}/Tony_Award_for_Best_Direction_of_a_Musical"),
    ("Best Direction of a Play",       f"{WIKI_BASE}/Tony_Award_for_Best_Direction_of_a_Play"),
]

WINNER_STYLE = "b0c4de"  # lowercase hex fragment present in winner row style


class WikipediaTonyScraper(BaseScraper):
    source = "wiki_tony"

    def run(self) -> dict:
        self.start_run()
        total_inserted = total_matched = total_errors = 0

        with get_connection(self.db_path) as conn:
            candidates = build_candidate_map(conn)

            for category_name, url in TONY_CATEGORIES:
                self.logger.info(f"Scraping: {category_name}")
                inserted = matched = errors = 0

                html = self.fetch(url)
                if not html:
                    self.logger.warning(f"  Failed to fetch {url}")
                    continue

                for record in _parse_tony_page(html, category_name):
                    show_id = _match_show(conn, candidates, record)
                    try:
                        conn.execute(
                            """INSERT OR REPLACE INTO tony_outcomes
                               (show_id, show_title, ceremony_year, category, nominated, won)
                               VALUES(?,?,?,?,1,?)""",
                            (show_id, record["title"], record["year"],
                             record["category"], 1 if record["won"] else 0),
                        )
                        inserted += 1
                        if show_id:
                            matched += 1
                    except Exception as e:
                        self.logger.debug(f"  Insert error ({record['title']}): {e}")
                        errors += 1

                conn.commit()
                self.logger.info(
                    f"  → {inserted} records, {matched} matched to shows, {errors} errors"
                )
                total_inserted += inserted
                total_matched += matched
                total_errors += errors

                time.sleep(1)  # polite delay between Wikipedia pages

        self.finish_run(total_inserted, 0, total_errors)
        self.logger.info(
            f"Done: {total_inserted} Tony records, {total_matched} matched to shows"
        )
        return {"inserted": total_inserted, "matched": total_matched, "errors": total_errors}


# ── Parsing ───────────────────────────────────────────────────────────────────

def _parse_tony_page(html: str, category_name: str) -> Iterator[dict]:
    """
    Parse all wikitables on a Tony Award category page.
    Yields dicts: {title, year, category, won}
    """
    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table", class_="wikitable")

    for table in tables:
        current_year = None
        rows = table.find_all("tr")

        for row in rows:
            cells = row.find_all(["th", "td"])
            if not cells:
                continue

            # Skip header rows
            if cells[0].find("th") or cells[0].get("scope") == "col":
                continue

            first_text = cells[0].get_text(" ", strip=True)

            # Year marker row: single cell with year pattern, no show content
            if len(cells) == 1 or (len(cells) >= 1 and re.match(r"^\d{4}", first_text)):
                year = _extract_year(first_text)
                if year:
                    current_year = year
                continue

            # Show row
            if current_year is None:
                continue

            is_winner = WINNER_STYLE in (row.get("style") or "").lower()

            # Show title is in first non-year cell — strip author credits
            raw_title = first_text
            title = _extract_show_title(raw_title)

            if not title or len(title) < 2:
                continue

            yield {
                "title": title,
                "year": current_year,
                "category": category_name,
                "won": is_winner,
            }


def _extract_year(text: str) -> Optional[int]:
    """Extract a 4-digit year from text like '2022(75th)[67]', '2020/2021', or '2022'."""
    # Split years like '2020/2021' — take the later year
    m = re.search(r"\b(19|20)\d{2}/(19|20)\d{2}\b", text)
    if m:
        return int(m.group().split("/")[1])
    m = re.search(r"\b(19|20)\d{2}\b", text)
    if m:
        return int(m.group())
    return None


def _extract_show_title(raw: str) -> str:
    """
    Strip author credits from a show title cell.
    Input:  'Kiss Me, Kate Book by Bella and Samuel Spewack, Music by Cole Porter'
    Output: 'Kiss Me, Kate'

    Input:  'Hamilton'
    Output: 'Hamilton'
    """
    # Credit markers that follow the title
    credit_markers = [
        r"\bBook\s+by\b",
        r"\bMusic\s+by\b",
        r"\bLyrics\s+by\b",
        r"\bWords\s+by\b",
        r"\bConceived\s+by\b",
        r"\bAdapted\s+by\b",
        r"\bBased\s+on\b",
        r"\bDirected\s+by\b",
        r"\bChoreograph",
        r"\bOriginal\s+",
    ]
    pattern = "|".join(credit_markers)
    m = re.search(pattern, raw, re.I)
    if m:
        title = raw[: m.start()].strip()
    else:
        title = raw.strip()

    # Clean trailing punctuation and Wikipedia reference markers like [67]
    title = re.sub(r"\[\d+\]", "", title)
    title = re.sub(r"\s+", " ", title).strip(" ,;.")

    return title


def _match_show(conn, candidates: dict, record: dict) -> Optional[int]:
    """Fuzzy-match a Tony record to a show in the DB."""
    target_year = record["year"] - 1 if record["year"] else None
    return find_best_match(record["title"], candidates, target_year=target_year)
