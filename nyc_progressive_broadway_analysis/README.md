# NYC Progressive Constituencies & Broadway Audience Propensity Analysis

A fully reproducible Python pipeline analyzing the geospatial overlap between progressive political constituencies and Broadway/cultural participation propensity in New York City.

## Overview

This analysis examines whether progressive political support and cultural participation (as a proxy for Broadway audience propensity) are geographically correlated at the NYC Census tract level.

**Key Finding:** Progressive political support and cultural participation show a **positive correlation** (Pearson r = 0.175, p < 0.001) across NYC census tracts.

## Repository Structure

```
nyc_progressive_broadway_analysis/
├── nyc_progressive_broadway_pipeline.py  # Main pipeline script
├── data/
│   ├── raw/                              # Raw data downloads
│   └── processed/                        # Cleaned datasets
│       ├── progressive_election_data.csv
│       └── acs_data.csv
├── outputs/
│   ├── report.md                         # Main analysis report
│   ├── figures/                          # Visualizations
│   │   ├── map_progressive_index.png
│   │   ├── map_cultural_index.png
│   │   ├── scatter_progressive_vs_cultural.png
│   │   └── residuals_hotspots.png
│   └── tables/                           # Results tables
│       ├── model_coefficients.csv
│       └── tract_level_indices.csv
└── README.md
```

## Methodology

### Data Sources (Public Only)

1. **NYC Board of Elections** (2018-2024): Progressive candidate vote shares
2. **U.S. Census ACS** (2022): Demographics, income, education, employment
3. **OpenStreetMap** (2024): Cultural venue locations
4. **TIGER/Line** (2020): Census tract boundaries

### Index Construction

**Progressive Support Index:** Z-score of progressive candidate vote shares (AOC, Mamdani, DSA-endorsed)

**Cultural Participation Index:** Composite of five z-scored components:
- Arts employment share (NAICS 71)
- Educational attainment (% Bachelor's+)
- Transit usage (% commuting via public transit)
- Theatre district proximity (inverse distance to Times Square)
- Cultural venue density (OSM venues per 1,000 residents)

### Statistical Model

```
Cultural_Index ~ Progressive_Index + median_income + pct_bachelors
                 + pct_renters + pct_age_18_44 + dist_to_theatre
```

**Model Fit:** R² = 0.855, F-statistic = 730.44 (p < 0.001)

## Key Results

- **Bivariate correlation:** r = 0.175 (p < 0.001), ρ = 0.073 (p = 0.047)
- **Progressive coefficient:** β = 0.017 (95% CI: [-0.002, 0.037], p = 0.082)
- **Strongest predictors of cultural participation:**
  - Education (β = 0.276, p < 0.001)
  - Renter percentage (β = 0.220, p < 0.001)
  - Proximity to theatre district (β = -0.233, p < 0.001)

## Running the Pipeline

### Requirements

```bash
pip install pandas geopandas requests shapely scipy scikit-learn statsmodels matplotlib seaborn
```

### Execution

```bash
python nyc_progressive_broadway_pipeline.py
```

The pipeline will:
1. Download public data sources (with graceful fallbacks)
2. Construct Progressive and Cultural indices
3. Run spatial analysis and regression models
4. Generate maps and visualizations
5. Create comprehensive report

**Runtime:** ~30 seconds
**Outputs:** 7 files (1 report, 4 maps, 2 tables)

## Limitations

1. **Ecological fallacy:** Tract-level correlations ≠ individual behavior
2. **Tourist confounding:** Broadway audiences include many tourists
3. **Proxy quality:** Cultural participation approximated, not measured directly
4. **Geographic aggregation:** ED→tract crosswalk introduces error
5. **Temporal mismatch:** Data from 2018-2024 span
6. **Omitted variables:** Race, ethnicity, immigrant status not fully captured

## Strategic Implications

- **High-overlap tracts:** Core constituencies for culturally-inflected progressive messaging
- **Positive residual tracts:** Cultural spaces with untapped progressive organizing potential
- **Negative residual tracts:** Progressive communities that could be engaged through cultural programming

## Output Files

All outputs are in the `outputs/` directory:

- **`report.md`** - Full analysis narrative with embedded visualizations
- **`figures/map_progressive_index.png`** - Progressive Support Index choropleth
- **`figures/map_cultural_index.png`** - Cultural Participation Index choropleth
- **`figures/scatter_progressive_vs_cultural.png`** - Scatter plot with OLS and LOWESS fits
- **`figures/residuals_hotspots.png`** - Geographic distribution of model residuals
- **`tables/model_coefficients.csv`** - Full regression results
- **`tables/tract_level_indices.csv`** - Complete tract-level dataset (750 tracts)

## Citation

```
NYC Progressive Constituencies & Broadway Audience Propensity Analysis (2025)
Public data pipeline using NYC BOE election results, U.S. Census ACS,
and OpenStreetMap cultural venue data.
```

## License

This analysis uses only publicly available data. The code is provided for reproducibility and research purposes.

---

**Generated:** 2025-11-09
**Analysis Date:** November 2025
**Geographic Scope:** NYC (5 boroughs, 750 Census tracts)
