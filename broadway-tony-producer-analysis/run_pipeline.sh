#!/bin/bash
# Broadway Tony Producer Analysis - Full Pipeline Runner
# This script runs the entire data collection and processing pipeline

set -e  # Exit on error

echo "=========================================="
echo "Broadway Tony Producer Analysis Pipeline"
echo "=========================================="
echo ""

# Check Python version
python --version
echo ""

# Step 1: Scrape Tony data
echo "Step 1/4: Scraping Tony Awards data..."
cd data
python scrape_tonys.py
echo "✓ Tony data scraped"
echo ""

# Step 2: Scrape producer data
echo "Step 2/4: Scraping producer counts..."
python scrape_producers.py
echo "✓ Producer data scraped"
echo ""

# Step 3: Collect grosses (will use manual CSV if available)
echo "Step 3/4: Collecting weekly grosses data..."
python get_grosses.py
echo "✓ Grosses data collected (if available)"
echo ""

# Step 4: Build master datasets
echo "Step 4/4: Building master datasets..."
python build_master.py
cd ..
echo "✓ Master datasets created"
echo ""

echo "=========================================="
echo "Pipeline complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Review master datasets in data/processed/"
echo "2. If you have weekly grosses data, place it in data/raw/grosses_raw.csv"
echo "3. Run the analysis notebook: jupyter notebook analysis/tony_producers_analysis.ipynb"
echo ""
echo "See README.md for detailed usage instructions."
