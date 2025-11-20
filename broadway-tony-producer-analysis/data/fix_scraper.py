#!/usr/bin/env python3
"""Quick fix for scrape_producers_from_grosses.py column detection"""

import re

# Read the file
with open('scrape_producers_from_grosses.py', 'r') as f:
    content = f.read()

# Find and replace the problematic section
old_pattern = r"# Get unique shows\s+if 'title' in grosses_df\.columns:\s+title_col = 'title'\s+elif 'show_name' in grosses_df\.columns:\s+title_col = 'show_name'\s+else:\s+logger\.error\(f\"No title column found\. Columns: \{grosses_df\.columns\.tolist\(\)\}\"\)\s+return \[\]"

new_code = """# Get unique shows - check for different column names
    possible_title_cols = ['title', 'show_title', 'show_name', 'show']
    title_col = None

    for col in possible_title_cols:
        if col in grosses_df.columns:
            title_col = col
            break

    if title_col is None:
        logger.error(f"No title column found. Columns: {grosses_df.columns.tolist()}")
        return []

    logger.info(f"Using column: {title_col}")"""

# If the pattern is found, replace it
if re.search(old_pattern, content, re.DOTALL):
    content = re.sub(old_pattern, new_code, content, flags=re.DOTALL)
    print("✓ Fixed old column detection code")
else:
    # Try simpler pattern - just look for the section after "Loaded X weekly records"
    pattern2 = r"(logger\.info\(f\"Loaded \{len\(grosses_df\)\} weekly records\"\)\s+)([\s\S]+?)(unique_shows = grosses_df\[title_col\]\.unique\(\))"

    replacement = r"\1\n    # Get unique shows - check for different column names\n    possible_title_cols = ['title', 'show_title', 'show_name', 'show']\n    title_col = None\n\n    for col in possible_title_cols:\n        if col in grosses_df.columns:\n            title_col = col\n            break\n\n    if title_col is None:\n        logger.error(f\"No title column found. Columns: {grosses_df.columns.tolist()}\")\n        return []\n\n    logger.info(f\"Using column: {title_col}\")\n\n    \3"

    if re.search(pattern2, content):
        content = re.sub(pattern2, replacement, content)
        print("✓ Fixed column detection")
    else:
        print("✗ Could not find section to fix - file may already be correct")
        print("Checking if 'possible_title_cols' exists...")
        if 'possible_title_cols' in content:
            print("✓ File already has the fix!")
        else:
            print("✗ Cannot auto-fix, manual edit needed")
            exit(1)

# Write back
with open('scrape_producers_from_grosses.py', 'w') as f:
    f.write(content)

print("✓ File updated successfully!")
print("\nRun: python3 scrape_producers_from_grosses.py")
