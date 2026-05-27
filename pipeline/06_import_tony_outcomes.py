#!/usr/bin/env python3
"""
Phase 5: Import Tony Award outcomes from existing CSV into tony_outcomes table.
Then attempts to match each tony record to a show_id in the shows table.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from config import EXISTING_TONY_CSV
from db import get_connection
from normalize.titles import find_best_match, build_candidate_map
from utils import get_logger

logger = get_logger("import_tony")


def main():
    if EXISTING_TONY_CSV is None or not EXISTING_TONY_CSV.exists():
        print("INFO: CIA_TONY_CSV env var not set or file missing.")
        print("This pipeline step seeds tony_outcomes from a pre-built CSV.")
        print("Alternative: run pipeline/06b_import_wikipedia_tony.py to scrape Tony "
              "data from Wikipedia, or set CIA_TONY_CSV=/path/to/tony_outcomes.csv.\n")
        print("Skipping Phase 5.")
        return

    logger.info(f"Loading Tony outcomes from {EXISTING_TONY_CSV}")
    df = pd.read_csv(EXISTING_TONY_CSV)
    logger.info(f"  {len(df)} rows loaded")

    # Actual columns: show_id, show_name, tony_win, tony_category, tony_year,
    #                 production_year, num_performances, scrape_status
    # This CSV only records Tony WINNERS — non-winners have tony_win=0 and
    # no category/year data. We import only winners since we can't distinguish
    # "not nominated" from "nominated but lost" for the other rows.
    col_map = {
        "show_name": "show_title",
        "tony_win": "won",
        "tony_category": "category",
        "tony_year": "ceremony_year",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    # Keep only Tony winners — non-winners have no useful ceremony data
    winners = df[df["won"] == 1].copy()
    logger.info(f"  {len(winners)} Tony winners found (out of {len(df)} total shows)")
    df = winners

    inserted = matched = skipped = 0

    with get_connection() as conn:
        candidates = build_candidate_map(conn)

        for _, row in df.iterrows():
            show_title = str(row.get("show_title", "")).strip()
            ceremony_year = int(row["ceremony_year"]) if pd.notna(row.get("ceremony_year")) else None
            category = str(row.get("category", "")).strip() if pd.notna(row.get("category")) else ""
            nominated = 1  # winners are always nominated
            won = 1

            if not show_title or show_title.lower() in ("nan", "unknown"):
                skipped += 1
                continue

            # Find matching show_id
            target_year = (ceremony_year - 1) if ceremony_year else None
            show_id = find_best_match(
                show_title, candidates, target_year=target_year
            )

            try:
                conn.execute(
                    """INSERT OR REPLACE INTO tony_outcomes
                       (show_id, show_title, ceremony_year, category, nominated, won)
                       VALUES(?,?,?,?,?,?)""",
                    (show_id, show_title, ceremony_year, category, nominated, won),
                )
                inserted += 1
                if show_id:
                    matched += 1
            except Exception as e:
                logger.warning(f"Tony insert failed ({show_title}): {e}")

        conn.commit()

    logger.info(
        f"Phase 5 complete: {inserted} tony records inserted "
        f"({matched} matched to shows, {inserted - matched} unmatched), "
        f"{skipped} skipped"
    )
    print(f"\nPhase 5 complete: {inserted} Tony records imported, {matched} matched to shows")


if __name__ == "__main__":
    main()
