#!/usr/bin/env python3
"""
HTML Snapshot Management for Audit and Debugging

Saves raw HTML responses to disk with rolling window to limit disk usage.
Enables post-mortem debugging when parsers fail.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
import hashlib
import json

logger = logging.getLogger(__name__)


class SnapshotManager:
    """Manages HTML snapshots with rolling window retention."""

    def __init__(
        self,
        base_dir: str = "public_signals/data/raw_snapshots",
        max_per_handle: int = 50
    ):
        """
        Initialize snapshot manager.

        Args:
            base_dir: Base directory for snapshots
            max_per_handle: Maximum snapshots to keep per handle
        """
        self.base_dir = Path(base_dir)
        self.max_per_handle = max_per_handle
        self.base_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Snapshot manager initialized: {self.base_dir}")

    def save_html_snapshot(
        self,
        html: str,
        source: str,
        handle: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[dict] = None
    ) -> Path:
        """
        Save HTML snapshot with metadata.

        Args:
            html: Raw HTML content
            source: Source name (e.g., 'tiktok', 'instagram')
            handle: Profile handle
            timestamp: Timestamp (default: now)
            metadata: Additional metadata dict

        Returns:
            Path to saved snapshot file

        Example:
            >>> manager = SnapshotManager()
            >>> manager.save_html_snapshot(
            ...     html="<html>...</html>",
            ...     source="tiktok",
            ...     handle="@hamiltonmusical",
            ...     metadata={"posts_found": 15}
            ... )
        """
        if timestamp is None:
            timestamp = datetime.now()

        # Create directory structure
        handle_dir = self.base_dir / source / handle.lstrip('@')
        handle_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        ts_str = timestamp.strftime("%Y%m%d_%H%M%S")
        html_file = handle_dir / f"{ts_str}.html"
        meta_file = handle_dir / f"{ts_str}.json"

        # Save HTML
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html)

        # Save metadata
        meta = {
            'timestamp': timestamp.isoformat(),
            'source': source,
            'handle': handle,
            'html_size_bytes': len(html.encode('utf-8')),
            'html_hash': hashlib.md5(html.encode('utf-8')).hexdigest()
        }

        if metadata:
            meta.update(metadata)

        with open(meta_file, 'w') as f:
            json.dump(meta, f, indent=2)

        logger.info(f"  💾 Snapshot saved: {html_file}")

        # Enforce rolling window
        self._cleanup_old_snapshots(handle_dir)

        return html_file

    def _cleanup_old_snapshots(self, handle_dir: Path):
        """
        Remove oldest snapshots to stay within max_per_handle limit.

        Args:
            handle_dir: Directory for specific handle
        """
        # Get all HTML files sorted by modification time
        html_files = sorted(
            handle_dir.glob("*.html"),
            key=lambda p: p.stat().st_mtime,
            reverse=True  # Newest first
        )

        # Remove oldest files beyond limit
        if len(html_files) > self.max_per_handle:
            files_to_remove = html_files[self.max_per_handle:]

            for html_file in files_to_remove:
                # Remove HTML and corresponding JSON
                meta_file = html_file.with_suffix('.json')

                html_file.unlink()
                if meta_file.exists():
                    meta_file.unlink()

            logger.debug(
                f"Cleaned up {len(files_to_remove)} old snapshots from {handle_dir.name}"
            )

    def get_latest_snapshot(
        self,
        source: str,
        handle: str
    ) -> Optional[tuple[str, dict]]:
        """
        Retrieve the most recent snapshot for a handle.

        Args:
            source: Source name
            handle: Profile handle

        Returns:
            Tuple of (html_content, metadata) or None if not found

        Example:
            >>> manager = SnapshotManager()
            >>> html, meta = manager.get_latest_snapshot("tiktok", "@hamilton")
            >>> if html:
            ...     print(f"Snapshot from {meta['timestamp']}")
        """
        handle_dir = self.base_dir / source / handle.lstrip('@')

        if not handle_dir.exists():
            return None

        # Find most recent HTML file
        html_files = sorted(
            handle_dir.glob("*.html"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        if not html_files:
            return None

        latest_html = html_files[0]
        latest_meta = latest_html.with_suffix('.json')

        # Load HTML
        with open(latest_html, 'r', encoding='utf-8') as f:
            html = f.read()

        # Load metadata
        metadata = {}
        if latest_meta.exists():
            with open(latest_meta, 'r') as f:
                metadata = json.load(f)

        return html, metadata

    def get_snapshot_count(self, source: str, handle: str) -> int:
        """
        Count snapshots for a handle.

        Args:
            source: Source name
            handle: Profile handle

        Returns:
            Number of snapshots
        """
        handle_dir = self.base_dir / source / handle.lstrip('@')

        if not handle_dir.exists():
            return 0

        return len(list(handle_dir.glob("*.html")))

    def list_handles(self, source: str) -> list[str]:
        """
        List all handles with snapshots for a source.

        Args:
            source: Source name

        Returns:
            List of handles
        """
        source_dir = self.base_dir / source

        if not source_dir.exists():
            return []

        return [d.name for d in source_dir.iterdir() if d.is_dir()]

    def get_summary(self) -> dict:
        """
        Get summary statistics for all snapshots.

        Returns:
            Dict with source -> handle -> count mapping

        Example:
            >>> manager = SnapshotManager()
            >>> summary = manager.get_summary()
            >>> print(summary)
            {'tiktok': {'hamiltonmusical': 15, 'ohmaryplay': 12}, ...}
        """
        summary = {}

        if not self.base_dir.exists():
            return summary

        for source_dir in self.base_dir.iterdir():
            if not source_dir.is_dir():
                continue

            source = source_dir.name
            summary[source] = {}

            for handle_dir in source_dir.iterdir():
                if not handle_dir.is_dir():
                    continue

                handle = handle_dir.name
                count = len(list(handle_dir.glob("*.html")))
                summary[source][handle] = count

        return summary


# Global instance
_snapshot_manager: Optional[SnapshotManager] = None


def get_snapshot_manager() -> SnapshotManager:
    """Get or create global snapshot manager instance."""
    global _snapshot_manager

    if _snapshot_manager is None:
        _snapshot_manager = SnapshotManager()

    return _snapshot_manager


def save_snapshot(
    html: str,
    source: str,
    handle: str,
    **kwargs
) -> Path:
    """
    Convenience function to save snapshot using global manager.

    Args:
        html: HTML content
        source: Source name
        handle: Profile handle
        **kwargs: Additional arguments passed to save_html_snapshot()

    Returns:
        Path to saved file
    """
    manager = get_snapshot_manager()
    return manager.save_html_snapshot(html, source, handle, **kwargs)
