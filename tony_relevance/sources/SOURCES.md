# Data sources & provenance

Every row in `award_broadcasts`, `audience_demographics` and `tv_universe`
carries a `source_key` that maps to a URL below. These are **secondary
aggregators and trade-press reports** gathered via web search (June 2026).
Treat them as a v1 seed: before publishing any *specific* figure, validate
against primary Nielsen releases and the per-ceremony Wikipedia infoboxes.

A known measurement wrinkle: outlets report different bases for the *same*
ceremony — Live+Same-Day vs. final national vs. "across-platform" (linear +
streaming). Recent years are the worst affected. Rows are tagged `measurement`
(`linear` vs `xplat`) and `confidence` (`high`/`med`/`low`) accordingly.

| source_key | Outlet / dataset | URL |
|---|---|---|
| statista  | Statista award-show viewership series (Tonys, Oscars, Emmys, Grammys) | https://www.statista.com/statistics/307240/tony-awards-number-of-viewers/ ; https://www.statista.com/statistics/253743/academy-awards-number-of-viewers/ ; https://www.statista.com/statistics/260428/emmy-awards-number-of-viewers/ ; https://www.statista.com/statistics/466534/grammy-awards-number-viewers/ |
| nytix     | NYTIX "Tony Award Ratings Year by Year" | https://www.nytix.com/news/tony-award-ratings-year-by-year |
| variety   | Variety ratings desk | https://variety.com/2022/awards/ratings/tony-awards-ratings-tonys-2022-viewership-1235292423/ ; https://variety.com/2025/tv/ratings/tony-awards-2025-ratings-largest-audience-since-2019-1236423861/ |
| deadline  | Deadline ratings | https://deadline.com/2022/06/tony-awards-ratings-2022-cbs-paramount-plus-1235044339/ |
| thewrap   | TheWrap ratings | https://www.thewrap.com/tonys-2024-viewership-ratings-cbs/ ; https://www.thewrap.com/tony-awards-ratings-viewership-cbs/ |
| thr       | The Hollywood Reporter | https://www.hollywoodreporter.com/tv/tv-news/emmys-2024-tv-ratings-1236004078/ |
| imdb      | IMDb news (2025 Tony cross-platform) | https://www.imdb.com/news/ni65326134/ |
| cbsnews   | CBS News (2024 Oscars) | https://www.cbsnews.com/news/oscars-ratings-2024/ |
| axios     | Axios (2025 Emmys) | https://www.axios.com/2025/09/16/emmys-hit-four-year-viewership-high |
| chartdata | @chartdata compiled Grammy viewership 2010–2026 | https://x.com/chartdata/status/2019485198757322755 |
| adage     | Ad Age, award-show median viewer ages | https://adage.com/article/media/grammy-oscar-special-special/134298/ |
| approx    | Author estimate from Nielsen TV-HH counts & Statista pay-TV penetration | https://www.statista.com/statistics/495693/cord-cut-penetration-usa/ ; https://www.tvb.org/wp-content/uploads/2022/10/National-TV-Household-Penetration-Trends.pdf |
| pending   | Placeholder for the 2026 (79th) Tony Nielsen figure, unreleased as of 2026-06-08 | (update on publication: Deadline / Variety / TheWrap ratings desks) |
| showbuzz  | Showbuzz Daily / Statista — SAG Awards historical linear ratings | https://www.statista.com/statistics/568316/sag-awards-number-of-viewers/ ; https://showbuzzdaily.com/tag/sag-awards-ratings |
| broadwayworld | BroadwayWorld / Broadway.com / Playbill — 79th (2026) Tony ratings | https://www.broadwayworld.com/article/79th-Tony-Awards-Viewership-Dips-Slightly-From-2025-Drawing-506-Million-Viewers-20260611 ; https://www.broadway.com/buzz/207320/the-79th-annual-tony-awards-telecast-hosted-by-pnk-draws-506-million-viewers/ ; https://playbill.com/article/ratings-tony-awards-2026-was-number-1-program-june-7 |

**2026 (79th) Tonys — measurement note.** 5.06M = CBS **linear** home viewers
(preliminary), the best Tony broadcast since 2019 and +4% vs 2025 linear (4.85M);
CBS cites +44% vs 2024 (3.53M) and +23% vs 2023 (4.12M). Outlets framed it a
"slight dip" only by comparing this linear figure to 2025's 5.10M **across-
platform** number — not comparable. Paramount+ add not yet released. See
`VERIFICATION.md` §A and `outputs/NIELSEN_2026.md`.

**SAG Awards (Phase-2 case study) sources.** Linear era: Statista/Showbuzz Daily
plus Variety (2021 record low: https://variety.com/2021/tv/news/sag-awards-2021-ratings-tnt-tbs-1234944724/)
and Deadline (2022, last TNT/TBS). Streaming era: Variety (2023 YouTube bridge:
https://variety.com/2023/awards/news/sag-awards-2023-ratings-views-netflix-youtube-1235536922/),
Deadline (2024 Netflix "on par," sub-Top-10:
https://deadline.com/2024/09/sag-awards-netflix-2024-viewership-tnt-tbs-1236094869/),
TheWrap (2025 2.6M weekly views, No. 7:
https://www.thewrap.com/sag-awards-netflix-viewership/). **Reminder:** linear
Nielsen "viewers" and Netflix "views" are different units — see
`outputs/SAG_NETFLIX_CASE.md` §2.

**2025 (78th) Tonys — corrected reading.** 4.85M = CBS Live+Same-Day **linear**
(most-watched since 2019, +38% YoY); 5.10M = **across platforms** incl.
Paramount+ (streaming +208% YoY). Sources: TheWrap (https://www.thewrap.com/tonys-2025-ratings-viewership-cbs-paramount-plus/),
Deadline (https://deadline.com/2025/06/tony-award-ratings-2025-1236428454/),
Playbill, Broadway.com (2025-06-09). See `VERIFICATION.md` §A.

## Primary sources to validate against (recommended before publication)
- Wikipedia "List of Tony Awards ceremonies" and per-ceremony articles
  (e.g. "75th Tony Awards") — viewership infobox fields.
- Nielsen press releases / Nielsen "most-watched" insights posts.
- The Numbers / ShowBuzzDaily archives for Live+Same-Day national numbers.

## Free, reproducible sources for the unbuilt attention layer
- **Wikimedia Pageviews API** (no key): `https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/all-agents/{ARTICLE}/daily/{START}/{END}`
- **Google Trends**: trends.google.com comparative query, or the `pytrends` library.
