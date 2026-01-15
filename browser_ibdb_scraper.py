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
import random
import re
import time
from typing import Dict, Optional
from urllib.parse import quote_plus

import pandas as pd
from selenium import webdriver
from REVIVALS_DICTIONARY import BROADWAY_REVIVALS
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
            'producer_names': None,
            'production_year': None,
            'num_performances': None,
            'scrape_status': 'pending',
            'scrape_notes': ''
        }

        try:
            self.logger.info(f"\n{'='*70}")
            self.logger.info(f"Processing: {show_name}")
            self.logger.info(f"{'='*70}")

            # Step 1: Search Google
            # Check if show is a revival and include revival year in search
            show_name_upper = show_name.upper()
            if show_name_upper in BROADWAY_REVIVALS:
                revival_year = BROADWAY_REVIVALS[show_name_upper]
                search_query = f"{show_name} IBDB Broadway revival {revival_year} 2010..2025"
                self.logger.info(f"✓ Detected revival from {revival_year}")
            else:
                search_query = f"{show_name} IBDB Broadway 2010..2025"

            google_url = f"https://www.google.com/search?q={quote_plus(search_query)}"

            self.logger.info(f"Searching Google: {search_query}")
            self.driver.get(google_url)

            # Wait for page to load
            time.sleep(3)

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

            # Wait for page to load (longer to appear more human-like)
            time.sleep(5)

            # Step 4: Extract producer information using Selenium element finding
            producer_data = self.parse_producers_from_page(show_name)

            # Update result with all extracted data
            result['num_total_producers'] = producer_data.get('num_total_producers')
            result['producer_names'] = producer_data.get('producer_names')
            result['production_year'] = producer_data.get('production_year')
            result['num_performances'] = producer_data.get('num_performances')

            if producer_data['num_total_producers'] is not None and producer_data['num_total_producers'] > 0:
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

            # Debug: Check if "Produced by" exists on page
            if 'Produced by' in page_text or 'produced by' in page_text.lower():
                # Find the location and show context
                idx = page_text.lower().find('produced by')
                if idx > 0:
                    context = page_text[max(0, idx-50):min(len(page_text), idx+200)]
                    self.logger.info(f"Found 'Produced by' at position {idx}. Context: {context[:150]}...")
            else:
                self.logger.warning("'Produced by' not found on page!")

            # Find ALL producer-related text using a broad regex
            # This captures: Lead Producer, Produced by, Co-Produced by, Associate Producer, in association with
            # Stop at the FIRST newline (not double newline) or stop words
            # Use non-greedy match and stop at newline to avoid capturing narrative text
            producer_pattern = r'(?:Lead Producer[s]?:|Produced by|Co-Produced by|Associate Producer[s]?:|in association with)\s+([^\n]+?)(?:\n|Credits|Directed by|Written by|Choreograph|Scenic Design|Costume Design|Lighting Design|Sound Design|Music Director|Musical Director|General Management|Company Management|Opening Night|Closing Night|$)'

            matches = list(re.finditer(producer_pattern, page_text, re.IGNORECASE))

            self.logger.info(f"Found {len(matches)} producer sections on page")

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
                    # Remove any leading producer category labels from the section
                    # (e.g., "Co-Producer: John Smith" becomes "John Smith")
                    section = re.sub(r'^\s*(?:Lead Producer[s]?:|Co-Produced by|Co-Producer[s]?:|Associate Producer[s]?:|in association with)\s*', '', section, flags=re.IGNORECASE)

                    # Replace " and " with comma
                    section = re.sub(r'\s+and\s+', ', ', section)

                    # Split by commas
                    names = section.split(',')

                    for name in names:
                        clean_name = name.strip()
                        clean_name = ' '.join(clean_name.split())

                        if clean_name and len(clean_name) > 2:
                            # Filter out narrative text and credits
                            skip_patterns = [
                                'written by', 'music by', 'lyrics by', 'book by',
                                'inspired by', 'based on', 'arrangements by', 'orchestrations by',
                                'music direction by', 'vocal arrangements', 'dance arrangements',
                                'original music', 'originally produced', 'originally commissioned',
                                'directed', 'choreograph', 'design', 'manager', 'direction',
                                'credits', 'cast', 'orchestra', 'staff', 'associate',
                                'opening night', 'closing night', 'performances', 'theatres',
                                'world premiere', 'was presented', 'received its'
                            ]

                            if not any(skip in clean_name.lower() for skip in skip_patterns):
                                all_producers.add(clean_name)
                                self.logger.info(f"  → Producer {len(all_producers)}: {clean_name}")

            self.logger.info(f"\nTOTAL PRODUCERS: {len(all_producers)}")

            # Extract production year from page
            production_year = None
            year_match = re.search(r'Opening Night:\s*\w+\s+\d+,\s+(\d{4})', page_text)
            if year_match:
                production_year = int(year_match.group(1))
                self.logger.info(f"Production Year: {production_year}")

            # Extract number of performances
            num_performances = None
            perf_match = re.search(r'Performances:\s*(\d+)', page_text, re.IGNORECASE)
            if perf_match:
                num_performances = int(perf_match.group(1))
                self.logger.info(f"Number of Performances: {num_performances}")

        except Exception as e:
            self.logger.error(f"Error parsing producers: {e}")

        return {
            'num_total_producers': len(all_producers) if all_producers else None,
            'producer_names': '; '.join(sorted(all_producers)) if all_producers else None,
            'production_year': production_year,
            'num_performances': num_performances
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
            df_checkpoint = pd.read_csv(checkpoint_csv, encoding='utf-8', errors='ignore')
            already_scraped = set(df_checkpoint['show_name'].tolist())
            results_list = df_checkpoint.to_dict('records')
            logger.info(f"✓ Loaded checkpoint: {len(already_scraped)} shows already scraped")
        except FileNotFoundError:
            logger.info("No checkpoint found, starting fresh")
        except UnicodeDecodeError:
            logger.warning("Checkpoint has encoding issues, trying with latin-1 encoding")
            try:
                df_checkpoint = pd.read_csv(checkpoint_csv, encoding='latin-1')
                already_scraped = set(df_checkpoint['show_name'].tolist())
                results_list = df_checkpoint.to_dict('records')
                logger.info(f"✓ Loaded checkpoint: {len(already_scraped)} shows already scraped")
            except Exception as e:
                logger.error(f"Could not load checkpoint: {e}")
                logger.info("Starting fresh instead")

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

            # Pause between shows (4 seconds - user will handle CAPTCHAs manually)
            logger.info(f"⏸  Waiting 4 seconds before next show...")
            time.sleep(4)

        # RETRY LOGIC: Keep retrying failed shows until all are successful
        retry_num = 0
        while True:
            # Find shows that failed
            df_current = pd.DataFrame(results_list)
            failed_shows = df_current[df_current['scrape_status'] != 'success']

            if len(failed_shows) == 0:
                logger.info("\n" + "="*70)
                logger.info("✓✓✓ ALL SHOWS SCRAPED SUCCESSFULLY! ✓✓✓")
                logger.info("="*70)
                break

            retry_num += 1
            logger.info("\n" + "="*70)
            logger.info(f"RETRY ROUND {retry_num}")
            logger.info("="*70)
            logger.info(f"Retrying {len(failed_shows)} failed shows...")
            logger.info(f"Success rate: {len(df_current[df_current['scrape_status'] == 'success'])}/{len(df_current)} ({len(df_current[df_current['scrape_status'] == 'success'])/len(df_current)*100:.1f}%)")

            # Retry each failed show
            for idx, failed_row in failed_shows.iterrows():
                show_name = failed_row['show_name']
                show_id = failed_row['show_id']

                logger.info(f"\n[RETRY {retry_num}] Retrying: {show_name}")
                logger.info(f"  Previous status: {failed_row['scrape_status']}")
                logger.info(f"  Previous note: {failed_row['scrape_notes']}")

                # Scrape the show again
                result = scraper.search_and_scrape(show_name)
                result['show_id'] = show_id

                # Update the result in results_list
                for i, r in enumerate(results_list):
                    if r['show_name'] == show_name:
                        results_list[i] = result
                        break

                # Save checkpoint after each retry
                if checkpoint_csv:
                    df_checkpoint = pd.DataFrame(results_list)
                    df_checkpoint.to_csv(checkpoint_csv, index=False)

                # Pause between retries
                logger.info(f"⏸  Waiting 4 seconds before next retry...")
                time.sleep(4)

            # After this retry round, show progress
            df_current = pd.DataFrame(results_list)
            remaining_failed = len(df_current[df_current['scrape_status'] != 'success'])
            success_count = len(df_current[df_current['scrape_status'] == 'success'])
            logger.info(f"\n✓ Retry round {retry_num} complete.")
            logger.info(f"  Status: {success_count}/{len(df_current)} successful ({success_count/len(df_current)*100:.1f}%)")
            logger.info(f"  Remaining failures: {remaining_failed}")

            if remaining_failed > 0:
                logger.info(f"\n→ Continuing to next retry round...")
            else:
                logger.info(f"\n✓ All shows scraped successfully!")

        # Save final results
        df_results = pd.DataFrame(results_list)

        # Reorder columns
        column_order = ['show_id', 'show_name', 'ibdb_url', 'production_year',
                       'num_total_producers', 'producer_names', 'num_performances',
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
            column_order = ['show_id', 'show_name', 'ibdb_url', 'production_year',
                           'num_total_producers', 'producer_names', 'num_performances',
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
