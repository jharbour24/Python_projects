#!/usr/bin/env python3
"""
Test Google-based IBDB search approach.

This tests whether using Google to find IBDB pages is more reliable
than direct URL construction.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from scrape_all_broadway_shows import ComprehensiveBroadwayScraper
from utils import setup_logger

logger = setup_logger(__name__)


def main():
    """Test Google search for IBDB pages."""

    logger.info("="*70)
    logger.info("TESTING GOOGLE-BASED IBDB SEARCH")
    logger.info("="*70)

    # Test shows - mix of easy and difficult titles
    test_shows = [
        "Hadestown",
        "Hamilton",
        "The Book of Mormon",
        "& Juliet",  # Has special character
        "Hello, Dolly!",  # Has comma
        "Natasha, Pierre & The Great Comet of 1812",  # Long complex title
    ]

    try:
        logger.info("\nInitializing scraper...")
        scraper = ComprehensiveBroadwayScraper()

        # Test Cloudflare bypass first
        if not scraper.test_cloudflare_bypass():
            logger.error("Cloudflare bypass failed - cannot proceed")
            return

        logger.info("\n" + "="*70)
        logger.info("TESTING GOOGLE SEARCH FOR EACH SHOW")
        logger.info("="*70)

        results = []

        for idx, title in enumerate(test_shows):
            logger.info(f"\n[{idx+1}/{len(test_shows)}] Testing: {title}")
            logger.info("-" * 70)

            url = scraper.search_ibdb(title)

            if url:
                results.append({
                    'title': title,
                    'url': url,
                    'found': True
                })
                logger.info(f"✓ SUCCESS")
                logger.info(f"  URL: {url}")
            else:
                results.append({
                    'title': title,
                    'url': None,
                    'found': False
                })
                logger.error(f"✗ FAILED - No URL found")

        # Summary
        logger.info("\n" + "="*70)
        logger.info("RESULTS SUMMARY")
        logger.info("="*70)

        successful = sum(1 for r in results if r['found'])
        logger.info(f"Successful: {successful}/{len(test_shows)}")
        logger.info("")

        for r in results:
            status = "✓" if r['found'] else "✗"
            logger.info(f"{status} {r['title']}")
            if r['url']:
                logger.info(f"  → {r['url']}")

        if successful == len(test_shows):
            logger.info("\n" + "="*70)
            logger.info("✓✓✓ ALL TESTS PASSED ✓✓✓")
            logger.info("Google search approach is working!")
            logger.info("Ready to run full producer scraper.")
            logger.info("="*70)
        else:
            logger.warning("\n" + "="*70)
            logger.warning(f"⚠ PARTIAL SUCCESS: {successful}/{len(test_shows)} found")
            logger.warning("May need to adjust search logic")
            logger.warning("="*70)

    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
