#!/usr/bin/env python3
"""
Phase 1: Discover all Broadway show slugs from DTLI sitemaps.
Populates the shows table with dtli_slug + placeholder titles.
Run time: ~30 seconds (14 sitemap files, all cached after first run).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import initialize_db
from scrapers.dtli_archive import DTLIArchiveScraper


def main(force_refresh: bool = False):
    initialize_db()
    scraper = DTLIArchiveScraper(force_refresh=force_refresh)
    result = scraper.run()
    print(f"\nPhase 1 complete: {result['added']} shows added, {result['updated']} updated")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Discover DTLI show slugs via sitemaps")
    p.add_argument("--refresh", action="store_true", help="Bypass HTML cache")
    args = p.parse_args()
    main(force_refresh=args.refresh)
