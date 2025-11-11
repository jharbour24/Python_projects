"""
BroadwayWorld grosses scraper for Broadway shows.
Uses BroadwayWorld JSON API for reliable weekly box office data.
Based on proven scraping strategy with dynamic capacity calculation.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import re
from .base import BaseScraper


# Broadway Theater canonical names and aliases
BROADWAY_THEATERS = [
    "Al Hirschfeld", "Ambassador", "American Airlines", "August Wilson", "Barrymore", "Belasco",
    "Bernard B. Jacobs", "Booth", "Broadhurst", "Broadway", "Brooks Atkinson", "Circle in the Square",
    "Ethel Barrymore", "Eugene O'Neill", "Gerald Schoenfeld", "Gershwin", "Golden", "Helen Hayes",
    "Hudson", "Imperial", "James Earl Jones", "John Golden", "Lena Horne", "Longacre", "Lunt-Fontanne",
    "Lyceum", "Lyric", "Majestic", "Marquis", "Minskoff", "Music Box", "Nederlander", "New Amsterdam",
    "Neil Simon", "Palace", "Richard Rodgers", "Samuel J. Friedman", "Shubert", "St. James",
    "Stephen Sondheim", "Studio 54", "Vivian Beaumont", "Walter Kerr", "Winter Garden"
]

THEATER_ALIASES = {
    'martin beck': 'Al Hirschfeld', 'ford center': 'Lyric', 'hilton': 'Lyric', 'foxwoods': 'Lyric',
    'cort': 'James Earl Jones', 'royale': 'Bernard B. Jacobs', 'plymouth': 'Gerald Schoenfeld',
    'virginia': 'August Wilson', 'todd haimes': 'American Airlines', 'jacobs': 'Bernard B. Jacobs',
    'schoenfeld': 'Gerald Schoenfeld', 'hayes': 'Helen Hayes', 'rodgers': 'Richard Rodgers',
    'friedman': 'Samuel J. Friedman', 'sondheim': 'Stephen Sondheim',
}

VENUE_CAPACITIES = {
    "Al Hirschfeld": 1424, "Ambassador": 1120, "American Airlines": 740, "August Wilson": 1222,
    "Barrymore": 1096, "Belasco": 1018, "Bernard B. Jacobs": 1078, "Booth": 782, "Broadhurst": 1186,
    "Broadway": 1761, "Brooks Atkinson": 1069, "Circle in the Square": 776, "Ethel Barrymore": 1094,
    "Eugene O'Neill": 1108, "Gerald Schoenfeld": 1079, "Gershwin": 1933, "Golden": 804, "Helen Hayes": 597,
    "Hudson": 970, "Imperial": 1443, "James Earl Jones": 1096, "John Golden": 804, "Lena Horne": 1096,
    "Longacre": 1091, "Lunt-Fontanne": 1509, "Lyceum": 922, "Lyric": 1622, "Majestic": 1645,
    "Marquis": 1612, "Minskoff": 1621, "Music Box": 1009, "Nederlander": 1232, "New Amsterdam": 1702,
    "Neil Simon": 1444, "Palace": 1610, "Richard Rodgers": 1380, "Samuel J. Friedman": 650,
    "Shubert": 1468, "St. James": 1710, "Stephen Sondheim": 1055, "Studio 54": 1006,
    "Vivian Beaumont": 1080, "Walter Kerr": 945, "Winter Garden": 1526
}


class BroadwayWorldGrossesScraper(BaseScraper):
    """Scraper for BroadwayWorld weekly grosses data using JSON API."""

    def __init__(self, cache_dir: Path, rate_limit: float = 1.0):
        super().__init__(cache_dir, rate_limit=rate_limit)

        # Build theater name mapping
        self.theater_map = {name.lower().replace('.', '').replace("'", "").strip(): name
                           for name in BROADWAY_THEATERS}
        self.theater_map.update(THEATER_ALIASES)

        self.base_url = "https://www.broadwayworld.com/json_grosses.cfm"

    def scrape_show_grosses(
        self,
        show_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Scrape weekly grosses data for a specific Broadway show.

        Uses BroadwayWorld JSON API to get complete historical data.

        Args:
            show_name: Name of the Broadway show
            start_date: Start date (default: 1 year ago)
            end_date: End date (default: today)

        Returns:
            DataFrame with columns: week_ending, show_name, theater, gross, attendance, capacity_pct, etc.
        """
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=365)

        # Get all Sunday dates in range
        sundays = self._get_sundays(start_date, end_date)

        print(f"Fetching grosses for '{show_name}' across {len(sundays)} weeks...")

        all_data = []

        for week_ending in sundays:
            week_data = self.scrape_weekly_grosses(week_ending)

            # Filter for this show
            if not week_data.empty:
                show_data = week_data[
                    week_data["show_name"].str.contains(show_name, case=False, na=False)
                ]
                if not show_data.empty:
                    all_data.append(show_data)

        if not all_data:
            print(f"No grosses data found for '{show_name}'")
            return self._empty_grosses_df()

        df = pd.concat(all_data, ignore_index=True)
        df = df.sort_values("week_ending").reset_index(drop=True)

        return df

    def scrape_weekly_grosses(self, week_ending: datetime) -> pd.DataFrame:
        """
        Scrape grosses for ALL shows for a specific week using JSON API.

        Args:
            week_ending: Date of week ending (typically Sunday)

        Returns:
            DataFrame with all shows' grosses for that week
        """
        date_str = week_ending.strftime("%Y-%m-%d")

        all_rows = []

        # Fetch both musicals and plays
        for show_type, type_code in [("MUSICAL", "M"), ("PLAY", "P")]:
            data = self._fetch_week_type(date_str, show_type, type_code)
            all_rows.extend(data)

        if not all_rows:
            return self._empty_grosses_df()

        df = pd.DataFrame(all_rows)
        return df

    def _fetch_week_type(
        self, date_str: str, type_param: str, type_code: str
    ) -> List[Dict]:
        """
        Fetch grosses for a specific week and show type (MUSICAL or PLAY).

        Args:
            date_str: Week ending date (YYYY-MM-DD)
            type_param: "MUSICAL" or "PLAY"
            type_code: "M" or "P"

        Returns:
            List of row dictionaries
        """
        cache_key = f"bw_json_{date_str}_{type_param}"

        # Fetch JSON from BroadwayWorld API
        url = f"{self.base_url}?week={date_str}&typer={type_param}"

        html = self.fetch_url(url, cache_key=cache_key)

        if not html or not html.strip():
            return []

        # Parse HTML (BroadwayWorld returns HTML, not JSON despite the endpoint name)
        soup = self.parse_html(html)
        if not soup:
            return []

        rows = []

        # Find all row divs with data attributes
        for row_div in soup.find_all("div", class_="row"):
            row_data = self._process_row(date_str, row_div, type_code)
            if row_data:
                rows.append(row_data)

        return rows

    def _process_row(
        self, date_str: str, row_tag, show_type: str
    ) -> Optional[Dict]:
        """
        Process a single row from BroadwayWorld JSON endpoint.

        Includes dynamic capacity calculation if capacity data is missing.

        Args:
            date_str: Week ending date string
            row_tag: BeautifulSoup Tag for the row
            show_type: "M" (musical) or "P" (play)

        Returns:
            Dict with grosses data or None
        """
        cells = row_tag.find_all("div", class_="cell")
        if not cells or len(cells) < 7:
            return None

        attrs = row_tag.attrs

        # Extract data from attributes
        show_name = attrs.get("data-name") or "Unknown"
        gross = self._clean_numeric(attrs.get("data-gross"))
        attendance = self._clean_numeric(attrs.get("data-attendee"))
        capacity_pct = self._clean_numeric(attrs.get("data-capacity"))
        avg_ticket = self._clean_numeric(attrs.get("data-ticket"))

        # Extract theater name from first cell
        theater_link = cells[0].find("a", class_="theater")
        raw_theater = theater_link.get_text(strip=True) if theater_link else ""
        theater_name = self._get_canonical_theater_name(raw_theater)

        # Dynamic capacity calculation
        seating_capacity = VENUE_CAPACITIES.get(theater_name)

        # If capacity not in our list, calculate from this week's data
        if seating_capacity is None and attendance and capacity_pct and capacity_pct > 0:
            estimated_capacity = attendance / (capacity_pct / 100.0)
            seating_capacity = round(estimated_capacity)

        # Extract top ticket price
        top_ticket = None
        if len(cells) > 4:
            top_ticket = self._clean_numeric(
                self._extract_cell_value(cells[4], span_class="in")
            )

        # Extract performances (regular + previews)
        regular_perfs = 0
        previews = 0
        if len(cells) > 6:
            regular_perfs = int(
                self._clean_numeric(
                    self._extract_cell_value(cells[6], span_class="out")
                )
                or 0
            )
            previews = int(
                self._clean_numeric(self._extract_cell_value(cells[6], span_class="in"))
                or 0
            )

        return {
            "week_ending": datetime.strptime(date_str, "%Y-%m-%d"),
            "show_name": show_name,
            "show_type": show_type,
            "theater": theater_name,
            "gross": gross,
            "avg_ticket": avg_ticket,
            "top_ticket": top_ticket,
            "attendance": attendance,
            "seating_capacity": seating_capacity,
            "num_perfs": regular_perfs,
            "num_previews": previews,
            "capacity_pct": capacity_pct,
        }

    def _extract_cell_value(self, cell, span_class: str) -> str:
        """Extract value from cell span with specific class."""
        span = cell.find("span", class_=span_class)
        return span.get_text(strip=True) if span else ""

    def _clean_numeric(self, value) -> Optional[float]:
        """Clean numeric string to float, handling currency, percentages, negatives."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)

        s = str(value).strip()
        is_negative = s.startswith("(") and s.endswith(")") or s.startswith("-")

        # Remove all non-digit/non-decimal characters
        s = re.sub(r"[^\d.]", "", s)

        if not s:
            return None

        try:
            num = float(s)
            return -num if is_negative else num
        except (ValueError, TypeError):
            return None

    def _get_canonical_theater_name(self, raw_name: str) -> str:
        """Map theater name to canonical form using aliases."""
        if not raw_name:
            return "Unknown"

        norm = raw_name.lower().replace(".", "").replace("'", "").strip()
        return self.theater_map.get(norm, raw_name)

    def _get_sundays(
        self, start_date: datetime, end_date: datetime
    ) -> List[datetime]:
        """Generate list of Sunday dates between start and end."""
        sundays = []

        # Move to first Sunday
        current = start_date
        while current.weekday() != 6:  # 6 = Sunday
            current += timedelta(days=1)

        # Collect all Sundays
        while current <= end_date:
            sundays.append(current)
            current += timedelta(days=7)

        return sundays

    def _empty_grosses_df(self) -> pd.DataFrame:
        """Return empty DataFrame with expected columns."""
        return pd.DataFrame(
            columns=[
                "week_ending",
                "show_name",
                "show_type",
                "theater",
                "gross",
                "avg_ticket",
                "top_ticket",
                "attendance",
                "seating_capacity",
                "num_perfs",
                "num_previews",
                "capacity_pct",
            ]
        )


def scrape_broadwayworld_grosses(
    show_name: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    cache_dir: Path = Path("data/raw/grosses"),
) -> pd.DataFrame:
    """
    Convenience function to scrape BroadwayWorld grosses using JSON API.

    Args:
        show_name: Name of Broadway show
        start_date: Start date (default: 1 year ago)
        end_date: End date (default: today)
        cache_dir: Cache directory

    Returns:
        DataFrame with weekly grosses data
    """
    scraper = BroadwayWorldGrossesScraper(cache_dir=cache_dir)
    return scraper.scrape_show_grosses(show_name, start_date, end_date)
