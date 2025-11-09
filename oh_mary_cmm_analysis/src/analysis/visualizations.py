"""Visualization module for CMM analysis."""
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List
import warnings
warnings.filterwarnings('ignore')

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10


class CMMVisualizer:
    """Creates visualizations for CMM analysis."""

    def __init__(self, output_dir: str = None):
        """
        Initialize visualizer.

        Args:
            output_dir: Directory to save visualizations
        """
        if output_dir is None:
            output_dir = Path(__file__).parent.parent.parent / "outputs" / "visualizations"

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_all_visualizations(
        self,
        df: pd.DataFrame,
        metrics: Dict[str, Any],
        cluster_labels: np.ndarray = None
    ):
        """
        Create all visualizations.

        Args:
            df: DataFrame with discourse data
            metrics: Calculated metrics
            cluster_labels: Optional cluster labels
        """
        print("\n📊 Generating visualizations...")

        # 1. CMM Metrics Dashboard
        self.plot_cmm_dashboard(metrics)

        # 2. Discourse Type Distribution
        self.plot_discourse_distribution(df)

        # 3. Movement Score Distribution
        self.plot_movement_score_distribution(df)

        # 4. Platform Comparison
        if 'platform' in df.columns:
            self.plot_platform_comparison(df)

        # 5. Temporal Analysis
        if 'created_utc' in df.columns:
            self.plot_temporal_trends(df)

        # 6. Engagement Analysis
        self.plot_engagement_analysis(df)

        # 7. Pronoun Analysis
        self.plot_pronoun_analysis(df)

        # 8. Cluster Visualization (if available)
        if cluster_labels is not None:
            self.plot_clusters(df, cluster_labels)

        print(f"✓ Visualizations saved to {self.output_dir}")

    def plot_cmm_dashboard(self, metrics: Dict[str, Any]):
        """Create CMM metrics dashboard."""
        fig, axes = plt.subplots(2, 4, figsize=(16, 10))
        fig.suptitle('Cultural Movement Marketing (CMM) Metrics Dashboard', fontsize=16, fontweight='bold')

        metric_names = ['MSS', 'IRI', 'ER', 'RAS', 'BIS', 'GIM', 'CFS', 'MPI']
        metric_labels = [
            'Movement Sentiment\nScore',
            'Identity Resonance\nIndex',
            'Evangelism\nRatio',
            'Repeat Attendance\nSignal',
            'Belonging Intensity\nScore',
            'Gatekeeping &\nInsider Markers',
            'Community Formation\nSignals',
            'Mimetic Propagation\nIndex'
        ]

        for idx, (metric, label) in enumerate(zip(metric_names, metric_labels)):
            ax = axes[idx // 4, idx % 4]

            if metric in metrics:
                score = metrics[metric]['score']

                # Create gauge-like visualization
                colors = ['#d9534f', '#f0ad4e', '#5bc0de', '#5cb85c']
                if score < 0.25:
                    color = colors[0]
                elif score < 0.5:
                    color = colors[1]
                elif score < 0.75:
                    color = colors[2]
                else:
                    color = colors[3]

                # Bar chart
                ax.barh([0], [score], color=color, height=0.5)
                ax.set_xlim(0, 1)
                ax.set_ylim(-0.5, 0.5)
                ax.set_xlabel('Score', fontsize=9)
                ax.set_title(label, fontsize=10, fontweight='bold')
                ax.set_yticks([])

                # Add score text
                ax.text(score/2, 0, f'{score:.2f}', ha='center', va='center',
                       fontsize=12, fontweight='bold', color='white')

                # Add interpretation
                if 'percentage' in metrics[metric]:
                    interp_text = f"{metrics[metric]['percentage']:.1f}%"
                else:
                    interp_text = f"{score:.2%}"

                ax.text(0.5, -0.3, interp_text, ha='center', va='top',
                       transform=ax.transAxes, fontsize=8, style='italic')

        plt.tight_layout()
        plt.savefig(self.output_dir / 'cmm_dashboard.png', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_discourse_distribution(self, df: pd.DataFrame):
        """Plot distribution of discourse types."""
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        # Labels
        labels = [
            'movement_framing', 'identity_resonance', 'belonging_signal',
            'necessity_framing', 'repeat_attendance', 'evangelism',
            'insider_gatekeeping', 'collective_voice'
        ]

        label_names = [
            'Movement\nFraming', 'Identity\nResonance', 'Belonging\nSignal',
            'Necessity\nFraming', 'Repeat\nAttendance', 'Evangelism',
            'Insider\nGatekeeping', 'Collective\nVoice'
        ]

        # Bar chart
        counts = [df[label].sum() if label in df.columns else 0 for label in labels]
        percentages = [c/len(df)*100 for c in counts]

        axes[0].barh(label_names, percentages, color='steelblue')
        axes[0].set_xlabel('Percentage of Posts (%)', fontsize=11)
        axes[0].set_title('Discourse Type Distribution', fontsize=13, fontweight='bold')
        axes[0].grid(axis='x', alpha=0.3)

        # Add value labels
        for i, (p, c) in enumerate(zip(percentages, counts)):
            axes[0].text(p + 1, i, f'{p:.1f}%\n(n={c})', va='center', fontsize=8)

        # Audience tone pie chart
        if 'audience_tone' in df.columns:
            tone_counts = df['audience_tone'].value_counts()
            colors = {'reverence': '#e74c3c', 'belonging': '#3498db',
                     'identity': '#9b59b6', 'casual': '#95a5a6'}
            plot_colors = [colors.get(t, '#95a5a6') for t in tone_counts.index]

            axes[1].pie(tone_counts.values, labels=tone_counts.index,
                       autopct='%1.1f%%', colors=plot_colors, startangle=90)
            axes[1].set_title('Audience Tone Distribution', fontsize=13, fontweight='bold')
        else:
            axes[1].text(0.5, 0.5, 'Tone data not available',
                        ha='center', va='center', transform=axes[1].transAxes)

        plt.tight_layout()
        plt.savefig(self.output_dir / 'discourse_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_movement_score_distribution(self, df: pd.DataFrame):
        """Plot movement score distribution."""
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        if 'movement_score' in df.columns:
            # Histogram
            axes[0].hist(df['movement_score'], bins=20, color='steelblue',
                        edgecolor='black', alpha=0.7)
            axes[0].axvline(df['movement_score'].mean(), color='red',
                          linestyle='--', linewidth=2, label=f'Mean: {df["movement_score"].mean():.2f}')
            axes[0].axvline(df['movement_score'].median(), color='orange',
                          linestyle='--', linewidth=2, label=f'Median: {df["movement_score"].median():.2f}')
            axes[0].set_xlabel('Movement Score', fontsize=11)
            axes[0].set_ylabel('Frequency', fontsize=11)
            axes[0].set_title('Movement Score Distribution', fontsize=13, fontweight='bold')
            axes[0].legend()
            axes[0].grid(alpha=0.3)

            # Box plot by platform
            if 'platform' in df.columns:
                df.boxplot(column='movement_score', by='platform', ax=axes[1])
                axes[1].set_title('Movement Score by Platform', fontsize=13, fontweight='bold')
                axes[1].set_xlabel('Platform', fontsize=11)
                axes[1].set_ylabel('Movement Score', fontsize=11)
                plt.suptitle('')  # Remove automatic title
            else:
                # Cumulative distribution
                sorted_scores = np.sort(df['movement_score'])
                cumulative = np.arange(1, len(sorted_scores) + 1) / len(sorted_scores)
                axes[1].plot(sorted_scores, cumulative, linewidth=2)
                axes[1].set_xlabel('Movement Score', fontsize=11)
                axes[1].set_ylabel('Cumulative Probability', fontsize=11)
                axes[1].set_title('Cumulative Distribution', fontsize=13, fontweight='bold')
                axes[1].grid(alpha=0.3)

        plt.tight_layout()
        plt.savefig(self.output_dir / 'movement_score_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_platform_comparison(self, df: pd.DataFrame):
        """Compare metrics across platforms."""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        platforms = df['platform'].unique()

        # Movement score by platform
        platform_data = []
        for platform in platforms:
            platform_df = df[df['platform'] == platform]
            if 'movement_score' in platform_df.columns:
                platform_data.append({
                    'platform': platform,
                    'mean_movement_score': platform_df['movement_score'].mean(),
                    'n': len(platform_df)
                })

        if platform_data:
            platform_summary = pd.DataFrame(platform_data)
            axes[0, 0].bar(platform_summary['platform'], platform_summary['mean_movement_score'],
                          color='steelblue')
            axes[0, 0].set_ylabel('Mean Movement Score', fontsize=11)
            axes[0, 0].set_title('Movement Score by Platform', fontsize=12, fontweight='bold')
            axes[0, 0].grid(axis='y', alpha=0.3)

            # Add n labels
            for i, row in platform_summary.iterrows():
                axes[0, 0].text(i, row['mean_movement_score'] + 0.02,
                              f"n={row['n']}", ha='center', fontsize=9)

        # Sample size by platform
        platform_counts = df['platform'].value_counts()
        axes[0, 1].bar(platform_counts.index, platform_counts.values, color='coral')
        axes[0, 1].set_ylabel('Number of Posts', fontsize=11)
        axes[0, 1].set_title('Sample Size by Platform', fontsize=12, fontweight='bold')
        axes[0, 1].grid(axis='y', alpha=0.3)

        # Discourse patterns by platform
        discourse_cols = ['identity_resonance', 'evangelism', 'repeat_attendance', 'collective_voice']
        discourse_by_platform = []

        for platform in platforms:
            platform_df = df[df['platform'] == platform]
            row = {'platform': platform}
            for col in discourse_cols:
                if col in platform_df.columns:
                    row[col] = platform_df[col].sum() / len(platform_df) * 100
                else:
                    row[col] = 0
            discourse_by_platform.append(row)

        if discourse_by_platform:
            discourse_df = pd.DataFrame(discourse_by_platform)
            discourse_df.set_index('platform')[discourse_cols].plot(
                kind='bar', ax=axes[1, 0], rot=0
            )
            axes[1, 0].set_ylabel('Percentage (%)', fontsize=11)
            axes[1, 0].set_xlabel('Platform', fontsize=11)
            axes[1, 0].set_title('Discourse Patterns by Platform', fontsize=12, fontweight='bold')
            axes[1, 0].legend(title='Pattern', bbox_to_anchor=(1.05, 1), loc='upper left')
            axes[1, 0].grid(axis='y', alpha=0.3)

        # Engagement by platform
        if 'score' in df.columns or 'engagement_score' in df.columns:
            eng_col = 'engagement_score' if 'engagement_score' in df.columns else 'score'
            df.boxplot(column=eng_col, by='platform', ax=axes[1, 1])
            axes[1, 1].set_title('Engagement by Platform', fontsize=12, fontweight='bold')
            axes[1, 1].set_ylabel('Engagement Score', fontsize=11)
            axes[1, 1].set_xlabel('Platform', fontsize=11)
            plt.suptitle('')

        plt.tight_layout()
        plt.savefig(self.output_dir / 'platform_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_temporal_trends(self, df: pd.DataFrame):
        """Plot temporal trends in discourse."""
        fig, axes = plt.subplots(2, 1, figsize=(14, 10))

        try:
            df['date'] = pd.to_datetime(df['created_utc'])
            df['month'] = df['date'].dt.to_period('M')

            # Posts over time
            posts_by_month = df.groupby('month').size()
            axes[0].plot(posts_by_month.index.to_timestamp(), posts_by_month.values,
                        marker='o', linewidth=2, markersize=8)
            axes[0].set_xlabel('Month', fontsize=11)
            axes[0].set_ylabel('Number of Posts', fontsize=11)
            axes[0].set_title('Post Volume Over Time', fontsize=13, fontweight='bold')
            axes[0].grid(alpha=0.3)

            # Movement score over time
            if 'movement_score' in df.columns:
                movement_by_month = df.groupby('month')['movement_score'].mean()
                axes[1].plot(movement_by_month.index.to_timestamp(), movement_by_month.values,
                           marker='o', linewidth=2, markersize=8, color='coral')
                axes[1].set_xlabel('Month', fontsize=11)
                axes[1].set_ylabel('Average Movement Score', fontsize=11)
                axes[1].set_title('Movement Signal Over Time', fontsize=13, fontweight='bold')
                axes[1].grid(alpha=0.3)

        except Exception as e:
            print(f"⚠ Could not create temporal visualization: {e}")

        plt.tight_layout()
        plt.savefig(self.output_dir / 'temporal_trends.png', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_engagement_analysis(self, df: pd.DataFrame):
        """Analyze engagement patterns."""
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        eng_col = 'engagement_score' if 'engagement_score' in df.columns else 'score'

        if eng_col in df.columns and 'movement_score' in df.columns:
            # Scatter: movement score vs engagement
            axes[0].scatter(df['movement_score'], df[eng_col], alpha=0.5, s=30)
            axes[0].set_xlabel('Movement Score', fontsize=11)
            axes[0].set_ylabel('Engagement Score', fontsize=11)
            axes[0].set_title('Movement Score vs Engagement', fontsize=13, fontweight='bold')
            axes[0].grid(alpha=0.3)

            # Add trend line
            z = np.polyfit(df['movement_score'], df[eng_col], 1)
            p = np.poly1d(z)
            axes[0].plot(df['movement_score'].sort_values(),
                        p(df['movement_score'].sort_values()),
                        "r--", linewidth=2, label='Trend')
            axes[0].legend()

            # Collective vs individual engagement
            if 'collective_voice' in df.columns:
                collective_eng = df[df['collective_voice'] == True][eng_col]
                individual_eng = df[df['collective_voice'] == False][eng_col]

                box_data = [collective_eng, individual_eng]
                axes[1].boxplot(box_data, labels=['Collective\nLanguage', 'Individual\nLanguage'])
                axes[1].set_ylabel('Engagement Score', fontsize=11)
                axes[1].set_title('Engagement: Collective vs Individual', fontsize=13, fontweight='bold')
                axes[1].grid(axis='y', alpha=0.3)

                # Add means
                means = [collective_eng.mean(), individual_eng.mean()]
                axes[1].plot([1, 2], means, 'ro-', linewidth=2, markersize=10, label='Mean')
                axes[1].legend()

        plt.tight_layout()
        plt.savefig(self.output_dir / 'engagement_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_pronoun_analysis(self, df: pd.DataFrame):
        """Analyze pronoun usage patterns."""
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        if 'first_person_plural' in df.columns and 'first_person_singular' in df.columns:
            # Pronoun counts
            we_total = df['first_person_plural'].sum()
            i_total = df['first_person_singular'].sum()

            axes[0].bar(['We/Us/Our', 'I/Me/My'], [we_total, i_total],
                       color=['steelblue', 'coral'])
            axes[0].set_ylabel('Total Count', fontsize=11)
            axes[0].set_title('Pronoun Usage Comparison', fontsize=13, fontweight='bold')
            axes[0].grid(axis='y', alpha=0.3)

            # Add percentages
            total = we_total + i_total
            if total > 0:
                we_pct = we_total / total * 100
                i_pct = i_total / total * 100
                axes[0].text(0, we_total + max(we_total, i_total)*0.05,
                           f'{we_pct:.1f}%', ha='center', fontsize=10, fontweight='bold')
                axes[0].text(1, i_total + max(we_total, i_total)*0.05,
                           f'{i_pct:.1f}%', ha='center', fontsize=10, fontweight='bold')

            # Distribution of we/i ratio
            df['we_i_ratio'] = df['first_person_plural'] / (df['first_person_singular'] + 1)
            axes[1].hist(df['we_i_ratio'], bins=20, color='steelblue',
                        edgecolor='black', alpha=0.7)
            axes[1].axvline(1, color='red', linestyle='--', linewidth=2,
                          label='Equal usage')
            axes[1].set_xlabel('We/I Ratio', fontsize=11)
            axes[1].set_ylabel('Frequency', fontsize=11)
            axes[1].set_title('We/I Ratio Distribution', fontsize=13, fontweight='bold')
            axes[1].legend()
            axes[1].grid(alpha=0.3)

        plt.tight_layout()
        plt.savefig(self.output_dir / 'pronoun_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_clusters(self, df: pd.DataFrame, cluster_labels: np.ndarray):
        """Visualize discourse clusters."""
        from sklearn.decomposition import PCA

        # Reduce to 2D for visualization
        numeric_features = df.select_dtypes(include=[np.number]).columns
        X = df[numeric_features].fillna(0).values

        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X)

        plt.figure(figsize=(12, 8))
        scatter = plt.scatter(X_pca[:, 0], X_pca[:, 1], c=cluster_labels,
                             cmap='viridis', alpha=0.6, s=50)
        plt.xlabel(f'PC1 ({pca.explained_variance_ratio_[0]:.1%} variance)', fontsize=11)
        plt.ylabel(f'PC2 ({pca.explained_variance_ratio_[1]:.1%} variance)', fontsize=11)
        plt.title('Discourse Clusters (PCA Visualization)', fontsize=13, fontweight='bold')
        plt.colorbar(scatter, label='Cluster')
        plt.grid(alpha=0.3)

        plt.tight_layout()
        plt.savefig(self.output_dir / 'discourse_clusters.png', dpi=300, bbox_inches='tight')
        plt.close()
