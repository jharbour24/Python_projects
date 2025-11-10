#!/usr/bin/env python3
"""
Lagged Causality Models for Broadway Marketing Analysis

Implements panel regression models to test whether social media engagement
(Reddit) predicts future box office grosses, accounting for advance ticket
purchase behavior (~31 days / 4 weeks).

Models:
1. OLS with fixed effects (statsmodels)
2. Panel regression with entity/time effects (linearmodels)
3. Granger causality tests (statsmodels)

All models use cluster-robust standard errors by show.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import logging
from pathlib import Path
from scipy import stats as scipy_stats
import warnings

# Statistical modeling packages
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.regression.linear_model import OLS
from statsmodels.tools.tools import add_constant

# Panel data modeling
try:
    from linearmodels.panel import PanelOLS
    from linearmodels.iv import compare
    LINEARMODELS_AVAILABLE = True
except ImportError:
    LINEARMODELS_AVAILABLE = False
    warnings.warn("linearmodels not installed - PanelOLS unavailable. Install: pip install linearmodels")

# Granger causality
from statsmodels.tsa.stattools import grangercausalitytests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LaggedCausalityModels:
    """
    Estimates causal effects of lagged social media engagement on grosses.

    Tests the advance purchase hypothesis: Does Reddit buzz at t-k predict
    box office grosses at t? Default lag k=4 weeks (≈31 days).
    """

    def __init__(self):
        """Initialize model framework."""
        self.results = {}
        self.models = {}

    def prepare_data(
        self,
        df: pd.DataFrame,
        outcome: str = 'gross',
        predictor: str = 'total_engagement_lag4',
        controls: Optional[List[str]] = None,
        show_fe: bool = True,
        time_fe: bool = True
    ) -> Tuple[pd.DataFrame, str]:
        """
        Prepare data for regression with proper handling of categoricals and missing data.

        Args:
            df: Panel DataFrame
            outcome: Dependent variable name
            predictor: Main independent variable (lagged engagement)
            controls: List of control variable names
            show_fe: Include show fixed effects
            time_fe: Include time (week) fixed effects

        Returns:
            (cleaned_df, formula_string)
        """
        df = df.copy()

        # Drop rows with missing outcome or main predictor
        initial_n = len(df)
        df = df.dropna(subset=[outcome, predictor])
        dropped = initial_n - len(df)

        if dropped > 0:
            logger.info(f"Dropped {dropped} rows ({dropped/initial_n*100:.1f}%) due to missing outcome/predictor")

        # Build formula
        formula_parts = [outcome, '~', predictor]

        # Add controls
        if controls:
            valid_controls = [c for c in controls if c in df.columns]
            if valid_controls:
                # Drop rows with missing controls
                df = df.dropna(subset=valid_controls)
                formula_parts.append(' + ' + ' + '.join(valid_controls))

        # Add fixed effects
        if show_fe:
            formula_parts.append(' + C(show_id)')
        if time_fe:
            # Create week index for time FE
            df['week_index'] = pd.factorize(df['week_start'])[0]
            formula_parts.append(' + C(week_index)')

        formula = ''.join(formula_parts)

        logger.info(f"Final sample: {len(df)} observations, {df['show_id'].nunique()} shows")
        logger.info(f"Formula: {formula}")

        return df, formula

    def fit_ols_fe(
        self,
        df: pd.DataFrame,
        outcome: str = 'gross',
        predictor: str = 'total_engagement_lag4',
        controls: Optional[List[str]] = None,
        cluster_var: str = 'show_id'
    ) -> Dict[str, Any]:
        """
        Estimate OLS with fixed effects and cluster-robust standard errors.

        Args:
            df: Panel DataFrame
            outcome: Dependent variable (e.g., 'gross', 'capacity_pct')
            predictor: Lagged engagement variable (e.g., 'total_engagement_lag4')
            controls: List of control variables
            cluster_var: Variable to cluster SEs by (default: 'show_id')

        Returns:
            Dictionary with model results, coefficients, p-values, etc.
        """
        logger.info("="*70)
        logger.info("ESTIMATING OLS WITH FIXED EFFECTS")
        logger.info("="*70)

        # Default controls
        if controls is None:
            controls = ['capacity_constrained']
            # Add phase controls if available
            if 'is_preview' in df.columns and df['is_preview'].notna().any():
                controls.append('is_preview')
            if 'is_post_opening' in df.columns and df['is_post_opening'].notna().any():
                controls.append('is_post_opening')

        # Prepare data
        clean_df, formula = self.prepare_data(
            df, outcome, predictor, controls,
            show_fe=True, time_fe=True
        )

        # Estimate model
        try:
            model = smf.ols(formula, data=clean_df).fit(
                cov_type='cluster',
                cov_kwds={'groups': clean_df[cluster_var]}
            )

            logger.info(f"✓ Model estimated successfully")
            logger.info(f"  N = {model.nobs:.0f}")
            logger.info(f"  R² = {model.rsquared:.4f}")
            logger.info(f"  Adj R² = {model.rsquared_adj:.4f}")

            # Extract key results
            results = {
                'model_type': 'OLS-FE',
                'outcome': outcome,
                'predictor': predictor,
                'nobs': int(model.nobs),
                'r_squared': float(model.rsquared),
                'adj_r_squared': float(model.rsquared_adj),
                'f_statistic': float(model.fvalue),
                'f_pvalue': float(model.f_pvalue),
                'n_shows': int(clean_df['show_id'].nunique()),
                'predictor_coef': float(model.params[predictor]),
                'predictor_se': float(model.bse[predictor]),
                'predictor_tstat': float(model.tvalues[predictor]),
                'predictor_pvalue': float(model.pvalues[predictor]),
                'predictor_ci_lower': float(model.conf_int().loc[predictor, 0]),
                'predictor_ci_upper': float(model.conf_int().loc[predictor, 1]),
                'controls': controls,
                'cluster_var': cluster_var,
                'formula': formula
            }

            # Log key coefficient
            logger.info(f"\nKey Result:")
            logger.info(f"  {predictor}: β = {results['predictor_coef']:.4f}")
            logger.info(f"  SE = {results['predictor_se']:.4f} (cluster-robust)")
            logger.info(f"  t = {results['predictor_tstat']:.2f}, p = {results['predictor_pvalue']:.4f}")
            logger.info(f"  95% CI: [{results['predictor_ci_lower']:.4f}, {results['predictor_ci_upper']:.4f}]")

            # Store full model
            self.models['ols_fe'] = model
            self.results['ols_fe'] = results

            return results

        except Exception as e:
            logger.error(f"Model estimation failed: {e}")
            return {'error': str(e)}

    def fit_panel_ols(
        self,
        df: pd.DataFrame,
        outcome: str = 'gross',
        predictor: str = 'total_engagement_lag4',
        controls: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Estimate panel regression with entity and time fixed effects using linearmodels.

        This is the "within" estimator, controlling for time-invariant show characteristics
        and common time trends.

        Args:
            df: Panel DataFrame with 'show_id' and 'week_start'
            outcome: Dependent variable
            predictor: Lagged engagement variable
            controls: List of control variables

        Returns:
            Dictionary with model results
        """
        if not LINEARMODELS_AVAILABLE:
            logger.error("linearmodels package not available - skipping PanelOLS")
            return {'error': 'linearmodels not installed'}

        logger.info("="*70)
        logger.info("ESTIMATING PANEL REGRESSION (WITHIN ESTIMATOR)")
        logger.info("="*70)

        # Default controls
        if controls is None:
            controls = ['capacity_constrained']
            if 'is_preview' in df.columns and df['is_preview'].notna().any():
                controls.append('is_preview')
            if 'is_post_opening' in df.columns and df['is_post_opening'].notna().any():
                controls.append('is_post_opening')

        # Prepare data - drop missing
        df = df.copy()
        required_vars = [outcome, predictor] + controls + ['show_id', 'week_start']
        df = df.dropna(subset=required_vars)

        # Set multi-index for panel data
        df = df.set_index(['show_id', 'week_start'])

        logger.info(f"Panel structure: {len(df)} obs, {df.index.get_level_values(0).nunique()} shows")

        # Build formula (no need for C() in linearmodels)
        formula_parts = [outcome, '~', predictor]
        if controls:
            formula_parts.append(' + ' + ' + '.join(controls))
        formula = ''.join(formula_parts)

        # Note: EntityEffects and TimeEffects are added separately, not in formula

        try:
            # Estimate with entity and time fixed effects
            model = PanelOLS.from_formula(
                formula,
                data=df,
                entity_effects=True,
                time_effects=True
            )

            # Fit with cluster-robust SEs (cluster by entity)
            fitted = model.fit(cov_type='clustered', cluster_entity=True)

            logger.info(f"✓ Panel model estimated successfully")
            logger.info(f"  N = {fitted.nobs:.0f}")
            logger.info(f"  Within R² = {fitted.rsquared_within:.4f}")
            logger.info(f"  Between R² = {fitted.rsquared_between:.4f}")
            logger.info(f"  Overall R² = {fitted.rsquared_overall:.4f}")

            # Extract results
            results = {
                'model_type': 'PanelOLS',
                'outcome': outcome,
                'predictor': predictor,
                'nobs': int(fitted.nobs),
                'n_entities': int(fitted.entity_info['total']),
                'within_r_squared': float(fitted.rsquared_within),
                'between_r_squared': float(fitted.rsquared_between),
                'overall_r_squared': float(fitted.rsquared_overall),
                'f_statistic': float(fitted.f_statistic.stat),
                'f_pvalue': float(fitted.f_statistic.pval),
                'predictor_coef': float(fitted.params[predictor]),
                'predictor_se': float(fitted.std_errors[predictor]),
                'predictor_tstat': float(fitted.tstats[predictor]),
                'predictor_pvalue': float(fitted.pvalues[predictor]),
                'predictor_ci_lower': float(fitted.conf_int().loc[predictor, 'lower']),
                'predictor_ci_upper': float(fitted.conf_int().loc[predictor, 'upper']),
                'controls': controls,
                'formula': formula
            }

            logger.info(f"\nKey Result:")
            logger.info(f"  {predictor}: β = {results['predictor_coef']:.4f}")
            logger.info(f"  SE = {results['predictor_se']:.4f} (clustered)")
            logger.info(f"  t = {results['predictor_tstat']:.2f}, p = {results['predictor_pvalue']:.4f}")
            logger.info(f"  95% CI: [{results['predictor_ci_lower']:.4f}, {results['predictor_ci_upper']:.4f}]")

            # Store model
            self.models['panel_ols'] = fitted
            self.results['panel_ols'] = results

            return results

        except Exception as e:
            logger.error(f"Panel model estimation failed: {e}")
            return {'error': str(e)}

    def granger_causality_tests(
        self,
        df: pd.DataFrame,
        engagement_var: str = 'total_engagement',
        gross_var: str = 'gross',
        max_lag: int = 6
    ) -> Dict[str, Any]:
        """
        Test Granger causality: Does engagement at t-k help predict grosses at t?

        Runs separate tests for each show, then aggregates results across shows.
        Uses Fisher's method to combine p-values.

        Args:
            df: Panel DataFrame
            engagement_var: Engagement variable (not lagged - function creates lags)
            gross_var: Gross revenue variable
            max_lag: Maximum lag to test (default 6 weeks)

        Returns:
            Dictionary with Granger test results aggregated across shows
        """
        logger.info("="*70)
        logger.info("GRANGER CAUSALITY TESTS")
        logger.info("="*70)
        logger.info(f"Testing: Does {engagement_var} Granger-cause {gross_var}?")
        logger.info(f"Max lag: {max_lag} weeks\n")

        results_by_show = {}

        for show_id in df['show_id'].unique():
            show_df = df[df['show_id'] == show_id].copy()
            show_df = show_df.sort_values('week_start')

            # Need at least 3*max_lag observations for reliable test
            if len(show_df) < 3 * max_lag:
                logger.debug(f"  Skipping {show_id}: insufficient data ({len(show_df)} obs)")
                continue

            # Create bivariate series (grosses, engagement)
            data = show_df[[gross_var, engagement_var]].dropna()

            if len(data) < 3 * max_lag:
                logger.debug(f"  Skipping {show_id}: insufficient data after dropna ({len(data)} obs)")
                continue

            try:
                # Run Granger test
                # Tests null hypothesis: engagement does NOT Granger-cause grosses
                test_result = grangercausalitytests(
                    data[[gross_var, engagement_var]],
                    maxlag=max_lag,
                    verbose=False
                )

                # Extract p-values for each lag
                lag_pvalues = {}
                for lag in range(1, max_lag + 1):
                    # Use F-test p-value
                    pval = test_result[lag][0]['ssr_ftest'][1]
                    lag_pvalues[f'lag_{lag}'] = pval

                results_by_show[show_id] = {
                    'nobs': len(data),
                    'pvalues': lag_pvalues,
                    'significant': any(p < 0.05 for p in lag_pvalues.values())
                }

                if results_by_show[show_id]['significant']:
                    logger.info(f"  ✓ {show_id}: Evidence of Granger causality")
                else:
                    logger.debug(f"  {show_id}: No evidence of Granger causality")

            except Exception as e:
                logger.debug(f"  Error testing {show_id}: {e}")
                continue

        if not results_by_show:
            logger.warning("No shows had sufficient data for Granger tests")
            return {'error': 'Insufficient data across all shows'}

        # Aggregate results across shows
        logger.info(f"\n✓ Tested {len(results_by_show)} shows")

        # Count significant shows at each lag
        lag_summary = {}
        for lag in range(1, max_lag + 1):
            lag_key = f'lag_{lag}'
            pvalues = [r['pvalues'][lag_key] for r in results_by_show.values() if lag_key in r['pvalues']]

            if pvalues:
                n_significant = sum(p < 0.05 for p in pvalues)
                pct_significant = n_significant / len(pvalues) * 100

                # Fisher's method to combine p-values
                fisher_stat = -2 * sum(np.log(p) for p in pvalues)
                fisher_pval = scipy_stats.chi2.sf(fisher_stat, 2 * len(pvalues))

                lag_summary[lag_key] = {
                    'n_shows': len(pvalues),
                    'n_significant': n_significant,
                    'pct_significant': pct_significant,
                    'fisher_combined_pvalue': fisher_pval
                }

                logger.info(f"  Lag {lag}: {n_significant}/{len(pvalues)} shows significant ({pct_significant:.1f}%)")
                logger.info(f"    Fisher combined p-value: {fisher_pval:.4f}")

        # Overall summary
        summary = {
            'engagement_var': engagement_var,
            'gross_var': gross_var,
            'max_lag': max_lag,
            'n_shows_tested': len(results_by_show),
            'n_shows_with_any_significant_lag': sum(r['significant'] for r in results_by_show.values()),
            'lag_summary': lag_summary,
            'by_show_results': results_by_show
        }

        self.results['granger'] = summary

        return summary

    def sensitivity_analysis(
        self,
        df: pd.DataFrame,
        outcome: str = 'gross',
        engagement_var: str = 'total_engagement',
        lags: List[int] = [1, 2, 4, 6],
        model_type: str = 'ols_fe'
    ) -> pd.DataFrame:
        """
        Run sensitivity analysis across different lag specifications.

        Tests whether results are robust to lag choice.

        Args:
            df: Panel DataFrame
            outcome: Dependent variable
            engagement_var: Base engagement variable (without _lag suffix)
            lags: List of lags to test
            model_type: 'ols_fe' or 'panel_ols'

        Returns:
            DataFrame with results for each lag
        """
        logger.info("="*70)
        logger.info("SENSITIVITY ANALYSIS: TESTING MULTIPLE LAGS")
        logger.info("="*70)

        results_list = []

        for lag in lags:
            predictor = f"{engagement_var}_lag{lag}"

            if predictor not in df.columns:
                logger.warning(f"  {predictor} not found in data, skipping")
                continue

            logger.info(f"\nTesting lag = {lag} weeks...")

            if model_type == 'ols_fe':
                result = self.fit_ols_fe(df, outcome=outcome, predictor=predictor)
            elif model_type == 'panel_ols':
                result = self.fit_panel_ols(df, outcome=outcome, predictor=predictor)
            else:
                logger.error(f"Unknown model_type: {model_type}")
                continue

            if 'error' not in result:
                results_list.append({
                    'lag': lag,
                    'predictor': predictor,
                    'coefficient': result['predictor_coef'],
                    'se': result['predictor_se'],
                    'tstat': result['predictor_tstat'],
                    'pvalue': result['predictor_pvalue'],
                    'ci_lower': result['predictor_ci_lower'],
                    'ci_upper': result['predictor_ci_upper'],
                    'r_squared': result.get('r_squared') or result.get('within_r_squared'),
                    'nobs': result['nobs']
                })

        results_df = pd.DataFrame(results_list)

        if not results_df.empty:
            logger.info("\n" + "="*70)
            logger.info("SENSITIVITY RESULTS SUMMARY")
            logger.info("="*70)
            logger.info(results_df.to_string(index=False))

            # Identify best lag
            sig_results = results_df[results_df['pvalue'] < 0.05]
            if not sig_results.empty:
                best_lag = sig_results.loc[sig_results['tstat'].abs().idxmax(), 'lag']
                logger.info(f"\n✓ Best performing lag: {best_lag} weeks (highest |t-stat| among significant)")
            else:
                logger.info("\n⚠ No lags achieved statistical significance at p<0.05")

        self.results['sensitivity'] = results_df

        return results_df
