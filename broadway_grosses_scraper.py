#!/usr/bin/env python3
"""
Broadway grosses scraper for BroadwayWorld data (2010-present).
Scrapes weekly grosses data for all Broadway shows.
"""

import os
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

import pandas as pd
import requests
from bs4 import BeautifulSoup, Tag

# === CONFIGURATION ===
BASE_URL = "https://www.broadwayworld.com/json_grosses.cfm"
OUTPUT_FILE = "data/broadway_grosses_2010_present.xlsx"
START_DATE = datetime(2010, 1, 3)  # First Sunday of 2010

# --- Broadway Theater Names & Aliases ---
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
THEATER_MAP = {name.lower().replace('.', '').replace("'", "").strip(): name for name in BROADWAY_THEATERS}
THEATER_MAP.update(THEATER_ALIASES)


# === HELPER FUNCTIONS ===
def get_sundays(start_date: datetime) -> List[str]:
    """Generate list of all Sunday dates from start_date to today."""
    all_dates = []
    current_date = start_date
    today = datetime.today()
    while current_date.weekday() != 6:
        current_date += timedelta(days=1)
    while current_date <= today:
        all_dates.append(current_date.strftime("%Y-%m-%d"))
        current_date += timedelta(days=7)
    return all_dates

def clean_numeric_string(s: Optional[str]) -> Optional[float]:
    """Clean and convert string to float, handling currency and negatives."""
    if s is None: return None
    if isinstance(s, (int, float)): return float(s)
    s = str(s).strip()
    is_negative = s.startswith('(') and s.endswith(')') or s.startswith('-')
    s = re.sub(r'[^\d.]', '', s)
    if not s: return None
    try:
        value = float(s)
        return -value if is_negative else value
    except (ValueError, TypeError):
        return None

def get_canonical_theater_name(raw_name: str) -> str:
    """Normalize theater name to canonical version."""
    if not raw_name: return "Unknown"
    norm = raw_name.lower().replace('.', '').replace("'", "").strip()
    return THEATER_MAP.get(norm, raw_name)

def extract_cell_values(cell: Tag) -> Tuple[str, str]:
    """Extract 'out' and 'in' span values from a cell."""
    out_span = cell.find('span', class_='out')
    in_span = cell.find('span', class_='in')
    out_value = out_span.get_text(strip=True) if out_span else ""
    in_value = in_span.get_text(strip=True) if in_span else ""
    return out_value, in_value


# === CORE DATA PROCESSING LOGIC ===
def process_row(date_str: str, row_tag: Tag, show_type: str) -> Optional[Dict[str, Any]]:
    """Process a single row, calculating seating capacity if missing."""
    cells = row_tag.find_all('div', class_='cell')
    if not cells or len(cells) < 7:
        return None

    attrs = row_tag.attrs
    show_name = attrs.get('data-name') or "Unknown"
    gross = clean_numeric_string(attrs.get('data-gross'))
    attendance = clean_numeric_string(attrs.get('data-attendee'))
    capacity_pct = clean_numeric_string(attrs.get('data-capacity'))
    avg_ticket = clean_numeric_string(attrs.get('data-ticket'))

    raw_theater = cells[0].find('a', class_='theater').get_text(strip=True) if cells[0].find('a', 'theater') else ""
    theater_name = get_canonical_theater_name(raw_theater)

    # Dynamic capacity calculation
    seating_capacity = VENUE_CAPACITIES.get(theater_name)
    if seating_capacity is None and attendance and capacity_pct and capacity_pct > 0:
        estimated_capacity = attendance / (capacity_pct / 100.0)
        seating_capacity = round(estimated_capacity)

    _, top_ticket_raw = extract_cell_values(cells[4])

    regular_perfs_raw, previews_raw = "", ""
    if len(cells) > 6:
        regular_perfs_raw, previews_raw = extract_cell_values(cells[6])

    regular_perfs = int(clean_numeric_string(regular_perfs_raw) or 0)
    previews = int(clean_numeric_string(previews_raw) or 0)

    return {
        'Week': date_str, 'Show': show_name, 'Type': show_type, 'Theater': theater_name,
        'Gross': gross, 'Avg_Ticket': avg_ticket, 'Top_Ticket': clean_numeric_string(top_ticket_raw),
        'Attendance': attendance, 'Seating_Capacity': seating_capacity,
        'Performances': regular_perfs + previews, 'Capacity_Pct': capacity_pct
    }


# === MAIN SCRIPT EXECUTION ===
def main():
    """Main function to orchestrate scraping, processing, and saving."""
    print("="*70)
    print("BROADWAY GROSSES SCRAPER (2010-Present)")
    print("="*70)

    scraping_start_date = START_DATE - timedelta(days=7)
    sundays_to_scrape = get_sundays(scraping_start_date)

    if not sundays_to_scrape:
        print("No weeks to scrape. Process complete.")
        return

    print(f"\nFound {len(sundays_to_scrape)} weeks to scrape")
    print(f"Date range: {scraping_start_date.strftime('%Y-%m-%d')} to {datetime.today().strftime('%Y-%m-%d')}")

    all_scraped_data: List[Dict] = []
    show_types_to_scrape = [('MUSICAL', 'M'), ('PLAY', 'P')]

    for idx, date_str in enumerate(sundays_to_scrape):
        print(f"\r🔎 Scraping [{idx+1}/{len(sundays_to_scrape)}] {date_str}", end="", flush=True)
        week_row_count = 0

        for type_param, type_code in show_types_to_scrape:
            try:
                params = {"week": date_str, "typer": type_param}
                response = requests.get(BASE_URL, params=params, timeout=20)
                response.raise_for_status()
                html_content = response.text
                if not html_content.strip(): continue
                soup = BeautifulSoup(html_content, 'lxml')
                for row in soup.find_all('div', class_='row'):
                    processed_data = process_row(date_str, row, type_code)
                    if processed_data:
                        all_scraped_data.append(processed_data)
                        week_row_count += 1
                time.sleep(0.01)
            except requests.exceptions.RequestException as e:
                print(f"\n   -> ❌ ERROR fetching {type_param}s for {date_str}: {e}")
            except Exception as e:
                print(f"\n   -> ❌ ERROR processing {type_param}s for {date_str}: {e}")

    print(f"\n\n✓ Scraped {len(all_scraped_data)} total show-week records")

    if not all_scraped_data:
        print("\n⚠️ No data was scraped. Check for errors above.")
        return

    print("\n⚙️  Processing data with pandas...")
    df_new = pd.DataFrame(all_scraped_data)
    df_new['Week'] = pd.to_datetime(df_new['Week'])

    # Load existing data if available
    df_existing = pd.DataFrame()
    if os.path.exists(OUTPUT_FILE):
        try:
            df_existing = pd.read_excel(OUTPUT_FILE)
            if 'Week' in df_existing.columns:
                df_existing['Week'] = pd.to_datetime(df_existing['Week'])
                weeks_scraped = set(df_new['Week'])
                df_existing = df_existing[~df_existing['Week'].isin(weeks_scraped)]
                print(f"✓ Loaded {len(df_existing)} existing rows")
        except Exception as e:
            print(f"⚠️  Could not load existing file: {e}")

    df = pd.concat([df_existing, df_new], ignore_index=True)

    # Clean data
    df = df[(df['Show'] != 'Unknown') & (df['Theater'] != 'Unknown')].copy()
    df.sort_values(by=['Week', 'Show', 'Theater', 'Type'], inplace=True)
    df.drop_duplicates(subset=['Week', 'Show', 'Theater'], keep='first', inplace=True)
    df.sort_values(by=['Show', 'Theater', 'Week'], inplace=True)
    df['Capacity_Pct'] = df['Capacity_Pct'] / 100.0

    # Calculate week-over-week changes
    grouped = df.groupby(['Show', 'Theater'])
    df['Gross_Prev_Week'] = grouped['Gross'].shift(1)
    df['Attendance_Prev_Week'] = grouped['Attendance'].shift(1)
    df['Capacity_Pct_Prev_Week'] = grouped['Capacity_Pct'].shift(1)
    df['Gross_Diff'] = df['Gross'] - df['Gross_Prev_Week']
    df['Gross_Diff_Pct'] = df['Gross_Diff'] / df['Gross_Prev_Week']
    df['Attendance_Diff_Pct'] = (df['Attendance'] - df['Attendance_Prev_Week']) / df['Attendance_Prev_Week']
    df['Capacity_Pct_Diff'] = df['Capacity_Pct'] - df['Capacity_Pct_Prev_Week']

    # Filter to start date
    df = df[df['Week'] >= START_DATE].copy()

    # Reorder columns
    final_columns = [
        'Week', 'Show', 'Theater', 'Gross', 'Gross_Prev_Week', 'Gross_Diff', 'Gross_Diff_Pct',
        'Avg_Ticket', 'Top_Ticket', 'Attendance', 'Attendance_Prev_Week', 'Attendance_Diff_Pct',
        'Seating_Capacity', 'Performances', 'Capacity_Pct', 'Capacity_Pct_Prev_Week', 'Capacity_Pct_Diff', 'Type'
    ]
    df = df[final_columns]
    df.sort_values(by=["Week", "Show"], inplace=True)

    print(f"💾 Saving {len(df)} rows to {OUTPUT_FILE}...")

    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)

    try:
        with pd.ExcelWriter(OUTPUT_FILE, engine='xlsxwriter', datetime_format='YYYY-MM-DD') as writer:
            df.to_excel(writer, index=False, sheet_name='Broadway Grosses')
            workbook  = writer.book
            worksheet = writer.sheets['Broadway Grosses']

            # Format columns
            money_format = workbook.add_format({'num_format': '$#,##0'})
            money_format_cents = workbook.add_format({'num_format': '$#,##0.00'})
            percent_format = workbook.add_format({'num_format': '0.00%'})
            integer_format = workbook.add_format({'num_format': '#,##0'})
            center_format = workbook.add_format({'align': 'center'})

            worksheet.set_column('A:A', 12)
            worksheet.set_column('B:C', 25)
            worksheet.set_column('D:F', 14, money_format)
            worksheet.set_column('G:G', 12, percent_format)
            worksheet.set_column('H:I', 12, money_format_cents)
            worksheet.set_column('J:K', 14, integer_format)
            worksheet.set_column('L:L', 12, percent_format)
            worksheet.set_column('M:N', 20, integer_format)
            worksheet.set_column('O:Q', 12, percent_format)
            worksheet.set_column('R:R', 6, center_format)

        print(f"\n🎉 Success! Data saved to {OUTPUT_FILE}")
        print(f"\n📊 Summary:")
        print(f"   Total shows: {df['Show'].nunique()}")
        print(f"   Date range: {df['Week'].min().strftime('%Y-%m-%d')} to {df['Week'].max().strftime('%Y-%m-%d')}")
        print(f"   Total weeks: {df['Week'].nunique()}")

    except Exception as e:
        print(f"\n❌ ERROR: Could not save Excel file: {e}")
        print(f"   You may need to install: pip install xlsxwriter openpyxl")

    print("\n✓ Scraping process complete")


if __name__ == '__main__':
    main()
