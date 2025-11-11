"""
BroadwayWorld grosses scraper for Broadway shows.
Scrapes weekly box office data from public BroadwayWorld pages.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import re
from .base import BaseScraper


class BroadwayWorldGrossesScraper(BaseScraper):
    """Scraper for BroadwayWorld weekly grosses data."""

    def __init__(self, cache_dir: Path, rate_limit: float = 1.0):
        super().__init__(cache_dir, rate_limit=rate_limit)

    def scrape_show_grosses(self, show_name: str) -> pd.DataFrame:
        """
        Scrape weekly grosses data for a Broadway show.

        BroadwayWorld publishes weekly grosses tables. This scraper attempts
        to find and parse grosses data for the specified show.

        Args:
            show_name: Name of the Broadway show

        Returns:
            DataFrame with columns: week_ending, gross, attendance, capacity_pct, num_previews, num_perfs
        """
        # Try different URL patterns
        show_slug = self._normalize_show_name(show_name)

        # BroadwayWorld grosses are typically at:
        # /grosses/YEAR/SHOW-NAME/ or in weekly grosses articles
        # For now, we'll scrape from the weekly grosses archive page

        grosses_data = []

        # Try to get recent grosses from main grosses page
        url = "https://www.broadwayworld.com/grosses/"
        html = self.fetch_url(url, cache_key=f"bw_grosses_main")

        if html:
            soup = self.parse_html(html)
            if soup:
                grosses = self._extract_show_from_weekly_table(soup, show_name)
                grosses_data.extend(grosses)

        if not grosses_data:
            print(
                f"Warning: Could not find grosses data for '{show_name}' on BroadwayWorld. "
                f"Show may not be currently running or data not publicly available."
            )
            return self._empty_grosses_df()

        df = pd.DataFrame(grosses_data)

        # Convert week_ending to datetime
        if "week_ending" in df.columns:
            df["week_ending"] = pd.to_datetime(df["week_ending"], errors="coerce")

        # Sort by date
        if not df.empty:
            df = df.sort_values("week_ending")

        return df

    def scrape_weekly_grosses(self, week_ending: datetime) -> pd.DataFrame:
        """
        Scrape grosses for all shows for a specific week.

        Args:
            week_ending: Date of week ending (typically Sunday)

        Returns:
            DataFrame with all shows' grosses for that week
        """
        # BroadwayWorld weekly grosses URLs follow pattern:
        # /grosses/BY-WEEK/YYYY-MM-DD/
        date_str = week_ending.strftime("%Y-%m-%d")
        url = f"https://www.broadwayworld.com/grosses/BY-WEEK/{date_str}/"

        cache_key = f"bw_grosses_week_{date_str}"
        html = self.fetch_url(url, cache_key=cache_key)

        if not html:
            print(f"Warning: Could not fetch grosses for week ending {date_str}")
            return self._empty_grosses_df()

        soup = self.parse_html(html)
        if not soup:
            return self._empty_grosses_df()

        # Parse the grosses table
        grosses = self._parse_weekly_grosses_table(soup, week_ending)

        if not grosses:
            return self._empty_grosses_df()

        return pd.DataFrame(grosses)

    def _extract_show_from_weekly_table(
        self, soup, show_name: str
    ) -> List[Dict]:
        """
        Extract a specific show's data from the weekly grosses table.

        Args:
            soup: BeautifulSoup object
            show_name: Show name to search for

        Returns:
            List of grosses records
        """
        grosses = []

        # BroadwayWorld uses tables with class 'grosses-table' or similar
        tables = soup.find_all("table")

        for table in tables:
            rows = table.find_all("tr")

            for row in rows:
                cells = row.find_all(["td", "th"])
                if len(cells) < 4:
                    continue

                # Look for show name in first cell
                show_cell = cells[0].get_text(strip=True)

                if self._show_name_matches(show_cell, show_name):
                    # Parse grosses data from this row
                    gross_data = self._parse_grosses_row(cells)
                    if gross_data:
                        grosses.append(gross_data)

        return grosses

    def _parse_weekly_grosses_table(
        self, soup, week_ending: datetime
    ) -> List[Dict]:
        """
        Parse the weekly grosses table from BroadwayWorld.

        Args:
            soup: BeautifulSoup object
            week_ending: Week ending date

        Returns:
            List of grosses records for all shows
        """
        grosses = []

        tables = soup.find_all("table")

        for table in tables:
            rows = table.find_all("tr")

            for row in rows[1:]:  # Skip header
                cells = row.find_all(["td", "th"])
                if len(cells) < 4:
                    continue

                gross_data = self._parse_grosses_row(cells)
                if gross_data:
                    gross_data["week_ending"] = week_ending
                    grosses.append(gross_data)

        return grosses

    def _parse_grosses_row(self, cells: List) -> Optional[Dict]:
        """
        Parse a single row of grosses data.

        Typical format:
        Show | Gross | Attendance | Capacity | Previews | Performances

        Args:
            cells: List of table cells

        Returns:
            Dict with grosses data or None if parsing fails
        """
        try:
            show_name = cells[0].get_text(strip=True)

            # Parse gross (remove $, commas)
            gross_text = cells[1].get_text(strip=True) if len(cells) > 1 else "0"
            gross = self._parse_currency(gross_text)

            # Parse attendance (remove commas)
            attendance_text = cells[2].get_text(strip=True) if len(cells) > 2 else "0"
            attendance = self._parse_number(attendance_text)

            # Parse capacity percentage
            capacity_text = cells[3].get_text(strip=True) if len(cells) > 3 else "0%"
            capacity_pct = self._parse_percentage(capacity_text)

            # Parse preview/performance counts
            num_previews = 0
            num_perfs = 0

            if len(cells) > 4:
                preview_text = cells[4].get_text(strip=True)
                num_previews = self._parse_number(preview_text)

            if len(cells) > 5:
                perf_text = cells[5].get_text(strip=True)
                num_perfs = self._parse_number(perf_text)

            return {
                "show_name": show_name,
                "gross": gross,
                "attendance": attendance,
                "capacity_pct": capacity_pct,
                "num_previews": num_previews,
                "num_perfs": num_perfs,
            }

        except (ValueError, IndexError):
            return None

    def _parse_currency(self, text: str) -> float:
        """Parse currency string to float."""
        # Remove $, commas, and convert to float
        cleaned = re.sub(r'[$,]', '', text)
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def _parse_number(self, text: str) -> int:
        """Parse number string to int."""
        cleaned = re.sub(r'[,]', '', text)
        try:
            return int(cleaned)
        except ValueError:
            return 0

    def _parse_percentage(self, text: str) -> float:
        """Parse percentage string to float."""
        cleaned = re.sub(r'[%]', '', text)
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def _show_name_matches(self, table_name: str, target_name: str) -> bool:
        """Check if show names match (case-insensitive, fuzzy)."""
        table_name_clean = table_name.lower().strip()
        target_name_clean = target_name.lower().strip()

        # Exact match
        if table_name_clean == target_name_clean:
            return True

        # Partial match
        if target_name_clean in table_name_clean or table_name_clean in target_name_clean:
            return True

        return False

    def _normalize_show_name(self, show_name: str) -> str:
        """Normalize show name for URL slugs."""
        # Convert to lowercase, replace spaces with hyphens
        slug = show_name.lower()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'[\s]+', '-', slug)
        return slug

    def _empty_grosses_df(self) -> pd.DataFrame:
        """Return empty DataFrame with expected columns."""
        return pd.DataFrame(
            columns=[
                "show_name",
                "week_ending",
                "gross",
                "attendance",
                "capacity_pct",
                "num_previews",
                "num_perfs",
            ]
        )


def scrape_broadwayworld_grosses(
    show_name: str,
    cache_dir: Path = Path("data/raw/grosses"),
) -> pd.DataFrame:
    """
    Convenience function to scrape BroadwayWorld grosses.

    Args:
        show_name: Name of Broadway show
        cache_dir: Cache directory

    Returns:
        DataFrame with weekly grosses data
    """
    scraper = BroadwayWorldGrossesScraper(cache_dir=cache_dir)
    return scraper.scrape_show_grosses(show_name)
