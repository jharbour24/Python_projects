#!/usr/bin/env python3
"""
Build Model-Ready Social Signals Panel

Transforms weekly panel into modeling format with:
- Lagged predictors (e.g., _lag4 for advance purchase hypothesis)
- Lead variables (placebo tests)
- Deltas (week-over-week changes)
- Rolling statistics (3-week windows)
- Z-score standardization

Usage:
    python -m public_signals.cli.build_model_ready_social \
        --input data/panel/weekly_social_signals.parquet \
        --output data/panel/weekly_social_signals_model_ready.parquet
"""

import argparse
import pandas as pd
import logging
import sys
from pathlib import Path
import json

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.features.panel_features import create_model_ready_features, get_feature_summary

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Build model-ready social signals panel with engineered features",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Build with defaults (lags 1,2,4,6 + lead 4)
    python -m public_signals.cli.build_model_ready_social

    # Custom lags and leads
    python -m public_signals.cli.build_model_ready_social \
        --lags 1 2 4 --leads 2 4

    # Skip deltas and rolling
    python -m public_signals.cli.build_model_ready_social \
        --no-deltas --no-rolling

    # Custom metrics
    python -m public_signals.cli.build_model_ready_social \
        --metrics tt_sum_views tt_sum_likes ig_sum_likes

Output:
    - Parquet file with all engineered features
    - CSV preview (first 1000 rows)
    - JSON metadata with feature summary
        """
    )

    parser.add_argument(
        '--input',
        type=str,
        default='public_signals/data/panel/weekly_social_signals.parquet',
        help='Path to weekly panel Parquet file'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='public_signals/data/panel/weekly_social_signals_model_ready.parquet',
        help='Path to save model-ready Parquet file'
    )

    parser.add_argument(
        '--lags',
        type=int,
        nargs='+',
        default=[1, 2, 4, 6],
        help='Lag periods to create (default: 1 2 4 6)'
    )

    parser.add_argument(
        '--leads',
        type=int,
        nargs='+',
        default=[4],
        help='Lead periods for placebo tests (default: 4)'
    )

    parser.add_argument(
        '--no-deltas',
        action='store_true',
        help='Skip delta features'
    )

    parser.add_argument(
        '--no-rolling',
        action='store_true',
        help='Skip rolling statistics'
    )

    parser.add_argument(
        '--rolling-window',
        type=int,
        default=3,
        help='Window size for rolling stats (default: 3)'
    )

    parser.add_argument(
        '--metrics',
        type=str,
        nargs='+',
        default=None,
        help='Core metrics to engineer features for (default: all engagement metrics)'
    )

    args = parser.parse_args()

    # Load data
    input_path = Path(args.input)

    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    logger.info(f"Loading panel: {input_path}")

    try:
        df = pd.read_parquet(input_path)
        logger.info(f"  Loaded {len(df)} rows, {len(df.columns)} columns")
    except Exception as e:
        logger.error(f"Error loading panel: {e}")
        sys.exit(1)

    # Create features
    logger.info("\nEngineering features...")
    logger.info(f"  Lags: {args.lags}")
    logger.info(f"  Leads: {args.leads}")
    logger.info(f"  Deltas: {not args.no_deltas}")
    logger.info(f"  Rolling: {not args.no_rolling}")

    try:
        model_df = create_model_ready_features(
            df,
            core_metrics=args.metrics,
            lags=args.lags,
            leads=args.leads,
            add_deltas=not args.no_deltas,
            add_rolling=not args.no_rolling,
            rolling_window=args.rolling_window
        )
    except Exception as e:
        logger.error(f"Error creating features: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Get feature summary
    summary = get_feature_summary(model_df)

    logger.info("\nFeature Summary:")
    print(summary.to_string(index=False))

    # Save outputs
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"\nSaving outputs...")

    # Parquet (main format)
    try:
        model_df.to_parquet(output_path, index=False)
        logger.info(f"  ✓ Saved Parquet: {output_path}")
    except Exception as e:
        logger.error(f"Error saving Parquet: {e}")
        sys.exit(1)

    # CSV preview
    try:
        csv_path = output_path.with_name(output_path.stem + '_preview.csv')
        model_df.head(1000).to_csv(csv_path, index=False)
        logger.info(f"  ✓ Saved CSV preview: {csv_path}")
    except Exception as e:
        logger.warning(f"Could not save CSV preview: {e}")

    # Metadata JSON
    try:
        metadata = {
            'input_file': str(input_path),
            'output_file': str(output_path),
            'n_rows': len(model_df),
            'n_columns': len(model_df.columns),
            'lags': args.lags,
            'leads': args.leads,
            'add_deltas': not args.no_deltas,
            'add_rolling': not args.no_rolling,
            'rolling_window': args.rolling_window,
            'feature_summary': summary.to_dict(orient='records')
        }

        meta_path = output_path.with_name(output_path.stem + '_metadata.json')
        with open(meta_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"  ✓ Saved metadata: {meta_path}")
    except Exception as e:
        logger.warning(f"Could not save metadata: {e}")

    logger.info(f"\n✓ Model-ready dataset created")
    logger.info(f"  {len(model_df)} rows × {len(model_df.columns)} columns")
    logger.info(f"  Location: {output_path}")


if __name__ == '__main__':
    main()
