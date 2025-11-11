"""
Score calculation for Movement Density Score (MDS) and Sales Velocity (SV).
Combines features into composite scores using z-score normalization.
"""

from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from scipy import stats


class MDSCalculator:
    """Calculate Movement Density Score from social features."""

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Initialize MDS calculator.

        Args:
            weights: Optional dict of feature weights. Defaults to equal weights.
        """
        self.default_weights = {
            "ig_comments_per_post": 1.0,
            "ig_comment_to_like_ratio": 1.0,
            "ig_repeat_commenter_rate": 1.0,
            "tt_hashtag_video_count": 1.0,
            "tt_ugc_share": 1.0,
            "tt_engagement_rate": 1.0,
            "reddit_thread_count": 1.0,
            "reddit_median_comments_per_thread": 1.0,
            "reddit_repeat_contributor_rate": 1.0,
            "trends_slope_4w": 1.0,
            "trends_volatility": -1.0,  # Negative weight: high volatility is bad
        }

        self.weights = weights or self.default_weights

    def calculate_mds(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Movement Density Score.

        MDS = sum of weighted z-scores across all features

        Args:
            features_df: DataFrame with weekly features

        Returns:
            DataFrame with added 'mds' column
        """
        df = features_df.copy()

        # Standardize (z-score) each feature
        mds_components = []

        for feature, weight in self.weights.items():
            if feature in df.columns:
                # Calculate z-score
                z_score = self._safe_zscore(df[feature])
                df[f"{feature}_z"] = z_score

                # Apply weight
                weighted_z = z_score * weight
                mds_components.append(weighted_z)
            else:
                # Feature not present, contribute 0
                mds_components.append(pd.Series(0, index=df.index))

        # Sum all weighted z-scores
        df["mds"] = sum(mds_components)

        # Normalize MDS to 0-100 scale for interpretability
        if df["mds"].std() > 0:
            df["mds_normalized"] = (
                (df["mds"] - df["mds"].min())
                / (df["mds"].max() - df["mds"].min())
                * 100
            )
        else:
            df["mds_normalized"] = 50  # Neutral score if no variance

        return df

    def _safe_zscore(self, series: pd.Series) -> pd.Series:
        """
        Calculate z-score safely (handles zero variance).

        Args:
            series: Pandas Series

        Returns:
            Z-scored Series
        """
        mean = series.mean()
        std = series.std()

        if std == 0 or pd.isna(std):
            return pd.Series(0, index=series.index)

        return (series - mean) / std


class SVCalculator:
    """Calculate Sales Velocity score from sales proxies."""

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Initialize SV calculator.

        Args:
            weights: Optional dict of feature weights. Defaults to equal weights.
        """
        self.default_weights = {
            "grosses_slope": 1.0,
            "attendance_slope": 1.0,
            "price_slope": 1.0,
            "availability_slope": -1.0,  # Negative: more availability = worse
            "discount_count_slope": -1.0,  # Negative: more discounts = worse
        }

        self.weights = weights or self.default_weights

    def calculate_sv(self, proxies_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Sales Velocity score.

        SV = sum of weighted z-scores of sales proxy slopes

        Args:
            proxies_df: DataFrame with weekly sales proxies

        Returns:
            DataFrame with added 'sv' column
        """
        df = proxies_df.copy()

        # Calculate slopes for each proxy
        df = self._calculate_slopes(df)

        # Standardize and weight
        sv_components = []

        for feature, weight in self.weights.items():
            if feature in df.columns:
                z_score = self._safe_zscore(df[feature])
                df[f"{feature}_z"] = z_score

                weighted_z = z_score * weight
                sv_components.append(weighted_z)
            else:
                sv_components.append(pd.Series(0, index=df.index))

        # Sum all weighted z-scores
        df["sv"] = sum(sv_components)

        # Normalize to 0-100 scale
        if df["sv"].std() > 0:
            df["sv_normalized"] = (
                (df["sv"] - df["sv"].min())
                / (df["sv"].max() - df["sv"].min())
                * 100
            )
        else:
            df["sv_normalized"] = 50

        return df

    def _calculate_slopes(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate weekly slopes for sales proxies.

        Uses 4-week rolling window to compute slope.

        Args:
            df: DataFrame with sales proxies

        Returns:
            DataFrame with added slope columns
        """
        result = df.copy()

        # Define proxy columns and their slope names
        proxy_columns = {
            "gross": "grosses_slope",
            "attendance": "attendance_slope",
            "min_price": "price_slope",
            "listings_count": "availability_slope",
            "discount_count": "discount_count_slope",
        }

        for proxy_col, slope_col in proxy_columns.items():
            if proxy_col in df.columns:
                result[slope_col] = self._rolling_slope(df[proxy_col], window=4)
            else:
                result[slope_col] = 0

        return result

    def _rolling_slope(self, series: pd.Series, window: int = 4) -> pd.Series:
        """
        Calculate rolling slope using linear regression.

        Args:
            series: Time series data
            window: Window size for rolling calculation

        Returns:
            Series of slopes
        """
        slopes = []

        for i in range(len(series)):
            if i < window - 1:
                slopes.append(0)
            else:
                window_data = series.iloc[i - window + 1 : i + 1]
                x = np.arange(window)
                y = window_data.values

                # Skip if too many NaNs
                if np.isnan(y).sum() > window / 2:
                    slopes.append(0)
                else:
                    # Linear regression
                    mask = ~np.isnan(y)
                    if mask.sum() >= 2:
                        slope = np.polyfit(x[mask], y[mask], 1)[0]
                        slopes.append(slope)
                    else:
                        slopes.append(0)

        return pd.Series(slopes, index=series.index)

    def _safe_zscore(self, series: pd.Series) -> pd.Series:
        """Calculate z-score safely."""
        mean = series.mean()
        std = series.std()

        if std == 0 or pd.isna(std):
            return pd.Series(0, index=series.index)

        return (series - mean) / std


def build_mds(features_df: pd.DataFrame, weights: Optional[Dict[str, float]] = None) -> pd.DataFrame:
    """
    Convenience function to build MDS.

    Args:
        features_df: Weekly features DataFrame
        weights: Optional feature weights

    Returns:
        DataFrame with MDS scores
    """
    calculator = MDSCalculator(weights=weights)
    return calculator.calculate_mds(features_df)


def build_sv(proxies_df: pd.DataFrame, weights: Optional[Dict[str, float]] = None) -> pd.DataFrame:
    """
    Convenience function to build SV.

    Args:
        proxies_df: Weekly sales proxies DataFrame
        weights: Optional feature weights

    Returns:
        DataFrame with SV scores
    """
    calculator = SVCalculator(weights=weights)
    return calculator.calculate_sv(proxies_df)


def build_scores_for_show(
    features_df: pd.DataFrame,
    grosses_df: pd.DataFrame,
    prices_df: pd.DataFrame,
    discounts_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build both MDS and SV scores for a show.

    Args:
        features_df: Weekly features (for MDS)
        grosses_df: Weekly grosses data
        prices_df: Price snapshots
        discounts_df: Discount counts

    Returns:
        DataFrame with both MDS and SV by week
    """
    # Calculate MDS
    mds_df = build_mds(features_df)

    # Build sales proxies DataFrame
    proxies = _build_sales_proxies(grosses_df, prices_df, discounts_df)

    # Calculate SV
    sv_df = build_sv(proxies)

    # Merge MDS and SV on week
    if "week" in mds_df.columns and "week" in sv_df.columns:
        result = pd.merge(
            mds_df[["week", "show_name", "mds", "mds_normalized"]],
            sv_df[["week", "sv", "sv_normalized"]],
            on="week",
            how="outer",
        )
    else:
        # If week not present, just concatenate
        result = pd.concat([mds_df, sv_df], axis=1)

    return result


def _build_sales_proxies(
    grosses_df: pd.DataFrame,
    prices_df: pd.DataFrame,
    discounts_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build unified sales proxies DataFrame.

    Args:
        grosses_df: Weekly grosses
        prices_df: Price snapshots
        discounts_df: Discount counts

    Returns:
        Combined proxies DataFrame
    """
    proxies = []

    # Process grosses
    if not grosses_df.empty:
        grosses_df = grosses_df.copy()
        if "week_ending" in grosses_df.columns:
            grosses_df["week"] = pd.to_datetime(grosses_df["week_ending"])
            proxies.append(grosses_df[["week", "gross", "attendance", "capacity_pct"]])

    # Process prices
    if not prices_df.empty:
        prices_df = prices_df.copy()
        if "date_scraped" in prices_df.columns:
            prices_df["week"] = pd.to_datetime(prices_df["date_scraped"]).dt.to_period("W").dt.to_timestamp()
            price_weekly = prices_df.groupby("week").agg({
                "min_price": "mean",
                "avg_price": "mean",
                "listings_count": "mean",
            }).reset_index()
            proxies.append(price_weekly)

    # Process discounts
    if not discounts_df.empty:
        discounts_df = discounts_df.copy()
        if "date_scraped" in discounts_df.columns:
            discounts_df["week"] = pd.to_datetime(discounts_df["date_scraped"]).dt.to_period("W").dt.to_timestamp()
            discount_weekly = discounts_df.groupby("week").agg({
                "discount_count": "mean",
            }).reset_index()
            proxies.append(discount_weekly)

    # Merge all proxies
    if not proxies:
        return pd.DataFrame(columns=["week"])

    result = proxies[0]
    for df in proxies[1:]:
        result = pd.merge(result, df, on="week", how="outer")

    result = result.sort_values("week").reset_index(drop=True)
    result = result.fillna(0)

    return result
