#!/usr/bin/env python3
"""
Social Panel Validation CLI

Validates weekly social signals panel for data quality:
- Coverage by source
- Anomaly detection
- Schema validation
- Timestamp checks

Usage:
    python -m public_signals.cli.validate_social_panel \
        --input data/panel/weekly_social_signals.parquet \
        --output data/panel/validation_report.json
"""

import argparse
import pandas as pd
import logging
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.quality.checks import (
    generate_validation_report,
    print_validation_summary,
    save_validation_report
)
from src.aggregation.weekly import validate_schema

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Validate social signals panel data quality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Validate panel with default thresholds
    python -m public_signals.cli.validate_social_panel

    # Custom input and output
    python -m public_signals.cli.validate_social_panel \
        --input data/panel/weekly_social_signals.parquet \
        --output data/panel/validation_report.json

    # Strict anomaly detection
    python -m public_signals.cli.validate_social_panel \
        --anomaly-threshold 3.0

Exit Codes:
    0: Validation passed (status OK)
    1: Validation failed (status ACTION_NEEDED)
    2: Error loading data or running validation
        """
    )

    parser.add_argument(
        '--input',
        type=str,
        default='public_signals/data/panel/weekly_social_signals.parquet',
        help='Path to weekly panel Parquet file (default: public_signals/data/panel/weekly_social_signals.parquet)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='public_signals/data/panel/validation_report.json',
        help='Path to save validation report JSON (default: public_signals/data/panel/validation_report.json)'
    )

    parser.add_argument(
        '--anomaly-threshold',
        type=float,
        default=5.0,
        help='Anomaly detection threshold (multiplier, default: 5.0)'
    )

    parser.add_argument(
        '--no-print',
        action='store_true',
        help='Suppress printing summary to console'
    )

    args = parser.parse_args()

    # Load data
    input_path = Path(args.input)

    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(2)

    logger.info(f"Loading panel: {input_path}")

    try:
        df = pd.read_parquet(input_path)
        logger.info(f"  Loaded {len(df)} rows, {len(df.columns)} columns")
    except Exception as e:
        logger.error(f"Error loading panel: {e}")
        sys.exit(2)

    # Generate validation report
    logger.info("\nRunning validation...")

    try:
        report = generate_validation_report(
            df,
            anomaly_threshold=args.anomaly_threshold,
            schema_validator=validate_schema
        )
    except Exception as e:
        logger.error(f"Error during validation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)

    # Print summary
    if not args.no_print:
        print_validation_summary(report)

    # Save report
    try:
        save_validation_report(report, args.output)
    except Exception as e:
        logger.error(f"Error saving report: {e}")
        sys.exit(2)

    # Exit with appropriate code
    if report.status == "OK":
        logger.info("✓ Validation passed")
        sys.exit(0)
    else:
        logger.warning("⚠ Validation flagged issues - review report")
        sys.exit(1)


if __name__ == '__main__':
    main()
