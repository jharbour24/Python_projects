"""
Visualization functions for MDS-SV analysis.
Generates publication-quality plots without seaborn.
"""

from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path


def make_scatter_mds_vs_sv(
    aligned_df: pd.DataFrame,
    output_path: Path,
    title_stats: Optional[Dict] = None,
) -> None:
    """
    Create scatter plot of MDS vs SV with correlation statistics.

    Args:
        aligned_df: DataFrame with MDS and SV scores
        output_path: Path to save PNG
        title_stats: Optional dict with correlation stats to display
    """
    # Filter valid data
    valid_df = aligned_df.dropna(subset=["mds", "sv"])

    if valid_df.empty:
        print("Warning: No valid data for scatter plot")
        return

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 7))

    # Scatter by cohort if available
    if "cohort" in valid_df.columns:
        cohorts = valid_df["cohort"].unique()
        colors = {"cmm_depth": "#2E86AB", "broad_appeal": "#A23B72"}
        markers = {"cmm_depth": "o", "broad_appeal": "s"}

        for cohort in cohorts:
            cohort_data = valid_df[valid_df["cohort"] == cohort]
            ax.scatter(
                cohort_data["mds"],
                cohort_data["sv"],
                c=colors.get(cohort, "#555555"),
                marker=markers.get(cohort, "o"),
                alpha=0.6,
                s=50,
                label=cohort.replace("_", " ").title(),
            )
    else:
        ax.scatter(valid_df["mds"], valid_df["sv"], alpha=0.6, s=50, c="#2E86AB")

    # Add regression line
    z = np.polyfit(valid_df["mds"], valid_df["sv"], 1)
    p = np.poly1d(z)
    x_line = np.linspace(valid_df["mds"].min(), valid_df["mds"].max(), 100)
    ax.plot(x_line, p(x_line), "r--", linewidth=2, alpha=0.7, label="Linear fit")

    # Labels and title
    ax.set_xlabel("Movement Density Score (MDS)", fontsize=12, fontweight="bold")
    ax.set_ylabel("Sales Velocity (SV)", fontsize=12, fontweight="bold")

    # Title with stats
    if title_stats:
        title = (
            f"MDS vs SV: Pearson r = {title_stats.get('pearson_r', 0):.3f}, "
            f"Spearman ρ = {title_stats.get('spearman_r', 0):.3f}\n"
            f"n = {title_stats.get('n_obs', 0)} observations, "
            f"{title_stats.get('n_shows', 0)} shows"
        )
    else:
        title = "Movement Density Score vs Sales Velocity"

    ax.set_title(title, fontsize=13, fontweight="bold", pad=15)

    # Grid and legend
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.legend(loc="best", framealpha=0.9)

    # Tight layout
    fig.tight_layout()

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved: {output_path}")

    # Also save backing CSV
    csv_path = output_path.with_suffix(".csv")
    valid_df[["show_name", "week_relative", "mds", "sv", "cohort"]].to_csv(
        csv_path, index=False
    )
    print(f"Saved: {csv_path}")


def make_facet_time_series(
    aligned_df: pd.DataFrame,
    output_path: Path,
    max_shows: int = 10,
) -> None:
    """
    Create faceted time series plots of MDS and SV by show.

    Args:
        aligned_df: Aligned data with relative weeks
        output_path: Path to save PNG
        max_shows: Maximum number of shows to plot
    """
    # Get unique shows
    shows = aligned_df["show_name"].unique()[:max_shows]

    # Determine grid size
    n_shows = len(shows)
    n_cols = 2
    n_rows = (n_shows + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(14, 4 * n_rows), sharex=True)

    if n_rows == 1:
        axes = axes.reshape(1, -1)

    for idx, show in enumerate(shows):
        row = idx // n_cols
        col = idx % n_cols
        ax = axes[row, col]

        show_data = aligned_df[aligned_df["show_name"] == show].sort_values(
            "week_relative"
        )

        # Plot MDS
        ax.plot(
            show_data["week_relative"],
            show_data["mds"],
            marker="o",
            linewidth=2,
            markersize=4,
            label="MDS",
            color="#2E86AB",
        )

        # Plot SV
        ax.plot(
            show_data["week_relative"],
            show_data["sv"],
            marker="s",
            linewidth=2,
            markersize=4,
            label="SV",
            color="#A23B72",
        )

        # Mark opening week
        ax.axvline(0, color="red", linestyle="--", alpha=0.5, linewidth=1)

        # Labels
        ax.set_title(show, fontsize=11, fontweight="bold")
        ax.set_ylabel("Score", fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best", fontsize=9)

    # Remove empty subplots
    for idx in range(n_shows, n_rows * n_cols):
        row = idx // n_cols
        col = idx % n_cols
        fig.delaxes(axes[row, col])

    # Common x-label
    fig.text(
        0.5,
        0.02,
        "Weeks Relative to Opening (0 = Opening Week)",
        ha="center",
        fontsize=12,
        fontweight="bold",
    )

    fig.suptitle(
        "MDS and SV Time Series by Show (Aligned to Opening)",
        fontsize=14,
        fontweight="bold",
        y=0.995,
    )

    fig.tight_layout(rect=[0, 0.03, 1, 0.99])

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved: {output_path}")

    # Save backing CSV
    csv_path = output_path.with_suffix(".csv")
    aligned_df[["show_name", "week_relative", "mds", "sv"]].to_csv(csv_path, index=False)
    print(f"Saved: {csv_path}")


def make_lead_lag_heatmap(
    lead_lag_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """
    Create heatmap of lead-lag correlations.

    Args:
        lead_lag_df: DataFrame with lag and pearson_r columns
        output_path: Path to save PNG
    """
    if lead_lag_df.empty:
        print("Warning: No lead-lag data to plot")
        return

    fig, ax = plt.subplots(figsize=(10, 6))

    lags = lead_lag_df["lag"].values
    correlations = lead_lag_df["pearson_r"].values

    # Bar plot
    colors = ["#2E86AB" if r > 0 else "#A23B72" for r in correlations]
    ax.bar(lags, correlations, color=colors, alpha=0.7, edgecolor="black")

    # Add value labels on bars
    for lag, corr in zip(lags, correlations):
        ax.text(
            lag,
            corr + (0.02 if corr > 0 else -0.02),
            f"{corr:.3f}",
            ha="center",
            va="bottom" if corr > 0 else "top",
            fontsize=10,
            fontweight="bold",
        )

    # Labels
    ax.set_xlabel("Lag (Weeks): MDS(t) → SV(t+L)", fontsize=12, fontweight="bold")
    ax.set_ylabel("Pearson Correlation", fontsize=12, fontweight="bold")
    ax.set_title(
        "Lead-Lag Analysis: Does MDS Predict Future SV?",
        fontsize=13,
        fontweight="bold",
        pad=15,
    )

    # Grid
    ax.grid(True, alpha=0.3, axis="y")
    ax.set_xticks(lags)

    # Reference line at 0
    ax.axhline(0, color="black", linewidth=1, linestyle="-")

    fig.tight_layout()

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved: {output_path}")

    # Save backing CSV
    csv_path = output_path.with_suffix(".csv")
    lead_lag_df.to_csv(csv_path, index=False)
    print(f"Saved: {csv_path}")


def make_cohort_boxplots(
    aligned_df: pd.DataFrame,
    output_path_mds: Path,
    output_path_sv: Path,
) -> None:
    """
    Create boxplots comparing MDS and SV across cohorts.

    Args:
        aligned_df: Aligned data with cohort labels
        output_path_mds: Path for MDS boxplot
        output_path_sv: Path for SV boxplot
    """
    if "cohort" not in aligned_df.columns:
        print("Warning: No cohort information available for boxplots")
        return

    cohorts = aligned_df["cohort"].unique()

    # MDS boxplot
    fig, ax = plt.subplots(figsize=(8, 6))

    mds_by_cohort = [
        aligned_df[aligned_df["cohort"] == c]["mds"].dropna() for c in cohorts
    ]

    bp = ax.boxplot(
        mds_by_cohort,
        labels=[c.replace("_", " ").title() for c in cohorts],
        patch_artist=True,
        showmeans=True,
    )

    # Color boxes
    colors = ["#2E86AB", "#A23B72"]
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    ax.set_ylabel("Movement Density Score (MDS)", fontsize=12, fontweight="bold")
    ax.set_title(
        "MDS Distribution by Cohort", fontsize=13, fontweight="bold", pad=15
    )
    ax.grid(True, alpha=0.3, axis="y")

    fig.tight_layout()
    output_path_mds.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path_mds, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved: {output_path_mds}")

    # SV boxplot
    fig, ax = plt.subplots(figsize=(8, 6))

    sv_by_cohort = [
        aligned_df[aligned_df["cohort"] == c]["sv"].dropna() for c in cohorts
    ]

    bp = ax.boxplot(
        sv_by_cohort,
        labels=[c.replace("_", " ").title() for c in cohorts],
        patch_artist=True,
        showmeans=True,
    )

    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    ax.set_ylabel("Sales Velocity (SV)", fontsize=12, fontweight="bold")
    ax.set_title("SV Distribution by Cohort", fontsize=13, fontweight="bold", pad=15)
    ax.grid(True, alpha=0.3, axis="y")

    fig.tight_layout()
    output_path_sv.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path_sv, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved: {output_path_sv}")

    # Save backing CSVs
    aligned_df[["show_name", "cohort", "mds"]].to_csv(
        output_path_mds.with_suffix(".csv"), index=False
    )
    aligned_df[["show_name", "cohort", "sv"]].to_csv(
        output_path_sv.with_suffix(".csv"), index=False
    )


def make_sensitivity_pca_plot(
    aligned_df_original: pd.DataFrame,
    aligned_df_pca: pd.DataFrame,
    output_path: Path,
) -> None:
    """
    Create sensitivity plot comparing original MDS vs PCA-based MDS.

    Args:
        aligned_df_original: Aligned data with original MDS
        aligned_df_pca: Aligned data with PCA-based MDS
        output_path: Path to save PNG
    """
    # Merge on show and week
    merged = pd.merge(
        aligned_df_original[["show_name", "week_relative", "mds", "sv"]],
        aligned_df_pca[["show_name", "week_relative", "mds_pca"]],
        on=["show_name", "week_relative"],
        how="inner",
    )

    merged = merged.dropna()

    if merged.empty:
        print("Warning: No data for PCA sensitivity plot")
        return

    # Create 2-panel plot
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Panel 1: Original MDS vs SV
    ax1 = axes[0]
    ax1.scatter(merged["mds"], merged["sv"], alpha=0.6, s=50, c="#2E86AB")

    z1 = np.polyfit(merged["mds"], merged["sv"], 1)
    p1 = np.poly1d(z1)
    x_line1 = np.linspace(merged["mds"].min(), merged["mds"].max(), 100)
    ax1.plot(x_line1, p1(x_line1), "r--", linewidth=2, alpha=0.7)

    from scipy.stats import pearsonr

    r1, p1_val = pearsonr(merged["mds"], merged["sv"])

    ax1.set_xlabel("Original MDS (Equal Weights)", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Sales Velocity (SV)", fontsize=11, fontweight="bold")
    ax1.set_title(f"Original: r = {r1:.3f}, p = {p1_val:.4f}", fontsize=12, fontweight="bold")
    ax1.grid(True, alpha=0.3)

    # Panel 2: PCA MDS vs SV
    ax2 = axes[1]
    ax2.scatter(merged["mds_pca"], merged["sv"], alpha=0.6, s=50, c="#A23B72")

    z2 = np.polyfit(merged["mds_pca"], merged["sv"], 1)
    p2 = np.poly1d(z2)
    x_line2 = np.linspace(merged["mds_pca"].min(), merged["mds_pca"].max(), 100)
    ax2.plot(x_line2, p2(x_line2), "r--", linewidth=2, alpha=0.7)

    r2, p2_val = pearsonr(merged["mds_pca"], merged["sv"])

    ax2.set_xlabel("PCA-Based MDS", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Sales Velocity (SV)", fontsize=11, fontweight="bold")
    ax2.set_title(f"PCA: r = {r2:.3f}, p = {p2_val:.4f}", fontsize=12, fontweight="bold")
    ax2.grid(True, alpha=0.3)

    fig.suptitle(
        "Sensitivity Analysis: Original vs PCA-Based MDS",
        fontsize=14,
        fontweight="bold",
    )

    fig.tight_layout(rect=[0, 0, 1, 0.97])

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved: {output_path}")

    # Save backing CSV
    csv_path = output_path.with_suffix(".csv")
    merged.to_csv(csv_path, index=False)
    print(f"Saved: {csv_path}")


def make_plots(
    aligned_df: pd.DataFrame,
    lead_lag_df: pd.DataFrame,
    correlation_stats: Dict,
    output_dir: Path = Path("outputs"),
    aligned_df_pca: Optional[pd.DataFrame] = None,
) -> None:
    """
    Generate all plots for the analysis.

    Args:
        aligned_df: Aligned MDS/SV data
        lead_lag_df: Lead-lag correlation results
        correlation_stats: Correlation statistics dict
        output_dir: Directory for output files
        aligned_df_pca: Optional PCA-based aligned data
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating plots...")

    # Scatter plot
    make_scatter_mds_vs_sv(
        aligned_df,
        output_dir / "scatter_MDS_vs_SV.png",
        title_stats=correlation_stats,
    )

    # Time series facets
    make_facet_time_series(aligned_df, output_dir / "facet_time_series_MDS_SV_by_show.png")

    # Lead-lag heatmap
    make_lead_lag_heatmap(lead_lag_df, output_dir / "lead_lag_corr_heatmap.png")

    # Cohort boxplots
    make_cohort_boxplots(
        aligned_df,
        output_dir / "cohort_boxplots_MDS.png",
        output_dir / "cohort_boxplots_SV.png",
    )

    # PCA sensitivity (if available)
    if aligned_df_pca is not None:
        make_sensitivity_pca_plot(
            aligned_df, aligned_df_pca, output_dir / "sensitivity_PCA_MDS_vs_SV.png"
        )

    print(f"All plots saved to {output_dir}/")
