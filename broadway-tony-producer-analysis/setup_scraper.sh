#!/bin/bash

# Broadway Producer Analysis - Quick Setup Script
# This downloads the latest scraper files and tests your setup

echo "============================================================"
echo "BROADWAY PRODUCER ANALYSIS - QUICK SETUP"
echo "============================================================"

cd "$(dirname "$0")/data" || exit 1

echo ""
echo "Step 1: Downloading latest scraper files..."
echo "============================================================"

GITHUB_RAW="https://raw.githubusercontent.com/jharbour24/Python_projects/claude/broadway-tony-producer-analysis-01Cdc38t4zVhAxDDqRB17GLJ/broadway-tony-producer-analysis/data"

curl -s -o scrape_all_broadway_shows.py "${GITHUB_RAW}/scrape_all_broadway_shows.py"
echo "✓ Downloaded scrape_all_broadway_shows.py"

curl -s -o test_hadestown_scrape.py "${GITHUB_RAW}/test_hadestown_scrape.py"
echo "✓ Downloaded test_hadestown_scrape.py"

curl -s -o test_simple_scraper.py "${GITHUB_RAW}/test_simple_scraper.py"
echo "✓ Downloaded test_simple_scraper.py"

echo ""
echo "Step 2: Checking dependencies..."
echo "============================================================"

# Check if packages are installed
python3 -c "import undetected_chromedriver" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠ undetected-chromedriver not installed"
    echo "Installing dependencies..."
    pip3 install undetected-chromedriver beautifulsoup4 selenium
else
    echo "✓ Dependencies already installed"
fi

echo ""
echo "Step 3: Testing setup..."
echo "============================================================"
echo "Running test_simple_scraper.py..."
echo ""

python3 test_simple_scraper.py

echo ""
echo "============================================================"
echo "SETUP COMPLETE"
echo "============================================================"
echo ""
echo "If the test passed, you can now run:"
echo "  python3 test_hadestown_scrape.py    # Test Hadestown (should find 44 producers)"
echo "  python3 scrape_all_broadway_shows.py  # Scrape all Broadway shows"
echo ""
