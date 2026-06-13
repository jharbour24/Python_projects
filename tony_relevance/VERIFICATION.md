# Data verification log

A rigorous pass over every cell in `tony_relevance.db`, done 2026-06-08. Goal:
make the dataset as accurate as the public record allows, document every
conflict between sources, and record how each was resolved. Cells that could not
be nailed to a primary source are flagged `confidence != high`.

> **Environment note.** Wikipedia and the per-ceremony pages (the ideal primary
> source) return HTTP 403 to the fetch tool in this sandbox, so verification was
> done by cross-referencing multiple secondary aggregators and trade-press
> reports via search. Before publishing any *single* figure, validate the
> `high`-confidence cells against the Wikipedia infobox / Nielsen release and the
> `med`/`low` cells especially.

---

## A. The headline update — 2025 & 2026 Tonys

| Ceremony | What changed | Resolution |
|---|---|---|
| **2025 (78th)** | Previously stored as **4.85M `xplat` (low confidence)** and wrongly excluded from the linear trend. | **CORRECTED.** 4.85M is the **CBS Live+Same-Day _linear_ average** — the most-watched Tonys since 2019, +38% vs. 2024. Re-tagged `linear`, `high`. The **across-platform** figure (incl. Paramount+, streaming +208% YoY) is **5.10M**, added as a separate `xplat` row. Sources: Deadline, TheWrap, Playbill, Variety (2025-06-09). |
| **2026 (79th)** | Aired **June 7, 2026** (Radio City; host Pink; CBS's final contracted year). | **NOW RELEASED & ADDED (2026-06-13).** CBS **linear** home viewers = **5.06M** (preliminary), the **best Tony number since 2019** and **+4% vs. 2025 linear (4.85M)**. CBS's own framing (+44% vs 2024's 3.53M; +23% vs 2023's 4.12M) confirms 5.06M is the *linear* figure. **Measurement caveat (important):** several outlets called it a "slight (−0.78%) dip" — but only by comparing this **linear** 5.06M to 2025's **5.10M across-platform** number. That is apples-to-oranges; like-for-like (linear→linear) the Tonys *rose*. The Paramount+ add for 2026 was not yet released. Coded `linear`, `med` (preliminary). |
| **2023 (76th)** | Was stored 4.30M (Variety "final"); CBS's own YoY math uses 4.12M. | **CHANGED to 4.12M `linear` (med).** Adopts the Live+Same-Day national basis, consistent with how 2024/2025/2026 are measured here and with CBS's published comparisons. The 4.30M Variety "final" is noted as an alternative. Effect on the DiD is negligible (one 0.18M cell; result moved +1.7%→+1.6%/yr). |

Effect on findings: including the corrected 2025 linear point, the 2014→latest
Tony decline eases from −50% (to the 2024 trough) to **−31%** (2025 rebound), and
the **DiD null strengthens** (+1.7%/yr, p=0.57 vs. +1.5%/p=0.67 before). The
qualitative conclusions are unchanged and, if anything, firmer.

---

## B. Tony Awards series — cell-by-cell

| Year | Stored (M) | Conf | Cross-check / conflicts | Resolution |
|---|---|---|---|---|
| 2001 | 8.30 | med | Reported ~8.3M (nytix). | Kept. |
| 2003 | 5.40 | low | A known low year; exact figure varies by source. | Kept, flagged `low` — validate. |
| 2011 | 6.95 | med | ~6.95M (nytix). | Kept. |
| 2012 | 6.01 | med | ~6.0M. | Kept. |
| 2013 | 7.24 | med | ~7.24M; local-rating peak (NPH). | Kept. |
| 2014 | 7.00 | med | ~7.0M. | Kept (trend base year). |
| 2015 | 6.35 | med | ~6.35M. | Kept. |
| 2016 | 8.70 | high | 8.7M, the Hamilton spike; confirmed across Statista + trades. | Kept. |
| 2017 | 6.00 | med | Sources split 6.0M vs 6.1M. | Kept 6.0; ±0.1 within rounding. |
| 2018 | 6.30 | med | ~6.3M. | Kept. |
| 2019 | 5.40 | high | Sources split 5.4M vs 5.5M; last pre-pandemic. | Kept 5.4 (most-cited). |
| 2021 | 2.62 | high | 74th, delayed to Sept 2021; CBS broadcast hour (2.62M) vs 2.77M figure floated for the wider telecast. | Kept 2.62 (CBS hour, L+SD). |
| 2022 | 3.86 | high | 75th; **3.86M** confirmed by Variety + Playbill (first live coast-to-coast, time-zone-adjusted L+SD). | Kept. |
| 2023 | 4.30 | med | **Conflict:** Variety reported **4.3M** ("most-watched since 2019"); TheWrap reported **4.12M** (L+SD). | Kept 4.30 (Variety final national); flagged `med`. The "most-watched since 2019" claim is internally consistent: 4.3 > 2021–22, and was later beaten by 2025's 4.85. |
| 2024 | 3.51 | high | TheWrap/BroadwayWorld "3.5M / 3.51M"; Deadline rounds to 3.53M. The +38% math to 4.85M implies 3.51M. | Kept 3.51. |
| 2025 | 4.85 | high | See §A. Linear; +38% YoY; best since 2019. | Corrected & kept. |
| 2025 | 5.10 | high | See §A. Across platforms (Paramount+). | Added as `xplat`. |
| 2026 | NULL | pending | See §A. | Pending. |

---

## C. Peer award shows — spot-verified against a second source

- **Oscars (ABC).** 2014 (43.7M), 2018 (26.5M), 2019 (29.6M), 2020 (23.6M)
  explicitly confirmed against a second source (Washington Post / CBS News /
  Statista); 2015–17 (37.3/34.4/32.9M) confirmed by trend and the compiled
  series; 2021 (10.4M all-time low), 2022 (16.6M), 2023 (18.7M), 2024 (19.5M),
  2025 (19.69M) confirmed via CBS News / Variety. **Caveat:** 2024–25 Oscars
  figures increasingly fold in **digital/streaming (Hulu)**; treat the most
  recent two years as slightly less comparable to the long linear run.
- **Emmys (rotating network).** Full 2014–2022 series (15.6 / 11.9 / 11.38 /
  11.38 / 10.17 / 6.98 / 6.36 / 7.4 / 5.92M) confirmed against THR/Deadline/
  Variety/Statista. 2023 ceremony **aired Jan 2024** (strike delay), all-time low
  ~4.3M; 2024 rebound ~6.9M (Axios "6.8M", Variety "6.9M" — kept 6.9, ±0.1);
  2025 ~7.4M (Axios "4-year high").
- **Grammys (CBS).** 2010–2026 series taken from a single compiled list
  (@chartdata) and corroborated for recent years by TheWrap (2025: 15.4M) and
  THR (2026: 14.4M). Note two anomalous spikes flagged in `notes`: 2012 (39.9M,
  Whitney Houston died the prior night) and 2020 (18.7M, Kobe Bryant).

**Status:** peer cells are cross-checked but, like the Tony series, should be
validated against primary Nielsen releases before any specific number is
published. The DiD result is insensitive to ±0.5M perturbations in any single
peer cell (year fixed effects + robustness specs).

---

## D. Denominators & demographics

- **`tv_universe`** (US TV households, pay-TV penetration) are **approximate**
  (`source_key='approx'`), interpolated from Nielsen TV-HH counts and Statista
  pay-TV penetration. They are used only for per-household *normalization* and
  *share* framing, not as precise point estimates. Flagged throughout.
- **`audience_demographics`** median-age figures are **sparse snapshots from
  different years** (the Ad Age survey is c. 2008; the Oscars 55+ figure is the
  96th/2024 ceremony). They support the *ranking* claim ("Tonys oldest") but not
  a year-by-year *trend*. Backfilling a full age panel is the top demographic
  to-do.

---

## E. Known residual risks (do before publication)

1. Validate every `confidence ∈ {med, low}` Tony cell (esp. 2003, 2017, 2023)
   against the Wikipedia per-ceremony infobox or the original Nielsen/Deadline
   release.
2. Decide a single consistent **measurement basis** per show-year (L+SD linear
   vs. final national vs. across-platform) and re-pull where outlets disagree —
   the 2023 Tony (4.30 vs 4.12) and the 2024–25 Oscars (digital inclusion) are
   the cases that matter most.
3. Replace the `approx` `tv_universe` rows with the exact Nielsen TV-HH series.
4. Fill the 2026 Tony row once Nielsen publishes it, then re-run all three
   scripts (the analysis windows already exclude the pending cell automatically).
