#!/usr/bin/env python3
"""
Network utilities for ethical web scraping.

Handles:
- robots.txt compliance
- Rate limiting with randomized delays
- Exponential backoff on errors
- Custom user-agent identification
"""

import time
import random
import logging
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from dataclasses import dataclass
from enum import Enum

import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Taxonomy of web scraping errors for monitoring."""
    ROBOTS_BLOCKED = "robots_blocked"
    RATE_LIMITED = "rate_limited"
    SERVER_ERROR = "server_error"
    CLIENT_ERROR = "client_error"
    TIMEOUT = "timeout"
    NETWORK = "network"
    PARSE_ERROR = "parse_error"
    UNKNOWN = "unknown"


@dataclass
class FetchResult:
    """Result of a fetch operation with metadata."""
    response: Optional[requests.Response]
    success: bool
    error_category: Optional[ErrorCategory]
    error_message: Optional[str]
    attempts: int
    total_wait_time: float


# Custom user agent identifying this research project
USER_AGENT = (
    "BroadwayMarketingResearch/1.0 "
    "(+https://github.com/research/broadway-analysis; academic research)"
)

# Cache for robots.txt parsers
_robots_cache: Dict[str, RobotFileParser] = {}


def respect_robots(url: str, user_agent: str = USER_AGENT) -> bool:
    """
    Check if URL is allowed by robots.txt.

    Args:
        url: URL to check
        user_agent: User agent string

    Returns:
        True if allowed, False if disallowed

    Example:
        >>> respect_robots("https://www.tiktok.com/@example")
        True
    """
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    robots_url = f"{base_url}/robots.txt"

    # Check cache
    if base_url in _robots_cache:
        rp = _robots_cache[base_url]
    else:
        # Fetch and parse robots.txt
        rp = RobotFileParser()
        rp.set_url(robots_url)

        try:
            rp.read()
            _robots_cache[base_url] = rp
            logger.debug(f"Loaded robots.txt from {robots_url}")
        except Exception as e:
            logger.warning(f"Could not fetch robots.txt from {robots_url}: {e}")
            # If we can't fetch robots.txt, assume allowed but log
            return True

    # Check if path is allowed
    can_fetch = rp.can_fetch(user_agent, url)

    if not can_fetch:
        logger.warning(f"URL blocked by robots.txt: {url}")

    return can_fetch


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=2, max=16),
    retry=retry_if_exception_type((requests.exceptions.HTTPError, requests.exceptions.Timeout)),
    reraise=True
)
def fetch(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
    sleep_range: tuple = (2, 5),
    check_robots: bool = True,
    method: str = "GET",
    **kwargs
) -> requests.Response:
    """
    Fetch URL with ethical safeguards.

    Features:
    - Checks robots.txt before fetching (configurable)
    - Adds custom user-agent
    - Random sleep between requests
    - Automatic retry with exponential backoff on 429/5xx

    Args:
        url: URL to fetch
        headers: Additional headers (user-agent added automatically)
        params: Query parameters
        timeout: Request timeout in seconds
        sleep_range: (min, max) seconds to sleep before request
        check_robots: Whether to check robots.txt
        method: HTTP method (GET, POST)
        **kwargs: Additional arguments passed to requests.request()

    Returns:
        Response object

    Raises:
        ValueError: If URL blocked by robots.txt
        requests.HTTPError: If response status indicates error
        requests.Timeout: If request times out

    Example:
        >>> response = fetch("https://example.com/api")
        >>> data = response.json()
    """
    # Check robots.txt
    if check_robots and not respect_robots(url):
        raise ValueError(f"URL blocked by robots.txt: {url}")

    # Sleep before request (randomized rate limiting)
    sleep_time = random.uniform(*sleep_range)
    logger.debug(f"Sleeping {sleep_time:.2f}s before request")
    time.sleep(sleep_time)

    # Prepare headers
    if headers is None:
        headers = {}

    if 'User-Agent' not in headers:
        headers['User-Agent'] = USER_AGENT

    # Make request
    logger.info(f"{method} {url}")

    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            timeout=timeout,
            **kwargs
        )

        # Raise for 4xx/5xx
        response.raise_for_status()

        logger.debug(f"Success: {response.status_code}")
        return response

    except requests.exceptions.HTTPError as e:
        # Log but let retry decorator handle it
        logger.warning(f"HTTP error {e.response.status_code}: {url}")

        # 429 Too Many Requests - let it retry
        if e.response.status_code == 429:
            logger.info("Rate limited (429), will retry with backoff")
            raise

        # 5xx Server errors - let it retry
        if 500 <= e.response.status_code < 600:
            logger.info(f"Server error {e.response.status_code}, will retry")
            raise

        # 4xx Client errors (except 429) - don't retry
        logger.error(f"Client error {e.response.status_code}, not retrying")
        raise

    except requests.exceptions.Timeout:
        logger.warning(f"Request timeout: {url}")
        raise


def fetch_safe(
    url: str,
    **kwargs
) -> Optional[requests.Response]:
    """
    Fetch with error handling that returns None on failure.

    Useful for optional data sources where failures should not stop the pipeline.

    Args:
        url: URL to fetch
        **kwargs: Arguments passed to fetch()

    Returns:
        Response object or None if fetch failed

    Example:
        >>> response = fetch_safe("https://example.com/optional")
        >>> if response:
        ...     data = response.json()
    """
    try:
        return fetch(url, **kwargs)
    except Exception as e:
        logger.error(f"Fetch failed (suppressed): {url} - {e}")
        return None


def fetch_with_metadata(
    url: str,
    max_retries: int = 4,
    **kwargs
) -> FetchResult:
    """
    Fetch with detailed metadata about attempts and errors.

    Args:
        url: URL to fetch
        max_retries: Maximum retry attempts
        **kwargs: Arguments passed to fetch()

    Returns:
        FetchResult with response and metadata

    Example:
        >>> result = fetch_with_metadata("https://example.com/api")
        >>> if result.success:
        ...     data = result.response.json()
        ... else:
        ...     print(f"Failed: {result.error_category}")
    """
    start_time = time.time()
    attempts = 0
    last_error = None
    error_category = None

    for attempt in range(max_retries):
        attempts += 1
        try:
            response = fetch(url, **kwargs)
            total_time = time.time() - start_time

            return FetchResult(
                response=response,
                success=True,
                error_category=None,
                error_message=None,
                attempts=attempts,
                total_wait_time=total_time
            )

        except ValueError as e:
            # robots.txt blocked
            if "robots.txt" in str(e):
                error_category = ErrorCategory.ROBOTS_BLOCKED
                last_error = str(e)
                break  # Don't retry

        except requests.exceptions.HTTPError as e:
            last_error = str(e)
            if e.response.status_code == 429:
                error_category = ErrorCategory.RATE_LIMITED
            elif 500 <= e.response.status_code < 600:
                error_category = ErrorCategory.SERVER_ERROR
            else:
                error_category = ErrorCategory.CLIENT_ERROR
                break  # Don't retry client errors

        except requests.exceptions.Timeout as e:
            error_category = ErrorCategory.TIMEOUT
            last_error = str(e)

        except requests.exceptions.RequestException as e:
            error_category = ErrorCategory.NETWORK
            last_error = str(e)

        except Exception as e:
            error_category = ErrorCategory.UNKNOWN
            last_error = str(e)
            break  # Don't retry unknown errors

        # Wait before retry (except on last attempt)
        if attempt < max_retries - 1:
            wait_time = 2 ** (attempt + 1)  # Exponential backoff
            logger.info(f"Retry {attempt + 1}/{max_retries} after {wait_time}s")
            time.sleep(wait_time)

    # All attempts failed
    total_time = time.time() - start_time

    return FetchResult(
        response=None,
        success=False,
        error_category=error_category or ErrorCategory.UNKNOWN,
        error_message=last_error,
        attempts=attempts,
        total_wait_time=total_time
    )
