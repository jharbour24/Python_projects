#!/usr/bin/env python3
"""
Complete Causal Analysis with All Data Sources

Runs comprehensive lagged causality analysis using:
- Reddit engagement metrics
- TikTok metrics
- Instagram metrics
- Wikipedia pageviews
- Google Trends
- Broadway box office grosses

Tests whether social engagement at t-k predicts grosses at t.

Usage:
    python -m public_signals.cli.run_complete_analysis \
        --input data/panel/complete_modeling_dataset.parquet \
        --output outputs/complete_causality_analysis/
"""

import argparse
import pandas as pd
import numpy as np
import logging
import sys
from pathlib import Path
import json
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from models.lagged_causality import LaggedCausalityModels
from analysis.feature_engineering import capacity_constraint_flag

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def prepare_data_for_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare merged dataset for causal analysis.

    Args:
        df: Complete merged panel

    Returns:
        DataFrame ready for modeling
    """
    logger.info("Preparing data for analysis...")

    df = df.copy()

    # Filter to rows with grosses (outcome variable)
    initial_rows = len(df)
    df = df[df['has_grosses'] == 1].copy()
    logger.info(f"  Filtered to {len(df)} rows with grosses (from {initial_rows})")

    # Add capacity constraint flag if not present
    if 'capacity_constraint' not in df.columns and 'capacity_pct' in df.columns:
        df = capacity_constraint_flag(df, cap_col='capacity_pct', threshold=0.98)
        logger.info(f"  Added capacity constraint flag")

    # Add week index for time fixed effects
    if 'week_start' in df.columns:
        df['week_start_dt'] = pd.to_datetime(df['week_start'])
        df = df.sort_values('week_start_dt')
        unique_weeks = df['week_start_dt'].unique()
        week_to_index = {week: idx for idx, week in enumerate(unique_weeks)}
        df['week_index'] = df['week_start_dt'].map(week_to_index)
        logger.info(f"  Created week_index: {df['week_index'].nunique()} unique weeks")

    # Ensure show_id exists
    if 'show_id' not in df.columns:
        show_to_id = {show: idx for idx, show in enumerate(df['show'].unique())}
        df['show_id'] = df['show'].map(show_to_id)
        logger.info(f"  Created show_id: {df['show_id'].nunique()} unique shows")

    logger.info(f"✓ Data ready: {len(df)} rows")

    return df


def identify_predictors(df: pd.DataFrame, lag: int = 4) -> dict:
    """
    Identify all available lagged predictors.

    Args:
        df: DataFrame with engineered features
        lag: Lag period to focus on

    Returns:
        Dict categorizing predictors by source
    """
    predictors = {
        'reddit': [],
        'tiktok': [],
        'instagram': [],
        'wikipedia': [],
        'google_trends': [],
        'all': []
    }

    lag_suffix = f'_lag{lag}'

    for col in df.columns:
        if lag_suffix not in col:
            continue

        predictors['all'].append(col)

        # Categorize by source
        if 'total_posts' in col or 'total_score' in col or 'unique_authors' in col or 'total_comments' in col:
            predictors['reddit'].append(col)
        elif col.startswith('tt_'):
            predictors['tiktok'].append(col)
        elif col.startswith('ig_'):
            predictors['instagram'].append(col)
        elif 'wiki_views' in col:
            predictors['wikipedia'].append(col)
        elif 'gt_index' in col:
            predictors['google_trends'].append(col)

    return predictors


def run_analysis_for_predictor(
    models: LaggedCausalityModels,
    df: pd.DataFrame,
    predictor: str,
    outcome: str = 'gross',
    controls: list = None
) -> dict:
    """
    Run OLS-FE analysis for a single predictor.

    Args:
        models: LaggedCausalityModels instance
        df: Panel DataFrame
        predictor: Predictor variable name
        outcome: Outcome variable name
        controls: List of control variables

    Returns:
        Dict with results
    """
    if controls is None:
        controls = ['capacity_constraint', 'week_index']

    # Check if predictor has sufficient non-null values
    non_null = df[predictor].notna().sum()
    if non_null < 30:
        logger.warning(f"  {predictor}: Insufficient data ({non_null} non-null), skipping")
        return None

    try:
        result = models.fit_ols_fe(
            df,
            outcome=outcome,
            predictor=predictor,
            controls=controls
        )

        # Add predictor name
        result['predictor'] = predictor

        return result

    except Exception as e:
        logger.warning(f"  {predictor}: Error - {e}")
        return None


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run complete causal analysis with all data sources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic analysis (lag 4, gross outcome)
    python -m public_signals.cli.run_complete_analysis

    # Custom lag
    python -m public_signals.cli.run_complete_analysis --lag 2

    # Different outcome
    python -m public_signals.cli.run_complete_analysis --outcome capacity_pct

    # Custom paths
    python -m public_signals.cli.run_complete_analysis \
        --input data/panel/complete_modeling_dataset.parquet \
        --output outputs/complete_causality_analysis/

Output:
    - JSON with results for all predictors
    - CSV with sorted results (by p-value)
    - Text report with significant findings
        """
    )

    parser.add_argument(
        '--input',
        type=str,
        default='data/panel/complete_modeling_dataset.parquet',
        help='Path to complete merged dataset'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='outputs/complete_causality_analysis',
        help='Output directory'
    )

    parser.add_argument(
        '--lag',
        type=int,
        default=4,
        help='Lag period in weeks (default: 4)'
    )

    parser.add_argument(
        '--outcome',
        type=str,
        default='gross',
        choices=['gross', 'capacity_pct', 'avg_ticket_price'],
        help='Outcome variable (default: gross)'
    )

    parser.add_argument(
        '--min-obs',
        type=int,
        default=30,
        help='Minimum non-null observations required per predictor (default: 30)'
    )

    args = parser.parse_args()

    # Load data
    input_path = Path(args.input)

    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    logger.info(f"Loading dataset: {input_path}")

    try:
        df = pd.read_parquet(input_path)
        logger.info(f"  Loaded {len(df)} rows, {len(df.columns)} columns")
    except Exception as e:
        logger.error(f"Error loading dataset: {e}")
        sys.exit(1)

    # Prepare data
    try:
        df = prepare_data_for_analysis(df)
    except Exception as e:
        logger.error(f"Error preparing data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Identify predictors
    logger.info(f"\nIdentifying lag-{args.lag} predictors...")
    predictors_by_source = identify_predictors(df, lag=args.lag)

    logger.info(f"\nPredictors by source:")
    for source, preds in predictors_by_source.items():
        if source != 'all':
            logger.info(f"  {source:15s}: {len(preds)} predictors")

    if not predictors_by_source['all']:
        logger.error("No lagged predictors found. Did you engineer features with --engineer-features?")
        sys.exit(1)

    # Run analysis
    logger.info(f"\n{'='*70}")
    logger.info(f"RUNNING CAUSAL ANALYSIS: {args.outcome} ~ predictors_lag{args.lag}")
    logger.info(f"{'='*70}\n")

    models = LaggedCausalityModels()
    results = []

    for predictor in predictors_by_source['all']:
        logger.info(f"Testing: {predictor}")

        result = run_analysis_for_predictor(
            models,
            df,
            predictor,
            outcome=args.outcome
        )

        if result:
            results.append(result)
            logger.info(f"  Coef: {result['coefficient']:.2f}, "
                       f"P-value: {result['pvalue']:.4f}, "
                       f"95% CI: [{result['ci_lower']:.2f}, {result['ci_upper']:.2f}]")

    if not results:
        logger.error("No results generated. Check data quality and predictor availability.")
        sys.exit(1)

    # Create results DataFrame
    results_df = pd.DataFrame(results)

    # Sort by p-value
    results_df = results_df.sort_values('pvalue')

    # Add significance flags
    results_df['significant_05'] = results_df['pvalue'] < 0.05
    results_df['significant_01'] = results_df['pvalue'] < 0.01

    # Add source category
    def categorize_source(pred):
        if 'total_posts' in pred or 'total_score' in pred or 'unique_authors' in pred:
            return 'reddit'
        elif pred.startswith('tt_'):
            return 'tiktok'
        elif pred.startswith('ig_'):
            return 'instagram'
        elif 'wiki_views' in pred:
            return 'wikipedia'
        elif 'gt_index' in pred:
            return 'google_trends'
        return 'other'

    results_df['source'] = results_df['predictor'].apply(categorize_source)

    # Save outputs
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    logger.info(f"\n{'='*70}")
    logger.info("SAVING RESULTS")
    logger.info(f"{'='*70}")

    # Save JSON
    json_path = output_dir / f"complete_analysis_lag{args.lag}_{timestamp}.json"
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"✓ Saved JSON: {json_path}")

    # Save CSV
    csv_path = output_dir / f"complete_analysis_lag{args.lag}_{timestamp}.csv"
    results_df.to_csv(csv_path, index=False)
    logger.info(f"✓ Saved CSV: {csv_path}")

    # Generate text report
    txt_path = output_dir / f"complete_analysis_lag{args.lag}_{timestamp}.txt"

    with open(txt_path, 'w') as f:
        f.write("="*70 + "\n")
        f.write(f"COMPLETE CAUSAL ANALYSIS: {args.outcome} ~ predictors_lag{args.lag}\n")
        f.write("="*70 + "\n\n")

        f.write(f"Dataset: {input_path}\n")
        f.write(f"Observations: {len(df)}\n")
        f.write(f"Shows: {df['show'].nunique()}\n")
        f.write(f"Predictors tested: {len(results)}\n\n")

        # Summary by source
        f.write("SUMMARY BY SOURCE\n")
        f.write("-"*70 + "\n")
        for source in ['reddit', 'tiktok', 'instagram', 'wikipedia', 'google_trends']:
            source_results = results_df[results_df['source'] == source]
            if len(source_results) > 0:
                sig_count = source_results['significant_05'].sum()
                f.write(f"{source:15s}: {len(source_results)} predictors, {sig_count} significant (p<0.05)\n")

        # Significant results
        sig_results = results_df[results_df['significant_05'] == True]

        f.write(f"\n{'='*70}\n")
        f.write(f"SIGNIFICANT RESULTS (p < 0.05): {len(sig_results)}\n")
        f.write("="*70 + "\n\n")

        if len(sig_results) > 0:
            for idx, row in sig_results.iterrows():
                f.write(f"Predictor: {row['predictor']}\n")
                f.write(f"  Source: {row['source']}\n")
                f.write(f"  Coefficient: {row['coefficient']:.2f}\n")
                f.write(f"  P-value: {row['pvalue']:.4f}\n")
                f.write(f"  95% CI: [{row['ci_lower']:.2f}, {row['ci_upper']:.2f}]\n")
                f.write(f"  R²: {row['r_squared']:.3f}\n")
                f.write(f"  Observations: {row['n_obs']}\n")
                f.write("\n")
        else:
            f.write("No significant results at p < 0.05\n")

        # Top 10 by p-value
        f.write(f"\n{'='*70}\n")
        f.write("TOP 10 PREDICTORS (by p-value)\n")
        f.write("="*70 + "\n\n")

        for idx, row in results_df.head(10).iterrows():
            f.write(f"{idx+1}. {row['predictor']} ({row['source']})\n")
            f.write(f"   Coef: {row['coefficient']:.2f}, P: {row['pvalue']:.4f}, ")
            f.write(f"CI: [{row['ci_lower']:.2f}, {row['ci_upper']:.2f}]\n")

    logger.info(f"✓ Saved report: {txt_path}")

    # Print summary
    logger.info(f"\n{'='*70}")
    logger.info("ANALYSIS COMPLETE")
    logger.info("="*70)

    sig_count = results_df['significant_05'].sum()
    logger.info(f"\nResults: {len(results)} predictors tested")
    logger.info(f"Significant (p<0.05): {sig_count}")

    if sig_count > 0:
        logger.info(f"\nTop significant predictor:")
        top = results_df.iloc[0]
        logger.info(f"  {top['predictor']} ({top['source']})")
        logger.info(f"  Coefficient: {top['coefficient']:.2f}")
        logger.info(f"  P-value: {top['pvalue']:.4f}")

    logger.info(f"\nOutputs saved to: {output_dir}")


if __name__ == '__main__':
    main()
