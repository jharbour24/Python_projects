"""
Grosses refresh: imports the existing BroadwayWorld grosses xlsx into
show_week_performances, then runs an incremental scrape for any weeks
not yet in the DB.

Week-number assignment:
  week_number = (week_ending_date - opening_week_ending_date) / 7
  where opening_week = the BW reporting week that *contains* opening night.
  Previews (weeks before opening week) get negative week numbers.

All week-number assignment runs AFTER the show's opening_date is known
(populated by the DTLI show scraper). A separate pipeline step recomputes
any NULLs.
"""
import sqlite3
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup

from config import (
    EXISTING_GROSSES_XLSX,
    BWW_GROSSES_URL,
    BWW_START_DATE_STR,
    DB_PATH,
)
from db import get_connection
from scrapers.base import BaseScraper
from utils import normalize_title

SHOW_TYPE_MAP = {"MUSICAL": "M", "PLAY": "P", "M": "M", "P": "P"}


class GrossesRefreshScraper(BaseScraper):
    source = "grosses"

    def run(self, import_existing: bool = True, incremental: bool = True) -> dict:
        self.start_run()
        added = 0

        if import_existing and EXISTING_GROSSES_XLSX.exists():
            added += self._import_existing_xlsx()

        if incremental:
            added += self._scrape_new_weeks()

        self.logger.info(f"Grosses refresh done: {added} rows inserted/updated")
        self.finish_run(added, 0, 0)
        return {"added": added}

    def recompute_week_numbers(self) -> int:
        """
        For all show_week_performances rows where week_number IS NULL,
        compute week_number using the show's opening_date.
        Call this after dtli_show scraper has populated opening_dates.
        Returns count of rows updated.
        """
        updated = 0
        with get_connection(self.db_path) as conn:
            shows = conn.execute(
                """SELECT DISTINCT s.show_id, s.opening_date
                   FROM shows s
                   JOIN show_week_performances swp ON swp.show_id = s.show_id
                   WHERE s.opening_date IS NOT NULL
                     AND swp.week_number IS NULL"""
            ).fetchall()

            for show in shows:
                show_id = show["show_id"]
                opening_date = date.fromisoformat(show["opening_date"])
                opening_week_ending = _next_sunday(opening_date)

                updated += conn.execute(
                    """UPDATE show_week_performances
                       SET week_number = CAST(
                           (julianday(week_ending) - julianday(?)) / 7 AS INTEGER
                       ),
                       is_preview = CASE
                           WHEN week_ending < ? THEN 1 ELSE 0
                       END
                       WHERE show_id = ?""",
                    (
                        opening_week_ending.isoformat(),
                        opening_week_ending.isoformat(),
                        show_id,
                    ),
                ).rowcount

            conn.commit()

        self.logger.info(f"Week numbers recomputed for {updated} performance rows")
        return updated

    # ── Import existing xlsx ──────────────────────────────────────────────────

    def _import_existing_xlsx(self) -> int:
        self.logger.info(f"Importing existing grosses from {EXISTING_GROSSES_XLSX}")
        try:
            df = pd.read_excel(EXISTING_GROSSES_XLSX, engine="openpyxl")
        except Exception as e:
            self.logger.error(f"Could not read xlsx: {e}")
            return 0

        # Normalize columns to our schema
        col_map = {
            "Week": "week_ending",
            "Show": "show_raw",
            "Theater": "theater",
            "Gross": "gross",
            "Gross_Prev_Week": "gross_prev_week",
            "Gross_Diff": "gross_diff",
            "Gross_Diff_Pct": "gross_diff_pct",
            "Avg_Ticket": "avg_ticket",
            "Top_Ticket": "top_ticket",
            "Attendance": "attendance",
            "Seating_Capacity": "seating_capacity",
            "Performances": "performances",
            "Capacity_Pct": "capacity_pct",
            "Type": "show_type",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        if "week_ending" not in df.columns:
            self.logger.error("Grosses xlsx missing 'Week' column")
            return 0

        df["week_ending"] = pd.to_datetime(df["week_ending"]).dt.date
        df["show_type"] = df.get("show_type", pd.Series("U", index=df.index)).map(
            lambda x: SHOW_TYPE_MAP.get(str(x).upper(), "U")
        )

        added = 0
        with get_connection(self.db_path) as conn:
            for _, row in df.iterrows():
                show_name = str(row.get("show_raw", "")).strip()
                if not show_name or show_name == "Unknown":
                    continue
                show_id = self._get_or_create_show(conn, show_name, row.get("theater"))
                if not show_id:
                    continue
                try:
                    conn.execute(
                        """INSERT OR IGNORE INTO show_week_performances
                           (show_id, week_ending, gross, gross_prev_week, gross_diff,
                            gross_diff_pct, avg_ticket, top_ticket, attendance,
                            seating_capacity, performances, capacity_pct, theater, show_type)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            show_id,
                            str(row["week_ending"]),
                            _safe_float(row.get("gross")),
                            _safe_float(row.get("gross_prev_week")),
                            _safe_float(row.get("gross_diff")),
                            _safe_float(row.get("gross_diff_pct")),
                            _safe_float(row.get("avg_ticket")),
                            _safe_float(row.get("top_ticket")),
                            _safe_int(row.get("attendance")),
                            _safe_int(row.get("seating_capacity")),
                            _safe_int(row.get("performances")),
                            _safe_float(row.get("capacity_pct")),
                            str(row.get("theater", "")),
                            row["show_type"],
                        ),
                    )
                    added += 1
                except Exception as e:
                    self.logger.debug(f"Row insert failed ({show_name}): {e}")

            conn.commit()

        self.logger.info(f"Imported {added} gross rows from xlsx")
        return added

    # ── Incremental scrape ────────────────────────────────────────────────────

    def _scrape_new_weeks(self) -> int:
        """Scrape BroadwayWorld for any Sundays not yet in show_week_performances."""
        with get_connection(self.db_path) as conn:
            latest = conn.execute(
                "SELECT MAX(week_ending) as max_week FROM show_week_performances"
            ).fetchone()["max_week"]

        if latest:
            start = date.fromisoformat(latest) + timedelta(days=7)
        else:
            start = date.fromisoformat(BWW_START_DATE_STR)

        today = date.today()
        if start > today:
            self.logger.info("Grosses are up to date — no new weeks to scrape")
            return 0

        weeks = _get_sundays_from(start, today)
        self.logger.info(f"Scraping {len(weeks)} new BroadwayWorld weeks ({start} – {today})")

        added = 0
        for i, week_str in enumerate(weeks):
            for type_param, type_code in [("MUSICAL", "M"), ("PLAY", "P")]:
                try:
                    resp = self.session.get(
                        BWW_GROSSES_URL,
                        params={"week": week_str, "typer": type_param},
                        timeout=20,
                    )
                    resp.raise_for_status()
                    rows = _parse_bww_response(resp.text, week_str, type_code)
                    with get_connection(self.db_path) as conn:
                        for row in rows:
                            show_id = self._get_or_create_show(conn, row["show"], row.get("theater"))
                            if not show_id:
                                continue
                            conn.execute(
                                """INSERT OR IGNORE INTO show_week_performances
                                   (show_id, week_ending, gross, avg_ticket, top_ticket,
                                    attendance, seating_capacity, performances, capacity_pct,
                                    theater, show_type)
                                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                                (
                                    show_id, week_str,
                                    row.get("gross"), row.get("avg_ticket"), row.get("top_ticket"),
                                    row.get("attendance"), row.get("seating_capacity"),
                                    row.get("performances"), row.get("capacity_pct"),
                                    row.get("theater"), type_code,
                                ),
                            )
                            added += 1
                        conn.commit()
                    import time; time.sleep(0.05)
                except Exception as e:
                    self.logger.warning(f"BW fetch failed {type_param} {week_str}: {e}")

            if i % 20 == 0:
                self.logger.info(f"  {i+1}/{len(weeks)} weeks done")

        return added

    # ── Show matching ─────────────────────────────────────────────────────────

    def _get_or_create_show(
        self,
        conn: sqlite3.Connection,
        show_name: str,
        theater: Optional[str] = None,
    ) -> Optional[int]:
        """Find existing show by normalized title, or create a stub."""
        norm = normalize_title(show_name)
        existing = conn.execute(
            "SELECT show_id FROM shows WHERE normalized_title=?", (norm,)
        ).fetchone()
        if existing:
            conn.execute("UPDATE shows SET source_bww=1 WHERE show_id=?", (existing["show_id"],))
            return existing["show_id"]

        # Fuzzy fallback
        from rapidfuzz import process, fuzz
        candidates = conn.execute(
            "SELECT show_id, normalized_title FROM shows"
        ).fetchall()
        if candidates:
            choices = {r["show_id"]: r["normalized_title"] for r in candidates}
            match = process.extractOne(
                norm, choices, scorer=fuzz.token_set_ratio, score_cutoff=90
            )
            if match:
                matched_id = match[2]
                conn.execute("UPDATE shows SET source_bww=1 WHERE show_id=?", (matched_id,))
                return matched_id

        # Create stub (will be enriched by DTLI scraper later)
        cur = conn.execute(
            """INSERT INTO shows(title, normalized_title, theater, source_bww)
               VALUES(?,?,?,1)""",
            (show_name, norm, theater),
        )
        return cur.lastrowid


# ── BroadwayWorld HTML parsing ────────────────────────────────────────────────

def _parse_bww_response(html: str, week_str: str, show_type: str) -> list[dict]:
    """Parse BroadwayWorld grosses HTML (same format as existing project)."""
    import re

    soup = BeautifulSoup(html, "lxml")
    rows = []
    for row in soup.find_all("div", class_="row"):
        show_name = row.get("data-name", "").strip()
        if not show_name or show_name == "Unknown":
            continue
        gross = _clean_numeric(row.get("data-gross"))
        attendance = _clean_numeric(row.get("data-attendee"))
        capacity_pct = _clean_numeric(row.get("data-capacity"))
        avg_ticket = _clean_numeric(row.get("data-ticket"))

        cells = row.find_all("div", class_="cell")
        theater = ""
        if cells:
            t = cells[0].find("a", class_="theater")
            if t:
                theater = t.get_text(strip=True)

        rows.append({
            "show": show_name,
            "theater": theater,
            "gross": gross,
            "attendance": attendance,
            "capacity_pct": capacity_pct,
            "avg_ticket": avg_ticket,
        })
    return rows


def _clean_numeric(s) -> Optional[float]:
    import re
    if s is None:
        return None
    s = str(s).strip()
    negative = s.startswith("(") and s.endswith(")")
    s = re.sub(r"[^\d.]", "", s)
    if not s:
        return None
    try:
        v = float(s)
        return -v if negative else v
    except ValueError:
        return None


def _safe_float(v) -> Optional[float]:
    try:
        return float(v) if pd.notna(v) else None
    except (ValueError, TypeError):
        return None


def _safe_int(v) -> Optional[int]:
    try:
        return int(v) if pd.notna(v) else None
    except (ValueError, TypeError):
        return None


def _next_sunday(d: date) -> date:
    """Return the next Sunday on or after date d."""
    days_ahead = 6 - d.weekday()  # Sunday = 6
    if days_ahead < 0:
        days_ahead += 7
    return d + timedelta(days=days_ahead)


def _get_sundays_from(start: date, end: date) -> list[str]:
    sundays = []
    d = start
    while d.weekday() != 6:
        d += timedelta(days=1)
    while d <= end:
        sundays.append(d.isoformat())
        d += timedelta(days=7)
    return sundays
