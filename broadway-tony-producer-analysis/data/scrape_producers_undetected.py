"""
Advanced producer count scraper using undetected-chromedriver to bypass Cloudflare.

This version uses undetected-chromedriver, a patched version of ChromeDriver that
is much harder for Cloudflare and other anti-bot systems to detect.

Installation:
    pip3 install undetected-chromedriver beautifulsoup4

Author: Broadway Analysis Pipeline
"""

import re
import time
from typing import Dict, List, Optional
import pandas as pd
from urllib.parse import quote_plus
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).parent.parent))

import config
from utils import normalize_title, create_show_id, parse_producer_list, setup_logger

logger = setup_logger(__name__)

# Check if undetected-chromedriver is installed
try:
    import undetected_chromedriver as uc
    from bs4 import BeautifulSoup
    UNDETECTED_AVAILABLE = True
except ImportError:
    UNDETECTED_AVAILABLE = False
    logger.warning("undetected-chromedriver not installed. Install with: pip3 install undetected-chromedriver")


class UndetectedProducerScraper:
    """Scraper using undetected-chromedriver to bypass Cloudflare protection."""

    def __init__(self, headless: bool = False):
        """
        Initialize undetected scraper.

        Parameters
        ----------
        headless : bool
            Run browser in headless mode (note: headless mode is more detectable)
        """
        if not UNDETECTED_AVAILABLE:
            raise ImportError("undetected-chromedriver not installed. Run: pip3 install undetected-chromedriver")

        try:
            # Initialize undetected Chrome
            options = uc.ChromeOptions()

            if headless:
                # Headless mode (more likely to be detected)
                options.add_argument('--headless=new')

            # Additional stealth options
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--no-sandbox')
            options.add_argument(f'user-agent={config.USER_AGENT}')

            # Create driver with undetected-chromedriver
            self.driver = uc.Chrome(options=options, version_main=None)

            # Set realistic window size
            self.driver.set_window_size(1920, 1080)

            logger.info("Undetected ChromeDriver initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize undetected ChromeDriver: {e}")
            raise

    def __del__(self):
        """Close browser on cleanup."""
        if hasattr(self, 'driver'):
            try:
                self.driver.quit()
            except:
                pass

    def test_cloudflare_bypass(self) -> bool:
        """
        Test if Cloudflare bypass is working.

        Returns
        -------
        bool
            True if bypass successful, False otherwise
        """
        try:
            logger.info("Testing Cloudflare bypass...")
            test_url = "https://www.ibdb.com/broadway-production/Hamilton-499521"

            self.driver.get(test_url)
            time.sleep(5)  # Wait for Cloudflare check

            html = self.driver.page_source

            # Check for Cloudflare block
            if "Sorry, you have been blocked" in html or "Just a moment" in html:
                logger.error("Cloudflare is still blocking")
                return False

            # Check for actual content
            if "Produced by" in html or "Producer" in html:
                logger.info("✓ Cloudflare bypass successful!")
                return True

            logger.warning("Page loaded but no producer data found")
            return False

        except Exception as e:
            logger.error(f"Error testing Cloudflare bypass: {e}")
            return False

    def search_ibdb(self, title: str) -> Optional[str]:
        """
        Search IBDB for a show.

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
            # Try direct URL first (most reliable)
            direct_url = f"https://www.ibdb.com/broadway-production/{quote_plus(title)}"
            logger.info(f"Trying direct URL: {direct_url}")

            self.driver.get(direct_url)
            time.sleep(3)  # Wait for page load and Cloudflare check

            # Check if we're on a valid show page
            html = self.driver.page_source

            if "Page Not Found" not in html and "404" not in html:
                logger.info(f"Found direct match: {direct_url}")
                return direct_url

            # Otherwise use search
            search_url = f"https://www.ibdb.com/search?q={quote_plus(title)}&type=production"
            logger.info(f"Searching: {search_url}")

            self.driver.get(search_url)
            time.sleep(3)

            # Find first production link
            try:
                # Look for links containing 'broadway-production'
                links = self.driver.find_elements("xpath", "//a[contains(@href, '/broadway-production/')]")

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
            time.sleep(4)  # Wait for page load and Cloudflare

            # Get page source and parse
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

            # Check for Cloudflare block
            if "Sorry, you have been blocked" in html:
                logger.error("Cloudflare blocked this request")
                return result

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

            # Strategy 2: Look for specific IBDB data structures
            for class_name in ['staff-role', 'production-staff', 'credits', 'staff-list']:
                producer_sections = soup.find_all(class_=class_name)
                for section in producer_sections:
                    section_text = section.get_text(separator='\n', strip=True)
                    if re.search(r'produc', section_text, re.IGNORECASE):
                        logger.info(f"Found producer section (Strategy 2 - {class_name}): {section_text[:100]}...")
                        result = self._parse_producer_text(section_text, result)
                        if result['scrape_success']:
                            return result

            # Strategy 3: Look in tables
            tables = soup.find_all('table')
            for table in tables:
                table_text = table.get_text(separator='\n', strip=True)
                if re.search(r'produc', table_text, re.IGNORECASE):
                    logger.info(f"Found producers in table (Strategy 3): {table_text[:200]}...")
                    result = self._parse_producer_text(table_text, result)
                    if result['scrape_success']:
                        return result

            # Strategy 4: Broad line parsing
            all_text = soup.get_text(separator='\n')
            lines = all_text.split('\n')

            producer_section_lines = []
            in_producer_section = False

            for line in lines:
                if re.search(r'produced?\\s+by', line, re.IGNORECASE):
                    in_producer_section = True
                    continue

                if in_producer_section:
                    if line.strip() and not re.search(r'(director|design|music|choreograph)', line, re.IGNORECASE):
                        producer_section_lines.append(line.strip())
                    elif len(producer_section_lines) > 0 and re.search(r'(director|design|music)', line, re.IGNORECASE):
                        break

                    if len(producer_section_lines) > 20:
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
    logger.info("BROADWAY PRODUCER SCRAPER (UNDETECTED CHROMEDRIVER)")
    logger.info("=" * 60)

    if not UNDETECTED_AVAILABLE:
        logger.error("undetected-chromedriver not installed!")
        logger.info("Install with: pip3 install undetected-chromedriver beautifulsoup4")
        return

    # Load shows to scrape - try top 200 template first, fall back to Tony list
    template_path = Path(__file__).parent / 'raw' / 'top_200_shows_producer_template.csv'
    tony_path = Path(__file__).parent / 'raw' / 'tony_outcomes_aggregated.csv'

    if template_path.exists():
        logger.info(f"Loading top 200 shows from {template_path}")
        df = pd.read_csv(template_path)
        # Only scrape shows that are still pending
        df = df[df['data_quality'] == 'pending']
        logger.info(f"Found {len(df)} shows pending scraping")
    elif tony_path.exists():
        logger.info(f"Loading Tony nominees from {tony_path}")
        df = pd.read_csv(tony_path)
        logger.info(f"Loaded {len(df)} shows from Tony outcomes")
    else:
        logger.error("No show list found!")
        logger.info("Run create_top200_template.py first")
        return

    # Initialize scraper
    try:
        logger.info("\nInitializing undetected ChromeDriver...")
        logger.info("This may take 30-60 seconds on first run...")
        scraper = UndetectedProducerScraper(headless=False)

        # Test bypass
        if not scraper.test_cloudflare_bypass():
            logger.error("\n⚠️  Cloudflare bypass test FAILED")
            logger.info("Cloudflare protection is still detecting the bot")
            logger.info("\nOptions:")
            logger.info("1. Try running with headless=False (more human-like)")
            logger.info("2. Use manual data collection with the template CSV")
            logger.info("3. Wait and try again later (Cloudflare may be having a strict period)")
            return

    except Exception as e:
        logger.error(f"Failed to initialize undetected scraper: {e}")
        logger.info("\nTroubleshooting:")
        logger.info("1. Install: pip3 install undetected-chromedriver")
        logger.info("2. Make sure Chrome browser is installed")
        logger.info("3. Try updating Chrome to latest version")
        return

    results = []
    successful = 0

    # Limit to first 10 shows for testing
    test_limit = 10
    logger.info(f"\n⚠️  Testing mode: scraping first {test_limit} shows only")
    logger.info("Remove test_limit in code to scrape all shows\n")

    for idx, row in df.head(test_limit).iterrows():
        title = row['title']

        logger.info(f"\n[{idx+1}/{min(len(df), test_limit)}] Scraping: {title}")

        # Search for show
        show_url = scraper.search_ibdb(title)

        if not show_url:
            logger.warning(f"Could not find IBDB page for: {title}")
            result = {
                'title': title,
                'ibdb_url': None,
                'scrape_success': False,
                'producer_count_total': None,
                'lead_producer_count': None,
                'co_producer_count': None,
            }
            results.append(result)
            continue

        # Scrape producers from show page
        producer_data = scraper.scrape_producers(show_url)

        # Combine with show info
        result = {
            'title': title,
            **producer_data
        }

        results.append(result)

        if producer_data['scrape_success']:
            successful += 1
            logger.info(f"✓ Success: {producer_data['producer_count_total']} producers found")
        else:
            logger.warning(f"✗ Failed to extract producer data")

        # Rate limiting - be respectful to IBDB
        time.sleep(config.RATE_LIMIT_DELAY)

    # Save results
    results_df = pd.DataFrame(results)

    output_path = Path(__file__).parent / 'raw' / 'producers_undetected_results.csv'
    results_df.to_csv(output_path, index=False)
    logger.info(f"\n{'=' * 60}")
    logger.info(f"Saved results to {output_path}")
    logger.info(f"Successfully scraped {successful} / {len(results)} shows ({successful/len(results)*100:.1f}%)")
    logger.info(f"{'=' * 60}")

    # If successful, merge with template
    if successful > 0 and template_path.exists():
        logger.info("\nUpdating template with scraped data...")
        template = pd.read_csv(template_path)

        for _, result in results_df[results_df['scrape_success'] == True].iterrows():
            mask = template['title'] == result['title']
            template.loc[mask, 'ibdb_url'] = result['ibdb_url']
            template.loc[mask, 'producer_count_total'] = result['producer_count_total']
            template.loc[mask, 'lead_producer_count'] = result['lead_producer_count']
            template.loc[mask, 'co_producer_count'] = result['co_producer_count']
            template.loc[mask, 'data_quality'] = 'scraped'

        template.to_csv(template_path, index=False)
        logger.info(f"Updated {template_path}")


if __name__ == '__main__':
    main()
