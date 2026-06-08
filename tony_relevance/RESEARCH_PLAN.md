# Are the Tonys Still Culturally Relevant? — A Research Plan

*A data-scientist's plan for testing the cultural relevance of the Tony Awards,
built in the spirit of Evan Shapiro's media-economics work: lead with the
denominator, kill the lazy narrative, and never confuse a linear-TV story for a
culture story.*

---

## 0. TL;DR — what this project found, and how it changed the thesis

We started where most takes start: *"Tony ratings are cratering, so the Tonys
are dying."* The data only **half** supports that, and the half it kills is the
interesting half.

| Claim | Verdict from the data | Where |
|---|---|---|
| Tony linear viewership fell sharply (7.0M in 2014 → 3.51M 2024 trough, ~−50%) | **TRUE** — but it then rebounded +38% to 4.85M in 2025 (best since 2019), trimming the 2014→2025 decline to −31% | `01_relevance_trends` |
| The Tonys are collapsing *faster than other award shows* | **FALSE** — DiD differential trend +1.7%/yr, p=0.57; they're actually the *slowest*-declining of the big four | `02_causal_did` (Design A/B) |
| The Tonys' *share* of the award-show audience is shrinking | **FALSE** — small but holding; if anything it rose (7.4% in 2014 → 10.2% in 2025 as peers fell faster) | `01` (§3) |
| The Tonys are the *smallest and oldest* award show | **TRUE** — lowest absolute reach; median viewer age ~61 vs ~45–52 for peers | `01` (§1, §4) |
| A culture-saturating show (Hamilton) materially moves the broadcast | **TRUE** — +45% above trend in 2016, while peers stayed on-trend | `02` (Design C) |

**The reframed, defensible thesis:** *The Tonys' television decline is not a
theatre story — it's the linear-TV story, shared by every award show. The
Tony-specific relevance problem is structural, not cyclical: the smallest
footprint, the oldest and aging audience, and a dependence on rare
Hamilton-scale cultural events that Broadway's economics no longer reliably
produce. The real question — "is theatre still in the cultural conversation?" —
cannot be answered on a Nielsen chart at all. It has to be answered* ***off***
*television.* That is the project's central, Shapiro-style move.

---

## 1. The hard part: "relevance" is a latent variable

There is no `relevance` column in any database. "Cultural relevance" is a
**latent construct** we can only triangulate through observable proxies. A
data scientist's first job is to refuse the single-number trap (Nielsen ratings)
and instead assemble a *measurement model* — several noisy indicators, each
capturing a different facet of relevance, with their disagreements treated as
information.

**Facets of relevance and their proxies:**

| Facet of "relevance" | Observable proxy | In this DB? |
|---|---|---|
| Broadcast reach | Nielsen linear viewers per ceremony | ✅ `award_broadcasts` |
| Reach vs. the TV universe | viewers ÷ US TV households | ✅ `tv_universe` |
| Share of cultural attention | share of big-four award-show audience | ✅ derived |
| Generational grip | median viewer age, % 18–34 | ◑ `audience_demographics` (sparse) |
| Off-TV curiosity | Google Trends interest around the ceremony | ☐ `attention_index` (to backfill) |
| Encyclopedic attention | Wikipedia pageview spikes on ceremony day | ☐ `attention_index` |
| Social conversation | X / TikTok / Reddit mention volume | ☐ `attention_index` |
| Downstream demand | streaming/box-office lift for nominated works | ☐ (separate; out of scope here) |

The single most important methodological commitment: **report the facets
side-by-side and let them disagree.** When broadcast reach falls but share-of-
voice holds and search interest collapses, that pattern *is* the finding.

---

## 2. The Evan Shapiro lens (how to frame it so it lands)

Shapiro's media-economics charts work because of a few repeatable moves. We
adopt them as design rules:

1. **Always show the denominator.** "5 million viewers" means nothing without
   "out of how many TV homes, and vs. what last year." We normalize per TV
   household and index to a base year so the reader can't be fooled by raw counts.
2. **Kill the lazy narrative with a control group.** The lazy take is "Tonys
   down → Tonys irrelevant." Shapiro would immediately ask: *compared to what?*
   The Oscars/Emmys/Grammys are the control that converts a correlation
   ("ratings fell") into something closer to a causal claim ("fell *because of*
   something Tony-specific" — which, here, turns out to be **false**, and that's
   the story).
3. **Share-of-attention > absolute attention.** In a fragmenting media universe,
   the right unit is *share of a shrinking pie*, not the raw number. We compute
   the Tonys' share of award-show viewing explicitly.
4. **One chart, one sentence.** Each chart's title is the claim
   ("Everyone is falling — not just the Tonys"), not a label ("Viewership over
   time"). See `03_charts.py`.
5. **Name the moments.** Annotate Hamilton, the pandemic, the streaming
   simulcast. Media audiences are event-driven; the chart should be too.
6. **Distinguish linear from total.** Shapiro is relentless that "linear TV" and
   "television" are now different things. Networks increasingly headline
   "across-platform" numbers that are not comparable to the historical linear
   series — e.g. the 2025 Tonys drew **4.85M on linear CBS** but **5.10M
   across platforms** (incl. Paramount+). We segregate `measurement =
   'linear' | 'xplat'` so the trend isn't quietly inflated. (An earlier draft of
   this project mistakenly tagged the 4.85M *linear* figure as cross-platform and
   dropped it; the verification pass in `VERIFICATION.md` caught and fixed it.)

---

## 3. Data architecture

Built by `build_db.py` into `tony_relevance.db` (SQLite, matches the repo's
existing `critics_impact.db` convention). Every row carries a `source_key` and
`confidence` flag; see `sources/SOURCES.md` for URLs.

```
award_broadcasts       core panel: 4 award shows × years, linear viewers,
                       network, host, measurement basis, confidence, source
audience_demographics  median viewer age snapshots (the "oldest audience" fact)
tv_universe            per-year denominators (US TV households, pay-TV %)
attention_index        SCHEMA + empty — the off-TV relevance proxies to backfill
v_relevance (view)     clean linear series joined to denominators
```

**Why a peer panel and not just the Tonys?** Because a single time series can
only ever be *described*, never *explained*. Three peer award shows that
absorbed the identical cord-cutting/streaming shock are the counterfactual that
makes difference-in-differences possible. This is the entire causal engine.

---

## 4. The causal ladder — from correlation to (as close as we can get to) cause

We climb a ladder of identification strength. Honesty about which rung the data
actually supports is the whole game.

| Rung | Design | What it identifies | Status here |
|---|---|---|---|
| 1 | Raw trend | "Tony ratings fell" | ✅ trivially true, uninteresting |
| 2 | Indexed / normalized trend | fell vs. its own past, net of TV-universe shrinkage | ✅ `01` |
| 3 | Share-of-voice | fell vs. the whole award-show category | ✅ `01` |
| 4 | **Difference-in-Differences** | Tony-*specific* deviation from the common award-show trajectory (year FE absorb cord-cutting, pandemic, streaming) | ✅ `02` Design A — **null** |
| 5 | **Event study / natural experiment** (Hamilton 2016) | causal value of a culture-saturating nominee | ✅ `02` Design C — **+45%** |
| 6 | Synthetic control | counterfactual "Tony without X" from a weighted peer combo | ◑ illustrative only — 3 donors, short panel |
| 7 | Interrupted time series | effect of a discrete Tony-specific shock (network/timeslot/simulcast change) | ☐ needs a clean shock + monthly data |

**Why DiD is the workhorse.** In
`log(viewers) ~ is_tony + C(year) + is_tony·year_c`, the **year fixed effects do
the heavy lifting**: they soak up *everything* that hit all award shows in a
given year — the secular flight from linear, the pandemic, the growth of
streaming, NFL counter-programming to the extent it's shared. Whatever is left
on the `is_tony·year_c` interaction is the Tonys' *own* differential trend. It
came back **+1.7%/yr, p=0.57** — statistically indistinguishable from zero, and
if anything positive. **That is the cord-cutting rebuttal, defeated with data:
the Tonys are not dying faster than the category; the category is dying.**

**Why Hamilton is the cleanest causal point.** 2016 is a natural experiment on
the *upside*: a single show (Hamilton) saturated the culture, the Tonys had it,
the peers didn't. Fitting the Tony trend *excluding* 2016 and measuring the miss
gives a **+45%** bump, while the same procedure on each peer (the placebo) sits
on-trend. That bounds the causal worth of *cultural penetration* — and reframes
the relevance problem as **a supply problem in Broadway's hit-making, not a
defect of the broadcast.**

---

## 5. Confounders and how each is handled

| Confounder | Threat | Mitigation |
|---|---|---|
| **Cord-cutting / linear decline** | makes any award show look "irrelevant" | year FE in DiD; per-TV-household normalization; share-of-voice |
| **The pandemic** (2020–21) | giant common shock, breaks parallel trends | year FE absorb it; robustness spec drops 2020–21 |
| **Measurement drift** (linear → across-platform) | inflates recent numbers | `measurement` flag; `xplat` rows excluded from the clean series |
| **Star nominee / event years** (Hamilton; Whitney/Kobe deaths inflating Grammys) | year-specific spikes | flagged in `notes`; treated as event-study signal, not noise |
| **Host/network effects** | idiosyncratic per-ceremony swings | `host`/`network` columns enable controls; awards' network rotation (Emmys) is a useful within-show comparison |
| **Reporting source variance** (L+SD vs final vs cross-platform) | same ceremony, different headline number | `confidence` flag + high-confidence-only robustness spec |

---

## 6. The "something else" beyond Nielsen — the attention layer (do this next)

This is where the project earns the word *relevance* rather than *ratings*. All
three proxies below measure cultural interest **that does not require owning a
television**, so they cleanly separate "theatre left the conversation" from
"linear TV left the living room." Schema is already in `attention_index`.

1. **Google Trends (the spine).** Pull weekly worldwide+US interest for
   `"Tony Awards"`, `"Oscars"`, `"Grammys"`, `"Emmys"` as a single comparative
   query (Trends normalizes them against each other, 0–100). Two metrics per
   year: (a) ceremony-week peak, (b) baseline (non-ceremony) interest. The
   *relative* Tony index vs. Oscars is the headline. *How:* `pytrends`
   (unofficial) or a manual CSV export from trends.google.com. **Causal-ish use:**
   the same DiD, now on log(search interest) — does the Tony *search* footprint
   fall faster than peers? (This is the test most likely to find a real
   Tony-specific gap, because search is where younger, non-TV audiences reveal
   curiosity.)
2. **Wikipedia pageviews (free, clean, API).** The Wikimedia REST pageviews API
   (`/metrics/pageviews/per-article/...`) gives daily views per article, 2015→
   today, no key required and not blocked by paywalls. Measure the
   ceremony-day spike on each year's `"<NN>th Tony Awards"` article vs. the
   `"<NN>th Academy Awards"` article. A shrinking spike = shrinking encyclopedic
   curiosity. This is the most reproducible non-TV signal and should be built
   first.
3. **Social conversation.** X/TikTok/Reddit mention volume around the ceremony.
   Hardest to get cleanly (API costs/limits); treat as a stretch goal. Reddit's
   API + `r/Broadway` vs. `r/movies` subscriber and post-volume ratios is a
   poor-man's proxy that's still directional.

> **Prediction to test:** the Nielsen DiD was null, but the *search/social* DiD
> will likely be negative for the Tonys — i.e., theatre's off-TV footprint has
> eroded relative to film/music even though its TV footprint hasn't. If that
> holds, you have a genuinely novel, causal-leaning finding: **the Tonys kept
> their (shrinking) TV audience but lost the cultural conversation around it.**

---

## 7. What you can write — concrete angles, each tied to a defensible finding

Write the honest version. It's a better piece than the lazy one, and it's
Shapiro-coded: counter-narrative, denominator-first, attention-economics.

**A. The lead essay — "The Tonys aren't dying. Theatre's relevance is dying
somewhere a Nielsen box can't see."**
- Hook: everyone says Tony ratings prove the show is irrelevant.
- Twist (Design A): on TV, the Tonys are falling *no faster than the Oscars or
  Grammys* — and actually the slowest of the four. The ratings panic is a
  linear-TV panic wearing a Broadway costume.
- Pivot: so where IS the relevance problem? Three structural facts — smallest
  reach, oldest audience (~61), Hamilton-dependence — plus the off-TV attention
  gap (once you backfill §6).
- Chart spine: `1_everyone_is_falling`, `2_smallest_in_the_room`,
  `4_oldest_audience`, then the (forthcoming) search-DiD chart.

**B. "The Hamilton Problem"** — a piece on Design C. A culture-saturating show
is worth +45% on the broadcast, but Broadway's economics (jukebox/IP-driven,
tourist-funded, risk-averse capitalization) manufacture fewer of them. Relevance
isn't a marketing problem the Tonys can fix; it's a *supply* problem upstream.

**C. "The oldest room in entertainment"** — the demographic essay. Median age
~61, the oldest of any award show, and the 18–34 share is tiny. Frame
generationally: an award show whose audience is aging out is losing its claim on
the culture being made *now*. (Backfill a full age panel first.)

**D. "Share of voice, not share of mind"** — the Shapiro-classic denominator
piece. Theatre's slice of award-show attention is flat at ~7–8%, but the whole
pie shrank by half. Use it to explain why "the Tonys held their share" and "the
Tonys are in trouble" are both true.

**E. The methods sidebar / "how we know"** — publish the DiD honestly, including
the null. The credibility move (and the most Shapiro thing you can do) is to show
your work and admit where the popular narrative is wrong.

**Headlines that match the evidence (and don't overclaim):**
- "Tony ratings fell 50%. So did everyone's. That's not the story."
- "The Tonys have the oldest audience in entertainment — and that's the real
  red flag."
- "What Hamilton was worth: +45%, and why Broadway can't make another on demand."

**Do NOT write** (the data won't back it): "the Tonys are dying faster than other
award shows," "the Tony broadcast is uniquely failing," or any single-number
"Nielsen proves irrelevance" claim. Those are precisely the takes this dataset
debunks.

---

## 8. Limitations & integrity notes

- **Seed data is from secondary aggregators** (Statista charts, trade press,
  compiled tweets). Before publishing any *specific* number, validate against
  primary Nielsen releases and the per-ceremony Wikipedia infoboxes. Low-
  confidence cells are flagged; the analysis already runs a high-confidence-only
  robustness spec.
- **Four units is a small N.** DiD inference with one treated unit and three
  controls is underpowered; p-values are directional. The qualitative conclusion
  (no Tony-specific TV decline) is robust across specs, but don't oversell
  precision.
- **Demographics are snapshots, not a panel.** The "oldest audience" fact is
  well-sourced but needs a full year-by-year age series to become a *trend*
  claim.
- **The attention layer is unbuilt.** The strongest potential Tony-specific
  finding (off-TV erosion) is a hypothesis until `attention_index` is populated.

---

## 9. Backfill checklist (in priority order)

1. **Wikipedia pageview spikes** for each ceremony (free API; highest ROI,
   fully reproducible). Populate `attention_index`.
2. **Google Trends** comparative index, Tony vs peers, ceremony-week & baseline.
3. Re-run DiD on log(search) and log(pageviews) — the off-TV relevance test.
4. **Full median-age panel** per award per year (Nielsen/Statista demographic
   breakouts) to turn the age snapshot into a trend.
5. Validate all `confidence != high` viewership cells against primary sources.
6. Optional rung-7 ITS: identify a clean Tony-specific shock (e.g., the 2021
   Paramount+ split telecast) and test for a level break in monthly data.

---

*Reproduce everything:*
```bash
pip install -r requirements.txt          # repo root
python3 tony_relevance/build_db.py
python3 tony_relevance/analysis/01_relevance_trends.py
python3 tony_relevance/analysis/02_causal_did.py
python3 tony_relevance/analysis/03_charts.py
```
