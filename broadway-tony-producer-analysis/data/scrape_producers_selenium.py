"""
Producer count scraper using Selenium (browser automation) to bypass IBDB bot protection.

This version uses a real Chrome browser to access IBDB, avoiding 403/429 errors.

Author: Broadway Analysis Pipeline
"""

import re
import time
from typing import Dict, List, Optional
import pandas as pd
from urllib.parse import quote_plus

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import config
from utils import normalize_title, create_show_id, parse_producer_list, setup_logger

logger = setup_logger(__name__)

# Check if Selenium is installed
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.warning("Selenium not installed. Install with: pip3 install selenium webdriver-manager")


class SeleniumProducerScraper:
    """Scraper using Selenium browser automation to bypass IBDB bot protection."""

    def __init__(self, headless: bool = True):
        """
        Initialize Selenium scraper.

        Parameters
        ----------
        headless : bool
            Run browser in headless mode (no GUI)
        """
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium not installed. Run: pip3 install selenium webdriver-manager")

        # Set up Chrome options
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Add user agent
        chrome_options.add_argument(f'user-agent={config.USER_AGENT}')

        # Initialize driver
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Selenium Chrome driver initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            logger.info("Trying Firefox as fallback...")
            try:
                from selenium.webdriver.firefox.service import Service as FirefoxService
                from selenium.webdriver.firefox.options import Options as FirefoxOptions
                from webdriver_manager.firefox import GeckoDriverManager

                firefox_options = FirefoxOptions()
                if headless:
                    firefox_options.add_argument("--headless")
                firefox_service = FirefoxService(GeckoDriverManager().install())
                self.driver = webdriver.Firefox(service=firefox_service, options=firefox_options)
                logger.info("Selenium Firefox driver initialized")
            except Exception as e2:
                raise RuntimeError(f"Failed to initialize both Chrome and Firefox: {e}, {e2}")

    def __del__(self):
        """Close browser on cleanup."""
        if hasattr(self, 'driver'):
            self.driver.quit()

    def search_ibdb(self, title: str) -> Optional[str]:
        """
        Search IBDB for a show using Selenium.

        Parameters
        ----------
        title : str
            Show title to search

        Returns
        -------
        str or None
            URL of the show page, or None if not found
        """
        try:
            # Try direct URL first
            direct_url = f"https://www.ibdb.com/broadway-production/{quote_plus(title)}"
            logger.info(f"Trying direct URL: {direct_url}")

            self.driver.get(direct_url)
            time.sleep(2)  # Wait for page load

            # Check if we're on a valid show page
            if "Page Not Found" not in self.driver.page_source:
                logger.info(f"Found direct match: {direct_url}")
                return direct_url

            # Otherwise use search
            search_url = f"https://www.ibdb.com/search?q={quote_plus(title)}&type=production"
            logger.info(f"Searching: {search_url}")

            self.driver.get(search_url)
            time.sleep(2)

            # Find first production link
            try:
                # Look for links containing 'broadway-production'
                links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/broadway-production/')]")

                if links:
                    first_link = links[0]
                    href = first_link.get_attribute('href')
                    logger.info(f"Found search result: {href}")
                    return href
                else:
                    logger.warning(f"No production links found for: {title}")
                    return None

            except Exception as e:
                logger.error(f"Error finding links: {e}")
                return None

        except Exception as e:
            logger.error(f"Error searching IBDB for {title}: {e}")
            return None

    def scrape_producers(self, show_url: str) -> Dict:
        """
        Scrape producer information from an IBDB show page.

        Parameters
        ----------
        show_url : str
            URL of IBDB show page

        Returns
        -------
        dict
            Producer information
        """
        result = {
            'ibdb_url': show_url,
            'producers_list': [],
            'lead_producers_list': [],
            'co_producers_list': [],
            'producer_count_total': 0,
            'lead_producer_count': 0,
            'co_producer_count': 0,
            'scrape_success': False
        }

        try:
            self.driver.get(show_url)
            time.sleep(2)

            # Look for "Produced by" section
            # IBDB typically has this in a div or section
            page_text = self.driver.page_source

            # Try to find producer section with various selectors
            producer_elements = self.driver.find_elements(By.XPATH,
                "//*[contains(text(), 'Produced by') or contains(text(), 'Producer')]")

            if not producer_elements:
                logger.warning(f"No producer information found on page: {show_url}")
                return result

            # Get the parent element that contains the producer list
            for elem in producer_elements:
                try:
                    # Get text from parent or sibling elements
                    parent = elem.find_element(By.XPATH, "..")
                    producer_text = parent.text

                    if producer_text and len(producer_text) > 10:
                        logger.info(f"Found producer text: {producer_text[:100]}...")

                        # Parse the producer text
                        lead_producers = []
                        co_producers = []

                        # Check for explicit sections
                        if re.search(r'lead producer', producer_text, re.IGNORECASE):
                            sections = re.split(r'\n\s*(?=Lead Producer|Co-Producer)', producer_text, flags=re.IGNORECASE)
                            for section in sections:
                                if re.match(r'lead producer', section, re.IGNORECASE):
                                    section_text = re.sub(r'^lead producer[s]?\s*:?\s*', '', section, flags=re.IGNORECASE)
                                    lead_producers.extend(parse_producer_list(section_text))
                                elif re.match(r'co-?producer', section, re.IGNORECASE):
                                    section_text = re.sub(r'^co-?producer[s]?\s*:?\s*', '', section, flags=re.IGNORECASE)
                                    co_producers.extend(parse_producer_list(section_text))
                        else:
                            # No explicit distinction
                            all_producers = parse_producer_list(producer_text)
                            lead_producers = all_producers
                            co_producers = []

                        result['producers_list'] = lead_producers + co_producers
                        result['lead_producers_list'] = lead_producers
                        result['co_producers_list'] = co_producers
                        result['producer_count_total'] = len(result['producers_list'])
                        result['lead_producer_count'] = len(lead_producers)
                        result['co_producer_count'] = len(co_producers)
                        result['scrape_success'] = True

                        logger.info(f"Found {result['producer_count_total']} producers "
                                  f"({result['lead_producer_count']} lead, {result['co_producer_count']} co-producers)")

                        break

                except Exception as e:
                    logger.debug(f"Error parsing producer element: {e}")
                    continue

            return result

        except Exception as e:
            logger.error(f"Error scraping producers from {show_url}: {e}")
            return result


def main():
    """Main scraping function."""

    logger.info("=" * 60)
    logger.info("BROADWAY PRODUCER SCRAPER (SELENIUM)")
    logger.info("=" * 60)

    if not SELENIUM_AVAILABLE:
        logger.error("Selenium not installed!")
        logger.info("Install with: pip3 install selenium webdriver-manager")
        return

    # Load Tony outcomes to get show list
    tony_path = Path(__file__).parent / 'raw' / 'tony_outcomes_aggregated.csv'

    if not tony_path.exists():
        logger.error(f"Tony outcomes file not found: {tony_path}")
        logger.info("Run scrape_tonys.py first")
        return

    tony_df = pd.read_csv(tony_path)
    logger.info(f"Loaded {len(tony_df)} shows from Tony outcomes")

    # Initialize scraper
    try:
        scraper = SeleniumProducerScraper(headless=True)
    except Exception as e:
        logger.error(f"Failed to initialize Selenium scraper: {e}")
        logger.info("\nTroubleshooting:")
        logger.info("1. Install Chrome or Firefox browser")
        logger.info("2. Install Selenium: pip3 install selenium webdriver-manager")
        logger.info("3. If issues persist, try running with headless=False to see browser")
        return

    results = []
    successful = 0

    for idx, row in tony_df.iterrows():
        title = row['title']
        year = row['tony_year']

        logger.info(f"\nScraping producers for: {title} ({year})")

        # Search for show
        show_url = scraper.search_ibdb(title)

        if not show_url:
            logger.warning(f"Could not find IBDB page for: {title}")
            result = {
                'title': title,
                'tony_year': year,
                'ibdb_url': None,
                'scrape_success': False,
                'producer_count_total': None,
                'lead_producer_count': None,
                'co_producer_count': None,
                'producers_list': None,
                'lead_producers_list': None,
                'co_producers_list': None,
            }
            results.append(result)
            continue

        # Scrape producers from show page
        producer_data = scraper.scrape_producers(show_url)

        # Combine with show info
        result = {
            'title': title,
            'tony_year': year,
            **producer_data
        }

        results.append(result)

        if producer_data['scrape_success']:
            successful += 1

        # Rate limiting - be respectful to IBDB
        time.sleep(config.RATE_LIMIT_DELAY)

    # Save results
    df = pd.DataFrame(results)

    raw_path = Path(__file__).parent / 'raw' / 'producers_raw_selenium.csv'
    df.to_csv(raw_path, index=False)
    logger.info(f"\nSaved raw producer data to {raw_path}")

    # Create clean version
    clean_df = df[['title', 'tony_year', 'producer_count_total', 'lead_producer_count',
                    'co_producer_count', 'scrape_success']].copy()

    clean_path = Path(__file__).parent / 'raw' / 'producers_clean_selenium.csv'
    clean_df.to_csv(clean_path, index=False)
    logger.info(f"Saved cleaned producer data to {clean_path}")

    logger.info(f"\nSuccessfully scraped {successful} / {len(tony_df)} shows")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
