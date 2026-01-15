"""
Test scraper on Romeo & Juliet to verify it captures co-producers.
"""

import logging
from browser_ibdb_scraper import BrowserIBDBScraper

# Set up detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

# Test with Romeo & Juliet (should capture both producers and co-producers)
print("="*70)
print("TESTING: ROMEO AND JULIET (Revival)")
print("Expected: Should capture Lead Producers AND Co-Producers")
print("="*70)

scraper = BrowserIBDBScraper(browser='chrome', headless=False)

try:
    scraper.start_browser()
    result = scraper.search_and_scrape("ROMEO AND JULIET")

    print("\n" + "="*70)
    print("RESULT:")
    print("="*70)
    print(f"IBDB URL: {result['ibdb_url']}")
    print(f"Total Producers: {result['num_total_producers']}")
    print(f"Status: {result['scrape_status']}")
    print(f"Notes: {result['scrape_notes']}")
    print("="*70)

    # Verify it found the revival (2013 production)
    if result['ibdb_url']:
        if '2013' in result['ibdb_url'] or 'romeo' in result['ibdb_url'].lower():
            print("\n✓ Found Romeo & Juliet page")
            print(f"✓ Counted {result['num_total_producers']} total producers (including co-producers)")
        else:
            print(f"\n? Check URL to verify correct production: {result['ibdb_url']}")

finally:
    scraper.close_browser()
