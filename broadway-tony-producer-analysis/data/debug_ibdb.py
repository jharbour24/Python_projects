"""
Debug script to inspect IBDB HTML structure.
Saves HTML to file for inspection.
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# Set up Chrome
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

# Load The Book of Mormon page
url = "https://www.ibdb.com/broadway-production/The+Book+of+Mormon"
print(f"Loading: {url}")
driver.get(url)
time.sleep(3)

# Save full HTML
html = driver.page_source
with open('ibdb_debug.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Saved HTML to ibdb_debug.html ({len(html)} chars)")

# Parse and show structure
soup = BeautifulSoup(html, 'html.parser')

# Search for "produc" in text
print("\n" + "="*60)
print("SEARCHING FOR 'PRODUC' IN PAGE TEXT:")
print("="*60)

all_text = soup.get_text(separator='\n')
lines = all_text.split('\n')

for i, line in enumerate(lines):
    if 'produc' in line.lower():
        # Show context (3 lines before and after)
        start = max(0, i-3)
        end = min(len(lines), i+4)
        print(f"\nLine {i}:")
        for j in range(start, end):
            marker = ">>> " if j == i else "    "
            print(f"{marker}{lines[j][:100]}")

# Search for specific elements
print("\n" + "="*60)
print("CHECKING COMMON STRUCTURES:")
print("="*60)

# Check for tables
tables = soup.find_all('table')
print(f"\nFound {len(tables)} tables")
for idx, table in enumerate(tables[:3]):  # Show first 3
    text = table.get_text(separator=' | ', strip=True)[:200]
    print(f"  Table {idx}: {text}...")

# Check for common class names
for class_name in ['staff', 'produc', 'credit', 'cast']:
    elements = soup.find_all(class_=lambda x: x and class_name in x.lower() if x else False)
    if elements:
        print(f"\nFound {len(elements)} elements with '{class_name}' in class:")
        for elem in elements[:3]:
            print(f"  Class: {elem.get('class')}")
            print(f"  Text: {elem.get_text(strip=True)[:100]}...")

# Check for divs and sections
print(f"\nFound {len(soup.find_all('div'))} div elements")
print(f"Found {len(soup.find_all('section'))} section elements")

driver.quit()

print("\n" + "="*60)
print("DONE! Check ibdb_debug.html for full page source")
print("="*60)
