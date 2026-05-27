# Scrapers

Low-level scraping modules invoked by `pipeline/`. You probably don't need to touch these directly.

| Module | Source | What it scrapes |
|---|---|---|
| `dtli_archive.py` | didtheylikeit.com | Show titles + slugs from Broadway archive pages |
| `dtli_show.py` | didtheylikeit.com | Per-show critic reviews |
| `nyt_critics_pick.py` | NYT Article Search API | Theater reviews + CP flags (Broadway only) |
| `nyt_spotlight_scraper.py` | NYT spotlight + Wayback | CP URL list refresh |
| `grosses_refresh.py` | BroadwayWorld | Weekly grosses, capacity, attendance |
| `wikipedia_tony.py` | Wikipedia | Tony nominees + winners (supplemental) |
| `base.py` | — | Shared `BaseScraper` class (rate-limiting, retries, caching) |

## Design

All scrapers inherit from `BaseScraper` in `base.py`, which provides:
- Polite rate limiting (`config.RATE_LIMIT_MIN`/`MAX`)
- HTML caching to `data/raw_html/<scraper-name>/`
- Retry logic with exponential backoff
- A `run()` method that returns a result dict for the pipeline to log

## Adding a new source

```python
from scrapers.base import BaseScraper

class MyScraper(BaseScraper):
    name = "mysource"
    cache_dir = "mysource"

    def discover(self):
        """Return list of URLs to fetch."""
        ...

    def parse(self, html, url):
        """Return list of dicts to insert."""
        ...
```

Then create a `pipeline/0X_my_source.py` script that instantiates it.
