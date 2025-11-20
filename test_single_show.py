"""
Test scraper on a single show to debug producer parsing.
"""

import logging
from browser_ibdb_scraper import BrowserIBDBScraper

# Set up detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

# Test with Hamilton (should have 4 producers)
print("="*70)
print("TESTING: HAMILTON")
print("Expected: 4 producers (Jeffrey Seller, Sander Jacobs, Jill Furman, The Public Theater)")
print("="*70)

scraper = BrowserIBDBScraper(browser='chrome', headless=False)

try:
    scraper.start_browser()
    result = scraper.search_and_scrape("HAMILTON")

    print("\n" + "="*70)
    print("RESULT:")
    print("="*70)
    print(f"IBDB URL: {result['ibdb_url']}")
    print(f"\nProducer Breakdown:")
    print(f"  Lead Producers: {result['num_lead_producers']}")
    print(f"  Producers: {result['num_producers']}")
    print(f"  Co-Producers: {result['num_co_producers']}")
    print(f"  Associate Producers: {result['num_associate_producers']}")
    print(f"  Produced in association with: {result['num_produced_in_association_with']}")
    print(f"  TOTAL: {result['num_total_producers']}")
    print(f"\nStatus: {result['scrape_status']}")
    print(f"Notes: {result['scrape_notes']}")
    print("="*70)

finally:
    scraper.close_browser()

print("\n" + "="*70)
print("NEXT: Try HADESTOWN")
print("Expected: 45 producers")
print("="*70)

scraper2 = BrowserIBDBScraper(browser='chrome', headless=False)

try:
    scraper2.start_browser()
    result2 = scraper2.search_and_scrape("HADESTOWN")

    print("\n" + "="*70)
    print("RESULT:")
    print("="*70)
    print(f"IBDB URL: {result2['ibdb_url']}")
    print(f"\nProducer Breakdown:")
    print(f"  Lead Producers: {result2['num_lead_producers']}")
    print(f"  Producers: {result2['num_producers']}")
    print(f"  Co-Producers: {result2['num_co_producers']}")
    print(f"  Associate Producers: {result2['num_associate_producers']}")
    print(f"  Produced in association with: {result2['num_produced_in_association_with']}")
    print(f"  TOTAL: {result2['num_total_producers']}")
    print(f"\nStatus: {result2['scrape_status']}")
    print(f"Notes: {result2['scrape_notes']}")
    print("="*70)

finally:
    scraper2.close_browser()
