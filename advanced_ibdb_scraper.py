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

    def search_google_for_ibdb(self, show_name: str) -> Optional[str]:
        """
        Search Google for IBDB page of a show.

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

        Args:
            html: HTML content of IBDB page
            show_name: Name of show (for logging)

        Returns:
            Dictionary with producer counts and details
        """
        self.logger.info(f"Parsing producers for: {show_name}")

        result = {
            'producer_names': [],
            'num_total_producers': 0,
            'num_lead_producers': 0,
            'num_co_producers': 0,
            'parse_status': 'unknown',
            'parse_notes': ''
        }

        try:
            soup = BeautifulSoup(html, 'html.parser')

            # IBDB structure: Look for producer credits
            # Common patterns:
            # - "Produced by" or "Producer" labels
            # - Credits section with role labels
            # - Person links (href="/person/...")

            producer_names = set()
            lead_producer_names = set()
            co_producer_names = set()

            # Strategy 1: Find all person links and check nearby text for producer roles
            person_links = soup.find_all('a', href=re.compile(r'/person/'))

            for link in person_links:
                # Get surrounding context
                parent = link.find_parent(['div', 'p', 'li', 'td', 'tr'])
                if not parent:
                    continue

                context_text = parent.get_text().lower()

                # Check if this person is listed as a producer
                if 'produc' in context_text:
                    person_name = link.get_text().strip()

                    if person_name and len(person_name) > 1:
                        producer_names.add(person_name)

                        # Determine producer type from context
                        if 'co-produc' in context_text or 'coproducer' in context_text:
                            co_producer_names.add(person_name)
                        elif 'associate produc' in context_text:
                            co_producer_names.add(person_name)
                        elif 'executive produc' in context_text:
                            # Could be either lead or co-, conservatively count as co-
                            co_producer_names.add(person_name)
                        elif 'produced by' in context_text or re.search(r'\bproducer\b', context_text):
                            lead_producer_names.add(person_name)

            # Strategy 2: Look for structured producer sections
            # Find headers that mention "Producer"
            headers = soup.find_all(['h3', 'h4', 'h5', 'strong', 'b'])

            for header in headers:
                header_text = header.get_text().strip().lower()

                if 'produc' in header_text:
                    # Find next siblings or parent's siblings to get producer names
                    container = header.find_parent(['div', 'section'])
                    if container:
                        names_in_section = container.find_all('a', href=re.compile(r'/person/'))

                        for name_link in names_in_section:
                            name = name_link.get_text().strip()
                            if name and len(name) > 1:
                                producer_names.add(name)

                                # Check role type from header
                                if 'co-produc' in header_text:
                                    co_producer_names.add(name)
                                elif 'associate' in header_text:
                                    co_producer_names.add(name)
                                else:
                                    lead_producer_names.add(name)

            # Strategy 3: Look for tables with production credits
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')

                for row in rows:
                    cells = row.find_all(['td', 'th'])

                    if len(cells) >= 2:
                        role_cell = cells[0].get_text().strip().lower()

                        if 'produc' in role_cell:
                            # Extract names from second cell
                            name_links = cells[1].find_all('a', href=re.compile(r'/person/'))

                            for name_link in name_links:
                                name = name_link.get_text().strip()
                                if name:
                                    producer_names.add(name)

                                    if 'co-produc' in role_cell or 'associate' in role_cell:
                                        co_producer_names.add(name)
                                    else:
                                        lead_producer_names.add(name)

            # Update result
            result['producer_names'] = sorted(list(producer_names))
            result['num_total_producers'] = len(producer_names)
            result['num_lead_producers'] = len(lead_producer_names)
            result['num_co_producers'] = len(co_producer_names)

            if result['num_total_producers'] > 0:
                result['parse_status'] = 'ok'
                result['parse_notes'] = f'Found {result["num_total_producers"]} total producers'
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
            'num_lead_producers': None,
            'num_co_producers': None,
            'scrape_status': 'pending',
            'scrape_notes': ''
        }

        try:
            # Step 1: Search Google for IBDB URL
            ibdb_url = self.search_google_for_ibdb(show_name)

            if not ibdb_url:
                result['scrape_status'] = 'not_found'
                result['scrape_notes'] = 'IBDB URL not found via Google search'
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
            result['num_lead_producers'] = producer_data['num_lead_producers']
            result['num_co_producers'] = producer_data['num_co_producers']
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
        logger.info(f"  Lead producers: {result['num_lead_producers']}")
        logger.info(f"  Co-producers: {result['num_co_producers']}")
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
