"""
Weekly Broadway grosses data collector.

Attempts to collect weekly grosses data from public sources.
If scraping is blocked or unavailable, provides helper functions to
import manually-obtained data.

Data sources (in order of preference):
1. Playbill grosses pages (if accessible)
2. The Numbers (if accessible)
3. Manual CSV drop-in (data/raw/grosses_raw.csv)

Expected fields per week:
- show_title
- week_ending_date
- weekly_gross
- capacity_pct (optional)
- avg_ticket_price (optional)
- performances (optional)

Author: Broadway Analysis Pipeline
"""

import re
import time
from typing import Dict, List, Optional
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import config
from utils import normalize_title, parse_date, setup_logger

logger = setup_logger(__name__)


class GrossesCollector:
    """Collector for weekly Broadway grosses data."""

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

    def scrape_playbill_grosses(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Attempt to scrape weekly grosses from Playbill.

        NOTE: This is a placeholder implementation. Playbill's grosses pages
        may be behind authentication or may have changed structure.

        Parameters
        ----------
        start_date : str
            Start date (ISO format)
        end_date : str
            End date (ISO format)

        Returns
        -------
        pd.DataFrame
            Weekly grosses data, or empty DataFrame if scraping fails
        """
        logger.warning("Playbill grosses scraping not implemented.")
        logger.warning("Playbill may require authentication or has anti-scraping measures.")
        logger.warning("TODO: Implement Playbill grosses scraping if accessible.")

        # Placeholder: return empty DataFrame
        return pd.DataFrame()

    def load_manual_grosses(self, filepath: Path = None) -> pd.DataFrame:
        """
        Load weekly grosses from a manually-provided CSV file.

        Expected CSV format:
        - show_title: str
        - week_ending_date: date (ISO format or parseable)
        - weekly_gross: float (dollar amount)
        - capacity_pct: float (0-100, optional)
        - avg_ticket_price: float (optional)
        - performances: int (optional)

        Parameters
        ----------
        filepath : Path, optional
            Path to CSV file (default: data/raw/grosses_raw.csv)

        Returns
        -------
        pd.DataFrame
            Loaded grosses data
        """
        if filepath is None:
            filepath = config.GROSSES_RAW_CSV

        if not filepath.exists():
            logger.error(f"Manual grosses file not found: {filepath}")
            logger.info("To use manual grosses data:")
            logger.info(f"  1. Obtain weekly grosses CSV (e.g., from Broadway World, Playbill, etc.)")
            logger.info(f"  2. Place it at: {filepath}")
            logger.info("  3. Ensure it has columns: show_title, week_ending_date, weekly_gross")
            logger.info("     Optional: capacity_pct, avg_ticket_price, performances")
            return pd.DataFrame()

        logger.info(f"Loading manual grosses from: {filepath}")

        df = pd.read_csv(filepath)

        # Validate required columns
        required_cols = ['show_title', 'week_ending_date', 'weekly_gross']
        missing = [col for col in required_cols if col not in df.columns]

        if missing:
            logger.error(f"Manual grosses CSV missing required columns: {missing}")
            return pd.DataFrame()

        # Parse dates
        df['week_ending_date'] = pd.to_datetime(df['week_ending_date'], errors='coerce')

        # Remove rows with invalid dates or grosses
        df = df.dropna(subset=['week_ending_date', 'weekly_gross'])

        logger.info(f"Loaded {len(df)} weekly grosses records")

        return df

    def normalize_grosses_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize and clean grosses data.

        - Normalize show titles
        - Ensure numeric types
        - Sort by show and date

        Parameters
        ----------
        df : pd.DataFrame
            Raw grosses data

        Returns
        -------
        pd.DataFrame
            Cleaned grosses data
        """
        if df.empty:
            return df

        # Normalize titles
        df['title_normalized'] = df['show_title'].apply(normalize_title)

        # Ensure numeric
        df['weekly_gross'] = pd.to_numeric(df['weekly_gross'], errors='coerce')

        if 'capacity_pct' in df.columns:
            df['capacity_pct'] = pd.to_numeric(df['capacity_pct'], errors='coerce')

        if 'avg_ticket_price' in df.columns:
            df['avg_ticket_price'] = pd.to_numeric(df['avg_ticket_price'], errors='coerce')

        # Sort
        df = df.sort_values(['show_title', 'week_ending_date'])

        logger.info(f"Normalized {len(df)} grosses records for {df['show_title'].nunique()} shows")

        return df

    def collect_grosses(self, start_year: int = None, end_year: int = None,
                       method: str = 'manual') -> pd.DataFrame:
        """
        Collect weekly grosses data.

        Parameters
        ----------
        start_year : int, optional
            Starting year (default: 2010)
        end_year : int, optional
            Ending year (default: current year)
        method : str
            Collection method: 'manual' (default), 'playbill', 'auto'

        Returns
        -------
        pd.DataFrame
            Weekly grosses data
        """
        if start_year is None:
            start_year = 2010
        if end_year is None:
            end_year = datetime.now().year

        if method == 'manual':
            df = self.load_manual_grosses()
        elif method == 'playbill':
            start_date = f"{start_year}-01-01"
            end_date = f"{end_year}-12-31"
            df = self.scrape_playbill_grosses(start_date, end_date)
        elif method == 'auto':
            # Try scraping first, fall back to manual
            logger.info("Attempting to scrape grosses...")
            start_date = f"{start_year}-01-01"
            end_date = f"{end_year}-12-31"
            df = self.scrape_playbill_grosses(start_date, end_date)
            if df.empty:
                logger.info("Scraping failed, falling back to manual CSV")
                df = self.load_manual_grosses()
        else:
            logger.error(f"Unknown method: {method}")
            return pd.DataFrame()

        # Normalize
        if not df.empty:
            df = self.normalize_grosses_data(df)

        return df


def create_grosses_template():
    """
    Create a template CSV for manual grosses data entry.

    This is a helper function for users who need to manually provide grosses data.
    """
    template_path = config.RAW_DATA_DIR / "grosses_raw_TEMPLATE.csv"

    template_data = {
        'show_title': ['Hamilton', 'Hamilton', 'Hadestown', 'Hadestown'],
        'week_ending_date': ['2015-08-16', '2015-08-23', '2019-05-05', '2019-05-12'],
        'weekly_gross': [587135.00, 622875.00, 412500.00, 438250.00],
        'capacity_pct': [99.8, 100.0, 95.2, 97.1],
        'avg_ticket_price': [123.45, 125.50, 98.30, 101.20],
        'performances': [8, 8, 8, 8],
    }

    df = pd.DataFrame(template_data)
    df.to_csv(template_path, index=False)

    logger.info(f"Created template CSV at: {template_path}")
    logger.info("Copy this template to 'grosses_raw.csv' and populate with real data.")


def main():
    """
    Main function: collect weekly grosses data.
    """
    logger.info("Starting grosses data collection...")

    # Create template for manual entry
    create_grosses_template()

    collector = GrossesCollector()

    # Attempt to collect grosses (default: manual CSV)
    df = collector.collect_grosses(method='auto')

    if df.empty:
        logger.warning("No grosses data collected.")
        logger.warning("Please provide manual data in: " + str(config.GROSSES_RAW_CSV))
        logger.warning("See grosses_raw_TEMPLATE.csv for expected format.")
        logger.warning("Grosses data sources:")
        logger.warning("  - Broadway League (member access only)")
        logger.warning("  - Playbill Grosses pages (may require scraping)")
        logger.warning("  - The Numbers (https://www.the-numbers.com/broadway)")
        logger.warning("  - Broadway World grosses archives")
        return

    # Save processed grosses
    output_path = config.PROCESSED_DATA_DIR / "weekly_grosses_preliminary.csv"
    df.to_csv(output_path, index=False)
    logger.info(f"Saved preliminary grosses data to: {output_path}")

    logger.info(f"Total weekly records: {len(df)}")
    logger.info(f"Shows covered: {df['show_title'].nunique()}")
    logger.info(f"Date range: {df['week_ending_date'].min()} to {df['week_ending_date'].max()}")


if __name__ == "__main__":
    main()
