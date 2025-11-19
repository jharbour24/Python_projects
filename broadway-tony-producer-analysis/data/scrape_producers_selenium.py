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
            time.sleep(3)  # Increased wait time

            # Get page source and parse with BeautifulSoup
            from bs4 import BeautifulSoup
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

            # Strategy 1: Look for "Produced by" in page text
            produced_by_elements = soup.find_all(string=re.compile(r'Produced by', re.IGNORECASE))

            if produced_by_elements:
                for elem in produced_by_elements:
                    parent = elem.parent
                    # Look for next sibling or child with producer names
                    producer_container = parent.find_next_sibling() or parent.find_next()

                    if producer_container:
                        producer_text = producer_container.get_text(separator='\n', strip=True)
                        if producer_text and len(producer_text) > 5:
                            logger.info(f"Found producer text (Strategy 1): {producer_text[:100]}...")
                            result = self._parse_producer_text(producer_text, result)
                            if result['scrape_success']:
                                return result

            # Strategy 2: Look for specific IBDB data structures (tables, divs with producer class)
            for class_name in ['staff-role', 'production-staff', 'credits', 'staff-list']:
                producer_sections = soup.find_all(class_=class_name)
                for section in producer_sections:
                    section_text = section.get_text(separator='\n', strip=True)
                    if re.search(r'produc', section_text, re.IGNORECASE):
                        logger.info(f"Found producer section (Strategy 2 - {class_name}): {section_text[:100]}...")
                        result = self._parse_producer_text(section_text, result)
                        if result['scrape_success']:
                            return result

            # Strategy 3: Look in tables (IBDB often uses tables for credits)
            tables = soup.find_all('table')
            for table in tables:
                table_text = table.get_text(separator='\n', strip=True)
                if re.search(r'produc', table_text, re.IGNORECASE):
                    logger.info(f"Found producers in table (Strategy 3): {table_text[:200]}...")
                    result = self._parse_producer_text(table_text, result)
                    if result['scrape_success']:
                        return result

            # Strategy 4: Broad search - any element containing "producer"
            all_text = soup.get_text(separator='\n')
            lines = all_text.split('\n')

            producer_section_lines = []
            in_producer_section = False

            for line in lines:
                if re.search(r'produced?\s+by', line, re.IGNORECASE):
                    in_producer_section = True
                    continue

                if in_producer_section:
                    if line.strip() and not re.search(r'(director|design|music|choreograph)', line, re.IGNORECASE):
                        producer_section_lines.append(line.strip())
                    elif len(producer_section_lines) > 0 and re.search(r'(director|design|music)', line, re.IGNORECASE):
                        break  # End of producer section

                    if len(producer_section_lines) > 20:  # Safety limit
                        break

            if producer_section_lines:
                producer_text = '\n'.join(producer_section_lines)
                logger.info(f"Found producers (Strategy 4 - line parsing): {producer_text[:100]}...")
                result = self._parse_producer_text(producer_text, result)
                if result['scrape_success']:
                    return result

            logger.warning(f"No producer information found on page: {show_url}")
            return result

        except Exception as e:
            logger.error(f"Error scraping producers from {show_url}: {e}")
            return result

    def _parse_producer_text(self, producer_text: str, result: Dict) -> Dict:
        """Parse producer text and update result dictionary."""
        try:
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
            result['scrape_success'] = result['producer_count_total'] > 0

            if result['scrape_success']:
                logger.info(f"Parsed {result['producer_count_total']} producers "
                          f"({result['lead_producer_count']} lead, {result['co_producer_count']} co-producers)")

            return result

        except Exception as e:
            logger.error(f"Error parsing producer text: {e}")
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
