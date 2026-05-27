#!/usr/bin/env python3
"""
Phase 2: Scrape individual DTLI show pages for metadata + all reviews.
Populates: shows (title, opening_date, theater), publications, critics, reviews.

Run time: ~1–3 hours for full archive (~8,400 shows), ~seconds on cache hits.
Use --limit N to test with a small batch first.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import get_connection
from scrapers.dtli_show import DTLIShowScraper


def main(
    broadway_only: bool = True,
    limit: int = None,
    slug: str = None,
    force_refresh: bool = False,
):
    scraper = DTLIShowScraper(force_refresh=force_refresh)

    if slug:
        print(f"Scraping single show: {slug}")
        result = scraper.run(broadway_only=broadway_only, slug=slug)
    else:
        with get_connection() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM shows WHERE dtli_slug IS NOT NULL"
            ).fetchone()[0]
        print(f"Found {total} shows to scrape (broadway_only={broadway_only})")
        result = scraper.run(broadway_only=broadway_only, limit=limit)

    print(f"\nPhase 2 complete: {result['added']} shows enriched, "
          f"{result['skipped']} skipped (off-broadway), {result.get('errors', 0)} errors")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Scrape DTLI individual show pages")
    p.add_argument("--all-venues", action="store_true", help="Include Off-Broadway shows")
    p.add_argument("--limit", type=int, help="Only process N shows (for testing)")
    p.add_argument("--slug", type=str, help="Scrape a single show by slug")
    p.add_argument("--refresh", action="store_true", help="Bypass HTML cache")
    args = p.parse_args()
    main(
        broadway_only=not args.all_venues,
        limit=args.limit,
        slug=args.slug,
        force_refresh=args.refresh,
    )
