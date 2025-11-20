#!/usr/bin/env python3
"""
Advanced IBDB scraper using cloudscraper with Google search approach.
Bypasses Cloudflare protection to scrape producer data.
"""

import re
import time
from typing import Optional, Dict, List
from urllib.parse import quote_plus, unquote
import cloudscraper
from bs4 import BeautifulSoup

from utils import setup_logger, RateLimiter

logger = setup_logger(__name__, log_file='logs/advanced_scraper.log')


class AdvancedIBDBScraper:
    """Advanced scraper using cloudscraper to bypass Cloudflare."""

    def __init__(self, rate_limit_delay: float = 3.0):
        """Initialize scraper with cloudscraper session."""
        self.logger = logger
        self.rate_limiter = RateLimiter(min_delay=rate_limit_delay, max_delay=8.0)

        # Create cloudscraper session (bypasses Cloudflare)
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            },
            delay=10  # Initial delay for Cloudflare challenge
        )

        self.ibdb_base = "https://www.ibdb.com"
        self.logger.info("AdvancedIBDBScraper initialized with Cloudflare bypass")

    def search_ibdb_directly(self, show_name: str) -> Optional[str]:
        """
        Search IBDB directly for a show's production page (bypasses Google).

        Args:
            show_name: Name of the Broadway show

        Returns:
            IBDB URL if found, None otherwise
        """
        self.logger.info(f"Searching IBDB directly for: {show_name}")

        # Try direct URL construction first (many shows work with this pattern)
        show_slug = show_name.lower().replace(' ', '-').replace("'", "").replace(":", "").replace("!", "")
        direct_url = f"https://www.ibdb.com/broadway-production/{show_slug}"

        self.rate_limiter.wait()

        try:
            response = self.scraper.get(direct_url, timeout=30)
            if response.status_code == 200:
                # Verify it's a real production page
                if 'Produced by' in response.text or 'Production Staff' in response.text:
                    self.logger.info(f"✓ Found IBDB URL (direct): {direct_url}")
                    return direct_url
        except Exception as e:
            self.logger.debug(f"Direct URL attempt failed: {e}")

        # If direct URL didn't work, try IBDB search
        try:
            search_url = f"https://www.ibdb.com/broadway-search?stext={quote_plus(show_name)}"

            self.rate_limiter.wait()
            response = self.scraper.get(search_url, timeout=30)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Look for production links
                for link in soup.find_all('a', href=True):
                    href = link['href']

                    if '/broadway-production/' in href:
                        full_url = href if href.startswith('http') else f"https://www.ibdb.com{href}"
                        self.logger.info(f"✓ Found IBDB URL (search): {full_url}")
                        return full_url

        except Exception as e:
            self.logger.warning(f"IBDB search failed: {e}")

        self.logger.warning(f"No IBDB URL found for: {show_name}")
        return None

    def search_google_for_ibdb(self, show_name: str) -> Optional[str]:
        """
        Search Google for IBDB page of a show (fallback method).

        Args:
            show_name: Name of the Broadway show

        Returns:
            IBDB URL if found, None otherwise
        """
        self.logger.info(f"Searching Google for: {show_name}")

        # Build search query
        search_query = f"{show_name} IBDB Broadway"
        encoded_query = quote_plus(search_query)
        search_url = f"https://www.google.com/search?q={encoded_query}"

        self.rate_limiter.wait()

        try:
            response = self.scraper.get(search_url, timeout=30)

            if response.status_code != 200:
                self.logger.warning(f"Google search failed with status {response.status_code}")
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find all links in search results
            for link in soup.find_all('a', href=True):
                href = link['href']

                # Google wraps actual URLs
                if '/url?q=' in href:
                    # Extract actual URL
                    match = re.search(r'/url\?q=(https?://[^&]+)', href)
                    if match:
                        actual_url = unquote(match.group(1))

                        # Check if it's an IBDB production page
                        if 'ibdb.com' in actual_url and 'broadway-production' in actual_url:
                            self.logger.info(f"✓ Found IBDB URL: {actual_url}")
                            return actual_url

                # Sometimes Google provides direct links
                elif 'ibdb.com' in href and 'broadway-production' in href:
                    if href.startswith('http'):
                        self.logger.info(f"✓ Found direct IBDB URL: {href}")
                        return href

            self.logger.warning(f"No IBDB URL found in Google results for: {show_name}")
            return None

        except Exception as e:
            self.logger.error(f"Error searching Google for {show_name}: {e}")
            return None

    def parse_producers_from_ibdb_page(self, html: str, show_name: str) -> Dict:
        """
        Parse producer information from IBDB production page HTML.

        IBDB lists all producers together under "Produced by" without distinguishing
        types (e.g., "Produced by Jeffrey Seller, Sander Jacobs, Jill Furman and
        The Public Theater..."). We simply count all entities listed.

        Args:
            html: HTML content of IBDB page
            show_name: Name of show (for logging)

        Returns:
            Dictionary with producer count and details
        """
        self.logger.info(f"Parsing producers for: {show_name}")

        result = {
            'producer_names': [],
            'num_total_producers': 0,
            'parse_status': 'unknown',
            'parse_notes': ''
        }

        try:
            soup = BeautifulSoup(html, 'html.parser')

            producer_names = set()

            # Strategy 1: Find "Produced by" text and extract the producer list
            # Look for text containing "Produced by" followed by names
            page_text = soup.get_text()

            # Find the "Produced by" section
            produced_by_match = re.search(r'Produced by\s+(.+?)(?:\n\n|Credits|Cast|Orchestra|Production Staff|$)',
                                         page_text, re.DOTALL | re.IGNORECASE)

            if produced_by_match:
                producer_text = produced_by_match.group(1)

                # Split by commas and "and" - these separate individual producers
                # First replace " and " with comma for consistent splitting
                producer_text = re.sub(r'\s+and\s+', ', ', producer_text)

                # Split by comma
                potential_producers = [p.strip() for p in producer_text.split(',')]

                for producer in potential_producers:
                    # Clean up: remove parenthetical notes (like role descriptions)
                    # Example: "The Public Theater (Oskar Eustis, Artistic Director...)"
                    # becomes "The Public Theater"
                    clean_name = re.sub(r'\s*\([^)]+\)', '', producer).strip()

                    # Skip if empty or too short
                    if clean_name and len(clean_name) > 2:
                        # Skip common non-producer text
                        skip_terms = ['artistic director', 'executive director', 'managing director',
                                    'general manager', 'producer', 'production']

                        if not any(term in clean_name.lower() for term in skip_terms if term == clean_name.lower()):
                            producer_names.add(clean_name)

            # Strategy 2: Look for person/company links in producer context
            # This catches cases where parsing from text might miss formatting
            person_links = soup.find_all('a', href=re.compile(r'/person/|/organization/'))

            for link in person_links:
                parent = link.find_parent(['div', 'p', 'li', 'td', 'tr'])
                if parent:
                    context_text = parent.get_text().lower()

                    # Only include if in "produced by" context
                    if 'produced by' in context_text or 'producer' in context_text:
                        name = link.get_text().strip()
                        if name and len(name) > 2:
                            producer_names.add(name)

            # Strategy 3: Look for tables with production credits
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')

                for row in rows:
                    cells = row.find_all(['td', 'th'])

                    if len(cells) >= 2:
                        role_cell = cells[0].get_text().strip().lower()

                        # Look for "produced by" or "producer" role
                        if 'produced by' in role_cell or role_cell == 'producer':
                            # Extract all names from the second cell
                            names_text = cells[1].get_text()

                            # Split by commas and "and"
                            names_text = re.sub(r'\s+and\s+', ', ', names_text)
                            names = [n.strip() for n in names_text.split(',')]

                            for name in names:
                                # Clean parentheticals
                                clean_name = re.sub(r'\s*\([^)]+\)', '', name).strip()
                                if clean_name and len(clean_name) > 2:
                                    producer_names.add(clean_name)

            # Update result
            result['producer_names'] = sorted(list(producer_names))
            result['num_total_producers'] = len(producer_names)

            if result['num_total_producers'] > 0:
                result['parse_status'] = 'ok'
                result['parse_notes'] = f'Found {result["num_total_producers"]} producers'
                self.logger.info(f"✓ Parsed {result['num_total_producers']} producers for {show_name}")
            else:
                result['parse_status'] = 'no_producers_found'
                result['parse_notes'] = 'No producer information found'
                self.logger.warning(f"⚠ No producers found for {show_name}")

        except Exception as e:
            result['parse_status'] = 'parse_error'
            result['parse_notes'] = f'Error: {str(e)}'
            self.logger.error(f"Error parsing producers for {show_name}: {e}")

        return result

    def get_producers_for_show(self, show_name: str) -> Dict:
        """
        Complete workflow: search Google -> fetch IBDB page -> parse producers.

        Args:
            show_name: Name of Broadway show

        Returns:
            Dictionary with all producer data
        """
        self.logger.info(f"\n{'='*70}")
        self.logger.info(f"Processing: {show_name}")
        self.logger.info(f"{'='*70}")

        result = {
            'show_name': show_name,
            'ibdb_url': None,
            'num_total_producers': None,
            'scrape_status': 'pending',
            'scrape_notes': ''
        }

        try:
            # Step 1: Search for IBDB URL (try direct search first, then Google as fallback)
            ibdb_url = self.search_ibdb_directly(show_name)

            # Fallback to Google if direct search failed
            if not ibdb_url:
                self.logger.info("Direct IBDB search failed, trying Google...")
                ibdb_url = self.search_google_for_ibdb(show_name)

            if not ibdb_url:
                result['scrape_status'] = 'not_found'
                result['scrape_notes'] = 'IBDB URL not found via direct search or Google'
                return result

            result['ibdb_url'] = ibdb_url

            # Step 2: Fetch IBDB page with cloudscraper
            self.rate_limiter.wait()
            self.logger.info(f"Fetching IBDB page: {ibdb_url}")

            response = self.scraper.get(ibdb_url, timeout=30)

            if response.status_code != 200:
                result['scrape_status'] = 'fetch_failed'
                result['scrape_notes'] = f'HTTP {response.status_code}'
                self.logger.error(f"Failed to fetch page: HTTP {response.status_code}")
                return result

            self.logger.info(f"✓ Successfully fetched IBDB page")

            # Step 3: Parse producers
            producer_data = self.parse_producers_from_ibdb_page(response.text, show_name)

            # Merge results
            result['num_total_producers'] = producer_data['num_total_producers']
            result['scrape_status'] = producer_data['parse_status']
            result['scrape_notes'] = producer_data['parse_notes']

            # Store producer names for debugging
            result['_producer_names'] = producer_data['producer_names']

        except Exception as e:
            result['scrape_status'] = 'error'
            result['scrape_notes'] = f'Error: {str(e)}'
            self.logger.error(f"Error processing {show_name}: {e}", exc_info=True)

        return result


def test_specific_shows():
    """Test scraper with specific shows mentioned by user."""
    logger.info("="*70)
    logger.info("TESTING ADVANCED SCRAPER WITH SPECIFIC SHOWS")
    logger.info("="*70)

    scraper = AdvancedIBDBScraper(rate_limit_delay=4.0)

    test_shows = [
        ("Hamilton", 4),  # Expected: 4 producers
        ("Hadestown", 45),  # Expected: 45 producers
    ]

    results = []

    for show_name, expected_count in test_shows:
        logger.info(f"\n{'='*70}")
        logger.info(f"TEST: {show_name} (expecting ~{expected_count} producers)")
        logger.info(f"{'='*70}")

        result = scraper.get_producers_for_show(show_name)
        results.append(result)

        # Display result
        logger.info(f"\nResults for {show_name}:")
        logger.info(f"  IBDB URL: {result['ibdb_url']}")
        logger.info(f"  Total producers: {result['num_total_producers']}")
        logger.info(f"  Status: {result['scrape_status']}")

        if result['num_total_producers']:
            diff = abs(result['num_total_producers'] - expected_count)
            if diff <= 2:
                logger.info(f"  ✓ MATCH (within ±2 of expected {expected_count})")
            else:
                logger.warning(f"  ⚠ OFF BY {diff} (expected {expected_count})")

        # Show first few producer names
        if '_producer_names' in result and result['_producer_names']:
            logger.info(f"  First 5 producers: {result['_producer_names'][:5]}")

        time.sleep(5)  # Be polite between requests

    # Summary
    logger.info(f"\n{'='*70}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*70}")

    for idx, (show_name, expected) in enumerate(test_shows):
        result = results[idx]
        found = result['num_total_producers'] or 0
        logger.info(f"{show_name}: Found {found}, Expected ~{expected}, Status: {result['scrape_status']}")

    return results


if __name__ == '__main__':
    test_specific_shows()
