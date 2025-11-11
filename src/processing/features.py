"""
Feature extraction for Movement Density Score (MDS) calculation.
Processes raw social and web data into weekly features.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np


def extract_instagram_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract Instagram engagement features by week.

    Args:
        df: DataFrame with Instagram posts data

    Returns:
        DataFrame with weekly features:
        - ig_comments_per_post
        - ig_comment_to_like_ratio
        - ig_repeat_commenter_rate
    """
    if df.empty:
        return pd.DataFrame(
            columns=[
                "week",
                "ig_comments_per_post",
                "ig_comment_to_like_ratio",
                "ig_repeat_commenter_rate",
            ]
        )

    # Ensure date column is datetime
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Group by week
    df["week"] = df["date"].dt.to_period("W").dt.to_timestamp()

    weekly_features = []

    for week, group in df.groupby("week"):
        total_comments = group["comments"].sum()
        total_likes = group["likes"].sum()
        total_posts = len(group)

        features = {
            "week": week,
            "ig_comments_per_post": total_comments / total_posts if total_posts > 0 else 0,
            "ig_comment_to_like_ratio": total_comments / total_likes if total_likes > 0 else 0,
            # Note: repeat_commenter_rate requires comment-level data with user IDs
            # Placeholder for now
            "ig_repeat_commenter_rate": 0.0,
        }

        weekly_features.append(features)

    return pd.DataFrame(weekly_features)


def extract_tiktok_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract TikTok engagement features by week.

    Args:
        df: DataFrame with TikTok videos data

    Returns:
        DataFrame with weekly features:
        - tt_hashtag_video_count
        - tt_ugc_share
        - tt_engagement_rate
    """
    if df.empty:
        return pd.DataFrame(
            columns=[
                "week",
                "tt_hashtag_video_count",
                "tt_ugc_share",
                "tt_engagement_rate",
            ]
        )

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["week"] = df["date"].dt.to_period("W").dt.to_timestamp()

    weekly_features = []

    for week, group in df.groupby("week"):
        total_videos = len(group)
        ugc_videos = (~group["is_official"]).sum() if "is_official" in group.columns else 0

        # Calculate engagement rate
        total_engagement = group[["likes", "comments", "shares"]].sum().sum()
        total_plays = group["plays"].sum() if "plays" in group.columns else 1

        features = {
            "week": week,
            "tt_hashtag_video_count": total_videos,
            "tt_ugc_share": ugc_videos / total_videos if total_videos > 0 else 0,
            "tt_engagement_rate": total_engagement / total_plays if total_plays > 0 else 0,
        }

        weekly_features.append(features)

    return pd.DataFrame(weekly_features)


def extract_reddit_features(posts_df: pd.DataFrame, comments_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """
    Extract Reddit activity features by week.

    Args:
        posts_df: DataFrame with Reddit posts
        comments_df: Optional DataFrame with comments (for repeat contributor analysis)

    Returns:
        DataFrame with weekly features:
        - reddit_thread_count
        - reddit_median_comments_per_thread
        - reddit_repeat_contributor_rate
    """
    if posts_df.empty:
        return pd.DataFrame(
            columns=[
                "week",
                "reddit_thread_count",
                "reddit_median_comments_per_thread",
                "reddit_repeat_contributor_rate",
            ]
        )

    posts_df = posts_df.copy()
    posts_df["date"] = pd.to_datetime(posts_df["date"], errors="coerce")
    posts_df["week"] = posts_df["date"].dt.to_period("W").dt.to_timestamp()

    weekly_features = []

    for week, group in posts_df.groupby("week"):
        thread_count = len(group)
        median_comments = group["num_comments"].median()

        # Calculate repeat contributor rate if comments data available
        repeat_rate = 0.0
        if comments_df is not None and not comments_df.empty:
            comments_df = comments_df.copy()
            comments_df["date"] = pd.to_datetime(comments_df["date"], unit="s", errors="coerce")
            comments_df["week"] = comments_df["date"].dt.to_period("W").dt.to_timestamp()

            week_comments = comments_df[comments_df["week"] == week]
            if not week_comments.empty:
                author_counts = week_comments["author"].value_counts()
                repeat_contributors = (author_counts >= 2).sum()
                total_contributors = len(author_counts)
                repeat_rate = repeat_contributors / total_contributors if total_contributors > 0 else 0

        features = {
            "week": week,
            "reddit_thread_count": thread_count,
            "reddit_median_comments_per_thread": median_comments,
            "reddit_repeat_contributor_rate": repeat_rate,
        }

        weekly_features.append(features)

    return pd.DataFrame(weekly_features)


def extract_trends_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract Google Trends features.

    Args:
        df: DataFrame with Google Trends interest over time (date index, show columns)

    Returns:
        DataFrame with weekly features:
        - trends_interest
        - trends_slope_4w (slope over last 4 weeks)
        - trends_volatility (std dev)
    """
    if df.empty:
        return pd.DataFrame(
            columns=["week", "trends_interest", "trends_slope_4w", "trends_volatility"]
        )

    df = df.copy()

    # If df has date as index, reset it
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    # Resample to weekly if not already
    df_weekly = df.resample("W").mean()

    # Calculate features
    features = []

    for i in range(len(df_weekly)):
        week = df_weekly.index[i]

        # Average interest across all query columns
        interest = df_weekly.iloc[i].mean()

        # Calculate 4-week slope
        if i >= 3:
            last_4_weeks = df_weekly.iloc[i - 3 : i + 1].mean(axis=1)
            slope = np.polyfit(range(4), last_4_weeks, 1)[0]
        else:
            slope = 0

        # Calculate volatility (std dev over last 4 weeks)
        if i >= 3:
            volatility = df_weekly.iloc[i - 3 : i + 1].mean(axis=1).std()
        else:
            volatility = 0

        features.append(
            {
                "week": week,
                "trends_interest": interest,
                "trends_slope_4w": slope,
                "trends_volatility": volatility,
            }
        )

    return pd.DataFrame(features)


def combine_all_features(
    instagram_features: pd.DataFrame,
    tiktok_features: pd.DataFrame,
    reddit_features: pd.DataFrame,
    trends_features: pd.DataFrame,
) -> pd.DataFrame:
    """
    Combine all feature DataFrames into a single weekly features table.

    Args:
        instagram_features: Instagram weekly features
        tiktok_features: TikTok weekly features
        reddit_features: Reddit weekly features
        trends_features: Google Trends weekly features

    Returns:
        Combined DataFrame with all features by week
    """
    # Start with an empty base
    all_dfs = [instagram_features, tiktok_features, reddit_features, trends_features]

    # Filter out empty DataFrames
    non_empty_dfs = [df for df in all_dfs if not df.empty]

    if not non_empty_dfs:
        return pd.DataFrame(columns=["week"])

    # Merge on week
    result = non_empty_dfs[0]
    for df in non_empty_dfs[1:]:
        result = pd.merge(result, df, on="week", how="outer")

    # Sort by week
    result = result.sort_values("week").reset_index(drop=True)

    # Fill NaN with 0 for missing features
    result = result.fillna(0)

    return result


def build_features_for_show(
    show_name: str,
    instagram_df: pd.DataFrame,
    tiktok_df: pd.DataFrame,
    reddit_posts_df: pd.DataFrame,
    reddit_comments_df: pd.DataFrame,
    trends_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build complete feature set for a single show.

    Args:
        show_name: Name of the show
        instagram_df: Instagram posts data
        tiktok_df: TikTok videos data
        reddit_posts_df: Reddit posts data
        reddit_comments_df: Reddit comments data
        trends_df: Google Trends data

    Returns:
        DataFrame with all weekly features for the show
    """
    ig_features = extract_instagram_features(instagram_df)
    tt_features = extract_tiktok_features(tiktok_df)
    reddit_features = extract_reddit_features(reddit_posts_df, reddit_comments_df)
    trends_features = extract_trends_features(trends_df)

    combined = combine_all_features(ig_features, tt_features, reddit_features, trends_features)

    # Add show name
    combined["show_name"] = show_name

    return combined
