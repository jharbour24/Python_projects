#!/usr/bin/env python3
"""
Merge All Data Sources into Complete Modeling Dataset

Combines:
- Reddit engagement metrics
- Broadway box office grosses
- TikTok metrics
- Instagram metrics
- Wikipedia pageviews
- Google Trends

Into a single unified panel for causal analysis.

Usage:
    python -m public_signals.cli.merge_all_sources \
        --reddit-grosses data/merged/merged_reddit_grosses_panel.parquet \
        --social-signals public_signals/data/panel/weekly_social_signals.parquet \
        --output data/panel/complete_modeling_dataset.parquet
"""

import argparse
import pandas as pd
import logging
import sys
from pathlib import Path
import json
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.features.panel_features import create_model_ready_features

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_panel(path: str, panel_name: str) -> pd.DataFrame:
    """Load a panel dataset with error handling."""
    path_obj = Path(path)

    if not path_obj.exists():
        logger.error(f"{panel_name} not found: {path}")
        return pd.DataFrame()

    logger.info(f"Loading {panel_name}: {path}")

    try:
        df = pd.read_parquet(path)
        logger.info(f"  {len(df)} rows, {len(df.columns)} columns")
        return df
    except Exception as e:
        logger.error(f"Error loading {panel_name}: {e}")
        return pd.DataFrame()


def merge_panels(
    reddit_grosses_df: pd.DataFrame,
    social_signals_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Merge Reddit+Grosses with Social Signals panels.

    Args:
        reddit_grosses_df: Reddit engagement + Broadway grosses
        social_signals_df: TikTok, Instagram, Wikipedia, Google Trends

    Returns:
        Merged DataFrame with all sources
    """
    logger.info("\n" + "="*70)
    logger.info("MERGING PANELS")
    logger.info("="*70)

    # Check for required columns
    required_cols = ['show', 'week_start']

    for col in required_cols:
        if col not in reddit_grosses_df.columns:
            raise ValueError(f"Reddit+Grosses panel missing '{col}' column")
        if col not in social_signals_df.columns:
            raise ValueError(f"Social Signals panel missing '{col}' column")

    # Get initial stats
    reddit_rows = len(reddit_grosses_df)
    social_rows = len(social_signals_df)
    reddit_shows = reddit_grosses_df['show'].nunique()
    social_shows = social_signals_df['show'].nunique()

    logger.info(f"\nInput panels:")
    logger.info(f"  Reddit+Grosses: {reddit_rows} rows, {reddit_shows} shows")
    logger.info(f"  Social Signals: {social_rows} rows, {social_shows} shows")

    # Check for overlapping shows
    reddit_show_set = set(reddit_grosses_df['show'].unique())
    social_show_set = set(social_signals_df['show'].unique())

    overlapping_shows = reddit_show_set & social_show_set
    reddit_only = reddit_show_set - social_show_set
    social_only = social_show_set - reddit_show_set

    logger.info(f"\nShow overlap:")
    logger.info(f"  Both panels: {len(overlapping_shows)} shows")
    if overlapping_shows:
        logger.info(f"    {sorted(overlapping_shows)}")
    logger.info(f"  Reddit only: {len(reddit_only)} shows")
    if reddit_only:
        logger.info(f"    {sorted(reddit_only)}")
    logger.info(f"  Social only: {len(social_only)} shows")
    if social_only:
        logger.info(f"    {sorted(social_only)}")

    # Identify overlapping columns (besides merge keys)
    reddit_cols = set(reddit_grosses_df.columns) - {'show', 'week_start'}
    social_cols = set(social_signals_df.columns) - {'show', 'week_start'}
    overlapping_cols = reddit_cols & social_cols

    if overlapping_cols:
        logger.warning(f"  Overlapping columns (will suffix with _reddit/_social): {overlapping_cols}")

    # Merge with outer join to keep all observations
    logger.info(f"\nMerging on ['show', 'week_start'] with outer join...")

    merged = reddit_grosses_df.merge(
        social_signals_df,
        on=['show', 'week_start'],
        how='outer',
        suffixes=('_reddit', '_social'),
        indicator=True
    )

    # Log merge statistics
    merge_stats = merged['_merge'].value_counts()
    logger.info(f"\nMerge results:")
    logger.info(f"  Both sources: {merge_stats.get('both', 0)} rows")
    logger.info(f"  Reddit only: {merge_stats.get('left_only', 0)} rows")
    logger.info(f"  Social only: {merge_stats.get('right_only', 0)} rows")
    logger.info(f"  Total: {len(merged)} rows")

    # Drop merge indicator
    merged = merged.drop(columns=['_merge'])

    # Add availability flags
    logger.info(f"\nAdding availability flags...")

    # Reddit available if any Reddit metric is non-null
    reddit_metrics = [col for col in merged.columns if 'total_posts' in col or 'total_score' in col]
    if reddit_metrics:
        merged['has_reddit'] = merged[reddit_metrics[0]].notna().astype(int)
    else:
        merged['has_reddit'] = 0

    # Social available if any social metric is non-null
    social_metrics = [col for col in merged.columns if col.startswith('tt_') or col.startswith('ig_')]
    if social_metrics:
        merged['has_social_signals'] = merged[social_metrics[0]].notna().astype(int)
    else:
        merged['has_social_signals'] = 0

    # Grosses available
    if 'gross' in merged.columns:
        merged['has_grosses'] = merged['gross'].notna().astype(int)
    else:
        merged['has_grosses'] = 0

    # Sort by show and week
    merged = merged.sort_values(['show', 'week_start']).reset_index(drop=True)

    logger.info(f"\nAvailability:")
    logger.info(f"  Reddit: {merged['has_reddit'].sum()} rows ({merged['has_reddit'].mean()*100:.1f}%)")
    logger.info(f"  Social: {merged['has_social_signals'].sum()} rows ({merged['has_social_signals'].mean()*100:.1f}%)")
    logger.info(f"  Grosses: {merged['has_grosses'].sum()} rows ({merged['has_grosses'].mean()*100:.1f}%)")

    # Count rows with all three
    all_three = (
        (merged['has_reddit'] == 1) &
        (merged['has_social_signals'] == 1) &
        (merged['has_grosses'] == 1)
    ).sum()
    logger.info(f"  All three: {all_three} rows ({all_three/len(merged)*100:.1f}%)")

    return merged


def generate_metadata(
    merged_df: pd.DataFrame,
    reddit_path: str,
    social_path: str
) -> dict:
    """Generate metadata about the merged dataset."""
    metadata = {
        'created_at': datetime.now().isoformat(),
        'source_files': {
            'reddit_grosses': str(reddit_path),
            'social_signals': str(social_path)
        },
        'dimensions': {
            'n_rows': len(merged_df),
            'n_columns': len(merged_df.columns),
            'n_shows': merged_df['show'].nunique(),
            'date_range': {
                'min': str(merged_df['week_start'].min()),
                'max': str(merged_df['week_start'].max())
            }
        },
        'availability': {
            'reddit': {
                'n_rows': int(merged_df['has_reddit'].sum()),
                'pct': float(merged_df['has_reddit'].mean() * 100)
            },
            'social_signals': {
                'n_rows': int(merged_df['has_social_signals'].sum()),
                'pct': float(merged_df['has_social_signals'].mean() * 100)
            },
            'grosses': {
                'n_rows': int(merged_df['has_grosses'].sum()),
                'pct': float(merged_df['has_grosses'].mean() * 100)
            },
            'all_three': {
                'n_rows': int(((merged_df['has_reddit'] == 1) &
                               (merged_df['has_social_signals'] == 1) &
                               (merged_df['has_grosses'] == 1)).sum()),
                'pct': float(((merged_df['has_reddit'] == 1) &
                              (merged_df['has_social_signals'] == 1) &
                              (merged_df['has_grosses'] == 1)).mean() * 100)
            }
        },
        'shows': sorted(merged_df['show'].unique().tolist())
    }

    return metadata


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Merge all data sources into complete modeling dataset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic merge
    python -m public_signals.cli.merge_all_sources

    # Custom paths
    python -m public_signals.cli.merge_all_sources \
        --reddit-grosses data/merged/merged_reddit_grosses_panel.parquet \
        --social-signals public_signals/data/panel/weekly_social_signals.parquet \
        --output data/panel/complete_modeling_dataset.parquet

    # With feature engineering
    python -m public_signals.cli.merge_all_sources --engineer-features

Output:
    - Complete panel with all sources
    - Availability flags (has_reddit, has_social_signals, has_grosses)
    - Metadata JSON with coverage statistics
        """
    )

    parser.add_argument(
        '--reddit-grosses',
        type=str,
        default='data/merged/merged_reddit_grosses_panel.parquet',
        help='Path to Reddit+Grosses panel (default: data/merged/merged_reddit_grosses_panel.parquet)'
    )

    parser.add_argument(
        '--social-signals',
        type=str,
        default='public_signals/data/panel/weekly_social_signals.parquet',
        help='Path to Social Signals panel (default: public_signals/data/panel/weekly_social_signals.parquet)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='data/panel/complete_modeling_dataset.parquet',
        help='Path to save merged dataset (default: data/panel/complete_modeling_dataset.parquet)'
    )

    parser.add_argument(
        '--engineer-features',
        action='store_true',
        help='Engineer features (lags, deltas, etc.) on merged dataset'
    )

    parser.add_argument(
        '--lags',
        type=int,
        nargs='+',
        default=[1, 2, 4, 6],
        help='Lag periods for feature engineering (default: 1 2 4 6)'
    )

    args = parser.parse_args()

    # Load panels
    reddit_grosses = load_panel(args.reddit_grosses, "Reddit+Grosses")
    social_signals = load_panel(args.social_signals, "Social Signals")

    if reddit_grosses.empty and social_signals.empty:
        logger.error("Both panels are empty or failed to load. Cannot merge.")
        sys.exit(1)

    if reddit_grosses.empty:
        logger.warning("Reddit+Grosses panel is empty. Using Social Signals only.")
        merged = social_signals
    elif social_signals.empty:
        logger.warning("Social Signals panel is empty. Using Reddit+Grosses only.")
        merged = reddit_grosses
    else:
        # Merge both panels
        try:
            merged = merge_panels(reddit_grosses, social_signals)
        except Exception as e:
            logger.error(f"Error during merge: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    # Engineer features if requested
    if args.engineer_features:
        logger.info("\n" + "="*70)
        logger.info("ENGINEERING FEATURES")
        logger.info("="*70)

        # Identify all engagement metrics
        core_metrics = []

        # Reddit metrics
        reddit_cols = [col for col in merged.columns if any(x in col for x in [
            'total_posts', 'total_score', 'total_comments', 'unique_authors'
        ])]
        core_metrics.extend(reddit_cols)

        # TikTok metrics
        tt_cols = [col for col in merged.columns if col.startswith('tt_') and
                   any(x in col for x in ['posts', 'views', 'likes', 'comments'])]
        core_metrics.extend(tt_cols)

        # Instagram metrics
        ig_cols = [col for col in merged.columns if col.startswith('ig_') and
                   any(x in col for x in ['posts', 'likes', 'comments'])]
        core_metrics.extend(ig_cols)

        # Google Trends
        if 'gt_index' in merged.columns:
            core_metrics.append('gt_index')

        logger.info(f"Creating features for {len(core_metrics)} metrics")

        try:
            merged = create_model_ready_features(
                merged,
                core_metrics=core_metrics,
                lags=args.lags,
                leads=[4],
                add_deltas=True,
                add_rolling=True,
                rolling_window=3
            )
        except Exception as e:
            logger.error(f"Error engineering features: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    # Save outputs
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("\n" + "="*70)
    logger.info("SAVING OUTPUTS")
    logger.info("="*70)

    # Save Parquet
    try:
        merged.to_parquet(output_path, index=False)
        logger.info(f"✓ Saved Parquet: {output_path}")
    except Exception as e:
        logger.error(f"Error saving Parquet: {e}")
        sys.exit(1)

    # Save CSV preview
    try:
        csv_path = output_path.with_suffix('.csv')
        merged.head(1000).to_csv(csv_path, index=False)
        logger.info(f"✓ Saved CSV preview: {csv_path}")
    except Exception as e:
        logger.warning(f"Could not save CSV preview: {e}")

    # Save metadata
    try:
        metadata = generate_metadata(merged, args.reddit_grosses, args.social_signals)

        meta_path = output_path.with_name(output_path.stem + '_metadata.json')
        with open(meta_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"✓ Saved metadata: {meta_path}")
    except Exception as e:
        logger.warning(f"Could not save metadata: {e}")

    # Summary
    logger.info("\n" + "="*70)
    logger.info("COMPLETE")
    logger.info("="*70)
    logger.info(f"\nMerged dataset: {len(merged)} rows × {len(merged.columns)} columns")
    logger.info(f"Shows: {merged['show'].nunique()}")
    logger.info(f"Date range: {merged['week_start'].min()} to {merged['week_start'].max()}")
    logger.info(f"\nOutput: {output_path}")


if __name__ == '__main__':
    main()
