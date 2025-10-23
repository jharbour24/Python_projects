#!/usr/bin/env python3
"""
SEC EDGAR Configuration Setup
SEC requires User-Agent with real contact information
Run this once to configure your credentials
"""

import json
from pathlib import Path

def setup_sec_credentials():
    """Interactive setup for SEC EDGAR access credentials"""

    print("=" * 70)
    print("SEC EDGAR ACCESS CONFIGURATION")
    print("=" * 70)
    print()
    print("SEC requires you to identify yourself when accessing EDGAR data.")
    print("This is for compliance and fair access monitoring.")
    print()
    print("Required information:")
    print("  1. Your name or organization name")
    print("  2. Your email address")
    print()
    print("Example: 'John Doe jdoe@university.edu'")
    print("Example: 'Broadway Research team@broadwayresearch.org'")
    print()

    # Get user input
    name = input("Enter your name or organization: ").strip()
    email = input("Enter your email address: ").strip()

    if not name or not email:
        print("\n❌ Error: Name and email are required")
        return False

    # Create User-Agent string
    user_agent = f"{name} {email}"

    # Save to config file
    config_dir = Path(__file__).parent.parent / '.config'
    config_dir.mkdir(exist_ok=True)

    config_file = config_dir / 'sec_credentials.json'

    config = {
        'user_agent': user_agent,
        'name': name,
        'email': email
    }

    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

    print()
    print("=" * 70)
    print("✓ Configuration saved!")
    print("=" * 70)
    print(f"User-Agent: {user_agent}")
    print(f"Config file: {config_file}")
    print()
    print("You can now run:")
    print("  python3 scripts/run_full_analysis.py --bulk")
    print()

    return True


def load_sec_credentials():
    """Load SEC credentials from config file"""
    config_file = Path(__file__).parent.parent / '.config' / 'sec_credentials.json'

    if config_file.exists():
        with open(config_file, 'r') as f:
            config = json.load(f)
            return config.get('user_agent')

    return None


def get_user_agent():
    """Get User-Agent string, prompting for setup if needed"""
    user_agent = load_sec_credentials()

    if not user_agent:
        print("\n⚠️  SEC EDGAR credentials not configured")
        print("Running setup...\n")

        if setup_sec_credentials():
            user_agent = load_sec_credentials()
        else:
            raise ValueError("SEC credentials setup failed")

    return user_agent


if __name__ == "__main__":
    print()
    setup_sec_credentials()
