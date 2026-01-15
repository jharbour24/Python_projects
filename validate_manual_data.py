#!/usr/bin/env python3
"""
Validate manually collected producer and Tony Award data.
"""

import sys
from pathlib import Path
import pandas as pd
from utils import setup_logger

logger = setup_logger(__name__)


def validate_producer_counts(file_path: str) -> tuple:
    """
    Validate producer counts data.

    Returns:
        (is_valid, error_messages)
    """
    logger.info(f"\nValidating producer counts: {file_path}")

    errors = []

    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        return False, [f"Error reading file: {e}"]

    # Check required columns
    required_cols = ['show_id', 'show_name', 'num_total_producers']
    optional_cols = ['ibdb_url', 'num_lead_producers', 'num_co_producers', 'scrape_status', 'scrape_notes']

    for col in required_cols:
        if col not in df.columns:
            errors.append(f"Missing required column: {col}")

    # Validate numeric columns
    numeric_cols = ['num_lead_producers', 'num_co_producers', 'num_total_producers']

    for col in numeric_cols:
        if col in df.columns:
            # Check for non-numeric values (excluding NaN)
            non_numeric = df[col].dropna().apply(lambda x: not str(x).replace('.', '').isdigit())
            if non_numeric.any():
                invalid_rows = df[non_numeric].index.tolist()
                errors.append(f"Column '{col}' has non-numeric values in rows: {invalid_rows[:10]}")

            # Check for unreasonable values
            numeric_vals = pd.to_numeric(df[col], errors='coerce')
            if (numeric_vals > 100).any():
                high_rows = df[numeric_vals > 100].index.tolist()
                errors.append(f"Column '{col}' has suspiciously high values (>100) in rows: {high_rows}")

            if (numeric_vals < 0).any():
                neg_rows = df[numeric_vals < 0].index.tolist()
                errors.append(f"Column '{col}' has negative values in rows: {neg_rows}")

    # Validate logical consistency
    if all(c in df.columns for c in ['num_lead_producers', 'num_co_producers', 'num_total_producers']):
        for idx, row in df.iterrows():
            try:
                lead = float(row['num_lead_producers']) if pd.notna(row['num_lead_producers']) else 0
                co = float(row['num_co_producers']) if pd.notna(row['num_co_producers']) else 0
                total = float(row['num_total_producers']) if pd.notna(row['num_total_producers']) else 0

                if total > 0 and total < (lead + co):
                    errors.append(f"Row {idx}: total ({total}) < lead ({lead}) + co ({co})")
            except:
                pass  # Already caught by non-numeric check

    # Validate URLs if present
    if 'ibdb_url' in df.columns:
        non_empty_urls = df['ibdb_url'].dropna()
        invalid_urls = non_empty_urls[~non_empty_urls.str.contains('ibdb.com', case=False, na=False)]
        if len(invalid_urls) > 0:
            errors.append(f"Found {len(invalid_urls)} URLs that don't appear to be IBDB links")

    # Summary stats
    logger.info(f"\n  Total shows: {len(df)}")
    if 'num_total_producers' in df.columns:
        filled = df['num_total_producers'].notna().sum()
        logger.info(f"  Shows with producer counts: {filled} ({filled/len(df)*100:.1f}%)")

        if filled > 0:
            logger.info(f"  Average total producers: {df['num_total_producers'].mean():.1f}")
            logger.info(f"  Range: {df['num_total_producers'].min():.0f} - {df['num_total_producers'].max():.0f}")

    if errors:
        logger.error(f"\n  ✗ Validation failed with {len(errors)} errors:")
        for error in errors[:20]:  # Show first 20 errors
            logger.error(f"    - {error}")
        return False, errors
    else:
        logger.info(f"  ✓ Producer counts validation passed!")
        return True, []


def validate_tony_outcomes(file_path: str) -> tuple:
    """
    Validate Tony outcomes data.

    Returns:
        (is_valid, error_messages)
    """
    logger.info(f"\nValidating Tony outcomes: {file_path}")

    errors = []

    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        return False, [f"Error reading file: {e}"]

    # Check required columns
    required_cols = ['show_id', 'show_name', 'tony_win']

    for col in required_cols:
        if col not in df.columns:
            errors.append(f"Missing required column: {col}")

    # Validate tony_win column
    if 'tony_win' in df.columns:
        non_empty = df['tony_win'].dropna()

        # Check for valid values (0 or 1)
        invalid_values = non_empty[~non_empty.isin([0, 1, '0', '1'])]
        if len(invalid_values) > 0:
            invalid_rows = invalid_values.index.tolist()
            errors.append(f"Column 'tony_win' has invalid values (must be 0 or 1) in rows: {invalid_rows[:10]}")

    # Validate tony_year if present
    if 'tony_year' in df.columns:
        non_empty_years = df['tony_year'].dropna()

        # Check for reasonable year range
        numeric_years = pd.to_numeric(non_empty_years, errors='coerce')
        invalid_years = numeric_years[(numeric_years < 2010) | (numeric_years > 2025)]
        if len(invalid_years) > 0:
            errors.append(f"Column 'tony_year' has years outside 2010-2025 range")

    # Summary stats
    logger.info(f"\n  Total shows: {len(df)}")
    if 'tony_win' in df.columns:
        filled = df['tony_win'].notna().sum()
        logger.info(f"  Shows with Tony outcome: {filled} ({filled/len(df)*100:.1f}%)")

        if filled > 0:
            winners = (df['tony_win'] == 1).sum() + (df['tony_win'] == '1').sum()
            logger.info(f"  Tony winners: {winners}")
            logger.info(f"  Non-winners: {filled - winners}")

    if errors:
        logger.error(f"\n  ✗ Validation failed with {len(errors)} errors:")
        for error in errors[:20]:
            logger.error(f"    - {error}")
        return False, errors
    else:
        logger.info(f"  ✓ Tony outcomes validation passed!")
        return True, []


def main():
    """Main validation entry point."""
    logger.info("="*70)
    logger.info("MANUAL DATA VALIDATION")
    logger.info("="*70)

    # Check for data files
    producer_files = [
        'data/show_producer_counts_manual.csv',
        'data/show_producer_counts_ibdb.csv',
        'data/templates/producer_counts_template.csv',
    ]

    tony_files = [
        'data/tony_outcomes_manual.csv',
        'data/tony_outcomes.csv',
        'data/templates/tony_outcomes_template.csv',
    ]

    all_valid = True

    # Validate producer files
    for file_path in producer_files:
        if Path(file_path).exists():
            valid, errors = validate_producer_counts(file_path)
            all_valid = all_valid and valid
        else:
            logger.info(f"\n{file_path} - not found (skipping)")

    # Validate Tony files
    for file_path in tony_files:
        if Path(file_path).exists():
            valid, errors = validate_tony_outcomes(file_path)
            all_valid = all_valid and valid
        else:
            logger.info(f"\n{file_path} - not found (skipping)")

    logger.info("\n" + "="*70)
    if all_valid:
        logger.info("✓✓✓ ALL VALIDATIONS PASSED ✓✓✓")
        logger.info("Data is ready for analysis!")
    else:
        logger.error("✗✗✗ VALIDATION FAILURES ✗✗✗")
        logger.error("Please fix errors before running analysis")
    logger.info("="*70)

    return 0 if all_valid else 1


if __name__ == '__main__':
    sys.exit(main())
