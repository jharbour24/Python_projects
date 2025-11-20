"""
Test scraper on Bye Bye Birdie to verify it finds the 2009 revival (not 1961 original).
"""

import logging
from browser_ibdb_scraper import BrowserIBDBScraper

# Set up detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

# Test with Bye Bye Birdie (should find 2009 revival with 1 producer: Roundabout Theatre Company)
print("="*70)
print("TESTING: BYE BYE BIRDIE")
print("Expected: 2009 revival with 1 producer (Roundabout Theatre Company)")
print("="*70)

scraper = BrowserIBDBScraper(browser='chrome', headless=False)

try:
    scraper.start_browser()
    result = scraper.search_and_scrape("BYE BYE BIRDIE")

    print("\n" + "="*70)
    print("RESULT:")
    print("="*70)
    print(f"IBDB URL: {result['ibdb_url']}")
    print(f"Total Producers: {result['num_total_producers']}")
    print(f"Status: {result['scrape_status']}")
    print(f"Notes: {result['scrape_notes']}")
    print("="*70)

    # Check if URL contains the correct production ID or year
    if result['ibdb_url']:
        if '2009' in result['ibdb_url'] or '495034' in result['ibdb_url']:
            print("\n✓ SUCCESS: Found the 2009 revival!")
        elif '1961' in result['ibdb_url'] or '2668' in result['ibdb_url']:
            print("\n✗ ERROR: Found the 1961 original instead of 2009 revival")
        else:
            print(f"\n? Check URL to verify correct production")

finally:
    scraper.close_browser()
