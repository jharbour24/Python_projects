#!/usr/bin/env python3
"""
Comparative Visualization Generator
Creates charts comparing CMM metrics across multiple shows.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False
    print("⚠ Matplotlib/Seaborn not installed. Install with: pip install matplotlib seaborn")


class ComparativeVisualizer:
    """Creates comparative visualizations for multi-show CMM analysis."""

    def __init__(self):
        """Initialize visualizer."""
        self.output_dir = Path("outputs/visualizations")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Set style
        if PLOTTING_AVAILABLE:
            sns.set_style("whitegrid")
            plt.rcParams['figure.facecolor'] = 'white'

    def load_results(self) -> dict:
        """
        Load analysis results from JSON file.

        Returns:
            Dictionary with show results
        """
        results_path = Path("outputs/detailed_results.json")

        if not results_path.exists():
            print(f"⚠ Results not found at {results_path}")
            print("  Run: python run_comparative_analysis.py first")
            return {}

        with open(results_path, 'r') as f:
            results = json.load(f)

        print(f"✓ Loaded results for {len(results)} shows")
        return results

    def plot_overall_comparison(self, results: dict):
        """
        Create overall CMM score comparison chart.

        Args:
            results: Dictionary with show results
        """
        if not PLOTTING_AVAILABLE:
            return

        # Extract overall scores
        shows = []
        scores = []
        posts = []

        for show_id, data in results.items():
            shows.append(data['show_name'])
            scores.append(data['metrics']['overall_cmm']['score'])
            posts.append(data['metrics']['posts_analyzed'])

        # Create figure
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Overall CMM scores
        bars1 = ax1.barh(shows, scores, color=['#1f77b4', '#ff7f0e', '#2ca02c'][:len(shows)])
        ax1.set_xlabel('Overall CMM Score', fontsize=12)
        ax1.set_title('Campaign Effectiveness Comparison', fontsize=14, fontweight='bold')
        ax1.set_xlim(0, 100)

        # Add score labels
        for i, (score, bar) in enumerate(zip(scores, bars1)):
            ax1.text(score + 2, i, f'{score:.1f}', va='center', fontsize=11)

        # Posts collected
        bars2 = ax2.barh(shows, posts, color=['#d62728', '#9467bd', '#8c564b'][:len(shows)])
        ax2.set_xlabel('Reddit Posts Collected', fontsize=12)
        ax2.set_title('Data Collection Volume', fontsize=14, fontweight='bold')

        # Add post count labels
        for i, (post_count, bar) in enumerate(zip(posts, bars2)):
            ax2.text(post_count + max(posts)*0.02, i, f'{post_count}', va='center', fontsize=11)

        plt.tight_layout()
        output_path = self.output_dir / "overall_comparison.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ✓ Saved: {output_path}")

    def plot_metrics_heatmap(self, results: dict):
        """
        Create heatmap of all CMM metrics across shows.

        Args:
            results: Dictionary with show results
        """
        if not PLOTTING_AVAILABLE:
            return

        # Extract metrics
        metric_names = ['MSS', 'IRI', 'ER', 'RAS', 'BIS', 'GIM', 'CFS', 'MPI']
        metric_keys = ['mss', 'iri', 'er', 'ras', 'bis', 'gim', 'cfs', 'mpi']

        data_matrix = []
        show_names = []

        for show_id, data in results.items():
            show_names.append(data['show_name'])
            row = [data['metrics'][key]['score'] for key in metric_keys]
            data_matrix.append(row)

        df_heatmap = pd.DataFrame(data_matrix, columns=metric_names, index=show_names)

        # Create heatmap
        fig, ax = plt.subplots(figsize=(12, 6))
        sns.heatmap(df_heatmap, annot=True, fmt='.1f', cmap='RdYlGn', center=50,
                    vmin=0, vmax=100, cbar_kws={'label': 'Score (0-100)'},
                    linewidths=0.5, ax=ax)

        ax.set_title('CMM Metrics Comparison Across Shows', fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('')
        ax.set_ylabel('')

        plt.tight_layout()
        output_path = self.output_dir / "metrics_heatmap.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ✓ Saved: {output_path}")

    def plot_radar_chart(self, results: dict):
        """
        Create radar chart comparing shows across all metrics.

        Args:
            results: Dictionary with show results
        """
        if not PLOTTING_AVAILABLE:
            return

        metric_names = ['MSS', 'IRI', 'ER', 'RAS', 'BIS', 'GIM', 'CFS', 'MPI']
        metric_keys = ['mss', 'iri', 'er', 'ras', 'bis', 'gim', 'cfs', 'mpi']

        # Number of metrics
        num_vars = len(metric_names)
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
        angles += angles[:1]  # Complete the circle

        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))

        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

        for idx, (show_id, data) in enumerate(results.items()):
            values = [data['metrics'][key]['score'] for key in metric_keys]
            values += values[:1]  # Complete the circle

            ax.plot(angles, values, 'o-', linewidth=2, label=data['show_name'],
                   color=colors[idx % len(colors)])
            ax.fill(angles, values, alpha=0.15, color=colors[idx % len(colors)])

        # Fix axis
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(metric_names, size=11)
        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(['20', '40', '60', '80', '100'], size=9)
        ax.grid(True, linestyle='--', alpha=0.7)

        plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=11)
        plt.title('CMM Metrics Radar Comparison', fontsize=14, fontweight='bold', pad=20)

        plt.tight_layout()
        output_path = self.output_dir / "radar_comparison.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ✓ Saved: {output_path}")

    def plot_individual_metrics(self, results: dict):
        """
        Create individual bar charts for each metric.

        Args:
            results: Dictionary with show results
        """
        if not PLOTTING_AVAILABLE:
            return

        metric_info = {
            'mss': ('Movement Sentiment Score', 'Collective voice engagement lift'),
            'iri': ('Identity Resonance Index', 'Personal identity connection'),
            'er': ('Evangelism Ratio', 'Sharing & recommendation behavior'),
            'ras': ('Repeat Attendance Signal', 'Multiple viewing indicators'),
            'bis': ('Belonging Intensity Score', 'Community & belonging language'),
            'gim': ('Gatekeeping Markers', 'Insider culture signals'),
            'cfs': ('Community Formation', 'Social bonding patterns'),
            'mpi': ('Mimetic Propagation', 'Viral quote/meme spread')
        }

        for metric_key, (metric_name, description) in metric_info.items():
            fig, ax = plt.subplots(figsize=(10, 6))

            shows = []
            scores = []

            for show_id, data in results.items():
                shows.append(data['show_name'])
                scores.append(data['metrics'][metric_key]['score'])

            bars = ax.barh(shows, scores, color=['#1f77b4', '#ff7f0e', '#2ca02c'][:len(shows)])
            ax.set_xlabel('Score (0-100)', fontsize=12)
            ax.set_title(f'{metric_name}\n{description}', fontsize=13, fontweight='bold')
            ax.set_xlim(0, 100)

            # Add score labels
            for i, (score, bar) in enumerate(zip(scores, bars)):
                ax.text(score + 2, i, f'{score:.1f}', va='center', fontsize=11)

            # Add reference lines
            ax.axvline(50, color='gray', linestyle='--', alpha=0.5, linewidth=1)
            ax.text(52, len(shows)-0.5, 'Baseline (50)', fontsize=9, alpha=0.7)

            plt.tight_layout()
            output_path = self.output_dir / f"metric_{metric_key}.png"
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()

        print(f"  ✓ Saved 8 individual metric charts")

    def generate_all_visualizations(self):
        """Generate all comparative visualizations."""
        if not PLOTTING_AVAILABLE:
            print("⚠ Plotting libraries not available. Skipping visualizations.")
            return

        print("\n" + "="*70)
        print("📊 Generating Comparative Visualizations")
        print("="*70)

        # Load results
        results = self.load_results()

        if not results:
            print("⚠ No results to visualize")
            return

        # Generate visualizations
        print("\n🎨 Creating charts...")
        self.plot_overall_comparison(results)
        self.plot_metrics_heatmap(results)
        self.plot_radar_chart(results)
        self.plot_individual_metrics(results)

        print("\n" + "="*70)
        print("✅ Visualizations Complete")
        print("="*70)
        print(f"\n📁 All visualizations saved to: {self.output_dir}")
        print("\n📊 Generated:")
        print("  • Overall comparison chart")
        print("  • Metrics heatmap")
        print("  • Radar comparison")
        print("  • 8 individual metric charts")


def main():
    """Main execution function."""
    visualizer = ComparativeVisualizer()
    visualizer.generate_all_visualizations()


if __name__ == "__main__":
    main()
