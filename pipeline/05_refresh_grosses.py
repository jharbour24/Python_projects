#!/usr/bin/env python3
"""
Phase 4: Import existing Broadway grosses xlsx + scrape any new weeks.
Populates show_week_performances table.
Also recomputes week_numbers after opening_dates are known.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import EXISTING_GROSSES_XLSX
from scrapers.grosses_refresh import GrossesRefreshScraper


def main(import_existing: bool = True, incremental: bool = True, recompute: bool = True):
    if import_existing and (EXISTING_GROSSES_XLSX is None or not EXISTING_GROSSES_XLSX.exists()):
        if EXISTING_GROSSES_XLSX is None:
            print("INFO: CIA_GROSSES_XLSX env var not set; will scrape grosses from scratch.")
        else:
            print(f"WARNING: Existing grosses file not found at {EXISTING_GROSSES_XLSX}")
        print("Skipping xlsx import. Will only scrape new weeks from BroadwayWorld.\n")
        import_existing = False

    scraper = GrossesRefreshScraper()
    result = scraper.run(import_existing=import_existing, incremental=incremental)

    if recompute:
        print("\nRecomputing week numbers...")
        updated = scraper.recompute_week_numbers()
        print(f"  Week numbers updated for {updated} performance rows")

    print(f"\nPhase 4 complete: {result['added']} gross rows loaded")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Import and refresh Broadway grosses")
    p.add_argument("--no-import", action="store_true", help="Skip importing existing xlsx")
    p.add_argument("--no-incremental", action="store_true", help="Skip scraping new weeks")
    p.add_argument("--no-recompute", action="store_true", help="Skip week number recomputation")
    args = p.parse_args()
    main(
        import_existing=not args.no_import,
        incremental=not args.no_incremental,
        recompute=not args.no_recompute,
    )
