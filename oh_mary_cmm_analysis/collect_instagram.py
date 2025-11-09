#!/usr/bin/env python3
"""
Instagram Manual Collection Helper
Browser-based collection WITHOUT requiring login.
"""

import csv
from datetime import datetime
from pathlib import Path

def print_instructions():
    print("="*70)
    print("Instagram Manual Collection Guide")
    print("="*70)
    print()
    print("📱 SAFE METHOD: No login required, uses public profiles/tags")
    print()
    print("Step-by-Step Instructions:")
    print("-" * 70)
    print()
    print("1. Open Instagram in your browser (instagram.com)")
    print("   - You DON'T need to log in (some content visible without login)")
    print("   - Use incognito/private mode")
    print()
    print("2. Search for Oh Mary content:")
    print("   - Visit: instagram.com/explore/tags/ohmary/")
    print("   - Visit: instagram.com/explore/tags/ohmarybroadway/")
    print("   - Visit: instagram.com/explore/locations/... (Lyceum Theatre)")
    print()
    print("   ALTERNATIVE if login required:")
    print("   - Use Picuki.com (Instagram viewer without login)")
    print("   - Search: #OhMary or @colewschooler")
    print()
    print("3. For each post (aim for 50-100 posts):")
    print("   - Click post to open")
    print("   - Copy the URL")
    print("   - Note: author, caption, hashtags, likes")
    print("   - Read 3-5 top comments")
    print()
    print("4. Use this interactive form to record data:")
    print()

def collect_post():
    """Collect single post data interactively."""
    print("\n" + "="*70)
    print("Enter Post Data (or 'done' to finish)")
    print("="*70)

    url = input("\n📎 Post URL: ").strip()
    if url.lower() == 'done':
        return None

    # Auto-extract post ID from URL
    post_id = url.split('/p/')[-1].split('/')[0] if '/p/' in url else url

    author = input("👤 Author (@username): ").strip()
    caption = input("📝 Caption: ").strip()
    hashtags = input("🏷️  Hashtags (comma-separated): ").strip()

    try:
        likes = int(input("❤️  Likes: ").strip() or 0)
    except:
        likes = 0

    try:
        comments_count = int(input("💬 Comments count: ").strip() or 0)
    except:
        comments_count = 0

    created_at = input("📅 Date (YYYY-MM-DD) or leave blank: ").strip()
    if not created_at:
        created_at = datetime.now().isoformat()

    post_type = input("📷 Post type (photo/video/carousel) [photo]: ").strip() or "photo"

    print("\n💭 Top comments (enter 3-5, press Enter twice when done):")
    top_comments = []
    while True:
        comment = input(f"   Comment {len(top_comments)+1}: ").strip()
        if not comment:
            break
        top_comments.append(comment)

    return {
        'post_id': post_id,
        'url': url,
        'author': author,
        'caption': caption,
        'hashtags': hashtags,
        'likes': likes,
        'comments_count': comments_count,
        'created_at': created_at,
        'post_type': post_type,
        'top_comments': str(top_comments)
    }

def main():
    print_instructions()

    data_dir = Path(__file__).parent / "data" / "raw"
    output_file = data_dir / "instagram_manual.csv"

    # Check if file exists
    posts = []
    if output_file.exists():
        print(f"\n✓ Found existing data file")
        response = input("Continue adding to existing file? (y/n): ").strip().lower()
        if response == 'y':
            with open(output_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                posts = list(reader)
            print(f"✓ Loaded {len(posts)} existing posts")

    print("\n" + "="*70)
    print("Start entering post data")
    print("="*70)
    print("TIP: Open Instagram/Picuki in one window, this script in another")
    print()
    print("💡 ALTERNATIVE TOOLS:")
    print("   - Picuki.com (view Instagram without login)")
    print("   - Imginn.com (another Instagram viewer)")
    print("   - Inflact.com (Instagram web viewer)")
    print()

    count = len(posts)
    while True:
        post = collect_post()
        if post is None:
            break

        posts.append(post)
        count += 1
        print(f"\n✅ Saved post {count}")

        if count % 10 == 0:
            print(f"\n🎉 Great progress! {count} posts collected")
            print(f"   Recommended: 50-100 total for good analysis")

        another = input("\nAdd another post? (y/n): ").strip().lower()
        if another != 'y':
            break

    # Save data
    if posts:
        fieldnames = [
            'post_id', 'url', 'author', 'caption', 'hashtags',
            'likes', 'comments_count', 'created_at', 'post_type', 'top_comments'
        ]

        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(posts)

        print("\n" + "="*70)
        print(f"✅ Saved {len(posts)} posts to: {output_file}")
        print("="*70)
        print()
        print("Next steps:")
        print("1. If not done yet, setup Reddit: python setup_reddit.py")
        print("2. Run analysis: python src/main.py")
        print()
    else:
        print("\n⚠️  No data collected")

    # Progress report
    if len(posts) >= 50:
        print("🎉 Excellent! 50+ posts is enough for robust analysis")
    elif len(posts) >= 25:
        print("👍 Good! 25+ posts will give decent results")
    elif len(posts) >= 10:
        print("📊 Minimum viable! 10+ posts will work, but more is better")
    else:
        print("💡 Tip: Aim for at least 25 posts for meaningful analysis")

if __name__ == "__main__":
    main()
