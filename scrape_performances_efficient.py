#!/usr/bin/env python3
"""
Efficient IBDB performance scraper using direct HTTP requests.
Similar approach to broadway_grosses_scraper.py but for IBDB data.
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import revivals dictionary
from REVIVALS_DICTIONARY import BROADWAY_REVIVALS


def search_google_for_ibdb(show_name):
    """Search Google for IBDB link to show."""
    try:
        # Construct search query
        query = f"{show_name} IBDB Broadway revival 2010..2025"

        # Google search URL (using a simple approach)
        search_url = "https://www.google.com/search"
        params = {
            'q': query,
            'num': 10
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        response = requests.get(search_url, params=params, headers=headers, timeout=10)

        if response.status_code != 200:
            logger.warning(f"Google search failed with status {response.status_code}")
            return None

        # Parse search results for IBDB link
        soup = BeautifulSoup(response.text, 'html.parser')

        # Look for IBDB links in search results
        for link in soup.find_all('a', href=True):
            href = link['href']
            if 'ibdb.com/broadway-production/' in href:
                # Extract actual URL from Google's redirect
                if 'url?q=' in href:
                    ibdb_url = href.split('url?q=')[1].split('&')[0]
                else:
                    ibdb_url = href

                # Clean up URL
                ibdb_url = ibdb_url.split('&')[0]

                if ibdb_url.startswith('http'):
                    logger.info(f"  Found IBDB URL: {ibdb_url}")
                    return ibdb_url

        logger.warning(f"  No IBDB link found in search results")
        return None

    except Exception as e:
        logger.error(f"  Error searching Google: {e}")
        return None


def fetch_ibdb_data(ibdb_url):
    """Fetch IBDB page and extract performance data."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        response = requests.get(ibdb_url, headers=headers, timeout=10)

        if response.status_code != 200:
            logger.warning(f"  IBDB page failed with status {response.status_code}")
            return None, None

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        page_text = soup.get_text()

        # Extract production year
        production_year = None
        year_match = re.search(r'Opening Night:\s*\w+\s+\d+,\s+(\d{4})', page_text, re.IGNORECASE)
        if year_match:
            production_year = int(year_match.group(1))

        # Extract number of performances
        num_performances = None
        perf_match = re.search(r'Performances:\s*(\d+)', page_text, re.IGNORECASE)
        if perf_match:
            num_performances = int(perf_match.group(1))

        return production_year, num_performances

    except Exception as e:
        logger.error(f"  Error fetching IBDB page: {e}")
        return None, None


def scrape_show(show_id, show_name):
    """Scrape performance data for a single show."""
    logger.info(f"\n{'='*70}")
    logger.info(f"[{show_id}] {show_name}")
    logger.info(f"{'='*70}")

    # Search Google for IBDB link
    ibdb_url = search_google_for_ibdb(show_name)

    if not ibdb_url:
        return None, None, 'not_found'

    # Small delay between requests
    time.sleep(2)

    # Fetch IBDB page
    production_year, num_performances = fetch_ibdb_data(ibdb_url)

    if production_year and num_performances:
        logger.info(f"  ✓ Year: {production_year}, Performances: {num_performances}")
        return production_year, num_performances, 'success'
    elif production_year or num_performances:
        logger.info(f"  ⚠️  Partial data - Year: {production_year}, Performances: {num_performances}")
        return production_year, num_performances, 'partial'
    else:
        logger.warning(f"  ❌ No data found")
        return None, None, 'not_found'


def main():
    """Main scraping function."""
    logger.info("="*70)
    logger.info("EFFICIENT IBDB PERFORMANCE SCRAPER")
    logger.info("="*70)

    # Load data
    input_file = Path('data/tony_outcomes_with_performances.csv')
    df = pd.read_csv(input_file)

    logger.info(f"\nLoaded {len(df)} shows from {input_file}")

    # Find pending shows
    pending = df[df['scrape_status'] == 'pending']
    logger.info(f"Shows to scrape: {len(pending)}")

    # Scrape each pending show
    for idx, row in pending.iterrows():
        show_id = row['show_id']
        show_name = row['show_name']

        # Scrape
        production_year, num_performances, status = scrape_show(show_id, show_name)

        # Update dataframe
        df.at[idx, 'production_year'] = production_year
        df.at[idx, 'num_performances'] = num_performances
        df.at[idx, 'scrape_status'] = status

        # Save progress every 20 shows
        if (idx + 1) % 20 == 0:
            df.to_csv(input_file, index=False)
            logger.info(f"\n✓ Progress saved ({idx + 1} shows processed)")

        # Delay between shows to avoid rate limiting
        time.sleep(3)

    # Final save
    df.to_csv(input_file, index=False)
    logger.info(f"\n✓ All data saved to {input_file}")

    # Summary
    logger.info("\n" + "="*70)
    logger.info("SUMMARY")
    logger.info("="*70)
    logger.info(f"Total shows: {len(df)}")
    logger.info(f"Success: {(df['scrape_status'] == 'success').sum()}")
    logger.info(f"Partial: {(df['scrape_status'] == 'partial').sum()}")
    logger.info(f"Not found: {(df['scrape_status'] == 'not_found').sum()}")
    logger.info(f"Pending: {(df['scrape_status'] == 'pending').sum()}")


if __name__ == '__main__':
    main()
