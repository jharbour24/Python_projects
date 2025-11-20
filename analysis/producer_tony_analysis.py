#!/usr/bin/env python3
"""
Statistical analysis of relationship between producer counts and Tony Award wins.

Analyzes whether Broadway shows with more producers are more/less likely to win Tony Awards.
Uses logistic regression to model the relationship.
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

from utils import setup_logger

logger = setup_logger(__name__, log_file='logs/analysis.log')


def load_and_merge_data():
    """
    Load producer counts and Tony outcomes, merge them.

    Returns:
        Merged DataFrame
    """
    logger.info("Loading data...")

    # Try different file names
    producer_files = [
        'data/show_producer_counts_manual.csv',
        'data/show_producer_counts_ibdb.csv',
    ]

    tony_files = [
        'data/tony_outcomes_manual.csv',
        'data/tony_outcomes.csv',
    ]

    # Load producer data
    producer_df = None
    for file_path in producer_files:
        if Path(file_path).exists():
            logger.info(f"Loading producer data from: {file_path}")
            producer_df = pd.read_csv(file_path)
            break

    if producer_df is None:
        raise FileNotFoundError(
            f"No producer data found. Please create one of: {producer_files}\n"
            f"Use templates in data/templates/ for manual data entry."
        )

    # Load Tony data
    tony_df = None
    for file_path in tony_files:
        if Path(file_path).exists():
            logger.info(f"Loading Tony outcomes from: {file_path}")
            tony_df = pd.read_csv(file_path)
            break

    if tony_df is None:
        raise FileNotFoundError(
            f"No Tony outcomes data found. Please create one of: {tony_files}\n"
            f"Use templates in data/templates/ for manual data entry."
        )

    # Merge on show_name
    logger.info(f"Merging datasets...")
    logger.info(f"  Producer data: {len(producer_df)} shows")
    logger.info(f"  Tony data: {len(tony_df)} shows")

    merged_df = producer_df.merge(
        tony_df[['show_name', 'tony_win', 'tony_category', 'tony_year']],
        on='show_name',
        how='inner'
    )

    logger.info(f"  Merged: {len(merged_df)} shows")

    return merged_df


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
    df['num_total_producers'] = pd.to_numeric(df['num_total_producers'], errors='coerce')
    df['tony_win'] = pd.to_numeric(df['tony_win'], errors='coerce')

    # Drop rows missing critical data
    df_clean = df.dropna(subset=['num_total_producers', 'tony_win']).copy()

    logger.info(f"  Dropped {initial_count - len(df_clean)} rows with missing data")
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


def save_results(df):
    """
    Save analysis dataset and summary.

    Args:
        df: Clean DataFrame
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

        f.write("PRODUCER COUNTS\n")
        f.write("-"*70 + "\n")
        f.write(f"Overall Mean: {df['num_total_producers'].mean():.2f}\n")
        f.write(f"Winners Mean: {df[df['tony_win']==1]['num_total_producers'].mean():.2f}\n")
        f.write(f"Non-Winners Mean: {df[df['tony_win']==0]['num_total_producers'].mean():.2f}\n\n")

        f.write("See full log file for detailed statistical results.\n")

    logger.info(f"✓ Saved summary: {summary_path}")


def main():
    """Main analysis entry point."""
    logger.info("="*70)
    logger.info("BROADWAY PRODUCER & TONY AWARDS ANALYSIS")
    logger.info("="*70)

    try:
        # Load and merge data
        df = load_and_merge_data()

        # Clean data
        df_clean = clean_data(df)

        if len(df_clean) == 0:
            logger.error("No data available for analysis after cleaning")
            return 1

        # Run analyses
        descriptive_stats(df_clean)
        statistical_tests(df_clean)
        logistic_regression(df_clean)
        create_visualizations(df_clean)
        save_results(df_clean)

        logger.info("\n" + "="*70)
        logger.info("✓✓✓ ANALYSIS COMPLETE ✓✓✓")
        logger.info("="*70)
        logger.info("\nResults saved to:")
        logger.info("  - data/producer_tony_analysis.csv (analysis dataset)")
        logger.info("  - analysis/results/ (visualizations and summary)")
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
