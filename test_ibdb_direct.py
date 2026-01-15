#!/usr/bin/env python3
"""
Test if we can access IBDB production pages directly (even if home page is blocked).
"""

import requests
from bs4 import BeautifulSoup
from utils import setup_logger, get_robust_session
import time

logger = setup_logger(__name__)


def test_known_ibdb_urls():
    """Test accessing known IBDB production URLs directly."""

    # Known valid IBDB production URLs (these are real shows)
    test_urls = [
        "https://www.ibdb.com/broadway-production/hamilton-499521",
        "https://www.ibdb.com/broadway-production/hadestown-509022",
        "https://www.ibdb.com/broadway-production/the-book-of-mormon-465783",
    ]

    session = get_robust_session()

    logger.info("="*70)
    logger.info("Testing direct access to known IBDB production pages")
    logger.info("="*70)

    results = []

    for url in test_urls:
        logger.info(f"\nTesting: {url}")
        time.sleep(3)  # Be polite

        try:
            response = session.get(url, timeout=30)

            if response.status_code == 200:
                logger.info(f"✓ SUCCESS - Got 200 OK")

                # Check if we got actual content
                soup = BeautifulSoup(response.text, 'html.parser')
                title_tag = soup.find('h1')
                if title_tag:
                    logger.info(f"  Page title: {title_tag.get_text().strip()}")

                # Check for producer information
                if 'produc' in response.text.lower():
                    logger.info(f"  ✓ Page contains producer information")
                    results.append((url, True, "Success"))
                else:
                    logger.warning(f"  ⚠ Page might not have producer info")
                    results.append((url, True, "No producer info found"))
            else:
                logger.error(f"✗ FAILED - Status {response.status_code}")
                results.append((url, False, f"HTTP {response.status_code}"))

        except requests.exceptions.HTTPError as e:
            logger.error(f"✗ FAILED - HTTP Error: {e}")
            results.append((url, False, str(e)))
        except Exception as e:
            logger.error(f"✗ FAILED - Error: {e}")
            results.append((url, False, str(e)))

    # Summary
    logger.info("\n" + "="*70)
    logger.info("SUMMARY")
    logger.info("="*70)

    successful = sum(1 for _, success, _ in results if success)
    logger.info(f"Successful: {successful}/{len(test_urls)}")

    for url, success, message in results:
        status = "✓" if success else "✗"
        show_name = url.split('/')[-1].split('-')[:-1]
        show_name = ' '.join(show_name).title()
        logger.info(f"{status} {show_name}: {message}")

    if successful > 0:
        logger.info("\n✓✓✓ Direct IBDB production page access works!")
        logger.info("We can proceed with scraping if we can find the right URLs")
    else:
        logger.error("\n✗✗✗ IBDB production pages are also blocked")
        logger.error("We need an alternative data source")

    return successful > 0


if __name__ == '__main__':
    success = test_known_ibdb_urls()
    exit(0 if success else 1)
