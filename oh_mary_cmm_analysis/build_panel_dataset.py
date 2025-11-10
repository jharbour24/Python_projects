#!/usr/bin/env python3
"""
Build Panel Dataset for Causal Analysis

Merges Reddit engagement data with Broadway grosses data at weekly level,
creates lagged variables, and adds control flags for causal modeling.

This script is the foundation for testing whether social media buzz (Reddit)
predicts future box office performance, accounting for advance purchase behavior.
"""

import pandas as pd
import numpy as np
import yaml
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Import our custom utilities
from analysis.merge_utils import standardize_week, normalize_show_names, safe_merge_weekly
from analysis.feature_engineering import make_lags, capacity_constraint_flag, phase_flags

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PanelDatasetBuilder:
    """Builds merged panel dataset from Reddit and grosses data."""

    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize builder with configuration."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.data_dir = Path("data")
        self.output_dir = Path("data/merged")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Initialized Panel Dataset Builder")

    def load_reddit_data(self) -> pd.DataFrame:
        """
        Load and aggregate Reddit data to weekly level.

        Reads individual show CSVs and aggregates metrics by (show, week).
        """
        logger.info("="*70)
        logger.info("LOADING REDDIT DATA")
        logger.info("="*70)

        all_reddit = []
        raw_dir = self.data_dir / "raw"

        if not raw_dir.exists():
            logger.error(f"Reddit data directory not found: {raw_dir}")
            return pd.DataFrame()

        # Load each show's Reddit data
        for csv_file in raw_dir.glob("reddit_*.csv"):
            show_id = csv_file.stem.replace('reddit_', '')

            try:
                df = pd.read_csv(csv_file)
                if df.empty:
                    logger.warning(f"  Skipping {show_id}: empty file")
                    continue

                df['show_id'] = show_id
                df['show_name'] = self.config['shows'].get(show_id, {}).get('name', show_id)
                all_reddit.append(df)

                logger.info(f"  ✓ Loaded {show_id}: {len(df)} posts")

            except Exception as e:
                logger.error(f"  ✗ Error loading {csv_file}: {e}")
                continue

        if not all_reddit:
            logger.error("No Reddit data loaded!")
            return pd.DataFrame()

        reddit_df = pd.concat(all_reddit, ignore_index=True)
        logger.info(f"\n✓ Combined Reddit data: {len(reddit_df):,} posts across {reddit_df['show_id'].nunique()} shows")

        # Standardize to weekly bins
        reddit_df = standardize_week(reddit_df, date_col='created_utc', week_start='Mon')

        # Aggregate to weekly level
        logger.info("\nAggregating to weekly metrics...")
        weekly_reddit = reddit_df.groupby(['show_id', 'show_name', 'week_start']).agg({
            'score': ['sum', 'mean', 'max'],
            'num_comments': ['sum', 'mean'],
            'id': 'count',  # post count
            'subreddit': 'nunique',  # subreddit diversity
            'author': 'nunique'  # unique contributors
        }).reset_index()

        # Flatten column names
        weekly_reddit.columns = [
            'show_id', 'show_name', 'week_start',
            'total_upvotes', 'avg_upvotes', 'max_upvotes',
            'total_comments', 'avg_comments',
            'post_count', 'subreddit_diversity', 'unique_contributors'
        ]

        # Calculate derived engagement metrics
        weekly_reddit['total_engagement'] = weekly_reddit['total_upvotes'] + weekly_reddit['total_comments']
        weekly_reddit['avg_engagement'] = weekly_reddit['total_engagement'] / weekly_reddit['post_count']
        weekly_reddit['viral_score'] = weekly_reddit['max_upvotes'] * weekly_reddit['subreddit_diversity']

        # Add advocacy/intent metrics if available from original data
        # For now, set as sum of upvotes as proxy
        weekly_reddit['advocacy_score'] = weekly_reddit['total_upvotes']

        logger.info(f"✓ Weekly Reddit data: {len(weekly_reddit):,} (show, week) observations")
        logger.info(f"  Date range: {weekly_reddit['week_start'].min()} to {weekly_reddit['week_start'].max()}")
        logger.info(f"  Avg weeks per show: {len(weekly_reddit) / weekly_reddit['show_id'].nunique():.1f}")

        return weekly_reddit

    def load_grosses_data(self) -> pd.DataFrame:
        """
        Load Broadway grosses data.

        Reads weekly grosses from CSV and ensures weekly alignment.
        """
        logger.info("\n" + "="*70)
        logger.info("LOADING BROADWAY GROSSES DATA")
        logger.info("="*70)

        grosses_file = self.data_dir / "grosses" / "broadway_grosses_2024_2025.csv"

        if not grosses_file.exists():
            logger.error(f"Grosses file not found: {grosses_file}")
            logger.error("Run broadway_grosses_scraper.py first!")
            return pd.DataFrame()

        grosses_df = pd.read_csv(grosses_file)
        logger.info(f"Loaded grosses data: {len(grosses_df):,} rows")

        # Standardize week (grosses have 'week_ending', map to Monday of that week)
        grosses_df = standardize_week(grosses_df, date_col='week_ending', week_start='Mon')

        # Aggregate by (show_id, week_start) in case of duplicates
        weekly_grosses = grosses_df.groupby(['show_id', 'config_name', 'week_start']).agg({
            'gross': 'sum',
            'capacity_percent': 'mean',
            'avg_ticket_price': 'mean',
            'attendance': 'sum',
            'performances': 'sum'
        }).reset_index()

        weekly_grosses = weekly_grosses.rename(columns={'config_name': 'show_name'})

        logger.info(f"✓ Weekly grosses data: {len(weekly_grosses):,} (show, week) observations")
        logger.info(f"  Shows: {weekly_grosses['show_id'].nunique()}")
        logger.info(f"  Date range: {weekly_grosses['week_start'].min()} to {weekly_grosses['week_start'].max()}")

        return weekly_grosses

    def merge_datasets(self, reddit_df: pd.DataFrame, grosses_df: pd.DataFrame) -> pd.DataFrame:
        """
        Merge Reddit and grosses data on (show_id, week_start).
        """
        logger.info("\n" + "="*70)
        logger.info("MERGING REDDIT & GROSSES")
        logger.info("="*70)

        # Use safe merge with validation
        merged = safe_merge_weekly(
            reddit_df,
            grosses_df,
            on=['show_id', 'week_start'],
            how='inner',
            validate='1:1'
        )

        # Keep show_name from grosses (more canonical)
        if 'show_name_x' in merged.columns:
            merged = merged.drop(columns=['show_name_x'])
            merged = merged.rename(columns={'show_name_y': 'show_name'})

        return merged

    def create_lags_and_controls(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create lagged variables and control flags.
        """
        logger.info("\n" + "="*70)
        logger.info("FEATURE ENGINEERING")
        logger.info("="*70)

        # Variables to lag (Reddit metrics that might predict future grosses)
        lag_vars = [
            'post_count',
            'total_engagement',
            'unique_contributors',
            'advocacy_score',
            'total_upvotes',
            'total_comments',
            'viral_score'
        ]

        # Create lags: 1, 2, 4, 6 weeks (4 weeks ≈ 31 days advance purchase)
        df = make_lags(df, lag_vars, group_col='show_id', time_col='week_start', lags=[1, 2, 4, 6])

        # Capacity constraint flag
        df = capacity_constraint_flag(df, cap_col='capacity_percent', threshold=0.98)

        # Phase flags (preview vs post-opening)
        # Try to infer opening dates or use config if available
        opening_dates = {}
        for show_id, show_info in self.config.get('shows', {}).items():
            if 'opening_date' in show_info:
                opening_dates[show_id] = show_info['opening_date']

        if opening_dates:
            df = phase_flags(df, show_col='show_id', week_col='week_start', opening_dates=opening_dates)
        else:
            logger.warning("No opening dates in config - phase flags will be null")
            df['is_preview'] = np.nan
            df['is_post_opening'] = np.nan

        return df

    def build_and_save(self):
        """
        Main pipeline: load, merge, engineer features, and save.
        """
        logger.info("\n" + "="*70)
        logger.info("BUILDING PANEL DATASET FOR CAUSAL ANALYSIS")
        logger.info("="*70)
        logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Load data
        reddit_df = self.load_reddit_data()
        if reddit_df.empty:
            logger.error("Failed to load Reddit data - aborting")
            return

        grosses_df = self.load_grosses_data()
        if grosses_df.empty:
            logger.error("Failed to load grosses data - aborting")
            return

        # Merge
        merged_df = self.merge_datasets(reddit_df, grosses_df)
        if merged_df.empty:
            logger.error("Merge resulted in empty dataset - check date/show alignment")
            return

        # Feature engineering
        panel_df = self.create_lags_and_controls(merged_df)

        # Final validation
        logger.info("\n" + "="*70)
        logger.info("FINAL VALIDATION")
        logger.info("="*70)

        # Check for NaN in merge keys
        for col in ['show_id', 'week_start']:
            nan_count = panel_df[col].isna().sum()
            if nan_count > 0:
                logger.error(f"ERROR: {nan_count} NaN values in key column '{col}'")
            else:
                logger.info(f"✓ No NaN in '{col}'")

        # Check for duplicates
        dups = panel_df.duplicated(subset=['show_id', 'week_start'], keep=False)
        if dups.any():
            logger.error(f"ERROR: {dups.sum()} duplicate (show, week) rows!")
        else:
            logger.info("✓ No duplicate (show, week) keys")

        # Summary statistics
        logger.info(f"\n✓ Final panel dataset:")
        logger.info(f"  Rows: {len(panel_df):,}")
        logger.info(f"  Shows: {panel_df['show_id'].nunique()}")
        logger.info(f"  Weeks: {panel_df['week_start'].nunique()}")
        logger.info(f"  Date range: {panel_df['week_start'].min()} to {panel_df['week_start'].max()}")
        logger.info(f"  Columns: {len(panel_df.columns)}")

        # Missingness report
        logger.info(f"\nMissingness by key variables:")
        key_vars = ['gross', 'capacity_percent', 'total_engagement', 'total_engagement_lag4']
        for var in key_vars:
            if var in panel_df.columns:
                missing_pct = panel_df[var].isna().sum() / len(panel_df) * 100
                logger.info(f"  {var}: {missing_pct:.1f}% missing")

        # Save outputs
        logger.info("\n" + "="*70)
        logger.info("SAVING OUTPUTS")
        logger.info("="*70)

        # Save as Parquet (efficient for large datasets)
        parquet_path = self.output_dir / "merged_reddit_grosses_panel.parquet"
        panel_df.to_parquet(parquet_path, index=False)
        logger.info(f"✓ Saved Parquet: {parquet_path}")

        # Save as CSV (human-readable)
        csv_path = self.output_dir / "merged_reddit_grosses_panel.csv"
        panel_df.to_csv(csv_path, index=False)
        logger.info(f"✓ Saved CSV: {csv_path}")

        # Save metadata
        metadata = {
            'created': datetime.now().isoformat(),
            'rows': len(panel_df),
            'shows': int(panel_df['show_id'].nunique()),
            'weeks': int(panel_df['week_start'].nunique()),
            'date_range': {
                'start': str(panel_df['week_start'].min()),
                'end': str(panel_df['week_start'].max())
            },
            'columns': list(panel_df.columns),
            'lag_variables': [col for col in panel_df.columns if '_lag' in col]
        }

        import json
        metadata_path = self.output_dir / "panel_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"✓ Saved metadata: {metadata_path}")

        logger.info("\n" + "="*70)
        logger.info("✅ PANEL DATASET BUILD COMPLETE")
        logger.info("="*70)
        logger.info(f"\nNext steps:")
        logger.info(f"  1. Run: python3 run_lagged_causality_analysis.py")
        logger.info(f"  2. Check: {parquet_path}")


def main():
    """Main execution."""
    builder = PanelDatasetBuilder()
    builder.build_and_save()


if __name__ == "__main__":
    main()
