#!/usr/bin/env python3
"""
Reddit API Setup Helper
Guides you through creating Reddit API credentials and configuring the scraper.
"""

import os
import sys
from pathlib import Path

def main():
    print("="*70)
    print("Reddit API Setup for Oh Mary! CMM Analysis")
    print("="*70)
    print()

    print("📋 Step 1: Create Reddit App")
    print("-" * 70)
    print("1. Go to: https://www.reddit.com/prefs/apps")
    print("2. Scroll to bottom and click 'create another app'")
    print("3. Fill in:")
    print("   - Name: oh_mary_analysis")
    print("   - Type: Select 'script'")
    print("   - Description: (optional)")
    print("   - About URL: (leave blank)")
    print("   - Redirect URI: http://localhost:8080")
    print("4. Click 'create app'")
    print()
    print("5. You'll see your app with credentials:")
    print("   - CLIENT_ID: Under 'personal use script' (14 characters)")
    print("   - CLIENT_SECRET: Next to 'secret' (27 characters)")
    print()

    input("Press ENTER when you've created the app...")
    print()

    print("📋 Step 2: Enter Your Credentials")
    print("-" * 70)

    client_id = input("Enter CLIENT_ID (14 chars): ").strip()
    client_secret = input("Enter CLIENT_SECRET (27 chars): ").strip()
    username = input("Enter your Reddit username: ").strip()

    if not client_id or not client_secret or not username:
        print("\n❌ Error: All fields are required")
        sys.exit(1)

    print()
    print("📋 Step 3: Install PRAW")
    print("-" * 70)
    print("Installing Reddit API library...")

    os.system("pip install -q praw tqdm")

    print("✓ PRAW installed")
    print()

    print("📋 Step 4: Update Configuration")
    print("-" * 70)

    # Create credentials file
    config_path = Path(__file__).parent / "config" / "reddit_credentials.py"

    with open(config_path, 'w') as f:
        f.write(f"""# Reddit API Credentials
# DO NOT COMMIT THIS FILE TO GIT

REDDIT_CLIENT_ID = '{client_id}'
REDDIT_CLIENT_SECRET = '{client_secret}'
REDDIT_USER_AGENT = 'oh_mary_cmm_analysis:v1.0 (by /u/{username})'
""")

    print(f"✓ Credentials saved to: {config_path}")
    print()

    # Update .gitignore
    gitignore_path = Path(__file__).parent / ".gitignore"

    gitignore_content = """# Credentials
config/reddit_credentials.py

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so
*.egg
*.egg-info/
dist/
build/

# Data
data/raw/*.json
data/raw/*_manual.csv

# Virtual environment
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
"""

    with open(gitignore_path, 'w') as f:
        f.write(gitignore_content)

    print(f"✓ Updated .gitignore")
    print()

    print("📋 Step 5: Test Connection")
    print("-" * 70)
    print("Testing Reddit API connection...")
    print()

    # Test connection
    try:
        import praw

        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=f'oh_mary_cmm_analysis:v1.0 (by /u/{username})'
        )

        # Test with a simple request
        subreddit = reddit.subreddit('broadway')
        print(f"✓ Successfully connected to Reddit!")
        print(f"✓ Test: r/broadway has {subreddit.subscribers:,} subscribers")
        print()

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print()
        print("Please check your credentials and try again.")
        sys.exit(1)

    print("="*70)
    print("✅ SETUP COMPLETE!")
    print("="*70)
    print()
    print("You can now run the analysis:")
    print()
    print("  cd oh_mary_cmm_analysis")
    print("  python src/main.py")
    print()
    print("The scraper will automatically collect Reddit posts about Oh Mary!")
    print()
    print("⚠️  IMPORTANT: Never share your credentials or commit them to git")
    print()

if __name__ == "__main__":
    main()
