#!/usr/bin/env python3
"""
Run Lagged Causality Analysis

CLI tool to estimate causal effects of social media engagement on box office grosses
using panel regression methods with lagged predictors.

Usage:
    python3 run_lagged_causality_analysis.py --lag 4 --outcome gross
    python3 run_lagged_causality_analysis.py --lag 4 --outcome capacity_percent --no-fe
    python3 run_lagged_causality_analysis.py --sensitivity  # test lags 1,2,4,6
    python3 run_lagged_causality_analysis.py --granger --max-lag 6
"""

import pandas as pd
import numpy as np
import argparse
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from models.lagged_causality import LaggedCausalityModels

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CausalityAnalysisRunner:
    """Orchestrates lagged causality analysis with various specifications."""

    def __init__(self, data_path: str):
        """
        Initialize runner.

        Args:
            data_path: Path to merged panel dataset (parquet or csv)
        """
        self.data_path = Path(data_path)
        self.output_dir = Path("outputs/lagged_causality")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load data
        logger.info(f"Loading panel data from: {self.data_path}")
        if self.data_path.suffix == '.parquet':
            self.df = pd.read_parquet(self.data_path)
        elif self.data_path.suffix == '.csv':
            self.df = pd.read_csv(self.data_path)
        else:
            raise ValueError(f"Unsupported file format: {self.data_path.suffix}")

        logger.info(f"✓ Loaded {len(self.df)} observations, {self.df['show_id'].nunique()} shows")

        # Initialize models
        self.models = LaggedCausalityModels()

        # Timestamp for output files
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    def run_main_specification(
        self,
        lag: int = 4,
        outcome: str = 'gross',
        engagement_var: str = 'total_engagement',
        model_type: str = 'both',
        include_fe: bool = True,
        include_controls: bool = True
    ) -> Dict[str, Any]:
        """
        Run main regression specification.

        Args:
            lag: Lag periods (default 4 weeks ≈ 31 days advance purchase)
            outcome: Dependent variable ('gross', 'capacity_percent', 'avg_ticket_price')
            engagement_var: Base engagement variable name
            model_type: 'ols_fe', 'panel_ols', or 'both'
            include_fe: Include fixed effects
            include_controls: Include control variables

        Returns:
            Dictionary with results from all models
        """
        logger.info("\n" + "="*80)
        logger.info("MAIN SPECIFICATION: LAGGED CAUSALITY ANALYSIS")
        logger.info("="*80)
        logger.info(f"Outcome: {outcome}")
        logger.info(f"Predictor: {engagement_var}_lag{lag}")
        logger.info(f"Model(s): {model_type}")
        logger.info(f"Fixed Effects: {include_fe}")
        logger.info(f"Controls: {include_controls}")

        predictor = f"{engagement_var}_lag{lag}"

        # Check predictor exists
        if predictor not in self.df.columns:
            raise ValueError(f"Predictor {predictor} not found in data. Available lags: {[c for c in self.df.columns if '_lag' in c]}")

        # Define controls
        controls = None
        if include_controls:
            controls = []
            if 'capacity_constrained' in self.df.columns:
                controls.append('capacity_constrained')
            if 'is_preview' in self.df.columns and self.df['is_preview'].notna().any():
                controls.append('is_preview')
            if 'is_post_opening' in self.df.columns and self.df['is_post_opening'].notna().any():
                controls.append('is_post_opening')

        results = {}

        # OLS with FE
        if model_type in ['ols_fe', 'both']:
            logger.info("\n" + "-"*80)
            logger.info("Estimating OLS with Fixed Effects...")
            logger.info("-"*80)

            if include_fe:
                ols_result = self.models.fit_ols_fe(
                    self.df,
                    outcome=outcome,
                    predictor=predictor,
                    controls=controls
                )
            else:
                # OLS without FE (not recommended, but for comparison)
                ols_result = self.models.fit_ols_fe(
                    self.df,
                    outcome=outcome,
                    predictor=predictor,
                    controls=controls
                )

            results['ols_fe'] = ols_result

        # Panel OLS
        if model_type in ['panel_ols', 'both']:
            logger.info("\n" + "-"*80)
            logger.info("Estimating Panel Regression (Within Estimator)...")
            logger.info("-"*80)

            panel_result = self.models.fit_panel_ols(
                self.df,
                outcome=outcome,
                predictor=predictor,
                controls=controls
            )

            results['panel_ols'] = panel_result

        return results

    def run_sensitivity_analysis(
        self,
        outcome: str = 'gross',
        engagement_var: str = 'total_engagement',
        lags: list = [1, 2, 4, 6],
        model_type: str = 'ols_fe'
    ) -> pd.DataFrame:
        """
        Run sensitivity analysis across multiple lags.

        Tests robustness of results to lag specification.

        Args:
            outcome: Dependent variable
            engagement_var: Base engagement variable
            lags: List of lags to test
            model_type: Which model to use for sensitivity

        Returns:
            DataFrame with results for each lag
        """
        logger.info("\n" + "="*80)
        logger.info("SENSITIVITY ANALYSIS: TESTING MULTIPLE LAGS")
        logger.info("="*80)

        results_df = self.models.sensitivity_analysis(
            self.df,
            outcome=outcome,
            engagement_var=engagement_var,
            lags=lags,
            model_type=model_type
        )

        return results_df

    def run_granger_tests(
        self,
        engagement_var: str = 'total_engagement',
        gross_var: str = 'gross',
        max_lag: int = 6
    ) -> Dict[str, Any]:
        """
        Run Granger causality tests.

        Tests whether engagement Granger-causes grosses.

        Args:
            engagement_var: Engagement variable (not lagged)
            gross_var: Gross revenue variable
            max_lag: Maximum lag to test

        Returns:
            Dictionary with Granger test results
        """
        logger.info("\n" + "="*80)
        logger.info("GRANGER CAUSALITY TESTS")
        logger.info("="*80)

        results = self.models.granger_causality_tests(
            self.df,
            engagement_var=engagement_var,
            gross_var=gross_var,
            max_lag=max_lag
        )

        return results

    def save_results(self, results: Dict[str, Any], suffix: str = ""):
        """
        Save results to multiple formats.

        Args:
            results: Dictionary of results
            suffix: Optional suffix for filenames
        """
        logger.info("\n" + "="*80)
        logger.info("SAVING RESULTS")
        logger.info("="*80)

        base_name = f"lagged_causality_results{suffix}_{self.timestamp}"

        # Save as JSON
        json_path = self.output_dir / f"{base_name}.json"
        with open(json_path, 'w') as f:
            # Convert numpy types to native Python for JSON serialization
            json_safe = json.loads(json.dumps(results, default=str))
            json.dump(json_safe, f, indent=2)
        logger.info(f"✓ Saved JSON: {json_path}")

        # Save summary as text
        txt_path = self.output_dir / f"{base_name}.txt"
        with open(txt_path, 'w') as f:
            f.write("="*80 + "\n")
            f.write("LAGGED CAUSALITY ANALYSIS RESULTS\n")
            f.write("="*80 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Write main results
            for model_name, model_results in results.items():
                if isinstance(model_results, dict) and 'error' not in model_results:
                    f.write(f"\n{'-'*80}\n")
                    f.write(f"{model_name.upper()}\n")
                    f.write(f"{'-'*80}\n")

                    for key, value in model_results.items():
                        if not isinstance(value, (list, dict)):
                            f.write(f"{key}: {value}\n")

        logger.info(f"✓ Saved TXT: {txt_path}")

        # If sensitivity results exist, save as CSV
        if 'sensitivity' in self.models.results and isinstance(self.models.results['sensitivity'], pd.DataFrame):
            csv_path = self.output_dir / f"sensitivity_analysis_{self.timestamp}.csv"
            self.models.results['sensitivity'].to_csv(csv_path, index=False)
            logger.info(f"✓ Saved sensitivity results: {csv_path}")

        logger.info(f"\n✓ All results saved to: {self.output_dir}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Run lagged causality analysis for Broadway marketing research',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run main analysis with 4-week lag (default)
  python3 run_lagged_causality_analysis.py

  # Test 2-week lag on capacity outcome
  python3 run_lagged_causality_analysis.py --lag 2 --outcome capacity_percent

  # Run sensitivity analysis across multiple lags
  python3 run_lagged_causality_analysis.py --sensitivity

  # Run Granger causality tests
  python3 run_lagged_causality_analysis.py --granger

  # Full analysis: all models + sensitivity + Granger
  python3 run_lagged_causality_analysis.py --full
        """
    )

    # Data arguments
    parser.add_argument(
        '--data',
        type=str,
        default='data/merged/merged_reddit_grosses_panel.parquet',
        help='Path to panel dataset (default: data/merged/merged_reddit_grosses_panel.parquet)'
    )

    # Main specification arguments
    parser.add_argument(
        '--lag',
        type=int,
        default=4,
        help='Lag periods in weeks (default: 4, approximately 31-day advance purchase)'
    )

    parser.add_argument(
        '--outcome',
        type=str,
        default='gross',
        choices=['gross', 'capacity_percent', 'avg_ticket_price'],
        help='Dependent variable (default: gross)'
    )

    parser.add_argument(
        '--engagement',
        type=str,
        default='total_engagement',
        help='Base engagement variable name (default: total_engagement)'
    )

    parser.add_argument(
        '--model',
        type=str,
        default='both',
        choices=['ols_fe', 'panel_ols', 'both'],
        help='Model type to estimate (default: both)'
    )

    parser.add_argument(
        '--no-fe',
        action='store_true',
        help='Exclude fixed effects (not recommended)'
    )

    parser.add_argument(
        '--no-controls',
        action='store_true',
        help='Exclude control variables'
    )

    # Analysis types
    parser.add_argument(
        '--sensitivity',
        action='store_true',
        help='Run sensitivity analysis across lags 1,2,4,6'
    )

    parser.add_argument(
        '--granger',
        action='store_true',
        help='Run Granger causality tests'
    )

    parser.add_argument(
        '--max-lag',
        type=int,
        default=6,
        help='Maximum lag for Granger tests (default: 6)'
    )

    parser.add_argument(
        '--full',
        action='store_true',
        help='Run complete analysis: main + sensitivity + Granger'
    )

    args = parser.parse_args()

    # Initialize runner
    logger.info("="*80)
    logger.info("BROADWAY MARKETING: LAGGED CAUSALITY ANALYSIS")
    logger.info("="*80)
    logger.info(f"Testing: Does social media engagement predict future grosses?")
    logger.info(f"Hypothesis: Advance ticket purchase (~31 days / 4 weeks)\n")

    runner = CausalityAnalysisRunner(args.data)

    all_results = {}

    # Main specification
    if not args.sensitivity and not args.granger or args.full:
        main_results = runner.run_main_specification(
            lag=args.lag,
            outcome=args.outcome,
            engagement_var=args.engagement,
            model_type=args.model,
            include_fe=not args.no_fe,
            include_controls=not args.no_controls
        )
        all_results.update(main_results)

    # Sensitivity analysis
    if args.sensitivity or args.full:
        sensitivity_df = runner.run_sensitivity_analysis(
            outcome=args.outcome,
            engagement_var=args.engagement,
            model_type='ols_fe'  # Use OLS-FE for sensitivity
        )
        all_results['sensitivity'] = sensitivity_df.to_dict('records')

    # Granger causality
    if args.granger or args.full:
        granger_results = runner.run_granger_tests(
            engagement_var=args.engagement,
            max_lag=args.max_lag
        )
        all_results['granger'] = granger_results

    # Save all results
    suffix = f"_lag{args.lag}" if not (args.sensitivity or args.granger or args.full) else "_full"
    runner.save_results(all_results, suffix=suffix)

    logger.info("\n" + "="*80)
    logger.info("✅ ANALYSIS COMPLETE")
    logger.info("="*80)
    logger.info(f"\nResults saved to: {runner.output_dir}")
    logger.info(f"\nNext steps:")
    logger.info(f"  1. Review results in outputs/lagged_causality/")
    logger.info(f"  2. Run visualization: python3 viz/lag_plots.py")
    logger.info(f"  3. Generate report: python3 generate_report.py")


if __name__ == "__main__":
    main()
