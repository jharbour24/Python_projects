#!/usr/bin/env python3
"""
SEC EDGAR Form D Retrieval Script
Retrieves Form D filings related to Broadway and theatrical productions from 2010-2025
"""

import requests
import xml.etree.ElementTree as ET
import pandas as pd
import time
import re
from datetime import datetime, timedelta
from pathlib import Path
import json
from typing import List, Dict, Optional
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SECEdgarRetriever:
    """Retrieves Form D filings from SEC EDGAR"""

    # SEC requires user agent with contact info
    HEADERS = {
        'User-Agent': 'Broadway Analysis Research contact@example.com',
        'Accept-Encoding': 'gzip, deflate',
        'Host': 'www.sec.gov'
    }

    BASE_URL = "https://www.sec.gov"
    SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"

    # Broadway/theatrical keywords for filtering
    THEATRICAL_KEYWORDS = [
        'broadway', 'theatrical', 'theatre', 'theater', 'musical', 'play',
        'productions', 'show', 'entertainment', 'stage', 'performance',
        'drama', 'comedy', 'revival', 'touring', 'production llc',
        'production lp', 'production limited'
    ]

    # Specific show patterns (can be expanded)
    SHOW_PATTERNS = [
        r'hamilton', r'hadestown', r'lion king', r'wicked', r'phantom',
        r'chicago', r'moulin rouge', r'funny girl', r'music man',
        r'harry potter', r'cursed child', r'beetlejuice', r'back to the future',
        r'les mis[eé]rables', r'rent', r'dear evan hansen', r'come from away',
        r'six', r'mrs doubtfire', r'tootsie', r'mean girls', r'frozen',
        r'aladdin', r'book of mormon', r'jersey boys', r'kinky boots'
    ]

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.rate_limit_delay = 0.1  # SEC rate limit: 10 requests/second

    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[requests.Response]:
        """Make HTTP request with rate limiting and error handling"""
        try:
            time.sleep(self.rate_limit_delay)
            response = requests.get(url, headers=self.HEADERS, params=params, timeout=30)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None

    def search_form_d_filings(self, start_date: str, end_date: str,
                             page: int = 0, size: int = 100) -> Optional[Dict]:
        """
        Search for Form D filings within date range

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            page: Page number (0-indexed)
            size: Results per page (max 100)
        """
        params = {
            'q': 'formType:"D"',
            'dateRange': 'custom',
            'startdt': start_date,
            'enddt': end_date,
            'page': page,
            'from': page * size,
            'size': size
        }

        response = self._make_request(self.SEARCH_URL, params=params)
        if response:
            try:
                return response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
        return None

    def is_theatrical_production(self, entity_name: str, description: str = "") -> bool:
        """
        Determine if entity is related to Broadway/theatrical production

        Args:
            entity_name: Name of the issuer entity
            description: Business description if available
        """
        text = (entity_name + " " + description).lower()

        # Check for exact keyword matches
        for keyword in self.THEATRICAL_KEYWORDS:
            if keyword in text:
                return True

        # Check for show title patterns
        for pattern in self.SHOW_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        return False

    def get_filing_detail(self, accession_number: str) -> Optional[str]:
        """
        Retrieve full Form D filing XML content

        Args:
            accession_number: SEC accession number (e.g., 0001234567-12-000001)
        """
        # Format accession number for URL (remove dashes)
        acc_no_nodash = accession_number.replace('-', '')

        # Construct URL to primary document
        # Form D is typically filed as primary_doc.xml
        filing_url = f"{self.BASE_URL}/Archives/edgar/data/{acc_no_nodash}/{accession_number}/primary_doc.xml"

        # Try alternative naming conventions
        alt_urls = [
            filing_url,
            f"{self.BASE_URL}/Archives/edgar/data/{acc_no_nodash}/{accession_number}/formDX01.xml",
            f"{self.BASE_URL}/Archives/edgar/data/{acc_no_nodash}/{accession_number}/d.xml"
        ]

        for url in alt_urls:
            response = self._make_request(url)
            if response and response.status_code == 200:
                return response.text

        logger.warning(f"Could not retrieve filing for accession {accession_number}")
        return None

    def retrieve_quarterly_filings(self, year: int, quarter: int) -> List[Dict]:
        """
        Retrieve Form D filings for a specific quarter

        Args:
            year: Year (2010-2025)
            quarter: Quarter (1-4)
        """
        # Calculate date range for quarter
        month_start = (quarter - 1) * 3 + 1
        if quarter == 4:
            month_end = 12
            day_end = 31
        else:
            month_end = quarter * 3
            day_end = 30

        start_date = f"{year}-{month_start:02d}-01"
        end_date = f"{year}-{month_end:02d}-{day_end:02d}"

        logger.info(f"Retrieving Form D filings for Q{quarter} {year} ({start_date} to {end_date})")

        all_results = []
        page = 0

        while True:
            results = self.search_form_d_filings(start_date, end_date, page=page)

            if not results or 'hits' not in results or 'hits' not in results['hits']:
                break

            hits = results['hits']['hits']
            if not hits:
                break

            all_results.extend(hits)
            logger.info(f"Retrieved page {page + 1}, total results: {len(all_results)}")

            # Check if there are more pages
            total = results['hits']['total']['value']
            if len(all_results) >= total:
                break

            page += 1
            time.sleep(0.1)  # Rate limiting

        return all_results

    def retrieve_all_filings(self, start_year: int = 2010, end_year: int = 2025) -> pd.DataFrame:
        """
        Retrieve all Form D filings for the specified year range

        Args:
            start_year: Starting year (inclusive)
            end_year: Ending year (inclusive)
        """
        all_filings = []

        for year in range(start_year, end_year + 1):
            for quarter in range(1, 5):
                # Don't search future quarters
                if year == 2025 and quarter > 4:
                    break
                if datetime(year, (quarter - 1) * 3 + 1, 1) > datetime.now():
                    break

                filings = self.retrieve_quarterly_filings(year, quarter)

                # Filter for theatrical productions
                theatrical_filings = []
                for filing in filings:
                    source = filing.get('_source', {})
                    entity_name = source.get('display_names', [''])[0] if source.get('display_names') else ''

                    if self.is_theatrical_production(entity_name):
                        theatrical_filings.append(filing)

                logger.info(f"Q{quarter} {year}: Found {len(theatrical_filings)} theatrical filings out of {len(filings)} total")
                all_filings.extend(theatrical_filings)

        # Convert to DataFrame
        if all_filings:
            df = pd.json_normalize([f['_source'] for f in all_filings])
            return df
        else:
            return pd.DataFrame()

    def save_raw_filings(self, filings_df: pd.DataFrame, filename: str = 'raw_form_d_search_results.csv'):
        """Save raw search results to CSV"""
        output_path = self.output_dir / filename
        filings_df.to_csv(output_path, index=False)
        logger.info(f"Saved {len(filings_df)} filings to {output_path}")
        return output_path


def main():
    """Main execution function"""
    output_dir = Path(__file__).parent.parent / 'data' / 'raw'

    retriever = SECEdgarRetriever(output_dir)

    logger.info("Starting Form D retrieval process...")
    logger.info("Date range: 2010-01-01 to 2025-12-31")

    # Retrieve all filings
    filings_df = retriever.retrieve_all_filings(2010, 2025)

    if not filings_df.empty:
        logger.info(f"Total theatrical Form D filings found: {len(filings_df)}")

        # Save raw results
        retriever.save_raw_filings(filings_df)

        logger.info("Retrieval complete!")
    else:
        logger.warning("No filings found!")


if __name__ == "__main__":
    main()
