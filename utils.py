#!/usr/bin/env python3
"""
Utility functions for Broadway producer scraping project.
Includes logging, rate limiting, and HTTP helpers.
"""

import logging
import sys
import time
from pathlib import Path
from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def setup_logger(name: str, log_file: Optional[str] = None, level=logging.INFO) -> logging.Logger:
    """
    Set up a logger with console and optional file output.

    Args:
        name: Logger name
        log_file: Optional log file path
        level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers = []  # Clear existing handlers

    # Console handler with detailed format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(console_format)
        logger.addHandler(file_handler)

    return logger


def get_robust_session(max_retries: int = 3, backoff_factor: float = 0.3) -> requests.Session:
    """
    Create a requests session with retry logic and proper headers.

    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Backoff factor for retries

    Returns:
        Configured requests Session
    """
    session = requests.Session()

    # Set up retry strategy
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Set reasonable headers to appear as a regular browser
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    })

    return session


class RateLimiter:
    """Simple rate limiter to ensure polite scraping."""

    def __init__(self, min_delay: float = 2.0, max_delay: float = 5.0):
        """
        Initialize rate limiter.

        Args:
            min_delay: Minimum delay between requests in seconds
            max_delay: Maximum delay between requests in seconds
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request_time = 0
        self.request_count = 0

    def wait(self):
        """Wait appropriate amount of time before next request."""
        current_time = time.time()
        elapsed = current_time - self.last_request_time

        # Use min_delay for first few requests, then increase slightly
        if self.request_count < 10:
            required_delay = self.min_delay
        else:
            # Gradually increase delay for longer scraping sessions
            required_delay = min(self.min_delay + (self.request_count // 50) * 0.5, self.max_delay)

        if elapsed < required_delay:
            sleep_time = required_delay - elapsed
            time.sleep(sleep_time)

        self.last_request_time = time.time()
        self.request_count += 1


def safe_get(url: str, session: requests.Session, logger: logging.Logger,
             timeout: int = 30) -> Optional[requests.Response]:
    """
    Safely fetch a URL with error handling and logging.

    Args:
        url: URL to fetch
        session: Requests session to use
        logger: Logger for output
        timeout: Request timeout in seconds

    Returns:
        Response object if successful, None otherwise
    """
    try:
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
        return response
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"URL not found (404): {url}")
        elif e.response.status_code == 403:
            logger.error(f"Access forbidden (403): {url} - May be blocked")
        else:
            logger.error(f"HTTP error {e.response.status_code}: {url}")
        return None
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching: {url}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error fetching {url}: {e}")
        return None


def normalize_show_title(title: str) -> str:
    """
    Normalize a show title for comparison and matching.

    Args:
        title: Show title to normalize

    Returns:
        Normalized title (lowercase, stripped, standardized punctuation)
    """
    import re

    # Convert to lowercase and strip
    normalized = title.lower().strip()

    # Standardize whitespace
    normalized = re.sub(r'\s+', ' ', normalized)

    # Remove common subtitle patterns for matching purposes
    # But keep the full title for display

    return normalized


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a string for use as a filename.

    Args:
        filename: String to sanitize

    Returns:
        Safe filename string
    """
    import re

    # Replace problematic characters
    safe = re.sub(r'[<>:"/\\|?*]', '_', filename)

    # Replace multiple underscores with single
    safe = re.sub(r'_+', '_', safe)

    # Limit length
    if len(safe) > 200:
        safe = safe[:200]

    return safe.strip('_')
