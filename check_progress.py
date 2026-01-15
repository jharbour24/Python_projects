#!/usr/bin/env python3
import pandas as pd

df = pd.read_csv('data/tony_outcomes_with_performances.csv')

pending = df[df['scrape_status'] == 'pending']
completed = df[df['scrape_status'].isin(['success', 'partial', 'not_found'])]

print(f'✅ Completed: {len(completed)}/{len(df)} ({len(completed)/len(df)*100:.1f}%)')
print(f'⏳ Pending: {len(pending)}')
print()
print('Status breakdown:')
print(f'  Success: {(df["scrape_status"] == "success").sum()}')
print(f'  Partial: {(df["scrape_status"] == "partial").sum()}')
print(f'  Not found: {(df["scrape_status"] == "not_found").sum()}')
print()

if len(completed) > 0:
    recent = df[df['scrape_status'].isin(['success', 'partial', 'not_found'])].tail(5)
    print('Last 5 shows processed:')
    for _, row in recent.iterrows():
        status_icon = '✓' if row['scrape_status'] == 'success' else '⚠' if row['scrape_status'] == 'partial' else '✗'
        year = row.get('production_year', '?')
        perfs = row.get('num_performances', '?')
        print(f'  [{row["show_id"]:3d}] {row["show_name"]:45s} - {status_icon} {year} ({perfs} perfs)')
