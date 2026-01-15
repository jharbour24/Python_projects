#!/usr/bin/env python3
"""
Add performance counts and production years to tony_outcomes.csv
Scrapes IBDB independently for each show.
"""

import pandas as pd
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from pathlib import Path
import logging

# Import revivals dictionary
from REVIVALS_DICTIONARY import BROADWAY_REVIVALS

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def extract_performances_and_year(page_text):
    """Extract number of performances and production year from IBDB page."""

    # Extract production year from "Opening Night"
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


def search_and_scrape_show(driver, show_name, show_id):
    """Search for a show on IBDB and extract performance data."""

    logger.info(f"\n{'='*70}")
    logger.info(f"[{show_id}] {show_name}")
    logger.info(f"{'='*70}")

    try:
        # Determine if this is a revival
        search_query = f"{show_name} IBDB Broadway revival 2010..2025"

        logger.info(f"Google search: {search_query}")

        # Go to Google
        driver.get("https://www.google.com")
        time.sleep(2)

        # Search
        search_box = driver.find_element(By.NAME, "q")
        search_box.clear()
        search_box.send_keys(search_query)
        search_box.submit()

        # Wait for 4 seconds to allow CAPTCHA solving
        logger.info("⏸️  4-second pause for CAPTCHA (if needed)...")
        time.sleep(4)

        # Find IBDB link
        try:
            # Look for IBDB link in search results
            ibdb_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'ibdb.com/broadway-production/')]")

            if not ibdb_links:
                logger.warning(f"❌ No IBDB link found for {show_name}")
                return None, None, "no_ibdb_link"

            # Click first IBDB link
            first_link = ibdb_links[0]
            ibdb_url = first_link.get_attribute('href')
            logger.info(f"Found IBDB: {ibdb_url}")

            driver.get(ibdb_url)
            time.sleep(2)

        except Exception as e:
            logger.warning(f"❌ Error finding IBDB link: {e}")
            return None, None, "search_error"

        # Extract page text
        try:
            page_text = driver.find_element(By.TAG_NAME, "body").text
        except:
            logger.warning(f"❌ Could not extract page text")
            return None, None, "extraction_error"

        # Extract data
        production_year, num_performances = extract_performances_and_year(page_text)

        if production_year:
            logger.info(f"✓ Production Year: {production_year}")
        else:
            logger.warning(f"⚠️  Production Year: Not found")

        if num_performances:
            logger.info(f"✓ Performances: {num_performances}")
        else:
            logger.warning(f"⚠️  Performances: Not found")

        status = "success" if (production_year and num_performances) else "partial"

        return production_year, num_performances, status

    except Exception as e:
        logger.error(f"❌ Error scraping {show_name}: {e}")
        return None, None, "error"


def main():
    """Main function to add performance data to tony_outcomes.csv"""

    logger.info("="*70)
    logger.info("ADD PERFORMANCES TO TONY OUTCOMES DATA")
    logger.info("="*70)

    # Load tony_outcomes.csv
    input_file = Path('data/tony_outcomes.csv')
    if not input_file.exists():
        logger.error(f"File not found: {input_file}")
        return 1

    df = pd.read_csv(input_file)
    logger.info(f"\nLoaded {len(df)} shows from {input_file}")

    # Add new columns if they don't exist
    if 'production_year' not in df.columns:
        df['production_year'] = None
    if 'num_performances' not in df.columns:
        df['num_performances'] = None
    if 'scrape_status' not in df.columns:
        df['scrape_status'] = None

    # Setup Selenium
    logger.info("\nInitializing browser...")
    try:
        # Try Chrome first
        from selenium.webdriver.chrome.options import Options as ChromeOptions
        chrome_options = ChromeOptions()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(options=chrome_options)
        logger.info("✓ Chrome browser initialized")
    except:
        try:
            # Fall back to Safari
            driver = webdriver.Safari()
            logger.info("✓ Safari browser initialized")
        except Exception as e:
            logger.error(f"❌ Could not initialize browser: {e}")
            return 1

    driver.maximize_window()

    # Scrape each show
    try:
        for idx, row in df.iterrows():
            show_id = row['show_id']
            show_name = row['show_name']

            # Skip if already has data
            if pd.notna(row.get('num_performances')) and pd.notna(row.get('production_year')):
                logger.info(f"[{show_id}] {show_name} - Already has data, skipping")
                continue

            # Scrape
            production_year, num_performances, status = search_and_scrape_show(driver, show_name, show_id)

            # Update dataframe
            df.at[idx, 'production_year'] = production_year
            df.at[idx, 'num_performances'] = num_performances
            df.at[idx, 'scrape_status'] = status

            # Save progress after each show
            df.to_csv(input_file, index=False)
            logger.info(f"✓ Progress saved")

            # Delay between shows
            time.sleep(4)

        # Infinite retry loop for failed shows
        retry_num = 0
        while True:
            failed_shows = df[df['scrape_status'] != 'success']

            if len(failed_shows) == 0:
                logger.info("\n" + "="*70)
                logger.info("✓✓✓ ALL SHOWS SCRAPED SUCCESSFULLY! ✓✓✓")
                logger.info("="*70)
                break

            retry_num += 1
            logger.info(f"\n{'='*70}")
            logger.info(f"RETRY ROUND {retry_num}")
            logger.info(f"Retrying {len(failed_shows)} failed shows...")
            logger.info(f"{'='*70}")

            for idx, row in failed_shows.iterrows():
                show_id = row['show_id']
                show_name = row['show_name']

                logger.info(f"\nRetrying [{show_id}] {show_name}")

                production_year, num_performances, status = search_and_scrape_show(driver, show_name, show_id)

                df.at[idx, 'production_year'] = production_year
                df.at[idx, 'num_performances'] = num_performances
                df.at[idx, 'scrape_status'] = status

                df.to_csv(input_file, index=False)
                logger.info(f"✓ Progress saved")

                time.sleep(4)

    finally:
        driver.quit()
        logger.info("\n✓ Browser closed")

    # Final save
    output_file = Path('data/tony_outcomes_with_performances.csv')
    df.to_csv(output_file, index=False)
    logger.info(f"\n✓ Final data saved to: {output_file}")

    # Print summary
    logger.info("\n" + "="*70)
    logger.info("SUMMARY")
    logger.info("="*70)
    logger.info(f"Total shows: {len(df)}")
    logger.info(f"Shows with performances: {df['num_performances'].notna().sum()}")
    logger.info(f"Shows with production year: {df['production_year'].notna().sum()}")
    logger.info(f"Complete data: {((df['num_performances'].notna()) & (df['production_year'].notna())).sum()}")

    return 0


if __name__ == '__main__':
    exit(main())
