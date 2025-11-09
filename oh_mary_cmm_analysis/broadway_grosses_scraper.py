#!/usr/bin/env python3
"""
Broadway Grosses Scraper
Scrapes weekly box office data from BroadwayWorld.com JSON API for 2024-2025 Tony season.
Uses the json_grosses.cfm endpoint which is more reliable than HTML scraping.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import yaml
import time
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from tqdm import tqdm


class BroadwayGrossesScraper:
    """Scrapes Broadway box office grosses from BroadwayWorld JSON API."""

    def __init__(self):
        """Initialize scraper."""
        # Use JSON API endpoint instead of HTML pages
        self.base_url = "https://www.broadwayworld.com/json_grosses.cfm"
        self.data_dir = Path("data/grosses")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Load show configuration
        with open("config/config.yaml", "r") as f:
            self.config = yaml.safe_load(f)

        # Simple headers for API requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        # 2024-2025 Tony season starts late April
        self.season_start = datetime(2024, 4, 15)
        self.season_end = datetime.now()

    def clean_numeric_string(self, s: Optional[str]) -> Optional[float]:
        """Clean numeric strings (remove $, %, commas, handle negatives)."""
        if s is None:
            return None
        if isinstance(s, (int, float)):
            return float(s)

        s = str(s).strip()
        is_negative = (s.startswith('(') and s.endswith(')')) or s.startswith('-')
        s = re.sub(r'[^\d.]', '', s)

        if not s:
            return None

        try:
            value = float(s)
            return -value if is_negative else value
        except (ValueError, TypeError):
            return None

    def get_weekly_grosses(self, date: datetime, show_type: str) -> List[Dict]:
        """
        Fetch grosses for a specific week and show type from JSON API.

        Args:
            date: Week ending date (Sunday)
            show_type: 'MUSICAL' or 'PLAY'

        Returns:
            List of show dictionaries with grosses data
        """
        date_str = date.strftime("%Y-%m-%d")
        params = {
            "week": date_str,
            "typer": show_type
        }

        try:
            response = self.session.get(self.base_url, params=params, timeout=20)
            response.raise_for_status()
            html_content = response.text

            if not html_content.strip():
                return []

            # Parse the HTML response (it's HTML fragments in the JSON response)
            soup = BeautifulSoup(html_content, 'lxml')
            results = []

            # Each show is a div with class 'row' containing data attributes
            for row in soup.find_all('div', class_='row'):
                show_data = self.parse_row(row, date_str)
                if show_data:
                    show_data['show_type_raw'] = 'M' if show_type == 'MUSICAL' else 'P'
                    results.append(show_data)

            return results

        except requests.exceptions.RequestException as e:
            # Silently continue for most errors
            return []
        except Exception as e:
            # Log unexpected errors but continue
            print(f"  ⚠️  Error processing {show_type}s for {date_str}: {e}")
            return []

    def parse_row(self, row_tag, date_str: str) -> Optional[Dict[str, Any]]:
        """Parse a single row from the BroadwayWorld JSON response."""
        try:
            attrs = row_tag.attrs
            cells = row_tag.find_all('div', class_='cell')

            if not cells or len(cells) < 7:
                return None

            # Extract data from attributes
            show_name = attrs.get('data-name', 'Unknown')
            gross = self.clean_numeric_string(attrs.get('data-gross'))
            attendance = self.clean_numeric_string(attrs.get('data-attendee'))
            capacity_pct = self.clean_numeric_string(attrs.get('data-capacity'))
            avg_ticket = self.clean_numeric_string(attrs.get('data-ticket'))

            # Extract theater name from first cell
            theater_elem = cells[0].find('a', class_='theater')
            theater_name = theater_elem.get_text(strip=True) if theater_elem else "Unknown"

            # Extract performances from 7th cell
            regular_perfs_raw = ""
            previews_raw = ""
            if len(cells) > 6:
                out_span = cells[6].find('span', class_='out')
                in_span = cells[6].find('span', class_='in')
                regular_perfs_raw = out_span.get_text(strip=True) if out_span else ""
                previews_raw = in_span.get_text(strip=True) if in_span else ""

            regular_perfs = int(self.clean_numeric_string(regular_perfs_raw) or 0)
            previews = int(self.clean_numeric_string(previews_raw) or 0)
            total_perfs = regular_perfs + previews

            return {
                'show_name': show_name,
                'theater': theater_name,
                'week_ending': date_str,
                'gross': gross,
                'avg_ticket_price': avg_ticket,
                'attendance': attendance,
                'capacity_percent': capacity_pct,
                'performances': total_perfs,
                'scrape_date': datetime.now().strftime('%Y-%m-%d')
            }

        except Exception as e:
            return None

    def match_show_to_config(self, broadway_name: str) -> Optional[str]:
        """Match Broadway World show name to our config shows."""
        broadway_name_lower = broadway_name.lower()

        # Try exact matches first
        for show_id, show_info in self.config['shows'].items():
            config_name = show_info['name'].lower()
            if config_name in broadway_name_lower or broadway_name_lower in config_name:
                return show_id

        # Try keyword matching
        for show_id, show_info in self.config['shows'].items():
            for keyword in show_info.get('keywords', []):
                if keyword.lower() in broadway_name_lower:
                    return show_id

        return None

    def get_sundays(self, start_date: datetime) -> List[datetime]:
        """Generate list of all Sundays from start_date to today."""
        sundays = []
        current_date = start_date

        # Move to first Sunday
        while current_date.weekday() != 6:  # 6 = Sunday
            current_date += timedelta(days=1)

        # Collect all Sundays until today
        while current_date <= self.season_end:
            sundays.append(current_date)
            current_date += timedelta(days=7)

        return sundays

    def scrape_season(self) -> pd.DataFrame:
        """Scrape entire 2024-2025 season using JSON API."""
        print("\n" + "="*70)
        print("📊 SCRAPING BROADWAY GROSSES (JSON API)")
        print("="*70)
        print(f"\nSeason period: {self.season_start.strftime('%Y-%m-%d')} to {self.season_end.strftime('%Y-%m-%d')}")

        all_grosses = []
        sundays = self.get_sundays(self.season_start)

        print(f"\n📅 Scraping {len(sundays)} weeks of data...")
        print("⏱️  This will take several minutes (rate limiting)...\n")

        # Track success/failure
        successful_fetches = 0
        failed_fetches = 0

        # Scrape each week for both musicals and plays
        for week_date in tqdm(sundays, desc="Scraping weeks"):
            week_data = []

            # Fetch musicals
            musicals = self.get_weekly_grosses(week_date, 'MUSICAL')
            week_data.extend(musicals)

            # Small delay between requests
            time.sleep(0.1)

            # Fetch plays
            plays = self.get_weekly_grosses(week_date, 'PLAY')
            week_data.extend(plays)

            if week_data:
                successful_fetches += 1

                # Match shows to our config
                for entry in week_data:
                    show_id = self.match_show_to_config(entry['show_name'])
                    if show_id:
                        entry['show_id'] = show_id
                        entry['config_name'] = self.config['shows'][show_id]['name']
                        entry['show_type'] = self.config['shows'][show_id].get('show_type', 'unknown')
                        all_grosses.append(entry)
            else:
                failed_fetches += 1

            # Rate limiting - be respectful
            time.sleep(0.5)

        # Diagnostic info
        print(f"\n📊 Fetch Results: {successful_fetches} successful, {failed_fetches} failed")

        # Convert to DataFrame
        df = pd.DataFrame(all_grosses)

        if df.empty:
            print("\n⚠️  No grosses data found!")
            print("\nPossible issues:")
            print("  1. API endpoint may have changed")
            print("  2. Network connectivity issues")
            print("  3. Show names in config don't match BroadwayWorld names")
            return df

        print(f"\n✅ Scraped {len(df)} records for {df['show_id'].nunique()} shows")

        # Save raw data
        output_path = self.data_dir / "broadway_grosses_2024_2025.csv"
        df.to_csv(output_path, index=False)
        print(f"💾 Saved: {output_path}")

        # Generate summary by show
        self.generate_summary(df)

        return df

    def generate_summary(self, df: pd.DataFrame):
        """Generate summary statistics by show."""
        if df.empty:
            return

        print("\n" + "="*70)
        print("📈 GROSSES SUMMARY BY SHOW")
        print("="*70)

        summary = df.groupby('show_id').agg({
            'gross': ['sum', 'mean', 'max'],
            'capacity_percent': 'mean',
            'avg_ticket_price': 'mean',
            'week_ending': 'count'
        }).round(2)

        summary.columns = ['Total Gross', 'Avg Weekly Gross', 'Peak Gross',
                          'Avg Capacity %', 'Avg Ticket $', 'Weeks Tracked']

        # Add show names
        summary['Show Name'] = summary.index.map(
            lambda x: self.config['shows'][x]['name']
        )

        # Reorder columns
        summary = summary[['Show Name', 'Weeks Tracked', 'Total Gross',
                          'Avg Weekly Gross', 'Peak Gross', 'Avg Capacity %', 'Avg Ticket $']]

        # Sort by total gross
        summary = summary.sort_values('Total Gross', ascending=False)

        print("\n" + summary.to_string())

        # Save summary
        summary_path = self.data_dir / "grosses_summary.csv"
        summary.to_csv(summary_path)
        print(f"\n💾 Saved: {summary_path}")


def main():
    """Main execution."""
    print("\n🎭 BROADWAY BOX OFFICE GROSSES SCRAPER")
    print("=" * 70)
    print("\nThis will scrape weekly grosses data from BroadwayWorld.com JSON API")
    print("for all shows in the 2024-2025 Tony season.\n")

    scraper = BroadwayGrossesScraper()
    df = scraper.scrape_season()

    print("\n" + "="*70)
    print("✅ SCRAPING COMPLETE")
    print("="*70)
    print("\n📁 Data saved to:")
    print("  • data/grosses/broadway_grosses_2024_2025.csv - Raw weekly data")
    print("  • data/grosses/grosses_summary.csv - Summary by show")


if __name__ == "__main__":
    main()
