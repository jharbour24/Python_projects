"""
Producer count scraper from IBDB and Playbill Vault.

For each show, extracts:
- List of producers (lead producers and co-producers)
- Counts: total, lead, co-producer

Sources:
- IBDB (Internet Broadway Database): https://www.ibdb.com/
- Playbill Vault: https://www.playbillvault.com/

Author: Broadway Analysis Pipeline
"""

import re
import time
from typing import Dict, List, Optional, Tuple
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import config
from utils import normalize_title, create_show_id, parse_producer_list, setup_logger

logger = setup_logger(__name__)


class ProducerScraper:
    """Scraper for Broadway producer information from IBDB and Playbill."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': config.USER_AGENT})

    def _get_page(self, url: str) -> Optional[BeautifulSoup]:
        """
        Fetch a web page and return BeautifulSoup object.

        Parameters
        ----------
        url : str
            URL to fetch

        Returns
        -------
        BeautifulSoup or None
            Parsed HTML, or None if request failed
        """
        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()
            time.sleep(config.RATE_LIMIT_DELAY)
            return BeautifulSoup(response.content, 'lxml')
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    def search_ibdb(self, title: str) -> Optional[str]:
        """
        Search IBDB for a show and return the URL of the first match.

        Parameters
        ----------
        title : str
            Show title to search

        Returns
        -------
        str or None
            URL of the show page, or None if not found
        """
        search_url = f"https://www.ibdb.com/broadway-production/{quote_plus(title)}"

        # Try direct URL first (if title is URL-friendly)
        soup = self._get_page(search_url)
        if soup and self._is_valid_show_page(soup):
            return search_url

        # Otherwise, use search
        search_url = f"https://www.ibdb.com/search?q={quote_plus(title)}&type=production"
        soup = self._get_page(search_url)

        if soup is None:
            return None

        # Find first result link
        # IBDB search results typically in <div class="search-result"> or similar
        # TODO: This selector may need adjustment based on actual IBDB HTML structure
        results = soup.find_all('a', href=re.compile(r'/broadway-production/'))

        if results:
            first_result = results[0]
            href = first_result.get('href')
            if href:
                return f"https://www.ibdb.com{href}" if href.startswith('/') else href

        logger.warning(f"No IBDB page found for: {title}")
        return None

    def _is_valid_show_page(self, soup: BeautifulSoup) -> bool:
        """Check if soup represents a valid IBDB show page."""
        # Simple heuristic: look for producer section or show title
        return bool(soup.find(string=re.compile(r'Produced by', re.IGNORECASE)))

    def scrape_ibdb_producers(self, title: str, opening_year: Optional[int] = None) -> Dict:
        """
        Scrape producer information from IBDB for a given show.

        Parameters
        ----------
        title : str
            Show title
        opening_year : int, optional
            Opening year (helps with disambiguation)

        Returns
        -------
        dict
            {
                'title': str,
                'opening_year': int or None,
                'producers_raw': str (raw producer text),
                'producers_list': list of str,
                'lead_producers_list': list of str,
                'co_producers_list': list of str,
                'producer_count_total': int,
                'lead_producer_count': int,
                'co_producer_count': int,
                'source_url': str,
                'scrape_success': bool,
            }
        """
        result = {
            'title': title,
            'opening_year': opening_year,
            'producers_raw': None,
            'producers_list': [],
            'lead_producers_list': [],
            'co_producers_list': [],
            'producer_count_total': 0,
            'lead_producer_count': 0,
            'co_producer_count': 0,
            'source_url': None,
            'scrape_success': False,
        }

        # Search for show page
        url = self.search_ibdb(title)
        if url is None:
            logger.warning(f"Could not find IBDB page for: {title}")
            return result

        result['source_url'] = url

        # Scrape show page
        soup = self._get_page(url)
        if soup is None:
            return result

        # Find producer section
        # IBDB typically has a section like:
        # <h3>Produced by</h3>
        # <div>Producer names...</div>
        # OR
        # <dt>Produced by</dt><dd>Producer names...</dd>

        producer_text = None

        # Strategy 1: Look for "Produced by" header
        produced_by_header = soup.find(['h3', 'h4', 'dt'], string=re.compile(r'Produced by', re.IGNORECASE))
        if produced_by_header:
            # Get next sibling or next element
            next_elem = produced_by_header.find_next_sibling()
            if next_elem:
                producer_text = next_elem.get_text(separator='\n', strip=True)

        # Strategy 2: Look for div/section with class or id containing "producer"
        if not producer_text:
            producer_section = soup.find(['div', 'section'], class_=re.compile(r'producer', re.IGNORECASE))
            if producer_section:
                producer_text = producer_section.get_text(separator='\n', strip=True)

        if not producer_text:
            logger.warning(f"Could not find producer section for: {title}")
            return result

        result['producers_raw'] = producer_text

        # Parse producers
        # Try to distinguish lead vs co-producers based on section headings or ordering
        # Common pattern: "Lead Producer(s):" followed by names, then "Co-Producer(s):" followed by names

        lead_producers = []
        co_producers = []

        # Check for explicit sections
        if re.search(r'lead producer', producer_text, re.IGNORECASE):
            # Split into sections
            sections = re.split(r'\n\s*(?=Lead Producer|Co-Producer)', producer_text, flags=re.IGNORECASE)
            for section in sections:
                if re.match(r'lead producer', section, re.IGNORECASE):
                    section_text = re.sub(r'^lead producer[s]?\s*:?\s*', '', section, flags=re.IGNORECASE)
                    lead_producers.extend(parse_producer_list(section_text))
                elif re.match(r'co-?producer', section, re.IGNORECASE):
                    section_text = re.sub(r'^co-?producer[s]?\s*:?\s*', '', section, flags=re.IGNORECASE)
                    co_producers.extend(parse_producer_list(section_text))
        else:
            # No explicit distinction: assume all are lead producers
            # (Conservative: we don't want to misclassify)
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

        # Sanity check
        if result['producer_count_total'] > config.MAX_PRODUCER_COUNT:
            logger.warning(f"Unusually high producer count ({result['producer_count_total']}) for {title}. Check data.")

        return result

    def scrape_shows(self, shows_df: pd.DataFrame) -> pd.DataFrame:
        """
        Scrape producer information for a list of shows.

        Parameters
        ----------
        shows_df : pd.DataFrame
            DataFrame with columns: title, opening_year (or tony_year)

        Returns
        -------
        pd.DataFrame
            Producer information for each show
        """
        results = []

        for idx, row in shows_df.iterrows():
            title = row['title']
            opening_year = row.get('opening_year') or row.get('tony_year')

            logger.info(f"Scraping producers for: {title} ({opening_year})")

            result = self.scrape_ibdb_producers(title, opening_year)
            results.append(result)

        return pd.DataFrame(results)


def main():
    """
    Main function: scrape producer data for Tony-nominated shows.
    """
    logger.info("Starting producer scraper...")

    # Load Tony outcomes (from previous step)
    tony_outcomes_file = config.RAW_DATA_DIR / "tony_outcomes_aggregated.csv"

    if not tony_outcomes_file.exists():
        logger.error(f"Tony outcomes file not found: {tony_outcomes_file}")
        logger.error("Please run scrape_tonys.py first.")
        return

    tony_df = pd.read_csv(tony_outcomes_file)
    logger.info(f"Loaded {len(tony_df)} shows from Tony outcomes")

    # Scrape producers
    scraper = ProducerScraper()
    producers_df = scraper.scrape_shows(tony_df)

    # Save raw output
    raw_output = config.PRODUCERS_RAW_CSV
    producers_df.to_csv(raw_output, index=False)
    logger.info(f"Saved raw producer data to {raw_output}")

    # Create cleaned version (just the counts and key fields)
    clean_df = producers_df[[
        'title', 'opening_year', 'producer_count_total',
        'lead_producer_count', 'co_producer_count',
        'source_url', 'scrape_success'
    ]].copy()

    clean_output = config.PRODUCERS_CLEAN_CSV
    clean_df.to_csv(clean_output, index=False)
    logger.info(f"Saved cleaned producer data to {clean_output}")

    # Report statistics
    success_count = producers_df['scrape_success'].sum()
    logger.info(f"Successfully scraped {success_count} / {len(producers_df)} shows")

    if success_count > 0:
        avg_producers = producers_df[producers_df['scrape_success']]['producer_count_total'].mean()
        logger.info(f"Average producer count: {avg_producers:.1f}")


if __name__ == "__main__":
    main()
