#!/usr/bin/env python3
"""
Test if Playbill.com allows scraping and has producer data.
"""

import requests
from bs4 import BeautifulSoup
from utils import setup_logger, get_robust_session
import time

logger = setup_logger(__name__)


def check_playbill_robots():
    """Check Playbill robots.txt."""
    logger.info("Checking Playbill robots.txt...")

    session = get_robust_session()

    try:
        response = session.get("https://www.playbill.com/robots.txt", timeout=30)
        logger.info(f"Status: {response.status_code}")

        if response.status_code == 200:
            logger.info("\nrobots.txt content (first 50 lines):")
            lines = response.text.split('\n')[:50]
            for line in lines:
                logger.info(f"  {line}")
            return True
        else:
            logger.error(f"Could not fetch robots.txt: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"Error: {e}")
        return False


def test_playbill_show_page():
    """Test accessing a known Playbill production page."""
    logger.info("\n" + "="*70)
    logger.info("Testing Playbill show page access")
    logger.info("="*70)

    session = get_robust_session()

    # Test URL - Hamilton on Playbill
    test_url = "https://www.playbill.com/production/hamilton-richard-rodgers-theatre-vault-0000014069"

    try:
        logger.info(f"\nAccessing: {test_url}")
        time.sleep(2)

        response = session.get(test_url, timeout=30)
        logger.info(f"Status code: {response.status_code}")

        if response.status_code == 200:
            logger.info("✓ Successfully accessed Playbill page")

            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for title
            title = soup.find('h1')
            if title:
                logger.info(f"Show title: {title.get_text().strip()}")

            # Look for credits/producer information
            if 'produc' in response.text.lower():
                logger.info("✓ Page contains producer-related content")

                # Look for credits section
                credits = soup.find_all(string=lambda text: text and 'producer' in text.lower())
                if credits:
                    logger.info(f"Found {len(credits)} producer mentions")
                    for i, credit in enumerate(credits[:5]):
                        logger.info(f"  {i+1}. {credit.strip()[:100]}")

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
    logger.info("="*70)
    logger.info("TESTING PLAYBILL.COM AS ALTERNATIVE DATA SOURCE")
    logger.info("="*70)

    robots_ok = check_playbill_robots()
    time.sleep(2)

    page_ok = test_playbill_show_page()

    logger.info("\n" + "="*70)
    if robots_ok and page_ok:
        logger.info("✓✓✓ PLAYBILL ACCESS WORKS! ✓✓✓")
        logger.info("Playbill could be an alternative to IBDB")
    else:
        logger.warning("Playbill access is limited or blocked")
    logger.info("="*70)
