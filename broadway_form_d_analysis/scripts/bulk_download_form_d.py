#!/usr/bin/env python3
"""
SEC EDGAR Bulk Form D Downloader
Downloads SEC's bulk Form D datasets instead of scraping daily indices
Much faster and avoids rate limiting issues!
"""

import requests
import zipfile
import pandas as pd
import xml.etree.ElementTree as ET
from pathlib import Path
import logging
import time
from datetime import datetime
from typing import List, Dict, Optional
import io
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from form_d_parser import FormDParser
from collect_form_d_data import BroadwayFormDCollector
from sec_config import get_user_agent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SECBulkFormDDownloader:
    """Downloads and processes SEC's bulk Form D datasets"""

    # SEC bulk data URLs
    BASE_URL = "https://www.sec.gov/dera/data"
    FORM_D_URL = f"{BASE_URL}/form-d-filings"

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / 'raw' / 'bulk'
        self.processed_dir = self.data_dir / 'processed'

        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

        self.parser = FormDParser()
        self.filter = BroadwayFormDCollector(self.data_dir)

        # Get SEC-compliant User-Agent
        user_agent = get_user_agent()
        self.headers = {
            'User-Agent': user_agent,
            'Accept': 'application/json, application/xml, text/xml, */*',
            'Accept-Encoding': 'gzip, deflate'
        }
        logger.info(f"Using User-Agent: {user_agent}")

    def download_bulk_dataset(self, year: int = None, quarter: int = None) -> Optional[Path]:
        """
        Download SEC's bulk Form D dataset

        Args:
            year: Specific year to download (2010-2025)
            quarter: Specific quarter (1-4), or None for full year

        Returns:
            Path to downloaded file, or None if failed
        """
        # SEC provides Form D data at this location
        # Note: URL structure may vary - checking common patterns

        possible_urls = []

        if year and quarter:
            # Quarterly file
            filename = f"form_d_{year}_Q{quarter}.zip"
            possible_urls.append(f"{self.FORM_D_URL}/{filename}")
            possible_urls.append(f"{self.FORM_D_URL}/{year}/Q{quarter}/form_d.zip")
        elif year:
            # Annual file
            filename = f"form_d_{year}.zip"
            possible_urls.append(f"{self.FORM_D_URL}/{filename}")
            possible_urls.append(f"{self.FORM_D_URL}/{year}/form_d_full.zip")
        else:
            # Complete dataset
            filename = "form_d_all.zip"
            possible_urls.append(f"{self.FORM_D_URL}/{filename}")
            possible_urls.append(f"{self.FORM_D_URL}/form_d_complete.zip")

        logger.info(f"Attempting to download Form D bulk data for {year or 'all years'}")

        # Try each possible URL
        for url in possible_urls:
            logger.info(f"Trying: {url}")

            try:
                response = requests.get(url, headers=self.headers, timeout=60, stream=True)

                if response.status_code == 200:
                    # Download successful
                    output_path = self.raw_dir / filename

                    # Download with progress
                    total_size = int(response.headers.get('content-length', 0))
                    logger.info(f"Downloading {total_size / (1024*1024):.1f} MB...")

                    with open(output_path, 'wb') as f:
                        downloaded = 0
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                pct = (downloaded / total_size) * 100
                                if int(pct) % 10 == 0:
                                    logger.info(f"Progress: {pct:.0f}%")

                    logger.info(f"✓ Downloaded to {output_path}")
                    return output_path

                elif response.status_code == 404:
                    logger.debug(f"Not found: {url}")
                    continue
                else:
                    logger.warning(f"HTTP {response.status_code} for {url}")

            except requests.exceptions.RequestException as e:
                logger.warning(f"Failed to download from {url}: {e}")
                continue

        logger.error("Could not download bulk data from any known URL")
        return None

    def download_via_edgar_api(self) -> Optional[pd.DataFrame]:
        """
        Alternative: Use SEC's EDGAR full-text search API to get Form D metadata
        Then download individual filings

        This is slower but more reliable than bulk downloads
        """
        logger.info("Using SEC EDGAR API for Form D collection...")

        all_filings = []

        # Search in batches
        for year in range(2010, 2026):
            logger.info(f"Collecting Form D filings for {year}...")

            # Use SEC's JSON API
            search_url = "https://efts.sec.gov/LATEST/search-index"

            page = 0
            while True:
                params = {
                    'q': f'formType:"D" AND filedAt:[{year}-01-01 TO {year}-12-31]',
                    'from': page * 100,
                    'size': 100,
                    'sort': [{'filedAt': {'order': 'desc'}}]
                }

                try:
                    time.sleep(0.2)  # Rate limiting
                    response = requests.get(search_url, headers=self.headers,
                                          params=params, timeout=30)

                    if response.status_code != 200:
                        logger.warning(f"HTTP {response.status_code} for year {year}")
                        break

                    data = response.json()
                    hits = data.get('hits', {}).get('hits', [])

                    if not hits:
                        break

                    for hit in hits:
                        source = hit.get('_source', {})
                        entity_name = source.get('display_names', [''])[0] if source.get('display_names') else ''

                        # Filter for Broadway productions
                        is_theatrical, reason = self.filter.is_theatrical(entity_name)

                        if is_theatrical:
                            filing = {
                                'entity_name': entity_name,
                                'accession_number': source.get('accession_number'),
                                'filing_date': source.get('filedAt'),
                                'cik': source.get('cik'),
                                'match_reason': reason
                            }
                            all_filings.append(filing)
                            logger.info(f"Found: {entity_name} ({reason})")

                    logger.info(f"  Year {year}: Page {page + 1}, found {len(hits)} filings")

                    # Check if more pages
                    total = data.get('hits', {}).get('total', {}).get('value', 0)
                    if (page + 1) * 100 >= total:
                        break

                    page += 1

                except Exception as e:
                    logger.error(f"Error searching year {year}: {e}")
                    break

            time.sleep(1)  # Pause between years

        if all_filings:
            return pd.DataFrame(all_filings)
        return pd.DataFrame()

    def extract_and_parse_bulk_zip(self, zip_path: Path) -> pd.DataFrame:
        """
        Extract and parse bulk ZIP file containing Form D filings

        Args:
            zip_path: Path to downloaded ZIP file

        Returns:
            DataFrame with parsed Form D data
        """
        logger.info(f"Extracting and parsing {zip_path}")

        parsed_filings = []

        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # List all XML files in the ZIP
                xml_files = [f for f in zip_ref.namelist() if f.endswith('.xml')]

                logger.info(f"Found {len(xml_files)} XML files in ZIP")

                for idx, xml_file in enumerate(xml_files):
                    if (idx + 1) % 100 == 0:
                        logger.info(f"Processing {idx + 1}/{len(xml_files)}...")

                    try:
                        # Read XML content
                        xml_content = zip_ref.read(xml_file).decode('utf-8')

                        # Extract accession number from filename
                        accession = Path(xml_file).stem

                        # Parse the Form D
                        parsed = self.parser.parse_xml_filing(xml_content, accession)

                        if parsed:
                            # Filter for Broadway productions
                            entity_name = parsed.get('entity_name', '')
                            is_theatrical, reason = self.filter.is_theatrical(entity_name)

                            if is_theatrical:
                                parsed['match_reason'] = reason
                                parsed_filings.append(parsed)
                                logger.info(f"✓ Broadway filing: {entity_name} ({reason})")

                    except Exception as e:
                        logger.warning(f"Failed to parse {xml_file}: {e}")
                        continue

        except zipfile.BadZipFile as e:
            logger.error(f"Invalid ZIP file: {e}")
            return pd.DataFrame()

        if parsed_filings:
            logger.info(f"Extracted {len(parsed_filings)} Broadway Form D filings")
            return pd.DataFrame(parsed_filings)

        return pd.DataFrame()

    def download_individual_filings(self, metadata_df: pd.DataFrame) -> pd.DataFrame:
        """
        Download individual Form D XML files based on metadata

        Args:
            metadata_df: DataFrame with accession numbers and CIKs

        Returns:
            DataFrame with fully parsed Form D data
        """
        logger.info(f"Downloading {len(metadata_df)} individual Form D filings...")

        parsed_filings = []
        failed = 0

        for idx, row in metadata_df.iterrows():
            if (idx + 1) % 10 == 0:
                logger.info(f"Progress: {idx + 1}/{len(metadata_df)} ({len(parsed_filings)} successful, {failed} failed)")

            accession = row['accession_number'].replace('-', '')
            cik = str(row['cik']).zfill(10)

            # Construct EDGAR URL
            # Format: https://www.sec.gov/Archives/edgar/data/CIK/ACCESSION/primary_doc.xml
            base_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}"

            # Try multiple filename patterns
            filenames = ['primary_doc.xml', 'formDX01.xml', 'doc.xml', 'form_d.xml']

            xml_content = None
            for filename in filenames:
                url = f"{base_url}/{filename}"

                try:
                    time.sleep(0.2)  # Rate limiting
                    response = requests.get(url, headers=self.headers, timeout=30)

                    if response.status_code == 200:
                        xml_content = response.text
                        break

                except Exception as e:
                    continue

            if xml_content:
                parsed = self.parser.parse_xml_filing(xml_content, row['accession_number'])

                if parsed:
                    parsed['cik'] = row['cik']
                    parsed['match_reason'] = row['match_reason']
                    parsed_filings.append(parsed)
                else:
                    failed += 1
            else:
                failed += 1
                logger.warning(f"Could not download filing for {row['entity_name']}")

        logger.info(f"Final: {len(parsed_filings)} successful, {failed} failed")

        if parsed_filings:
            return pd.DataFrame(parsed_filings)
        return pd.DataFrame()

    def run_bulk_collection(self, method: str = 'api') -> pd.DataFrame:
        """
        Execute complete bulk data collection

        Args:
            method: 'api' (use EDGAR API) or 'download' (try bulk download)

        Returns:
            DataFrame with all parsed Broadway Form D filings
        """
        logger.info("=" * 80)
        logger.info("SEC FORM D BULK DATA COLLECTION")
        logger.info("=" * 80)

        if method == 'api':
            # Method 1: Use EDGAR API (slower but reliable)
            logger.info("Using EDGAR API method...")

            metadata_df = self.download_via_edgar_api()

            if metadata_df.empty:
                logger.error("No Form D filings found via API")
                return pd.DataFrame()

            # Save metadata
            metadata_path = self.raw_dir / 'form_d_metadata.csv'
            metadata_df.to_csv(metadata_path, index=False)
            logger.info(f"Saved metadata: {len(metadata_df)} Broadway filings")

            # Download individual XML files
            parsed_df = self.download_individual_filings(metadata_df)

        else:
            # Method 2: Try bulk download (faster if available)
            logger.info("Attempting bulk download...")

            # Try downloading complete dataset
            zip_path = self.download_bulk_dataset()

            if zip_path:
                parsed_df = self.extract_and_parse_bulk_zip(zip_path)
            else:
                logger.warning("Bulk download failed, falling back to API method")
                return self.run_bulk_collection(method='api')

        # Save final results
        if not parsed_df.empty:
            output_path = self.processed_dir / 'broadway_form_d_2010_2025.csv'
            parsed_df.to_csv(output_path, index=False)
            logger.info(f"✓ Saved {len(parsed_df)} Broadway Form D filings to {output_path}")

        return parsed_df


def main():
    """Main execution"""
    project_dir = Path(__file__).parent.parent
    data_dir = project_dir / 'data'

    downloader = SECBulkFormDDownloader(data_dir)

    logger.info("Starting SEC Form D bulk collection...")
    logger.info("Method: EDGAR API (more reliable than bulk downloads)")

    # Run collection using API method
    results = downloader.run_bulk_collection(method='api')

    if not results.empty:
        logger.info(f"\n{'=' * 80}")
        logger.info(f"SUCCESS! Collected {len(results)} Broadway Form D filings")
        logger.info(f"{'=' * 80}")
        logger.info(f"\nDate range: {results['filing_date'].min()} to {results['filing_date'].max()}")
        logger.info(f"\nSample data:")
        print(results[['entity_name', 'filing_date', 'total_offering_amount']].head(10))
    else:
        logger.warning("No data collected")


if __name__ == "__main__":
    main()
