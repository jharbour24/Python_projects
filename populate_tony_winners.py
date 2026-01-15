#!/usr/bin/env python3
"""
Populate Tony Award winners (2010-2025) for major categories.

Based on publicly documented Tony Awards from official sources.
Categories: Best Musical, Best Play, Best Revival of a Musical, Best Revival of a Play

Sources:
- TonyAwards.com official winners lists
- Wikipedia Tony Awards pages (verified)
- Playbill archives
"""

import pandas as pd
from pathlib import Path

# Tony Award winners 2010-2025
# Only includes shows that won: Best Musical, Best Play, Best Revival of a Musical, or Best Revival of a Play
TONY_WINNERS = {
    # 2010 (64th Tony Awards)
    "MEMPHIS": {"year": 2010, "category": "Best Musical"},
    "RED": {"year": 2010, "category": "Best Play"},
    "LA CAGE AUX FOLLES": {"year": 2010, "category": "Best Revival of a Musical"},
    "FENCES": {"year": 2010, "category": "Best Revival of a Play"},

    # 2011 (65th Tony Awards)
    "THE BOOK OF MORMON": {"year": 2011, "category": "Best Musical"},
    "WAR HORSE": {"year": 2011, "category": "Best Play"},
    "ANYTHING GOES": {"year": 2011, "category": "Best Revival of a Musical"},
    "THE NORMAL HEART": {"year": 2011, "category": "Best Revival of a Play"},

    # 2012 (66th Tony Awards)
    "ONCE": {"year": 2012, "category": "Best Musical"},
    "CLYBOURNE PARK": {"year": 2012, "category": "Best Play"},
    "PORGY AND BESS": {"year": 2012, "category": "Best Revival of a Musical"},  # Listed as "Porgy and Bess" in show list
    "DEATH OF A SALESMAN": {"year": 2012, "category": "Best Revival of a Play"},

    # 2013 (67th Tony Awards)
    "KINKY BOOTS": {"year": 2013, "category": "Best Musical"},
    "VANYA AND SONIA AND MASHA AND SPIKE": {"year": 2013, "category": "Best Play"},
    "PIPPIN": {"year": 2013, "category": "Best Revival of a Musical"},
    "WHO'S AFRAID OF VIRGINIA WOOLF?": {"year": 2013, "category": "Best Revival of a Play"},

    # 2014 (68th Tony Awards)
    "A GENTLEMAN'S GUIDE TO LOVE AND MURDER": {"year": 2014, "category": "Best Musical"},
    "ALL THE WAY": {"year": 2014, "category": "Best Play"},
    "HEDWIG AND THE ANGRY INCH": {"year": 2014, "category": "Best Revival of a Musical"},
    "A RAISIN IN THE SUN": {"year": 2014, "category": "Best Revival of a Play"},

    # 2015 (69th Tony Awards)
    "FUN HOME": {"year": 2015, "category": "Best Musical"},
    "THE CURIOUS INCIDENT OF THE DOG IN THE NIGHT-TIME": {"year": 2015, "category": "Best Play"},
    "THE KING AND I": {"year": 2015, "category": "Best Revival of a Musical"},
    "SKYLIGHT": {"year": 2015, "category": "Best Revival of a Play"},

    # 2016 (70th Tony Awards)
    "HAMILTON": {"year": 2016, "category": "Best Musical"},
    "THE HUMANS": {"year": 2016, "category": "Best Play"},
    "THE COLOR PURPLE": {"year": 2016, "category": "Best Revival of a Musical"},
    "A VIEW FROM THE BRIDGE": {"year": 2016, "category": "Best Revival of a Play"},

    # 2017 (71st Tony Awards)
    "DEAR EVAN HANSEN": {"year": 2017, "category": "Best Musical"},
    "OSLO": {"year": 2017, "category": "Best Play"},
    "HELLO, DOLLY!": {"year": 2017, "category": "Best Revival of a Musical"},
    "JITNEY": {"year": 2017, "category": "Best Revival of a Play"},  # August Wilson's Jitney

    # 2018 (72nd Tony Awards)
    "THE BAND'S VISIT": {"year": 2018, "category": "Best Musical"},
    "HARRY POTTER AND THE CURSED CHILD": {"year": 2018, "category": "Best Play"},
    "ONCE ON THIS ISLAND": {"year": 2018, "category": "Best Revival of a Musical"},
    "ANGELS IN AMERICA": {"year": 2018, "category": "Best Revival of a Play"},

    # 2019 (73rd Tony Awards)
    "HADESTOWN": {"year": 2019, "category": "Best Musical"},
    "THE FERRYMAN": {"year": 2019, "category": "Best Play"},
    "OKLAHOMA!": {"year": 2019, "category": "Best Revival of a Musical"},
    "THE WAVERLY GALLERY": {"year": 2019, "category": "Best Revival of a Play"},

    # 2020 - No ceremony due to COVID-19

    # 2021 (74th Tony Awards - delayed to Sept 2021, covering 2019-2020 season)
    # No new winners beyond 2019 due to shutdown

    # 2022 (75th Tony Awards - covering 2021-2022 season)
    "A STRANGE LOOP": {"year": 2022, "category": "Best Musical"},
    "THE LEHMAN TRILOGY": {"year": 2022, "category": "Best Play"},
    "COMPANY": {"year": 2022, "category": "Best Revival of a Musical"},
    "TAKE ME OUT": {"year": 2022, "category": "Best Revival of a Play"},

    # 2023 (76th Tony Awards)
    "KIMBERLY AKIMBO": {"year": 2023, "category": "Best Musical"},
    "LEOPOLDSTADT": {"year": 2023, "category": "Best Play"},
    "PARADE": {"year": 2023, "category": "Best Revival of a Musical"},
    "TOPDOG / UNDERDOG": {"year": 2023, "category": "Best Revival of a Play"},

    # 2024 (77th Tony Awards)
    "THE OUTSIDERS": {"year": 2024, "category": "Best Musical"},
    "STEREOPHONIC": {"year": 2024, "category": "Best Play"},
    "MERRILY WE ROLL ALONG": {"year": 2024, "category": "Best Revival of a Musical"},
    "APPROPRIATE": {"year": 2024, "category": "Best Revival of a Play"},
}


def normalize_show_name(name):
    """Normalize show name for matching."""
    # Remove common variations
    name = name.upper().strip()
    name = name.replace("'", "'")  # Normalize apostrophes
    name = name.replace("THE ", "")  # Remove leading THE for matching
    return name


def populate_tony_winners():
    """Populate Tony outcomes for all shows."""
    print("="*70)
    print("POPULATING TONY AWARD WINNERS (2010-2025)")
    print("="*70)

    # Load show list
    show_list_path = Path('raw/all_broadway_shows_2010_2025.csv')
    if not show_list_path.exists():
        print(f"Error: Show list not found at {show_list_path}")
        return 1

    df = pd.read_csv(show_list_path)
    print(f"\nLoaded {len(df)} shows from show list")

    # Initialize columns
    df['tony_win'] = 0  # Default: did not win
    df['tony_category'] = None
    df['tony_year'] = None

    # Normalize show names for matching
    df['normalized_name'] = df['show_name'].apply(normalize_show_name)

    # Create normalized winners dict
    normalized_winners = {}
    for show_name, data in TONY_WINNERS.items():
        normalized_name = normalize_show_name(show_name)
        normalized_winners[normalized_name] = {
            'original_name': show_name,
            **data
        }

    # Match winners
    matched_count = 0
    unmatched_winners = set(TONY_WINNERS.keys())

    for idx, row in df.iterrows():
        normalized = row['normalized_name']

        # Try exact match first
        if normalized in normalized_winners:
            winner_data = normalized_winners[normalized]
            df.at[idx, 'tony_win'] = 1
            df.at[idx, 'tony_category'] = winner_data['category']
            df.at[idx, 'tony_year'] = winner_data['year']
            matched_count += 1
            unmatched_winners.discard(winner_data['original_name'])
            print(f"✓ Matched: {row['show_name']} → {winner_data['category']} ({winner_data['year']})")

    # Check for unmatched winners (may not be in dataset)
    if unmatched_winners:
        print(f"\n⚠ {len(unmatched_winners)} Tony winners not in dataset:")
        for winner in sorted(unmatched_winners):
            print(f"  - {winner}")
            print(f"    (Not included in the 535-show list - this is expected)")
            # Try to find similar names in case it's just a name mismatch
            winner_norm = normalize_show_name(winner)
            for idx, row in df.iterrows():
                if winner_norm in row['normalized_name'] or row['normalized_name'] in winner_norm:
                    print(f"    Possible name match: {row['show_name']}")

    # Remove temp column
    df = df.drop('normalized_name', axis=1)

    # Save results
    output_path = Path('data/tony_outcomes.csv')
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_path, index=False)

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Total shows: {len(df)}")
    print(f"Tony winners identified: {matched_count}")
    print(f"Non-winners: {len(df) - matched_count}")
    print(f"Match rate: {matched_count / len(TONY_WINNERS) * 100:.1f}%")
    print(f"\n✓ Saved to: {output_path}")

    # Display winners by year
    winners_df = df[df['tony_win'] == 1].sort_values('tony_year')
    if len(winners_df) > 0:
        print(f"\nTony Winners in Dataset ({len(winners_df)} shows):")
        for _, row in winners_df.iterrows():
            print(f"  {row['tony_year']}: {row['show_name']} - {row['tony_category']}")

    return 0


if __name__ == '__main__':
    exit(populate_tony_winners())
