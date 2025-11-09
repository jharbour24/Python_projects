#!/usr/bin/env python3
"""
Broadway Grosses Scraper
Scrapes weekly box office data from BroadwayWorld.com for 2024-2025 Tony season.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import yaml
import time
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any
from tqdm import tqdm


class BroadwayGrossesScraper:
    """Scrapes Broadway box office grosses from BroadwayWorld."""

    def __init__(self):
        """Initialize scraper."""
        self.base_url = "https://www.broadwayworld.com/grosses/"
        self.data_dir = Path("data/grosses")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Load show configuration
        with open("config/config.yaml", "r") as f:
            self.config = yaml.safe_load(f)

        # User agent to avoid blocking
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        # 2024-2025 Tony season typically starts late April
        self.season_start = datetime(2024, 4, 15)
        self.season_end = datetime.now()

    def get_weekly_grosses_page(self, date: datetime) -> str:
        """Fetch the grosses page for a specific week."""
        # BroadwayWorld uses format: grosses/Week-Ending-MM-DD-YY
        date_str = date.strftime("%m-%d-%y")
        url = f"{self.base_url}Week-Ending-{date_str}"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"  ⚠️  Failed to fetch {url}: {e}")
            return None

    def parse_grosses_table(self, html: str, week_ending: datetime) -> List[Dict]:
        """Parse the grosses table from HTML."""
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        results = []

        # BroadwayWorld table structure - find the main grosses table
        # The table usually has headers: Show, Gross, Potential Gross, Diff, Avg Paid, Capacity, Perf, Prev Week
        table = soup.find('table', {'class': 'grosses-table'})

        if not table:
            # Try alternative table identification
            table = soup.find('table', string=re.compile('Gross|Theatre|Capacity'))

        if not table:
            return []

        # Find all rows
        rows = table.find_all('tr')

        for row in rows[1:]:  # Skip header row
            cols = row.find_all('td')
            if len(cols) < 5:
                continue

            try:
                # Extract show name
                show_name_elem = cols[0]
                show_name = show_name_elem.get_text(strip=True)

                # Clean up show name
                show_name = re.sub(r'\s+', ' ', show_name)

                # Extract numeric values (remove $, %, commas)
                def clean_number(text):
                    text = text.strip()
                    text = re.sub(r'[$,%]', '', text)
                    text = re.sub(r',', '', text)
                    try:
                        return float(text) if text else None
                    except ValueError:
                        return None

                # Typical column order (may vary):
                # 0: Show, 1: Gross, 2: Potential Gross, 3: Diff, 4: Avg Ticket, 5: Capacity, 6: Performances
                gross = clean_number(cols[1].get_text(strip=True)) if len(cols) > 1 else None
                capacity_pct = clean_number(cols[5].get_text(strip=True)) if len(cols) > 5 else None
                avg_ticket = clean_number(cols[4].get_text(strip=True)) if len(cols) > 4 else None
                performances = clean_number(cols[6].get_text(strip=True)) if len(cols) > 6 else None

                results.append({
                    'show_name': show_name,
                    'week_ending': week_ending.strftime('%Y-%m-%d'),
                    'gross': gross,
                    'capacity_percent': capacity_pct,
                    'avg_ticket_price': avg_ticket,
                    'performances': performances,
                    'scrape_date': datetime.now().strftime('%Y-%m-%d')
                })

            except Exception as e:
                print(f"  ⚠️  Error parsing row: {e}")
                continue

        return results

    def match_show_to_config(self, broadway_name: str) -> str:
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

    def scrape_season(self) -> pd.DataFrame:
        """Scrape entire 2024-2025 season."""
        print("\n" + "="*70)
        print("📊 SCRAPING BROADWAY GROSSES")
        print("="*70)
        print(f"\nSeason period: {self.season_start.strftime('%Y-%m-%d')} to {self.season_end.strftime('%Y-%m-%d')}")

        all_grosses = []

        # Generate all Sundays (week-ending dates) in the season
        current_date = self.season_start
        week_dates = []

        while current_date <= self.season_end:
            # Move to next Sunday
            days_until_sunday = (6 - current_date.weekday()) % 7
            sunday = current_date + timedelta(days=days_until_sunday)
            if sunday <= self.season_end:
                week_dates.append(sunday)
            current_date = sunday + timedelta(days=7)

        print(f"\n📅 Scraping {len(week_dates)} weeks of data...")
        print("⏱️  This will take several minutes (rate limiting)...\n")

        # Scrape each week
        for week_date in tqdm(week_dates, desc="Scraping weeks"):
            html = self.get_weekly_grosses_page(week_date)

            if html:
                weekly_data = self.parse_grosses_table(html, week_date)

                # Match to our shows
                for entry in weekly_data:
                    show_id = self.match_show_to_config(entry['show_name'])
                    if show_id:
                        entry['show_id'] = show_id
                        entry['config_name'] = self.config['shows'][show_id]['name']
                        entry['show_type'] = self.config['shows'][show_id].get('show_type', 'unknown')
                        all_grosses.append(entry)

            # Rate limiting - be respectful
            time.sleep(2)

        # Convert to DataFrame
        df = pd.DataFrame(all_grosses)

        if df.empty:
            print("\n⚠️  No grosses data found!")
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
    print("\nThis will scrape weekly grosses data from BroadwayWorld.com")
    print("for all shows in the 2024-2025 Tony season.\n")
    print("⚠️  Note: BroadwayWorld may change their website structure,")
    print("which could affect scraping. Manual verification recommended.\n")

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
