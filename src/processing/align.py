"""
Timeline alignment utilities for Broadway shows.
Aligns data by relative timeline (weeks from opening).
"""

from datetime import datetime, timedelta
from typing import Optional, Union
import pandas as pd
import numpy as np


def align_relative_timeline(
    opening_date: Union[str, datetime],
    df: pd.DataFrame,
    date_column: str = "week",
    weeks_before: int = 4,
    weeks_after: int = 12,
) -> pd.DataFrame:
    """
    Align DataFrame to relative timeline from opening date.

    Creates a 'week_relative' column where 0 = opening week,
    negative = weeks before opening, positive = weeks after.

    Args:
        opening_date: Show opening date (or preview start if opening not available)
        df: DataFrame with time series data
        date_column: Name of date column to align
        weeks_before: Number of weeks before opening to include
        weeks_after: Number of weeks after opening to include

    Returns:
        DataFrame with 'week_relative' column and filtered to time window
    """
    if isinstance(opening_date, str):
        opening_date = pd.to_datetime(opening_date)

    df = df.copy()

    # Ensure date column is datetime
    df[date_column] = pd.to_datetime(df[date_column])

    # Calculate weeks from opening
    df["week_relative"] = ((df[date_column] - opening_date).dt.days / 7).round().astype(int)

    # Filter to desired window
    df = df[
        (df["week_relative"] >= -weeks_before)
        & (df["week_relative"] <= weeks_after)
    ]

    return df


def create_aligned_timeline_for_show(
    show_name: str,
    opening_date: Union[str, datetime],
    mds_df: pd.DataFrame,
    sv_df: pd.DataFrame,
    weeks_before: int = 4,
    weeks_after: int = 12,
) -> pd.DataFrame:
    """
    Create aligned timeline combining MDS and SV for a show.

    Args:
        show_name: Name of the show
        opening_date: Opening date
        mds_df: MDS scores by week
        sv_df: SV scores by week
        weeks_before: Weeks before opening
        weeks_after: Weeks after opening

    Returns:
        Aligned DataFrame with both MDS and SV
    """
    # Align MDS
    mds_aligned = align_relative_timeline(
        opening_date, mds_df, weeks_before=weeks_before, weeks_after=weeks_after
    )

    # Align SV
    sv_aligned = align_relative_timeline(
        opening_date, sv_df, weeks_before=weeks_before, weeks_after=weeks_after
    )

    # Merge on week_relative
    if not mds_aligned.empty and not sv_aligned.empty:
        result = pd.merge(
            mds_aligned,
            sv_aligned[["week_relative", "sv", "sv_normalized"]],
            on="week_relative",
            how="outer",
        )
    elif not mds_aligned.empty:
        result = mds_aligned
        result["sv"] = np.nan
        result["sv_normalized"] = np.nan
    elif not sv_aligned.empty:
        result = sv_aligned
        result["mds"] = np.nan
        result["mds_normalized"] = np.nan
    else:
        # Both empty
        return pd.DataFrame(columns=["week_relative", "mds", "sv"])

    # Add show name
    result["show_name"] = show_name

    # Sort by relative week
    result = result.sort_values("week_relative").reset_index(drop=True)

    return result


def create_aligned_timeline_all_shows(
    shows_config: dict,
    scores_by_show: dict,
    weeks_before: int = 4,
    weeks_after: int = 12,
) -> pd.DataFrame:
    """
    Create aligned timeline for all shows.

    Args:
        shows_config: Shows configuration dict (from YAML)
        scores_by_show: Dict mapping show_name -> DataFrame with MDS/SV scores
        weeks_before: Weeks before opening
        weeks_after: Weeks after opening

    Returns:
        Combined DataFrame with all shows in relative timeline
    """
    all_aligned = []

    for show_id, show_info in shows_config.items():
        show_name = show_info["name"]
        opening_date = show_info.get("opening_date")

        # Skip if no opening date
        if not opening_date:
            print(f"Skipping {show_name}: no opening date")
            continue

        # Get scores for this show
        if show_name not in scores_by_show:
            print(f"Warning: No scores found for {show_name}")
            continue

        scores_df = scores_by_show[show_name]

        # Split into MDS and SV columns
        mds_cols = ["week", "mds", "mds_normalized"]
        sv_cols = ["week", "sv", "sv_normalized"]

        mds_df = scores_df[mds_cols] if all(c in scores_df.columns for c in mds_cols) else pd.DataFrame()
        sv_df = scores_df[sv_cols] if all(c in scores_df.columns for c in sv_cols) else pd.DataFrame()

        # Create aligned timeline
        aligned = create_aligned_timeline_for_show(
            show_name, opening_date, mds_df, sv_df, weeks_before, weeks_after
        )

        # Add cohort info
        aligned["cohort"] = show_info.get("cohort", "unknown")

        all_aligned.append(aligned)

    if not all_aligned:
        return pd.DataFrame()

    # Combine all shows
    combined = pd.concat(all_aligned, ignore_index=True)

    return combined


def fill_missing_weeks(
    df: pd.DataFrame,
    week_relative_col: str = "week_relative",
    weeks_before: int = 4,
    weeks_after: int = 12,
) -> pd.DataFrame:
    """
    Fill in missing weeks with NaN values.

    Ensures every show has entries for all weeks in the range, even if data is missing.

    Args:
        df: DataFrame with week_relative column
        week_relative_col: Name of relative week column
        weeks_before: Weeks before opening
        weeks_after: Weeks after opening

    Returns:
        DataFrame with filled missing weeks
    """
    if df.empty:
        return df

    # Create complete week range
    all_weeks = range(-weeks_before, weeks_after + 1)

    filled_dfs = []

    for show_name, group in df.groupby("show_name"):
        # Create complete timeline
        complete_timeline = pd.DataFrame({week_relative_col: all_weeks})

        # Merge with existing data
        merged = pd.merge(complete_timeline, group, on=week_relative_col, how="left")

        # Fill show_name
        merged["show_name"] = show_name

        # Fill cohort (if present)
        if "cohort" in group.columns:
            merged["cohort"] = group["cohort"].iloc[0]

        filled_dfs.append(merged)

    result = pd.concat(filled_dfs, ignore_index=True)

    return result


def compute_lead_lag_correlations(
    aligned_df: pd.DataFrame,
    max_lag: int = 4,
) -> pd.DataFrame:
    """
    Compute lead-lag correlations between MDS and SV.

    Tests whether MDS at time t predicts SV at time t+L for L in [0, max_lag].

    Args:
        aligned_df: Aligned DataFrame with MDS and SV
        max_lag: Maximum lag to test (weeks)

    Returns:
        DataFrame with lag, correlation coefficient, and p-value
    """
    results = []

    for lag in range(0, max_lag + 1):
        # Shift SV by lag weeks
        df_lagged = aligned_df.copy()
        df_lagged["sv_lagged"] = df_lagged.groupby("show_name")["sv"].shift(-lag)

        # Drop rows with missing values
        df_valid = df_lagged.dropna(subset=["mds", "sv_lagged"])

        if len(df_valid) < 3:
            # Not enough data
            results.append({"lag": lag, "pearson_r": np.nan, "p_value": np.nan, "n": 0})
            continue

        # Calculate correlation
        r, p = pearson_correlation(df_valid["mds"], df_valid["sv_lagged"])

        results.append({"lag": lag, "pearson_r": r, "p_value": p, "n": len(df_valid)})

    return pd.DataFrame(results)


def pearson_correlation(x: pd.Series, y: pd.Series) -> tuple:
    """
    Calculate Pearson correlation coefficient and p-value.

    Args:
        x: First series
        y: Second series

    Returns:
        Tuple of (correlation coefficient, p-value)
    """
    from scipy.stats import pearsonr

    valid = ~(x.isna() | y.isna())
    x_valid = x[valid]
    y_valid = y[valid]

    if len(x_valid) < 3:
        return np.nan, np.nan

    return pearsonr(x_valid, y_valid)


def spearman_correlation(x: pd.Series, y: pd.Series) -> tuple:
    """
    Calculate Spearman rank correlation coefficient and p-value.

    Args:
        x: First series
        y: Second series

    Returns:
        Tuple of (correlation coefficient, p-value)
    """
    from scipy.stats import spearmanr

    valid = ~(x.isna() | y.isna())
    x_valid = x[valid]
    y_valid = y[valid]

    if len(x_valid) < 3:
        return np.nan, np.nan

    return spearmanr(x_valid, y_valid)
