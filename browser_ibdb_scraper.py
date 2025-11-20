"""
Browser-based IBDB scraper using Selenium.

This scraper opens a real browser (Chrome or Safari) and automates the search process:
1. Searches Google for "[show name] IBDB"
2. Clicks the first IBDB result
3. Counts producers on the page
4. Moves to the next show

This approach mimics human behavior and is harder to block than pure HTTP requests.
"""

import logging
import re
import time
from typing import Dict, Optional
from urllib.parse import quote_plus

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class BrowserIBDBScraper:
    """Scrapes IBDB using browser automation (Selenium)."""

    def __init__(self, browser='chrome', headless=False):
        """
        Initialize the browser-based scraper.

        Args:
            browser: 'chrome' or 'safari'
            headless: Run browser in headless mode (no visible window)
        """
        self.browser_name = browser.lower()
        self.headless = headless
        self.driver = None
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def start_browser(self):
        """Start the browser driver."""
        self.logger.info(f"Starting {self.browser_name} browser...")

        try:
            if self.browser_name == 'chrome':
                options = webdriver.ChromeOptions()
                if self.headless:
                    options.add_argument('--headless')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)

                self.driver = webdriver.Chrome(options=options)

            elif self.browser_name == 'safari':
                # Safari doesn't support headless mode
                if self.headless:
                    self.logger.warning("Safari doesn't support headless mode, running visible")

                self.driver = webdriver.Safari()

            else:
                raise ValueError(f"Unsupported browser: {self.browser_name}")

            self.driver.implicitly_wait(10)
            self.logger.info("✓ Browser started successfully")

        except Exception as e:
            self.logger.error(f"Failed to start browser: {e}")
            raise

    def close_browser(self):
        """Close the browser."""
        if self.driver:
            self.driver.quit()
            self.logger.info("Browser closed")

    def search_and_scrape(self, show_name: str) -> Dict:
        """
        Search for a show on IBDB and scrape producer data.

        Args:
            show_name: Name of the Broadway show

        Returns:
            Dictionary with scraping results
        """
        result = {
            'show_name': show_name,
            'ibdb_url': None,
            'num_total_producers': None,
            'scrape_status': 'pending',
            'scrape_notes': ''
        }

        try:
            self.logger.info(f"\n{'='*70}")
            self.logger.info(f"Processing: {show_name}")
            self.logger.info(f"{'='*70}")

            # Step 1: Search Google
            # Add year range to prioritize recent productions (2010-2025)
            search_query = f"{show_name} IBDB Broadway 2010..2025"
            google_url = f"https://www.google.com/search?q={quote_plus(search_query)}"

            self.logger.info(f"Searching Google: {search_query}")
            self.driver.get(google_url)

            # Wait a bit for page to load
            time.sleep(2)

            # Step 2: Find and click first IBDB link
            ibdb_link = None

            try:
                # Look for IBDB links in search results
                links = self.driver.find_elements(By.TAG_NAME, 'a')

                for link in links:
                    href = link.get_attribute('href')
                    if href and 'ibdb.com/broadway-production' in href:
                        ibdb_link = href
                        self.logger.info(f"✓ Found IBDB link: {ibdb_link}")
                        break

                if not ibdb_link:
                    result['scrape_status'] = 'not_found'
                    result['scrape_notes'] = 'No IBDB link found in Google results'
                    self.logger.warning("⚠ No IBDB link found")
                    return result

            except Exception as e:
                result['scrape_status'] = 'search_failed'
                result['scrape_notes'] = f'Google search error: {str(e)}'
                self.logger.error(f"Error finding IBDB link: {e}")
                return result

            # Step 3: Navigate to IBDB page
            self.logger.info("Navigating to IBDB page...")
            self.driver.get(ibdb_link)
            result['ibdb_url'] = ibdb_link

            # Wait for page to load
            time.sleep(3)

            # Step 4: Extract producer information using Selenium element finding
            producer_data = self.parse_producers_from_page(show_name)

            if producer_data['num_total_producers'] is not None and producer_data['num_total_producers'] > 0:
                result['num_total_producers'] = producer_data['num_total_producers']
                result['scrape_status'] = 'success'
                result['scrape_notes'] = 'Successfully scraped'
                self.logger.info(f"✓ SUCCESS: Found {producer_data['num_total_producers']} total producers")
            else:
                result['scrape_status'] = 'parse_failed'
                result['scrape_notes'] = 'Could not find producer information on page'
                self.logger.warning("⚠ Could not parse producer count")

            return result

        except Exception as e:
            result['scrape_status'] = 'error'
            result['scrape_notes'] = f'Error: {str(e)}'
            self.logger.error(f"Error scraping {show_name}: {e}")
            return result

    def parse_producers_from_page(self, show_name: str) -> Dict:
        """
        Parse ALL producers from IBDB page (counts all types together).

        Args:
            show_name: Name of show (for logging)

        Returns:
            Dictionary with total producer count
        """
        all_producers = set()

        try:
            # Get all text on the page
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text

            # Find ALL producer-related text using a broad regex
            # This captures: Lead Producer, Produced by, Co-Produced by, Associate Producer, in association with
            # Note: We allow semicolons in the match because they can appear inside parentheses
            producer_pattern = r'(?:Lead Producer[s]?:|Produced by|Co-Produced by|Associate Producer[s]?:|in association with)\s+(.+?)(?:\n\n|Credits|Directed|Written|Choreograph|Scenic Design|Costume Design|Lighting Design|Sound Design|Music Director|Musical Director|General Management|Company Management)'

            matches = re.finditer(producer_pattern, page_text, re.IGNORECASE)

            for match in matches:
                producer_text = match.group(1)

                # First remove ALL parenthetical notes (including those with semicolons inside)
                # Use a loop to handle nested or multiple parentheticals
                while '(' in producer_text:
                    producer_text = re.sub(r'\([^)]*\)', '', producer_text)

                # Now split by semicolons (which separate different producer sections)
                # Each section after semicolon might be a new category (e.g., "Produced by X; Associate Producer: Y")
                sections = producer_text.split(';')

                for section in sections:
                    # Skip sections that start with a producer category label (we'll catch those separately)
                    if re.match(r'^\s*(?:Lead Producer|Co-Produced|Associate Producer|in association)', section, re.IGNORECASE):
                        continue

                    # Replace " and " with comma
                    section = re.sub(r'\s+and\s+', ', ', section)

                    # Split by commas
                    names = section.split(',')

                    for name in names:
                        clean_name = name.strip()
                        clean_name = ' '.join(clean_name.split())

                        if clean_name and len(clean_name) > 2:
                            # Filter out narrative text
                            skip_patterns = [
                                'written by', 'music by', 'lyrics by', 'book by',
                                'original music', 'originally produced', 'originally commissioned',
                                'directed', 'choreograph', 'design', 'manager',
                                'credits', 'cast', 'orchestra', 'staff',
                                'opening night', 'closing night', 'performances', 'theatres',
                                'world premiere', 'was presented', 'received its'
                            ]

                            if not any(skip in clean_name.lower() for skip in skip_patterns):
                                all_producers.add(clean_name)
                                self.logger.info(f"  → Producer {len(all_producers)}: {clean_name}")

            self.logger.info(f"\nTOTAL PRODUCERS: {len(all_producers)}")

        except Exception as e:
            self.logger.error(f"Error parsing producers: {e}")

        return {
            'num_total_producers': len(all_producers) if all_producers else None
        }

    def _is_stop_line(self, line: str) -> bool:
        """Check if a line indicates we should stop collecting producer names."""
        stop_indicators = [
            'Credits', 'Opening Night', 'Closing Night', 'Cast',
            'Theatres', 'Performances', 'Musical Numbers',
            'Directed by', 'Choreographed by', 'Choreography by',
            'Scenic Design', 'Costume Design', 'Lighting Design',
            'Sound Design', 'Music Director', 'Musical Director',
            'Conducted by', 'General Manager', 'Company Manager',
            'Stage Manager', 'Technical Supervisor',
            'world premiere', 'received its', 'was presented'
        ]

        return any(indicator in line for indicator in stop_indicators)

    def parse_producers_from_html(self, html: str, show_name: str) -> Dict:
        """
        Parse producer information from IBDB page HTML.

        Args:
            html: HTML content of IBDB page
            show_name: Name of show (for logging)

        Returns:
            Dictionary with producer count
        """
        producer_names = set()

        try:
            # Look for "Produced by" section
            produced_by_match = re.search(
                r'Produced by\s+(.+?)(?:\n\n|Credits|Cast|Orchestra|Production Staff|<)',
                html,
                re.DOTALL | re.IGNORECASE
            )

            if produced_by_match:
                producer_text = produced_by_match.group(1)

                # Clean up HTML tags
                producer_text = re.sub(r'<[^>]+>', '', producer_text)

                # Replace " and " with comma for consistent splitting
                producer_text = re.sub(r'\s+and\s+', ', ', producer_text)

                # Split by commas
                potential_producers = [p.strip() for p in producer_text.split(',')]

                for producer in potential_producers:
                    # Remove parenthetical notes (e.g., "(Artistic Director)")
                    clean_name = re.sub(r'\s*\([^)]+\)', '', producer).strip()

                    # Remove extra whitespace and newlines
                    clean_name = ' '.join(clean_name.split())

                    if clean_name and len(clean_name) > 2:
                        # Filter out common non-producer text
                        if not any(skip in clean_name.lower() for skip in [
                            'credits', 'cast', 'orchestra', 'staff', 'opening night'
                        ]):
                            producer_names.add(clean_name)

        except Exception as e:
            self.logger.error(f"Error parsing producers: {e}")

        return {
            'num_total_producers': len(producer_names) if producer_names else None
        }


def scrape_all_shows(input_csv: str, output_csv: str, browser='chrome', headless=False,
                     checkpoint_csv: Optional[str] = None):
    """
    Scrape all shows using browser automation.

    Args:
        input_csv: Path to CSV with show list
        output_csv: Path to save results
        browser: 'chrome' or 'safari'
        headless: Run in headless mode
        checkpoint_csv: Path to checkpoint file for resume capability
    """
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    # Load show list
    df_shows = pd.read_csv(input_csv)
    total_shows = len(df_shows)

    logger.info("="*70)
    logger.info("BROADWAY PRODUCER BROWSER SCRAPER")
    logger.info("="*70)
    logger.info(f"Total shows to scrape: {total_shows}")
    logger.info(f"Browser: {browser}")
    logger.info(f"Headless mode: {headless}")

    # Load checkpoint if exists
    already_scraped = set()
    results_list = []

    if checkpoint_csv:
        try:
            df_checkpoint = pd.read_csv(checkpoint_csv)
            already_scraped = set(df_checkpoint['show_name'].tolist())
            results_list = df_checkpoint.to_dict('records')
            logger.info(f"✓ Loaded checkpoint: {len(already_scraped)} shows already scraped")
        except FileNotFoundError:
            logger.info("No checkpoint found, starting fresh")

    # Initialize scraper
    scraper = BrowserIBDBScraper(browser=browser, headless=headless)

    try:
        scraper.start_browser()

        # Process each show
        for idx, row in df_shows.iterrows():
            show_name = row['show_name']

            # Skip if already scraped
            if show_name in already_scraped:
                logger.info(f"[{idx+1}/{total_shows}] Skipping (already scraped): {show_name}")
                continue

            logger.info(f"\n[{idx+1}/{total_shows}] ({(idx+1)/total_shows*100:.1f}%) Processing: {show_name}")

            # Scrape the show
            result = scraper.search_and_scrape(show_name)
            result['show_id'] = row['show_id']

            results_list.append(result)

            # Save checkpoint after each show
            if checkpoint_csv:
                df_checkpoint = pd.DataFrame(results_list)
                df_checkpoint.to_csv(checkpoint_csv, index=False)

            # Pause between shows to be polite
            time.sleep(3)

        # Save final results
        df_results = pd.DataFrame(results_list)

        # Reorder columns
        column_order = ['show_id', 'show_name', 'ibdb_url', 'num_total_producers',
                       'scrape_status', 'scrape_notes']
        df_results = df_results[column_order]

        df_results.to_csv(output_csv, index=False)

        # Print summary
        logger.info("\n" + "="*70)
        logger.info("SCRAPING COMPLETE!")
        logger.info("="*70)
        logger.info(f"Total shows: {total_shows}")
        logger.info(f"Successfully scraped: {len(df_results[df_results['scrape_status'] == 'success'])}")
        logger.info(f"Failed: {len(df_results[df_results['scrape_status'] != 'success'])}")
        logger.info(f"Results saved to: {output_csv}")

    except KeyboardInterrupt:
        logger.warning("\n⚠ Interrupted by user!")
        logger.info("Saving progress...")

        # Save what we have so far
        if results_list:
            df_results = pd.DataFrame(results_list)
            column_order = ['show_id', 'show_name', 'ibdb_url', 'num_total_producers',
                           'scrape_status', 'scrape_notes']
            df_results = df_results[column_order]
            df_results.to_csv(checkpoint_csv or output_csv, index=False)
            logger.info(f"✓ Progress saved to: {checkpoint_csv or output_csv}")

    finally:
        scraper.close_browser()


if __name__ == '__main__':
    scrape_all_shows(
        input_csv='raw/all_broadway_shows_2010_2025.csv',
        output_csv='data/show_producer_counts_ibdb.csv',
        browser='chrome',  # Change to 'safari' if you don't have Chrome
        headless=False,    # Set to True to hide the browser window
        checkpoint_csv='data/checkpoint_browser_scrape.csv'
    )
