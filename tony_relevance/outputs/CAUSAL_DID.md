# Tony Awards — Causal-leaning analysis (DiD against peer award shows)

_Generated 2026-06-06 23:26. Window 2014–2024, linear-TV viewers only. Control group: Oscars, Emmys, Grammys._

## Design A — Difference-in-Differences (the headline causal test)

`log(viewers) ~ is_tony + C(year) + is_tony:year_c`. The year fixed effects soak up every shock common to all award shows (cord-cutting, the pandemic, the secular flight from linear). The interaction is the Tonys' **extra** annual change beyond that common path.

| Specification | Tony extra annual change | 95% CI | p | n |
|---|---|---|---|---|
| Main (2014–2024) | +1.5% | [-5.3%, +8.9%] | 0.668 | 43 |
| Drop pandemic (2020–21) | +1.9% | [-5.4%, +9.7%] | 0.628 | 36 |
| High-confidence cells only | +0.4% | [-11.5%, +13.8%] | 0.951 | 27 |

**Read:** the Tonys' differential trend is **+1.5%/yr** (indistinguishable from zero, p=0.67). 
In plain terms: **the Tonys are not falling on TV any faster than the Oscars, Emmys or Grammys.** The ratings collapse is a *linear-TV* phenomenon, not a *theatre* phenomenon. This is the single most important — and most counter-intuitive — result in the project, and it should reshape the thesis (see RESEARCH_PLAN §'What the data actually licenses you to say').

## Design B — Who is bleeding fastest? (separate slopes)

| Award | Annual % change in linear viewers | p | n |
|---|---|---|---|
| Emmys | -9.9% | 0.000 | 11 |
| Oscars | -9.8% | 0.000 | 11 |
| Grammys | -9.1% | 0.000 | 11 |
| Tony | -8.2% | 0.000 | 10 |

**Read:** by annual rate of decline the Tonys rank **#4 of 4** (1 = fastest-falling). The Tonys are mid-pack in *rate*; their problem is *level* (lowest absolute reach) and *age* (oldest audience), not an unusually steep slope.

## Design C — Hamilton (2016) as a natural experiment

Fit the Tonys' 2014–2024 trend *excluding* 2016, predict 2016, and measure the miss. Peers (no Hamilton) are the placebo — their 2016 should sit on-trend.

- **Tony 2016 bump above its own trend: +41%.**
- Placebo Oscars 2016 vs trend: +2%
- Placebo Emmys 2016 vs trend: -0%
- Placebo Grammys 2016 vs trend: +5%

**Read:** a single culture-saturating show (Hamilton) lifted the Tony broadcast by roughly the size of the bump above, while peers stayed on-trend. That bounds the causal value of *cultural penetration*: when theatre makes something the whole country is arguing about, the ratings follow. The relevance problem is the scarcity of Hamilton-scale shows, not the broadcast itself.

## Identification caveats (read before quoting any coefficient)

- **Four units is not many.** With one treated show and three controls, robust/clustered inference is underpowered; treat p-values as directional.
- **Parallel-trends is an assumption, not a fact.** DiD assumes the Tonys would have tracked the peer trajectory absent any Tony-specific cause. The drop-pandemic and high-confidence rows are partial stress-tests.
- **'Relevance' ≠ 'linear ratings.'** Every design here is built on Nielsen linear viewers. That measures *broadcast reach*, which is necessary but not sufficient for cultural relevance. The strongest Tony-specific evidence (oldest/aging audience; smallest off-TV search & social footprint) lives in the demographic and attention layers, which need backfilling — see RESEARCH_PLAN.
- **Measurement drift.** Networks increasingly headline 'across-platform' numbers (e.g. Tony 2025) that include streaming and are not comparable to the historical linear series; those rows are excluded here and the exclusion matters for the recent slope.
