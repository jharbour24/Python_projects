#!/usr/bin/env python3
"""
Feature engineering for causal panel analysis.

Creates lagged variables, control flags, and temporal features for
Broadway marketing analysis.
"""

import pandas as pd
import numpy as np
from typing import List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def make_lags(
    df: pd.DataFrame,
    cols: List[str],
    group_col: str = "show",
    time_col: str = "week_start",
    lags: List[int] = [1, 2, 4, 6]
) -> pd.DataFrame:
    """
    Create lagged variables for panel data.

    Generates lag variables within each group (show), properly handling
    time ordering. Essential for testing whether Reddit buzz at t-k predicts
    grosses at t (advance purchase hypothesis).

    Args:
        df: Panel DataFrame
        cols: List of column names to lag
        group_col: Column defining panel groups (e.g., 'show')
        time_col: Column defining time periods (must be sortable)
        lags: List of lag periods (e.g., [1,2,4,6] for 1-week, 2-week, etc.)

    Returns:
        DataFrame with added lag columns named {col}_lag{n}

    Example:
        >>> df = pd.DataFrame({
        ...     'show': ['a','a','a'],
        ...     'week_start': ['2024-01-01','2024-01-08','2024-01-15'],
        ...     'engagement': [100, 150, 200]
        ... })
        >>> make_lags(df, ['engagement'], lags=[1,2])
           show  week_start  engagement  engagement_lag1  engagement_lag2
        0    a  2024-01-01         100              NaN              NaN
        1    a  2024-01-08         150            100.0              NaN
        2    a  2024-01-15         200            150.0            100.0
    """
    df = df.copy()

    # Ensure time column is proper type
    if not pd.api.types.is_datetime64_any_dtype(df[time_col]):
        df[time_col] = pd.to_datetime(df[time_col])

    # Sort by group and time
    df = df.sort_values([group_col, time_col])

    logger.info(f"Creating lags for {len(cols)} variables across {lags}")
    logger.info(f"Panel structure: {df[group_col].nunique()} groups, "
                f"{df.groupby(group_col)[time_col].count().mean():.1f} avg periods per group")

    lag_cols_created = []

    for col in cols:
        if col not in df.columns:
            logger.warning(f"Column '{col}' not found in DataFrame, skipping")
            continue

        for lag in lags:
            lag_col_name = f"{col}_lag{lag}"

            # Use groupby + shift to create lags within groups
            df[lag_col_name] = df.groupby(group_col)[col].shift(lag)

            lag_cols_created.append(lag_col_name)

            # Log missingness after lag creation
            missing_pct = df[lag_col_name].isna().sum() / len(df) * 100
            logger.info(f"  Created {lag_col_name}: {missing_pct:.1f}% missing (expected for first {lag} periods per show)")

    logger.info(f"✓ Created {len(lag_cols_created)} lag variables")

    return df


def capacity_constraint_flag(
    df: pd.DataFrame,
    cap_col: str = "capacity_pct",
    threshold: float = 0.98,
    output_col: str = "capacity_constrained"
) -> pd.DataFrame:
    """
    Flag weeks where show is near/at capacity (supply constrained).

    When a show is at/near capacity, additional demand (from social buzz) cannot
    translate to higher grosses - important control for causal interpretation.

    Args:
        df: DataFrame with capacity percentage
        cap_col: Column containing capacity percentage (0-1 or 0-100)
        threshold: Threshold for flagging as constrained (default 0.98 = 98%)
        output_col: Name for output binary flag column

    Returns:
        DataFrame with added capacity_constrained binary flag

    Example:
        >>> df = pd.DataFrame({'capacity_pct': [0.85, 0.95, 0.99, 1.0]})
        >>> capacity_constraint_flag(df, threshold=0.98)
           capacity_pct  capacity_constrained
        0          0.85                     0
        1          0.95                     0
        2          0.99                     1
        3          1.00                     1
    """
    df = df.copy()

    if cap_col not in df.columns:
        logger.warning(f"Capacity column '{cap_col}' not found - creating null flag")
        df[output_col] = np.nan
        return df

    # Handle both 0-1 and 0-100 scales
    cap_values = df[cap_col].dropna()
    if cap_values.max() > 1.5:  # Likely 0-100 scale
        logger.info(f"Detected 0-100 scale for {cap_col}, converting to 0-1")
        df[cap_col] = df[cap_col] / 100.0
        threshold_adj = threshold  # threshold already in 0-1 scale
    else:
        threshold_adj = threshold

    # Create binary flag
    df[output_col] = (df[cap_col] >= threshold_adj).astype(int)

    # Handle missing values
    df.loc[df[cap_col].isna(), output_col] = np.nan

    flagged_pct = (df[output_col] == 1).sum() / df[output_col].notna().sum() * 100 if df[output_col].notna().sum() > 0 else 0
    logger.info(f"Created capacity constraint flag: {flagged_pct:.1f}% of weeks flagged as constrained (threshold={threshold})")

    return df


def phase_flags(
    df: pd.DataFrame,
    show_col: str = "show",
    week_col: str = "week_start",
    perf_col: Optional[str] = None,
    opening_dates: Optional[dict] = None,
    preview_window_weeks: int = 4
) -> pd.DataFrame:
    """
    Create flags for preview vs post-opening phases.

    Preview periods often have different demand dynamics (discounted, press building).
    Post-opening is when reviews are public and word-of-mouth accelerates.

    Args:
        df: Panel DataFrame
        show_col: Column identifying shows
        week_col: Column with week dates
        perf_col: Optional column with performance numbers (can infer opening)
        opening_dates: Optional dict mapping show -> opening date
        preview_window_weeks: Number of weeks before opening to consider "preview"

    Returns:
        DataFrame with is_preview and is_post_opening binary flags

    Example:
        >>> df = pd.DataFrame({
        ...     'show': ['a','a','a','a'],
        ...     'week_start': ['2024-01-01','2024-01-08','2024-01-15','2024-01-22']
        ... })
        >>> opening_dates = {'a': '2024-01-15'}
        >>> phase_flags(df, opening_dates=opening_dates, preview_window_weeks=2)
           show  week_start  is_preview  is_post_opening
        0    a  2024-01-01           1                0
        1    a  2024-01-08           1                0
        2    a  2024-01-15           0                1
        3    a  2024-01-22           0                1
    """
    df = df.copy()

    # Ensure week_col is datetime
    if not pd.api.types.is_datetime64_any_dtype(df[week_col]):
        df[week_col] = pd.to_datetime(df[week_col])

    # Initialize flags as NaN (unknown)
    df['is_preview'] = np.nan
    df['is_post_opening'] = np.nan

    if opening_dates is None:
        logger.warning("No opening_dates provided - phase flags will be null")
        logger.warning("Consider providing opening_dates dict: {show_id: 'YYYY-MM-DD'}")
        return df

    # Convert opening dates to datetime
    opening_dates_dt = {k: pd.to_datetime(v) for k, v in opening_dates.items()}

    logger.info(f"Creating phase flags for {len(opening_dates)} shows with known opening dates")

    for show in df[show_col].unique():
        if show not in opening_dates_dt:
            logger.debug(f"No opening date for {show} - leaving flags as null")
            continue

        opening_date = opening_dates_dt[show]
        preview_start = opening_date - pd.Timedelta(weeks=preview_window_weeks)

        show_mask = df[show_col] == show

        # is_preview: weeks in the preview window before opening
        df.loc[show_mask & (df[week_col] >= preview_start) & (df[week_col] < opening_date), 'is_preview'] = 1
        df.loc[show_mask & ((df[week_col] < preview_start) | (df[week_col] >= opening_date)), 'is_preview'] = 0

        # is_post_opening: weeks on or after opening
        df.loc[show_mask & (df[week_col] >= opening_date), 'is_post_opening'] = 1
        df.loc[show_mask & (df[week_col] < opening_date), 'is_post_opening'] = 0

    preview_pct = (df['is_preview'] == 1).sum() / df['is_preview'].notna().sum() * 100 if df['is_preview'].notna().sum() > 0 else 0
    post_opening_pct = (df['is_post_opening'] == 1).sum() / df['is_post_opening'].notna().sum() * 100 if df['is_post_opening'].notna().sum() > 0 else 0

    logger.info(f"Phase distribution: {preview_pct:.1f}% preview, {post_opening_pct:.1f}% post-opening")
    logger.info(f"Unknown phases: {df['is_preview'].isna().sum()} rows")

    return df


def standardize_predictors(
    df: pd.DataFrame,
    cols: List[str],
    method: str = "z-score",
    by_group: Optional[str] = None
) -> pd.DataFrame:
    """
    Standardize predictor variables for regression.

    Standardization makes coefficients interpretable as "effect per SD change"
    and prevents numerical issues in mixed-effects models.

    Args:
        df: DataFrame with predictors
        cols: Columns to standardize
        method: 'z-score' (mean=0, std=1) or 'min-max' (0-1 range)
        by_group: Optional column to standardize within groups

    Returns:
        DataFrame with standardized columns (original column names, values replaced)

    Example:
        >>> df = pd.DataFrame({'x': [10, 20, 30], 'group': ['a', 'a', 'b']})
        >>> standardize_predictors(df, ['x'])
              x group
        0 -1.22     a
        1  0.00     a
        2  1.22     b
    """
    df = df.copy()

    if method not in ['z-score', 'min-max']:
        raise ValueError(f"method must be 'z-score' or 'min-max', got '{method}'")

    for col in cols:
        if col not in df.columns:
            logger.warning(f"Column '{col}' not found, skipping standardization")
            continue

        if by_group:
            # Standardize within groups
            if method == 'z-score':
                df[col] = df.groupby(by_group)[col].transform(lambda x: (x - x.mean()) / x.std())
            else:  # min-max
                df[col] = df.groupby(by_group)[col].transform(lambda x: (x - x.min()) / (x.max() - x.min()))

            logger.info(f"Standardized '{col}' within '{by_group}' using {method}")
        else:
            # Standardize globally
            if method == 'z-score':
                mean = df[col].mean()
                std = df[col].std()
                df[col] = (df[col] - mean) / std
            else:  # min-max
                min_val = df[col].min()
                max_val = df[col].max()
                df[col] = (df[col] - min_val) / (max_val - min_val)

            logger.info(f"Standardized '{col}' globally using {method}")

    return df
