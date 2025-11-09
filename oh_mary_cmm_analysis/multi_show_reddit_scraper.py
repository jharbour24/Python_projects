#!/usr/bin/env python3
"""
Multi-Show Reddit Scraper
Collects Reddit data for comparative Broadway show analysis.
"""

try:
    import praw
    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False
    print("ERROR: PRAW not installed. Run: pip install praw")
    exit(1)

import yaml
import json
import time
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, *args, **kwargs):
        return iterable


class MultiShowRedditScraper:
    """Scrapes Reddit for multiple Broadway shows for comparative analysis."""

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize multi-show Reddit scraper.

        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Reddit API credentials (provided by user)
        self.client_id = "22B5R9jLxYTP57kKYQKpjA"
        self.client_secret = "bZEos_3-52PK0g-n6IYvTBR7t1P2Jg"
        self.user_agent = "Jharbour123"

        # Initialize Reddit API
        print("🔧 Initializing Reddit API...")
        try:
            self.reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent
            )
            # Test connection
            self.reddit.user.me()
            print("✓ Reddit API connected successfully!")
        except Exception as e:
            print(f"✗ Failed to connect to Reddit API: {e}")
            print("\nPlease verify your credentials are correct.")
            exit(1)

        # Extract show configurations
        self.shows = self.config.get('shows', {})
        self.subreddits = self.config.get('reddit', {}).get('subreddits', [])
        self.limit_per_subreddit = self.config.get('limits', {}).get('reddit_posts_per_subreddit', 100)

        print(f"\n📊 Configuration loaded:")
        print(f"  • Shows to analyze: {len(self.shows)}")
        print(f"  • Subreddits to search: {len(self.subreddits)}")
        print(f"  • Posts per subreddit: {self.limit_per_subreddit}")

    def search_subreddit_for_show(self, subreddit_name: str, show_name: str, keywords: List[str]) -> List[Dict]:
        """
        Search a subreddit for posts about a specific show.

        Args:
            subreddit_name: Name of subreddit
            show_name: Name of the show
            keywords: List of keywords to search

        Returns:
            List of post dictionaries
        """
        posts = []

        try:
            subreddit = self.reddit.subreddit(subreddit_name)

            for keyword in keywords:
                try:
                    search_results = subreddit.search(
                        keyword,
                        limit=self.limit_per_subreddit,
                        time_filter='year',
                        sort='relevance'
                    )

                    for submission in search_results:
                        post_data = self._extract_post_data(submission, show_name)
                        posts.append(post_data)
                        time.sleep(0.1)  # Rate limiting

                except Exception as e:
                    # Skip if subreddit doesn't exist or is private
                    if "private" in str(e).lower() or "banned" in str(e).lower():
                        continue
                    # Rate limit handling
                    elif "429" in str(e) or "rate limit" in str(e).lower():
                        print(f"  ⏸ Rate limited, waiting 60 seconds...")
                        time.sleep(60)
                        continue
                    else:
                        continue

        except Exception as e:
            # Subreddit doesn't exist or other error
            pass

        return posts

    def _extract_post_data(self, submission, show_name: str) -> Dict[str, Any]:
        """
        Extract relevant data from Reddit submission.

        Args:
            submission: PRAW submission object
            show_name: Name of the show this post is about

        Returns:
            Dictionary with post data
        """
        # Expand comments (limited to avoid excessive API calls)
        try:
            submission.comments.replace_more(limit=0)
            comments = []

            for comment in list(submission.comments.list())[:25]:  # Top 25 comments
                try:
                    comments.append({
                        'id': comment.id,
                        'author': str(comment.author) if comment.author else '[deleted]',
                        'text': comment.body,
                        'score': comment.score,
                        'created_utc': datetime.fromtimestamp(comment.created_utc).isoformat(),
                    })
                except:
                    continue
        except:
            comments = []

        return {
            'id': submission.id,
            'title': submission.title,
            'text': submission.selftext,
            'author': str(submission.author) if submission.author else '[deleted]',
            'subreddit': str(submission.subreddit),
            'score': submission.score,
            'upvote_ratio': submission.upvote_ratio,
            'num_comments': submission.num_comments,
            'created_utc': datetime.fromtimestamp(submission.created_utc).isoformat(),
            'url': f"https://reddit.com{submission.permalink}",
            'comments': comments,
            'platform': 'reddit',
            'show': show_name,
            'scraped_at': datetime.now().isoformat()
        }

    def collect_for_show(self, show_id: str, show_config: Dict) -> List[Dict]:
        """
        Collect all Reddit data for a specific show.

        Args:
            show_id: Show identifier (e.g., 'oh_mary')
            show_config: Show configuration with name and keywords

        Returns:
            List of all collected posts for this show
        """
        show_name = show_config['name']
        keywords = show_config['keywords']
        all_posts = []

        print(f"\n{'='*70}")
        print(f"🎭 Collecting data for: {show_name}")
        print(f"{'='*70}")
        print(f"Keywords: {', '.join(keywords[:3])}{'...' if len(keywords) > 3 else ''}")

        for subreddit in tqdm(self.subreddits, desc=f"Searching subreddits"):
            posts = self.search_subreddit_for_show(subreddit, show_name, keywords)
            all_posts.extend(posts)
            time.sleep(2)  # Rate limiting between subreddits

        # Deduplicate by post ID
        seen_ids = set()
        unique_posts = []
        for post in all_posts:
            if post['id'] not in seen_ids:
                seen_ids.add(post['id'])
                unique_posts.append(post)

        print(f"\n✓ Collected {len(unique_posts)} unique posts for {show_name}")

        return unique_posts

    def collect_all_shows(self) -> Dict[str, List[Dict]]:
        """
        Collect data for all shows in configuration.

        Returns:
            Dictionary mapping show_id to list of posts
        """
        results = {}

        print("\n" + "="*70)
        print("🚀 Starting Multi-Show Reddit Collection")
        print("="*70)
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        for show_id, show_config in self.shows.items():
            results[show_id] = self.collect_for_show(show_id, show_config)

            # Save after each show (in case of interruption)
            self._save_show_data(show_id, results[show_id], show_config['name'])

        return results

    def _save_show_data(self, show_id: str, posts: List[Dict], show_name: str):
        """
        Save collected data for a show to CSV and JSON.

        Args:
            show_id: Show identifier
            posts: List of post dictionaries
            show_name: Full name of the show
        """
        if not posts:
            print(f"⚠ No data collected for {show_name}, skipping save")
            return

        # Create output directory
        data_dir = Path("data/raw")
        data_dir.mkdir(parents=True, exist_ok=True)

        # Prepare data for CSV (flatten comments)
        csv_data = []
        for post in posts:
            post_copy = post.copy()
            # Convert comments to JSON string for CSV
            post_copy['comments_json'] = json.dumps(post_copy['comments'])
            post_copy['comment_count'] = len(post_copy['comments'])
            del post_copy['comments']
            csv_data.append(post_copy)

        # Save CSV
        csv_path = data_dir / f"reddit_{show_id}.csv"
        df = pd.DataFrame(csv_data)
        df.to_csv(csv_path, index=False)
        print(f"  💾 Saved CSV: {csv_path}")

        # Save full JSON (with nested comments)
        json_path = data_dir / f"reddit_{show_id}.json"
        with open(json_path, 'w') as f:
            json.dump(posts, f, indent=2)
        print(f"  💾 Saved JSON: {json_path}")

    def generate_collection_summary(self, results: Dict[str, List[Dict]]):
        """
        Generate and save collection summary.

        Args:
            results: Dictionary mapping show_id to posts
        """
        print("\n" + "="*70)
        print("📊 COLLECTION SUMMARY")
        print("="*70)

        summary = {
            'collection_date': datetime.now().isoformat(),
            'total_subreddits_searched': len(self.subreddits),
            'shows': {}
        }

        for show_id, posts in results.items():
            show_name = self.shows[show_id]['name']

            # Calculate statistics
            subreddits = set(p['subreddit'] for p in posts)
            total_comments = sum(len(p.get('comments', [])) for p in posts)
            total_score = sum(p.get('score', 0) for p in posts)
            avg_score = total_score / len(posts) if posts else 0

            summary['shows'][show_id] = {
                'name': show_name,
                'posts_collected': len(posts),
                'subreddits_found_in': len(subreddits),
                'total_comments': total_comments,
                'average_score': round(avg_score, 2),
                'date_range': {
                    'earliest': min((p['created_utc'] for p in posts), default='N/A'),
                    'latest': max((p['created_utc'] for p in posts), default='N/A')
                }
            }

            print(f"\n{show_name}:")
            print(f"  • Posts: {len(posts)}")
            print(f"  • Comments: {total_comments}")
            print(f"  • Subreddits: {len(subreddits)}")
            print(f"  • Avg Score: {avg_score:.1f}")

        # Save summary
        summary_path = Path("data/raw/collection_summary.json")
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"\n💾 Summary saved to: {summary_path}")
        print("\n" + "="*70)
        print("✅ Collection Complete!")
        print("="*70)


def main():
    """Main execution function."""
    print("\n" + "="*70)
    print("🎭 Multi-Show Broadway Reddit Scraper")
    print("="*70)
    print("\nThis will collect Reddit data for:")
    print("  1. Oh Mary!")
    print("  2. John Proctor is the Villain")
    print("  3. Maybe Happy Ending")
    print("\nSearching across 30+ subreddits...")
    print("\n⚠️  This may take 20-40 minutes depending on Reddit API rate limits.")

    response = input("\nProceed with collection? (yes/no): ").strip().lower()

    if response not in ['yes', 'y']:
        print("Collection cancelled.")
        return

    # Initialize scraper
    scraper = MultiShowRedditScraper()

    # Collect data for all shows
    results = scraper.collect_all_shows()

    # Generate summary
    scraper.generate_collection_summary(results)

    print("\n🚀 Next steps:")
    print("  1. Review collected data in data/raw/")
    print("  2. Run analysis: python run_comparative_analysis.py")


if __name__ == "__main__":
    main()
