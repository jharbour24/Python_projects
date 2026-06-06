# Are the Tonys Still Relevant? — a data project

A small, self-contained database + analysis testing whether the Tony Awards are
losing cultural relevance — built to get **as close to causal as the data allow**
(not just "ratings went down"), and framed in the spirit of Evan Shapiro's
media-economics work.

> **The punchline.** Tony linear-TV viewership fell ~50% since 2014 — but so did
> every other award show's, and the Tonys actually declined the *slowest* of the
> big four. A difference-in-differences test against the Oscars/Emmys/Grammys
> finds **no Tony-specific TV decline** (+1.5%/yr, p=0.67). The real
> Tony-specific relevance problem isn't the slope — it's the **smallest reach,
> the oldest audience (~61), and a dependence on rare Hamilton-scale hits**
> (worth +41% to the broadcast). And the deepest question — has theatre left the
> cultural conversation? — has to be answered **off** television, in search and
> social data the project is scaffolded to ingest next.

Read **[`RESEARCH_PLAN.md`](RESEARCH_PLAN.md)** for the full plan: how
"relevance" is operationalized as a latent variable, the causal ladder, the
confounders, the off-TV "attention layer" to build next, and **exactly what you
can and can't defensibly write.**

## Run it

```bash
pip install -r ../requirements.txt        # numpy, pandas, statsmodels, matplotlib
python3 build_db.py                       # builds tony_relevance.db from sources/
python3 analysis/01_relevance_trends.py   # descriptive: absolute, indexed, per-HH, share, age
python3 analysis/02_causal_did.py         # DiD vs peers + Hamilton event study
python3 analysis/03_charts.py             # four Evan-Shapiro-style charts
```

## What's here

```
build_db.py                 curated, source-tagged seed -> tony_relevance.db (SQLite)
RESEARCH_PLAN.md            the plan, the causal logic, and the writing angles
sources/
  award_broadcasts.csv      4 award shows x years: linear viewers, network, host, source
  audience_demographics.csv median viewer age snapshots (Tonys = oldest)
  tv_universe.csv           per-year denominators (US TV households, pay-TV %)
  SOURCES.md                provenance + URLs + data-quality notes
analysis/
  01_relevance_trends.py    measurement layer (no causal claims)
  02_causal_did.py          difference-in-differences + event study
  03_charts.py              charts -> charts/
outputs/                    generated markdown reports (RELEVANCE_TRENDS.md, CAUSAL_DID.md)
charts/                     generated PNGs
```

## The four charts

| File | Claim it makes |
|---|---|
| `1_everyone_is_falling.png`   | Indexed to 2014, the Tony line tracks its peers down — it's not falling faster |
| `2_smallest_in_the_room.png`  | The Tonys were always the smallest absolute audience, even at the Hamilton peak |
| `3_share_of_voice.png`        | Theatre's slice of award-show attention is flat (~7–8%) — the pie shrank, not the slice |
| `4_oldest_audience.png`       | Median viewer age ~61, the oldest of any award show |

## Status & honesty

This is a **v1 seed**: viewership figures come from secondary aggregators (see
`sources/SOURCES.md`) and should be validated against primary Nielsen/Wikipedia
sources before publication. The `attention_index` table (Google Trends /
Wikipedia pageviews / social) is **scaffolded but empty** — backfilling it is
the highest-value next step and the most likely place to find a genuinely
Tony-specific erosion. Inference is underpowered (four award shows); p-values are
directional. The qualitative finding — *no Tony-specific TV decline; the problem
is structural and off-screen* — is robust across specifications.
