"""Data storage utilities."""
import json
import csv
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


class DataStorage:
    """Handles storage of scraped data."""

    def __init__(self, base_path: str = None):
        """
        Initialize data storage.

        Args:
            base_path: Base directory for data storage
        """
        if base_path is None:
            self.base_path = Path(__file__).parent.parent.parent / "data"
        else:
            self.base_path = Path(base_path)

        self.raw_path = self.base_path / "raw"
        self.processed_path = self.base_path / "processed"

        # Create directories if they don't exist
        self.raw_path.mkdir(parents=True, exist_ok=True)
        self.processed_path.mkdir(parents=True, exist_ok=True)

    def save_raw_json(self, data: List[Dict], platform: str, timestamp: str = None):
        """
        Save raw data as JSON.

        Args:
            data: List of data dictionaries
            platform: Platform name (reddit, tiktok, instagram)
            timestamp: Optional timestamp string
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        filename = f"{platform}_raw_{timestamp}.json"
        filepath = self.raw_path / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"✓ Saved {len(data)} items to {filepath}")
        return filepath

    def save_processed_csv(self, df: pd.DataFrame, filename: str):
        """
        Save processed data as CSV.

        Args:
            df: DataFrame to save
            filename: Output filename
        """
        filepath = self.processed_path / filename
        df.to_csv(filepath, index=False, encoding='utf-8')
        print(f"✓ Saved processed data to {filepath}")
        return filepath

    def load_raw_json(self, platform: str, timestamp: str = None) -> List[Dict]:
        """
        Load raw JSON data.

        Args:
            platform: Platform name
            timestamp: Optional specific timestamp to load

        Returns:
            List of data dictionaries
        """
        if timestamp:
            filename = f"{platform}_raw_{timestamp}.json"
            filepath = self.raw_path / filename
        else:
            # Load most recent file
            files = list(self.raw_path.glob(f"{platform}_raw_*.json"))
            if not files:
                return []
            filepath = max(files, key=lambda p: p.stat().st_mtime)

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"✓ Loaded {len(data)} items from {filepath}")
        return data

    def save_assumption_log(self, log_entries: List[str]):
        """
        Save methodological assumptions and limitations.

        Args:
            log_entries: List of log entry strings
        """
        filepath = self.base_path.parent / "outputs" / "reports" / "assumption_log.md"

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# Assumption Log\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## Methodological Decisions and Limitations\n\n")

            for i, entry in enumerate(log_entries, 1):
                f.write(f"{i}. {entry}\n\n")

        print(f"✓ Saved assumption log to {filepath}")
        return filepath
