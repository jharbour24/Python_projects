#!/usr/bin/env python3
"""
Verification script to match revivals against the show list CSV
"""

import csv
from broadway_revivals_2010_2025 import BROADWAY_REVIVALS_2010_2025

# Read the CSV file
csv_path = '/home/user/Python_projects/raw/all_broadway_shows_2010_2025.csv'
csv_shows = set()

with open(csv_path, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        csv_shows.add(row['show_name'])

# Check which revivals are in the CSV
revivals_in_csv = []
revivals_not_in_csv = []

for show, year in sorted(BROADWAY_REVIVALS_2010_2025.items(), key=lambda x: x[1]):
    if show in csv_shows:
        revivals_in_csv.append((show, year))
    else:
        revivals_not_in_csv.append((show, year))

print("=" * 80)
print("BROADWAY REVIVALS 2010-2025 - VERIFICATION REPORT")
print("=" * 80)
print(f"\nTotal revivals identified: {len(BROADWAY_REVIVALS_2010_2025)}")
print(f"Revivals matching CSV: {len(revivals_in_csv)}")
print(f"Revivals not in CSV: {len(revivals_not_in_csv)}")

print("\n" + "=" * 80)
print("REVIVALS IN CSV (sorted by year):")
print("=" * 80)

current_year = None
for show, year in revivals_in_csv:
    if year != current_year:
        print(f"\n{year}:")
        current_year = year
    print(f"  - {show}")

if revivals_not_in_csv:
    print("\n" + "=" * 80)
    print("REVIVALS NOT IN CSV (may be scheduled for future or not in 2010-2025 range):")
    print("=" * 80)
    for show, year in revivals_not_in_csv:
        print(f"  {year}: {show}")

# Count by decade
musicals = []
plays = []

# Rough categorization (you can refine this)
musical_keywords = ['MUSICAL', 'OPERA', 'DOLLY', 'CHICAGO', 'HAIR', 'CABARET', 'GODSPELL',
                   'EVITA', 'ANNIE', 'PIPPIN', 'CATS', 'CAROUSEL', 'OKLAHOMA', 'COMPANY',
                   'GYPSY', 'SWEENEY', 'MERRILY', 'SPAMALOT', 'WIZ', 'TOMMY', 'FIDDLER',
                   'KING AND I', 'MISS SAIGON', 'FUNNY GIRL', 'INTO THE WOODS', 'MUSIC MAN',
                   'MY FAIR LADY', 'WEST SIDE STORY', 'COLOR PURPLE', 'HELLO', 'SUNSET',
                   'SUNDAY', 'SHE LOVES ME', 'FALSETTOS', 'ONCE ON THIS ISLAND', 'VIOLET',
                   'ON THE TOWN', 'HEDWIG', 'SIDE SHOW', 'SPRING AWAKENING', 'ANYTHING GOES',
                   'HOW TO SUCCEED', 'PORGY', 'EDWIN DROOD', 'JESUS CHRIST', 'BIRDIE',
                   'FINIAN', 'SOUTH PACIFIC', 'NIGHT MUSIC', 'RAGTIME', 'CLEAR DAY',
                   'DAMES AT SEA', 'GIGI', 'TWENTIETH CENTURY', 'KISS ME', 'BUTTERFL',
                   'PARADE', 'CAMELOT', '1776', 'COLORED GIRLS', 'CAROLINE', 'MATTRESS',
                   'ROSES', 'MISERABLES']

for show in revivals_in_csv:
    is_musical = any(keyword in show[0].upper() for keyword in musical_keywords)
    if is_musical:
        musicals.append(show)
    else:
        plays.append(show)

print("\n" + "=" * 80)
print("SUMMARY STATISTICS:")
print("=" * 80)
print(f"Musicals (estimated): {len(musicals)}")
print(f"Plays (estimated): {len(plays)}")
print(f"Total: {len(revivals_in_csv)}")

print("\n" + "=" * 80)
print("PYTHON DICTIONARY READY TO USE:")
print("=" * 80)
print("The complete dictionary is available in: broadway_revivals_2010_2025.py")
print("Import with: from broadway_revivals_2010_2025 import BROADWAY_REVIVALS_2010_2025")

