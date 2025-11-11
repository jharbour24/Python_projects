"""
Statistical models for analyzing MDS-SV relationship.
Includes correlations, OLS regression, and robustness tests.
"""

from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import warnings


class MDSSVAnalysis:
    """Comprehensive analysis of MDS-SV relationship."""

    def __init__(self, aligned_df: pd.DataFrame):
        """
        Initialize analysis with aligned data.

        Args:
            aligned_df: DataFrame with MDS and SV scores aligned by relative week
        """
        self.df = aligned_df.copy()
        self.results = {}

    def run_correlations(self) -> Dict[str, float]:
        """
        Calculate Pearson and Spearman correlations between MDS and SV.

        Returns:
            Dict with correlation results
        """
        # Drop rows with missing MDS or SV
        valid_df = self.df.dropna(subset=["mds", "sv"])

        if len(valid_df) < 3:
            return {
                "n_obs": 0,
                "n_shows": 0,
                "pearson_r": np.nan,
                "pearson_p": np.nan,
                "spearman_r": np.nan,
                "spearman_p": np.nan,
            }

        # Calculate correlations
        pearson_r, pearson_p = stats.pearsonr(valid_df["mds"], valid_df["sv"])
        spearman_r, spearman_p = stats.spearmanr(valid_df["mds"], valid_df["sv"])

        n_shows = valid_df["show_name"].nunique()

        results = {
            "n_obs": len(valid_df),
            "n_shows": n_shows,
            "pearson_r": pearson_r,
            "pearson_p": pearson_p,
            "spearman_r": spearman_r,
            "spearman_p": spearman_p,
        }

        self.results["correlations"] = results
        return results

    def run_ols_regression(self, include_fixed_effects: bool = True) -> Dict:
        """
        Run OLS regression: SV ~ MDS + fixed effects

        Args:
            include_fixed_effects: Include show and week fixed effects

        Returns:
            Dict with regression results
        """
        from scipy.stats import t as t_dist

        valid_df = self.df.dropna(subset=["mds", "sv"]).copy()

        if len(valid_df) < 10:
            return {"error": "Insufficient data for regression"}

        # Prepare data
        y = valid_df["sv"].values
        X_mds = valid_df["mds"].values.reshape(-1, 1)

        if include_fixed_effects:
            # Add show fixed effects (dummy variables)
            show_dummies = pd.get_dummies(valid_df["show_name"], prefix="show", drop_first=True)

            # Add week fixed effects
            week_dummies = pd.get_dummies(valid_df["week_relative"], prefix="week", drop_first=True)

            # Combine
            X = np.column_stack([X_mds, show_dummies.values, week_dummies.values])
            feature_names = ["mds"] + list(show_dummies.columns) + list(week_dummies.columns)
        else:
            X = X_mds
            feature_names = ["mds"]

        # Add intercept
        X = np.column_stack([np.ones(len(X)), X])
        feature_names = ["intercept"] + feature_names

        # OLS estimation
        try:
            # Beta = (X'X)^-1 X'y
            XtX = X.T @ X
            Xty = X.T @ y
            beta = np.linalg.solve(XtX, Xty)

            # Predictions and residuals
            y_pred = X @ beta
            residuals = y - y_pred

            # Standard errors (robust)
            n = len(y)
            k = len(beta)
            dof = n - k

            # Residual variance
            sigma2 = (residuals ** 2).sum() / dof

            # Covariance matrix
            cov_matrix = sigma2 * np.linalg.inv(XtX)

            # Standard errors
            se = np.sqrt(np.diag(cov_matrix))

            # T-statistics
            t_stats = beta / se

            # P-values (two-tailed)
            p_values = 2 * (1 - t_dist.cdf(np.abs(t_stats), dof))

            # 95% confidence intervals
            t_crit = t_dist.ppf(0.975, dof)
            ci_lower = beta - t_crit * se
            ci_upper = beta + t_crit * se

            # R-squared
            ss_tot = ((y - y.mean()) ** 2).sum()
            ss_res = (residuals ** 2).sum()
            r_squared = 1 - (ss_res / ss_tot)

            # Adjusted R-squared
            r_squared_adj = 1 - (ss_res / dof) / (ss_tot / (n - 1))

            # Package results
            results = {
                "coefficients": {
                    name: {
                        "estimate": beta[i],
                        "std_error": se[i],
                        "t_stat": t_stats[i],
                        "p_value": p_values[i],
                        "ci_lower": ci_lower[i],
                        "ci_upper": ci_upper[i],
                    }
                    for i, name in enumerate(feature_names)
                },
                "n_obs": n,
                "n_features": k,
                "r_squared": r_squared,
                "r_squared_adj": r_squared_adj,
                "residual_std_error": np.sqrt(sigma2),
                "fixed_effects": include_fixed_effects,
            }

            self.results["ols"] = results
            return results

        except np.linalg.LinAlgError:
            return {"error": "Singular matrix - collinearity issue"}

    def run_lead_lag_analysis(self, max_lag: int = 4) -> pd.DataFrame:
        """
        Test whether MDS predicts future SV.

        Args:
            max_lag: Maximum weeks to lag

        Returns:
            DataFrame with lag, correlation, and p-value
        """
        from src.processing.align import compute_lead_lag_correlations

        lead_lag_results = compute_lead_lag_correlations(self.df, max_lag=max_lag)

        self.results["lead_lag"] = lead_lag_results
        return lead_lag_results

    def run_pca_mds(self, features_df: pd.DataFrame, n_components: int = 1) -> Tuple[pd.DataFrame, Dict]:
        """
        Alternative MDS using PCA for feature reduction.

        Args:
            features_df: DataFrame with raw features (not z-scored)
            n_components: Number of PCA components

        Returns:
            Tuple of (DataFrame with PCA-based MDS, explained variance info)
        """
        # Select MDS-related features
        mds_features = [
            "ig_comments_per_post",
            "ig_comment_to_like_ratio",
            "tt_hashtag_video_count",
            "tt_ugc_share",
            "reddit_thread_count",
            "reddit_median_comments_per_thread",
            "trends_slope_4w",
        ]

        available_features = [f for f in mds_features if f in features_df.columns]

        if len(available_features) < 2:
            return features_df, {"error": "Insufficient features for PCA"}

        # Extract feature matrix
        X = features_df[available_features].fillna(0).values

        # Standardize
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # PCA
        pca = PCA(n_components=n_components)
        pca_scores = pca.fit_transform(X_scaled)

        # Add to dataframe
        result_df = features_df.copy()
        result_df["mds_pca"] = pca_scores[:, 0]

        pca_info = {
            "explained_variance": pca.explained_variance_ratio_.tolist(),
            "components": pca.components_.tolist(),
            "feature_names": available_features,
        }

        return result_df, pca_info

    def run_robustness_tests(self) -> Dict:
        """
        Run robustness checks:
        1. Exclude outlier weeks (Tony nominations/awards)
        2. Cohort-specific analysis

        Returns:
            Dict with robustness test results
        """
        robustness_results = {}

        # Test 1: Exclude Tony weeks (hypothetical weeks 8-10)
        tony_weeks = [8, 9, 10]
        df_no_tony = self.df[~self.df["week_relative"].isin(tony_weeks)]

        if len(df_no_tony) > 10:
            valid = df_no_tony.dropna(subset=["mds", "sv"])
            if len(valid) >= 3:
                r, p = stats.pearsonr(valid["mds"], valid["sv"])
                robustness_results["no_tony_weeks"] = {
                    "n_obs": len(valid),
                    "pearson_r": r,
                    "pearson_p": p,
                }

        # Test 2: CMM cohort only
        if "cohort" in self.df.columns:
            df_cmm = self.df[self.df["cohort"] == "cmm_depth"]
            valid_cmm = df_cmm.dropna(subset=["mds", "sv"])

            if len(valid_cmm) >= 3:
                r_cmm, p_cmm = stats.pearsonr(valid_cmm["mds"], valid_cmm["sv"])
                robustness_results["cmm_only"] = {
                    "n_obs": len(valid_cmm),
                    "pearson_r": r_cmm,
                    "pearson_p": p_cmm,
                }

            # Test 3: Broad appeal cohort only
            df_broad = self.df[self.df["cohort"] == "broad_appeal"]
            valid_broad = df_broad.dropna(subset=["mds", "sv"])

            if len(valid_broad) >= 3:
                r_broad, p_broad = stats.pearsonr(valid_broad["mds"], valid_broad["sv"])
                robustness_results["broad_appeal_only"] = {
                    "n_obs": len(valid_broad),
                    "pearson_r": r_broad,
                    "pearson_p": p_broad,
                }

        self.results["robustness"] = robustness_results
        return robustness_results

    def generate_summary_report(self) -> str:
        """
        Generate a text summary of all analyses.

        Returns:
            Formatted summary report
        """
        report = []
        report.append("=" * 80)
        report.append("MDS-SV RELATIONSHIP ANALYSIS SUMMARY")
        report.append("=" * 80)
        report.append("")

        # Correlations
        if "correlations" in self.results:
            corr = self.results["correlations"]
            report.append("PRIMARY CORRELATIONS")
            report.append("-" * 40)
            report.append(f"Sample size: {corr['n_obs']} observations across {corr['n_shows']} shows")
            report.append(f"Pearson r:   {corr['pearson_r']:.3f} (p = {corr['pearson_p']:.4f})")
            report.append(f"Spearman ρ:  {corr['spearman_r']:.3f} (p = {corr['spearman_p']:.4f})")
            report.append("")

        # OLS
        if "ols" in self.results:
            ols = self.results["ols"]
            if "error" not in ols:
                report.append("OLS REGRESSION: SV ~ MDS + Fixed Effects")
                report.append("-" * 40)
                report.append(f"N = {ols['n_obs']}, R² = {ols['r_squared']:.3f}, Adj R² = {ols['r_squared_adj']:.3f}")

                mds_coef = ols["coefficients"]["mds"]
                report.append(f"MDS coefficient: {mds_coef['estimate']:.3f}")
                report.append(f"  Std Error: {mds_coef['std_error']:.3f}")
                report.append(f"  95% CI: [{mds_coef['ci_lower']:.3f}, {mds_coef['ci_upper']:.3f}]")
                report.append(f"  p-value: {mds_coef['p_value']:.4f}")
                report.append("")

        # Lead-lag
        if "lead_lag" in self.results:
            ll = self.results["lead_lag"]
            report.append("LEAD-LAG ANALYSIS: Does MDS(t) predict SV(t+L)?")
            report.append("-" * 40)
            for _, row in ll.iterrows():
                report.append(
                    f"Lag {int(row['lag'])} weeks: r = {row['pearson_r']:.3f}, "
                    f"p = {row['p_value']:.4f}, n = {int(row['n'])}"
                )
            report.append("")

        # Robustness
        if "robustness" in self.results:
            rob = self.results["robustness"]
            report.append("ROBUSTNESS TESTS")
            report.append("-" * 40)

            if "no_tony_weeks" in rob:
                nt = rob["no_tony_weeks"]
                report.append(
                    f"Excluding Tony weeks: r = {nt['pearson_r']:.3f}, "
                    f"p = {nt['pearson_p']:.4f}, n = {nt['n_obs']}"
                )

            if "cmm_only" in rob:
                cmm = rob["cmm_only"]
                report.append(
                    f"CMM cohort only: r = {cmm['pearson_r']:.3f}, "
                    f"p = {cmm['pearson_p']:.4f}, n = {cmm['n_obs']}"
                )

            if "broad_appeal_only" in rob:
                broad = rob["broad_appeal_only"]
                report.append(
                    f"Broad appeal only: r = {broad['pearson_r']:.3f}, "
                    f"p = {broad['pearson_p']:.4f}, n = {broad['n_obs']}"
                )

            report.append("")

        report.append("=" * 80)
        report.append("INTERPRETATION")
        report.append("-" * 40)
        report.append(
            "These results test the association between digital movement density (MDS)"
        )
        report.append(
            "and sales velocity (SV). Positive correlation suggests that deeper, more"
        )
        report.append(
            "persistent engagement across social platforms is associated with stronger"
        )
        report.append(
            "sales performance. Lead-lag analysis tests predictive power. This is"
        )
        report.append(
            "correlational evidence only and does not establish causation."
        )
        report.append("=" * 80)

        return "\n".join(report)


def run_correlations_and_models(
    aligned_df: pd.DataFrame,
    features_df: Optional[pd.DataFrame] = None,
) -> Dict:
    """
    Convenience function to run full analysis suite.

    Args:
        aligned_df: Aligned MDS/SV data
        features_df: Optional raw features for PCA analysis

    Returns:
        Dict with all analysis results
    """
    analysis = MDSSVAnalysis(aligned_df)

    # Run all analyses
    corr_results = analysis.run_correlations()
    ols_results = analysis.run_ols_regression(include_fixed_effects=True)
    lead_lag_results = analysis.run_lead_lag_analysis(max_lag=4)
    robustness_results = analysis.run_robustness_tests()

    # PCA alternative if features provided
    pca_results = None
    if features_df is not None:
        try:
            _, pca_results = analysis.run_pca_mds(features_df)
        except Exception as e:
            print(f"Warning: PCA analysis failed: {e}")

    # Generate summary
    summary_report = analysis.generate_summary_report()

    return {
        "correlations": corr_results,
        "ols": ols_results,
        "lead_lag": lead_lag_results,
        "robustness": robustness_results,
        "pca": pca_results,
        "summary_report": summary_report,
        "analysis_object": analysis,
    }
