#!/usr/bin/env python3
"""
Statistical analysis of relationship between producer counts and Tony Award wins.

Analyzes:
1. Whether Broadway shows with more producers are more/less likely to win Tony Awards
2. Which specific producers have higher Tony win rates
3. Yearly trends in producer counts
4. 5-year prediction for future producer counts

Uses logistic regression and time series forecasting.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import statsmodels.api as sm
from statsmodels.formula.api import logit
from sklearn.linear_model import LinearRegression
from collections import Counter

from utils import setup_logger

logger = setup_logger(__name__, log_file='logs/analysis.log')


def load_and_merge_data():
    """
    Load producer counts, Tony outcomes, and grosses data, merge them.

    Returns:
        Merged DataFrame, grosses DataFrame
    """
    logger.info("Loading data...")

    # Try different file names for Tony data (now with performances)
    tony_files = [
        'data/tony_outcomes_with_performances.csv',  # NEW: Enhanced with performance data
        'data/tony_outcomes_manual.csv',
        'data/tony_outcomes.csv',
    ]

    # Producer data (optional - may not exist yet)
    producer_files = [
        'data/broadway_producer_data.xlsx',  # Output from browser_ibdb_scraper.py
        'data/show_producer_counts_manual.csv',
        'data/show_producer_counts_ibdb.csv',
    ]

    grosses_files = [
        'data/broadway_grosses_2010_present.xlsx',
    ]

    # Load Tony data (required)
    tony_df = None
    for file_path in tony_files:
        if Path(file_path).exists():
            logger.info(f"Loading Tony outcomes from: {file_path}")
            if file_path.endswith('.xlsx'):
                tony_df = pd.read_excel(file_path)
            else:
                tony_df = pd.read_csv(file_path)
            break

    if tony_df is None:
        raise FileNotFoundError(
            f"No Tony outcomes data found. Please create one of: {tony_files}\n"
            f"Use templates in data/templates/ for manual data entry."
        )

    logger.info(f"  Tony data: {len(tony_df)} shows")

    # Load producer data (optional)
    producer_df = None
    for file_path in producer_files:
        if Path(file_path).exists():
            logger.info(f"Loading producer data from: {file_path}")
            if file_path.endswith('.xlsx'):
                producer_df = pd.read_excel(file_path)
            else:
                producer_df = pd.read_csv(file_path)
            logger.info(f"  Producer data: {len(producer_df)} shows")
            break

    # Load grosses data (optional)
    grosses_df = None
    for file_path in grosses_files:
        if Path(file_path).exists():
            logger.info(f"Loading grosses data from: {file_path}")
            try:
                grosses_df = pd.read_excel(file_path)
                logger.info(f"  Grosses data: {len(grosses_df)} show-week records")
            except Exception as e:
                logger.warning(f"  Could not load grosses data: {e}")
                grosses_df = None
            break

    # Merge datasets
    logger.info(f"Merging datasets...")

    if producer_df is not None:
        # If we have producer data, merge it with Tony data
        # Keep performance data from tony_df (more reliable)
        merge_cols = ['show_name', 'num_total_producers', 'producer_names']
        if 'num_performances' in producer_df.columns and 'num_performances' not in tony_df.columns:
            merge_cols.append('num_performances')
        if 'production_year' in producer_df.columns and 'production_year' not in tony_df.columns:
            merge_cols.append('production_year')

        # Filter to columns that exist
        merge_cols = [col for col in merge_cols if col in producer_df.columns]

        merged_df = tony_df.merge(
            producer_df[merge_cols],
            on='show_name',
            how='left',  # Keep all tony data even if no producer data
            suffixes=('', '_producer')
        )

        # If we have duplicate performance/year columns, prefer the tony_df version
        if 'num_performances_producer' in merged_df.columns:
            merged_df['num_performances'] = merged_df['num_performances'].fillna(merged_df['num_performances_producer'])
            merged_df = merged_df.drop('num_performances_producer', axis=1)

        if 'production_year_producer' in merged_df.columns:
            merged_df['production_year'] = merged_df['production_year'].fillna(merged_df['production_year_producer'])
            merged_df = merged_df.drop('production_year_producer', axis=1)

    else:
        # No producer data yet - use tony_df as-is
        logger.warning("  No producer data found - analysis will be limited")
        merged_df = tony_df.copy()

        # Add num_total_producers column if missing
        if 'num_total_producers' not in merged_df.columns:
            merged_df['num_total_producers'] = None

    logger.info(f"  Final merged: {len(merged_df)} shows")

    return merged_df, grosses_df


def clean_data(df):
    """
    Clean and prepare data for analysis.

    Args:
        df: Merged DataFrame

    Returns:
        Cleaned DataFrame
    """
    logger.info("\nCleaning data...")

    initial_count = len(df)

    # Convert numeric columns
    if 'num_total_producers' in df.columns:
        df['num_total_producers'] = pd.to_numeric(df['num_total_producers'], errors='coerce')
    if 'num_performances' in df.columns:
        df['num_performances'] = pd.to_numeric(df['num_performances'], errors='coerce')
    if 'production_year' in df.columns:
        df['production_year'] = pd.to_numeric(df['production_year'], errors='coerce')
    df['tony_win'] = pd.to_numeric(df['tony_win'], errors='coerce')

    # Drop rows missing critical tony data (always required)
    df_clean = df.dropna(subset=['tony_win']).copy()

    # For producer analysis, we need num_total_producers
    # But we'll keep all rows and just skip producer analysis if missing
    has_producer_data = 'num_total_producers' in df_clean.columns and df_clean['num_total_producers'].notna().any()

    if not has_producer_data:
        logger.warning(f"  No producer count data available - producer analysis will be skipped")
    else:
        logger.info(f"  Shows with producer data: {df_clean['num_total_producers'].notna().sum()}")

    logger.info(f"  Dropped {initial_count - len(df_clean)} rows with missing Tony data")
    logger.info(f"  Final analysis dataset: {len(df_clean)} shows")

    # Convert tony_win to int
    df_clean['tony_win'] = df_clean['tony_win'].astype(int)

    return df_clean


def descriptive_stats(df):
    """
    Compute and display descriptive statistics.

    Args:
        df: Clean DataFrame
    """
    logger.info("\n" + "="*70)
    logger.info("DESCRIPTIVE STATISTICS")
    logger.info("="*70)

    # Overall stats
    logger.info(f"\nDataset size: {len(df)} shows")
    logger.info(f"Tony winners: {df['tony_win'].sum()} ({df['tony_win'].mean()*100:.1f}%)")
    logger.info(f"Non-winners: {(1-df['tony_win']).sum()} ({(1-df['tony_win'].mean())*100:.1f}%)")

    # Producer count distributions
    logger.info(f"\nProducer counts (all shows):")
    logger.info(f"  Mean total producers: {df['num_total_producers'].mean():.2f}")
    logger.info(f"  Median total producers: {df['num_total_producers'].median():.1f}")
    logger.info(f"  Std dev: {df['num_total_producers'].std():.2f}")
    logger.info(f"  Range: {df['num_total_producers'].min():.0f} - {df['num_total_producers'].max():.0f}")

    # By Tony win status
    logger.info(f"\n--- Tony Winners ---")
    winners = df[df['tony_win'] == 1]
    if len(winners) > 0:
        logger.info(f"  N = {len(winners)}")
        logger.info(f"  Mean total producers: {winners['num_total_producers'].mean():.2f}")
        logger.info(f"  Median total producers: {winners['num_total_producers'].median():.1f}")
        logger.info(f"  Std dev: {winners['num_total_producers'].std():.2f}")
    else:
        logger.warning("  No Tony winners in dataset")

    logger.info(f"\n--- Non-Winners ---")
    non_winners = df[df['tony_win'] == 0]
    if len(non_winners) > 0:
        logger.info(f"  N = {len(non_winners)}")
        logger.info(f"  Mean total producers: {non_winners['num_total_producers'].mean():.2f}")
        logger.info(f"  Median total producers: {non_winners['num_total_producers'].median():.1f}")
        logger.info(f"  Std dev: {non_winners['num_total_producers'].std():.2f}")

    # Difference
    if len(winners) > 0 and len(non_winners) > 0:
        diff = winners['num_total_producers'].mean() - non_winners['num_total_producers'].mean()
        logger.info(f"\n--- Difference (Winners - Non-Winners) ---")
        logger.info(f"  Mean difference: {diff:+.2f} producers")

        if diff > 0:
            logger.info(f"  → Winners have MORE producers on average")
        elif diff < 0:
            logger.info(f"  → Winners have FEWER producers on average")
        else:
            logger.info(f"  → No difference in average producer counts")


def statistical_tests(df):
    """
    Run statistical tests.

    Args:
        df: Clean DataFrame
    """
    logger.info("\n" + "="*70)
    logger.info("STATISTICAL TESTS")
    logger.info("="*70)

    winners = df[df['tony_win'] == 1]['num_total_producers']
    non_winners = df[df['tony_win'] == 0]['num_total_producers']

    if len(winners) < 2 or len(non_winners) < 2:
        logger.warning("Insufficient data for statistical tests")
        return

    # T-test
    logger.info("\n--- Independent Samples T-Test ---")
    logger.info("H0: Winners and non-winners have equal mean producer counts")

    t_stat, p_value = stats.ttest_ind(winners, non_winners)
    logger.info(f"  t-statistic: {t_stat:.3f}")
    logger.info(f"  p-value: {p_value:.4f}")

    if p_value < 0.05:
        logger.info(f"  Result: SIGNIFICANT (p < 0.05)")
        logger.info(f"  → Reject null hypothesis: difference is statistically significant")
    else:
        logger.info(f"  Result: NOT SIGNIFICANT (p >= 0.05)")
        logger.info(f"  → Cannot reject null hypothesis: no significant difference")

    # Mann-Whitney U test (non-parametric alternative)
    logger.info("\n--- Mann-Whitney U Test (non-parametric) ---")
    u_stat, p_value_mw = stats.mannwhitneyu(winners, non_winners, alternative='two-sided')
    logger.info(f"  U-statistic: {u_stat:.3f}")
    logger.info(f"  p-value: {p_value_mw:.4f}")

    if p_value_mw < 0.05:
        logger.info(f"  Result: SIGNIFICANT (p < 0.05)")
    else:
        logger.info(f"  Result: NOT SIGNIFICANT (p >= 0.05)")


def logistic_regression(df):
    """
    Run logistic regression: tony_win ~ num_total_producers.

    Args:
        df: Clean DataFrame
    """
    logger.info("\n" + "="*70)
    logger.info("LOGISTIC REGRESSION ANALYSIS")
    logger.info("="*70)

    logger.info("\nModel: tony_win ~ num_total_producers")
    logger.info("(Binary logistic regression)")

    try:
        # Prepare data
        df_model = df[['tony_win', 'num_total_producers']].dropna()

        if len(df_model) < 10:
            logger.warning("Insufficient data for regression (need at least 10 observations)")
            return

        # Fit model
        model = logit('tony_win ~ num_total_producers', data=df_model)
        result = model.fit(disp=False)

        # Display results
        logger.info("\n" + str(result.summary()))

        # Extract key statistics
        coef = result.params['num_total_producers']
        p_value = result.pvalues['num_total_producers']
        conf_int = result.conf_int().loc['num_total_producers']

        logger.info("\n--- Key Results ---")
        logger.info(f"Coefficient (log-odds): {coef:.4f}")
        logger.info(f"95% CI: [{conf_int[0]:.4f}, {conf_int[1]:.4f}]")
        logger.info(f"p-value: {p_value:.4f}")

        # Interpret odds ratio
        odds_ratio = np.exp(coef)
        logger.info(f"\nOdds Ratio: {odds_ratio:.3f}")

        logger.info("\n--- Interpretation ---")
        if p_value < 0.05:
            if coef > 0:
                logger.info(f"✓ SIGNIFICANT POSITIVE association (p < 0.05)")
                logger.info(f"  Each additional producer increases the odds of winning by {(odds_ratio-1)*100:.1f}%")
            else:
                logger.info(f"✓ SIGNIFICANT NEGATIVE association (p < 0.05)")
                logger.info(f"  Each additional producer decreases the odds of winning by {(1-odds_ratio)*100:.1f}%")
        else:
            logger.info(f"✗ NO SIGNIFICANT association (p >= 0.05)")
            logger.info(f"  Producer count does not significantly predict Tony wins in this sample")

        # Practical significance
        logger.info(f"\n--- Practical Significance ---")
        logger.info(f"Pseudo R-squared: {result.prsquared:.3f}")
        logger.info(f"(Proportion of variance explained: {result.prsquared*100:.1f}%)")

        if result.prsquared < 0.02:
            logger.info(f"→ Very weak explanatory power")
        elif result.prsquared < 0.1:
            logger.info(f"→ Weak explanatory power")
        elif result.prsquared < 0.3:
            logger.info(f"→ Moderate explanatory power")
        else:
            logger.info(f"→ Strong explanatory power")

    except Exception as e:
        logger.error(f"Error in logistic regression: {e}")
        import traceback
        traceback.print_exc()


def create_visualizations(df):
    """
    Create visualizations of the data.

    Args:
        df: Clean DataFrame
    """
    logger.info("\n" + "="*70)
    logger.info("CREATING VISUALIZATIONS")
    logger.info("="*70)

    output_dir = Path('analysis/results')
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Set style
        sns.set_style("whitegrid")

        # Figure 1: Distribution comparison
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        # Box plot
        df['Tony Winner'] = df['tony_win'].map({1: 'Yes', 0: 'No'})
        sns.boxplot(data=df, x='Tony Winner', y='num_total_producers', ax=axes[0])
        axes[0].set_title('Producer Counts by Tony Win Status')
        axes[0].set_ylabel('Number of Total Producers')

        # Histogram
        winners = df[df['tony_win'] == 1]['num_total_producers']
        non_winners = df[df['tony_win'] == 0]['num_total_producers']

        axes[1].hist(non_winners, alpha=0.5, label='Non-Winners', bins=15)
        axes[1].hist(winners, alpha=0.5, label='Tony Winners', bins=15)
        axes[1].set_xlabel('Number of Total Producers')
        axes[1].set_ylabel('Frequency')
        axes[1].set_title('Distribution of Producer Counts')
        axes[1].legend()

        plt.tight_layout()
        fig_path = output_dir / 'producer_counts_comparison.png'
        plt.savefig(fig_path, dpi=150, bbox_inches='tight')
        logger.info(f"✓ Saved: {fig_path}")
        plt.close()

        # Figure 2: Scatter plot with trend line
        fig, ax = plt.subplots(figsize=(10, 6))

        # Add jitter for better visibility
        jitter = 0.05
        x = df['num_total_producers']
        y = df['tony_win'] + np.random.normal(0, jitter, len(df))

        colors = df['tony_win'].map({1: 'red', 0: 'blue'})
        ax.scatter(x, y, alpha=0.5, c=colors)

        # Fit line
        from sklearn.linear_model import LogisticRegression
        lr = LogisticRegression()
        X = df[['num_total_producers']].values
        y_true = df['tony_win'].values
        lr.fit(X, y_true)

        x_range = np.linspace(X.min(), X.max(), 100).reshape(-1, 1)
        y_prob = lr.predict_proba(x_range)[:, 1]

        ax.plot(x_range, y_prob, 'g-', linewidth=2, label='Logistic Fit')

        ax.set_xlabel('Number of Total Producers')
        ax.set_ylabel('Probability of Tony Win')
        ax.set_title('Producer Count vs. Tony Win Probability')
        ax.set_ylim(-0.1, 1.1)
        ax.legend(['Logistic Fit', 'Non-Winners', 'Tony Winners'])

        fig_path = output_dir / 'producer_tony_relationship.png'
        plt.savefig(fig_path, dpi=150, bbox_inches='tight')
        logger.info(f"✓ Saved: {fig_path}")
        plt.close()

        logger.info(f"\nVisualizations saved to: {output_dir}/")

    except Exception as e:
        logger.warning(f"Could not create visualizations: {e}")


def analyze_individual_producers(df):
    """
    Analyze which specific producers have higher Tony win rates and longest-running shows.

    Args:
        df: Clean DataFrame with producer_names and num_performances columns
    """
    logger.info("\n" + "="*70)
    logger.info("INDIVIDUAL PRODUCER ANALYSIS")
    logger.info("="*70)

    if 'producer_names' not in df.columns:
        logger.warning("producer_names column not found - skipping individual producer analysis")
        return None

    # Parse producer names and track their wins and performances
    producer_stats = {}

    for _, row in df.iterrows():
        if pd.isna(row['producer_names']):
            continue

        # Split by semicolon
        producers = [p.strip() for p in str(row['producer_names']).split(';') if p.strip()]
        tony_win = row['tony_win']
        num_performances = row.get('num_performances', None)

        for producer in producers:
            if producer not in producer_stats:
                producer_stats[producer] = {
                    'wins': 0,
                    'total': 0,
                    'shows': [],
                    'total_performances': 0,
                    'performance_counts': []
                }

            producer_stats[producer]['total'] += 1
            producer_stats[producer]['wins'] += tony_win
            producer_stats[producer]['shows'].append(row['show_name'])

            # Track performances if available
            if num_performances is not None and not pd.isna(num_performances):
                producer_stats[producer]['total_performances'] += num_performances
                producer_stats[producer]['performance_counts'].append(num_performances)

    # Convert to DataFrame
    producer_df = pd.DataFrame([
        {
            'producer_name': name,
            'total_shows': stats['total'],
            'tony_wins': stats['wins'],
            'win_rate': stats['wins'] / stats['total'] if stats['total'] > 0 else 0,
            'total_performances': stats['total_performances'],
            'avg_performances': stats['total_performances'] / len(stats['performance_counts']) if len(stats['performance_counts']) > 0 else 0,
            'shows': '; '.join(stats['shows'])
        }
        for name, stats in producer_stats.items()
    ])

    # Filter producers with at least 3 shows
    producer_df_filtered = producer_df[producer_df['total_shows'] >= 3].copy()
    producer_df_filtered = producer_df_filtered.sort_values('win_rate', ascending=False)

    logger.info(f"\nTotal unique producers: {len(producer_df)}")
    logger.info(f"Producers with 3+ shows: {len(producer_df_filtered)}")

    # TOP 5 BY TONY WIN RATE
    logger.info("\n" + "="*70)
    logger.info("TOP 5 PRODUCERS BY TONY WIN RATE (min 3 shows)")
    logger.info("="*70)
    for i, row in producer_df_filtered.head(5).iterrows():
        logger.info(f"{i+1}. {row['producer_name']:50s} | {row['tony_wins']}/{row['total_shows']} wins ({row['win_rate']*100:.1f}%)")

    # Top 20 producers by win rate (with at least 3 shows)
    logger.info("\n--- TOP 20 PRODUCERS BY TONY WIN RATE (min 3 shows) ---")
    for i, row in producer_df_filtered.head(20).iterrows():
        logger.info(f"{row['producer_name']:50s} | {row['tony_wins']}/{row['total_shows']} wins ({row['win_rate']*100:.1f}%)")

    # TOP 5 BY AVERAGE PERFORMANCES (longest running shows on average)
    if 'num_performances' in df.columns:
        producer_with_perf = producer_df[(producer_df['total_shows'] >= 3) & (producer_df['avg_performances'] > 0)].copy()
        producer_with_perf = producer_with_perf.sort_values('avg_performances', ascending=False)

        logger.info("\n" + "="*70)
        logger.info("TOP 5 PRODUCERS BY AVERAGE PERFORMANCES (min 3 shows)")
        logger.info("Longest running shows on average")
        logger.info("="*70)
        for i, row in producer_with_perf.head(5).iterrows():
            logger.info(f"{i+1}. {row['producer_name']:50s} | Avg: {row['avg_performances']:.0f} perfs/show ({row['total_shows']} shows)")

        # TOP 5 BY TOTAL PERFORMANCES (most performances collectively)
        producer_by_total = producer_df[(producer_df['total_shows'] >= 3) & (producer_df['total_performances'] > 0)].copy()
        producer_by_total = producer_by_total.sort_values('total_performances', ascending=False)

        logger.info("\n" + "="*70)
        logger.info("TOP 5 PRODUCERS BY TOTAL PERFORMANCES (min 3 shows)")
        logger.info("Most performances across all shows collectively")
        logger.info("="*70)
        for i, row in producer_by_total.head(5).iterrows():
            logger.info(f"{i+1}. {row['producer_name']:50s} | Total: {row['total_performances']:.0f} perfs ({row['total_shows']} shows)")

    # Most prolific producers (10+ shows)
    prolific = producer_df[producer_df['total_shows'] >= 10].sort_values('total_shows', ascending=False)
    if len(prolific) > 0:
        logger.info("\n--- MOST PROLIFIC PRODUCERS (10+ shows) ---")
        for i, row in prolific.head(15).iterrows():
            logger.info(f"{row['producer_name']:50s} | {row['total_shows']} shows, {row['tony_wins']} wins ({row['win_rate']*100:.1f}%)")

    # Save detailed producer analysis
    output_path = Path('analysis/results/producer_success_analysis.csv')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    producer_df.sort_values('win_rate', ascending=False).to_csv(output_path, index=False)
    logger.info(f"\n✓ Saved detailed producer analysis: {output_path}")

    return producer_df


def analyze_producer_financials(df, grosses_df):
    """
    Analyze financial metrics for producers using grosses data.

    Args:
        df: Clean DataFrame with producer_names column
        grosses_df: DataFrame with Broadway grosses data

    Returns:
        DataFrame with producer financial metrics
    """
    logger.info("\n" + "="*70)
    logger.info("PRODUCER FINANCIAL ANALYSIS")
    logger.info("="*70)

    if grosses_df is None or 'producer_names' not in df.columns:
        logger.warning("Grosses data or producer_names not available - skipping financial analysis")
        return None

    # Normalize show names in both datasets for matching
    df_shows = df.copy()
    df_shows['show_name_upper'] = df_shows['show_name'].str.upper().str.strip()

    grosses_df['Show_upper'] = grosses_df['Show'].str.upper().str.strip()

    # Aggregate grosses by show
    show_grosses = grosses_df.groupby('Show_upper').agg({
        'Gross': ['sum', 'mean'],
        'Avg_Ticket': 'mean',
        'Attendance': 'sum',
        'Week': 'count'
    }).reset_index()

    show_grosses.columns = ['Show_upper', 'Total_Gross', 'Avg_Weekly_Gross', 'Avg_Ticket_Price', 'Total_Attendance', 'Num_Weeks']

    # Merge with producer data
    df_with_grosses = df_shows.merge(show_grosses, left_on='show_name_upper', right_on='Show_upper', how='left')

    # Parse producer names and aggregate financial metrics
    producer_financial_stats = {}

    for _, row in df_with_grosses.iterrows():
        if pd.isna(row['producer_names']) or pd.isna(row['Total_Gross']):
            continue

        producers = [p.strip() for p in str(row['producer_names']).split(';') if p.strip()]

        for producer in producers:
            if producer not in producer_financial_stats:
                producer_financial_stats[producer] = {
                    'total_gross': 0,
                    'gross_counts': [],
                    'ticket_prices': [],
                    'show_count': 0
                }

            producer_financial_stats[producer]['total_gross'] += row['Total_Gross']
            producer_financial_stats[producer]['gross_counts'].append(row['Total_Gross'])
            if not pd.isna(row['Avg_Ticket_Price']):
                producer_financial_stats[producer]['ticket_prices'].append(row['Avg_Ticket_Price'])
            producer_financial_stats[producer]['show_count'] += 1

    # Convert to DataFrame
    financial_df = pd.DataFrame([
        {
            'producer_name': name,
            'total_shows_with_data': stats['show_count'],
            'total_gross': stats['total_gross'],
            'avg_gross_per_show': stats['total_gross'] / stats['show_count'] if stats['show_count'] > 0 else 0,
            'avg_ticket_price': sum(stats['ticket_prices']) / len(stats['ticket_prices']) if len(stats['ticket_prices']) > 0 else 0
        }
        for name, stats in producer_financial_stats.items()
    ])

    # Filter for producers with at least 3 shows with grosses data
    financial_df_filtered = financial_df[financial_df['total_shows_with_data'] >= 3].copy()

    logger.info(f"\nProducers with financial data (3+ shows): {len(financial_df_filtered)}")

    # TOP 5 BY AVERAGE TICKET PRICE
    if len(financial_df_filtered) > 0:
        top_ticket = financial_df_filtered.sort_values('avg_ticket_price', ascending=False)

        logger.info("\n" + "="*70)
        logger.info("TOP 5 PRODUCERS BY AVERAGE TICKET PRICE (min 3 shows)")
        logger.info("="*70)
        for i, row in top_ticket.head(5).iterrows():
            logger.info(f"{i+1}. {row['producer_name']:50s} | Avg ticket: ${row['avg_ticket_price']:.2f} ({row['total_shows_with_data']} shows)")

        # TOP 5 BY AVERAGE GROSS PER SHOW
        top_avg_gross = financial_df_filtered.sort_values('avg_gross_per_show', ascending=False)

        logger.info("\n" + "="*70)
        logger.info("TOP 5 PRODUCERS BY AVERAGE GROSS PER SHOW (min 3 shows)")
        logger.info("="*70)
        for i, row in top_avg_gross.head(5).iterrows():
            logger.info(f"{i+1}. {row['producer_name']:50s} | Avg gross: ${row['avg_gross_per_show']:,.0f} ({row['total_shows_with_data']} shows)")

        # TOP 5 BY TOTAL GROSS
        top_total_gross = financial_df_filtered.sort_values('total_gross', ascending=False)

        logger.info("\n" + "="*70)
        logger.info("TOP 5 PRODUCERS BY TOTAL GROSS (min 3 shows)")
        logger.info("Most gross revenue collectively")
        logger.info("="*70)
        for i, row in top_total_gross.head(5).iterrows():
            logger.info(f"{i+1}. {row['producer_name']:50s} | Total gross: ${row['total_gross']:,.0f} ({row['total_shows_with_data']} shows)")

    # Save financial analysis
    output_path = Path('analysis/results/producer_financial_analysis.csv')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    financial_df.sort_values('total_gross', ascending=False).to_csv(output_path, index=False)
    logger.info(f"\n✓ Saved producer financial analysis: {output_path}")

    return financial_df


def analyze_yearly_trends(df):
    """
    Analyze trends in producer counts over the years.

    Args:
        df: Clean DataFrame with production_year column
    """
    logger.info("\n" + "="*70)
    logger.info("YEARLY TRENDS IN PRODUCER COUNTS")
    logger.info("="*70)

    if 'production_year' not in df.columns:
        logger.warning("production_year column not found - skipping yearly trend analysis")
        return None

    # Group by year
    df_clean = df[df['production_year'].notna()].copy()
    df_clean['production_year'] = df_clean['production_year'].astype(int)

    yearly_stats = df_clean.groupby('production_year').agg({
        'num_total_producers': ['mean', 'median', 'std', 'min', 'max', 'count'],
        'tony_win': 'sum'
    }).round(2)

    yearly_stats.columns = ['mean_producers', 'median_producers', 'std_producers',
                           'min_producers', 'max_producers', 'num_shows', 'tony_wins']
    yearly_stats = yearly_stats.reset_index()

    logger.info(f"\nYearly producer count statistics:")
    logger.info(f"\n{yearly_stats.to_string(index=False)}")

    # Calculate trend
    years = yearly_stats['production_year'].values.reshape(-1, 1)
    mean_producers = yearly_stats['mean_producers'].values

    # Fit linear regression
    model = LinearRegression()
    model.fit(years, mean_producers)
    slope = model.coef_[0]
    intercept = model.intercept_

    logger.info(f"\n--- TREND ANALYSIS ---")
    logger.info(f"Linear trend: y = {slope:.3f}x + {intercept:.1f}")

    if abs(slope) < 0.05:
        logger.info(f"→ Producer counts are relatively STABLE over time")
    elif slope > 0:
        logger.info(f"→ Producer counts are INCREASING by ~{slope:.2f} per year")
    else:
        logger.info(f"→ Producer counts are DECREASING by ~{abs(slope):.2f} per year")

    # Save yearly stats
    output_path = Path('analysis/results/yearly_producer_trends.csv')
    yearly_stats.to_csv(output_path, index=False)
    logger.info(f"\n✓ Saved yearly trends: {output_path}")

    return yearly_stats, model


def predict_future_producers(yearly_stats, model):
    """
    Predict producer counts for the next 5 years.

    Args:
        yearly_stats: DataFrame with yearly statistics
        model: Fitted LinearRegression model
    """
    logger.info("\n" + "="*70)
    logger.info("5-YEAR PREDICTION FOR PRODUCER COUNTS")
    logger.info("="*70)

    if yearly_stats is None or model is None:
        logger.warning("Skipping prediction - yearly trend analysis not available")
        return None

    # Get last year in data
    last_year = int(yearly_stats['production_year'].max())

    # Predict next 5 years
    future_years = np.array(range(last_year + 1, last_year + 6)).reshape(-1, 1)
    predictions = model.predict(future_years)

    logger.info(f"\nProjected mean producer counts (based on linear trend):")
    logger.info(f"{'Year':<10} {'Predicted Mean Producers':<30}")
    logger.info("-" * 50)

    for year, pred in zip(future_years.flatten(), predictions):
        logger.info(f"{year:<10} {pred:.2f}")

    # Calculate confidence based on historical variance
    historical_std = yearly_stats['mean_producers'].std()

    logger.info(f"\n--- PREDICTION CONFIDENCE ---")
    logger.info(f"Historical standard deviation: ±{historical_std:.2f} producers")
    logger.info(f"95% prediction interval: approximately ±{1.96 * historical_std:.2f} producers")

    logger.info(f"\n--- INTERPRETATION ---")
    last_mean = yearly_stats['mean_producers'].iloc[-1]
    change = predictions[-1] - last_mean

    if abs(change) < 1:
        logger.info(f"Producer counts expected to remain STABLE (~{last_mean:.1f} producers)")
    elif change > 0:
        logger.info(f"Producer counts expected to INCREASE from {last_mean:.1f} to {predictions[-1]:.1f} by {future_years[-1][0]}")
    else:
        logger.info(f"Producer counts expected to DECREASE from {last_mean:.1f} to {predictions[-1]:.1f} by {future_years[-1][0]}")

    # Save predictions
    prediction_df = pd.DataFrame({
        'year': future_years.flatten(),
        'predicted_mean_producers': predictions,
        'lower_bound_95': predictions - 1.96 * historical_std,
        'upper_bound_95': predictions + 1.96 * historical_std
    })

    output_path = Path('analysis/results/producer_count_predictions.csv')
    prediction_df.to_csv(output_path, index=False)
    logger.info(f"\n✓ Saved predictions: {output_path}")

    return prediction_df


def create_enhanced_visualizations(df, yearly_stats, prediction_df, producer_df, financial_df=None):
    """
    Create enhanced visualizations including trends and predictions.

    Args:
        df: Clean DataFrame
        yearly_stats: Yearly statistics DataFrame
        prediction_df: Future predictions DataFrame
        producer_df: Producer analysis DataFrame
    """
    logger.info("\n" + "="*70)
    logger.info("CREATING ENHANCED VISUALIZATIONS")
    logger.info("="*70)

    output_dir = Path('analysis/results')
    output_dir.mkdir(parents=True, exist_ok=True)

    sns.set_style("whitegrid")

    try:
        # Figure 1: Yearly trends with predictions
        if yearly_stats is not None and prediction_df is not None:
            fig, ax = plt.subplots(figsize=(12, 6))

            # Historical data
            ax.plot(yearly_stats['production_year'], yearly_stats['mean_producers'],
                   'o-', linewidth=2, markersize=8, label='Historical Mean', color='blue')
            ax.fill_between(yearly_stats['production_year'],
                           yearly_stats['mean_producers'] - yearly_stats['std_producers'],
                           yearly_stats['mean_producers'] + yearly_stats['std_producers'],
                           alpha=0.2, color='blue', label='±1 Std Dev')

            # Predictions
            ax.plot(prediction_df['year'], prediction_df['predicted_mean_producers'],
                   'o--', linewidth=2, markersize=8, label='Predicted Mean', color='red')
            ax.fill_between(prediction_df['year'],
                           prediction_df['lower_bound_95'],
                           prediction_df['upper_bound_95'],
                           alpha=0.2, color='red', label='95% Prediction Interval')

            ax.set_xlabel('Year', fontsize=12)
            ax.set_ylabel('Mean Number of Producers', fontsize=12)
            ax.set_title('Producer Count Trends and 5-Year Forecast', fontsize=14, fontweight='bold')
            ax.legend(loc='best')
            ax.grid(True, alpha=0.3)

            fig_path = output_dir / 'producer_trends_forecast.png'
            plt.savefig(fig_path, dpi=150, bbox_inches='tight')
            logger.info(f"✓ Saved: {fig_path}")
            plt.close()

        # Figure 2: Top producers by win rate
        if producer_df is not None:
            top_producers = producer_df[producer_df['total_shows'] >= 5].sort_values('win_rate', ascending=False).head(15)

            if len(top_producers) > 0:
                fig, ax = plt.subplots(figsize=(12, 8))

                bars = ax.barh(range(len(top_producers)), top_producers['win_rate'] * 100)
                ax.set_yticks(range(len(top_producers)))
                ax.set_yticklabels(top_producers['producer_name'])
                ax.set_xlabel('Tony Win Rate (%)', fontsize=12)
                ax.set_title('Top 15 Producers by Tony Win Rate (5+ shows)', fontsize=14, fontweight='bold')
                ax.grid(axis='x', alpha=0.3)

                # Add value labels
                for i, (idx, row) in enumerate(top_producers.iterrows()):
                    ax.text(row['win_rate'] * 100 + 1, i,
                           f"{row['win_rate']*100:.1f}% ({row['tony_wins']}/{row['total_shows']})",
                           va='center', fontsize=9)

                fig_path = output_dir / 'top_producers_win_rate.png'
                plt.savefig(fig_path, dpi=150, bbox_inches='tight')
                logger.info(f"✓ Saved: {fig_path}")
                plt.close()

        # Figure 3: Top producers by average performances
        if producer_df is not None and 'avg_performances' in producer_df.columns:
            top_avg_perf = producer_df[(producer_df['total_shows'] >= 3) & (producer_df['avg_performances'] > 0)].sort_values('avg_performances', ascending=False).head(10)

            if len(top_avg_perf) > 0:
                fig, ax = plt.subplots(figsize=(12, 8))

                bars = ax.barh(range(len(top_avg_perf)), top_avg_perf['avg_performances'])
                ax.set_yticks(range(len(top_avg_perf)))
                ax.set_yticklabels(top_avg_perf['producer_name'])
                ax.set_xlabel('Average Performances per Show', fontsize=12)
                ax.set_title('Top 10 Producers by Average Show Length (3+ shows)', fontsize=14, fontweight='bold')
                ax.grid(axis='x', alpha=0.3)

                # Add value labels
                for i, (idx, row) in enumerate(top_avg_perf.iterrows()):
                    ax.text(row['avg_performances'] + 20, i,
                           f"{row['avg_performances']:.0f} perfs ({row['total_shows']} shows)",
                           va='center', fontsize=9)

                fig_path = output_dir / 'top_producers_avg_performances.png'
                plt.savefig(fig_path, dpi=150, bbox_inches='tight')
                logger.info(f"✓ Saved: {fig_path}")
                plt.close()

        # Figure 4: Top producers by total performances
        if producer_df is not None and 'total_performances' in producer_df.columns:
            top_total_perf = producer_df[(producer_df['total_shows'] >= 3) & (producer_df['total_performances'] > 0)].sort_values('total_performances', ascending=False).head(10)

            if len(top_total_perf) > 0:
                fig, ax = plt.subplots(figsize=(12, 8))

                bars = ax.barh(range(len(top_total_perf)), top_total_perf['total_performances'])
                ax.set_yticks(range(len(top_total_perf)))
                ax.set_yticklabels(top_total_perf['producer_name'])
                ax.set_xlabel('Total Performances Across All Shows', fontsize=12)
                ax.set_title('Top 10 Producers by Total Performances (3+ shows)', fontsize=14, fontweight='bold')
                ax.grid(axis='x', alpha=0.3)

                # Add value labels
                for i, (idx, row) in enumerate(top_total_perf.iterrows()):
                    ax.text(row['total_performances'] + 100, i,
                           f"{row['total_performances']:.0f} perfs ({row['total_shows']} shows)",
                           va='center', fontsize=9)

                fig_path = output_dir / 'top_producers_total_performances.png'
                plt.savefig(fig_path, dpi=150, bbox_inches='tight')
                logger.info(f"✓ Saved: {fig_path}")
                plt.close()

        # Figure 5: Top producers by average ticket price
        if financial_df is not None and len(financial_df) > 0:
            top_ticket_price = financial_df[financial_df['total_shows_with_data'] >= 3].sort_values('avg_ticket_price', ascending=False).head(10)

            if len(top_ticket_price) > 0:
                fig, ax = plt.subplots(figsize=(12, 8))

                bars = ax.barh(range(len(top_ticket_price)), top_ticket_price['avg_ticket_price'])
                ax.set_yticks(range(len(top_ticket_price)))
                ax.set_yticklabels(top_ticket_price['producer_name'])
                ax.set_xlabel('Average Ticket Price ($)', fontsize=12)
                ax.set_title('Top 10 Producers by Average Ticket Price (3+ shows)', fontsize=14, fontweight='bold')
                ax.grid(axis='x', alpha=0.3)

                # Add value labels
                for i, (idx, row) in enumerate(top_ticket_price.iterrows()):
                    ax.text(row['avg_ticket_price'] + 2, i,
                           f"${row['avg_ticket_price']:.2f} ({row['total_shows_with_data']} shows)",
                           va='center', fontsize=9)

                fig_path = output_dir / 'top_producers_avg_ticket_price.png'
                plt.savefig(fig_path, dpi=150, bbox_inches='tight')
                logger.info(f"✓ Saved: {fig_path}")
                plt.close()

        # Figure 6: Top producers by average gross per show
        if financial_df is not None and len(financial_df) > 0:
            top_avg_gross = financial_df[financial_df['total_shows_with_data'] >= 3].sort_values('avg_gross_per_show', ascending=False).head(10)

            if len(top_avg_gross) > 0:
                fig, ax = plt.subplots(figsize=(12, 8))

                bars = ax.barh(range(len(top_avg_gross)), top_avg_gross['avg_gross_per_show'] / 1_000_000)
                ax.set_yticks(range(len(top_avg_gross)))
                ax.set_yticklabels(top_avg_gross['producer_name'])
                ax.set_xlabel('Average Gross per Show (Millions $)', fontsize=12)
                ax.set_title('Top 10 Producers by Average Gross per Show (3+ shows)', fontsize=14, fontweight='bold')
                ax.grid(axis='x', alpha=0.3)

                # Add value labels
                for i, (idx, row) in enumerate(top_avg_gross.iterrows()):
                    ax.text(row['avg_gross_per_show'] / 1_000_000 + 5, i,
                           f"${row['avg_gross_per_show']/1_000_000:.1f}M ({row['total_shows_with_data']} shows)",
                           va='center', fontsize=9)

                fig_path = output_dir / 'top_producers_avg_gross.png'
                plt.savefig(fig_path, dpi=150, bbox_inches='tight')
                logger.info(f"✓ Saved: {fig_path}")
                plt.close()

        # Figure 7: Top producers by total gross
        if financial_df is not None and len(financial_df) > 0:
            top_total_gross = financial_df[financial_df['total_shows_with_data'] >= 3].sort_values('total_gross', ascending=False).head(10)

            if len(top_total_gross) > 0:
                fig, ax = plt.subplots(figsize=(12, 8))

                bars = ax.barh(range(len(top_total_gross)), top_total_gross['total_gross'] / 1_000_000)
                ax.set_yticks(range(len(top_total_gross)))
                ax.set_yticklabels(top_total_gross['producer_name'])
                ax.set_xlabel('Total Gross Revenue (Millions $)', fontsize=12)
                ax.set_title('Top 10 Producers by Total Gross Revenue (3+ shows)', fontsize=14, fontweight='bold')
                ax.grid(axis='x', alpha=0.3)

                # Add value labels
                for i, (idx, row) in enumerate(top_total_gross.iterrows()):
                    ax.text(row['total_gross'] / 1_000_000 + 20, i,
                           f"${row['total_gross']/1_000_000:.1f}M ({row['total_shows_with_data']} shows)",
                           va='center', fontsize=9)

                fig_path = output_dir / 'top_producers_total_gross.png'
                plt.savefig(fig_path, dpi=150, bbox_inches='tight')
                logger.info(f"✓ Saved: {fig_path}")
                plt.close()

        logger.info(f"\nEnhanced visualizations saved to: {output_dir}/")

    except Exception as e:
        logger.warning(f"Could not create enhanced visualizations: {e}")
        import traceback
        traceback.print_exc()


def save_results(df, producer_df=None, yearly_stats=None, financial_df=None):
    """
    Save analysis dataset and summary.

    Args:
        df: Clean DataFrame
        producer_df: Producer analysis DataFrame (optional)
        yearly_stats: Yearly statistics DataFrame (optional)
        financial_df: Producer financial analysis DataFrame (optional)
    """
    logger.info("\n" + "="*70)
    logger.info("SAVING RESULTS")
    logger.info("="*70)

    output_dir = Path('data')

    # Save analysis dataset
    output_path = output_dir / 'producer_tony_analysis.csv'
    df.to_csv(output_path, index=False)
    logger.info(f"✓ Saved analysis dataset: {output_path}")

    # Create summary file
    summary_path = Path('analysis/results/analysis_summary.txt')
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    with open(summary_path, 'w') as f:
        f.write("="*70 + "\n")
        f.write("BROADWAY PRODUCER & TONY AWARDS ANALYSIS - SUMMARY\n")
        f.write("="*70 + "\n\n")

        f.write(f"Analysis Date: {pd.Timestamp.now()}\n\n")

        f.write("DATASET\n")
        f.write("-"*70 + "\n")
        f.write(f"Total Shows: {len(df)}\n")
        f.write(f"Tony Winners: {df['tony_win'].sum()}\n")
        f.write(f"Non-Winners: {(1-df['tony_win']).sum()}\n\n")

        # Producer counts (if available)
        if 'num_total_producers' in df.columns and df['num_total_producers'].notna().any():
            f.write("PRODUCER COUNTS\n")
            f.write("-"*70 + "\n")
            producer_data = df[df['num_total_producers'].notna()]
            f.write(f"Overall Mean: {producer_data['num_total_producers'].mean():.2f}\n")
            if (producer_data['tony_win']==1).any():
                f.write(f"Winners Mean: {producer_data[producer_data['tony_win']==1]['num_total_producers'].mean():.2f}\n")
            if (producer_data['tony_win']==0).any():
                f.write(f"Non-Winners Mean: {producer_data[producer_data['tony_win']==0]['num_total_producers'].mean():.2f}\n")
            f.write("\n")

        if producer_df is not None:
            f.write("INDIVIDUAL PRODUCERS\n")
            f.write("-"*70 + "\n")
            f.write(f"Total Unique Producers: {len(producer_df)}\n")
            top_producer = producer_df[producer_df['total_shows'] >= 3].sort_values('win_rate', ascending=False).iloc[0]
            f.write(f"Top Producer (3+ shows): {top_producer['producer_name']} ({top_producer['win_rate']*100:.1f}% win rate)\n\n")

        if yearly_stats is not None:
            f.write("YEARLY TRENDS\n")
            f.write("-"*70 + "\n")
            f.write(f"Years Covered: {int(yearly_stats['production_year'].min())} - {int(yearly_stats['production_year'].max())}\n")
            f.write(f"Recent Year Mean Producers: {yearly_stats['mean_producers'].iloc[-1]:.2f}\n\n")

        if financial_df is not None and len(financial_df) > 0:
            f.write("FINANCIAL METRICS\n")
            f.write("-"*70 + "\n")
            top_gross_producer = financial_df[financial_df['total_shows_with_data'] >= 3].sort_values('total_gross', ascending=False).iloc[0]
            f.write(f"Top Producer by Total Gross (3+ shows): {top_gross_producer['producer_name']} (${top_gross_producer['total_gross']/1e6:.1f}M)\n")
            top_ticket_producer = financial_df[financial_df['total_shows_with_data'] >= 3].sort_values('avg_ticket_price', ascending=False).iloc[0]
            f.write(f"Top Producer by Avg Ticket Price (3+ shows): {top_ticket_producer['producer_name']} (${top_ticket_producer['avg_ticket_price']:.2f})\n\n")

        f.write("See full log file for detailed statistical results.\n")

    logger.info(f"✓ Saved summary: {summary_path}")


def main():
    """Main analysis entry point."""
    logger.info("="*70)
    logger.info("BROADWAY PRODUCER & TONY AWARDS ANALYSIS")
    logger.info("="*70)

    try:
        # Load and merge data
        df, grosses_df = load_and_merge_data()

        # Clean data
        df_clean = clean_data(df)

        if len(df_clean) == 0:
            logger.error("No data available for analysis after cleaning")
            return 1

        # Check if we have producer data
        has_producer_data = 'num_total_producers' in df_clean.columns and df_clean['num_total_producers'].notna().any()

        # Run basic analyses (only if we have producer data)
        if has_producer_data:
            descriptive_stats(df_clean)
            statistical_tests(df_clean)
            logistic_regression(df_clean)
        else:
            logger.warning("\n⚠️  Skipping producer-based analyses - no producer count data available")
            logger.info("Run browser_ibdb_scraper.py to collect producer data, then re-run this analysis")

        # Run enhanced analyses
        producer_df = None
        if has_producer_data:
            producer_df = analyze_individual_producers(df_clean)

        # Run financial analysis if grosses data is available
        financial_df = None
        if grosses_df is not None and has_producer_data:
            financial_df = analyze_producer_financials(df_clean, grosses_df)

        yearly_result = None
        if has_producer_data:
            yearly_result = analyze_yearly_trends(df_clean)
        if yearly_result is not None:
            yearly_stats, model = yearly_result
            prediction_df = predict_future_producers(yearly_stats, model)
        else:
            yearly_stats = None
            prediction_df = None

        # Create all visualizations (only if we have producer data)
        if has_producer_data:
            create_visualizations(df_clean)
            create_enhanced_visualizations(df_clean, yearly_stats, prediction_df, producer_df, financial_df)
        else:
            logger.info("\n⚠️  Skipping visualizations - requires producer data")

        # Save results
        save_results(df_clean, producer_df, yearly_stats, financial_df)

        logger.info("\n" + "="*70)
        logger.info("✓✓✓ ANALYSIS COMPLETE ✓✓✓")
        logger.info("="*70)
        logger.info("\nResults saved to:")
        logger.info("  - data/producer_tony_analysis.csv (analysis dataset)")
        logger.info("  - analysis/results/producer_success_analysis.csv (individual producer stats)")
        logger.info("  - analysis/results/producer_financial_analysis.csv (financial metrics)")
        logger.info("  - analysis/results/yearly_producer_trends.csv (yearly trends)")
        logger.info("  - analysis/results/producer_count_predictions.csv (5-year forecast)")
        logger.info("  - analysis/results/ (visualizations including financial charts)")
        logger.info("  - logs/analysis.log (detailed output)")

        return 0

    except FileNotFoundError as e:
        logger.error(f"\n{e}")
        logger.error("\nPlease collect data using the manual templates:")
        logger.error("  - See: MANUAL_DATA_COLLECTION_GUIDE.md")
        logger.error("  - Templates in: data/templates/")
        return 1

    except Exception as e:
        logger.error(f"Error in analysis: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
