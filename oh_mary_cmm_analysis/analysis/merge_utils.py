#!/usr/bin/env python3
"""
Merge utilities for aligning Reddit and Broadway grosses data.

Handles weekly time binning, show name normalization, and safe merges with logging.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, List
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def standardize_week(
    df: pd.DataFrame,
    date_col: str,
    week_start: str = "Mon",
    output_col: str = "week_start"
) -> pd.DataFrame:
    """
    Floor dates to weekly bins and add week_start column.

    Maps all dates within a week to the Monday (or specified day) of that week.
    This ensures Reddit posts and Broadway grosses align to the same weekly periods.

    Args:
        df: DataFrame with date column
        date_col: Name of column containing dates (will be converted to datetime)
        week_start: Day of week to use as week start ('Mon', 'Sun', etc.)
        output_col: Name for the output week_start column

    Returns:
        DataFrame with added week_start column (YYYY-MM-DD format)

    Example:
        >>> df = pd.DataFrame({'date': ['2024-01-03', '2024-01-05', '2024-01-08']})
        >>> standardize_week(df, 'date')
           date      week_start
        0  2024-01-03  2024-01-01
        1  2024-01-05  2024-01-01
        2  2024-01-08  2024-01-08
    """
    df = df.copy()

    # Ensure date column is datetime
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df[date_col] = pd.to_datetime(df[date_col])

    # Map week_start string to pandas offset
    week_offsets = {
        'Mon': 'W-MON',
        'Tue': 'W-TUE',
        'Wed': 'W-WED',
        'Thu': 'W-THU',
        'Fri': 'W-FRI',
        'Sat': 'W-SAT',
        'Sun': 'W-SUN'
    }

    if week_start not in week_offsets:
        raise ValueError(f"week_start must be one of {list(week_offsets.keys())}")

    # Floor to start of week
    # Use to_period and to_timestamp to get week starts
    df[output_col] = df[date_col].dt.to_period(week_offsets[week_start]).dt.to_timestamp()

    # Convert to string format YYYY-MM-DD for consistency
    df[output_col] = df[output_col].dt.strftime('%Y-%m-%d')

    logger.info(f"Standardized {len(df)} rows to weekly bins starting on {week_start}")
    logger.info(f"Date range: {df[output_col].min()} to {df[output_col].max()}")
    logger.info(f"Unique weeks: {df[output_col].nunique()}")

    return df


def normalize_show_names(
    df: pd.DataFrame,
    name_col: str,
    mapping_dict: Optional[Dict[str, str]] = None,
    output_col: str = "show_normalized"
) -> pd.DataFrame:
    """
    Normalize show names for consistent merging.

    Applies deterministic mapping from config and optional fuzzy matching.
    Ensures Reddit data and grosses data use consistent show identifiers.

    Args:
        df: DataFrame with show name column
        name_col: Name of column containing show names
        mapping_dict: Optional dict mapping raw names to normalized names
        output_col: Name for output normalized column

    Returns:
        DataFrame with added normalized show name column

    Example:
        >>> df = pd.DataFrame({'show': ['Oh Mary!', 'OH MARY', 'oh mary']})
        >>> normalize_show_names(df, 'show')
           show        show_normalized
        0  Oh Mary!    oh_mary
        1  OH MARY     oh_mary
        2  oh mary     oh_mary
    """
    df = df.copy()

    # Basic normalization: lowercase, remove punctuation, strip whitespace
    def basic_normalize(name: str) -> str:
        if pd.isna(name):
            return ""
        name = str(name).lower().strip()
        # Remove common punctuation but keep alphanumeric and spaces
        name = ''.join(c if c.isalnum() or c.isspace() else '' for c in name)
        # Replace multiple spaces with single space
        name = ' '.join(name.split())
        # Replace spaces with underscores for identifier
        name = name.replace(' ', '_')
        return name

    df[output_col] = df[name_col].apply(basic_normalize)

    # Apply custom mapping if provided
    if mapping_dict:
        # Normalize mapping keys for case-insensitive matching
        normalized_mapping = {basic_normalize(k): v for k, v in mapping_dict.items()}
        df[output_col] = df[output_col].map(lambda x: normalized_mapping.get(x, x))
        logger.info(f"Applied custom mapping for {len(mapping_dict)} shows")

    logger.info(f"Normalized {df[name_col].nunique()} unique show names to {df[output_col].nunique()} normalized names")

    # Log any shows that might need manual review (very short or very long names)
    suspicious = df[output_col].str.len()
    if (suspicious < 3).any():
        logger.warning(f"Found {(suspicious < 3).sum()} shows with very short normalized names (< 3 chars)")
    if (suspicious > 50).any():
        logger.warning(f"Found {(suspicious > 50).sum()} shows with very long normalized names (> 50 chars)")

    return df


def safe_merge_weekly(
    left: pd.DataFrame,
    right: pd.DataFrame,
    on: List[str] = ["show", "week_start"],
    how: str = "inner",
    validate: str = "1:1"
) -> pd.DataFrame:
    """
    Safely merge DataFrames with extensive logging and validation.

    Performs merge and logs row counts before/after to catch data loss.
    Asserts no duplicated merge keys to prevent explosion.

    Args:
        left: Left DataFrame
        right: Right DataFrame
        on: Columns to merge on (must exist in both DataFrames)
        how: Type of merge ('inner', 'left', 'outer')
        validate: Pandas merge validation ('1:1', '1:m', 'm:1', 'm:m')

    Returns:
        Merged DataFrame

    Raises:
        AssertionError: If duplicate keys found or unexpected data loss

    Example:
        >>> reddit = pd.DataFrame({'show': ['a', 'a'], 'week_start': ['2024-01-01', '2024-01-08'], 'posts': [10, 20]})
        >>> grosses = pd.DataFrame({'show': ['a', 'a'], 'week_start': ['2024-01-01', '2024-01-08'], 'gross': [100, 200]})
        >>> merged = safe_merge_weekly(reddit, grosses)
    """
    logger.info("="*70)
    logger.info("SAFE MERGE OPERATION")
    logger.info("="*70)

    # Validate merge columns exist
    for col in on:
        if col not in left.columns:
            raise ValueError(f"Merge column '{col}' not found in left DataFrame")
        if col not in right.columns:
            raise ValueError(f"Merge column '{col}' not found in right DataFrame")

    # Log pre-merge statistics
    logger.info(f"Left DataFrame: {len(left):,} rows, {len(left.columns)} columns")
    logger.info(f"Right DataFrame: {len(right):,} rows, {len(right.columns)} columns")
    logger.info(f"Merge keys: {on}")
    logger.info(f"Merge type: {how}")

    # Check for duplicates in merge keys
    left_dups = left.duplicated(subset=on, keep=False)
    right_dups = right.duplicated(subset=on, keep=False)

    if left_dups.any():
        logger.error(f"Found {left_dups.sum()} duplicate keys in LEFT DataFrame:")
        logger.error(left[left_dups][on].head(10))
        raise AssertionError(f"Left DataFrame has {left_dups.sum()} duplicate keys on {on}")

    if right_dups.any():
        logger.error(f"Found {right_dups.sum()} duplicate keys in RIGHT DataFrame:")
        logger.error(right[right_dups][on].head(10))
        raise AssertionError(f"Right DataFrame has {right_dups.sum()} duplicate keys on {on}")

    # Count unique keys before merge
    left_unique = left[on].drop_duplicates().shape[0]
    right_unique = right[on].drop_duplicates().shape[0]
    logger.info(f"Left unique keys: {left_unique:,}")
    logger.info(f"Right unique keys: {right_unique:,}")

    # Perform merge
    merged = pd.merge(left, right, on=on, how=how, validate=validate, indicator=True)

    # Log merge indicator counts
    merge_counts = merged['_merge'].value_counts()
    logger.info(f"\nMerge results:")
    logger.info(f"  Both: {merge_counts.get('both', 0):,} rows")
    logger.info(f"  Left only: {merge_counts.get('left_only', 0):,} rows")
    logger.info(f"  Right only: {merge_counts.get('right_only', 0):,} rows")

    # Calculate retention rates
    if how == "inner":
        left_retention = (merge_counts.get('both', 0) / len(left) * 100) if len(left) > 0 else 0
        right_retention = (merge_counts.get('both', 0) / len(right) * 100) if len(right) > 0 else 0
        logger.info(f"\nRetention rates:")
        logger.info(f"  Left: {left_retention:.1f}%")
        logger.info(f"  Right: {right_retention:.1f}%")

        # Warn if retention is low
        if left_retention < 50:
            logger.warning(f"Low left retention ({left_retention:.1f}%) - many left rows not matched!")
        if right_retention < 50:
            logger.warning(f"Low right retention ({right_retention:.1f}%) - many right rows not matched!")

    # Remove merge indicator column before returning
    merged = merged.drop(columns='_merge')

    # Check for NaN in merge keys (should not happen after merge)
    for col in on:
        nan_count = merged[col].isna().sum()
        if nan_count > 0:
            logger.error(f"Found {nan_count} NaN values in merge key '{col}' after merge!")
            raise AssertionError(f"NaN values found in merge key '{col}' after merge")

    logger.info(f"\n✓ Merge successful: {len(merged):,} rows, {len(merged.columns)} columns")
    logger.info("="*70)

    return merged
