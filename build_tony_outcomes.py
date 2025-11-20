#!/usr/bin/env python3
"""
Build Tony Award outcomes dataset from Wikipedia.
Tries to scrape Tony winners 2010-2025 from Wikipedia.
Falls back to template if scraping fails.
"""

import re
import time
from pathlib import Path
import pandas as pd
import requests
from bs4 import BeautifulSoup
from utils import setup_logger, get_robust_session, safe_get

logger = setup_logger(__name__, log_file='logs/tony_outcomes.log')


# Tony Award years and Wikipedia URLs
TONY_YEARS = {
    2010: "64th Tony Awards",
    2011: "65th Tony Awards",
    2012: "66th Tony Awards",
    2013: "67th Tony Awards",
    2014: "68th Tony Awards",
    2015: "69th Tony Awards",
    2016: "70th Tony Awards",
    2017: "71st Tony Awards",
    2018: "72nd Tony Awards",
    2019: "73rd Tony Awards",
    2020: None,  # No ceremony due to COVID
    2021: "74th Tony Awards",
    2022: "75th Tony Awards",
    2023: "76th Tony Awards",
    2024: "77th Tony Awards",
    2025: "78th Tony Awards",  # Future
}


def scrape_tony_winners_for_year(year: int, session) -> list:
    """
    Scrape Tony Award winners for a specific year from Wikipedia.

    Args:
        year: Tony Awards year
        session: Requests session

    Returns:
        List of winner dictionaries
    """
    ceremony_name = TONY_YEARS.get(year)
    if not ceremony_name:
        logger.warning(f"No Tony ceremony for {year}")
        return []

    logger.info(f"Scraping Tony winners for {year} ({ceremony_name})...")

    # Wikipedia URL
    url = f"https://en.wikipedia.org/wiki/{ceremony_name.replace(' ', '_')}"

    try:
        response = safe_get(url, session, logger)
        if not response or response.status_code != 200:
            logger.warning(f"Failed to fetch Wikipedia page for {year}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')

        winners = []
        categories = [
            "Best Musical",
            "Best Play",
            "Best Revival of a Musical",
            "Best Revival of a Play",
            "Best Musical Revival",  # Alternative name
            "Best Play Revival",  # Alternative name
        ]

        # Wikipedia structure: Look for sections or tables with award categories
        # Strategy 1: Find tables with "Winner" columns
        tables = soup.find_all('table', class_='wikitable')

        for table in tables:
            rows = table.find_all('tr')

            for row in rows:
                cells = row.find_all(['td', 'th'])

                # Look for category in first cell, winner in subsequent cells
                if len(cells) >= 2:
                    category_text = cells[0].get_text().strip()

                    # Check if this is one of our target categories
                    for cat in categories:
                        if cat.lower() in category_text.lower():
                            # Find the winner (usually has specific styling or is first entry)
                            # Winners are often in bold or have special marking
                            winner_cell = cells[1]

                            # Look for linked show titles (Wikipedia links show titles)
                            links = winner_cell.find_all('a')
                            for link in links:
                                show_title = link.get_text().strip()
                                if show_title and len(show_title) > 1:
                                    winners.append({
                                        'show_name': show_title,
                                        'tony_year': year,
                                        'tony_category': cat,
                                        'tony_win': 1
                                    })
                                    logger.info(f"  Found winner: {show_title} ({cat})")
                                    break  # Only take first link (the show title)
                            break

        # Strategy 2: Look for "Winners and nominees" section with lists
        if not winners:
            # Find all headers
            headers = soup.find_all(['h2', 'h3'])

            for header in headers:
                header_text = header.get_text().lower()

                if 'winner' in header_text or 'awards and nominations' in header_text:
                    # Find the section after this header
                    next_sibling = header.find_next_sibling()

                    while next_sibling and next_sibling.name not in ['h2', 'h3']:
                        # Look for category mentions
                        text = next_sibling.get_text() if hasattr(next_sibling, 'get_text') else str(next_sibling)

                        for cat in categories:
                            if cat.lower() in text.lower():
                                # Find linked titles nearby
                                if hasattr(next_sibling, 'find_all'):
                                    links = next_sibling.find_all('a')
                                    for link in links:
                                        show_title = link.get_text().strip()
                                        if show_title and len(show_title) > 2:
                                            winners.append({
                                                'show_name': show_title,
                                                'tony_year': year,
                                                'tony_category': cat,
                                                'tony_win': 1
                                            })
                                            logger.info(f"  Found winner: {show_title} ({cat})")
                                            break

                        next_sibling = next_sibling.find_next_sibling()

        logger.info(f"Found {len(winners)} winners for {year}")
        return winners

    except Exception as e:
        logger.error(f"Error scraping Tony winners for {year}: {e}")
        return []


def build_tony_outcomes_dataset() -> pd.DataFrame:
    """
    Build complete Tony outcomes dataset.

    Returns:
        DataFrame with all shows and Tony outcomes
    """
    logger.info("="*70)
    logger.info("BUILDING TONY AWARD OUTCOMES DATASET")
    logger.info("="*70)

    # Load show list
    show_list_path = Path('raw/all_broadway_shows_2010_2025.csv')
    if not show_list_path.exists():
        logger.error("Show list not found!")
        return pd.DataFrame()

    shows_df = pd.read_csv(show_list_path)
    logger.info(f"Loaded {len(shows_df)} shows from show list")

    # Test Wikipedia access
    session = get_robust_session()
    test_response = safe_get("https://en.wikipedia.org/wiki/Tony_Awards", session, logger)

    if not test_response or test_response.status_code != 200:
        logger.error("Cannot access Wikipedia - will create empty template")
        shows_df['tony_win'] = None
        shows_df['tony_category'] = None
        shows_df['tony_year'] = None
        return shows_df

    logger.info("✓ Wikipedia access successful\n")

    # Scrape winners for each year
    all_winners = []

    for year in range(2010, 2026):
        logger.info(f"\n{'='*70}")
        logger.info(f"Processing {year}")
        logger.info(f"{'='*70}")

        winners = scrape_tony_winners_for_year(year, session)
        all_winners.extend(winners)

        time.sleep(2)  # Be polite to Wikipedia

    # Create winners DataFrame
    if all_winners:
        winners_df = pd.DataFrame(all_winners)
        logger.info(f"\n✓ Total winners collected: {len(winners_df)}")

        # Merge with show list
        # Normalize show names for matching
        shows_df['show_name_lower'] = shows_df['show_name'].str.lower().str.strip()
        winners_df['show_name_lower'] = winners_df['show_name'].str.lower().str.strip()

        # Merge
        result_df = shows_df.merge(
            winners_df[['show_name_lower', 'tony_win', 'tony_category', 'tony_year']],
            on='show_name_lower',
            how='left'
        )

        # Drop temp column
        result_df = result_df.drop('show_name_lower', axis=1)

        # Fill NaN tony_win with 0 (didn't win)
        result_df['tony_win'] = result_df['tony_win'].fillna(0).astype(int)

        # Count matches
        winners_matched = result_df['tony_win'].sum()
        logger.info(f"Matched {winners_matched} winners to show list")

        return result_df
    else:
        logger.warning("No winners collected - creating empty template")
        shows_df['tony_win'] = None
        shows_df['tony_category'] = None
        shows_df['tony_year'] = None
        return shows_df


def main():
    """Main entry point."""
    df = build_tony_outcomes_dataset()

    # Save results
    output_path = Path('data/tony_outcomes.csv')
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_path, index=False)
    logger.info(f"\n✓ Saved Tony outcomes to: {output_path}")

    # Display summary
    if 'tony_win' in df.columns:
        winners_count = df['tony_win'].sum() if df['tony_win'].notna().any() else 0
        logger.info(f"\nSummary:")
        logger.info(f"  Total shows: {len(df)}")
        logger.info(f"  Tony winners: {winners_count}")
        logger.info(f"  Non-winners: {len(df) - winners_count}")

        if winners_count > 0:
            logger.info(f"\nTony winners in dataset:")
            winners = df[df['tony_win'] == 1][['show_name', 'tony_category', 'tony_year']]
            logger.info(winners.to_string())

    logger.info(f"\n{'='*70}")
    logger.info("DONE")
    logger.info(f"{'='*70}")


if __name__ == '__main__':
    main()
