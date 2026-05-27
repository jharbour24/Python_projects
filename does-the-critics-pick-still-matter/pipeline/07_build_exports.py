#!/usr/bin/env python3
"""
Phase 7: Build flat CSV and Parquet exports for analysis.

Exports produced:
  exports/shows.csv                   — show metadata
  exports/reviews.csv                 — all reviews with publication/critic
  exports/publications.csv            — publication stats
  exports/critics.csv                 — critic stats
  exports/tony_outcomes.csv           — Tony nomination/win data
  exports/weekly_grosses.csv          — raw weekly gross data with week_number
  exports/opening_consensus.csv       — opening-window review pivot (one row per show)
  exports/master.parquet              — joined analytical dataset (primary analysis file)

master.parquet structure (one row per show × week):
  show_id, show_title, show_type, is_revival, opening_date
  week_number, week_ending, is_preview, gross, capacity_pct, attendance
  [publication]_sentiment columns (e.g., nyt_sentiment = up/meh/down/NULL)
  nyt_critics_pick (0/1)
  any_up_count, any_meh_count, any_down_count (opening window totals)
  tony_nominated, tony_won, tony_nominations_count, tony_wins_count
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import sqlite3

from config import EXPORTS_DIR, DB_PATH
from db import get_connection
from utils import get_logger

logger = get_logger("build_exports")
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


def main():
    logger.info("Building exports...")

    with get_connection() as conn:
        _export_shows(conn)
        _export_reviews(conn)
        _export_publications(conn)
        _export_critics(conn)
        _export_tony(conn)
        _export_weekly_grosses(conn)
        _export_opening_consensus(conn)
        _export_master_parquet(conn)

    logger.info(f"All exports written to {EXPORTS_DIR}")
    print(f"\nPhase 7 complete — exports in {EXPORTS_DIR}")


def _export_shows(conn):
    df = pd.read_sql(
        "SELECT * FROM shows ORDER BY opening_date, title",
        conn,
    )
    df.to_csv(EXPORTS_DIR / "shows.csv", index=False)
    logger.info(f"  shows.csv: {len(df)} rows")


def _export_reviews(conn):
    df = pd.read_sql(
        """SELECT r.review_id, s.title as show_title, s.opening_date,
                  p.name as publication, c.name as critic,
                  r.sentiment, r.review_date, r.is_opening_window,
                  r.days_from_opening, r.is_nyt_critics_pick, r.excerpt, r.source
           FROM reviews r
           JOIN shows s ON s.show_id = r.show_id
           JOIN publications p ON p.publication_id = r.publication_id
           JOIN critics c ON c.critic_id = r.critic_id
           ORDER BY s.opening_date, p.name""",
        conn,
    )
    df.to_csv(EXPORTS_DIR / "reviews.csv", index=False)
    logger.info(f"  reviews.csv: {len(df)} rows")


def _export_publications(conn):
    df = pd.read_sql(
        """SELECT p.publication_id, p.name,
                  COUNT(r.review_id) as total_reviews,
                  SUM(CASE WHEN r.sentiment='up' THEN 1 ELSE 0 END) as up_count,
                  SUM(CASE WHEN r.sentiment='meh' THEN 1 ELSE 0 END) as meh_count,
                  SUM(CASE WHEN r.sentiment='down' THEN 1 ELSE 0 END) as down_count,
                  SUM(CASE WHEN r.is_opening_window=1 THEN 1 ELSE 0 END) as opening_window_reviews,
                  MIN(r.review_date) as first_review, MAX(r.review_date) as last_review
           FROM publications p
           LEFT JOIN reviews r ON r.publication_id = p.publication_id
           GROUP BY p.publication_id
           ORDER BY total_reviews DESC""",
        conn,
    )
    df.to_csv(EXPORTS_DIR / "publications.csv", index=False)
    logger.info(f"  publications.csv: {len(df)} rows")


def _export_critics(conn):
    df = pd.read_sql(
        """SELECT c.critic_id, c.name, p.name as primary_publication,
                  COUNT(r.review_id) as total_reviews,
                  SUM(CASE WHEN r.sentiment='up' THEN 1 ELSE 0 END) as up_count,
                  SUM(CASE WHEN r.sentiment='meh' THEN 1 ELSE 0 END) as meh_count,
                  SUM(CASE WHEN r.sentiment='down' THEN 1 ELSE 0 END) as down_count,
                  MIN(r.review_date) as first_review, MAX(r.review_date) as last_review
           FROM critics c
           LEFT JOIN publications p ON p.publication_id = c.primary_publication_id
           LEFT JOIN reviews r ON r.critic_id = c.critic_id
           GROUP BY c.critic_id
           ORDER BY total_reviews DESC""",
        conn,
    )
    df.to_csv(EXPORTS_DIR / "critics.csv", index=False)
    logger.info(f"  critics.csv: {len(df)} rows")


def _export_tony(conn):
    df = pd.read_sql(
        """SELECT t.tony_id, COALESCE(s.title, t.show_title) as show_title,
                  s.opening_date, t.ceremony_year, t.category, t.nominated, t.won
           FROM tony_outcomes t
           LEFT JOIN shows s ON s.show_id = t.show_id
           ORDER BY t.ceremony_year, t.category""",
        conn,
    )
    df.to_csv(EXPORTS_DIR / "tony_outcomes.csv", index=False)
    logger.info(f"  tony_outcomes.csv: {len(df)} rows")


def _export_weekly_grosses(conn):
    df = pd.read_sql(
        """SELECT s.title as show_title, s.opening_date, s.show_type, s.is_revival,
                  swp.week_ending, swp.week_number, swp.is_preview,
                  swp.gross, swp.gross_diff_pct, swp.capacity_pct,
                  swp.attendance, swp.avg_ticket, swp.top_ticket,
                  swp.performances, swp.theater
           FROM show_week_performances swp
           JOIN shows s ON s.show_id = swp.show_id
           WHERE swp.week_number IS NOT NULL
           ORDER BY s.title, swp.week_number""",
        conn,
    )
    df.to_csv(EXPORTS_DIR / "weekly_grosses.csv", index=False)
    logger.info(f"  weekly_grosses.csv: {len(df)} rows")


def _export_opening_consensus(conn):
    """
    Two exports:
      opening_reviews_long.csv  — one row per show × publication review (long format)
      opening_consensus.csv     — one row per show, one column per publication (wide/pivot)
    """
    # ── Long format ───────────────────────────────────────────────────────────
    long_df = pd.read_sql(
        """SELECT s.show_id, s.title as show_title, s.opening_date,
                  s.show_type, s.is_revival,
                  p.name as publication,
                  r.sentiment, r.review_date,
                  c.name as critic,
                  r.is_nyt_critics_pick, r.excerpt
           FROM reviews r
           JOIN shows s ON s.show_id = r.show_id
           JOIN publications p ON p.publication_id = r.publication_id
           JOIN critics c ON c.critic_id = r.critic_id
           WHERE r.is_opening_window = 1
           ORDER BY s.opening_date, p.name""",
        conn,
    )
    long_df.to_csv(EXPORTS_DIR / "opening_reviews_long.csv", index=False)
    logger.info(f"  opening_reviews_long.csv: {len(long_df)} rows")

    # ── Wide/pivot format ─────────────────────────────────────────────────────
    # Normalize publication names for column headers
    long_df["pub_col"] = (
        long_df["publication"]
        .str.lower()
        .str.strip()
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.strip("_")
    )

    # Canonical name merges for known duplicates
    pub_aliases = {
        "ny_daily_news": "new_york_daily_news",
        "nbc_new_york": "nbc_ny",
        "am_new_york": "am_new_york",
        "did_they_like_it": "dtli",
    }
    long_df["pub_col"] = long_df["pub_col"].replace(pub_aliases)

    # When a publication reviewed a show more than once in the window,
    # keep the review closest to opening night (smallest abs days_from_opening)
    opening_reviews = pd.read_sql(
        """SELECT r.review_id, r.show_id, p.name as publication,
                  r.sentiment, r.days_from_opening
           FROM reviews r
           JOIN publications p ON p.publication_id = r.publication_id
           WHERE r.is_opening_window = 1""",
        conn,
    )
    opening_reviews["pub_col"] = (
        opening_reviews["publication"]
        .str.lower()
        .str.strip()
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.strip("_")
        .replace(pub_aliases)
    )
    # Keep closest-to-opening review per show × publication
    opening_reviews["abs_days"] = opening_reviews["days_from_opening"].abs().fillna(999)
    deduped = (
        opening_reviews
        .sort_values("abs_days")
        .groupby(["show_id", "pub_col"], as_index=False)
        .first()
    )

    # Pivot: rows = show, columns = publication, values = sentiment (up/meh/down)
    pivot = deduped.pivot(index="show_id", columns="pub_col", values="sentiment")
    pivot.columns.name = None

    # Show metadata
    shows_df = pd.read_sql(
        """SELECT s.show_id, s.title as show_title, s.opening_date,
                  s.show_type, s.is_revival,
                  MAX(CASE WHEN r.is_nyt_critics_pick=1 THEN 1 ELSE 0 END) as nyt_critics_pick,
                  COUNT(r.review_id) as total_opening_reviews,
                  SUM(CASE WHEN r.sentiment='up' THEN 1 ELSE 0 END) as up_count,
                  SUM(CASE WHEN r.sentiment='meh' THEN 1 ELSE 0 END) as meh_count,
                  SUM(CASE WHEN r.sentiment='down' THEN 1 ELSE 0 END) as down_count
           FROM shows s
           LEFT JOIN reviews r ON r.show_id = s.show_id AND r.is_opening_window = 1
           GROUP BY s.show_id
           ORDER BY s.opening_date""",
        conn,
    ).set_index("show_id")

    wide_df = shows_df.join(pivot, how="left").reset_index(drop=True)

    wide_df.to_csv(EXPORTS_DIR / "opening_consensus.csv", index=False)
    logger.info(
        f"  opening_consensus.csv: {len(wide_df)} shows × "
        f"{len(pivot.columns)} publication columns"
    )


def _export_master_parquet(conn):
    """
    The primary analysis file.
    Joins weekly grosses with opening-window review stats per show.
    One row per show × week.
    """
    # Get opening window stats per show
    consensus_df = pd.read_sql(
        """SELECT show_id,
                  SUM(CASE WHEN sentiment='up' THEN 1 ELSE 0 END) as opening_up_count,
                  SUM(CASE WHEN sentiment='meh' THEN 1 ELSE 0 END) as opening_meh_count,
                  SUM(CASE WHEN sentiment='down' THEN 1 ELSE 0 END) as opening_down_count,
                  COUNT(*) as opening_total_reviews,
                  MAX(CASE WHEN is_nyt_critics_pick=1 THEN 1 ELSE 0 END) as nyt_critics_pick,
                  MAX(CASE WHEN publication_id IN (
                      SELECT publication_id FROM publications WHERE normalized_name LIKE '%new york times%'
                  ) AND sentiment='up' THEN 1 ELSE 0 END) as nyt_up
           FROM reviews
           WHERE is_opening_window = 1
           GROUP BY show_id""",
        conn,
    )
    consensus_df["pct_positive"] = (
        consensus_df["opening_up_count"] / consensus_df["opening_total_reviews"]
    ).fillna(0)

    # Get Tony outcomes per show (summarized)
    tony_df = pd.read_sql(
        """SELECT show_id,
                  SUM(nominated) as tony_nominations,
                  SUM(won) as tony_wins,
                  MAX(CASE WHEN won=1 THEN 1 ELSE 0 END) as tony_winner
           FROM tony_outcomes
           WHERE show_id IS NOT NULL
           GROUP BY show_id""",
        conn,
    )

    # Weekly gross data
    grosses_df = pd.read_sql(
        """SELECT swp.show_id, s.title as show_title, s.show_type, s.is_revival,
                  s.opening_date, swp.week_ending, swp.week_number, swp.is_preview,
                  swp.gross, swp.gross_diff_pct, swp.capacity_pct,
                  swp.attendance, swp.avg_ticket, swp.theater
           FROM show_week_performances swp
           JOIN shows s ON s.show_id = swp.show_id
           WHERE swp.week_number IS NOT NULL""",
        conn,
    )

    # Merge
    df = grosses_df.merge(consensus_df, on="show_id", how="left")
    df = df.merge(tony_df, on="show_id", how="left")

    # Fill Tony NULLs
    for col in ["tony_nominations", "tony_wins", "tony_winner"]:
        if col in df.columns:
            df[col] = df[col].fillna(0).astype(int)

    # Derive review signal columns
    df["has_opening_reviews"] = df["opening_total_reviews"].fillna(0) > 0
    df["majority_positive"] = df["pct_positive"].fillna(0) >= 0.6

    out = EXPORTS_DIR / "master.parquet"
    df.to_parquet(out, index=False, engine="pyarrow")
    logger.info(f"  master.parquet: {len(df)} rows, {len(df.columns)} columns → {out}")

    # Also save a CSV version for non-Python users
    df.to_csv(EXPORTS_DIR / "master.csv", index=False)
    logger.info(f"  master.csv: {len(df)} rows")


if __name__ == "__main__":
    main()
