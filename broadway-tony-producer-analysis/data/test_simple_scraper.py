"""
Simple working test of undetected-chromedriver for IBDB scraping.
This version avoids all compatibility issues.

Run this first to verify your setup works before running the full scraper.
"""

import time
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils import setup_logger

logger = setup_logger(__name__)

def test_basic_scraping():
    """Test basic undetected-chromedriver setup."""

    logger.info("="*60)
    logger.info("TESTING UNDETECTED-CHROMEDRIVER SETUP")
    logger.info("="*60)

    # Check imports
    try:
        import undetected_chromedriver as uc
        from bs4 import BeautifulSoup
        logger.info("✓ Required packages installed")
    except ImportError as e:
        logger.error(f"✗ Missing package: {e}")
        logger.info("Install with: pip3 install undetected-chromedriver beautifulsoup4")
        return False

    # Initialize driver (simplest possible way)
    try:
        logger.info("\nInitializing Chrome (this may take 30-60 seconds first time)...")

        # Simplest initialization - let undetected-chromedriver handle everything
        driver = uc.Chrome()

        logger.info("✓ Chrome initialized successfully")

    except Exception as e:
        logger.error(f"✗ Failed to initialize Chrome: {e}")
        logger.info("\nTroubleshooting:")
        logger.info("1. Make sure Google Chrome is installed")
        logger.info("2. Try: pip3 install --upgrade undetected-chromedriver")
        logger.info("3. Close all Chrome windows and try again")
        return False

    # Test IBDB access
    try:
        logger.info("\nTesting IBDB access (Hadestown page)...")
        logger.info("⚠ DO NOT close the browser window that opens!")
        url = "https://www.ibdb.com/broadway-production/hadestown-504445"

        driver.get(url)
        time.sleep(8)  # Wait longer for page load and Cloudflare

        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        # Check for Cloudflare block
        if "Sorry, you have been blocked" in html or "Just a moment" in html:
            logger.error("✗ Cloudflare is blocking access")
            logger.info("This may vary by network/time - try again later")
            driver.quit()
            return False

        # Check what's actually on the page
        page_text = soup.get_text()

        # Show first 2000 chars to see what we got
        logger.info(f"\nFirst 2000 characters of page:")
        logger.info("-" * 60)
        logger.info(page_text[:2000])
        logger.info("-" * 60)

        # Check for Cloudflare challenge page
        if "Checking your browser" in page_text or "Cloudflare" in page_text[:500]:
            logger.warning("⚠ Cloudflare challenge page detected")
            logger.info("Waiting 10 seconds for challenge to complete...")
            time.sleep(10)

            # Try again after waiting
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            page_text = soup.get_text()

        # Check for actual content
        if "Hadestown" in html or "Hadestown" in page_text:
            logger.info("✓ Successfully accessed IBDB page!")
            logger.info("✓ Found Hadestown in page content")

            # Check for producer info
            if "Produced" in html or "producer" in page_text.lower():
                logger.info("✓ Producer information visible on page")

                # Find producer section
                if "Mara Isaacs" in page_text:
                    logger.info("✓ Found Mara Isaacs (lead producer of Hadestown)")

            driver.quit()
            return True
        else:
            logger.warning("⚠ Page loaded but Hadestown content not found")
            logger.info(f"Page length: {len(html)} characters")
            logger.info(f"Text length: {len(page_text)} characters")

            # Check what we did get
            if "404" in page_text or "not found" in page_text.lower():
                logger.error("Page returned 404 - URL may be wrong")

            driver.quit()
            return False

    except Exception as e:
        logger.error(f"✗ Error accessing IBDB: {e}")
        try:
            driver.quit()
        except:
            pass
        return False


if __name__ == '__main__':
    success = test_basic_scraping()

    print("\n" + "="*60)
    if success:
        print("✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("You can now run the full scraper:")
        print("  python3 scrape_all_broadway_shows.py")
    else:
        print("✗✗✗ TESTS FAILED ✗✗✗")
        print("Fix the issues above before running the full scraper")
    print("="*60)
