#!/usr/bin/env python3
"""
WHY Campaigns Succeed: Qualitative Deep-Dive Analysis

Goes beyond metrics to understand:
- What language/themes resonate?
- How do people talk about successful vs unsuccessful shows?
- What narratives drive engagement?
- What content strategies work?
"""

import pandas as pd
import numpy as np
import yaml
import json
import re
from pathlib import Path
from collections import Counter
from typing import Dict, List, Any, Tuple


class WhyCampaignsSucceed:
    """Deep qualitative analysis of what makes campaigns succeed."""

    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize analysis."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.shows = self.config.get('shows', {})
        self.data_dir = Path("data/raw")
        self.output_dir = Path("outputs")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_top_themes(self, df: pd.DataFrame, show_name: str, n=10) -> Dict[str, Any]:
        """
        Extract most discussed themes/topics.

        What are people actually talking about?
        """
        if df.empty:
            return {'themes': [], 'examples': []}

        # Combine all text
        all_text = ' '.join(df['title'].fillna('') + ' ' + df['text'].fillna(''))

        # Common theater-related words to analyze
        theme_categories = {
            'performance': ['performance', 'acting', 'actor', 'actress', 'cast', 'play', 'played'],
            'creative': ['director', 'writing', 'script', 'choreography', 'music', 'score', 'design'],
            'emotional': ['funny', 'hilarious', 'moving', 'emotional', 'cried', 'laughed', 'felt'],
            'quality': ['brilliant', 'amazing', 'incredible', 'perfect', 'genius', 'masterpiece'],
            'negative': ['disappointing', 'boring', 'waste', 'overrated', 'bad'],
            'social': ['see it', 'recommend', 'everyone', 'friends', 'together'],
            'identity': ['queer', 'gay', 'representation', 'seen', 'represented', 'community'],
            'repeat': ['again', 'second time', 'third time', 'multiple times', 'rush'],
            'value': ['worth it', 'expensive', 'ticket', 'price', 'affordable', 'lottery']
        }

        theme_counts = {}
        for theme, keywords in theme_categories.items():
            count = sum(all_text.lower().count(keyword) for keyword in keywords)
            theme_counts[theme] = count

        # Find most distinctive posts for each theme
        theme_examples = {}
        for theme, keywords in theme_categories.items():
            if theme_counts[theme] > 0:
                # Find posts mentioning this theme
                matching_posts = df[df['title'].fillna('').str.lower().str.contains('|'.join(keywords), regex=True)]
                if len(matching_posts) > 0:
                    # Get highest scored post
                    top_post = matching_posts.nlargest(1, 'score')
                    if len(top_post) > 0:
                        theme_examples[theme] = {
                            'title': top_post.iloc[0]['title'],
                            'score': int(top_post.iloc[0]['score']),
                            'comments': int(top_post.iloc[0]['num_comments'])
                        }

        return {
            'show': show_name,
            'theme_counts': theme_counts,
            'dominant_themes': sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            'theme_examples': theme_examples
        }

    def analyze_conversation_patterns(self, df: pd.DataFrame, show_name: str) -> Dict[str, Any]:
        """
        Analyze HOW people talk about the show.

        Are they asking questions? Making statements? Recommending?
        """
        if df.empty:
            return {}

        patterns = {
            'questions': 0,
            'exclamations': 0,
            'recommendations': 0,
            'discussions': 0,
            'reviews': 0,
            'comparisons': 0,
            'ticket_seeking': 0,
            'spoiler_warnings': 0
        }

        for _, row in df.iterrows():
            title = str(row['title']).lower()
            text = str(row['text']).lower()
            full_text = title + ' ' + text

            # Question posts
            if '?' in title:
                patterns['questions'] += 1

            # Excitement
            if '!' in title or len(re.findall(r'[A-Z]{3,}', str(row['title']))) > 0:
                patterns['exclamations'] += 1

            # Recommendations
            if any(phrase in full_text for phrase in ['should see', 'must see', 'recommend', 'go see']):
                patterns['recommendations'] += 1

            # Reviews
            if any(phrase in title for phrase in ['review', 'thoughts on', 'just saw']):
                patterns['reviews'] += 1

            # Comparisons
            if any(phrase in full_text for phrase in [' vs ', ' versus ', 'better than', 'compared to']):
                patterns['comparisons'] += 1

            # Ticket seeking
            if any(phrase in full_text for phrase in ['lottery', 'rush', 'ticket', 'discount', 'tkts']):
                patterns['ticket_seeking'] += 1

            # Spoiler discussions
            if 'spoiler' in full_text:
                patterns['spoiler_warnings'] += 1

        total = len(df)
        pattern_percentages = {k: (v / total * 100) if total > 0 else 0 for k, v in patterns.items()}

        return {
            'show': show_name,
            'patterns': patterns,
            'pattern_percentages': pattern_percentages,
            'dominant_pattern': max(pattern_percentages.items(), key=lambda x: x[1])[0] if pattern_percentages else None
        }

    def analyze_viral_content(self, df: pd.DataFrame, show_name: str) -> Dict[str, Any]:
        """
        What content goes viral? What gets people excited?

        Analyzes highest-performing posts to understand what resonates.
        """
        if df.empty or len(df) < 5:
            return {'viral_posts': []}

        # Get top 10% most viral posts
        threshold = df['score'].quantile(0.90)
        viral_posts = df[df['score'] >= threshold].copy()

        if len(viral_posts) == 0:
            return {'viral_posts': []}

        # Analyze what makes them viral
        viral_analysis = []
        for _, post in viral_posts.nlargest(10, 'score').iterrows():
            analysis = {
                'title': post['title'],
                'score': int(post['score']),
                'comments': int(post['num_comments']),
                'engagement_ratio': post['score'] / max(post['num_comments'], 1),
                'characteristics': []
            }

            title_lower = str(post['title']).lower()
            text_lower = str(post['text']).lower()
            full_text = title_lower + ' ' + text_lower

            # Identify characteristics
            if '?' in post['title']:
                analysis['characteristics'].append('question')
            if '!' in post['title']:
                analysis['characteristics'].append('excitement')
            if any(w in title_lower for w in ['amazing', 'incredible', 'brilliant', 'perfect']):
                analysis['characteristics'].append('strong_positive')
            if any(w in full_text for w in ['recommend', 'must see', 'should see']):
                analysis['characteristics'].append('recommendation')
            if any(w in full_text for w in ['funny', 'hilarious', 'laughed']):
                analysis['characteristics'].append('humor')
            if any(w in full_text for w in ['cried', 'emotional', 'moving']):
                analysis['characteristics'].append('emotional')
            if any(w in full_text for w in ['queer', 'gay', 'representation']):
                analysis['characteristics'].append('identity')
            if pd.notna(post['text']) and isinstance(post['text'], str) and len(post['text']) > 200:
                analysis['characteristics'].append('detailed_review')

            viral_analysis.append(analysis)

        # Common characteristics across viral posts
        all_characteristics = []
        for post in viral_analysis:
            all_characteristics.extend(post['characteristics'])

        characteristic_counts = Counter(all_characteristics)

        return {
            'show': show_name,
            'viral_posts': viral_analysis,
            'common_viral_traits': dict(characteristic_counts.most_common(5)),
            'avg_viral_score': viral_posts['score'].mean(),
            'avg_viral_comments': viral_posts['num_comments'].mean()
        }

    def analyze_audience_language(self, df: pd.DataFrame, show_name: str) -> Dict[str, Any]:
        """
        How does the audience speak? What's the tone and voice?

        Identifies language patterns that indicate engagement level.
        """
        if df.empty:
            return {}

        all_titles = ' '.join(df['title'].fillna('').astype(str))

        language_markers = {
            'personal_connection': ['i', 'me', 'my', 'felt'],
            'collective': ['we', 'us', 'our'],
            'superlatives': ['best', 'worst', 'most', 'greatest', 'ever'],
            'urgency': ['must', 'need', 'have to', 'should'],
            'enthusiasm': ['!!', '!!!', 'omg', 'wow'],
            'analytical': ['think', 'believe', 'opinion', 'thoughts'],
            'emotional': ['love', 'loved', 'hate', 'hated', 'feel', 'felt'],
            'social_proof': ['everyone', 'people', 'friends', 'anyone']
        }

        marker_counts = {}
        for marker_type, keywords in language_markers.items():
            count = sum(all_titles.lower().count(keyword) for keyword in keywords)
            marker_counts[marker_type] = count

        total_words = len(all_titles.split())
        marker_densities = {k: (v / max(total_words, 1) * 1000) for k, v in marker_counts.items()}  # Per 1000 words

        return {
            'show': show_name,
            'language_markers': marker_counts,
            'language_density': marker_densities,
            'dominant_voice': max(marker_densities.items(), key=lambda x: x[1])[0] if marker_densities else None
        }

    def extract_key_differentiators(
        self,
        successful_themes_data: List[Dict],
        unsuccessful_themes_data: List[Dict],
        successful_viral_data: List[Dict],
        unsuccessful_viral_data: List[Dict],
        successful_language_data: List[Dict],
        unsuccessful_language_data: List[Dict]
    ) -> Dict[str, Any]:
        """
        Compare successful vs unsuccessful to find KEY DIFFERENCES.

        What do successful campaigns do that unsuccessful ones don't?
        """
        print("\n" + "="*70)
        print("🔍 IDENTIFYING KEY DIFFERENTIATORS")
        print("="*70)

        differentiators = []

        # Compare themes
        print("\n📌 THEME ANALYSIS:")
        successful_themes = {}
        unsuccessful_themes = {}

        for data in successful_themes_data:
            for theme, count in data.get('theme_counts', {}).items():
                successful_themes[theme] = successful_themes.get(theme, 0) + count

        for data in unsuccessful_themes_data:
            for theme, count in data.get('theme_counts', {}).items():
                unsuccessful_themes[theme] = unsuccessful_themes.get(theme, 0) + count

        # Normalize by number of shows
        for theme in successful_themes:
            successful_themes[theme] /= len(successful_themes_data) if successful_themes_data else 1
        for theme in unsuccessful_themes:
            unsuccessful_themes[theme] /= len(unsuccessful_themes_data) if unsuccessful_themes_data else 1

        theme_diffs = []
        for theme in set(successful_themes.keys()) | set(unsuccessful_themes.keys()):
            success_val = successful_themes.get(theme, 0)
            fail_val = unsuccessful_themes.get(theme, 0)
            diff_pct = ((success_val - fail_val) / max(fail_val, 1)) * 100 if fail_val > 0 else 0

            theme_diffs.append({
                'theme': theme,
                'successful_avg': success_val,
                'unsuccessful_avg': fail_val,
                'difference_pct': diff_pct
            })

        theme_diffs.sort(key=lambda x: abs(x['difference_pct']), reverse=True)

        print("\nTop theme differences:")
        for diff in theme_diffs[:5]:
            direction = "MORE" if diff['difference_pct'] > 0 else "LESS"
            print(f"  • {diff['theme'].title()}: Successful shows have {abs(diff['difference_pct']):.0f}% {direction} mentions")
            differentiators.append(f"Successful shows have {abs(diff['difference_pct']):.0f}% {direction} {diff['theme']} language")

        # Compare conversation patterns
        print("\n📌 CONVERSATION PATTERN ANALYSIS:")
        # This would compare pattern_percentages across successful vs unsuccessful

        # Compare viral characteristics
        print("\n📌 VIRAL CONTENT ANALYSIS:")
        successful_viral_traits = Counter()
        unsuccessful_viral_traits = Counter()

        for data in successful_viral_data:
            viral_traits = data.get('common_viral_traits', {})
            successful_viral_traits.update(viral_traits)

        for data in unsuccessful_viral_data:
            viral_traits = data.get('common_viral_traits', {})
            unsuccessful_viral_traits.update(viral_traits)

        print("\nSuccessful shows' viral content features:")
        for trait, count in successful_viral_traits.most_common(5):
            print(f"  • {trait}: {count} occurrences")

        print("\nUnsuccessful shows' viral content features:")
        for trait, count in unsuccessful_viral_traits.most_common(5):
            print(f"  • {trait}: {count} occurrences")

        # Language voice comparison
        print("\n📌 AUDIENCE VOICE ANALYSIS:")
        print("(How audiences talk about successful vs unsuccessful shows)")

        # Aggregate language markers
        successful_markers = Counter()
        unsuccessful_markers = Counter()

        for data in successful_language_data:
            markers = data.get('language_markers', {})
            successful_markers.update(markers)

        for data in unsuccessful_language_data:
            markers = data.get('language_markers', {})
            unsuccessful_markers.update(markers)

        if successful_markers:
            print("\nSuccessful shows' language patterns:")
            for marker, count in successful_markers.most_common(5):
                print(f"  • {marker}: {count} uses")

        if unsuccessful_markers:
            print("\nUnsuccessful shows' language patterns:")
            for marker, count in unsuccessful_markers.most_common(5):
                print(f"  • {marker}: {count} uses")

        return {
            'theme_differentiators': theme_diffs,
            'successful_viral_traits': dict(successful_viral_traits.most_common(10)),
            'unsuccessful_viral_traits': dict(unsuccessful_viral_traits.most_common(10)),
            'successful_language_markers': dict(successful_markers.most_common(10)),
            'unsuccessful_language_markers': dict(unsuccessful_markers.most_common(10)),
            'key_insights': differentiators,
            'viral_traits_successful': dict(successful_viral_traits.most_common(10)),
            'viral_traits_unsuccessful': dict(unsuccessful_viral_traits.most_common(10))
        }

    def generate_why_report(self, all_analyses: Dict, differentiators: Dict):
        """Generate comprehensive WHY report."""
        print("\n" + "="*70)
        print("📝 GENERATING 'WHY' REPORT")
        print("="*70)

        report_path = self.output_dir / "why_campaigns_succeed_report.md"

        with open(report_path, 'w') as f:
            f.write("# WHY Broadway Marketing Campaigns Succeed\n\n")
            f.write("## Deep Qualitative Analysis\n\n")
            f.write(f"*Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}*\n\n")
            f.write("---\n\n")

            # Key Differentiators Section
            f.write("## 🔑 KEY DIFFERENTIATORS\n\n")
            f.write("### What Successful Campaigns Do Differently:\n\n")

            theme_diffs = differentiators['theme_differentiators']
            for diff in theme_diffs[:10]:
                if diff['difference_pct'] > 20:  # Only show significant differences
                    direction = "MORE" if diff['difference_pct'] > 0 else "LESS"
                    f.write(f"- **{diff['theme'].title()} Language:** {abs(diff['difference_pct']):.0f}% {direction} ")
                    f.write(f"({diff['successful_avg']:.0f} vs {diff['unsuccessful_avg']:.0f} mentions)\n")

            f.write("\n### Viral Content Characteristics:\n\n")
            f.write("**Successful Shows:**\n")
            for trait, count in sorted(differentiators['viral_traits_successful'].items(),
                                      key=lambda x: x[1], reverse=True)[:5]:
                f.write(f"- {trait.replace('_', ' ').title()}: {count} viral posts\n")

            f.write("\n**Unsuccessful Shows:**\n")
            for trait, count in sorted(differentiators['viral_traits_unsuccessful'].items(),
                                      key=lambda x: x[1], reverse=True)[:5]:
                f.write(f"- {trait.replace('_', ' ').title()}: {count} viral posts\n")

            f.write("\n---\n\n")

            # Individual Show Deep Dives
            f.write("## 📊 INDIVIDUAL SHOW ANALYSES\n\n")

            for show_id, analysis in all_analyses.items():
                f.write(f"### {analysis['themes']['show']}\n\n")

                # Dominant themes
                f.write("**Top Themes Discussed:**\n")
                for theme, count in analysis['themes']['dominant_themes']:
                    f.write(f"- {theme.title()}: {count} mentions\n")

                # Conversation pattern
                if 'dominant_pattern' in analysis['patterns']:
                    pattern = analysis['patterns']['dominant_pattern']
                    f.write(f"\n**Dominant Conversation Type:** {pattern.replace('_', ' ').title()}\n")

                # Example viral post
                if analysis['viral']['viral_posts']:
                    top_viral = analysis['viral']['viral_posts'][0]
                    f.write(f"\n**Most Viral Post:**\n")
                    f.write(f'- Title: "{top_viral["title"]}"\n')
                    f.write(f"- Score: {top_viral['score']} upvotes, {top_viral['comments']} comments\n")
                    f.write(f"- Characteristics: {', '.join(top_viral['characteristics'])}\n")

                f.write("\n")

            f.write("---\n\n")

            # Actionable Insights
            f.write("## 💡 ACTIONABLE INSIGHTS\n\n")
            f.write("### Based on this analysis, successful campaigns:\n\n")

            insights = differentiators.get('key_insights', [])
            for insight in insights[:10]:
                f.write(f"- {insight}\n")

            f.write("\n### Recommendations for Future Campaigns:\n\n")
            f.write("1. **Focus on themes that resonate:** Emphasize the themes that successful shows naturally generate buzz around\n")
            f.write("2. **Encourage the right conversations:** Create content that sparks the conversation patterns seen in successful shows\n")
            f.write("3. **Amplify viral content types:** Understand what content characteristics drive sharing and engagement\n")
            f.write("4. **Match the audience voice:** Speak in the language and tone that successful shows inspire in their audiences\n")

        print(f"\n💾 Saved WHY report: {report_path}")
        return report_path

    def run_complete_analysis(self):
        """Execute the full WHY analysis."""
        print("\n" + "="*70)
        print("🎓 WHY CAMPAIGNS SUCCEED: DEEP ANALYSIS")
        print("="*70)

        all_analyses = {}
        successful_data = {'themes': [], 'patterns': [], 'viral': [], 'language': []}
        unsuccessful_data = {'themes': [], 'patterns': [], 'viral': [], 'language': []}

        # Analyze each show
        for show_id, show_config in self.shows.items():
            csv_path = self.data_dir / f"reddit_{show_id}.csv"

            if not csv_path.exists():
                print(f"\n⚠ Skipping {show_config['name']} - no data file")
                continue

            df = pd.read_csv(csv_path)
            show_name = show_config['name']
            category = show_config.get('category', 'unknown')

            print(f"\n{'='*70}")
            print(f"Analyzing: {show_name} ({category})")
            print(f"{'='*70}")

            # Extract all insights
            themes = self.extract_top_themes(df, show_name)
            patterns = self.analyze_conversation_patterns(df, show_name)
            viral = self.analyze_viral_content(df, show_name)
            language = self.analyze_audience_language(df, show_name)

            all_analyses[show_id] = {
                'themes': themes,
                'patterns': patterns,
                'viral': viral,
                'language': language
            }

            # Categorize for comparison
            if category == 'successful':
                successful_data['themes'].append(themes)
                successful_data['patterns'].append(patterns)
                successful_data['viral'].append(viral)
                successful_data['language'].append(language)
            elif category == 'unsuccessful':
                unsuccessful_data['themes'].append(themes)
                unsuccessful_data['patterns'].append(patterns)
                unsuccessful_data['viral'].append(viral)
                unsuccessful_data['language'].append(language)

        # Compare successful vs unsuccessful
        differentiators = self.extract_key_differentiators(
            successful_data['themes'],
            unsuccessful_data['themes'],
            successful_data['viral'],
            unsuccessful_data['viral'],
            successful_data['language'],
            unsuccessful_data['language']
        )

        # Generate comprehensive report
        report_path = self.generate_why_report(all_analyses, differentiators)

        # Save raw data
        json_path = self.output_dir / "why_analysis_raw_data.json"
        with open(json_path, 'w') as f:
            json.dump({
                'all_analyses': all_analyses,
                'differentiators': differentiators
            }, f, indent=2, default=str)
        print(f"💾 Saved raw data: {json_path}")


def main():
    """Main execution."""
    analyzer = WhyCampaignsSucceed()
    analyzer.run_complete_analysis()

    print("\n" + "="*70)
    print("✅ WHY ANALYSIS COMPLETE")
    print("="*70)
    print("\n📄 Check outputs/why_campaigns_succeed_report.md for findings")


if __name__ == "__main__":
    main()
