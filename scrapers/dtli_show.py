"""
Scrape individual show pages from didtheylikeit.com.

For each show in the DB with a dtli_slug but no review data:
  1. Fetch /shows/{slug}/
  2. Parse: title, opening date, theater, venue type (broadway/off-broadway)
  3. Parse each review: critic, publication, sentiment, date, excerpt
  4. Filter to Broadway only (configurable)
  5. Upsert shows, publications, critics, reviews
  6. Compute is_opening_window / days_from_opening for each review

Sentiment detection: looks for img classes BigThumbs_UP, BigThumbs_MEH, BigThumbs_DOWN
"""
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from typing import Optional

from bs4 import BeautifulSoup, Tag

from config import MAX_WORKERS, OPENING_WINDOW_DAYS
from db import get_connection, upsert_critic, upsert_publication
from scrapers.base import BaseScraper
from utils import normalize_name, normalize_title

# Sentiment: img.image-2 has alt="BigThumbs_UP" / "BigThumbs_MEH" / "BigThumbs_DOWN"
ALT_SENTIMENT_MAP = {
    "bigthumbs_up": "up",
    "bigthumbs_meh": "meh",
    "bigthumbs_down": "down",
}

# These body classes indicate Off-Broadway — skip if broadway_only=True
OFF_BROADWAY_BODY_CLASSES = {"category-off-broadway", "term-off-broadway", "show_cat-off-broadway"}

DATE_FMTS = ["%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y", "%Y-%m-%d", "%m/%d/%Y"]


class DTLIShowScraper(BaseScraper):
    source = "dtli_show"

    def run(
        self,
        broadway_only: bool = True,
        limit: Optional[int] = None,
        slug: Optional[str] = None,
    ) -> dict:
        self.start_run()

        if slug:
            slugs = [(slug,)]
        else:
            with self._conn() as conn:
                slugs = conn.execute(
                    """SELECT dtli_slug FROM shows
                       WHERE dtli_slug IS NOT NULL
                         AND source_dtli = 1
                       ORDER BY updated_at DESC"""
                ).fetchall()

        if limit:
            slugs = slugs[:limit]

        self.logger.info(f"Processing {len(slugs)} shows (broadway_only={broadway_only})")

        added = updated = skipped = errors = 0

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {
                pool.submit(self._process_show, row[0], broadway_only): row[0]
                for row in slugs
            }
            for i, future in enumerate(as_completed(futures), 1):
                slug_done = futures[future]
                try:
                    result = future.result()
                    if result == "added":
                        added += 1
                    elif result == "updated":
                        updated += 1
                    elif result == "skipped":
                        skipped += 1
                except Exception as e:
                    self.logger.error(f"Unhandled error on slug={slug_done}: {e}")
                    errors += 1

                if i % 50 == 0:
                    self.logger.info(f"  {i}/{len(slugs)} shows processed")

        self.logger.info(
            f"Done: {added} added, {updated} updated, {skipped} skipped, {errors} errors"
        )
        self.finish_run(added, updated, errors)
        return {"added": added, "updated": updated, "skipped": skipped, "errors": errors}

    # ── Per-show processing ───────────────────────────────────────────────────

    def _process_show(self, slug: str, broadway_only: bool) -> str:
        url = f"https://didtheylikeit.com/shows/{slug}/"
        html = self.fetch(url)
        if not html:
            return "error"

        soup = BeautifulSoup(html, "lxml")

        venue_type = self._detect_venue_type(soup)
        if broadway_only and venue_type == "off-broadway":
            return "skipped"

        meta = self._parse_show_meta(soup)
        reviews = self._parse_reviews(soup)

        if not meta.get("title") and not reviews:
            self.logger.warning(f"Nothing parseable at slug={slug}")
            return "skipped"

        with self._conn() as conn:
            show_id = self._upsert_show_full(conn, slug, meta, venue_type)
            opening_date = meta.get("opening_date")
            for rev in reviews:
                self._upsert_review(conn, show_id, opening_date, rev)
            conn.commit()

        return "added"

    # ── Parsing ───────────────────────────────────────────────────────────────

    def _detect_venue_type(self, soup: BeautifulSoup) -> str:
        """Detect Broadway vs Off-Broadway from body classes, breadcrumbs, or meta."""
        body = soup.find("body")
        if body:
            body_classes = set(body.get("class", []))
            if body_classes & OFF_BROADWAY_BODY_CLASSES:
                return "off-broadway"
            if any("broadway" in c and "off" not in c for c in body_classes):
                return "broadway"

        # Check <link rel="canonical"> or meta description for clues
        canonical = soup.find("link", rel="canonical")
        if canonical:
            href = canonical.get("href", "")
            if "/off-broadway/" in href:
                return "off-broadway"
            if "/broadway/" in href:
                return "broadway"

        # Check for breadcrumb nav
        breadcrumbs = soup.find_all(["nav", "div"], class_=re.compile(r"breadcrumb", re.I))
        for bc in breadcrumbs:
            text = bc.get_text().lower()
            if "off-broadway" in text:
                return "off-broadway"
            if "broadway" in text:
                return "broadway"

        # Check any visible text containing "Broadway" near the top of page
        for el in soup.find_all(["h1", "h2", "h3", "p", "span", "div"])[:30]:
            text = el.get_text().lower()
            if "off-broadway" in text or "off broadway" in text:
                return "off-broadway"
            if "broadway" in text:
                return "broadway"

        return "unknown"

    def _parse_show_meta(self, soup: BeautifulSoup) -> dict:
        """
        Extract title, opening date, theater from page.
        Real HTML structure:
          <h1 class="hero-title">The Lost Boys</h1>
          <div class="section-review-featured-bottom-section">
            <p class="review-hero-info">
              Opening Night: <span class="review-hero-info-pink">April 26, 2026</span>
              Theater: <a ...>Palace Theatre</a>
        """
        meta = {}

        # Title from og:title (most reliable — strips "– Did They Like It?" suffix)
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            meta["title"] = _clean_title(og_title["content"])
        else:
            h1 = soup.find("h1", class_="hero-title") or soup.find("h1")
            if h1:
                meta["title"] = _clean_title(h1.get_text())

        # Opening date from span.review-hero-info-pink
        date_span = soup.find("span", class_="review-hero-info-pink")
        if date_span:
            meta["opening_date"] = _parse_date(date_span.get_text(strip=True))

        # Theater: first <a class="review-hero-info-link"> in the hero section
        hero_section = soup.find("div", class_="section-review-featured-bottom-section")
        if hero_section:
            theater_link = hero_section.find("a", class_="review-hero-info-link")
            if theater_link:
                meta["theater"] = theater_link.get_text(strip=True)

        return meta

    def _parse_reviews(self, soup: BeautifulSoup) -> list[dict]:
        """
        Real HTML structure per review:
          <div class="review-item">
            <div class="review-item-header">
              <img class="review-item-attribution" alt="NEW YORK TIMES" .../>
              <img class="image-2" alt="BigThumbs_UP" .../>
              <h2 class="review-item-critic-name"><a>Helen<br/>Shaw</a></h2>
            </div>
            <h3 class="review-item-date">April 26, 2026</h3>
            <p class="paragraph">Excerpt text...</p>
          </div>
        """
        reviews = []
        for item in soup.find_all("div", class_="review-item"):
            review = _extract_review_from_item(item)
            if review:
                reviews.append(review)
        return reviews

    # ── DB writes ─────────────────────────────────────────────────────────────

    def _upsert_show_full(
        self,
        conn: sqlite3.Connection,
        slug: str,
        meta: dict,
        venue_type: str,
    ) -> int:
        """Update the show row (already created by archive scraper) with full metadata."""
        title = meta.get("title") or slug.replace("-", " ").title()
        conn.execute(
            """UPDATE shows
               SET title=?, normalized_title=?, opening_date=?, theater=?,
                   updated_at=CURRENT_TIMESTAMP
               WHERE dtli_slug=?""",
            (
                title,
                normalize_title(title),
                meta.get("opening_date"),
                meta.get("theater"),
                slug,
            ),
        )
        # Add venue_type column if it doesn't exist (handled at schema level but safety check)
        row = conn.execute(
            "SELECT show_id FROM shows WHERE dtli_slug=?", (slug,)
        ).fetchone()
        if row:
            return row["show_id"]
        # Fallback: insert
        cur = conn.execute(
            """INSERT INTO shows(title, normalized_title, dtli_slug, opening_date,
                                 theater, source_dtli)
               VALUES(?,?,?,?,?,1)""",
            (title, normalize_title(title), slug, meta.get("opening_date"), meta.get("theater")),
        )
        return cur.lastrowid

    def _upsert_review(
        self,
        conn: sqlite3.Connection,
        show_id: int,
        opening_date: Optional[str],
        rev: dict,
    ) -> None:
        pub_id = upsert_publication(conn, rev["publication"])
        critic_id = upsert_critic(conn, rev["critic"], pub_id)

        days_from_opening = None
        is_opening_window = 0
        if opening_date and rev.get("review_date"):
            try:
                open_dt = date.fromisoformat(str(opening_date))
                rev_dt = date.fromisoformat(str(rev["review_date"]))
                days_from_opening = (rev_dt - open_dt).days
                is_opening_window = 1 if abs(days_from_opening) <= OPENING_WINDOW_DAYS else 0
            except (ValueError, TypeError):
                pass

        conn.execute(
            """INSERT OR IGNORE INTO reviews
               (show_id, critic_id, publication_id, sentiment, review_date,
                excerpt, is_opening_window, days_from_opening, source)
               VALUES(?,?,?,?,?,?,?,?,'dtli')""",
            (
                show_id,
                critic_id,
                pub_id,
                rev["sentiment"],
                rev.get("review_date"),
                rev.get("excerpt"),
                is_opening_window,
                days_from_opening,
            ),
        )

    def _conn(self) -> sqlite3.Connection:
        return get_connection(self.db_path)


# ── HTML parsing helpers ──────────────────────────────────────────────────────

def _extract_review_from_item(item: Tag) -> Optional[dict]:
    """
    Extract all fields from a <div class="review-item"> element.

    Structure:
      header > img.review-item-attribution (alt = publication name)
      header > img.image-2 (alt = BigThumbs_UP / BigThumbs_MEH / BigThumbs_DOWN)
      header > h2.review-item-critic-name > a (text = critic name, may have <br/>)
      h3.review-item-date (text = review date)
      p.paragraph (text = excerpt)
    """
    header = item.find("div", class_="review-item-header")
    if not header:
        return None

    # Publication: img.review-item-attribution (alt) OR div.review_image > div (text)
    pub_img = header.find("img", class_="review-item-attribution")
    if pub_img and pub_img.get("alt"):
        publication = pub_img["alt"].strip()
    else:
        pub_div = header.find("div", class_="review_image")
        inner = pub_div.find("div") if pub_div else None
        publication = inner.get_text(strip=True) if inner else "Unknown"

    # Sentiment: img.image-2 alt text → BigThumbs_UP / BigThumbs_MEH / BigThumbs_DOWN
    sentiment_img = header.find("img", class_="image-2")
    sentiment = None
    if sentiment_img:
        alt_norm = sentiment_img.get("alt", "").lower().replace("bigthumbs_", "")
        sentiment = {"up": "up", "meh": "meh", "down": "down"}.get(alt_norm)
    if sentiment is None:
        return None

    # Critic name: h2.review-item-critic-name a — collapse whitespace (br tags create newlines)
    critic_el = header.find("h2", class_="review-item-critic-name")
    critic = "Unknown"
    if critic_el:
        critic_link = critic_el.find("a")
        if critic_link:
            # Replace <br/> tags with space before extracting text
            for br in critic_link.find_all("br"):
                br.replace_with(" ")
            critic = re.sub(r"\s+", " ", critic_link.get_text()).strip()

    # Date: h3.review-item-date
    date_el = item.find("h3", class_="review-item-date")
    review_date = _parse_date(date_el.get_text(strip=True)) if date_el else None

    # Excerpt: p.paragraph
    excerpt_el = item.find("p", class_="paragraph")
    excerpt = excerpt_el.get_text(" ", strip=True)[:500] if excerpt_el else None

    if publication == "Unknown" and critic == "Unknown":
        return None

    return {
        "sentiment": sentiment,
        "publication": publication,
        "critic": critic,
        "review_date": review_date,
        "excerpt": excerpt,
    }


def _parse_date(s: str) -> Optional[str]:
    """Parse a date string into ISO format YYYY-MM-DD."""
    s = s.strip().replace(",", "")
    for fmt in DATE_FMTS:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _clean_title(title: str) -> str:
    """Strip review suffixes like ' – Did They Like It?' from og:title."""
    for suffix in [
        " – Did They Like It?", " - Did They Like It?",
        " Review", " Reviews", " review", " reviews",
    ]:
        if title.endswith(suffix):
            title = title[: -len(suffix)]
    return title.strip()
