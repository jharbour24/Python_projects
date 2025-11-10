#!/usr/bin/env python3
"""
Time binning utilities for weekly aggregation.

Ensures consistent weekly binning across all data sources for panel analysis.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def to_week_start(
    ts: pd.Timestamp,
    week_start: str = "Mon"
) -> str:
    """
    Floor timestamp to start of week (Monday by default).

    Args:
        ts: Timestamp to floor
        week_start: Day of week ('Mon', 'Tue', ..., 'Sun')

    Returns:
        Week start date as 'YYYY-MM-DD' string

    Example:
        >>> to_week_start(pd.Timestamp('2024-01-03'))  # Wednesday
        '2024-01-01'  # Monday of that week
    """
    # Map week_start to pandas offset
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
    week_floor = ts.to_period(week_offsets[week_start]).to_timestamp()

    return week_floor.strftime('%Y-%m-%d')


def week_agg(
    df: pd.DataFrame,
    date_col: str,
    group_cols: List[str],
    agg_spec: Dict[str, Any],
    week_start: str = "Mon"
) -> pd.DataFrame:
    """
    Aggregate DataFrame to weekly level.

    Args:
        df: Input DataFrame
        date_col: Column containing dates/timestamps
        group_cols: Columns to group by (e.g., ['show'])
        agg_spec: Aggregation specification (e.g., {'value': 'sum', 'count': 'count'})
        week_start: Day to start week on

    Returns:
        Weekly aggregated DataFrame with 'week_start' column

    Example:
        >>> df = pd.DataFrame({
        ...     'date': pd.date_range('2024-01-01', periods=14, freq='D'),
        ...     'show': 'ShowA',
        ...     'views': range(14)
        ... })
        >>> weekly = week_agg(df, 'date', ['show'], {'views': 'sum'})
        >>> len(weekly)
        2  # Two weeks of data
    """
    df = df.copy()

    # Ensure date column is datetime
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df[date_col] = pd.to_datetime(df[date_col])

    # Add week_start column
    df['week_start'] = df[date_col].apply(lambda x: to_week_start(x, week_start))

    # Group and aggregate
    group_keys = group_cols + ['week_start']
    weekly = df.groupby(group_keys, as_index=False).agg(agg_spec)

    logger.info(f"Aggregated {len(df)} rows to {len(weekly)} weekly observations")
    logger.info(f"Date range: {weekly['week_start'].min()} to {weekly['week_start'].max()}")

    return weekly


def generate_week_range(
    start_date: str,
    end_date: str,
    week_start: str = "Mon"
) -> List[str]:
    """
    Generate list of week_start dates in range.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        week_start: Day to start week on

    Returns:
        List of week_start dates as strings

    Example:
        >>> weeks = generate_week_range('2024-01-01', '2024-01-31')
        >>> len(weeks)
        5  # 5 weeks in January 2024
    """
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)

    # Floor start to week start
    start_week = pd.Timestamp(to_week_start(start, week_start))

    # Generate all weeks
    weeks = []
    current = start_week

    while current <= end:
        weeks.append(current.strftime('%Y-%m-%d'))
        current += pd.Timedelta(weeks=1)

    logger.debug(f"Generated {len(weeks)} weeks from {start_date} to {end_date}")

    return weeks


def fill_missing_weeks(
    df: pd.DataFrame,
    start_date: str,
    end_date: str,
    id_cols: List[str],
    week_start: str = "Mon"
) -> pd.DataFrame:
    """
    Fill in missing weeks with NaN for complete time series.

    Useful for ensuring balanced panel data where some shows may have
    missing weeks due to lack of activity.

    Args:
        df: DataFrame with 'week_start' column
        start_date: Start of date range
        end_date: End of date range
        id_cols: ID columns (e.g., ['show'])
        week_start: Day to start week on

    Returns:
        DataFrame with all weeks filled in for each ID

    Example:
        >>> df = pd.DataFrame({
        ...     'show': ['A', 'A'],
        ...     'week_start': ['2024-01-01', '2024-01-15'],
        ...     'value': [10, 20]
        ... })
        >>> filled = fill_missing_weeks(df, '2024-01-01', '2024-01-31', ['show'])
        >>> len(filled)
        5  # A now has all 5 weeks, with NaN for missing
    """
    # Generate all weeks
    all_weeks = generate_week_range(start_date, end_date, week_start)

    # Get all unique IDs
    id_values = df[id_cols].drop_duplicates()

    # Create complete index (Cartesian product of IDs × weeks)
    complete_index = []
    for _, id_row in id_values.iterrows():
        for week in all_weeks:
            row = id_row.to_dict()
            row['week_start'] = week
            complete_index.append(row)

    complete_df = pd.DataFrame(complete_index)

    # Merge with original data
    filled = complete_df.merge(df, on=id_cols + ['week_start'], how='left')

    logger.info(f"Filled panel: {len(complete_df)} total rows, {(filled.isna().sum().sum() / filled.size * 100):.1f}% missing")

    return filled
