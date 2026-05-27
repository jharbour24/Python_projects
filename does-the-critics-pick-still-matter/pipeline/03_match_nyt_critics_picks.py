#!/usr/bin/env python3
"""
Phase 3: Scrape NYT theater reviews for Critics Pick designation.
Sets is_nyt_critics_pick=1 on matching reviews.

Requires NYT_API_KEY environment variable for full historical coverage.
Get a free key at: https://developer.nytimes.com/

Without API key: only recent articles (2-3 years) are accessible via section scrape.

Run time: ~10–30 minutes with API key (rate limited to 5 req/sec by NYT).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os


def main(start_year: int = 2000, end_year: int = None):
    api_key = os.getenv("NYT_API_KEY")
    if not api_key:
        print("WARNING: NYT_API_KEY not set.")
        print("Full historical Critics Pick data requires a free NYT API key.")
        print("Get one at: https://developer.nytimes.com/")
        print("Falling back to section scrape (recent articles only)...\n")

    from scrapers.nyt_critics_pick import NYTCriticsPickScraper
    scraper = NYTCriticsPickScraper()
    result = scraper.run(start_year=start_year, end_year=end_year)
    print(f"\nPhase 3 complete: {result['added']} Critics Picks flagged, "
          f"{result['updated']} updated, {result['errors']} errors")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Scrape NYT Critics Picks")
    p.add_argument("--start-year", type=int, default=2000)
    p.add_argument("--end-year", type=int, default=None)
    args = p.parse_args()
    main(start_year=args.start_year, end_year=args.end_year)
