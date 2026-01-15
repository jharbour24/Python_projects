#!/usr/bin/env python3
"""
Test Cloudflare bypass using cloudscraper library.
"""

import cloudscraper
from bs4 import BeautifulSoup
from utils import setup_logger
import time

logger = setup_logger(__name__)


def test_with_cloudscraper():
    """Test accessing IBDB with cloudscraper."""

    logger.info("="*70)
    logger.info("Testing IBDB access with Cloudscraper")
    logger.info("="*70)

    try:
        # Create cloudscraper session
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )

        # Test 1: Home page
        logger.info("\nTest 1: Accessing IBDB home page")
        response = scraper.get("https://www.ibdb.com/", timeout=30)
        logger.info(f"Status code: {response.status_code}")

        if response.status_code == 200:
            logger.info("✓ Successfully accessed IBDB home page!")
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.find('title')
            if title:
                logger.info(f"Page title: {title.get_text()}")
        else:
            logger.error(f"✗ Failed with status {response.status_code}")
            return False

        time.sleep(3)

        # Test 2: Production page
        logger.info("\nTest 2: Accessing Hamilton production page")
        prod_url = "https://www.ibdb.com/broadway-production/hamilton-499521"
        response = scraper.get(prod_url, timeout=30)
        logger.info(f"Status code: {response.status_code}")

        if response.status_code == 200:
            logger.info("✓ Successfully accessed production page!")

            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for title
            title = soup.find('h1')
            if title:
                logger.info(f"Show title: {title.get_text().strip()}")

            # Look for producer information
            if 'produc' in response.text.lower():
                logger.info("✓ Page contains producer information")

                # Try to find specific producer mentions
                producer_count = response.text.lower().count('producer')
                logger.info(f"Found 'producer' mentioned {producer_count} times on page")

                return True
            else:
                logger.warning("⚠ No producer information found")
                return False
        else:
            logger.error(f"✗ Failed with status {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_with_cloudscraper()

    logger.info("\n" + "="*70)
    if success:
        logger.info("✓✓✓ CLOUDSCRAPER WORKS! ✓✓✓")
        logger.info("We can proceed with IBDB scraping using cloudscraper")
        logger.info("="*70)
        exit(0)
    else:
        logger.error("✗✗✗ CLOUDSCRAPER FAILED ✗✗✗")
        logger.error("IBDB access is blocked even with Cloudflare bypass")
        logger.error("We need to use an alternative data source")
        logger.error("="*70)
        exit(1)
