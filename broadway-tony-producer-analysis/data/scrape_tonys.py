"""
Tony Awards scraper: nominations and wins (2010-present).

This module scrapes Tony Award nominations and wins from publicly available sources.
Primary sources:
- Wikipedia Tony Award year pages (e.g., "65th Tony Awards")
- TonyAwards.com (if accessible and structured)

For each year from 2011-present, extracts:
- Nominated shows by category
- Winners
- Computes aggregates: total nominations, total wins, major wins

Author: Broadway Analysis Pipeline
"""

import re
import time
from typing import Dict, List, Optional, Tuple
import pandas as pd
import requests
from bs4 import BeautifulSoup

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import config
from utils import normalize_title, create_show_id, setup_logger

logger = setup_logger(__name__)


class TonyScraper:
    """Scraper for Tony Awards nominations and wins."""

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

    def _scrape_wikipedia_tony_year(self, tony_year: int) -> List[Dict]:
        """
        Scrape Tony nominations from Wikipedia for a given year.

        Wikipedia pages follow pattern: "https://en.wikipedia.org/wiki/65th_Tony_Awards"

        Parameters
        ----------
        tony_year : int
            Tony ceremony year (e.g., 2011)

        Returns
        -------
        list of dict
            Each dict contains: title, category, nominated (bool), won (bool), tony_year
        """
        # Determine ordinal (65th, 66th, etc.)
        # First Tony Awards: 1947 (1st)
        ordinal_number = tony_year - 1947 + 1
        ordinal = self._get_ordinal(ordinal_number)

        url = f"https://en.wikipedia.org/wiki/{ordinal}_Tony_Awards"
        soup = self._get_page(url)

        if soup is None:
            logger.warning(f"Could not scrape Wikipedia for Tony year {tony_year}")
            return []

        records = []

        # Wikipedia structure: typically has tables or lists for each category
        # Strategy: look for headers with category names, then parse nominee lists

        # Find all headers (h2, h3) that might be categories
        headers = soup.find_all(['h2', 'h3'])

        for header in headers:
            category_text = header.get_text(strip=True)

            # Check if this is a Tony category
            # Common patterns: "Best Musical", "Best Play", "Best Revival of a Musical", etc.
            if not self._is_tony_category(category_text):
                continue

            category = category_text

            # Find the next sibling element (usually a <ul> or <table> with nominees)
            sibling = header.find_next_sibling()

            if sibling is None:
                continue

            # Parse nominees from list or table
            if sibling.name == 'ul':
                items = sibling.find_all('li', recursive=False)
                for item in items:
                    text = item.get_text()
                    title, won = self._parse_nominee_text(text)
                    if title:
                        records.append({
                            'title': title,
                            'category': category,
                            'nominated': True,
                            'won': won,
                            'tony_year': tony_year,
                        })

            elif sibling.name == 'table':
                # Some years use tables
                rows = sibling.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) < 1:
                        continue

                    text = cells[0].get_text()
                    title, won = self._parse_nominee_text(text)
                    if title:
                        records.append({
                            'title': title,
                            'category': category,
                            'nominated': True,
                            'won': won,
                            'tony_year': tony_year,
                        })

        logger.info(f"Scraped {len(records)} nominations for Tony year {tony_year}")
        return records

    def _get_ordinal(self, n: int) -> str:
        """Convert number to ordinal string (1 -> '1st', 2 -> '2nd', etc.)."""
        if 10 <= n % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
        return f"{n}{suffix}"

    def _is_tony_category(self, text: str) -> bool:
        """Check if header text represents a Tony Award category."""
        # List of keywords indicating a Tony category
        keywords = [
            'Best Musical', 'Best Play', 'Best Revival',
            'Best Book', 'Best Score', 'Best Actor', 'Best Actress',
            'Best Direction', 'Best Choreography', 'Best Orchestrations',
            'Best Scenic Design', 'Best Costume Design', 'Best Lighting',
            'Best Sound Design',
        ]
        return any(kw.lower() in text.lower() for kw in keywords)

    def _parse_nominee_text(self, text: str) -> Tuple[Optional[str], bool]:
        """
        Parse nominee text to extract show title and whether it won.

        Common patterns:
        - "Show Title (winner)" or "Show Title (WINNER)" or "Show Title – WINNER"
        - "Show Title" (no indication = nominee but not winner)
        - Sometimes: "Show Title – Producer Name" (extract just show)

        Returns
        -------
        tuple of (str or None, bool)
            (title, won)
        """
        if not text or not isinstance(text, str):
            return None, False

        text = text.strip()

        # Check for winner indicator
        won = False
        if re.search(r'\b(winner|won)\b', text, re.IGNORECASE):
            won = True

        # Remove winner indicator
        text = re.sub(r'\s*[–—-]\s*(winner|won)\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s*\((winner|won)\)\s*', '', text, flags=re.IGNORECASE)

        # Remove producer/cast names after em dash
        # Pattern: "Show Title – Producer/Cast names"
        text = re.sub(r'\s*[–—]\s*.*$', '', text)

        # Remove text in parentheses (often producer names or notes)
        # But be careful: some shows have parentheses in title like "Oh, Hello (on Broadway)"
        # Strategy: only remove if it's at the end and looks like metadata
        text = re.sub(r'\s*\([^)]*\)\s*$', '', text)

        # Clean up
        text = text.strip()

        if not text:
            return None, False

        return text, won

    def scrape_all_years(self, start_year: int = None, end_year: int = None) -> pd.DataFrame:
        """
        Scrape Tony nominations for all years in range.

        Parameters
        ----------
        start_year : int, optional
            Starting Tony year (default: from config)
        end_year : int, optional
            Ending Tony year (default: from config)

        Returns
        -------
        pd.DataFrame
            Columns: title, category, nominated, won, tony_year
        """
        if start_year is None:
            start_year = config.START_TONY_YEAR
        if end_year is None:
            end_year = config.END_TONY_YEAR

        all_records = []

        for year in range(start_year, end_year + 1):
            logger.info(f"Scraping Tony year {year}...")
            records = self._scrape_wikipedia_tony_year(year)
            all_records.extend(records)

        df = pd.DataFrame(all_records)

        if df.empty:
            logger.warning("No Tony data scraped!")
            return df

        # Add season column
        df['season'] = df['tony_year'].apply(lambda y: f"{y-1}-{y}")

        return df

    def aggregate_tony_outcomes(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate Tony nominations to show-level statistics.

        Parameters
        ----------
        df : pd.DataFrame
            Raw nominations data (from scrape_all_years)

        Returns
        -------
        pd.DataFrame
            One row per show, with columns:
            - title
            - tony_year
            - season
            - tony_nom_count
            - tony_win_count
            - tony_win_any
            - tony_major_win
        """
        if df.empty:
            return pd.DataFrame()

        # Group by title and tony_year
        grouped = df.groupby(['title', 'tony_year', 'season'], as_index=False).agg({
            'nominated': 'sum',  # Total nominations
            'won': 'sum',  # Total wins
        })

        grouped.rename(columns={
            'nominated': 'tony_nom_count',
            'won': 'tony_win_count',
        }, inplace=True)

        # tony_win_any: 1 if any wins
        grouped['tony_win_any'] = (grouped['tony_win_count'] > 0).astype(int)

        # tony_major_win: 1 if won Best Musical/Play/Revival
        major_wins = df[df['won'] & df['category'].isin(config.MAJOR_TONY_CATEGORIES)]
        major_win_shows = major_wins.groupby(['title', 'tony_year']).size().reset_index(name='major_count')
        grouped = grouped.merge(major_win_shows, on=['title', 'tony_year'], how='left')
        grouped['tony_major_win'] = (grouped['major_count'].fillna(0) > 0).astype(int)
        grouped.drop(columns=['major_count'], inplace=True)

        return grouped


def main():
    """
    Main function: scrape Tony data and save to CSV.
    """
    logger.info("Starting Tony Awards scraper...")

    scraper = TonyScraper()

    # Scrape all years
    raw_df = scraper.scrape_all_years()

    if raw_df.empty:
        logger.error("No data scraped. Exiting.")
        return

    # Save raw data
    raw_output = config.TONY_NOMINATIONS_RAW_CSV
    raw_df.to_csv(raw_output, index=False)
    logger.info(f"Saved raw Tony nominations to {raw_output}")

    # Aggregate to show level
    aggregated_df = scraper.aggregate_tony_outcomes(raw_df)

    # Save aggregated data
    aggregated_output = config.RAW_DATA_DIR / "tony_outcomes_aggregated.csv"
    aggregated_df.to_csv(aggregated_output, index=False)
    logger.info(f"Saved aggregated Tony outcomes to {aggregated_output}")

    logger.info(f"Total shows with Tony nominations: {len(aggregated_df)}")
    logger.info(f"Total nominations scraped: {len(raw_df)}")


if __name__ == "__main__":
    main()
