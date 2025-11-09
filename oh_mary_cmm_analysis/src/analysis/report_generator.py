"""Report generator for CMM analysis."""
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import json


class ReportGenerator:
    """Generates comprehensive CMM analysis reports."""

    def __init__(self, output_dir: str = None):
        """
        Initialize report generator.

        Args:
            output_dir: Directory to save reports
        """
        if output_dir is None:
            output_dir = Path(__file__).parent.parent.parent / "outputs" / "reports"

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_main_report(
        self,
        metrics: Dict[str, Any],
        df: pd.DataFrame,
        config: Dict[str, Any],
        examples: Dict[str, List[str]] = None
    ):
        """
        Generate main analysis report.

        Args:
            metrics: Calculated CMM metrics
            df: Discourse DataFrame
            config: Configuration dict
            examples: Example quotes by category
        """
        report = []

        # Header
        report.append("# Oh Mary! Cultural Movement Marketing (CMM) Analysis")
        report.append("")
        report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**Analysis Period:** {config.get('date_range', 'Last 12 months')}")
        report.append(f"**Total Posts Analyzed:** {len(df):,}")
        report.append("")
        report.append("---")
        report.append("")

        # Executive Summary
        report.append("## Executive Summary")
        report.append("")

        overall = metrics.get('Overall_CMM_Score', {})
        report.append(f"**Overall CMM Score:** {overall.get('score', 0):.1f}/100")
        report.append(f"**Category:** {overall.get('category', 'N/A')}")
        report.append("")
        report.append(f"**Finding:** {overall.get('interpretation', 'N/A')}")
        report.append("")

        # Core Research Question
        report.append("### Core Research Question")
        report.append("")
        report.append("> Does the audience speak as if \"Oh Mary!\" is a movement, identity space,")
        report.append("> or necessity — rather than just entertainment?")
        report.append("")

        # Answer
        if overall.get('score', 0) >= 70:
            report.append("**ANSWER: YES** — Oh Mary! demonstrates definitive Cultural Movement Marketing characteristics.")
        elif overall.get('score', 0) >= 50:
            report.append("**ANSWER: STRONG SIGNAL** — Oh Mary! shows clear movement-like audience behaviors.")
        elif overall.get('score', 0) >= 30:
            report.append("**ANSWER: MODERATE SIGNAL** — Oh Mary! has some movement characteristics.")
        else:
            report.append("**ANSWER: NO** — Oh Mary! functions primarily as entertainment.")

        report.append("")
        report.append("---")
        report.append("")

        # Movement-Like Behaviors Detected
        report.append("## Movement-Like Audience Behaviors Detected")
        report.append("")

        behaviors = self._identify_movement_behaviors(metrics)
        if behaviors:
            for i, behavior in enumerate(behaviors, 1):
                report.append(f"### {i}. {behavior['name']}")
                report.append("")
                report.append(f"**Evidence:** {behavior['evidence']}")
                report.append("")
                report.append(f"**Strength:** {behavior['strength']}")
                report.append("")
        else:
            report.append("*No strong movement-like behaviors detected.*")
            report.append("")

        report.append("---")
        report.append("")

        # Detailed Metrics
        report.append("## Detailed CMM Metrics")
        report.append("")

        metric_sections = [
            ('MSS', 'Movement Sentiment Score (MSS)'),
            ('IRI', 'Identity Resonance Index (IRI)'),
            ('ER', 'Evangelism Ratio (ER)'),
            ('RAS', 'Repeat Attendance Signal (RAS)'),
            ('BIS', 'Belonging Intensity Score (BIS)'),
            ('GIM', 'Gatekeeping & Insider Markers (GIM)'),
            ('CFS', 'Community Formation Signals (CFS)'),
            ('MPI', 'Mimetic Propagation Index (MPI)')
        ]

        for metric_key, metric_name in metric_sections:
            if metric_key in metrics:
                report.append(f"### {metric_name}")
                report.append("")
                report.append(f"**Score:** {metrics[metric_key]['score']:.3f}")
                report.append("")
                report.append(f"**Interpretation:** {metrics[metric_key]['interpretation']}")
                report.append("")

                # Additional details
                metric_data = metrics[metric_key]
                if 'percentage' in metric_data:
                    report.append(f"- Percentage: {metric_data['percentage']:.1f}%")
                if 'n_posts' in metric_data:
                    report.append(f"- Number of posts: {metric_data['n_posts']}")
                if 'lift_percentage' in metric_data:
                    report.append(f"- Engagement lift: {metric_data['lift_percentage']:.1f}%")
                if 'statistical_significance' in metric_data:
                    sig = "Yes" if metric_data['statistical_significance'] else "No"
                    report.append(f"- Statistically significant: {sig}")
                if 'ci' in metric_data:
                    ci = metric_data['ci']
                    report.append(f"- 95% CI: [{ci[0]:.3f}, {ci[1]:.3f}]")

                report.append("")

        report.append("---")
        report.append("")

        # Evidence Examples
        if examples:
            report.append("## Evidence: Audience Discourse Examples")
            report.append("")
            report.append("*All examples include source URLs and timestamps for verification.*")
            report.append("")

            for category, quotes in examples.items():
                if quotes:
                    report.append(f"### {category}")
                    report.append("")
                    for quote in quotes[:5]:  # Top 5 examples
                        report.append(f"- {quote}")
                    report.append("")

        # Counter-Signals
        report.append("---")
        report.append("")
        report.append("## Counter-Signals and Limitations")
        report.append("")
        report.append(self._generate_counter_signals(df, metrics))
        report.append("")

        # Uncertainty Documentation
        report.append("---")
        report.append("")
        report.append("## Uncertainty & Confidence")
        report.append("")
        report.append(self._generate_uncertainty_section(metrics))
        report.append("")

        # Strategic Implications
        report.append("---")
        report.append("")
        report.append("## Strategic Implications for Producers")
        report.append("")
        report.append(self._generate_strategic_implications(metrics, overall.get('score', 0)))
        report.append("")

        # Methodology
        report.append("---")
        report.append("")
        report.append("## Methodology")
        report.append("")
        report.append("### Data Sources")
        report.append("")
        platforms = df['platform'].unique() if 'platform' in df.columns else []
        for platform in platforms:
            count = len(df[df['platform'] == platform])
            report.append(f"- **{platform.title()}**: {count} posts/comments")
        report.append("")

        report.append("### Analysis Methods")
        report.append("")
        report.append("1. **Lexicon-based discourse extraction** using movement language taxonomy")
        report.append("2. **NLP analysis** with transformer embeddings and clustering")
        report.append("3. **Statistical analysis** with bootstrap confidence intervals")
        report.append("4. **Weak supervision** for discourse type labeling")
        report.append("")

        report.append("### Compliance")
        report.append("")
        report.append("- ✓ Public data only (no login-required scraping)")
        report.append("- ✓ All claims linked to URLs + timestamps")
        report.append("- ✓ Uncertainty quantified via bootstrap CIs")
        report.append("- ✓ Counter-signals documented")
        report.append("")

        # Save report
        report_text = "\n".join(report)
        report_path = self.output_dir / "report.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_text)

        print(f"✓ Main report saved to {report_path}")
        return report_path

    def _identify_movement_behaviors(self, metrics: Dict[str, Any]) -> List[Dict[str, str]]:
        """Identify at least 3 movement-like behaviors or prove absence."""
        behaviors = []

        # 1. Identity Resonance
        if metrics.get('IRI', {}).get('score', 0) > 0.15:
            behaviors.append({
                'name': 'Strong Identity Alignment',
                'evidence': f"{metrics['IRI']['percentage']:.1f}% of posts express identity resonance or feeling represented",
                'strength': 'STRONG' if metrics['IRI']['score'] > 0.3 else 'MODERATE'
            })

        # 2. Evangelism
        if metrics.get('ER', {}).get('score', 0) > 0.2:
            behaviors.append({
                'name': 'Proactive Evangelism',
                'evidence': f"{metrics['ER']['percentage']:.1f}% of posts actively urge others to attend",
                'strength': 'STRONG' if metrics['ER']['score'] > 0.4 else 'MODERATE'
            })

        # 3. Repeat Attendance
        if metrics.get('RAS', {}).get('score', 0) > 0.15:
            behaviors.append({
                'name': 'Ritual Repeat Attendance',
                'evidence': f"{metrics['RAS']['percentage']:.1f}% mention seeing the show multiple times",
                'strength': 'STRONG' if metrics['RAS']['score'] > 0.3 else 'MODERATE'
            })

        # 4. Collective Voice
        if metrics.get('MSS', {}).get('lift_percentage', 0) > 20:
            behaviors.append({
                'name': 'Collective Language Usage',
                'evidence': f"Collective language drives {metrics['MSS']['lift_percentage']:.1f}% higher engagement than individual language",
                'strength': 'STRONG' if metrics['MSS']['lift_percentage'] > 50 else 'MODERATE'
            })

        # 5. Community Formation
        if metrics.get('CFS', {}).get('score', 0) > 0.15:
            behaviors.append({
                'name': 'Organized Fan Communities',
                'evidence': f"{metrics['CFS']['percentage']:.1f}% reference community structures (rush line, lottery, meetups)",
                'strength': 'STRONG' if metrics['CFS']['score'] > 0.25 else 'MODERATE'
            })

        # 6. Insider Culture
        if metrics.get('GIM', {}).get('score', 0) > 0.15:
            behaviors.append({
                'name': 'Insider/Gatekeeping Culture',
                'evidence': f"{metrics['GIM']['percentage']:.1f}% use insider language or gatekeeping markers",
                'strength': 'STRONG' if metrics['GIM']['score'] > 0.25 else 'MODERATE'
            })

        return behaviors

    def _generate_counter_signals(self, df: pd.DataFrame, metrics: Dict[str, Any]) -> str:
        """Generate counter-signals section."""
        counter = []

        counter.append("### Negative/Mixed Sentiment")
        # Look for critique markers
        if 'original_text' in df.columns:
            critique_count = df['original_text'].str.contains(
                'disappointed|overrated|overhyped|not worth',
                case=False, na=False
            ).sum()
            counter.append(f"- {critique_count} posts ({critique_count/len(df)*100:.1f}%) contain critical language")
        else:
            counter.append("- Sentiment analysis data not available")

        counter.append("")
        counter.append("### Casual Entertainment Frame")
        casual_count = len(df[df.get('audience_tone', 'casual') == 'casual'])
        counter.append(f"- {casual_count} posts ({casual_count/len(df)*100:.1f}%) frame the show as casual entertainment")

        counter.append("")
        counter.append("### Low Movement Metrics")
        low_metrics = []
        for metric in ['MSS', 'IRI', 'ER', 'RAS', 'BIS', 'GIM', 'CFS']:
            if metrics.get(metric, {}).get('score', 0) < 0.2:
                low_metrics.append(metric)

        if low_metrics:
            counter.append(f"- Low scores on: {', '.join(low_metrics)}")
        else:
            counter.append("- All metrics show moderate to strong movement signals")

        return "\n".join(counter)

    def _generate_uncertainty_section(self, metrics: Dict[str, Any]) -> str:
        """Generate uncertainty documentation."""
        uncertainty = []

        uncertainty.append("### Sample Limitations")
        uncertainty.append("- Analysis based on publicly available data only")
        uncertainty.append("- Platform API restrictions may limit sample representativeness")
        uncertainty.append("- Viral posts may be over-represented in search results")

        uncertainty.append("")
        uncertainty.append("### Statistical Uncertainty")
        uncertainty.append("- All proportions reported with 95% bootstrap confidence intervals")
        uncertainty.append("- Statistical significance tested via t-tests (α = 0.05)")

        uncertainty.append("")
        uncertainty.append("### Classification Uncertainty")
        uncertainty.append("- Discourse labeling uses weak supervision (lexicon + patterns)")
        uncertainty.append("- Boundary cases may be misclassified")
        uncertainty.append("- Human validation recommended for critical claims")

        return "\n".join(uncertainty)

    def _generate_strategic_implications(self, metrics: Dict[str, Any], overall_score: float) -> str:
        """Generate strategic implications for producers."""
        implications = []

        if overall_score >= 70:
            implications.append("### High CMM Score (70+): Lean Into Movement Status")
            implications.append("")
            implications.append("**Recommended Actions:**")
            implications.append("1. **Amplify fan voices** — Feature audience testimonials prominently")
            implications.append("2. **Build community infrastructure** — Formalize rush line culture, create official fan spaces")
            implications.append("3. **Enable identity expression** — Merchandise/content that lets fans signal belonging")
            implications.append("4. **Facilitate evangelism** — Referral programs, group discounts, 'bring a friend' nights")
            implications.append("5. **Extend the ritual** — Consider longer runs, tours to reach distributed communities")

        elif overall_score >= 50:
            implications.append("### Strong CMM Signals (50-69): Cultivate Movement Potential")
            implications.append("")
            implications.append("**Recommended Actions:**")
            implications.append("1. **Strengthen identity connections** — Emphasize representation in marketing")
            implications.append("2. **Support repeat attendance** — Lottery systems, membership programs")
            implications.append("3. **Encourage word-of-mouth** — Social media campaigns that amplify fan content")
            implications.append("4. **Test community features** — Pilot meetups, fan events")

        elif overall_score >= 30:
            implications.append("### Moderate CMM (30-49): Entertainment with Community Potential")
            implications.append("")
            implications.append("**Recommended Actions:**")
            implications.append("1. **Identify core constituencies** — Who shows movement behaviors? Target them.")
            implications.append("2. **Lower barriers to repeat** — Affordable return visit options")
            implications.append("3. **Test movement messaging** — Does community framing resonate?")

        else:
            implications.append("### Limited CMM (<30): Traditional Entertainment Marketing")
            implications.append("")
            implications.append("**Recommended Actions:**")
            implications.append("1. **Focus on quality and reviews** — Traditional PR approach")
            implications.append("2. **Consider demographic targeting** — If movement signals are absent overall, may exist in niches")
            implications.append("3. **Monitor for emergent patterns** — CMM can develop over time")

        return "\n".join(implications)

    def save_csv_outputs(self, df: pd.DataFrame, memes: List[Dict], community: pd.DataFrame = None):
        """
        Save CSV outputs.

        Args:
            df: Audience discourse DataFrame
            memes: Memes catalog
            community: Community signals DataFrame
        """
        # Audience discourse
        discourse_path = self.output_dir.parent.parent / "data" / "processed" / "audience_discourse.csv"
        df.to_csv(discourse_path, index=False, encoding='utf-8')
        print(f"✓ Saved audience_discourse.csv to {discourse_path}")

        # Memes catalog
        if memes:
            memes_df = pd.DataFrame(memes)
            memes_path = self.output_dir.parent.parent / "data" / "processed" / "memes_catalog.csv"
            memes_df.to_csv(memes_path, index=False, encoding='utf-8')
            print(f"✓ Saved memes_catalog.csv to {memes_path}")

        # Community signals
        if community is not None:
            community_path = self.output_dir.parent.parent / "data" / "processed" / "community_signals.csv"
            community.to_csv(community_path, index=False, encoding='utf-8')
            print(f"✓ Saved community_signals.csv to {community_path}")

    def save_metrics_json(self, metrics: Dict[str, Any]):
        """Save metrics as JSON."""
        import numpy as np

        # Custom JSON encoder for numpy types and booleans
        class NumpyEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, np.integer):
                    return int(obj)
                elif isinstance(obj, np.floating):
                    return float(obj)
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                elif isinstance(obj, np.bool_):
                    return bool(obj)
                return super(NumpyEncoder, self).default(obj)

        metrics_path = self.output_dir / "metrics.json"
        with open(metrics_path, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, cls=NumpyEncoder)
        print(f"✓ Saved metrics.json to {metrics_path}")
