"""
Simple producer scraper that uses existing weekly grosses data to find shows.

This script:
1. Loads show titles from existing weekly_grosses data
2. Scrapes producer information for each show from IBDB
3. Uses undetected-chromedriver to bypass Cloudflare

Much simpler and more reliable than trying to scrape IBDB's season pages!

Author: Broadway Analysis Pipeline
"""

import re
import time
from typing import Dict, List
import pandas as pd
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).parent.parent))

import config
from utils import normalize_title, create_show_id, setup_logger

logger = setup_logger(__name__)

# Check if undetected-chromedriver is installed
try:
    import undetected_chromedriver as uc
    from selenium.webdriver.support.ui import WebDriverWait
    from bs4 import BeautifulSoup
    UNDETECTED_AVAILABLE = True
except ImportError:
    UNDETECTED_AVAILABLE = False
    logger.warning("undetected-chromedriver not installed")

# Import the scraper class from the comprehensive scraper
from scrape_all_broadway_shows import ComprehensiveBroadwayScraper


def get_shows_from_grosses() -> List[Dict]:
    """
    Get list of shows from existing weekly grosses data.

    Returns
    -------
    list of dict
        Shows with title and show_id
    """
    logger.info("Loading shows from weekly grosses data...")

    # Try to load from processed data first
    grosses_paths = [
        Path(__file__).parent / 'processed' / 'weekly_grosses.csv',
        Path(__file__).parent / 'raw' / 'weekly_grosses_preliminary.csv',
    ]

    grosses_df = None
    for path in grosses_paths:
        if path.exists():
            logger.info(f"Loading from: {path}")
            grosses_df = pd.read_csv(path)
            break

    if grosses_df is None:
        logger.error("No weekly grosses data found!")
        logger.info("Run the Broadway World scraper first to get grosses data")
        return []

    logger.info(f"Loaded {len(grosses_df)} weekly records")

    # Get unique shows - check for different column names
    possible_title_cols = ['title', 'show_title', 'show_name', 'show']
    title_col = None

    for col in possible_title_cols:
        if col in grosses_df.columns:
            title_col = col
            break

    if title_col is None:
        logger.error(f"No title column found. Columns: {grosses_df.columns.tolist()}")
        return []

    logger.info(f"Using column: {title_col}")

    unique_shows = grosses_df[title_col].unique()
    logger.info(f"Found {len(unique_shows)} unique shows")

    # Create show list
    shows = []
    for title in unique_shows:
        if pd.notna(title) and title.strip():
            shows.append({
                'title': title.strip(),
                'show_id': create_show_id(title)
            })

    # Sort by title for easier tracking
    shows = sorted(shows, key=lambda x: x['title'])

    logger.info(f"Prepared {len(shows)} shows for scraping")
    logger.info(f"Sample shows: {[s['title'] for s in shows[:5]]}")

    return shows


def main():
    """Main scraping function."""

    logger.info("=" * 80)
    logger.info("BROADWAY PRODUCER SCRAPER (FROM GROSSES DATA)")
    logger.info("=" * 80)

    if not UNDETECTED_AVAILABLE:
        logger.error("Required packages not installed!")
        logger.info("Install with: pip3 install undetected-chromedriver selenium beautifulsoup4")
        return

    # Step 1: Get shows from grosses data
    shows = get_shows_from_grosses()

    if not shows:
        logger.error("No shows found - cannot proceed")
        return

    # Step 2: Initialize scraper
    try:
        logger.info("\n" + "="*80)
        logger.info("Initializing ChromeDriver...")
        logger.info("="*80)
        scraper = ComprehensiveBroadwayScraper()

        # Test Cloudflare bypass
        if not scraper.test_cloudflare_bypass():
            logger.error("\n⚠️  Cloudflare bypass failed")
            logger.info("Options:")
            logger.info("1. Try again later")
            logger.info("2. Use a VPN or different network")
            logger.info("3. Manual data collection")
            return

    except Exception as e:
        logger.error(f"Failed to initialize scraper: {e}")
        return

    # Step 3: Scrape producers for each show
    logger.info("\n" + "="*80)
    logger.info("SCRAPING PRODUCER DATA")
    logger.info("="*80)

    # TEST MODE - only scrape first 10 shows
    test_mode = True
    test_limit = 10

    if test_mode:
        logger.info(f"\n⚠️  TEST MODE: Scraping first {test_limit} shows only")
        logger.info("Edit script and set test_mode = False to scrape all shows\n")
        shows_to_scrape = shows[:test_limit]
    else:
        shows_to_scrape = shows

    results = []
    successful = 0

    for idx, show in enumerate(shows_to_scrape):
        title = show['title']

        logger.info(f"\n[{idx+1}/{len(shows_to_scrape)}] {title}")

        # Build IBDB URL - try direct URL construction
        # IBDB URLs are like: https://www.ibdb.com/broadway-production/Show-Name-ID
        # We'll try searching and using the first result

        ibdb_url = scraper.search_ibdb(title)

        if not ibdb_url:
            logger.warning(f"Could not find IBDB page for: {title}")
            result = {
                'title': title,
                'show_id': show['show_id'],
                'ibdb_url': None,
                'scrape_success': False,
                'producer_count_total': None,
            }
            results.append(result)
            continue

        # Scrape producers
        producer_data = scraper.scrape_producers_detailed(ibdb_url)

        # Combine with show info
        result = {
            'title': title,
            'show_id': show['show_id'],
            **producer_data
        }

        results.append(result)

        if producer_data['scrape_success']:
            successful += 1
            logger.info(f"✓ Success: {producer_data['producer_count_total']} producers")
        else:
            logger.warning(f"✗ Failed to extract producers")

        # Rate limiting
        time.sleep(config.RATE_LIMIT_DELAY)

    # Save results
    results_df = pd.DataFrame(results)
    output_path = Path(__file__).parent / 'raw' / 'producers_from_grosses.csv'
    results_df.to_csv(output_path, index=False)

    logger.info("\n" + "="*80)
    logger.info("SCRAPING COMPLETE")
    logger.info("="*80)
    logger.info(f"Shows scraped: {len(results)}")
    logger.info(f"Successful: {successful} ({successful/len(results)*100:.1f}%)")
    logger.info(f"Output: {output_path}")
    logger.info("="*80)

    # Show statistics
    if successful > 0:
        success_df = results_df[results_df['scrape_success'] == True]
        logger.info(f"\nProducer count statistics:")
        logger.info(f"  Mean: {success_df['producer_count_total'].mean():.1f}")
        logger.info(f"  Median: {success_df['producer_count_total'].median():.1f}")
        logger.info(f"  Min: {success_df['producer_count_total'].min()}")
        logger.info(f"  Max: {success_df['producer_count_total'].max()}")


if __name__ == '__main__':
    main()
