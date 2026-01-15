#!/usr/bin/env python3
"""
Test direct IBDB access with cloudscraper (no Google search).
"""

import time
import cloudscraper
from bs4 import BeautifulSoup
from utils import setup_logger

logger = setup_logger(__name__)


def test_direct_ibdb_with_cloudscraper():
    """Test direct IBDB page access with cloudscraper."""

    logger.info("="*70)
    logger.info("TESTING DIRECT IBDB ACCESS WITH CLOUDSCRAPER")
    logger.info("="*70)

    # Create cloudscraper session
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        },
        delay=10
    )

    # Known IBDB URLs
    test_urls = [
        ("Hamilton", "https://www.ibdb.com/broadway-production/hamilton-499521", 4),
        ("Hadestown", "https://www.ibdb.com/broadway-production/hadestown-509022", 45),
    ]

    for show_name, url, expected_producers in test_urls:
        logger.info(f"\n{'='*70}")
        logger.info(f"TEST: {show_name}")
        logger.info(f"URL: {url}")
        logger.info(f"Expected producers: ~{expected_producers}")
        logger.info(f"{'='*70}")

        try:
            logger.info("Fetching with cloudscraper...")
            response = scraper.get(url, timeout=30)

            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response size: {len(response.text)} bytes")

            if response.status_code == 200:
                logger.info("✓ SUCCESS - Got 200 OK!")

                # Check if we got actual content or Cloudflare challenge
                if 'cloudflare' in response.text.lower() and 'challenge' in response.text.lower():
                    logger.error("✗ Got Cloudflare challenge page (not bypassed)")
                else:
                    logger.info("✓ Got actual page content (not a challenge)")

                    # Try to parse producers
                    soup = BeautifulSoup(response.text, 'html.parser')

                    # Look for title
                    title = soup.find('h1')
                    if title:
                        logger.info(f"Page title: {title.get_text().strip()}")

                    # Count producer mentions
                    producer_count = response.text.lower().count('producer')
                    logger.info(f"Word 'producer' appears {producer_count} times")

                    # Look for person links (IBDB links people with /person/)
                    person_links = soup.find_all('a', href=lambda x: x and '/person/' in x)
                    logger.info(f"Found {len(person_links)} person links on page")

                    # Try to find producers specifically
                    producer_names = set()

                    for link in person_links:
                        parent = link.find_parent(['div', 'p', 'li', 'td', 'tr'])
                        if parent:
                            context = parent.get_text().lower()
                            if 'produc' in context:
                                name = link.get_text().strip()
                                if name:
                                    producer_names.add(name)

                    logger.info(f"Found {len(producer_names)} unique producer names")

                    if len(producer_names) > 0:
                        logger.info(f"First 10 producers: {list(producer_names)[:10]}")

                        diff = abs(len(producer_names) - expected_producers)
                        if diff <= 5:
                            logger.info(f"✓✓✓ CLOSE TO EXPECTED (within ±5)")
                        else:
                            logger.warning(f"Off by {diff} from expected {expected_producers}")

            else:
                logger.error(f"✗ FAILED - Status {response.status_code}")

        except Exception as e:
            logger.error(f"✗ ERROR: {e}")
            import traceback
            traceback.print_exc()

        time.sleep(3)

    logger.info(f"\n{'='*70}")
    logger.info("TEST COMPLETE")
    logger.info(f"{'='*70}")


if __name__ == '__main__':
    test_direct_ibdb_with_cloudscraper()
