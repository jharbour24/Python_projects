#!/usr/bin/env python3
"""
Add show-level financial metrics and create bubble charts for producers.
This module enhances the main analysis with per-show ATP/gross and network visualizations.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def add_show_financial_metrics(df, grosses_df):
    """
    Add average ATP and average weekly gross for each show.

    Args:
        df: DataFrame with show data
        grosses_df: DataFrame with weekly grosses data

    Returns:
        DataFrame with added financial columns
    """
    if grosses_df is None:
        logger.warning("No grosses data available")
        return df

    logger.info("\nAdding show-level financial metrics...")

    # Normalize show names
    df_copy = df.copy()
    df_copy['show_name_upper'] = df_copy['show_name'].str.upper().str.strip()
    grosses_df['Show_upper'] = grosses_df['Show'].str.upper().str.strip()

    # Aggregate by show
    show_metrics = grosses_df.groupby('Show_upper').agg({
        'Avg_Ticket': 'mean',
        'Gross': 'mean',
        'Week': 'count'
    }).reset_index()

    show_metrics.columns = ['Show_upper', 'avg_atp', 'avg_weekly_gross', 'num_weeks']

    # Merge with main dataframe
    df_enhanced = df_copy.merge(show_metrics, left_on='show_name_upper', right_on='Show_upper', how='left')
    df_enhanced = df_enhanced.drop(['show_name_upper', 'Show_upper'], axis=1)

    # Log results
    shows_with_data = df_enhanced['avg_atp'].notna().sum()
    logger.info(f"  Shows with financial data: {shows_with_data}/{len(df_enhanced)}")
    logger.info(f"  Avg ATP range: ${df_enhanced['avg_atp'].min():.2f} - ${df_enhanced['avg_atp'].max():.2f}")
    logger.info(f"  Avg weekly gross range: ${df_enhanced['avg_weekly_gross'].min():,.0f} - ${df_enhanced['avg_weekly_gross'].max():,.0f}")

    return df_enhanced


def create_producer_bubble_charts(df, grosses_df, time_period='all'):
    """
    Create bubble charts showing top 25 producers by number of shows.
    Three versions: avg weekly gross, total gross.

    Args:
        df: DataFrame with producer data
        grosses_df: DataFrame with grosses data
        time_period: 'all' (2010-2025) or 'post_pandemic' (2021+)
    """
    if grosses_df is None or 'producer_names' not in df.columns:
        logger.warning("Cannot create bubble charts - missing data")
        return

    logger.info(f"\nCreating producer bubble charts ({time_period})...")

    # Filter by time period
    if time_period == 'post_pandemic':
        df_filtered = df[df['production_year'] >= 2021].copy()
        title_suffix = " (2021-2025 Post-Pandemic)"
        file_suffix = "_post_pandemic"
    else:
        df_filtered = df.copy()
        title_suffix = " (2010-2025)"
        file_suffix = "_all_years"

    # Normalize show names
    df_filtered['show_name_upper'] = df_filtered['show_name'].str.upper().str.strip()
    grosses_df['Show_upper'] = grosses_df['Show'].str.upper().str.strip()

    # Aggregate grosses by show
    show_grosses = grosses_df.groupby('Show_upper').agg({
        'Gross': ['sum', 'mean'],
        'Avg_Ticket': 'mean'
    }).reset_index()

    show_grosses.columns = ['Show_upper', 'total_gross', 'avg_weekly_gross', 'avg_atp']

    # Merge with show data
    df_with_grosses = df_filtered.merge(show_grosses, left_on='show_name_upper', right_on='Show_upper', how='left')

    # Parse producers and aggregate
    producer_stats = {}

    for _, row in df_with_grosses.iterrows():
        if pd.isna(row['producer_names']):
            continue

        producers = [p.strip() for p in str(row['producer_names']).split(';') if p.strip()]

        for producer in producers:
            if producer not in producer_stats:
                producer_stats[producer] = {
                    'show_count': 0,
                    'total_gross': 0,
                    'avg_weekly_grosses': [],
                    'shows': []
                }

            producer_stats[producer]['show_count'] += 1
            producer_stats[producer]['shows'].append(row['show_name'])

            if not pd.isna(row['total_gross']):
                producer_stats[producer]['total_gross'] += row['total_gross']
            if not pd.isna(row['avg_weekly_gross']):
                producer_stats[producer]['avg_weekly_grosses'].append(row['avg_weekly_gross'])

    # Convert to DataFrame
    producer_df = pd.DataFrame([
        {
            'producer': name,
            'show_count': stats['show_count'],
            'total_gross': stats['total_gross'],
            'avg_weekly_gross': np.mean(stats['avg_weekly_grosses']) if stats['avg_weekly_grosses'] else 0
        }
        for name, stats in producer_stats.items()
    ])

    # Get top 25 by show count
    top_25 = producer_df.sort_values('show_count', ascending=False).head(25)

    # Create bubble charts
    output_dir = Path('analysis/results')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Chart 1: Size by average weekly gross
    fig, ax = plt.subplots(figsize=(16, 12))

    scatter = ax.scatter(
        range(len(top_25)),
        top_25['show_count'],
        s=top_25['avg_weekly_gross'] / 1000,  # Scale down for visibility
        alpha=0.6,
        c=top_25['avg_weekly_gross'],
        cmap='YlOrRd'
    )

    # Add producer labels
    for idx, row in enumerate(top_25.itertuples()):
        ax.annotate(
            row.producer,
            (idx, row.show_count),
            fontsize=8,
            ha='center',
            va='bottom'
        )

    ax.set_xlabel('Producers (ranked by number of shows)', fontsize=12)
    ax.set_ylabel('Number of Shows', fontsize=12)
    ax.set_title(f'Top 25 Broadway Producers{title_suffix}\nBubble Size = Average Weekly Gross', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)

    # Colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Avg Weekly Gross ($)', fontsize=10)

    plt.tight_layout()
    output_path = output_dir / f'producer_bubble_avg_weekly{file_suffix}.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"  ✓ Saved: {output_path}")

    # Chart 2: Size by total gross
    fig, ax = plt.subplots(figsize=(16, 12))

    scatter = ax.scatter(
        range(len(top_25)),
        top_25['show_count'],
        s=top_25['total_gross'] / 100000,  # Scale down for visibility
        alpha=0.6,
        c=top_25['total_gross'],
        cmap='viridis'
    )

    # Add producer labels
    for idx, row in enumerate(top_25.itertuples()):
        ax.annotate(
            row.producer,
            (idx, row.show_count),
            fontsize=8,
            ha='center',
            va='bottom'
        )

    ax.set_xlabel('Producers (ranked by number of shows)', fontsize=12)
    ax.set_ylabel('Number of Shows', fontsize=12)
    ax.set_title(f'Top 25 Broadway Producers{title_suffix}\nBubble Size = Total Gross Revenue', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)

    # Colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Total Gross ($)', fontsize=10)

    plt.tight_layout()
    output_path = output_dir / f'producer_bubble_total_gross{file_suffix}.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"  ✓ Saved: {output_path}")

    return top_25


def get_tony_season_year(production_year, opening_month):
    """
    Determine which Tony season a show belongs to.
    Tony season runs from ~May of previous year to May of current year.
    Awards are in June.

    Args:
        production_year: Year show opened
        opening_month: Month show opened (1-12)

    Returns:
        Tony season year (the year of the awards ceremony)
    """
    if pd.isna(opening_month) or pd.isna(production_year):
        return production_year

    # If opened May-December, eligible for NEXT year's Tonys
    if opening_month >= 5:
        return production_year + 1
    # If opened Jan-April, eligible for SAME year's Tonys
    else:
        return production_year


def analyze_tony_wins_by_year(df, grosses_df=None):
    """
    Analyze relationship between producer count and Tony wins year by year.
    Only includes NEW Tony-nominated shows for each season.

    Args:
        df: DataFrame with show data including production_year
        grosses_df: Optional grosses data

    Returns:
        DataFrame with year-by-year analysis
    """
    logger.info("\n" + "="*70)
    logger.info("YEAR-BY-YEAR TONY ANALYSIS (NEW SHOWS ONLY)")
    logger.info("="*70)

    # Filter to Tony-nominated shows only (either won or were nominated)
    # Assuming tony_win column exists and shows with tony_category are nominated
    df_tony = df[(df['tony_win'] == 1) | (df['tony_category'].notna())].copy()

    if len(df_tony) == 0:
        logger.warning("No Tony-nominated shows found")
        return None

    # Group by Tony season year
    yearly_stats = []

    for year in sorted(df_tony['production_year'].unique()):
        if pd.isna(year):
            continue

        year_shows = df_tony[df_tony['production_year'] == year].copy()

        if len(year_shows) == 0:
            continue

        # Calculate stats for this year
        total_shows = len(year_shows)
        winners = year_shows[year_shows['tony_win'] == 1]
        num_winners = len(winners)

        # Producer counts
        avg_producers_all = year_shows['num_total_producers'].mean()
        avg_producers_winners = winners['num_total_producers'].mean() if len(winners) > 0 else np.nan
        avg_producers_nominees = year_shows[year_shows['tony_win'] == 0]['num_total_producers'].mean()

        yearly_stats.append({
            'year': int(year),
            'total_nominated': total_shows,
            'num_winners': num_winners,
            'win_rate': num_winners / total_shows if total_shows > 0 else 0,
            'avg_producers_all': avg_producers_all,
            'avg_producers_winners': avg_producers_winners,
            'avg_producers_nominees': avg_producers_nominees,
            'producer_differential': avg_producers_winners - avg_producers_nominees if not pd.isna(avg_producers_nominees) else np.nan
        })

    yearly_df = pd.DataFrame(yearly_stats)

    # Log results
    logger.info(f"\nTony seasons analyzed: {len(yearly_df)}")
    logger.info(f"Total Tony-nominated shows: {df_tony.shape[0]}")
    logger.info(f"Total Tony winners: {df_tony['tony_win'].sum()}")

    logger.info("\n" + "="*70)
    logger.info("YEAR-BY-YEAR BREAKDOWN")
    logger.info("="*70)
    logger.info(f"{'Year':<6} {'Nominated':<10} {'Winners':<8} {'Avg Prod (All)':<15} {'Avg Prod (Winners)':<20} {'Avg Prod (Nominees)':<20} {'Differential':<12}")
    logger.info("-"*110)

    for _, row in yearly_df.iterrows():
        logger.info(
            f"{row['year']:<6.0f} "
            f"{row['total_nominated']:<10.0f} "
            f"{row['num_winners']:<8.0f} "
            f"{row['avg_producers_all']:<15.2f} "
            f"{row['avg_producers_winners']:<20.2f} "
            f"{row['avg_producers_nominees']:<20.2f} "
            f"{row['producer_differential']:<12.2f}"
        )

    # Calculate correlation between avg producers and win rate
    if len(yearly_df) > 2:
        from scipy.stats import pearsonr
        corr, p_value = pearsonr(yearly_df['avg_producers_all'].dropna(), yearly_df['win_rate'].dropna())
        logger.info(f"\nCorrelation between avg producers and win rate: {corr:.3f} (p={p_value:.3f})")

    # Save results
    output_path = Path('analysis/results/tony_wins_by_year.csv')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    yearly_df.to_csv(output_path, index=False)
    logger.info(f"\n✓ Saved year-by-year analysis: {output_path}")

    return yearly_df


if __name__ == '__main__':
    print("This module provides enhanced analysis functions.")
    print("Run producer_tony_analysis.py to execute the full analysis.")
