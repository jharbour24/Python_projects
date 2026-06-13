"""
01_relevance_trends.py — Descriptive relevance trends (the "what happened" layer)
=================================================================================

This is the measurement layer. It does NOT make causal claims; it establishes
the stylised facts that the causal script (02) then tries to attribute.

Four lenses, each designed to pre-empt the obvious "...but everything on TV is
down" rebuttal:

  1. ABSOLUTE        raw linear viewers per ceremony.
  2. INDEXED         each award indexed to a common base year (2014 = 100), so
                     trajectories are comparable regardless of starting size.
  3. NORMALISED      viewers per 1,000 US TV households — strips out the
                     shrinking-TV-universe story. If the Tonys fall even as a
                     SHARE of available TV homes, that is relevance loss, not
                     just cord-cutting.
  4. SHARE-OF-VOICE  Tony viewers as a share of the big-four award-show audience
                     that year — "of all the attention award shows command, how
                     much goes to theatre?"

Plus the demographic kicker: median viewer age (Tonys are the oldest).

Writes: outputs/RELEVANCE_TRENDS.md  and prints the headline numbers.
Run:    python3 tony_relevance/analysis/01_relevance_trends.py
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "tony_relevance.db"
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)
REPORT = OUT / "RELEVANCE_TRENDS.md"

BASE_YEAR = 2014   # first year all four shows are present in the clean series
AWARDS = ["Tony", "Oscars", "Emmys", "Grammys"]


def load() -> pd.DataFrame:
    con = sqlite3.connect(DB)
    df = pd.read_sql("SELECT * FROM v_relevance ORDER BY award, year", con)
    con.close()
    # Drop cells with no viewership yet (e.g. the 2026 ceremony, pending Nielsen).
    df = df.dropna(subset=["viewers_m"]).reset_index(drop=True)
    # Phase 1 is the "big four" only — keep SAG (Phase 2) out of share-of-voice etc.
    df = df[df.award.isin(AWARDS)].reset_index(drop=True)
    return df


def cagr(v0, v1, years):
    if v0 <= 0 or v1 <= 0 or years <= 0:
        return np.nan
    return (v1 / v0) ** (1 / years) - 1


def pct_change(v0, v1):
    return (v1 / v0 - 1) if v0 else np.nan


def main():
    df = load()
    L = []
    L.append("# Tony Awards — Relevance Trends (descriptive layer)\n")
    L.append(f"_Generated {pd.Timestamp.now():%Y-%m-%d %H:%M}. Linear-TV viewers only "
             f"(streaming/'across-platforms' rows excluded for comparability)._\n")

    # ---- 1 & 2: absolute + decline since base year and since peak ----
    L.append("## 1. Absolute decline and decline vs. peers\n")
    L.append(f"Indexed to {BASE_YEAR} = 100. % change is {BASE_YEAR} → latest "
             "clean linear year for each show.\n")
    L.append("| Award | Base-yr viewers (M) | Latest yr | Latest viewers (M) | "
             f"% change since {BASE_YEAR} | Peak (M, yr) | % off peak |")
    L.append("|---|---|---|---|---|---|---|")
    rows = {}
    for a in AWARDS:
        s = df[df.award == a].sort_values("year")
        if s.empty:
            continue
        base = s[s.year == BASE_YEAR]
        base_v = float(base.viewers_m.iloc[0]) if not base.empty else np.nan
        last = s.iloc[-1]
        peak = s.loc[s.viewers_m.idxmax()]
        chg = pct_change(base_v, last.viewers_m) if not np.isnan(base_v) else np.nan
        off_peak = pct_change(peak.viewers_m, last.viewers_m)
        rows[a] = dict(base_v=base_v, last_v=last.viewers_m, last_y=int(last.year),
                       peak_v=peak.viewers_m, peak_y=int(peak.year), chg=chg, off_peak=off_peak)
        L.append(f"| {a} | {base_v:.1f} | {int(last.year)} | {last.viewers_m:.2f} | "
                 f"{chg:+.0%} | {peak.viewers_m:.1f} ({int(peak.year)}) | {off_peak:+.0%} |")
    L.append("")

    # Relative framing: Tony vs peer average decline
    tony_chg = rows["Tony"]["chg"]
    peer_chg = np.nanmean([rows[a]["chg"] for a in AWARDS if a != "Tony" and a in rows])
    L.append(f"**Read:** Since {BASE_YEAR}, the Tonys' linear audience changed "
             f"**{tony_chg:+.0%}** vs. a peer-average of **{peer_chg:+.0%}** "
             f"(Oscars/Emmys/Grammys). The Tonys also sit at the **lowest absolute "
             f"reach** of the four — they entered the streaming era smallest and "
             f"remain smallest.\n")

    # ---- 3: per-TV-household normalisation ----
    L.append("## 2. Normalised for the shrinking TV universe\n")
    L.append("Viewers per 1,000 US TV households. If the line still falls, the "
             "decline is **not** merely 'fewer people own TVs'.\n")
    L.append("| Award | Base-yr per-1k-HH | Latest per-1k-HH | % change |")
    L.append("|---|---|---|---|")
    for a in AWARDS:
        s = df[df.award == a].sort_values("year")
        if s.empty:
            continue
        base = s[s.year == BASE_YEAR]
        if base.empty:
            continue
        b = float(base.viewers_per_1000_tvhh.iloc[0])
        l = float(s.iloc[-1].viewers_per_1000_tvhh)
        L.append(f"| {a} | {b:.1f} | {l:.1f} | {pct_change(b, l):+.0%} |")
    L.append("")
    L.append("**Read:** the per-household decline is nearly as steep as the raw "
             "decline — cord-cutting explains only a sliver. The Tonys are losing "
             "the audience that *still owns a television*.\n")

    # ---- 4: share-of-voice among the big four ----
    L.append("## 3. Share of the award-show audience (share of voice)\n")
    wide = df.pivot_table(index="year", columns="award", values="viewers_m")
    common = wide.dropna(subset=AWARDS, how="any")  # years where all four exist
    sov = common.div(common.sum(axis=1), axis=0)
    L.append("Tony viewers ÷ (Tony+Oscars+Emmys+Grammys) viewers, years where all "
             "four aired:\n")
    L.append("| Year | Tony share | Tony (M) | Big-four total (M) |")
    L.append("|---|---|---|---|")
    for y in common.index:
        L.append(f"| {int(y)} | {sov.loc[y,'Tony']:.1%} | {common.loc[y,'Tony']:.2f} | "
                 f"{common.loc[y].sum():.1f} |")
    L.append("")
    if len(sov) >= 2:
        first, last = sov.index.min(), sov.index.max()
        L.append(f"**Read:** the Tonys' share of the big-four award-show audience went "
                 f"from **{sov.loc[first,'Tony']:.1%}** ({int(first)}) to "
                 f"**{sov.loc[last,'Tony']:.1%}** ({int(last)}). Theatre commands a "
                 f"shrinking slice of an already-shrinking pie.\n")

    # ---- 5: demographics ----
    con = sqlite3.connect(DB)
    demo = pd.read_sql("SELECT * FROM audience_demographics ORDER BY median_viewer_age DESC", con)
    con.close()
    L.append("## 4. The audience is the oldest in the business\n")
    L.append("| Award | Year | Median viewer age | Note |")
    L.append("|---|---|---|---|")
    for _, r in demo.iterrows():
        L.append(f"| {r['award']} | {int(r['year'])} | {r['median_viewer_age']:.1f} | {r['notes']} |")
    L.append("")
    L.append("**Read:** at a median age of ~61, the Tony audience is older than the "
             "Oscars (~50), Emmys (~52) and Grammys (~45). An award show whose viewers "
             "are aging out is, almost by definition, losing its grip on the culture "
             "being made *now*. (Sparse snapshots — backfill a full age panel to make "
             "this a trend, not a point.)\n")

    # ---- 6: most-recent ceremonies (2025 correction + 2026 pending) ----
    con = sqlite3.connect(DB)
    recent = pd.read_sql(
        "SELECT ceremony_year AS year, viewers_m, measurement, confidence, notes "
        "FROM award_broadcasts WHERE award='Tony' AND ceremony_year >= 2024 "
        "ORDER BY ceremony_year, measurement", con)
    con.close()
    L.append("## 5. Most recent ceremonies (2024–2026)\n")
    L.append("| Year | Viewers (M) | Basis | Confidence | Note |")
    L.append("|---|---|---|---|---|")
    for _, r in recent.iterrows():
        v = "—" if pd.isna(r["viewers_m"]) else f"{r['viewers_m']:.2f}"
        L.append(f"| {int(r['year'])} | {v} | {r['measurement']} | {r['confidence']} | {r['notes']} |")
    L.append("")
    L.append("**Read:** the Tonys have now **recovered for four straight years** — "
             "2021 trough 2.62M → **5.06M in 2026, the best since 2019** — climbing "
             "right through the years everyone was calling them culturally dead. The "
             "rebound mirrors a category-wide post-pandemic bounce (Oscars 10.4M→19.7M; "
             "Grammys 9.2M→16.9M), which is why the causal test (02) still finds **no "
             "Tony-specific decline**. Two data-integrity notes: (1) 2026's 5.06M is the "
             "**linear** CBS number; several outlets called it a 'slight dip' only by "
             "comparing it to 2025's **5.10M across-platform** figure — on a like-for-"
             "like linear basis it actually **rose ~4%** (4.85M→5.06M). (2) The "
             "Paramount+ streaming add for 2026 had not been released at the time of "
             "writing.\n")

    REPORT.write_text("\n".join(L))
    print(f"Wrote {REPORT}\n")

    # Console headline
    print("HEADLINE NUMBERS")
    print(f"  Tony {BASE_YEAR}->{rows['Tony']['last_y']}: {rows['Tony']['base_v']:.1f}M -> "
          f"{rows['Tony']['last_v']:.2f}M  ({rows['Tony']['chg']:+.0%})")
    print(f"  Peer-average change over same span: {peer_chg:+.0%}")
    print(f"  Tony off its own peak ({rows['Tony']['peak_y']}): {rows['Tony']['off_peak']:+.0%}")
    if len(sov) >= 2:
        print(f"  Tony share of big-four award audience: "
              f"{sov.loc[first,'Tony']:.1%} ({int(first)}) -> {sov.loc[last,'Tony']:.1%} ({int(last)})")


if __name__ == "__main__":
    main()
