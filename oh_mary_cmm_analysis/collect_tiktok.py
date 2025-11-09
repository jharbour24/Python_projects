#!/usr/bin/env python3
"""
TikTok Manual Collection Helper
Browser-based collection WITHOUT requiring login.
"""

import csv
from datetime import datetime
from pathlib import Path

def print_instructions():
    print("="*70)
    print("TikTok Manual Collection Guide")
    print("="*70)
    print()
    print("📱 SAFE METHOD: No login required, uses public search")
    print()
    print("Step-by-Step Instructions:")
    print("-" * 70)
    print()
    print("1. Open TikTok in your browser (tiktok.com)")
    print("   - You DON'T need to log in")
    print("   - Use incognito/private mode for clean results")
    print()
    print("2. Search for Oh Mary content:")
    print("   - Search: #OhMary")
    print("   - Search: #OhMaryBroadway")
    print("   - Search: Oh Mary Broadway")
    print()
    print("3. For each video (aim for 50-100 videos):")
    print("   - Click video to open")
    print("   - Copy the URL from address bar")
    print("   - Note: author, caption, likes, comments, views")
    print("   - Read 3-5 top comments")
    print()
    print("4. Use this interactive form to record data:")
    print()

def collect_video():
    """Collect single video data interactively."""
    print("\n" + "="*70)
    print("Enter Video Data (or 'done' to finish)")
    print("="*70)

    url = input("\n📎 Video URL: ").strip()
    if url.lower() == 'done':
        return None

    # Auto-extract video ID from URL
    video_id = url.split('/')[-1].split('?')[0] if '/' in url else url

    author = input("👤 Author (@username): ").strip()
    caption = input("📝 Caption: ").strip()
    hashtags = input("🏷️  Hashtags (comma-separated): ").strip()

    try:
        likes = int(input("❤️  Likes: ").strip() or 0)
    except:
        likes = 0

    try:
        comments = int(input("💬 Comments: ").strip() or 0)
    except:
        comments = 0

    try:
        shares = int(input("🔄 Shares: ").strip() or 0)
    except:
        shares = 0

    try:
        views = int(input("👁️  Views: ").strip() or 0)
    except:
        views = 0

    created_at = input("📅 Date (YYYY-MM-DD) or leave blank: ").strip()
    if not created_at:
        created_at = datetime.now().isoformat()

    print("\n💭 Top comments (enter 3-5, press Enter twice when done):")
    top_comments = []
    while True:
        comment = input(f"   Comment {len(top_comments)+1}: ").strip()
        if not comment:
            break
        top_comments.append(comment)

    return {
        'video_id': video_id,
        'url': url,
        'author': author,
        'caption': caption,
        'hashtags': hashtags,
        'likes': likes,
        'comments': comments,
        'shares': shares,
        'views': views,
        'created_at': created_at,
        'top_comments': str(top_comments)
    }

def main():
    print_instructions()

    data_dir = Path(__file__).parent / "data" / "raw"
    output_file = data_dir / "tiktok_manual.csv"

    # Check if file exists
    videos = []
    if output_file.exists():
        print(f"\n✓ Found existing data file with entries")
        response = input("Continue adding to existing file? (y/n): ").strip().lower()
        if response == 'y':
            with open(output_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                videos = list(reader)
            print(f"✓ Loaded {len(videos)} existing videos")

    print("\n" + "="*70)
    print("Start entering video data")
    print("="*70)
    print("TIP: Open TikTok in one window, this script in another")
    print()

    count = len(videos)
    while True:
        video = collect_video()
        if video is None:
            break

        videos.append(video)
        count += 1
        print(f"\n✅ Saved video {count}")

        if count % 10 == 0:
            print(f"\n🎉 Great progress! {count} videos collected")
            print(f"   Recommended: 50-100 total for good analysis")

        another = input("\nAdd another video? (y/n): ").strip().lower()
        if another != 'y':
            break

    # Save data
    if videos:
        fieldnames = [
            'video_id', 'url', 'author', 'caption', 'hashtags',
            'likes', 'comments', 'shares', 'views', 'created_at', 'top_comments'
        ]

        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(videos)

        print("\n" + "="*70)
        print(f"✅ Saved {len(videos)} videos to: {output_file}")
        print("="*70)
        print()
        print("Next steps:")
        print("1. Collect Instagram data: python collect_instagram.py")
        print("2. Run analysis: python src/main.py")
        print()
    else:
        print("\n⚠️  No data collected")

    # Progress report
    if len(videos) >= 50:
        print("🎉 Excellent! 50+ videos is enough for robust analysis")
    elif len(videos) >= 25:
        print("👍 Good! 25+ videos will give decent results")
    elif len(videos) >= 10:
        print("📊 Minimum viable! 10+ videos will work, but more is better")
    else:
        print("💡 Tip: Aim for at least 25 videos for meaningful analysis")

if __name__ == "__main__":
    main()
