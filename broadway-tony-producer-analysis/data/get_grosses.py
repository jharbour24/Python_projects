"""
Weekly Broadway grosses data collector using Broadway World API.

Scrapes weekly grosses from BroadwayWorld.com's JSON endpoint.
Uses proven scraping strategy that handles server errors gracefully.

Data source: https://www.broadwayworld.com/json_grosses.cfm

Author: Broadway Analysis Pipeline (Updated with robust error handling)
"""

import os
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

import pandas as pd
import requests
from bs4 import BeautifulSoup, Tag

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import config
from utils import normalize_title, setup_logger

logger = setup_logger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_URL = "https://www.broadwayworld.com/json_grosses.cfm"
START_DATE = datetime(2000, 1, 2)  # Start from 2000 to get maximum coverage

# Broadway Theater Names & Aliases
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


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_sundays(start_date: datetime, end_date: datetime = None) -> List[str]:
    """Generate list of all Sunday dates from start_date to end_date (or today)."""
    all_dates = []
    current_date = start_date

    if end_date is None:
        end_date = datetime.today()

    while current_date.weekday() != 6:
        current_date += timedelta(days=1)

    while current_date <= end_date:
        all_dates.append(current_date.strftime("%Y-%m-%d"))
        current_date += timedelta(days=7)

    return all_dates


def clean_numeric_string(s: Optional[str]) -> Optional[float]:
    """Clean and parse numeric strings from Broadway World data."""
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


def get_canonical_theater_name(raw_name: str) -> str:
    """Map raw theater name to canonical Broadway theater name."""
    if not raw_name:
        return "Unknown"

    norm = raw_name.lower().replace('.', '').replace("'", "").strip()
    return THEATER_MAP.get(norm, raw_name)


def extract_cell_values(cell: Tag) -> Tuple[str, str]:
    """Extract 'out' and 'in' span values from a Broadway World table cell."""
    out_span = cell.find('span', class_='out')
    in_span = cell.find('span', class_='in')

    out_value = out_span.get_text(strip=True) if out_span else ""
    in_value = in_span.get_text(strip=True) if in_span else ""

    return out_value, in_value


# =============================================================================
# CORE DATA PROCESSING
# =============================================================================

def process_row(date_str: str, row_tag: Tag, show_type: str) -> Optional[Dict[str, Any]]:
    """Process a single Broadway World data row into structured format."""
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
        'Week': date_str,
        'Show': show_name,
        'Type': show_type,
        'Theater': theater_name,
        'Gross': gross,
        'Avg_Ticket': avg_ticket,
        'Top_Ticket': clean_numeric_string(top_ticket_raw),
        'Attendance': attendance,
        'Seating_Capacity': seating_capacity,
        'Performances': regular_perfs + previews,
        'Capacity_Pct': capacity_pct
    }


# =============================================================================
# BROADWAY WORLD SCRAPER
# =============================================================================

def scrape_broadway_world_grosses(start_date: datetime = START_DATE) -> pd.DataFrame:
    """
    Main scraping function with robust error handling.

    Parameters
    ----------
    start_date : datetime
        Starting date for scraping

    Returns
    -------
    pd.DataFrame
        All scraped grosses data
    """
    scraping_start_date = start_date - timedelta(days=7)
    sundays_to_scrape = get_sundays(scraping_start_date)

    if not sundays_to_scrape:
        logger.warning("No weeks to scrape.")
        return pd.DataFrame()

    logger.info(f"Found {len(sundays_to_scrape)} weeks to scrape, starting from {scraping_start_date.strftime('%Y-%m-%d')}")

    all_scraped_data: List[Dict] = []
    show_types_to_scrape = [('MUSICAL', 'M'), ('PLAY', 'P')]

    for idx, date_str in enumerate(sundays_to_scrape, 1):
        if idx % 10 == 0:
            logger.info(f"Progress: {idx}/{len(sundays_to_scrape)} weeks ({100*idx/len(sundays_to_scrape):.1f}%)")

        week_row_count = 0

        for type_param, type_code in show_types_to_scrape:
            try:
                params = {"week": date_str, "typer": type_param}
                response = requests.get(BASE_URL, params=params, timeout=20)
                response.raise_for_status()

                html_content = response.text
                if not html_content.strip():
                    continue

                soup = BeautifulSoup(html_content, 'lxml')

                for row in soup.find_all('div', class_='row'):
                    processed_data = process_row(date_str, row, type_code)
                    if processed_data:
                        all_scraped_data.append(processed_data)
                        week_row_count += 1

                time.sleep(0.01)

            except requests.exceptions.RequestException as e:
                # Log error but continue - some weeks may not have data
                if idx % 50 == 0:  # Only log every 50th error to avoid spam
                    logger.warning(f"Error fetching {type_param}s for {date_str}: {e}")
            except Exception as e:
                logger.error(f"Error processing {type_param}s for {date_str}: {e}")

        if idx % 50 == 0 and all_scraped_data:
            logger.info(f"Scraped {len(all_scraped_data)} total records so far...")

    if not all_scraped_data:
        logger.warning("No data was scraped. Check for errors above.")
        return pd.DataFrame()

    logger.info(f"Scraping complete! Total records: {len(all_scraped_data)}")

    return pd.DataFrame(all_scraped_data)


def process_grosses_data(df: pd.DataFrame) -> pd.DataFrame:
    """Process and enrich raw grosses data."""
    if df.empty:
        return df

    logger.info("Processing all scraped data...")

    df['Week'] = pd.to_datetime(df['Week'])

    # Filter unknowns
    df = df[(df['Show'] != 'Unknown') & (df['Theater'] != 'Unknown')].copy()
    logger.info(f"Filtered out 'Unknown' entries. Remaining: {len(df)} records")

    # Deduplicate
    df.sort_values(by=['Week', 'Show', 'Theater', 'Type'], inplace=True)
    df.drop_duplicates(subset=['Week', 'Show', 'Theater'], keep='first', inplace=True)
    logger.info(f"Deduplicated. Remaining: {len(df)} records")

    # Sort for time series operations
    df.sort_values(by=['Show', 'Theater', 'Week'], inplace=True)

    # Normalize capacity percentage
    df['Capacity_Pct'] = df['Capacity_Pct'] / 100.0

    # Compute week-over-week changes
    grouped = df.groupby(['Show', 'Theater'])
    df['Gross_Prev_Week'] = grouped['Gross'].shift(1)
    df['Attendance_Prev_Week'] = grouped['Attendance'].shift(1)
    df['Capacity_Pct_Prev_Week'] = grouped['Capacity_Pct'].shift(1)
    df['Gross_Diff'] = df['Gross'] - df['Gross_Prev_Week']
    df['Gross_Diff_Pct'] = df['Gross_Diff'] / df['Gross_Prev_Week']
    df['Attendance_Diff_Pct'] = (df['Attendance'] - df['Attendance_Prev_Week']) / df['Attendance_Prev_Week']
    df['Capacity_Pct_Diff'] = df['Capacity_Pct'] - df['Capacity_Pct_Prev_Week']

    # Filter to START_DATE
    logger.info(f"Filtering final data to start from {START_DATE.strftime('%Y-%m-%d')}")
    df = df[df['Week'] >= START_DATE].copy()

    # Final column order
    final_columns = [
        'Week', 'Show', 'Theater', 'Type',
        'Gross', 'Gross_Prev_Week', 'Gross_Diff', 'Gross_Diff_Pct',
        'Avg_Ticket', 'Top_Ticket',
        'Attendance', 'Attendance_Prev_Week', 'Attendance_Diff_Pct',
        'Seating_Capacity', 'Performances',
        'Capacity_Pct', 'Capacity_Pct_Prev_Week', 'Capacity_Pct_Diff'
    ]

    df = df[final_columns]
    df.sort_values(by=["Week", "Show"], inplace=True)

    logger.info("Processing complete!")

    return df


def convert_to_pipeline_format(df: pd.DataFrame) -> pd.DataFrame:
    """Convert Broadway World data to pipeline-compatible format."""
    logger.info("Converting to pipeline format...")

    df_pipeline = df.rename(columns={
        'Week': 'week_ending_date',
        'Show': 'show_title',
        'Theater': 'theatre_name',
        'Gross': 'weekly_gross',
        'Capacity_Pct': 'capacity_pct',
        'Avg_Ticket': 'avg_ticket_price',
        'Performances': 'performances',
        'Attendance': 'attendance',
        'Seating_Capacity': 'theatre_size',
        'Type': 'show_type'
    })

    df_pipeline['title_normalized'] = df_pipeline['show_title'].apply(normalize_title)

    pipeline_columns = [
        'week_ending_date', 'show_title', 'title_normalized',
        'theatre_name', 'weekly_gross', 'capacity_pct',
        'avg_ticket_price', 'performances', 'attendance',
        'theatre_size', 'show_type'
    ]

    df_pipeline = df_pipeline[[col for col in pipeline_columns if col in df_pipeline.columns]]

    logger.info(f"Converted {len(df_pipeline)} records to pipeline format")

    return df_pipeline


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main function: scrape Broadway World grosses and save to CSV."""
    logger.info("=" * 60)
    logger.info("BROADWAY WORLD GROSSES SCRAPER")
    logger.info("=" * 60)

    # Scrape data
    df_raw = scrape_broadway_world_grosses(START_DATE)

    if df_raw.empty:
        logger.error("No data scraped. Exiting.")
        return

    # Process and enrich
    df_processed = process_grosses_data(df_raw)

    # Save full Broadway World format
    bw_output = config.RAW_DATA_DIR / "broadway_world_grosses_full.csv"
    df_processed.to_csv(bw_output, index=False)
    logger.info(f"Saved full format to {bw_output}")

    # Convert to pipeline format
    df_pipeline = convert_to_pipeline_format(df_processed)

    # Save pipeline-compatible format
    pipeline_output = config.PROCESSED_DATA_DIR / "weekly_grosses_preliminary.csv"
    df_pipeline.to_csv(pipeline_output, index=False)
    logger.info(f"Saved pipeline format to {pipeline_output}")

    # Summary statistics
    logger.info("=" * 60)
    logger.info("SCRAPING SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total weekly records: {len(df_pipeline)}")
    logger.info(f"Unique shows: {df_pipeline['show_title'].nunique()}")
    logger.info(f"Date range: {df_pipeline['week_ending_date'].min()} to {df_pipeline['week_ending_date'].max()}")
    logger.info(f"Musicals: {(df_pipeline['show_type'] == 'M').sum()}")
    logger.info(f"Plays: {(df_pipeline['show_type'] == 'P').sum()}")

    # Top grossing shows
    if not df_pipeline.empty and 'weekly_gross' in df_pipeline.columns:
        top_grosses = df_pipeline.groupby('show_title')['weekly_gross'].sum().sort_values(ascending=False).head(10)
        logger.info("\nTop 10 shows by total gross:")
        for show, total in top_grosses.items():
            logger.info(f"  {show}: ${total:,.0f}")

    logger.info("\nGrosses data collection complete!")


if __name__ == "__main__":
    main()
