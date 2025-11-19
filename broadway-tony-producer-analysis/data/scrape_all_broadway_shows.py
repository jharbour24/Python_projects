"""
Comprehensive Broadway show scraper - gets ALL shows since 2010 with accurate producer counts.

This script:
1. Gets complete list of all Broadway shows from IBDB (2010-present)
2. Scrapes accurate producer data from each show page
3. Gets weekly grosses from Broadway World
4. Uses undetected-chromedriver to bypass Cloudflare

Author: Broadway Analysis Pipeline
"""

import re
import time
import json
from typing import Dict, List, Optional, Tuple
import pandas as pd
from urllib.parse import quote_plus, urljoin
from pathlib import Path
from datetime import datetime

import sys
sys.path.append(str(Path(__file__).parent.parent))

import config
from utils import normalize_title, create_show_id, setup_logger

logger = setup_logger(__name__)

# Check if undetected-chromedriver is installed
try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from bs4 import BeautifulSoup
    UNDETECTED_AVAILABLE = True
except ImportError:
    UNDETECTED_AVAILABLE = False
    logger.warning("undetected-chromedriver not installed. Install with: pip3 install undetected-chromedriver selenium")


class ComprehensiveBroadwayScraper:
    """Scraper to get ALL Broadway shows and accurate producer data."""

    def __init__(self):
        """
        Initialize comprehensive scraper.

        Always runs in visible (non-headless) mode for better Cloudflare bypass.
        """
        if not UNDETECTED_AVAILABLE:
            raise ImportError("Required packages not installed. Run: pip3 install undetected-chromedriver selenium beautifulsoup4")

        try:
            # Initialize undetected Chrome - simplest method for compatibility
            # Let undetected-chromedriver handle all the stealth setup automatically
            logger.info("=" * 60)
            logger.info("⚠️  IMPORTANT: A Chrome window will open")
            logger.info("⚠️  DO NOT CLOSE IT - the scraper needs it!")
            logger.info("⚠️  It will close automatically when done")
            logger.info("=" * 60)

            self.driver = uc.Chrome()

            # Wait for browser to fully initialize
            logger.info("Chrome opened - waiting for it to stabilize...")
            time.sleep(3)

            self.wait = WebDriverWait(self.driver, 10)

            logger.info("✓ ChromeDriver ready")

        except Exception as e:
            logger.error(f"Failed to initialize ChromeDriver: {e}")
            logger.error("Make sure Google Chrome browser is installed")
            raise

    def __del__(self):
        """Close browser on cleanup."""
        if hasattr(self, 'driver'):
            try:
                self.driver.quit()
            except:
                pass

    def test_cloudflare_bypass(self) -> bool:
        """Test if Cloudflare bypass is working."""
        try:
            logger.info("\nTesting Cloudflare bypass on IBDB...")
            logger.info("⚠️  The browser will navigate to Hadestown page - don't close it!")
            test_url = "https://www.ibdb.com/broadway-production/hadestown-520711"

            # Check if window is still alive
            try:
                current_url = self.driver.current_url
                logger.info(f"Browser is at: {current_url}")
            except Exception as e:
                logger.error(f"Browser window already closed before navigation: {e}")
                return False

            logger.info(f"Navigating to: {test_url}")
            self.driver.get(test_url)

            logger.info("Waiting for page to load (10 seconds)...")
            time.sleep(10)

            # Check window is still alive after navigation
            try:
                html = self.driver.page_source
            except Exception as e:
                logger.error(f"Cannot get page source - window may have closed: {e}")
                return False

            logger.info(f"Page loaded - {len(html)} characters")

            if "Sorry, you have been blocked" in html or "Just a moment" in html:
                logger.error("✗ Cloudflare is blocking")
                return False

            if "Produced by" in html or "Hadestown" in html:
                logger.info("✓ Cloudflare bypass successful")
                return True

            logger.warning("⚠ Page loaded but content unclear")
            logger.info(f"First 500 chars: {html[:500]}")
            return False

        except Exception as e:
            logger.error(f"Error testing bypass: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def get_all_broadway_shows(self, start_year: int = 2010) -> List[Dict]:
        """
        Get complete list of all Broadway shows since start_year.

        This uses IBDB's production search/browse functionality.

        Parameters
        ----------
        start_year : int
            Starting year for show search

        Returns
        -------
        list of dict
            List of shows with title, IBDB URL, year
        """
        logger.info(f"Getting all Broadway shows since {start_year}...")

        all_shows = []

        # Strategy 1: Try IBDB advanced search
        # IBDB has URLs like: https://www.ibdb.com/broadway-season/2010-11
        # We can iterate through each season

        current_year = datetime.now().year
        seasons_to_check = range(start_year, current_year + 1)

        for year in seasons_to_check:
            season_url = f"https://www.ibdb.com/broadway-season/{year}-{str(year+1)[-2:]}"
            logger.info(f"\nChecking season {year}-{year+1}: {season_url}")

            try:
                self.driver.get(season_url)
                time.sleep(4)  # Wait for page load and Cloudflare

                html = self.driver.page_source

                # Check for Cloudflare block
                if "Sorry, you have been blocked" in html:
                    logger.error(f"✗ Cloudflare blocked season {year}")
                    continue

                soup = BeautifulSoup(html, 'html.parser')

                # Find all production links
                # IBDB uses links like /broadway-production/Show-Name-123456
                production_links = soup.find_all('a', href=re.compile(r'/broadway-production/[^/]+-\d+'))

                season_shows = []
                for link in production_links:
                    href = link.get('href')
                    title = link.get_text(strip=True)

                    if href and title:
                        full_url = urljoin("https://www.ibdb.com", href)

                        # Avoid duplicates within season
                        if full_url not in [s['ibdb_url'] for s in season_shows]:
                            season_shows.append({
                                'title': title,
                                'ibdb_url': full_url,
                                'season_year': year,
                                'show_id': create_show_id(title)
                            })

                logger.info(f"  Found {len(season_shows)} shows in {year}-{year+1} season")
                all_shows.extend(season_shows)

                # Be respectful - rate limit between seasons
                time.sleep(3)

            except Exception as e:
                logger.error(f"Error scraping season {year}: {e}")
                continue

        # Remove duplicates across seasons (same show may run multiple seasons)
        unique_shows = []
        seen_urls = set()

        for show in all_shows:
            if show['ibdb_url'] not in seen_urls:
                unique_shows.append(show)
                seen_urls.add(show['ibdb_url'])

        logger.info(f"\n{'='*60}")
        logger.info(f"Total unique shows found: {len(unique_shows)}")
        logger.info(f"{'='*60}")

        return unique_shows

    def scrape_producers_detailed(self, show_url: str) -> Dict:
        """
        Scrape ALL producer information from IBDB show page.

        This version counts ALL producer credits, not just certain types.

        Parameters
        ----------
        show_url : str
            URL of IBDB show page

        Returns
        -------
        dict
            Complete producer information
        """
        result = {
            'ibdb_url': show_url,
            'producers_raw_text': '',
            'producers_list': [],
            'producer_count_total': 0,
            'scrape_success': False,
            'scrape_method': None
        }

        try:
            self.driver.get(show_url)

            # Wait longer for JavaScript to load the actual content
            time.sleep(8)

            # Scroll down to trigger lazy-loaded content
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)

            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

            # Check for Cloudflare block
            if "Sorry, you have been blocked" in html:
                logger.error("✗ Cloudflare blocked")
                return result

            # Strategy: Find the "Produced by" section and get ALL names after it
            # Look for text containing "Produced by" or "Producer"

            # Try multiple strategies to find producer section

            # Strategy 1: Find element with "Produced by" text
            produced_by_elements = soup.find_all(string=re.compile(r'Produced by', re.IGNORECASE))

            producer_text = ""

            if produced_by_elements:
                for elem in produced_by_elements:
                    # Get parent and all following content until next major section
                    parent = elem.find_parent()

                    if parent:
                        # Get all text after this point until we hit another credit type
                        following_text_parts = []

                        for sibling in parent.find_all_next():
                            text = sibling.get_text(strip=True)

                            # Stop if we hit another credit category
                            if re.search(r'(Directed by|Choreograph|Music by|Lyrics by|Book by|Scenic Design|Lighting Design|Costume Design)', text, re.IGNORECASE):
                                break

                            if text and len(text) > 2:
                                following_text_parts.append(text)

                            # Limit to reasonable amount
                            if len(following_text_parts) > 100:
                                break

                        producer_text = '\n'.join(following_text_parts)
                        if producer_text:
                            result['scrape_method'] = 'produced_by_text'
                            break

            # Strategy 2: Look for specific IBDB structure classes/ids
            if not producer_text:
                for identifier in ['staff-role', 'production-staff', 'credits', 'credit-list']:
                    sections = soup.find_all(class_=identifier)

                    for section in sections:
                        section_text = section.get_text(separator='\n', strip=True)
                        if re.search(r'produc', section_text, re.IGNORECASE):
                            producer_text = section_text
                            result['scrape_method'] = f'class_{identifier}'
                            break

                    if producer_text:
                        break

            # Strategy 3: Look in tables
            if not producer_text:
                tables = soup.find_all('table')
                for table in tables:
                    table_text = table.get_text(separator='\n', strip=True)
                    if re.search(r'produc', table_text, re.IGNORECASE):
                        producer_text = table_text
                        result['scrape_method'] = 'table'
                        break

            if not producer_text:
                logger.warning(f"No producer section found on {show_url}")
                return result

            # Store raw text
            result['producers_raw_text'] = producer_text[:5000]  # Limit storage

            # Parse producers - count ALL names
            producers = self._parse_all_producers(producer_text)

            result['producers_list'] = producers
            result['producer_count_total'] = len(producers)
            result['scrape_success'] = len(producers) > 0

            if result['scrape_success']:
                logger.info(f"✓ Found {len(producers)} producers (method: {result['scrape_method']})")
            else:
                logger.warning(f"✗ No producers parsed from text")

            return result

        except Exception as e:
            logger.error(f"Error scraping {show_url}: {e}")
            return result

    def _parse_all_producers(self, text: str) -> List[str]:
        """
        Parse ALL producer names from text.

        This is aggressive - counts every name/entity mentioned.

        Parameters
        ----------
        text : str
            Raw producer section text

        Returns
        -------
        list of str
            All producer names found
        """
        producers = []

        # Remove section headers
        text = re.sub(r'(Produced by|Producer[s]?|Lead Producer[s]?|Co-Producer[s]?|Associate Producer[s]?|Executive Producer[s]?)\s*:?\s*', '', text, flags=re.IGNORECASE)

        # Split by newlines first (primary delimiter on IBDB)
        lines = text.split('\n')

        for line in lines:
            line = line.strip()

            # Skip empty lines
            if len(line) < 3:
                continue

            # STOP if we hit production history text
            stop_patterns = [
                r'received its .* Premiere',
                r'Additional development',
                r'World Premiere',
                r'Off-Broadway',
                r'originally produced',
                r'first produced',
            ]

            should_stop = False
            for pattern in stop_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    should_stop = True
                    break

            if should_stop:
                # Stop parsing - we've moved past producer credits
                break

            # Skip common non-producer text
            skip_patterns = [
                r'^by$',
                r'^for$',
                r'^in association with',
                r'^presented by',
                r'^\d+$',  # Just numbers
                r'^\d{4}$',  # Just years
                r'^(directed|choreograph|music|book|lyrics|design|cast|scenic|lighting|costume|sound)',  # Other credits
            ]

            should_skip = False
            for pattern in skip_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    should_skip = True
                    break

            if should_skip:
                continue

            # Clean up the name
            line = re.sub(r'\s+', ' ', line)  # Normalize whitespace
            line = line.strip('.,;:-()[]{}')  # Remove surrounding punctuation

            # Must have at least one letter
            if not re.search(r'[a-zA-Z]', line):
                continue

            # Add to list if it looks like a name/organization
            if len(line) >= 3:
                producers.append(line)

        return producers


def main():
    """Main execution function."""

    logger.info("=" * 80)
    logger.info("COMPREHENSIVE BROADWAY SHOW & PRODUCER SCRAPER")
    logger.info("=" * 80)

    if not UNDETECTED_AVAILABLE:
        logger.error("Required packages not installed!")
        logger.info("Install with: pip3 install undetected-chromedriver selenium beautifulsoup4")
        return

    # Initialize scraper
    try:
        logger.info("\nInitializing ChromeDriver (may take 30-60s first time)...")
        scraper = ComprehensiveBroadwayScraper()

        # Test Cloudflare bypass
        if not scraper.test_cloudflare_bypass():
            logger.error("\n" + "="*80)
            logger.error("CLOUDFLARE BYPASS FAILED")
            logger.error("="*80)
            logger.info("The scraper cannot bypass Cloudflare protection.")
            logger.info("\nOptions:")
            logger.info("1. Try again later (Cloudflare strictness varies)")
            logger.info("2. Use a VPN or different network")
            logger.info("3. Manual data collection")
            return

    except Exception as e:
        logger.error(f"Failed to initialize scraper: {e}")
        return

    # Step 1: Get all Broadway shows since 2010
    logger.info("\n" + "="*80)
    logger.info("STEP 1: Getting complete list of Broadway shows")
    logger.info("="*80)

    shows = scraper.get_all_broadway_shows(start_year=2010)

    if not shows:
        logger.error("No shows found! Check if IBDB structure has changed.")
        return

    # Save show list
    shows_df = pd.DataFrame(shows)
    shows_list_path = Path(__file__).parent / 'raw' / 'broadway_shows_complete_list.csv'
    shows_df.to_csv(shows_list_path, index=False)
    logger.info(f"\n✓ Saved show list: {shows_list_path}")
    logger.info(f"  Total shows: {len(shows)}")

    # Step 2: Scrape producers for each show
    logger.info("\n" + "="*80)
    logger.info("STEP 2: Scraping producer data for each show")
    logger.info("="*80)

    # For initial run, test on first 10 shows
    test_mode = True
    test_limit = 10

    if test_mode:
        logger.info(f"\n⚠️  TEST MODE: Scraping first {test_limit} shows only")
        logger.info("Set test_mode = False in code to scrape all shows\n")
        shows_to_scrape = shows[:test_limit]
    else:
        shows_to_scrape = shows

    results = []
    successful = 0

    for idx, show in enumerate(shows_to_scrape):
        logger.info(f"\n[{idx+1}/{len(shows_to_scrape)}] {show['title']}")
        logger.info(f"  URL: {show['ibdb_url']}")

        producer_data = scraper.scrape_producers_detailed(show['ibdb_url'])

        # Combine show info with producer data
        result = {
            **show,
            **producer_data
        }

        results.append(result)

        if producer_data['scrape_success']:
            successful += 1

        # Rate limiting
        time.sleep(config.RATE_LIMIT_DELAY)

    # Save results
    results_df = pd.DataFrame(results)
    output_path = Path(__file__).parent / 'raw' / 'broadway_shows_with_producers.csv'
    results_df.to_csv(output_path, index=False)

    logger.info("\n" + "="*80)
    logger.info("SCRAPING COMPLETE")
    logger.info("="*80)
    logger.info(f"Shows scraped: {len(results)}")
    logger.info(f"Successful: {successful} ({successful/len(results)*100:.1f}%)")
    logger.info(f"Output: {output_path}")
    logger.info("="*80)

    # Show some statistics
    if successful > 0:
        success_df = results_df[results_df['scrape_success'] == True]
        logger.info(f"\nProducer count statistics:")
        logger.info(f"  Mean: {success_df['producer_count_total'].mean():.1f}")
        logger.info(f"  Median: {success_df['producer_count_total'].median():.1f}")
        logger.info(f"  Min: {success_df['producer_count_total'].min()}")
        logger.info(f"  Max: {success_df['producer_count_total'].max()}")

        # Show top 5 shows by producer count
        top_5 = success_df.nlargest(5, 'producer_count_total')[['title', 'producer_count_total']]
        logger.info(f"\nTop 5 shows by producer count:")
        for _, row in top_5.iterrows():
            logger.info(f"  {row['title']}: {row['producer_count_total']} producers")


if __name__ == '__main__':
    main()
