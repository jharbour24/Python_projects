# Phase 2 — The deeper research program

*Three linked questions that turn the "are the Tonys still relevant?" project from
a ratings post-mortem into a research-intensive thesis about platform strategy
and Broadway's place in pop culture. Same house style: lead with the
denominator, use a control group, steelman the hard claim, and write down
falsifiable predictions before looking.*

This builds directly on Phase 1 (`RESEARCH_PLAN.md`). Phase 1 established the
counter-intuitive fact that the Tonys' TV decline is **not Tony-specific** — it's
the linear-TV decline. Phase 2 asks the three questions that fact forces:

- **Q1 (Platform).** The CBS broadcast contract is up *now*. Where should the
  Tonys go, and what does the evidence say each option does to reach, demo, and
  Broadway's actual goal?
- **Q2 (Monoculture).** Is Broadway still *producing* pop culture, or only
  *importing* it? (The steelman.)
- **Q3 (Audience).** Has Broadway become a tourist/superfan luxury good rather
  than a mass cultural force — and can that be measured causally?

---

## Q1 — The broadcast-rights inflection: a real decision under a real deadline

### Why this is the timely spine of the whole project

- CBS has carried the Tonys **since 1978** (48 years). The current deal, struck
  in **October 2017, runs *through 2026***. The 79th ceremony (June 7, 2026) was
  the **final contracted year**, and **no renewal had been announced** as of this
  writing. The rights are genuinely open. ([Deadline, 2017](https://deadline.com/2017/10/cbs-tony-awards-through-2026-new-deal-1202187002/); [Variety, 2017](https://variety.com/2017/tv/awards/cbs-tony-awards-1202588195/))
- Simultaneously, awards shows are **migrating to streaming**: the SAG Awards
  left TNT/TBS for **Netflix** (2024 onward, rebranded the "Actor Awards,"
  committed through 2028). Netflix is buying live — NFL, boxing, WWE, awards.
  ([Netflix Tudum](https://www.netflix.com/tudum/articles/actor-awards-sag-aftra-2027-2028-date-time))

So the question isn't abstract. It's: **given everything Phase 1 found, where do
the Tonys belong after 2026?**

### Design 1A — The SAG→Netflix natural experiment (the key causal study)

The SAG Awards are the **best available analog** for a mid-tier awards show
leaving linear for a global streamer. Treat the 2024 move as a treatment and run:

- **Interrupted time series / synthetic control** on SAG outcomes around the
  move: linear-equivalent reach, Google-Trends interest, Wikipedia pageviews,
  social volume, and (if obtainable) median viewer age / 18–34 share.
- **Synthetic SAG** built from award shows that *stayed* on linear (Tonys,
  Emmys, Grammys) to estimate the counterfactual "SAG had it stayed on TNT."
- **Read-across to the Tonys:** the estimated treatment effect of "go to
  streaming" on reach and demo is the single most decision-relevant number you
  can produce for the rights question. If Netflix *grew* SAG's young-adult
  share, that's the strongest argument for moving the Tonys.

> This is novel, causal-leaning, and directly actionable — exactly the kind of
> study no one has cleanly done for the Tonys' decision.

### Design 1B — Multi-criteria platform fit (decision analysis, not vibes)

Score each landing spot against criteria weighted by **Broadway's actual
objective** (which is *not* raw ratings — it's selling tickets and recruiting the
next generation of theatregoers):

| Candidate | Linear reach | Streaming/global reach | Young-adult demo | Discoverability (algorithm) | Rights $ | Strategic fit to Broadway's goal |
|---|---|---|---|---|---|---|
| Stay CBS + Paramount+ | high (declining) | mid | weak | weak | known | incumbent inertia |
| Paramount+ exclusive | none | mid | mid | mid | ? | kills linear reach |
| **Netflix / global streamer** | none | **very high, global** | **strong** | **strong** | unknown | aligns with int'l audience (see Q3) |
| NBC/Peacock or ABC/Hulu | high | mid | mid | mid | ? | bundled awards portfolio |
| YouTube / free, ad-supported | none | very high, global, **free** | **strongest** | **strongest** | low/none | maximizes the *funnel*, not the fee |

**The sharpest, data-driven insight for this table:** Phase-1/Q3 data show
**~41% of Broadway ticket-buyers are international tourists**, yet the Tony
broadcast is **US-linear-only**. The product's revenue base is global; its
broadcast is parochial. A global streamer (or free global YouTube) **aligns the
broadcast's reach with Broadway's actual customers** — a structural mismatch the
numbers expose and the incumbent deal entrenches.

**Deliverable:** a one-page MCDA with an explicit, sourced weighting and a
sensitivity analysis (how the recommendation flips as you re-weight "reach
today" vs. "build the 25-year-old of 2035").

---

## Q2 — Is Broadway still *making* pop culture, or only *importing* it? (steelman)

This is the deep thesis. Operationalize "pop-cultural relevance" as **cultural
*export*: does Broadway still push songs, shows, and language into the shared
culture — or has it become a downstream consumer of IP made elsewhere?**

### The steelman (argue it at full strength)

1. **The "built-in Wikipedia page" problem.** The new-musical pipeline is
   increasingly **adaptations** — movies, TV, celebrity catalogs (jukebox),
   documentaries. The 2025–26 slate (*The Lost Boys, Beaches, Titaníque,
   Schmigadoon!*) is emblematic. A field that adapts movies into musicals is
   **downstream** of pop culture, not a **source** of it. ([OnStage, 2026](https://www.onstageblog.com/editorials/2026/4/7/not-every-new-broadway-musical-needs-to-be-based-on-movies))
2. **Monoculture decay.** Cultural fragmentation killed the shared hit; Broadway
   used to mint songs everyone knew (*West Side Story, Annie, The Lion King*) and
   now rarely does. **Hamilton (2015) looks like the last true Broadway
   crossover** — a cast album on the Billboard charts, lyrics in the discourse,
   a genuine monoculture event. Nothing since has matched it.
3. **Price as a relevance filter.** Average paid admission ~**$131**; premium
   seats multiples of that. At those prices Broadway is a **luxury/tourist
   experience**, not a youth-culture entry point — and originality looks riskier,
   so producers reach for pre-sold IP. ([Davler/Broadway League demographics](https://www.davlermedia.com/20-of-broadway-tickets-sold-to-in-market-tourists/))
4. **Audience structure.** ~**67% tourists**, ~**41% international**, NYC-suburb
   share at a **30-year low**, and **6% of attendees buy ~35% of tickets**: a
   product propped up by visitors and a small superfan base, not a broad cultural
   public. ([Deadline 2024-25 report](https://deadline.com/2025/12/broadway-audience-demographics-report-1236644529/))

**The thesis, stated sharply:** *Broadway is commercially healthy but culturally
**enclosed** — it sells tickets to tourists and superfans while it has stopped
**exporting** songs and stories into the wider culture. The Tony ratings slide
isn't the disease; it's a symptom of a field that the culture no longer treats as
a* source. *The award show for an art form that doesn't generate pop culture
can't itself be pop-culturally relevant.*

### The honest counter-evidence (a rigorous analyst must state it)

- **Broadway grosses are at/near record highs** (pre-pandemic and recovering) —
  commercial irrelevance is *false*.
- **Only 4 of the last ~15 Best Musical winners were movie adaptations** (*Once,
  Kinky Boots, The Band's Visit, Moulin Rouge!*) — the Tonys still reward
  originals; the "Kids' Choice Awards for recycled IP" framing is overstated.
- **Gen-Z fandoms exist** — TikTok-native shows (*Six, & Juliet, Hadestown,
  Beetlejuice*) have real young audiences and viral sounds.

**Resolution (the publishable nuance):** distinguish **commercial health** from
**cultural export**. The defensible claim is not "Broadway is dying" but
**"Broadway has decoupled from the monoculture: thriving as a destination,
fading as a* source *of shared culture."** That decoupling is the real story, and
it's measurable.

### Design 2 — measuring cultural export (concrete, buildable)

| Metric (the dependent variable = "cultural export") | Source | What a decline proves |
|---|---|---|
| Billboard Hot 100 / 200 appearances of Broadway cast recordings per year | Billboard archives | shrinking song crossover |
| Spotify/Apple monthly listeners of cast albums vs. show attendance | streaming APIs / chart sites | fewer people *consume* the music than *see* the show → no spillover |
| TikTok sounds/hashtags **originating** from musicals, by year | TikTok / social vendor | shrinking native virality |
| Wikipedia pageviews of shows vs. comparable films | Wikimedia API (free) | encyclopedic attention gap |
| **IP-share of new musicals** (original vs. movie/jukebox/play adaptation), by season | IBDB/Playbill coding | rising = importing not creating |

**Causal-leaning analyses:**
- **IP-share trend + mediation.** Code every new musical's source 1990→present
  (the existing `critics_impact.db` already has `show_type`; extend it with a
  `source_type`). Test whether rising IP-share **mediates** falling
  cultural-export metrics: `IP-reliance → fewer original cultural artifacts →
  less crossover`.
- **The cultural Tony "bump" — but on streams, not box office.** You explicitly
  *don't* want box office. Cleaner: does a Tony win/performance move **Spotify
  streams of the cast album** in the days after the broadcast, and **has that
  bump shrunk over time**? A shrinking streaming-bump = the broadcast is losing
  its power to push music into the culture. (Event study around the ceremony
  date; same engine as Phase 1 Design C, new outcome.)
- **"Last monoculture moment" test.** Quantify the Hamilton outlier (chart weeks,
  streams, search) and show the gap to the best post-Hamilton show — bounding how
  exceptional, and how unrepeated, it was.

---

## Q3 — From mass culture to tourist luxury good (the audience-structure layer)

Operationalize relevance as **breadth and youth** of the audience, and test
whether Broadway/the Tonys are aging and narrowing **faster than the population**.

- **Generational divergence.** Plot median Broadway-attendee age and median
  Tony-viewer age against the **US median age** over time. If the gap widens, the
  field is aging *relative to the country* — generational abandonment, not just
  an old country. (Broadway League demographic reports give attendee age annually;
  pair with the Tony-viewer-age panel from Phase 1's backfill list.)
- **Concentration / Gini of attendance.** The "6% buy 35%" stat implies a highly
  unequal, superfan-dependent demand curve. Track its concentration over seasons —
  rising concentration = narrowing cultural base even if grosses hold.
- **Tourist-dependence index.** Tourist % (esp. international) over time, against
  the US-linear-only broadcast footprint — the mismatch that powers the Q1
  recommendation.

---

## Falsifiable predictions (write these down *before* pulling the data)

If the "enclosed, no-longer-a-source" thesis is right, you should see:

1. Billboard/Spotify crossover of cast recordings **declines** post-2016, with
   **Hamilton as a lone spike**.
2. **IP-share of new musicals rises** secularly from the 1990s to today.
3. The **Tony streaming-bump on cast albums shrinks** over time.
4. Broadway attendee & Tony-viewer median age **rise faster than US median age**.
5. The **SAG→Netflix move grew young-adult share** — predicting a streaming move
   would do the same for the Tonys.

If instead crossover holds, IP-share is flat, and the streaming-bump is stable,
the thesis is **wrong** and the honest finding becomes "Broadway is fine,
the Tony broadcast just needs a better platform." Either way you have a piece.

---

## What you can write out of Phase 2

- **The cover story:** *"Broadway's lease is up. Where it lands will decide
  whether it still matters."* — the rights decision as the frame, the SAG→Netflix
  experiment as the evidence, the international-mismatch as the kicker.
- **The deep essay:** *"The last monoculture musical."* — the cultural-export
  decline, Hamilton as the lone spike, IP-share as the mechanism, with the
  counter-evidence (record grosses) honestly handled via the
  commercial-health-vs-cultural-export distinction.
- **The contrarian sidebar:** *"Actually, Broadway is thriving — just not where
  you're looking."* — grosses up, fandoms real, but the culture exits the
  building. The decoupling *is* the thesis.

## Build order (highest ROI first)

1. **SAG→Netflix study** (Q1) — most decision-relevant, cleanest causal design,
   and the platform data is gettable.
2. **IP-share time series** (Q2) — extend `critics_impact.db` with `source_type`;
   it's the mechanism variable and reuses data you already have.
3. **Cast-album streaming-bump** event study (Q2) — the "cultural Tony bump"
   that replaces the box-office angle you set aside.
4. **Generational divergence** (Q3) — pair Broadway League age data with the
   Tony-viewer-age panel from Phase 1's backfill list.
5. **Wikipedia/Trends attention layer** (Phase 1 backfill) — feeds Q2 and Q3.
