"""
Test script to verify producer counting on Hadestown.

User reported Hadestown should have 44 producers, not 21.
This script tests the scraper specifically on Hadestown to verify accuracy.

Author: Broadway Analysis Pipeline
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from scrape_all_broadway_shows import ComprehensiveBroadwayScraper
from utils import setup_logger

logger = setup_logger(__name__)


def main():
    """Test Hadestown producer scraping."""

    logger.info("="*60)
    logger.info("HADESTOWN PRODUCER COUNT TEST")
    logger.info("="*60)
    logger.info("Expected: 44 producers (per user)")
    logger.info("Previous count: 25 (4 lead, 21 co) - INCORRECT")
    logger.info("="*60)

    hadestown_url = "https://www.ibdb.com/broadway-production/hadestown-504445"

    try:
        logger.info("\nInitializing scraper...")
        scraper = ComprehensiveBroadwayScraper(headless=False)

        # Test Cloudflare bypass first
        if not scraper.test_cloudflare_bypass():
            logger.error("Cloudflare bypass failed - cannot proceed")
            return

        # Scrape Hadestown
        logger.info(f"\nScraping Hadestown: {hadestown_url}")
        result = scraper.scrape_producers_detailed(hadestown_url)

        # Display results
        logger.info("\n" + "="*60)
        logger.info("RESULTS")
        logger.info("="*60)

        if result['scrape_success']:
            logger.info(f"✓ Scrape successful")
            logger.info(f"  Method: {result['scrape_method']}")
            logger.info(f"  Producer count: {result['producer_count_total']}")
            logger.info(f"\n  Producers found:")
            for i, producer in enumerate(result['producers_list'], 1):
                logger.info(f"    {i}. {producer}")

            # Check if count matches expected
            if result['producer_count_total'] == 44:
                logger.info(f"\n✓✓✓ CORRECT! Count matches expected 44 producers")
            elif result['producer_count_total'] < 44:
                logger.warning(f"\n⚠ UNDERCOUNTING: Found {result['producer_count_total']}, expected 44")
                logger.info(f"Missing {44 - result['producer_count_total']} producers")
            else:
                logger.warning(f"\n⚠ OVERCOUNTING: Found {result['producer_count_total']}, expected 44")
                logger.info(f"Extra {result['producer_count_total'] - 44} producers")

            # Show raw text for debugging
            if result['producers_raw_text']:
                logger.info(f"\n--- Raw producer text (first 1000 chars) ---")
                logger.info(result['producers_raw_text'][:1000])
                logger.info("--- End raw text ---")

        else:
            logger.error(f"✗ Scrape failed - no producers found")

    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
