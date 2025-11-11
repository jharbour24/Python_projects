# Instagram & TikTok Authentication Guide

This guide explains how to add authenticated access to Instagram and TikTok for more complete data collection.

## ⚠️ Important Considerations

**Before implementing authentication:**
1. **Terms of Service**: Review each platform's ToS. Automated scraping may violate terms even with authentication
2. **Rate Limits**: Authenticated access often has stricter rate limits
3. **Account Risk**: Your personal account could be suspended or banned
4. **Legal**: Ensure compliance with CFAA and platform agreements

**Recommendation**: Use official APIs where available, or dedicated research accounts (not personal accounts).

---

## Option 1: Instagram Authentication (Recommended: Official API)

### A. Instagram Graph API (Business Accounts Only)

**Best for**: Production use, official data access

**Requirements**:
- Facebook Developer Account
- Instagram Business or Creator Account
- Facebook Page linked to Instagram account

**Setup Steps**:

1. **Create Facebook App**:
   ```bash
   # Go to https://developers.facebook.com/apps
   # Create new app → Select "Business" type
   ```

2. **Add Instagram Graph API**:
   ```
   App Dashboard → Add Product → Instagram Graph API
   ```

3. **Get Access Token**:
   ```
   Tools → Graph API Explorer
   → Select your app
   → Add permissions: instagram_basic, instagram_manage_insights
   → Generate Token
   ```

4. **Create credentials file**:
   ```bash
   # config/credentials.yaml (add to .gitignore!)
   instagram:
     access_token: "YOUR_ACCESS_TOKEN_HERE"
     instagram_account_id: "YOUR_IG_ACCOUNT_ID"
   ```

5. **Install Instagram API client**:
   ```bash
   pip install facebook-sdk
   ```

6. **Update Instagram scraper**:

```python
# src/scrapers/instagram_auth.py
"""
Authenticated Instagram scraper using Graph API.
"""

import facebook
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd


class InstagramGraphAPIScraper:
    """Scraper using Instagram Graph API (requires business account)."""

    def __init__(self, credentials_path: Path = Path("config/credentials.yaml")):
        """
        Initialize with credentials.

        Args:
            credentials_path: Path to credentials YAML file
        """
        with open(credentials_path, 'r') as f:
            creds = yaml.safe_load(f)

        self.access_token = creds['instagram']['access_token']
        self.account_id = creds['instagram']['instagram_account_id']

        self.graph = facebook.GraphAPI(access_token=self.access_token, version="18.0")

    def get_media_posts(
        self,
        limit: int = 100,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Fetch media posts from Instagram account.

        Args:
            limit: Max number of posts to fetch
            since: Start date
            until: End date

        Returns:
            DataFrame with post data
        """
        # Build query
        fields = "id,caption,media_type,media_url,permalink,timestamp,like_count,comments_count"

        params = {"fields": fields, "limit": limit}

        if since:
            params["since"] = int(since.timestamp())
        if until:
            params["until"] = int(until.timestamp())

        # Fetch media
        media = self.graph.get_object(f"{self.account_id}/media", **params)

        posts = []
        for item in media.get("data", []):
            posts.append({
                "post_id": item.get("id"),
                "caption": item.get("caption", ""),
                "media_type": item.get("media_type"),
                "permalink": item.get("permalink"),
                "timestamp": datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00")),
                "likes": item.get("like_count", 0),
                "comments": item.get("comments_count", 0),
            })

        return pd.DataFrame(posts)

    def get_media_insights(self, media_id: str) -> Dict:
        """
        Get insights for a specific media post.

        Args:
            media_id: Instagram media ID

        Returns:
            Dict with engagement, impressions, reach, saves
        """
        metrics = "engagement,impressions,reach,saved"
        insights = self.graph.get_object(f"{media_id}/insights", metric=metrics)

        result = {}
        for item in insights.get("data", []):
            result[item["name"]] = item["values"][0]["value"]

        return result

    def get_account_insights(
        self,
        since: datetime,
        until: datetime,
        period: str = "day"
    ) -> pd.DataFrame:
        """
        Get account-level insights.

        Args:
            since: Start date
            until: End date
            period: day, week, days_28

        Returns:
            DataFrame with daily metrics
        """
        metrics = "impressions,reach,profile_views,follower_count"

        params = {
            "metric": metrics,
            "period": period,
            "since": int(since.timestamp()),
            "until": int(until.timestamp()),
        }

        insights = self.graph.get_object(f"{self.account_id}/insights", **params)

        # Parse time series
        data = []
        for metric in insights.get("data", []):
            metric_name = metric["name"]
            for value in metric.get("values", []):
                data.append({
                    "date": datetime.fromisoformat(value["end_time"].replace("Z", "+00:00")),
                    metric_name: value["value"],
                })

        df = pd.DataFrame(data)
        if not df.empty:
            df = df.groupby("date").first().reset_index()

        return df
```

**Usage**:
```python
from src.scrapers.instagram_auth import InstagramGraphAPIScraper

scraper = InstagramGraphAPIScraper()

# Get recent posts
posts = scraper.get_media_posts(limit=100)

# Get insights for a post
insights = scraper.get_media_insights(posts.iloc[0]['post_id'])

# Get account metrics
account_data = scraper.get_account_insights(
    since=datetime(2024, 1, 1),
    until=datetime.now()
)
```

---

### B. Instaloader (Username/Password - Use at your own risk)

**Best for**: Research, personal projects

**⚠️ WARNING**: This violates Instagram ToS and risks account suspension. Use a dedicated research account, not your personal account.

**Setup**:

```bash
pip install instaloader
```

```python
# src/scrapers/instagram_instaloader.py
"""
Instagram scraper using Instaloader (username/password auth).
WARNING: Violates Instagram ToS. Use at your own risk.
"""

import instaloader
import yaml
from pathlib import Path
from datetime import datetime
from typing import Optional
import pandas as pd


class InstagramInstaloader:
    """Scraper using Instaloader with authentication."""

    def __init__(self, credentials_path: Path = Path("config/credentials.yaml")):
        """Initialize and login."""
        with open(credentials_path, 'r') as f:
            creds = yaml.safe_load(f)

        self.username = creds['instagram']['username']
        self.password = creds['instagram']['password']

        self.L = instaloader.Instaloader(
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=True,
            save_metadata=False,
        )

        # Login
        try:
            self.L.load_session_from_file(self.username)
            print(f"Loaded existing session for @{self.username}")
        except FileNotFoundError:
            print(f"Logging in as @{self.username}...")
            self.L.login(self.username, self.password)
            self.L.save_session_to_file()
            print("Session saved for future use")

    def scrape_profile(
        self,
        profile_name: str,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Scrape posts from a profile.

        Args:
            profile_name: Instagram username (without @)
            since: Start date
            until: End date

        Returns:
            DataFrame with post data
        """
        profile = instaloader.Profile.from_username(self.L.context, profile_name)

        posts = []

        for post in profile.get_posts():
            # Date filter
            if until and post.date > until:
                continue
            if since and post.date < since:
                break  # Stop iteration (posts are chronological)

            # Get comment details
            commenters = set()
            comment_count = 0

            try:
                for comment in post.get_comments():
                    commenters.add(comment.owner.username)
                    comment_count += 1
                    if comment_count >= 1000:  # Limit to avoid rate limiting
                        break
            except Exception as e:
                print(f"Could not fetch comments for post {post.shortcode}: {e}")

            posts.append({
                "post_id": post.mediaid,
                "shortcode": post.shortcode,
                "date": post.date,
                "likes": post.likes,
                "comments": post.comments,
                "caption": post.caption or "",
                "media_type": "video" if post.is_video else "photo",
                "url": f"https://www.instagram.com/p/{post.shortcode}/",
                "unique_commenters": len(commenters),
            })

        return pd.DataFrame(posts)

    def get_profile_stats(self, profile_name: str) -> Dict:
        """Get profile statistics."""
        profile = instaloader.Profile.from_username(self.L.context, profile_name)

        return {
            "username": profile.username,
            "full_name": profile.full_name,
            "followers": profile.followers,
            "following": profile.followees,
            "posts": profile.mediacount,
            "is_business": profile.is_business_account,
            "is_verified": profile.is_verified,
        }
```

**credentials.yaml** (for Instaloader):
```yaml
instagram:
  username: "your_research_account_username"
  password: "your_password"
```

**⚠️ Security**:
```bash
# Add to .gitignore
echo "config/credentials.yaml" >> .gitignore
echo "session-*" >> .gitignore  # Instaloader session files
```

---

## Option 2: TikTok Authentication

### A. TikTok Research API (Recommended, but requires approval)

**Best for**: Academic research, official use

**Requirements**:
- Institutional affiliation (university, research org)
- Research proposal
- IRB approval (for human subjects research)

**Setup**:

1. **Apply for access**:
   ```
   https://developers.tiktok.com/products/research-api
   ```

2. **Once approved, get credentials**:
   ```yaml
   # config/credentials.yaml
   tiktok:
     client_key: "YOUR_CLIENT_KEY"
     client_secret: "YOUR_CLIENT_SECRET"
   ```

3. **Install official client**:
   ```bash
   pip install tiktok-research-api-client
   ```

4. **Implement authenticated scraper**:

```python
# src/scrapers/tiktok_research_api.py
"""
TikTok Research API scraper (requires institutional approval).
"""

from tiktok_research_api import TikTokResearchAPI
import yaml
from pathlib import Path
from datetime import datetime
from typing import List
import pandas as pd


class TikTokResearchScraper:
    """Scraper using official TikTok Research API."""

    def __init__(self, credentials_path: Path = Path("config/credentials.yaml")):
        """Initialize with credentials."""
        with open(credentials_path, 'r') as f:
            creds = yaml.safe_load(f)

        self.client = TikTokResearchAPI(
            client_key=creds['tiktok']['client_key'],
            client_secret=creds['tiktok']['client_secret'],
        )

    def search_videos(
        self,
        query: str,
        start_date: datetime,
        end_date: datetime,
        max_count: int = 100,
    ) -> pd.DataFrame:
        """
        Search for videos matching query.

        Args:
            query: Search query (hashtag or keyword)
            start_date: Start date
            end_date: End date
            max_count: Max videos to return

        Returns:
            DataFrame with video data
        """
        videos = self.client.video.query(
            query={"and": [{"field_name": "hashtag_name", "operation": "IN", "field_values": [query]}]},
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
            max_count=max_count,
        )

        data = []
        for video in videos:
            data.append({
                "video_id": video.id,
                "create_time": datetime.fromtimestamp(video.create_time),
                "username": video.username,
                "region_code": video.region_code,
                "video_description": video.video_description,
                "music_id": video.music_id,
                "like_count": video.like_count,
                "comment_count": video.comment_count,
                "share_count": video.share_count,
                "view_count": video.view_count,
                "hashtags": video.hashtag_names,
            })

        return pd.DataFrame(data)

    def get_user_info(self, username: str) -> Dict:
        """Get user profile information."""
        user = self.client.user.info(username=username)

        return {
            "username": user.username,
            "display_name": user.display_name,
            "follower_count": user.follower_count,
            "following_count": user.following_count,
            "video_count": user.video_count,
            "is_verified": user.is_verified,
        }
```

---

### B. Unofficial TikTok API (No authentication, limited data)

**Best for**: Quick prototyping, limited access

**⚠️ WARNING**: Unofficial, may break at any time.

```bash
pip install TikTokApi
```

```python
# src/scrapers/tiktok_unofficial.py
"""
Unofficial TikTok scraper (no auth, limited access).
May violate ToS. Use at your own risk.
"""

from TikTokApi import TikTokApi
from datetime import datetime
import pandas as pd


class TikTokUnofficialScraper:
    """Unofficial TikTok scraper."""

    def __init__(self):
        """Initialize API."""
        self.api = TikTokApi()

    def search_hashtag(
        self,
        hashtag: str,
        count: int = 30,
    ) -> pd.DataFrame:
        """
        Search videos by hashtag.

        Args:
            hashtag: Hashtag without #
            count: Number of videos to fetch

        Returns:
            DataFrame with video data
        """
        videos = []

        try:
            # Get hashtag videos
            for video in self.api.hashtag(name=hashtag).videos(count=count):
                videos.append({
                    "video_id": video.id,
                    "create_time": datetime.fromtimestamp(video.create_time),
                    "author": video.author.username,
                    "description": video.desc,
                    "likes": video.stats.digg_count,
                    "comments": video.stats.comment_count,
                    "shares": video.stats.share_count,
                    "plays": video.stats.play_count,
                })
        except Exception as e:
            print(f"Error fetching TikTok data: {e}")

        return pd.DataFrame(videos)
```

---

## Updating the Pipeline for Authentication

### 1. Add credentials template

```yaml
# config/credentials.template.yaml
# Copy to credentials.yaml and fill in your values

instagram:
  # Option A: Graph API (Business accounts)
  access_token: "YOUR_ACCESS_TOKEN_HERE"
  instagram_account_id: "YOUR_IG_ACCOUNT_ID"

  # Option B: Instaloader (Use at your own risk)
  username: "your_research_account"
  password: "your_password"

tiktok:
  # TikTok Research API
  client_key: "YOUR_CLIENT_KEY"
  client_secret: "YOUR_CLIENT_SECRET"
```

### 2. Update `.gitignore`

```bash
# Add to .gitignore
config/credentials.yaml
session-*
*.session
```

### 3. Update requirements.txt

```bash
# Add to requirements.txt
facebook-sdk==3.1.0  # For Instagram Graph API
instaloader==4.10.3  # For Instagram username/password (use with caution)
tiktok-research-api-client==0.1.0  # For TikTok Research API (if approved)
TikTokApi==6.0.0  # Unofficial TikTok (use with caution)
```

### 4. Update notebooks to use authenticated scrapers

```python
# notebooks/01_collect.ipynb - Add authentication cell

## Optional: Use Authenticated Scrapers

# Check if credentials exist
if Path('../config/credentials.yaml').exists():
    # Instagram Graph API
    from src.scrapers.instagram_auth import InstagramGraphAPIScraper
    ig_auth = InstagramGraphAPIScraper()

    # Fetch authenticated data
    for show_id, show_info in shows.items():
        handle = show_info.get('instagram_handle')
        if handle:
            posts = ig_auth.get_media_posts(limit=200)
            # ... process posts

    # TikTok Research API
    from src.scrapers.tiktok_research_api import TikTokResearchScraper
    tt_auth = TikTokResearchScraper()

    # ... similar for TikTok
else:
    print("No credentials file found. Using unauthenticated scrapers.")
```

---

## Best Practices

1. **Use Dedicated Research Accounts**: Never use personal accounts for automated scraping
2. **Respect Rate Limits**: Even with authentication, don't spam requests
3. **Cache Aggressively**: Store authenticated data locally to minimize API calls
4. **Monitor Account Health**: Check for warnings/restrictions daily
5. **Document Data Provenance**: Note which data came from which auth method
6. **Legal Review**: Have institutional legal counsel review your approach

---

## Recommended Approach for Your Pipeline

Given your research context, I recommend:

**Instagram**: Use **Graph API** if you can get business account access, otherwise document limitation in methodology

**TikTok**: Apply for **Research API** (takes 2-4 weeks for approval). In the meantime, use public scraping with heavy caching.

**Fallback**: If authentication not feasible, clearly document in `METHODOLOGY.md` that public data limitations are a known threat to validity.

---

**Questions?** See platform documentation:
- Instagram: https://developers.facebook.com/docs/instagram-api
- TikTok Research API: https://developers.tiktok.com/doc/research-api-overview
