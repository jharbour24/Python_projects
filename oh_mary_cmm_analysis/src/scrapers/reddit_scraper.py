"""Reddit scraper for Oh Mary! discourse analysis."""
try:
    import praw
    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False

import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

try:
    from tqdm import tqdm
except ImportError:
    # Fallback if tqdm not available
    def tqdm(iterable, *args, **kwargs):
        return iterable


class RedditScraper:
    """Scrapes Reddit for Oh Mary! related content."""

    def __init__(self, config: Dict[str, Any], use_api: bool = True):
        """
        Initialize Reddit scraper.

        Args:
            config: Configuration dictionary
            use_api: Whether to use Reddit API (requires credentials)
        """
        self.config = config
        self.keywords = config.get('keywords', [])
        self.subreddits = config.get('reddit', {}).get('subreddits', [])
        self.use_api = use_api and PRAW_AVAILABLE
        self.reddit = None

        if use_api and PRAW_AVAILABLE:
            try:
                # Try to initialize PRAW (will fail without credentials)
                self.reddit = praw.Reddit(
                    client_id='YOUR_CLIENT_ID',
                    client_secret='YOUR_CLIENT_SECRET',
                    user_agent='oh_mary_cmm_analysis:v1.0 (by /u/YOUR_USERNAME)'
                )
                print("✓ Reddit API initialized")
            except Exception as e:
                print(f"⚠ Reddit API not available: {e}")
                print("⚠ Falling back to manual data collection")
                self.use_api = False
        elif not PRAW_AVAILABLE:
            print("⚠ PRAW not installed. Install with: pip install praw")
            print("⚠ Falling back to manual data collection")
            self.use_api = False

    def search_subreddit(self, subreddit_name: str, query: str, limit: int = 100) -> List[Dict]:
        """
        Search a subreddit for posts matching query.

        Args:
            subreddit_name: Name of subreddit
            query: Search query
            limit: Maximum posts to retrieve

        Returns:
            List of post dictionaries
        """
        if not self.use_api or not self.reddit:
            return []

        posts = []
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            search_results = subreddit.search(query, limit=limit, time_filter='year')

            for submission in tqdm(search_results, desc=f"r/{subreddit_name}", leave=False):
                post_data = self._extract_post_data(submission)
                posts.append(post_data)

                # Rate limiting
                time.sleep(0.1)

        except Exception as e:
            print(f"✗ Error searching r/{subreddit_name}: {e}")

        return posts

    def _extract_post_data(self, submission) -> Dict[str, Any]:
        """
        Extract relevant data from Reddit submission.

        Args:
            submission: PRAW submission object

        Returns:
            Dictionary with post data
        """
        # Expand comments
        submission.comments.replace_more(limit=0)
        comments = []

        for comment in submission.comments.list()[:50]:  # Limit to top 50 comments
            comments.append({
                'id': comment.id,
                'author': str(comment.author) if comment.author else '[deleted]',
                'text': comment.body,
                'score': comment.score,
                'created_utc': datetime.fromtimestamp(comment.created_utc).isoformat(),
                'permalink': f"https://reddit.com{comment.permalink}"
            })

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
            'scraped_at': datetime.now().isoformat()
        }

    def collect_all(self) -> List[Dict]:
        """
        Collect all Reddit data based on configuration.

        Returns:
            List of all collected posts
        """
        all_posts = []

        if not self.use_api:
            print("\n⚠ Reddit API not configured. Manual collection required.")
            print("\nTo enable automated collection:")
            print("1. Create Reddit app at https://www.reddit.com/prefs/apps")
            print("2. Set client_id, client_secret, and user_agent in code")
            print("\nAlternatively, provide manual CSV with columns:")
            print("  [id, title, text, author, subreddit, score, url, created_utc]")
            return []

        print(f"\n🔍 Searching {len(self.subreddits)} subreddits...")

        for subreddit in self.subreddits:
            for keyword in self.keywords:
                print(f"\n  → r/{subreddit} for '{keyword}'")
                posts = self.search_subreddit(subreddit, keyword, limit=100)
                all_posts.extend(posts)
                time.sleep(1)  # Rate limiting between searches

        # Deduplicate by post ID
        seen_ids = set()
        unique_posts = []
        for post in all_posts:
            if post['id'] not in seen_ids:
                seen_ids.add(post['id'])
                unique_posts.append(post)

        print(f"\n✓ Collected {len(unique_posts)} unique posts")
        return unique_posts


def create_manual_reddit_template():
    """Create a template CSV for manual Reddit data entry."""
    import pandas as pd
    from pathlib import Path

    template_data = {
        'id': ['example_id'],
        'title': ['Example: Oh Mary! on Broadway'],
        'text': ['Full post text here...'],
        'author': ['username'],
        'subreddit': ['broadway'],
        'score': [100],
        'num_comments': [25],
        'url': ['https://reddit.com/r/broadway/comments/...'],
        'created_utc': ['2024-01-01T12:00:00'],
        'comments_json': ['[{"text": "comment text", "score": 10}]']
    }

    df = pd.DataFrame(template_data)
    output_path = Path(__file__).parent.parent.parent / "data" / "raw" / "reddit_manual_template.csv"
    df.to_csv(output_path, index=False)
    print(f"✓ Created manual template at {output_path}")
