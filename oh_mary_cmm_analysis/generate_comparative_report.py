#!/usr/bin/env python3
"""
Comparative Report Generator
Creates comprehensive markdown report comparing campaign effectiveness.
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime


class ComparativeReportGenerator:
    """Generates comparative analysis reports."""

    def __init__(self):
        """Initialize report generator."""
        self.output_dir = Path("outputs/reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_results(self) -> dict:
        """Load analysis results."""
        results_path = Path("outputs/detailed_results.json")

        if not results_path.exists():
            print(f"⚠ Results not found at {results_path}")
            return {}

        with open(results_path, 'r') as f:
            results = json.load(f)

        return results

    def load_comparison(self) -> pd.DataFrame:
        """Load comparative summary."""
        comparison_path = Path("outputs/comparative_summary.csv")

        if not comparison_path.exists():
            return pd.DataFrame()

        return pd.read_csv(comparison_path)

    def generate_report(self):
        """Generate comprehensive comparative report."""
        results = self.load_results()
        df_comparison = self.load_comparison()

        if not results or df_comparison.empty:
            print("⚠ No data available for report")
            return

        report_path = self.output_dir / "comparative_analysis_report.md"

        with open(report_path, 'w') as f:
            # Header
            f.write("# Broadway Campaign Effectiveness Analysis\n\n")
            f.write("## Comparative Cultural Movement Marketing (CMM) Study\n\n")
            f.write(f"**Analysis Date:** {datetime.now().strftime('%B %d, %Y')}\n\n")
            f.write("**Shows Analyzed:**\n")
            for show_id, data in results.items():
                f.write(f"- {data['show_name']}\n")
            f.write("\n---\n\n")

            # Executive Summary
            f.write("## Executive Summary\n\n")

            if len(df_comparison) > 0:
                winner = df_comparison.iloc[0]
                f.write(f"### 🏆 Most Effective Campaign: **{winner['Show']}**\n\n")
                f.write(f"**Overall CMM Score:** {winner['Overall CMM']:.1f}/100\n\n")

                f.write("This analysis evaluated three Broadway shows to determine which generated ")
                f.write("the strongest Cultural Movement Marketing effects—where audiences discuss ")
                f.write("the show as a movement, identity space, or cultural necessity rather than ")
                f.write("just entertainment.\n\n")

                f.write("**Campaign Effectiveness Ranking:**\n\n")
                for idx, row in df_comparison.iterrows():
                    rank = idx + 1
                    medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉"
                    f.write(f"{rank}. {medal} **{row['Show']}** — {row['Overall CMM']:.1f}/100 ")
                    f.write(f"({row['Posts']} Reddit posts analyzed)\n")

                f.write("\n---\n\n")

            # Overall Comparison
            f.write("## Overall CMM Scores\n\n")
            f.write("| Show | CMM Score | Posts Analyzed | Campaign Assessment |\n")
            f.write("|------|-----------|----------------|---------------------|\n")

            for idx, row in df_comparison.iterrows():
                score = row['Overall CMM']
                assessment = self._get_assessment(score)
                f.write(f"| {row['Show']} | {score:.1f}/100 | {row['Posts']} | {assessment} |\n")

            f.write("\n")
            f.write("**Score Interpretation:**\n")
            f.write("- **70-100:** Strong movement characteristics\n")
            f.write("- **50-69:** Moderate movement signals\n")
            f.write("- **30-49:** Weak movement formation\n")
            f.write("- **0-29:** Minimal movement discourse\n\n")

            f.write("---\n\n")

            # Detailed Metrics Breakdown
            f.write("## Detailed Metrics Comparison\n\n")

            metric_descriptions = {
                'MSS': 'Movement Sentiment Score — Collective voice engagement lift',
                'IRI': 'Identity Resonance Index — Personal identity connection',
                'ER': 'Evangelism Ratio — Sharing & recommendation behavior',
                'RAS': 'Repeat Attendance Signal — Multiple viewing indicators',
                'BIS': 'Belonging Intensity Score — Community & belonging language',
                'GIM': 'Gatekeeping Markers — Insider culture signals',
                'CFS': 'Community Formation — Social bonding patterns',
                'MPI': 'Mimetic Propagation — Viral quote/meme spread'
            }

            for metric_code, description in metric_descriptions.items():
                f.write(f"### {metric_code}: {description}\n\n")
                f.write("| Show | Score | Interpretation |\n")
                f.write("|------|-------|----------------|\n")

                # Sort by this metric
                df_sorted = df_comparison.sort_values(metric_code, ascending=False)
                for idx, row in df_sorted.iterrows():
                    score = row[metric_code]
                    interpretation = self._interpret_metric_score(score)
                    leader = " 👑" if idx == df_sorted.index[0] else ""
                    f.write(f"| {row['Show']}{leader} | {score:.1f} | {interpretation} |\n")

                f.write("\n")

            f.write("---\n\n")

            # Key Insights
            f.write("## Key Insights\n\n")

            # Find strongest and weakest metrics for each show
            for show_id, data in results.items():
                show_name = data['show_name']
                metrics = data['metrics']

                f.write(f"### {show_name}\n\n")

                # Calculate metric scores
                metric_scores = {
                    'MSS': metrics['mss']['score'],
                    'IRI': metrics['iri']['score'],
                    'ER': metrics['er']['score'],
                    'RAS': metrics['ras']['score'],
                    'BIS': metrics['bis']['score'],
                    'GIM': metrics['gim']['score'],
                    'CFS': metrics['cfs']['score'],
                    'MPI': metrics['mpi']['score']
                }

                strongest = max(metric_scores.items(), key=lambda x: x[1])
                weakest = min(metric_scores.items(), key=lambda x: x[1])

                f.write(f"**Posts Analyzed:** {metrics['posts_analyzed']}\n\n")
                f.write(f"**Strongest Signal:** {strongest[0]} ({strongest[1]:.1f}/100)\n")
                f.write(f"- {metric_descriptions[strongest[0]]}\n\n")
                f.write(f"**Weakest Signal:** {weakest[0]} ({weakest[1]:.1f}/100)\n")
                f.write(f"- {metric_descriptions[weakest[0]]}\n\n")

            f.write("---\n\n")

            # Methodology
            f.write("## Methodology\n\n")
            f.write("### Data Collection\n\n")
            f.write("- **Platform:** Reddit\n")
            f.write("- **Subreddits:** 30+ communities (broadway, musicals, theater, NYC, LGBTQ+, etc.)\n")
            f.write("- **Time Range:** Past 12 months\n")
            f.write("- **Collection Method:** Reddit API via PRAW\n\n")

            f.write("### Analysis Framework\n\n")
            f.write("Cultural Movement Marketing (CMM) measures whether audiences discuss ")
            f.write("entertainment as a movement versus just a product. Eight metrics capture:\n\n")
            f.write("1. **Collective voice patterns** (we/us vs I/me)\n")
            f.write("2. **Identity resonance** (personal connection)\n")
            f.write("3. **Evangelism behavior** (telling others)\n")
            f.write("4. **Repeat engagement** (multiple viewings)\n")
            f.write("5. **Belonging signals** (community language)\n")
            f.write("6. **Insider culture** (gatekeeping markers)\n")
            f.write("7. **Community formation** (social bonding)\n")
            f.write("8. **Viral propagation** (memes, quotes)\n\n")

            f.write("---\n\n")

            # Strategic Implications
            f.write("## Strategic Implications\n\n")

            if len(df_comparison) > 0:
                winner = df_comparison.iloc[0]

                f.write(f"### For {winner['Show']} (Top Performer)\n\n")
                f.write("**Leverage existing momentum:**\n")
                f.write("- Amplify grassroots fan content\n")
                f.write("- Support fan community initiatives\n")
                f.write("- Create exclusive experiences for repeat attendees\n")
                f.write("- Encourage social sharing with branded hashtags\n\n")

                if len(df_comparison) > 1:
                    for idx in range(1, len(df_comparison)):
                        show_name = df_comparison.iloc[idx]['Show']
                        f.write(f"### For {show_name}\n\n")
                        f.write("**Growth opportunities:**\n")
                        f.write("- Foster community spaces for audience discussion\n")
                        f.write("- Develop shareable content (quotes, moments)\n")
                        f.write("- Engage with identity-based marketing\n")
                        f.write("- Create incentives for repeat attendance\n\n")

            f.write("---\n\n")

            # Visualizations
            f.write("## Visualizations\n\n")
            f.write("See `outputs/visualizations/` for:\n")
            f.write("- Overall campaign comparison\n")
            f.write("- Metrics heatmap\n")
            f.write("- Radar comparison chart\n")
            f.write("- Individual metric breakdowns\n\n")

            f.write("---\n\n")

            # Footer
            f.write("## Data Files\n\n")
            f.write("- **Comparative summary:** `outputs/comparative_summary.csv`\n")
            f.write("- **Detailed results:** `outputs/detailed_results.json`\n")
            f.write("- **Processed data:** `data/processed/`\n")
            f.write("- **Raw data:** `data/raw/`\n\n")

            f.write(f"*Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")

        print(f"✓ Report saved: {report_path}")
        return report_path

    def _get_assessment(self, score: float) -> str:
        """Get campaign assessment based on score."""
        if score >= 70:
            return "Strong movement"
        elif score >= 50:
            return "Moderate movement"
        elif score >= 30:
            return "Weak movement"
        else:
            return "Minimal movement"

    def _interpret_metric_score(self, score: float) -> str:
        """Interpret individual metric score."""
        if score >= 70:
            return "Strong signal"
        elif score >= 50:
            return "Moderate signal"
        elif score >= 30:
            return "Weak signal"
        else:
            return "Minimal signal"


def main():
    """Main execution function."""
    print("\n" + "="*70)
    print("📝 Generating Comparative Report")
    print("="*70)

    generator = ComparativeReportGenerator()
    report_path = generator.generate_report()

    if report_path:
        print("\n" + "="*70)
        print("✅ Report Complete")
        print("="*70)
        print(f"\n📄 Report: {report_path}")


if __name__ == "__main__":
    main()
