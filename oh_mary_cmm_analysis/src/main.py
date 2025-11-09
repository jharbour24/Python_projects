#!/usr/bin/env python3
"""
Main script for Oh Mary! Cultural Movement Marketing (CMM) Analysis.

This script orchestrates the complete analysis pipeline:
1. Data collection from Reddit, TikTok, Instagram
2. Discourse extraction and labeling
3. NLP analysis (embeddings, clustering, sentiment)
4. CMM metrics calculation
5. Visualization generation
6. Report compilation
"""

import sys
import warnings
from pathlib import Path
import pandas as pd
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Import modules
from utils.config_loader import load_config, get_search_keywords, get_platforms, get_movement_lexicon
from utils.data_storage import DataStorage
from scrapers.reddit_scraper import RedditScraper, create_manual_reddit_template
from scrapers.tiktok_scraper import TikTokScraper
from scrapers.instagram_scraper import InstagramScraper
from analysis.discourse_extractor import DiscourseExtractor
from analysis.nlp_engine import NLPEngine
from analysis.cmm_metrics import CMMMetricsCalculator
from analysis.visualizations import CMMVisualizer
from analysis.report_generator import ReportGenerator

warnings.filterwarnings('ignore')


class OhMaryCMMAnalysis:
    """Main analysis orchestrator."""

    def __init__(self, config_path: str = None):
        """
        Initialize analysis.

        Args:
            config_path: Path to configuration file
        """
        print("\n" + "="*70)
        print("Oh Mary! Cultural Movement Marketing (CMM) Analysis")
        print("="*70)

        # Load configuration
        self.config = load_config(config_path)
        self.keywords = get_search_keywords(self.config)
        self.platforms = get_platforms(self.config)
        self.lexicon = get_movement_lexicon(self.config)

        # Initialize components
        self.storage = DataStorage()
        self.discourse_extractor = DiscourseExtractor(self.lexicon)
        self.nlp_engine = NLPEngine(self.config)
        self.metrics_calculator = CMMMetricsCalculator(self.config)
        self.visualizer = CMMVisualizer()
        self.report_generator = ReportGenerator()

        # Data
        self.raw_data = []
        self.processed_df = None
        self.metrics = {}
        self.assumption_log = []

        print(f"\n✓ Configuration loaded")
        print(f"  - Platforms: {', '.join(self.platforms)}")
        print(f"  - Keywords: {len(self.keywords)}")
        print(f"  - Date range: {self.config.get('date_range', 'N/A')}")

    def collect_data(self):
        """Step 1: Collect data from all platforms."""
        print("\n" + "="*70)
        print("STEP 1: Data Collection")
        print("="*70)

        all_data = []

        # Reddit
        if 'reddit' in self.platforms:
            print("\n📱 Reddit Data Collection")
            print("-" * 60)
            reddit_scraper = RedditScraper(self.config)
            reddit_data = reddit_scraper.collect_all()

            if not reddit_data:
                print("\n⚠ No Reddit data collected via API.")
                print("Checking for manual data file...")
                manual_path = Path(__file__).parent.parent / "data" / "raw" / "reddit_manual.csv"
                if manual_path.exists():
                    try:
                        df = pd.read_csv(manual_path)
                        reddit_data = df.to_dict('records')
                        for item in reddit_data:
                            item['platform'] = 'reddit'
                        print(f"✓ Loaded {len(reddit_data)} posts from manual file")
                    except Exception as e:
                        print(f"✗ Error loading manual file: {e}")
                else:
                    create_manual_reddit_template()
                    self.assumption_log.append(
                        "Reddit data: No API access. Template created for manual entry. "
                        "Analysis will proceed with available data from other platforms."
                    )

            all_data.extend(reddit_data)

        # TikTok
        if 'tiktok' in self.platforms:
            print("\n📱 TikTok Data Collection")
            print("-" * 60)
            tiktok_scraper = TikTokScraper(self.config)
            tiktok_data = tiktok_scraper.collect_all()

            # Check for manual data
            manual_path = Path(__file__).parent.parent / "data" / "raw" / "tiktok_manual.csv"
            if manual_path.exists():
                manual_data = tiktok_scraper.load_manual_data(str(manual_path))
                all_data.extend(manual_data)
            else:
                self.assumption_log.append(
                    "TikTok data: Automated scraping blocked. Template created for manual entry. "
                    "Consider using third-party APIs (Apify, RapidAPI) for comprehensive TikTok data."
                )

        # Instagram
        if 'instagram' in self.platforms:
            print("\n📱 Instagram Data Collection")
            print("-" * 60)
            instagram_scraper = InstagramScraper(self.config)
            instagram_data = instagram_scraper.collect_all()

            # Check for manual data
            manual_path = Path(__file__).parent.parent / "data" / "raw" / "instagram_manual.csv"
            if manual_path.exists():
                manual_data = instagram_scraper.load_manual_data(str(manual_path))
                all_data.extend(manual_data)
            else:
                self.assumption_log.append(
                    "Instagram data: Requires authentication. Template created for manual entry. "
                    "Consider using Instagram Basic Display API or third-party scrapers."
                )

        # Save raw data
        if all_data:
            self.raw_data = all_data
            self.storage.save_raw_json(all_data, "combined")
            print(f"\n✓ Total collected: {len(all_data)} items")
        else:
            print("\n⚠ WARNING: No data collected!")
            print("Creating demonstration dataset for analysis pipeline...")
            self.raw_data = self._create_demo_data()

        return len(all_data)

    def process_discourse(self):
        """Step 2: Extract and label discourse."""
        print("\n" + "="*70)
        print("STEP 2: Discourse Extraction & Labeling")
        print("="*70)

        processed_items = []

        for item in self.raw_data:
            # Extract text
            text = self._extract_text(item)

            if not text:
                continue

            # Extract features
            features = self.discourse_extractor.extract_features(text)

            # Label discourse type
            labels = self.discourse_extractor.label_discourse_type(features)

            # Classify tone
            tone = self.discourse_extractor.classify_audience_tone(features, labels)

            # Sentiment analysis
            sentiment = self.nlp_engine.analyze_sentiment(text)

            # Combine all data
            processed = {
                **item,
                **features,
                **labels,
                'audience_tone': tone,
                'sentiment_polarity': sentiment['polarity'],
                'sentiment_subjectivity': sentiment['subjectivity']
            }

            # Add engagement score (normalized)
            processed['engagement_score'] = self._calculate_engagement_score(item)

            processed_items.append(processed)

        # Create DataFrame
        self.processed_df = pd.DataFrame(processed_items)

        print(f"\n✓ Processed {len(self.processed_df)} items")
        print(f"  - Movement score > 0.5: {(self.processed_df['movement_score'] > 0.5).sum()}")
        print(f"  - Identity resonance: {self.processed_df['identity_resonance'].sum()}")
        print(f"  - Evangelism: {self.processed_df['evangelism'].sum()}")

        return self.processed_df

    def perform_nlp_analysis(self):
        """Step 3: Advanced NLP analysis."""
        print("\n" + "="*70)
        print("STEP 3: NLP Analysis")
        print("="*70)

        # Generate embeddings
        print("\n🧠 Generating embeddings...")
        texts = self.processed_df['original_text'].tolist()
        embeddings = self.nlp_engine.generate_embeddings(texts)

        # Clustering
        print("\n🔍 Clustering discourse...")
        # Adjust clusters based on sample size
        n_clusters = min(5, max(2, len(texts) // 2))
        if len(texts) >= 2:
            cluster_labels, cluster_info = self.nlp_engine.cluster_discourse(embeddings, n_clusters=n_clusters)
            self.processed_df['cluster'] = cluster_labels
        else:
            print("⚠ Insufficient data for clustering")
            cluster_labels = np.zeros(len(texts))
            self.processed_df['cluster'] = cluster_labels

        # Pronoun shift analysis
        print("\n📊 Analyzing pronoun patterns...")
        pronoun_stats = self.nlp_engine.calculate_pronoun_shift(texts)
        print(f"  - We/Us/Our: {pronoun_stats['we_count']}")
        print(f"  - I/Me/My: {pronoun_stats['i_count']}")
        print(f"  - Shift index: {pronoun_stats['shift_index']:.3f}")

        # Extract key phrases
        print("\n🔑 Extracting key phrases...")
        key_phrases = self.nlp_engine.extract_key_phrases(texts, top_n=20)
        print("  Top phrases:")
        for phrase, count in key_phrases[:10]:
            print(f"    - '{phrase}': {count}")

        # Detect memes
        print("\n🎭 Detecting mimetic motifs...")
        memes = self.nlp_engine.detect_mimetic_motifs(texts, min_frequency=3)
        print(f"  - Found {len(memes)} repeated motifs")

        self.memes = memes
        self.cluster_labels = cluster_labels

        return embeddings, cluster_labels, memes

    def calculate_metrics(self):
        """Step 4: Calculate CMM metrics."""
        print("\n" + "="*70)
        print("STEP 4: CMM Metrics Calculation")
        print("="*70)

        self.metrics = self.metrics_calculator.calculate_all_metrics(self.processed_df)

        # Print summary
        print(f"\n📈 Metrics Summary:")
        print(f"  - Overall CMM Score: {self.metrics['Overall_CMM_Score']['score']:.1f}/100")
        print(f"  - Category: {self.metrics['Overall_CMM_Score']['category']}")
        print(f"  - MSS: {self.metrics['MSS']['score']:.3f}")
        print(f"  - IRI: {self.metrics['IRI']['percentage']:.1f}%")
        print(f"  - ER: {self.metrics['ER']['percentage']:.1f}%")
        print(f"  - RAS: {self.metrics['RAS']['percentage']:.1f}%")

        return self.metrics

    def generate_outputs(self):
        """Step 5: Generate visualizations and reports."""
        print("\n" + "="*70)
        print("STEP 5: Output Generation")
        print("="*70)

        # Visualizations
        print("\n📊 Creating visualizations...")
        self.visualizer.create_all_visualizations(
            self.processed_df,
            self.metrics,
            self.cluster_labels
        )

        # Reports
        print("\n📝 Generating reports...")
        examples = self._extract_examples()

        self.report_generator.generate_main_report(
            self.metrics,
            self.processed_df,
            self.config,
            examples
        )

        # Save CSVs
        print("\n💾 Saving data outputs...")
        community_signals = self._extract_community_signals()
        self.report_generator.save_csv_outputs(
            self.processed_df,
            self.memes,
            community_signals
        )

        # Save metrics
        self.report_generator.save_metrics_json(self.metrics)

        # Assumption log
        self.storage.save_assumption_log(self.assumption_log)

        print("\n✓ All outputs generated")

    def run_complete_analysis(self):
        """Run complete analysis pipeline."""
        try:
            # Step 1: Collect data
            self.collect_data()

            # Step 2: Process discourse
            self.process_discourse()

            # Step 3: NLP analysis
            self.perform_nlp_analysis()

            # Step 4: Calculate metrics
            self.calculate_metrics()

            # Step 5: Generate outputs
            self.generate_outputs()

            print("\n" + "="*70)
            print("✅ ANALYSIS COMPLETE")
            print("="*70)

            print(f"\n📊 Final Results:")
            print(f"  - Overall CMM Score: {self.metrics['Overall_CMM_Score']['score']:.1f}/100")
            print(f"  - {self.metrics['Overall_CMM_Score']['interpretation']}")

            print(f"\n📁 Outputs saved to:")
            print(f"  - Report: outputs/reports/report.md")
            print(f"  - Metrics: outputs/reports/metrics.json")
            print(f"  - Visualizations: outputs/visualizations/")
            print(f"  - Data: data/processed/")

        except Exception as e:
            print(f"\n❌ Error during analysis: {e}")
            import traceback
            traceback.print_exc()
            raise

    # Helper methods

    def _extract_text(self, item: dict) -> str:
        """Extract text from item."""
        # Try different text fields
        for field in ['text', 'caption', 'selftext', 'body', 'title']:
            if field in item and item[field]:
                text = str(item[field])
                # Add title if it exists and is different
                if field != 'title' and 'title' in item and item['title']:
                    text = f"{item['title']} {text}"
                return text
        return ""

    def _calculate_engagement_score(self, item: dict) -> float:
        """Calculate normalized engagement score."""
        # Reddit: score (upvotes - downvotes)
        if 'score' in item:
            return max(float(item['score']), 0)

        # TikTok/Instagram: likes
        if 'likes' in item:
            return float(item['likes'])

        return 0.0

    def _extract_examples(self) -> dict:
        """Extract example quotes for each category."""
        examples = {}

        categories = [
            ('identity_resonance', 'Identity Resonance'),
            ('evangelism', 'Evangelism'),
            ('repeat_attendance', 'Repeat Attendance'),
            ('collective_voice', 'Collective Voice'),
            ('insider_gatekeeping', 'Insider Gatekeeping')
        ]

        for col, name in categories:
            if col in self.processed_df.columns:
                matching = self.processed_df[self.processed_df[col] == True]
                if len(matching) > 0:
                    # Get top by engagement
                    top = matching.nlargest(5, 'engagement_score')
                    quotes = []
                    for _, row in top.iterrows():
                        text = row['original_text'][:200] + "..." if len(row['original_text']) > 200 else row['original_text']
                        url = row.get('url', 'N/A')
                        created = row.get('created_utc', 'N/A')
                        quotes.append(f'"{text}" ([Source]({url}), {created})')
                    examples[name] = quotes

        return examples

    def _extract_community_signals(self) -> pd.DataFrame:
        """Extract community formation signals."""
        community_posts = self.processed_df[
            self.processed_df['community_reference'] == True
        ].copy()

        if len(community_posts) > 0:
            return community_posts[[
                'platform', 'original_text', 'url', 'created_utc',
                'engagement_score', 'community_reference'
            ]]
        else:
            return pd.DataFrame()

    def _create_demo_data(self) -> list:
        """Create demonstration dataset if no real data available."""
        print("\n⚠ Creating demonstration dataset...")
        self.assumption_log.append(
            "DEMO MODE: No real data collected. Using synthetic examples to demonstrate analysis pipeline. "
            "Results are for illustration only."
        )

        demo_posts = [
            {
                'platform': 'reddit',
                'text': 'Oh Mary! changed my life. As a queer person, I felt so seen and represented. This show is for us.',
                'score': 150,
                'url': 'https://reddit.com/example1',
                'created_utc': '2024-06-01T12:00:00'
            },
            {
                'platform': 'reddit',
                'text': 'Saw Oh Mary for the third time! The rush line community is amazing. If you know you know.',
                'score': 89,
                'url': 'https://reddit.com/example2',
                'created_utc': '2024-06-15T14:30:00'
            },
            {
                'platform': 'reddit',
                'text': 'You MUST see Oh Mary! I dragged all my friends and they loved it. Essential theater.',
                'score': 120,
                'url': 'https://reddit.com/example3',
                'created_utc': '2024-07-01T16:00:00'
            },
            {
                'platform': 'reddit',
                'text': 'Oh Mary was fun but not life-changing. Good show.',
                'score': 45,
                'url': 'https://reddit.com/example4',
                'created_utc': '2024-07-10T10:00:00'
            },
            {
                'platform': 'reddit',
                'text': 'The Oh Mary community is so welcoming! Met amazing people at the lottery. Our show!',
                'score': 95,
                'url': 'https://reddit.com/example5',
                'created_utc': '2024-08-01T18:00:00'
            }
        ]

        print(f"✓ Created {len(demo_posts)} demonstration posts")
        return demo_posts


def main():
    """Main entry point."""
    # Initialize analysis
    analysis = OhMaryCMMAnalysis()

    # Run complete pipeline
    analysis.run_complete_analysis()


if __name__ == "__main__":
    main()
