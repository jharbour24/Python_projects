#!/usr/bin/env python3
"""
Weekly Aggregation & Canonical Schema Enforcement

Handles:
- Week binning (Monday start)
- Deduplication by post_id
- Source-specific aggregators (TikTok, Instagram, Google Trends)
- Canonical schema enforcement with JSON schema validation
"""

import pandas as pd
import numpy as np
import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from ..common.timebins import to_week_start

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Canonical Weekly Panel Schema
CANONICAL_SCHEMA = {
    "columns": [
        {"name": "show", "dtype": "object"},
        {"name": "week_start", "dtype": "object"},  # YYYY-MM-DD string
        {"name": "tt_posts", "dtype": "Int64", "nullable": True},
        {"name": "tt_sum_views", "dtype": "Int64", "nullable": True},
        {"name": "tt_sum_likes", "dtype": "Int64", "nullable": True},
        {"name": "tt_sum_comments", "dtype": "Int64", "nullable": True},
        {"name": "tt_sum_shares", "dtype": "Int64", "nullable": True},
        {"name": "tt_unique_hashtags", "dtype": "Int64", "nullable": True},
        {"name": "tt_posting_days", "dtype": "Int64", "nullable": True},
        {"name": "ig_posts", "dtype": "Int64", "nullable": True},
        {"name": "ig_sum_likes", "dtype": "Int64", "nullable": True},
        {"name": "ig_sum_comments", "dtype": "Int64", "nullable": True},
        {"name": "ig_unique_hashtags", "dtype": "Int64", "nullable": True},
        {"name": "ig_reel_ct", "dtype": "Int64", "nullable": True},
        {"name": "ig_posting_days", "dtype": "Int64", "nullable": True},
        {"name": "gt_index", "dtype": "float64", "nullable": True},
        {"name": "gt_is_partial", "dtype": "bool", "nullable": True},
        {"name": "scrape_run_at", "dtype": "object"}
    ]
}


def dedupe_posts(df: pd.DataFrame, id_col: str = "post_id") -> pd.DataFrame:
    """
    Deduplicate posts by post_id, keeping the most recent scrape.

    Args:
        df: DataFrame with posts
        id_col: Column name for post ID

    Returns:
        Deduplicated DataFrame

    Example:
        >>> df = dedupe_posts(df, id_col="post_id")
    """
    if df.empty or id_col not in df.columns:
        return df

    initial_count = len(df)

    # Sort by scrape time if available (most recent first)
    if 'scrape_run_at' in df.columns:
        df = df.sort_values('scrape_run_at', ascending=False)

    # Drop duplicates, keeping first (most recent)
    df = df.drop_duplicates(subset=[id_col], keep='first')

    removed = initial_count - len(df)
    if removed > 0:
        logger.info(f"  Removed {removed} duplicate posts")

    return df


def aggregate_tiktok_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate TikTok posts to weekly level.

    Args:
        df: DataFrame with columns: show, post_datetime, post_id, views, likes,
            comments, shares, hashtags

    Returns:
        Weekly DataFrame with schema:
        - show
        - week_start
        - tt_posts
        - tt_sum_views
        - tt_sum_likes
        - tt_sum_comments
        - tt_sum_shares
        - tt_unique_hashtags
        - tt_posting_days

    Example:
        >>> weekly = aggregate_tiktok_weekly(posts_df)
    """
    if df.empty:
        return pd.DataFrame(columns=[
            'show', 'week_start', 'tt_posts', 'tt_sum_views', 'tt_sum_likes',
            'tt_sum_comments', 'tt_sum_shares', 'tt_unique_hashtags', 'tt_posting_days'
        ])

    df = df.copy()

    # Deduplicate
    df = dedupe_posts(df, id_col='post_id')

    # Ensure datetime
    df['post_datetime'] = pd.to_datetime(df['post_datetime'])

    # Add week_start
    df['week_start'] = df['post_datetime'].apply(to_week_start)

    # Add date (for counting posting days)
    df['date'] = df['post_datetime'].dt.date

    # Aggregate numeric columns
    weekly = df.groupby(['show', 'week_start']).agg({
        'post_id': 'count',
        'views': 'sum',
        'likes': 'sum',
        'comments': 'sum',
        'shares': 'sum',
        'date': 'nunique'  # Posting days
    }).reset_index()

    # Count unique hashtags per week
    hashtag_counts = df.groupby(['show', 'week_start']).apply(
        lambda x: len(set([tag for tags in x['hashtags'] for tag in tags]))
    ).reset_index(name='unique_hashtags')

    # Merge
    weekly = weekly.merge(hashtag_counts, on=['show', 'week_start'], how='left')

    # Rename columns
    weekly = weekly.rename(columns={
        'post_id': 'tt_posts',
        'views': 'tt_sum_views',
        'likes': 'tt_sum_likes',
        'comments': 'tt_sum_comments',
        'shares': 'tt_sum_shares',
        'unique_hashtags': 'tt_unique_hashtags',
        'date': 'tt_posting_days'
    })

    logger.info(f"TikTok aggregated to {len(weekly)} show-weeks")

    return weekly


def aggregate_instagram_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate Instagram posts to weekly level.

    Args:
        df: DataFrame with columns: show, post_datetime, post_id, likes, comments,
            hashtags, is_reel

    Returns:
        Weekly DataFrame with schema:
        - show
        - week_start
        - ig_posts
        - ig_sum_likes
        - ig_sum_comments
        - ig_unique_hashtags
        - ig_reel_ct
        - ig_posting_days

    Example:
        >>> weekly = aggregate_instagram_weekly(posts_df)
    """
    if df.empty:
        return pd.DataFrame(columns=[
            'show', 'week_start', 'ig_posts', 'ig_sum_likes', 'ig_sum_comments',
            'ig_unique_hashtags', 'ig_reel_ct', 'ig_posting_days'
        ])

    df = df.copy()

    # Deduplicate
    df = dedupe_posts(df, id_col='post_id')

    # Ensure datetime
    df['post_datetime'] = pd.to_datetime(df['post_datetime'])

    # Add week_start
    df['week_start'] = df['post_datetime'].apply(to_week_start)

    # Add date
    df['date'] = df['post_datetime'].dt.date

    # Aggregate (likes/comments may be null)
    weekly = df.groupby(['show', 'week_start']).agg({
        'post_id': 'count',
        'likes': lambda x: x.sum() if x.notna().any() else pd.NA,
        'comments': lambda x: x.sum() if x.notna().any() else pd.NA,
        'is_reel': 'sum',
        'date': 'nunique'
    }).reset_index()

    # Count unique hashtags per week
    hashtag_counts = df.groupby(['show', 'week_start']).apply(
        lambda x: len(set([tag for tags in x['hashtags'] for tag in tags]))
    ).reset_index(name='unique_hashtags')

    # Merge
    weekly = weekly.merge(hashtag_counts, on=['show', 'week_start'], how='left')

    # Rename columns
    weekly = weekly.rename(columns={
        'post_id': 'ig_posts',
        'likes': 'ig_sum_likes',
        'comments': 'ig_sum_comments',
        'unique_hashtags': 'ig_unique_hashtags',
        'is_reel': 'ig_reel_ct',
        'date': 'ig_posting_days'
    })

    logger.info(f"Instagram aggregated to {len(weekly)} show-weeks")

    return weekly


def aggregate_google_trends_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate Google Trends to weekly level.

    Google Trends data is already weekly, but may have multiple queries per show.
    This aggregates across queries.

    Args:
        df: DataFrame with columns: show, week_start, gt_index, is_partial

    Returns:
        Weekly DataFrame with schema:
        - show
        - week_start
        - gt_index (average across queries)
        - gt_is_partial (True if any query was partial)

    Example:
        >>> weekly = aggregate_google_trends_weekly(trends_df)
    """
    if df.empty:
        return pd.DataFrame(columns=[
            'show', 'week_start', 'gt_index', 'gt_is_partial'
        ])

    df = df.copy()

    # Aggregate across queries
    weekly = df.groupby(['show', 'week_start']).agg({
        'gt_index': 'mean',  # Average interest across queries
        'is_partial': 'any'   # Flag if any query was partial
    }).reset_index()

    # Rename
    weekly = weekly.rename(columns={'is_partial': 'gt_is_partial'})

    logger.info(f"Google Trends aggregated to {len(weekly)} show-weeks")

    return weekly


def enforce_canonical_schema(df: pd.DataFrame, scrape_timestamp: Optional[str] = None) -> pd.DataFrame:
    """
    Enforce canonical schema on weekly panel.

    Ensures:
    - All required columns present
    - Correct column order
    - Correct dtypes
    - Fills missing columns with NA

    Args:
        df: Input DataFrame
        scrape_timestamp: Timestamp of scrape run (ISO format)

    Returns:
        DataFrame with canonical schema

    Example:
        >>> df = enforce_canonical_schema(df, scrape_timestamp="2025-01-10T12:00:00")
    """
    # Get canonical column order
    canonical_cols = [col['name'] for col in CANONICAL_SCHEMA['columns']]

    # Add missing columns
    for col_spec in CANONICAL_SCHEMA['columns']:
        col_name = col_spec['name']
        if col_name not in df.columns:
            df[col_name] = pd.NA

    # Add scrape timestamp
    if scrape_timestamp is None:
        scrape_timestamp = datetime.now().isoformat()

    df['scrape_run_at'] = scrape_timestamp

    # Reorder columns
    df = df[canonical_cols]

    # Convert dtypes
    for col_spec in CANONICAL_SCHEMA['columns']:
        col_name = col_spec['name']
        dtype = col_spec['dtype']

        if dtype == 'Int64':
            df[col_name] = pd.to_numeric(df[col_name], errors='coerce').astype('Int64')
        elif dtype == 'float64':
            df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
        elif dtype == 'bool':
            df[col_name] = df[col_name].astype('bool')
        elif dtype == 'object':
            df[col_name] = df[col_name].astype(str)

    logger.info(f"Schema enforced: {len(df)} rows, {len(df.columns)} columns")

    return df


def validate_schema(df: pd.DataFrame) -> tuple[bool, List[str]]:
    """
    Validate DataFrame against canonical schema.

    Args:
        df: DataFrame to validate

    Returns:
        Tuple of (is_valid, error_messages)

    Example:
        >>> is_valid, errors = validate_schema(df)
        >>> if not is_valid:
        ...     for err in errors:
        ...         print(f"Error: {err}")
    """
    errors = []

    # Check columns exist
    canonical_cols = [col['name'] for col in CANONICAL_SCHEMA['columns']]
    missing_cols = set(canonical_cols) - set(df.columns)

    if missing_cols:
        errors.append(f"Missing columns: {missing_cols}")

    # Check column order
    if list(df.columns) != canonical_cols:
        errors.append("Column order doesn't match canonical schema")

    # Check dtypes
    for col_spec in CANONICAL_SCHEMA['columns']:
        col_name = col_spec['name']
        expected_dtype = col_spec['dtype']

        if col_name in df.columns:
            actual_dtype = str(df[col_name].dtype)

            # Flexible dtype checking
            if expected_dtype == 'Int64' and actual_dtype not in ['Int64', 'int64']:
                errors.append(f"Column {col_name}: expected {expected_dtype}, got {actual_dtype}")
            elif expected_dtype == 'float64' and not actual_dtype.startswith('float'):
                errors.append(f"Column {col_name}: expected {expected_dtype}, got {actual_dtype}")
            elif expected_dtype == 'bool' and actual_dtype != 'bool':
                errors.append(f"Column {col_name}: expected {expected_dtype}, got {actual_dtype}")

    is_valid = len(errors) == 0

    return is_valid, errors


def save_weekly_panel(
    df: pd.DataFrame,
    output_path: str,
    validate: bool = True
) -> Path:
    """
    Save weekly panel with validation.

    Args:
        df: Weekly panel DataFrame
        output_path: Path to save (Parquet)
        validate: Whether to validate schema before saving

    Returns:
        Path to saved file

    Raises:
        ValueError: If validation fails

    Example:
        >>> save_weekly_panel(df, "data/panel/weekly_social_signals.parquet")
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Validate schema
    if validate:
        is_valid, errors = validate_schema(df)

        if not is_valid:
            error_msg = "\n".join(errors)
            raise ValueError(f"Schema validation failed:\n{error_msg}")

    # Save Parquet
    df.to_parquet(output_file, index=False)
    logger.info(f"✓ Saved weekly panel: {output_file}")

    # Save CSV preview (first 1000 rows)
    csv_file = output_file.with_suffix('.csv')
    df.head(1000).to_csv(csv_file, index=False)
    logger.info(f"✓ Saved CSV preview: {csv_file}")

    # Save schema JSON
    schema_file = output_file.parent / "weekly_panel_schema.json"
    with open(schema_file, 'w') as f:
        json.dump(CANONICAL_SCHEMA, f, indent=2)
    logger.info(f"✓ Saved schema: {schema_file}")

    return output_file


def merge_weekly_sources(
    tiktok_df: pd.DataFrame,
    instagram_df: pd.DataFrame,
    google_trends_df: pd.DataFrame,
    scrape_timestamp: Optional[str] = None
) -> pd.DataFrame:
    """
    Merge all weekly sources into canonical panel.

    Args:
        tiktok_df: Weekly TikTok data
        instagram_df: Weekly Instagram data
        google_trends_df: Weekly Google Trends data
        scrape_timestamp: Timestamp of scrape run

    Returns:
        Merged panel with canonical schema

    Example:
        >>> panel = merge_weekly_sources(tt_weekly, ig_weekly, gt_weekly)
    """
    # Get all unique show-week combinations
    all_dfs = []

    if not tiktok_df.empty:
        all_dfs.append(tiktok_df[['show', 'week_start']])
    if not instagram_df.empty:
        all_dfs.append(instagram_df[['show', 'week_start']])
    if not google_trends_df.empty:
        all_dfs.append(google_trends_df[['show', 'week_start']])

    if not all_dfs:
        logger.warning("No data from any source")
        return pd.DataFrame()

    # Create base panel
    panel = pd.concat(all_dfs, ignore_index=True).drop_duplicates()
    logger.info(f"Base panel: {len(panel)} unique show-weeks")

    # Merge each source
    if not tiktok_df.empty:
        panel = panel.merge(tiktok_df, on=['show', 'week_start'], how='left')
        logger.info(f"  + TikTok: {panel['tt_posts'].notna().sum()} rows with data")

    if not instagram_df.empty:
        panel = panel.merge(instagram_df, on=['show', 'week_start'], how='left')
        logger.info(f"  + Instagram: {panel['ig_posts'].notna().sum()} rows with data")

    if not google_trends_df.empty:
        panel = panel.merge(google_trends_df, on=['show', 'week_start'], how='left')
        logger.info(f"  + Google Trends: {panel['gt_index'].notna().sum()} rows with data")

    # Enforce canonical schema
    panel = enforce_canonical_schema(panel, scrape_timestamp)

    # Sort
    panel = panel.sort_values(['show', 'week_start']).reset_index(drop=True)

    return panel
