#!/usr/bin/env python3
"""
Panel Feature Engineering for Modeling

Creates analytics-ready features:
- Lags (e.g., _lag4 for advance purchase hypothesis)
- Leads (placebo tests)
- Deltas (week-over-week changes)
- Rolling statistics (3-week sums/means)
- Z-score standardization
"""

import pandas as pd
import numpy as np
import logging
from typing import List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def make_lags(
    df: pd.DataFrame,
    cols: List[str],
    lags: List[int] = [1, 2, 4, 6],
    group_col: str = "show",
    time_col: str = "week_start"
) -> pd.DataFrame:
    """
    Create lagged variables within each group.

    Args:
        df: Panel DataFrame
        cols: Columns to lag
        lags: List of lag periods (in weeks)
        group_col: Grouping column (typically 'show')
        time_col: Time column (must be sortable)

    Returns:
        DataFrame with additional _lag{n} columns

    Example:
        >>> df = make_lags(df, ['tt_sum_views', 'ig_sum_likes'], lags=[1, 2, 4])
        >>> # Creates: tt_sum_views_lag1, tt_sum_views_lag2, tt_sum_views_lag4, etc.
    """
    df = df.copy()

    # Sort by group and time
    df = df.sort_values([group_col, time_col]).reset_index(drop=True)

    logger.info(f"Creating lags: {lags} for {len(cols)} columns")

    for col in cols:
        if col not in df.columns:
            logger.warning(f"Column {col} not found, skipping")
            continue

        for lag in lags:
            lag_col_name = f"{col}_lag{lag}"
            df[lag_col_name] = df.groupby(group_col)[col].shift(lag)

            logger.debug(f"  {lag_col_name}: {df[lag_col_name].notna().sum()} non-null values")

    logger.info(f"✓ Created {len(cols) * len(lags)} lag features")

    return df


def make_leads(
    df: pd.DataFrame,
    cols: List[str],
    leads: List[int] = [4],
    group_col: str = "show",
    time_col: str = "week_start"
) -> pd.DataFrame:
    """
    Create lead variables for placebo tests.

    Leads look into the future - useful for testing whether future values
    "predict" current outcomes (they shouldn't in a causal model).

    Args:
        df: Panel DataFrame
        cols: Columns to lead
        leads: List of lead periods (in weeks)
        group_col: Grouping column
        time_col: Time column

    Returns:
        DataFrame with additional _lead{n} columns

    Example:
        >>> df = make_leads(df, ['tt_sum_views'], leads=[4])
        >>> # Creates: tt_sum_views_lead4 (placebo test)
    """
    df = df.copy()

    # Sort by group and time
    df = df.sort_values([group_col, time_col]).reset_index(drop=True)

    logger.info(f"Creating leads (placebo): {leads} for {len(cols)} columns")

    for col in cols:
        if col not in df.columns:
            logger.warning(f"Column {col} not found, skipping")
            continue

        for lead in leads:
            lead_col_name = f"{col}_lead{lead}"
            # Negative shift = forward in time
            df[lead_col_name] = df.groupby(group_col)[col].shift(-lead)

            logger.debug(f"  {lead_col_name}: {df[lead_col_name].notna().sum()} non-null values")

    logger.info(f"✓ Created {len(cols) * len(leads)} lead features")

    return df


def make_deltas(
    df: pd.DataFrame,
    cols: List[str],
    group_col: str = "show",
    time_col: str = "week_start"
) -> pd.DataFrame:
    """
    Create week-over-week change features.

    Creates both absolute (_delta) and percentage (_pct_change) deltas.

    Args:
        df: Panel DataFrame
        cols: Columns to compute deltas for
        group_col: Grouping column
        time_col: Time column

    Returns:
        DataFrame with additional _delta and _pct_change columns

    Example:
        >>> df = make_deltas(df, ['tt_sum_views'])
        >>> # Creates: tt_sum_views_delta, tt_sum_views_pct_change
    """
    df = df.copy()

    # Sort by group and time
    df = df.sort_values([group_col, time_col]).reset_index(drop=True)

    logger.info(f"Creating deltas for {len(cols)} columns")

    for col in cols:
        if col not in df.columns:
            logger.warning(f"Column {col} not found, skipping")
            continue

        # Absolute delta
        delta_col = f"{col}_delta"
        df[delta_col] = df.groupby(group_col)[col].diff()

        # Percentage change
        pct_col = f"{col}_pct_change"
        df[pct_col] = df.groupby(group_col)[col].pct_change()

        logger.debug(f"  {delta_col}: {df[delta_col].notna().sum()} non-null values")

    logger.info(f"✓ Created {len(cols) * 2} delta features")

    return df


def make_rolling_stats(
    df: pd.DataFrame,
    cols: List[str],
    window: int = 3,
    group_col: str = "show",
    time_col: str = "week_start"
) -> pd.DataFrame:
    """
    Create rolling window statistics.

    Creates rolling sum and mean over specified window.

    Args:
        df: Panel DataFrame
        cols: Columns to compute rolling stats for
        window: Window size in periods (default: 3 weeks)
        group_col: Grouping column
        time_col: Time column

    Returns:
        DataFrame with additional _roll{window} columns

    Example:
        >>> df = make_rolling_stats(df, ['tt_sum_views'], window=3)
        >>> # Creates: tt_sum_views_roll3_sum, tt_sum_views_roll3_mean
    """
    df = df.copy()

    # Sort by group and time
    df = df.sort_values([group_col, time_col]).reset_index(drop=True)

    logger.info(f"Creating rolling stats (window={window}) for {len(cols)} columns")

    for col in cols:
        if col not in df.columns:
            logger.warning(f"Column {col} not found, skipping")
            continue

        # Rolling sum
        roll_sum_col = f"{col}_roll{window}_sum"
        df[roll_sum_col] = df.groupby(group_col)[col].transform(
            lambda x: x.rolling(window, min_periods=1).sum()
        )

        # Rolling mean
        roll_mean_col = f"{col}_roll{window}_mean"
        df[roll_mean_col] = df.groupby(group_col)[col].transform(
            lambda x: x.rolling(window, min_periods=1).mean()
        )

        logger.debug(f"  {roll_sum_col}: {df[roll_sum_col].notna().sum()} non-null values")

    logger.info(f"✓ Created {len(cols) * 2} rolling features")

    return df


def standardize(
    df: pd.DataFrame,
    cols: List[str],
    method: str = "zscore"
) -> pd.DataFrame:
    """
    Standardize features across the panel.

    Args:
        df: Panel DataFrame
        cols: Columns to standardize
        method: Standardization method ('zscore' or 'minmax')

    Returns:
        DataFrame with additional _z or _scaled columns

    Example:
        >>> df = standardize(df, ['tt_sum_views', 'ig_sum_likes'])
        >>> # Creates: tt_sum_views_z, ig_sum_likes_z
    """
    df = df.copy()

    if method == "zscore":
        suffix = "_z"
        logger.info(f"Creating z-scores for {len(cols)} columns")

        for col in cols:
            if col not in df.columns:
                logger.warning(f"Column {col} not found, skipping")
                continue

            z_col = f"{col}{suffix}"
            mean = df[col].mean()
            std = df[col].std()

            if std > 0:
                df[z_col] = (df[col] - mean) / std
            else:
                df[z_col] = 0.0

            logger.debug(f"  {z_col}: mean={df[z_col].mean():.3f}, std={df[z_col].std():.3f}")

    elif method == "minmax":
        suffix = "_scaled"
        logger.info(f"Creating min-max scaled features for {len(cols)} columns")

        for col in cols:
            if col not in df.columns:
                logger.warning(f"Column {col} not found, skipping")
                continue

            scaled_col = f"{col}{suffix}"
            min_val = df[col].min()
            max_val = df[col].max()

            if max_val > min_val:
                df[scaled_col] = (df[col] - min_val) / (max_val - min_val)
            else:
                df[scaled_col] = 0.0

            logger.debug(f"  {scaled_col}: min={df[scaled_col].min():.3f}, max={df[scaled_col].max():.3f}")

    else:
        raise ValueError(f"Unknown standardization method: {method}")

    logger.info(f"✓ Created {len(cols)} standardized features")

    return df


def create_model_ready_features(
    df: pd.DataFrame,
    core_metrics: Optional[List[str]] = None,
    lags: List[int] = [1, 2, 4, 6],
    leads: List[int] = [4],
    add_deltas: bool = True,
    add_rolling: bool = True,
    rolling_window: int = 3,
    standardize_cols: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Create all model-ready features in one pass.

    Args:
        df: Weekly panel DataFrame
        core_metrics: Core metric columns to engineer features for
                     (default: TikTok and Instagram engagement metrics)
        lags: Lag periods to create
        leads: Lead periods for placebo tests
        add_deltas: Whether to add delta features
        add_rolling: Whether to add rolling statistics
        rolling_window: Window size for rolling stats
        standardize_cols: Columns to standardize (if None, uses core_metrics)

    Returns:
        DataFrame with all engineered features

    Example:
        >>> model_df = create_model_ready_features(weekly_df)
    """
    if core_metrics is None:
        core_metrics = [
            'tt_sum_views',
            'tt_sum_likes',
            'tt_sum_comments',
            'tt_posts',
            'ig_sum_likes',
            'ig_sum_comments',
            'ig_posts',
            'gt_index'
        ]

    # Filter to metrics that exist in df
    existing_metrics = [col for col in core_metrics if col in df.columns]

    if not existing_metrics:
        logger.warning("No core metrics found in DataFrame")
        return df

    logger.info(f"\nCreating model-ready features for {len(existing_metrics)} metrics")
    logger.info(f"Metrics: {existing_metrics}")

    df = df.copy()

    # 1. Lags
    df = make_lags(df, existing_metrics, lags=lags)

    # 2. Leads (placebo)
    df = make_leads(df, existing_metrics, leads=leads)

    # 3. Deltas
    if add_deltas:
        df = make_deltas(df, existing_metrics)

    # 4. Rolling stats
    if add_rolling:
        df = make_rolling_stats(df, existing_metrics, window=rolling_window)

    # 5. Standardization
    if standardize_cols is None:
        # Standardize core metrics and their lags
        standardize_cols = existing_metrics.copy()
        for metric in existing_metrics:
            for lag in lags:
                standardize_cols.append(f"{metric}_lag{lag}")

    # Filter to columns that exist
    standardize_cols = [col for col in standardize_cols if col in df.columns]

    if standardize_cols:
        df = standardize(df, standardize_cols, method="zscore")

    logger.info(f"\n✓ Model-ready dataset: {len(df)} rows, {len(df.columns)} columns")

    return df


def get_feature_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Get summary statistics for engineered features.

    Args:
        df: DataFrame with engineered features

    Returns:
        Summary DataFrame

    Example:
        >>> summary = get_feature_summary(model_df)
        >>> print(summary)
    """
    # Identify feature types
    lag_cols = [col for col in df.columns if '_lag' in col]
    lead_cols = [col for col in df.columns if '_lead' in col]
    delta_cols = [col for col in df.columns if '_delta' in col or '_pct_change' in col]
    roll_cols = [col for col in df.columns if '_roll' in col]
    z_cols = [col for col in df.columns if '_z' in col]

    summary = pd.DataFrame({
        'feature_type': ['lags', 'leads', 'deltas', 'rolling', 'z_scores'],
        'count': [len(lag_cols), len(lead_cols), len(delta_cols), len(roll_cols), len(z_cols)]
    })

    return summary
