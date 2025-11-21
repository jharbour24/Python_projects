#!/usr/bin/env python3
"""
Scrape performance counts internally using web searches.
This script will be run by Claude to populate performance data.
"""

import pandas as pd
import re
from pathlib import Path

# Import revivals dictionary
from REVIVALS_DICTIONARY import BROADWAY_REVIVALS

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


def main():
    """Load tony_outcomes.csv and prepare for scraping."""

    # Load data
    input_file = Path('data/tony_outcomes.csv')
    df = pd.read_csv(input_file)

    print(f"Loaded {len(df)} shows from {input_file}")

    # Add columns if they don't exist
    if 'production_year' not in df.columns:
        df['production_year'] = None
    if 'num_performances' not in df.columns:
        df['num_performances'] = None
    if 'scrape_status' not in df.columns:
        df['scrape_status'] = 'pending'

    # Save initial structure
    output_file = Path('data/tony_outcomes_with_performances.csv')
    df.to_csv(output_file, index=False)

    print(f"Created {output_file}")
    print(f"Ready to scrape {len(df)} shows")

    return df


if __name__ == '__main__':
    main()
