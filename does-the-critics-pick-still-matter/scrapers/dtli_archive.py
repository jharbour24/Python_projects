"""
Discover all DTLI Broadway show slugs via the XML sitemaps.

Strategy:
  1. Fetch sitemap.xml index → find all shows-sitemapN.xml entries
  2. Fetch each shows-sitemap XML → extract show URLs + lastmod
  3. Upsert into shows table with dtli_slug extracted from URL
  4. Broadway/Off-Broadway filtering happens in dtli_show.py during page parse
"""
import re
import sqlite3
from datetime import datetime
from typing import Iterator
from xml.etree import ElementTree as ET

from scrapers.base import BaseScraper

SITEMAP_INDEX = "https://didtheylikeit.com/sitemap.xml"
SHOWS_SITEMAP_PATTERN = re.compile(r"shows-sitemap\d+\.xml$")
SLUG_RE = re.compile(r"didtheylikeit\.com/shows/([^/]+)(?:/[^/]+)?/?$")


class DTLIArchiveScraper(BaseScraper):
    source = "dtli_archive"

    def run(self, force_refresh: bool = False) -> dict:
        self.start_run()
        self.logger.info("Fetching sitemap index...")

        sitemap_urls = list(self._discover_show_sitemaps())
        if not sitemap_urls:
            self.logger.error("No show sitemaps found — check sitemap.xml")
            self.finish_run(0, 0, 1, "No show sitemaps discovered")
            return {"added": 0, "updated": 0, "errors": 1}

        self.logger.info(f"Found {len(sitemap_urls)} show sitemaps")

        added = updated = errors = 0
        with self._conn() as conn:
            for sitemap_url in sitemap_urls:
                self.logger.info(f"  Processing: {sitemap_url}")
                for show_url, lastmod in self._parse_sitemap(sitemap_url):
                    slug = self._extract_slug(show_url)
                    if not slug or slug == "":
                        continue
                    result = self._upsert_show(conn, show_url, slug, lastmod)
                    if result == "added":
                        added += 1
                    elif result == "updated":
                        updated += 1
                    elif result == "error":
                        errors += 1
                conn.commit()

        self.logger.info(f"Archive discovery complete: {added} added, {updated} updated, {errors} errors")
        self.finish_run(added, updated, errors)
        return {"added": added, "updated": updated, "errors": errors}

    # ── Internal ─────────────────────────────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        from db import get_connection
        return get_connection(self.db_path)

    def _discover_show_sitemaps(self) -> Iterator[str]:
        html = self.fetch(SITEMAP_INDEX, force=self.force_refresh)
        if not html:
            return
        try:
            root = ET.fromstring(html)
        except ET.ParseError:
            self.logger.error("Could not parse sitemap.xml")
            return
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        for sitemap in root.findall("sm:sitemap", ns):
            loc = sitemap.findtext("sm:loc", namespaces=ns) or ""
            if SHOWS_SITEMAP_PATTERN.search(loc):
                yield loc.strip()

    def _parse_sitemap(self, url: str) -> Iterator[tuple[str, str | None]]:
        html = self.fetch(url, force=self.force_refresh)
        if not html:
            return
        try:
            root = ET.fromstring(html)
        except ET.ParseError:
            self.logger.error(f"Could not parse sitemap: {url}")
            return
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        for url_el in root.findall("sm:url", ns):
            loc = (url_el.findtext("sm:loc", namespaces=ns) or "").strip()
            lastmod = (url_el.findtext("sm:lastmod", namespaces=ns) or "").strip() or None
            if loc:
                yield loc, lastmod

    def _extract_slug(self, url: str) -> str | None:
        m = SLUG_RE.search(url)
        if m:
            return m.group(1)
        # Fallback: strip trailing slash, take last path segment
        parts = url.rstrip("/").split("/shows/")
        if len(parts) == 2:
            return parts[1].strip("/").split("/")[0]
        return None

    def _upsert_show(
        self,
        conn: sqlite3.Connection,
        show_url: str,
        slug: str,
        lastmod: str | None,
    ) -> str:
        try:
            existing = conn.execute(
                "SELECT show_id, updated_at FROM shows WHERE dtli_slug=?", (slug,)
            ).fetchone()

            if existing:
                # Update lastmod if newer
                if lastmod:
                    conn.execute(
                        "UPDATE shows SET updated_at=? WHERE dtli_slug=?",
                        (lastmod, slug),
                    )
                return "updated"
            else:
                # Placeholder title from slug — will be filled in by dtli_show scraper
                placeholder_title = slug.replace("-reviews", "").replace("-review", "").replace("-", " ").title()
                from utils import normalize_title
                conn.execute(
                    """INSERT INTO shows
                       (title, normalized_title, dtli_slug, source_dtli, updated_at)
                       VALUES (?,?,?,1,?)""",
                    (
                        placeholder_title,
                        normalize_title(placeholder_title),
                        slug,
                        lastmod or datetime.utcnow().isoformat(),
                    ),
                )
                return "added"
        except Exception as e:
            self.logger.warning(f"Upsert failed for slug={slug}: {e}")
            return "error"
