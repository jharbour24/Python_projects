#!/usr/bin/env python3
"""
Comprehensive Broadway show scraper with IBDB integration.
Includes Google-based IBDB search and producer data extraction.
"""

import re
import time
from typing import Optional, Dict, List, Tuple
from urllib.parse import quote_plus, urljoin
import requests
from bs4 import BeautifulSoup

from utils import setup_logger, get_robust_session, RateLimiter, safe_get


class ComprehensiveBroadwayScraper:
    """Scraper for Broadway show data from IBDB with Google search fallback."""

    def __init__(self, rate_limit_delay: float = 2.5):
        """
        Initialize the scraper.

        Args:
            rate_limit_delay: Minimum delay between requests in seconds
        """
        self.logger = setup_logger(__name__, log_file='logs/broadway_scraper.log')
        self.session = get_robust_session()
        self.rate_limiter = RateLimiter(min_delay=rate_limit_delay, max_delay=6.0)

        # Base URLs
        self.ibdb_base = "https://www.ibdb.com"
        self.google_search_base = "https://www.google.com/search"

        self.logger.info("ComprehensiveBroadwayScraper initialized")

    def test_cloudflare_bypass(self) -> bool:
        """
        Test if we can access IBDB (check for Cloudflare blocking).

        Returns:
            True if successful, False if blocked
        """
        self.logger.info("Testing Cloudflare bypass / IBDB access...")

        try:
            response = self.session.get(self.ibdb_base, timeout=30)
            response.raise_for_status()

            # Check if we got an actual page or Cloudflare challenge
            if 'cloudflare' in response.text.lower() and 'checking' in response.text.lower():
                self.logger.error("Cloudflare challenge detected - may be blocked")
                return False

            self.logger.info("✓ IBDB access successful")
            return True

        except Exception as e:
            self.logger.error(f"Failed to access IBDB: {e}")
            return False

    def search_ibdb(self, show_title: str) -> Optional[str]:
        """
        Search for a Broadway show on IBDB using Google.

        Args:
            show_title: Title of the show to search for

        Returns:
            IBDB production URL if found, None otherwise
        """
        self.logger.info(f"Searching IBDB for: {show_title}")

        # Build Google search query
        # Use site:ibdb.com to limit to IBDB, add "production" to get show pages
        search_query = f'site:ibdb.com/broadway-production "{show_title}"'
        encoded_query = quote_plus(search_query)

        search_url = f"{self.google_search_base}?q={encoded_query}"

        self.rate_limiter.wait()

        try:
            response = safe_get(search_url, self.session, self.logger)
            if not response:
                self.logger.warning(f"Failed to get Google search results for: {show_title}")
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Parse Google search results to find IBDB links
            # Google uses different HTML structures, we look for links in result divs
            for link in soup.find_all('a', href=True):
                href = link['href']

                # Google wraps URLs in /url?q= parameters
                if '/url?q=' in href:
                    # Extract the actual URL
                    match = re.search(r'/url\?q=(https?://[^&]+)', href)
                    if match:
                        actual_url = match.group(1)

                        # Check if it's an IBDB production page
                        if 'ibdb.com' in actual_url and '/broadway-production/' in actual_url:
                            self.logger.info(f"✓ Found IBDB URL: {actual_url}")
                            return actual_url

            self.logger.warning(f"No IBDB URL found for: {show_title}")
            return None

        except Exception as e:
            self.logger.error(f"Error searching for {show_title}: {e}")
            return None

    def parse_producers_from_ibdb(self, html: str, show_title: str) -> Dict:
        """
        Parse producer information from an IBDB production page.

        Args:
            html: HTML content of IBDB production page
            show_title: Title of the show (for logging)

        Returns:
            Dictionary with producer counts and details
        """
        self.logger.info(f"Parsing producers for: {show_title}")

        result = {
            'lead_producers': [],
            'co_producers': [],
            'associate_producers': [],
            'all_producers': [],
            'num_lead_producers': 0,
            'num_co_producers': 0,
            'num_total_producers': 0,
            'parse_status': 'unknown',
            'parse_notes': ''
        }

        try:
            soup = BeautifulSoup(html, 'html.parser')

            # IBDB structure: Look for sections with producer credits
            # Typical structure has divs or sections with headers like "Produced by", "Associate Producer", etc.

            # Find all text nodes that might indicate producer sections
            # Look for common patterns in IBDB's HTML

            # Strategy 1: Look for "Produced by" or "Producer" headers
            producer_headers = soup.find_all(['h4', 'h3', 'h2', 'div', 'span'],
                                            string=re.compile(r'Produc(ed by|er)', re.IGNORECASE))

            if not producer_headers:
                # Strategy 2: Look for staff section with producer roles
                # IBDB often has a "Staff" or "Credits" section
                staff_section = soup.find(['div', 'section'], class_=re.compile(r'staff|credit', re.IGNORECASE))
                if staff_section:
                    producer_headers = staff_section.find_all(string=re.compile(r'Produc', re.IGNORECASE))

            all_producer_names = set()
            lead_producer_names = set()
            co_producer_names = set()
            associate_producer_names = set()

            # Extract producer names from the sections we found
            for header in producer_headers:
                # Find the parent element and look for names nearby
                parent = header.find_parent(['div', 'section', 'li', 'tr'])
                if not parent:
                    parent = header

                # Get text around the header
                header_text = header.get_text() if hasattr(header, 'get_text') else str(header)

                # Determine producer type from header
                is_co_producer = bool(re.search(r'co-?produc', header_text, re.IGNORECASE))
                is_associate = bool(re.search(r'associate produc', header_text, re.IGNORECASE))
                is_lead = bool(re.search(r'^produc(ed by|er)$', header_text.strip(), re.IGNORECASE))

                # Look for names in the vicinity
                # Names are typically in <a> tags or plain text after the header
                next_sibling = parent.find_next_sibling()
                search_area = next_sibling if next_sibling else parent

                # Find all links (IBDB typically links person names)
                name_links = search_area.find_all('a', href=re.compile(r'/person/'))

                if name_links:
                    for link in name_links:
                        name = link.get_text().strip()
                        if name and len(name) > 1:
                            all_producer_names.add(name)

                            if is_co_producer:
                                co_producer_names.add(name)
                            elif is_associate:
                                associate_producer_names.add(name)
                            elif is_lead:
                                lead_producer_names.add(name)
                else:
                    # Try to extract names from plain text
                    text_content = search_area.get_text()
                    # Simple heuristic: names are typically capitalized words
                    potential_names = re.findall(r'\b([A-Z][a-z]+ (?:[A-Z][a-z]+\.? ?)+)', text_content)
                    for name in potential_names:
                        name = name.strip()
                        if len(name) > 3:  # Avoid false positives
                            all_producer_names.add(name)

            # Alternative strategy: Look for structured data in tables
            if not all_producer_names:
                # Some IBDB pages have production credits in tables
                tables = soup.find_all('table')
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 2:
                            role = cells[0].get_text().strip()
                            if 'produc' in role.lower():
                                name = cells[1].get_text().strip()
                                if name:
                                    all_producer_names.add(name)
                                    if 'co-produc' in role.lower():
                                        co_producer_names.add(name)
                                    elif 'associate' in role.lower():
                                        associate_producer_names.add(name)

            # Update result
            result['all_producers'] = sorted(list(all_producer_names))
            result['lead_producers'] = sorted(list(lead_producer_names))
            result['co_producers'] = sorted(list(co_producer_names))
            result['associate_producers'] = sorted(list(associate_producer_names))

            result['num_total_producers'] = len(all_producer_names)
            result['num_lead_producers'] = len(lead_producer_names)
            result['num_co_producers'] = len(co_producer_names)

            if result['num_total_producers'] > 0:
                result['parse_status'] = 'ok'
                result['parse_notes'] = f'Found {result["num_total_producers"]} producers'
                self.logger.info(f"✓ Parsed {result['num_total_producers']} producers for {show_title}")
            else:
                result['parse_status'] = 'no_producers_found'
                result['parse_notes'] = 'No producer information found on page'
                self.logger.warning(f"No producers found for {show_title}")

        except Exception as e:
            result['parse_status'] = 'parse_error'
            result['parse_notes'] = f'Error parsing: {str(e)}'
            self.logger.error(f"Error parsing producers for {show_title}: {e}")

        return result

    def get_producer_counts_for_show(self, show_title: str) -> Dict:
        """
        Get producer counts for a single show (main entry point).

        Args:
            show_title: Title of the Broadway show

        Returns:
            Dictionary with all producer data and metadata
        """
        self.logger.info(f"Getting producer counts for: {show_title}")

        result = {
            'show_name': show_title,
            'ibdb_url': None,
            'num_lead_producers': None,
            'num_co_producers': None,
            'num_total_producers': None,
            'scrape_status': 'pending',
            'scrape_notes': ''
        }

        try:
            # Step 1: Search for IBDB URL
            ibdb_url = self.search_ibdb(show_title)

            if not ibdb_url:
                result['scrape_status'] = 'not_found'
                result['scrape_notes'] = 'Could not find IBDB page via Google search'
                self.logger.warning(f"Could not find IBDB URL for: {show_title}")
                return result

            result['ibdb_url'] = ibdb_url

            # Step 2: Fetch the IBDB page
            self.rate_limiter.wait()
            response = safe_get(ibdb_url, self.session, self.logger)

            if not response:
                result['scrape_status'] = 'fetch_failed'
                result['scrape_notes'] = 'Could not fetch IBDB page'
                self.logger.error(f"Failed to fetch IBDB page for: {show_title}")
                return result

            # Step 3: Parse producer information
            producer_data = self.parse_producers_from_ibdb(response.text, show_title)

            # Merge producer data into result
            result['num_lead_producers'] = producer_data['num_lead_producers'] or None
            result['num_co_producers'] = producer_data['num_co_producers'] or None
            result['num_total_producers'] = producer_data['num_total_producers'] or None
            result['scrape_status'] = producer_data['parse_status']
            result['scrape_notes'] = producer_data['parse_notes']

            # Store detailed producer lists for potential debugging
            result['_debug_producers'] = producer_data

        except Exception as e:
            result['scrape_status'] = 'error'
            result['scrape_notes'] = f'Unexpected error: {str(e)}'
            self.logger.error(f"Error processing {show_title}: {e}", exc_info=True)

        return result


# Convenience function for testing
def test_single_show(show_title: str):
    """Test scraping a single show."""
    scraper = ComprehensiveBroadwayScraper()
    result = scraper.get_producer_counts_for_show(show_title)
    print(f"\nResults for '{show_title}':")
    for key, value in result.items():
        if not key.startswith('_'):  # Skip debug fields
            print(f"  {key}: {value}")
    return result


if __name__ == '__main__':
    # Quick test
    test_shows = ["Hamilton", "Hadestown", "The Book of Mormon"]
    for show in test_shows:
        test_single_show(show)
        time.sleep(3)
