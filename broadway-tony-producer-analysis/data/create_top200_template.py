"""
Create a template CSV for manual producer data entry for top 200 Broadway shows.

This script:
1. Loads the processed weekly grosses data
2. Ranks shows by total gross revenue
3. Selects the top 200 highest-grossing shows
4. Creates a template CSV for manual IBDB data entry

Run this on your Mac after build_master.py has been executed.

Author: Broadway Analysis Pipeline
"""

import pandas as pd
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from utils import setup_logger

logger = setup_logger(__name__)


def main():
    """Create top 200 shows template from existing grosses data."""

    logger.info("=" * 60)
    logger.info("CREATE TOP 200 BROADWAY SHOWS TEMPLATE")
    logger.info("=" * 60)

    # Load processed weekly grosses
    grosses_path = Path(__file__).parent / 'processed' / 'weekly_grosses.csv'

    if not grosses_path.exists():
        logger.error(f"Weekly grosses file not found: {grosses_path}")
        logger.info("Run build_master.py first to create processed data")
        return

    logger.info(f"Loading weekly grosses from {grosses_path}")
    grosses = pd.read_csv(grosses_path)
    logger.info(f"Loaded {len(grosses)} weekly records")

    # Calculate total gross per show
    show_stats = grosses.groupby('show_id').agg({
        'title': 'first',
        'weekly_gross': ['sum', 'count', 'mean'],
        'week_ending': ['min', 'max']
    }).reset_index()

    # Flatten column names
    show_stats.columns = ['show_id', 'title', 'total_gross', 'weeks_tracked',
                         'avg_weekly_gross', 'first_week', 'last_week']

    # Sort by total gross
    show_stats = show_stats.sort_values('total_gross', ascending=False)

    logger.info(f"\nTop 10 highest-grossing shows:")
    for idx, row in show_stats.head(10).iterrows():
        logger.info(f"  {row['title']}: ${row['total_gross']:,.0f} ({row['weeks_tracked']} weeks)")

    # Select top 200
    top_200 = show_stats.head(200).copy()
    logger.info(f"\nSelected top {len(top_200)} shows by total gross")

    # Create template with empty producer columns
    template = pd.DataFrame({
        'title': top_200['title'],
        'show_id': top_200['show_id'],
        'total_gross': top_200['total_gross'],
        'weeks_tracked': top_200['weeks_tracked'],
        'avg_weekly_gross': top_200['avg_weekly_gross'],
        'first_week': top_200['first_week'],
        'last_week': top_200['last_week'],
        'ibdb_url': '',
        'producer_count_total': '',
        'lead_producer_count': '',
        'co_producer_count': '',
        'notes': '',
        'data_quality': 'pending'
    })

    # Save template
    template_path = Path(__file__).parent / 'raw' / 'top_200_shows_producer_template.csv'
    template.to_csv(template_path, index=False)

    logger.info(f"\nCreated template: {template_path}")
    logger.info(f"Contains {len(template)} shows")

    # Print statistics
    logger.info("\n" + "=" * 60)
    logger.info("TEMPLATE STATISTICS")
    logger.info("=" * 60)
    logger.info(f"Total shows: {len(template)}")
    logger.info(f"Total gross range: ${template['total_gross'].min():,.0f} - ${template['total_gross'].max():,.0f}")
    logger.info(f"Average gross: ${template['total_gross'].mean():,.0f}")
    logger.info(f"Date range: {template['first_week'].min()} to {template['last_week'].max()}")

    logger.info("\n" + "=" * 60)
    logger.info("NEXT STEPS")
    logger.info("=" * 60)
    logger.info("1. Open top_200_shows_producer_template.csv")
    logger.info("2. For each show, visit IBDB and fill in:")
    logger.info("   - ibdb_url: Direct link to show page")
    logger.info("   - producer_count_total: Total number of producers")
    logger.info("   - lead_producer_count: Number of lead producers")
    logger.info("   - co_producer_count: Number of co-producers")
    logger.info("   - notes: Any relevant observations")
    logger.info("   - data_quality: Change to 'verified' after manual entry")
    logger.info("3. Or try the advanced scraper: python3 scrape_producers_undetected.py")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
