#!/usr/bin/env python3
"""
Comprehensive SEC Form D Data Collection Pipeline
Retrieves, parses, and structures Form D filings for Broadway theatrical productions
"""

import requests
import pandas as pd
import time
import re
import json
from pathlib import Path
from typing import List, Dict, Optional
import logging
from datetime import datetime, timedelta
from form_d_parser import FormDParser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BroadwayFormDCollector:
    """Comprehensive Form D data collector for Broadway productions"""

    HEADERS = {
        'User-Agent': 'Broadway Research Analysis research@university.edu',
        'Accept-Encoding': 'gzip, deflate'
    }

    # Broadway/theatrical identification patterns
    THEATRICAL_PATTERNS = {
        'keywords': [
            'broadway', 'theatrical', 'theatre', 'theater', 'musical', 'play',
            'production', 'show', 'stage', 'drama', 'comedy', 'revival',
            'performing arts', 'live entertainment'
        ],
        'entity_types': [
            r'production[s]?\s+(llc|lp|inc)',
            r'theatrical\s+',
            r'broadway\s+',
            r'\s+musical\s+',
            r'\s+play\s+'
        ],
        'known_shows': [
            'hamilton', 'hadestown', 'lion king', 'wicked', 'phantom',
            'chicago', 'moulin rouge', 'funny girl', 'music man',
            'harry potter', 'beetlejuice', 'back to the future',
            'les miserables', 'rent', 'dear evan hansen', 'come from away',
            'six', 'mrs doubtfire', 'tootsie', 'mean girls', 'frozen',
            'aladdin', 'book of mormon', 'jersey boys', 'kinky boots',
            'sweeney todd', 'into the woods', 'company', 'cabaret',
            'spring awakening', 'hedwig', 'waitress', 'anastasia'
        ]
    }

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / 'raw'
        self.processed_dir = self.data_dir / 'processed'

        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

        self.parser = FormDParser()
        self.rate_limit = 0.1  # 10 requests/second max for SEC

    def _request_with_retry(self, url: str, max_retries: int = 3) -> Optional[requests.Response]:
        """Make HTTP request with exponential backoff retry"""
        for attempt in range(max_retries):
            try:
                time.sleep(self.rate_limit)
                response = requests.get(url, headers=self.HEADERS, timeout=30)
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:  # Rate limited
                    wait_time = (2 ** attempt) * 2
                    logger.warning(f"Rate limited, waiting {wait_time}s")
                    time.sleep(wait_time)
                else:
                    logger.warning(f"HTTP {response.status_code} for {url}")
                    return None
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
        return None

    def is_theatrical(self, entity_name: str, business_desc: str = "") -> tuple:
        """
        Determine if entity is theatrical production

        Returns:
            (is_theatrical: bool, match_reason: str)
        """
        text = (entity_name + " " + business_desc).lower()

        # Check keywords
        for keyword in self.THEATRICAL_PATTERNS['keywords']:
            if keyword in text:
                return True, f"keyword: {keyword}"

        # Check entity type patterns
        for pattern in self.THEATRICAL_PATTERNS['entity_types']:
            if re.search(pattern, text, re.IGNORECASE):
                return True, f"entity_pattern: {pattern}"

        # Check known shows
        for show in self.THEATRICAL_PATTERNS['known_shows']:
            if show in text:
                return True, f"known_show: {show}"

        return False, "no_match"

    def get_company_tickers(self) -> pd.DataFrame:
        """
        Retrieve company ticker mapping from SEC
        This helps identify entities in EDGAR
        """
        url = "https://www.sec.gov/files/company_tickers.json"
        response = self._request_with_retry(url)

        if response:
            data = response.json()
            df = pd.DataFrame.from_dict(data, orient='index')
            return df
        return pd.DataFrame()

    def search_edgar_full_text(self, query: str, start_date: str, end_date: str) -> List[Dict]:
        """
        Search SEC EDGAR using full-text search API

        Note: SEC's full-text search endpoint structure
        """
        # This is a placeholder - SEC's actual search API requires
        # web scraping or using their RSS feeds
        results = []

        logger.info(f"Searching for: {query} between {start_date} and {end_date}")

        # Alternative approach: Use SEC's RSS feed for daily filings
        # and filter by Form D
        return results

    def get_daily_index(self, date: datetime) -> List[Dict]:
        """
        Retrieve daily filing index from SEC EDGAR

        Args:
            date: Date to retrieve index for

        Returns:
            List of filing metadata dictionaries
        """
        year = date.year
        quarter = (date.month - 1) // 3 + 1
        date_str = date.strftime('%Y%m%d')

        # SEC daily index URL structure
        url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&CIK=&type=D&company=&dateb={date_str}&owner=exclude&start=0&count=100&output=atom"

        # Alternative: Use the daily index files
        index_url = f"https://www.sec.gov/Archives/edgar/daily-index/{year}/QTR{quarter}/master.{date_str}.idx"

        response = self._request_with_retry(index_url)

        if response and response.status_code == 200:
            return self._parse_daily_index(response.text)

        return []

    def _parse_daily_index(self, index_content: str) -> List[Dict]:
        """Parse SEC daily index file"""
        filings = []
        lines = index_content.split('\n')

        # Skip header lines (typically first 11 lines)
        data_started = False
        for line in lines:
            if line.startswith('---'):
                data_started = True
                continue

            if not data_started:
                continue

            # Parse pipe-delimited or fixed-width format
            if '|' in line:
                parts = line.split('|')
                if len(parts) >= 5:
                    filing = {
                        'cik': parts[0].strip(),
                        'company_name': parts[1].strip(),
                        'form_type': parts[2].strip(),
                        'date_filed': parts[3].strip(),
                        'filename': parts[4].strip()
                    }

                    if filing['form_type'] in ['D', 'D/A']:
                        filings.append(filing)

        return filings

    def collect_filings_by_date_range(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Collect all Form D filings within date range

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame of filings metadata
        """
        all_filings = []
        current_date = start_date

        while current_date <= end_date:
            logger.info(f"Processing {current_date.strftime('%Y-%m-%d')}")

            daily_filings = self.get_daily_index(current_date)

            for filing in daily_filings:
                is_theatrical, reason = self.is_theatrical(filing['company_name'])
                if is_theatrical:
                    filing['match_reason'] = reason
                    all_filings.append(filing)
                    logger.info(f"Found theatrical filing: {filing['company_name']} ({reason})")

            current_date += timedelta(days=1)
            time.sleep(self.rate_limit)

        if all_filings:
            return pd.DataFrame(all_filings)
        return pd.DataFrame()

    def download_filing_xml(self, filename: str) -> Optional[str]:
        """
        Download full Form D XML filing

        Args:
            filename: EDGAR filename path (e.g., edgar/data/1234567/0001234567-12-000001.txt)

        Returns:
            XML content as string
        """
        base_url = "https://www.sec.gov/Archives"
        full_url = f"{base_url}/{filename}"

        response = self._request_with_retry(full_url)

        if response:
            return response.text
        return None

    def process_all_filings(self, filings_df: pd.DataFrame) -> pd.DataFrame:
        """
        Download and parse all identified Form D filings

        Args:
            filings_df: DataFrame with filing metadata (must have 'filename' column)

        Returns:
            DataFrame with fully parsed Form D data
        """
        parsed_filings = []

        for idx, row in filings_df.iterrows():
            logger.info(f"Processing {idx + 1}/{len(filings_df)}: {row['company_name']}")

            xml_content = self.download_filing_xml(row['filename'])

            if xml_content:
                # Extract accession number from filename
                accession = row['filename'].split('/')[-1].replace('.txt', '')

                parsed_data = self.parser.parse_xml_filing(xml_content, accession)

                if parsed_data:
                    # Add metadata
                    parsed_data['cik'] = row.get('cik')
                    parsed_data['match_reason'] = row.get('match_reason')
                    parsed_filings.append(parsed_data)

            time.sleep(self.rate_limit)

        if parsed_filings:
            return pd.DataFrame(parsed_filings)
        return pd.DataFrame()

    def run_full_collection(self, start_year: int = 2010, end_year: int = 2025) -> pd.DataFrame:
        """
        Execute complete data collection pipeline

        Args:
            start_year: Starting year (inclusive)
            end_year: Ending year (inclusive)

        Returns:
            Fully parsed and structured DataFrame
        """
        start_date = datetime(start_year, 1, 1)
        end_date = min(datetime(end_year, 12, 31), datetime.now())

        logger.info(f"Starting full collection: {start_date} to {end_date}")

        # Step 1: Collect filing metadata
        logger.info("Step 1: Collecting Form D filing metadata...")
        filings_metadata = self.collect_filings_by_date_range(start_date, end_date)

        if filings_metadata.empty:
            logger.warning("No theatrical Form D filings found")
            return pd.DataFrame()

        # Save metadata
        metadata_path = self.raw_dir / 'form_d_metadata.csv'
        filings_metadata.to_csv(metadata_path, index=False)
        logger.info(f"Saved {len(filings_metadata)} filing records to {metadata_path}")

        # Step 2: Download and parse full XML filings
        logger.info("Step 2: Downloading and parsing Form D XML filings...")
        parsed_data = self.process_all_filings(filings_metadata)

        if not parsed_data.empty:
            # Save parsed data
            output_path = self.processed_dir / 'broadway_form_d_2010_2025.csv'
            parsed_data.to_csv(output_path, index=False)
            logger.info(f"Saved {len(parsed_data)} parsed filings to {output_path}")

        return parsed_data


def main():
    """Main execution"""
    project_dir = Path(__file__).parent.parent
    data_dir = project_dir / 'data'

    collector = BroadwayFormDCollector(data_dir)

    logger.info("=" * 80)
    logger.info("SEC Form D Broadway Theatrical Production Data Collection")
    logger.info("Date Range: 2010-01-01 to 2025-12-31")
    logger.info("=" * 80)

    # Run full collection
    results = collector.run_full_collection(2010, 2025)

    if not results.empty:
        logger.info(f"\nCollection complete! Total filings: {len(results)}")
        logger.info(f"\nSample data:")
        print(results.head())
    else:
        logger.warning("No data collected")


if __name__ == "__main__":
    main()
