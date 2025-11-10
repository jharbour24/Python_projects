#!/usr/bin/env python3
"""
Weekly Panel Builder

Merges all public signals sources into a single weekly panel dataset.

Input: Individual weekly CSVs from each source
Output: Combined panel with (show, week_start) as key
"""

import argparse
import pandas as pd
import logging
from pathlib import Path
import json
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.common.timebins import fill_missing_weeks

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_source_data(weekly_dir: Path, source_name: str) -> pd.DataFrame:
    """
    Load weekly data for a source.

    Args:
        weekly_dir: Directory containing weekly CSV files
        source_name: Name of source (e.g., 'google_trends')

    Returns:
        DataFrame or empty DataFrame if file not found
    """
    file_path = weekly_dir / f"{source_name}_weekly.csv"

    if not file_path.exists():
        logger.warning(f"File not found: {file_path}")
        return pd.DataFrame()

    logger.info(f"Loading: {file_path}")
    df = pd.read_csv(file_path)
    logger.info(f"  Loaded {len(df)} rows")

    return df


def merge_all_sources(
    google_trends_df: pd.DataFrame,
    wikipedia_df: pd.DataFrame,
    tiktok_df: pd.DataFrame,
    instagram_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Merge all source DataFrames on (show, week_start).

    Uses outer join to preserve all observations.

    Args:
        google_trends_df: Google Trends weekly data
        wikipedia_df: Wikipedia weekly data
        tiktok_df: TikTok weekly data
        instagram_df: Instagram weekly data

    Returns:
        Combined DataFrame
    """
    logger.info("\nMerging sources...")

    # Start with shows × weeks from all sources
    all_dfs = []

    if not google_trends_df.empty:
        # For Google Trends, we may have multiple queries per show-week
        # Aggregate to one row per show-week
        gt_agg = google_trends_df.groupby(['show', 'week_start']).agg({
            'gt_index': 'mean',  # Average across queries
            'is_partial': 'any'   # Flag if any query was partial
        }).reset_index()
        gt_agg = gt_agg.rename(columns={'gt_index': 'gt_avg_index'})
        all_dfs.append(gt_agg[['show', 'week_start']])
        logger.info(f"  Google Trends: {len(gt_agg)} show-weeks")
    else:
        gt_agg = pd.DataFrame()
        logger.warning("  Google Trends: No data")

    if not wikipedia_df.empty:
        all_dfs.append(wikipedia_df[['show', 'week_start']])
        logger.info(f"  Wikipedia: {len(wikipedia_df)} show-weeks")
    else:
        logger.warning("  Wikipedia: No data")

    if not tiktok_df.empty:
        all_dfs.append(tiktok_df[['show', 'week_start']])
        logger.info(f"  TikTok: {len(tiktok_df)} show-weeks")
    else:
        logger.warning("  TikTok: No data")

    if not instagram_df.empty:
        all_dfs.append(instagram_df[['show', 'week_start']])
        logger.info(f"  Instagram: {len(instagram_df)} show-weeks")
    else:
        logger.warning("  Instagram: No data")

    if not all_dfs:
        logger.error("No data from any source!")
        return pd.DataFrame()

    # Get unique show-week combinations
    panel_index = pd.concat(all_dfs, ignore_index=True).drop_duplicates()
    logger.info(f"\n  Combined panel: {len(panel_index)} unique show-weeks")

    # Merge each source with outer join
    panel = panel_index.copy()

    if not gt_agg.empty:
        panel = panel.merge(gt_agg, on=['show', 'week_start'], how='left')
        logger.info(f"    + Google Trends: {panel['gt_avg_index'].notna().sum()} rows with data")

    if not wikipedia_df.empty:
        panel = panel.merge(wikipedia_df, on=['show', 'week_start'], how='left')
        logger.info(f"    + Wikipedia: {panel['wiki_views'].notna().sum()} rows with data")

    if not tiktok_df.empty:
        panel = panel.merge(tiktok_df, on=['show', 'week_start'], how='left')
        logger.info(f"    + TikTok: {panel['tt_posts'].notna().sum()} rows with data")

    if not instagram_df.empty:
        panel = panel.merge(instagram_df, on=['show', 'week_start'], how='left')
        logger.info(f"    + Instagram: {panel['ig_posts'].notna().sum()} rows with data")

    # Add source availability flags
    panel['has_google_trends'] = panel['gt_avg_index'].notna().astype(int)
    panel['has_wikipedia'] = panel['wiki_views'].notna().astype(int)
    panel['has_tiktok'] = panel['tt_posts'].notna().astype(int)
    panel['has_instagram'] = panel['ig_posts'].notna().astype(int)

    # Sort by show and week
    panel = panel.sort_values(['show', 'week_start']).reset_index(drop=True)

    return panel


def generate_summary_stats(panel: pd.DataFrame) -> dict:
    """
    Generate summary statistics for the panel.

    Args:
        panel: Combined panel DataFrame

    Returns:
        Dict with summary stats
    """
    stats = {
        'n_shows': int(panel['show'].nunique()),
        'n_weeks': int(panel['week_start'].nunique()),
        'n_observations': len(panel),
        'date_range': {
            'min': panel['week_start'].min(),
            'max': panel['week_start'].max()
        },
        'coverage': {
            'google_trends': {
                'n_obs': int(panel['has_google_trends'].sum()),
                'pct': float(panel['has_google_trends'].mean() * 100)
            },
            'wikipedia': {
                'n_obs': int(panel['has_wikipedia'].sum()),
                'pct': float(panel['has_wikipedia'].mean() * 100)
            },
            'tiktok': {
                'n_obs': int(panel['has_tiktok'].sum()),
                'pct': float(panel['has_tiktok'].mean() * 100)
            },
            'instagram': {
                'n_obs': int(panel['has_instagram'].sum()),
                'pct': float(panel['has_instagram'].mean() * 100)
            }
        }
    }

    return stats


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Build weekly panel dataset from all public signals sources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  # Build panel from default locations
  python3 make_weekly_panel.py

  # Custom input/output directories
  python3 make_weekly_panel.py --input public_signals/data/weekly --output data/panel
        """
    )

    parser.add_argument(
        '--input',
        type=str,
        default='public_signals/data/weekly',
        help='Directory containing weekly CSV files (default: public_signals/data/weekly)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='public_signals/data/panel',
        help='Output directory for panel dataset (default: public_signals/data/panel)'
    )

    parser.add_argument(
        '--fill-missing',
        action='store_true',
        help='Fill in missing weeks with NaN (create balanced panel)'
    )

    args = parser.parse_args()

    weekly_dir = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load all sources
    logger.info("="*70)
    logger.info("LOADING SOURCES")
    logger.info("="*70 + "\n")

    google_trends_df = load_source_data(weekly_dir, 'google_trends')
    wikipedia_df = load_source_data(weekly_dir, 'wikipedia')
    tiktok_df = load_source_data(weekly_dir, 'tiktok')
    instagram_df = load_source_data(weekly_dir, 'instagram')

    # Merge
    logger.info("\n" + "="*70)
    logger.info("MERGING")
    logger.info("="*70)

    panel = merge_all_sources(
        google_trends_df,
        wikipedia_df,
        tiktok_df,
        instagram_df
    )

    if panel.empty:
        logger.error("Panel is empty, exiting")
        sys.exit(1)

    # Fill missing weeks if requested
    if args.fill_missing:
        logger.info("\nFilling missing weeks...")
        panel = fill_missing_weeks(
            panel,
            start_date=panel['week_start'].min(),
            end_date=panel['week_start'].max(),
            id_cols=['show']
        )
        logger.info(f"  Balanced panel: {len(panel)} observations")

    # Generate summary stats
    logger.info("\n" + "="*70)
    logger.info("SUMMARY")
    logger.info("="*70)

    stats = generate_summary_stats(panel)

    logger.info(f"\n  Shows: {stats['n_shows']}")
    logger.info(f"  Weeks: {stats['n_weeks']}")
    logger.info(f"  Observations: {stats['n_observations']}")
    logger.info(f"  Date range: {stats['date_range']['min']} to {stats['date_range']['max']}")
    logger.info("\n  Coverage:")
    for source, cov in stats['coverage'].items():
        logger.info(f"    {source:20s}: {cov['n_obs']:5d} obs ({cov['pct']:5.1f}%)")

    # Save outputs
    logger.info("\n" + "="*70)
    logger.info("SAVING")
    logger.info("="*70)

    # Parquet (main format)
    parquet_file = output_dir / "weekly_signals_panel.parquet"
    panel.to_parquet(parquet_file, index=False)
    logger.info(f"  ✓ {parquet_file}")

    # CSV (human-readable preview, first 1000 rows)
    csv_file = output_dir / "weekly_signals_panel_preview.csv"
    panel.head(1000).to_csv(csv_file, index=False)
    logger.info(f"  ✓ {csv_file} (preview)")

    # Metadata JSON
    metadata_file = output_dir / "panel_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(stats, f, indent=2)
    logger.info(f"  ✓ {metadata_file}")

    logger.info(f"\nPanel dataset ready: {parquet_file}")


if __name__ == '__main__':
    main()
