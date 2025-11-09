# Revised Methodology: Geospatial Analysis of Progressive Political Support and Cultural Venue Accessibility in New York City

**Version 2.0 – Spatially-Aware, Robustness-Centered, Publication-Quality**

---

## Abstract

This document presents a revised methodology for estimating the spatial relationship between progressive political support and access to cultural venues (Broadway theaters and performing arts spaces) at the Census tract level in New York City. The revision addresses three critical methodological concerns from the initial analysis: (1) **outcome variable contamination** through inclusion of sociodemographic predictors in the dependent variable, (2) **spatial dependence** in both political preferences and cultural access, and (3) **insufficient robustness testing** of key modeling assumptions. We present a theoretically-grounded, spatially-explicit framework that uses latent variable methods for index construction, population-weighted dasymetric mapping for geographic harmonization, and a comprehensive suite of spatial econometric models with extensive sensitivity analyses.

---

## 1. Theoretical Framework

### 1.1 Research Question

**Do neighborhoods with stronger progressive political preferences exhibit greater spatial accessibility to Broadway and performing arts venues, net of confounding sociodemographic factors?**

This is a **descriptive spatial association question**, not a causal inquiry. We seek to characterize geographic overlap patterns that may inform cultural sector outreach and progressive organizing strategies.

### 1.2 Conceptual Model

We hypothesize spatial clustering in both outcomes based on:

1. **Cultural consumption theory** (Bourdieu 1984; Peterson & Kern 1996): Cultural participation correlates with education and class, which also predict political orientation, generating spurious association.

2. **Urban spatial structure** (Isard 1956; Fujita & Thisse 2002): Both progressive voters and cultural consumers cluster near transit-accessible, high-amenity urban cores due to residential sorting.

3. **Spatial spillovers** (Anselin 2003): Political preferences and cultural tastes may exhibit positive spatial autocorrelation through peer effects, though this analysis does not identify such mechanisms.

**Key theoretical insight**: Any observed correlation between progressive voting and cultural access may reflect:
- **Confounding** by education, income, age (addressed via controls)
- **Spatial dependence** (addressed via spatial models)
- **Measurement error** in precinct-tract crosswalks (addressed via sensitivity tests)
- **Ecological fallacy** (acknowledged, not solvable at this resolution)

---

## 2. Outcome Variable: Cultural Venue Accessibility Index (Non-Leaking)

### 2.1 Problem Statement

**Original specification flaw**: The Cultural Participation Index included education, transit use, and income—variables that are also controls in the regression. This creates **mechanical correlation** and inflates R².

### 2.2 Revised Specification

The **Cultural Venue Accessibility Index** (CVAI) is constructed using **only spatial-behavioral indicators**, excluding all sociodemographic variables:

#### Component 1: Network Travel Time to Broadway Theater District (Weight: 0.40)

**Indicator**: Median travel time (minutes) from tract centroid to Times Square/Theater District (40.758°N, -73.986°W) via public transit, departing 7:00–8:00pm on a typical Wednesday.

**Justification**:
- Behavioral proxy: Captures **friction of distance** for potential Broadway attendance (Hansen 1959; Geurs & van Wee 2004).
- Time-specific: Evening departure reflects actual theater-going behavior.
- Network-based: Uses MTA GTFS routing, not Euclidean distance, accounting for transit network structure.

**Data source**:
- MTA GTFS feed (November 2024)
- OpenTripPlanner or r5py for isochrone calculation
- Inverted to accessibility score: `access_score = 1 / (1 + travel_time_minutes)`

**Technical note**: For tracts with no transit access within 90 minutes, assign minimum score (right-censored distribution).

---

#### Component 2: Performing Arts Venue Density (Weight: 0.35)

**Indicator**: Count of performing arts venues per km² within tract boundaries, normalized by citywide distribution.

**Justification**:
- Spatial proxy: Direct measure of **local cultural infrastructure** (Currid & Williams 2010).
- Venue types included: Broadway theaters, Off-Broadway venues, concert halls, dance studios, black box theaters (NAICS 711110, 711120, 711190; OSM tags: `amenity=theatre`, `amenity=arts_centre`).
- Excludes: Movie theaters, sports venues, bars/nightclubs (different audience).

**Data source**:
- OpenStreetMap Overpass API (November 2024)
- NYC Open Data: Department of Cultural Affairs venue registry
- Manual validation for Broadway theaters (exact list: 41 official Broadway houses)

**Normalization**:
```
density_score = (venues_per_km² - mean) / sd
```

---

#### Component 3: Cultural Event Permit Density (Weight: 0.15)

**Indicator**: Annual count of permitted outdoor cultural events (concerts, street fairs, performances) per 1,000 residents.

**Justification**:
- Behavioral activation: Reflects **revealed cultural demand** rather than demographic potential (Glaeser et al. 2001).
- Public data: NYC Mayor's Office Special Events permits (public record).

**Data source**:
- NYC Open Data: Special Events database (2022-2024)
- Filter: Event types = performance, concert, festival, art installation
- Geocode to tract; normalize by tract population

**Normalization**:
```
event_score = log(1 + events_per_1000_pop)
```

---

#### Component 4: Nighttime Cultural Mobility Index (Weight: 0.10)

**Indicator**: Relative mobility to cultural destinations 6pm–11pm.

**Justification**:
- Behavioral trace: **Observed movement patterns** toward cultural venues (Athey 2017; SafeGraph use cases).
- If public mobility data unavailable, **substitute**: Distance to nearest 3 performing arts venues (inverse-weighted).

**Data source**:
- SafeGraph Patterns (if accessible via academic license)
- **Fallback**: Calculate multi-venue accessibility:
  ```
  mobility_proxy = Σ(1 / distance_to_venue_i) for i in {3 nearest venues}
  ```

**Normalization**: Standardize to mean 0, SD 1.

---

### 2.3 Index Aggregation

**Method 1 (Theory-Driven)**: Weighted sum with expert weights (0.40, 0.35, 0.15, 0.10).

**Method 2 (Data-Driven)**: Principal Components Analysis (PCA)
- Extract first principal component from standardized indicators
- Interpret loadings to validate construct coherence
- Report % variance explained

**Method 3 (Latent Variable)**: Confirmatory Factor Analysis (CFA)
- Specify single latent factor "Cultural Accessibility"
- Test measurement model fit (CFI > 0.90, RMSEA < 0.08)
- Use factor scores as outcome

**Primary specification**: Method 2 (PCA) for transparency and replicability.

**Sensitivity test**: Re-estimate all models with Methods 1 and 3; report coefficient stability.

---

### 2.4 Validity Checks

1. **Convergent validity**: Correlate CVAI with NEA SPPA arts attendance rates (if available at metro level).
2. **Discriminant validity**: CVAI should NOT correlate >0.7 with median income (else still contaminated).
3. **Face validity**: Map CVAI; verify high scores in Midtown, Lincoln Center, Downtown Brooklyn (known cultural clusters).

---

## 3. Predictor Variable: Progressive Political Support Index (Latent Factor Model)

### 3.1 Problem Statement

**Original specification flaw**: Simple z-score averaging across races ignores:
- **Turnout differences** across years/races
- **Precinct-tract mismatch** (ecological aggregation error)
- **Year-specific shocks** (e.g., 2020 COVID turnout surge)
- **Measurement error** in precinct-level returns

### 3.2 Data Collection

#### Election Results (Precinct-Level)

**Races included**:
1. **2018 Congressional Primary, NY-14**: Ocasio-Cortez (Dem) vs. Crowley (Dem establishment)
2. **2020 Congressional General, NY-14**: Ocasio-Cortez vote share
3. **2021 State Assembly Primary, AD-36**: Mamdani (DSA) vs. establishment
4. **2022 Congressional Primary, NY-14**: Ocasio-Cortez vote share
5. **2024 State Assembly races**: DSA-endorsed candidates vs. incumbents
6. **2025 NYC Mayoral Primary**: Progressive candidate(s) vs. moderate/establishment

**Data source**: NYC Board of Elections precinct-level results (CSV downloads per race).

**Progressive vote definition**:
- For primaries: Progressive candidate vote share of two-party vote
- For generals: Progressive candidate vote share (Democratic line only)

**Exclusion criteria**:
- Unopposed races (no variance)
- Races with <100 votes cast in NYC (truncation issues)

---

#### Geographic Harmonization: Precinct → Tract

**Challenge**: NYC election districts (EDs) do not nest cleanly within Census tracts.

**Method**: Population-weighted dasymetric mapping (Mennis 2003; Schroeder 2007)

**Algorithm**:
```
For each tract t:
  1. Spatial overlay: Identify all EDs intersecting t
  2. For each intersecting ED e:
     a. Calculate intersection polygon area A_{e,t}
     b. Extract population from Census block-level data within A_{e,t}
     c. Weight w_{e,t} = pop_{e,t} / pop_e
  3. Aggregate:
     progressive_vote_t = Σ(w_{e,t} * progressive_vote_e)
     total_vote_t = Σ(w_{e,t} * total_vote_e)
  4. Calculate: progressive_share_t = progressive_vote_t / total_vote_t
```

**Data requirements**:
- ED shapefiles (NYC Open Data: "Election Districts 2020")
- Census block-level population (P.L. 94-171 Redistricting Data)
- Precinct results with ED identifiers

**Sensitivity test**: Compare population-weighted vs. area-weighted aggregation; report correlation.

---

### 3.3 Turnout-Weighted Progressive Score

**Rationale**: Low-turnout races (e.g., off-year primaries) may over-represent activist subsets. Weight by turnout to reflect broader electorate.

**Formula**:
```
For tract t across races r = 1,...,R:
  weight_r,t = votes_cast_r,t / voting_age_population_t

Turnout-adjusted score:
  progressive_t = Σ(weight_r,t * progressive_share_r,t) / Σ(weight_r,t)
```

**Normalization**: Within-year standardization before aggregation to remove cycle effects.

---

### 3.4 Latent Factor Model (Bayesian Partial Pooling)

**Problem**: Simple averaging assumes each race measures the same latent "progressive-ness" with equal precision. More appropriate: hierarchical factor model.

**Model specification**:

```
Level 1 (Observed vote shares):
  progressive_share[r,t] ~ Normal(λ[r] * θ[t] + α[r], σ²[r])

Where:
  θ[t] = latent progressive support in tract t (what we want)
  λ[r] = factor loading for race r (allows different scales)
  α[r] = race-specific intercept (base progressive vote)
  σ²[r] = race-specific measurement error variance

Level 2 (Latent trait):
  θ[t] ~ Normal(μ_borough[t], τ²)

Where:
  μ_borough = borough-specific mean (partial pooling)
  τ² = between-tract variance within borough
```

**Estimation**:
- Bayesian: Stan or PyMC (MCMC)
- Frequentist: Structural equation model (lavaan in R, semopy in Python)

**Output**: Posterior mean (or MLE) of θ[t] for each tract = **Progressive Support Index (PSI)**.

**Advantages**:
1. Accounts for differing measurement precision across races
2. Borrows strength across tracts (shrinkage for low-turnout areas)
3. Provides uncertainty estimates (posterior SD)

**Sensitivity test**: Compare latent factor PSI vs. simple turnout-weighted average; report rank correlation.

---

### 3.5 Validity Checks

1. **Predictive validity**: PSI should strongly predict 2024 Presidential vote (Biden vote share).
2. **Concurrent validity**: Correlate PSI with Working Families Party enrollment rates (public voter file data).
3. **Face validity**: Map PSI; verify high scores in known progressive strongholds (Astoria, North Brooklyn, Upper West Side).

---

## 4. Control Variables (Confounders)

**Principle**: Include only variables that:
1. Are **theoretically** plausible confounders (predict both outcome and exposure)
2. Are **not** colliders or mediators
3. Are measured **independently** of outcome variable

### 4.1 Sociodemographic Controls (Tract-Level, ACS 2018-2022 5-Year Estimates)

| Variable | ACS Table | Justification |
|----------|-----------|---------------|
| Median household income (log) | B19013 | Class-based cultural consumption; political economy of voting |
| % Bachelor's degree+ | B15003 | Cultural capital (Bourdieu 1984); education-ideology link |
| % Renter-occupied housing | B25003 | Residential stability; housing politics |
| % Age 18-34 | B01001 | Life-cycle cultural participation; generational political shifts |
| % Age 65+ | B01001 | Retirement effects on both outcomes |
| % Non-Hispanic White | B03002 | Race-ethnicity as confounder (not interest, but necessary control) |
| Population density (log) | B01003 / AREALAND | Urbanization correlates with both outcomes |

**Normalization**: Standardize all controls to mean 0, SD 1.

**Multicollinearity check**: Report variance inflation factors (VIF); flag VIF > 5.

---

### 4.2 Spatial Controls

| Variable | Source | Justification |
|----------|--------|---------------|
| Distance to Manhattan CBD (km) | Calculated from tract centroid | Monocentric city model (Alonso 1964); both outcomes cluster centrally |
| Subway stop density (per km²) | MTA GTFS + spatial join | General accessibility; correlated with both voting and cultural access |
| Borough fixed effects | Census FIPS codes | Unmodeled borough-level heterogeneity |

**Note**: Subway density and travel time (in CVAI) measure different constructs:
- **Subway density**: General network access (control)
- **Travel time to Theater District**: Specific behavioral friction (outcome component)

---

## 5. Spatial Econometric Framework

### 5.1 Motivation

**Spatial autocorrelation diagnostic**: Before modeling, calculate:
- **Global Moran's I** for both CVAI and PSI
- **Local Moran's I** (LISA) to identify clusters
- **Lagrange Multiplier tests** for spatial lag vs. spatial error

**Expected result**: Positive spatial autocorrelation in both variables (Tobler's First Law). Ignoring this violates OLS independence assumption → biased standard errors (Type I error inflation).

---

### 5.2 Model Suite

#### Model 1: OLS Baseline (Benchmark)

```
CVAI[t] = β₀ + β₁ PSI[t] + X[t]'γ + ε[t]

Where:
  X[t] = vector of controls (section 4)
  ε[t] ~ i.i.d. N(0, σ²) [assumption likely violated]
```

**Purpose**: Establish baseline; demonstrate need for spatial models via residual autocorrelation test.

---

#### Model 2: Spatial Error Model (SEM)

```
CVAI[t] = β₀ + β₁ PSI[t] + X[t]'γ + u[t]
u[t] = λ W u[t] + ε[t]
ε[t] ~ i.i.d. N(0, σ²)

Where:
  W = spatial weights matrix (queen contiguity, row-normalized)
  λ = spatial error autocorrelation parameter
```

**Interpretation**: Controls for unmodeled spatially-clustered omitted variables. Does **not** imply cultural access spillovers—only that errors are correlated across space.

**Estimation**: Maximum likelihood (PySAL spreg)

---

#### Model 3: Spatial Lag Model (SAR)

```
CVAI[t] = ρ W CVAI[t] + β₀ + β₁ PSI[t] + X[t]'γ + ε[t]
ε[t] ~ i.i.d. N(0, σ²)

Where:
  ρ = spatial autoregressive parameter
```

**Interpretation**: Allows cultural accessibility in tract *t* to depend on accessibility in neighboring tracts (e.g., Broadway district creates spillover demand in adjacent areas).

**Caution**: Coefficient β₁ is **not** the total effect; must calculate direct vs. indirect effects (LeSage & Pace 2009).

---

#### Model 4: Spatial Durbin Model (SDM)

```
CVAI[t] = ρ W CVAI[t] + β₁ PSI[t] + θ₁ W PSI[t] + X[t]'γ + W X[t]'δ + ε[t]
```

**Interpretation**: Most flexible spatial specification; allows both outcome spillovers (ρ) and covariate spillovers (θ, δ).

**Test**: If θ = -ρβ and δ = -ργ, SDM collapses to SEM (testable restriction).

---

#### Model 5: Spatial Quantile Regression

```
Q_τ(CVAI[t] | PSI[t], X[t]) = β₀(τ) + β₁(τ) PSI[t] + X[t]'γ(τ)
```

**Purpose**: Check for heterogeneous effects across CVAI distribution (e.g., stronger PSI effect in high-accessibility tracts).

**Spatial extension**: Use spatial quantile regression (McMillen 2013) with contiguity structure.

---

### 5.3 Spatial Weights Matrix Specifications

**Primary**: Queen contiguity (shared edge or vertex), row-normalized.

**Sensitivity tests**:
1. Rook contiguity (shared edge only)
2. K-nearest neighbors (k=5, k=8)
3. Inverse distance decay (threshold = 2km, 5km)
4. Network distance (street network via OSMnx)

**Robustness criterion**: Sign and significance of β₁ should be stable across W specifications.

---

### 5.4 Standard Errors

**Primary**: Spatial HAC (Conley 1999) with bandwidth = 5km
- Robust to arbitrary spatial correlation within 5km
- Implemented via `spreg` or manual Conley SE calculation

**Sensitivity**: Compare with:
1. OLS standard errors (should be too small)
2. Cluster-robust SE (borough clusters)
3. Spatial error model's ML standard errors

---

## 6. Model Selection and Inference

### 6.1 Selection Criteria

1. **Information criteria**: Compare AIC, BIC across models
2. **LM tests**: Lagrange Multiplier tests for SAR vs. SEM (Anselin 1988)
3. **Vuong test**: Non-nested model comparison
4. **Residual diagnostics**: Moran's I on residuals (should → 0 in spatial models)

**Decision rule**: Select most parsimonious model that eliminates residual spatial autocorrelation.

---

### 6.2 Effect Decomposition (for SAR/SDM)

Do **not** interpret β₁ directly in spatial lag models. Instead, report:

```
Average Direct Effect (ADE): ∂E[CVAI[t]] / ∂PSI[t]
Average Indirect Effect (AIE): ∂E[CVAI[t]] / ∂PSI[s], s ≠ t
Average Total Effect (ATE): ADE + AIE
```

Calculated via matrix inversion: `(I - ρW)⁻¹` (LeSage & Pace 2009, Ch. 2).

**Substantive interpretation**: ADE = within-tract association; AIE = cross-tract spillover.

---

## 7. Robustness and Validation

### 7.1 Spatial Cross-Validation

**Method**: Geographic k-fold CV (spatial blocks, not random splits)

**Algorithm**:
1. Partition NYC into 5 spatial clusters (k-means on tract centroids)
2. For each fold:
   - Train model on 4 clusters
   - Predict CVAI on held-out cluster
   - Calculate RMSE, MAE, R²
3. Report mean ± SD across folds

**Criterion**: Spatial CV R² should not drop >0.10 from in-sample R² (else overfitting).

---

### 7.2 Leave-One-Borough-Out (LOBO)

**Purpose**: Test generalization to unobserved boroughs.

**Algorithm**:
```
For borough b in {Bronx, Brooklyn, Manhattan, Queens, Staten Island}:
  1. Train model on tracts in other 4 boroughs
  2. Predict CVAI for borough b
  3. Calculate borough-specific R², RMSE
  4. Report β₁ estimate from LOBO model
```

**Criterion**: β₁ should have consistent sign and order-of-magnitude across LOBO iterations.

---

### 7.3 Placebo Tests

**Placebo outcome 1**: Sports venue accessibility (should **not** correlate with PSI conditional on controls).

**Placebo outcome 2**: Fast food restaurant density (arbitrary spatial pattern).

**Placebo outcome 3**: Industrial land use percentage (should be negatively correlated if at all, not positive).

**Test**: Run full model suite with placebo outcomes. If β₁ is significant for placebos, suspect spurious spatial correlation.

---

### 7.4 Negative Controls

**Concept**: Variables that **should not** be associated with PSI conditional on controls, but might be correlated spatially.

**Examples**:
1. Tree canopy coverage (NYC Parks data)
2. Average building age (PLUTO data)
3. Noise complaint density (311 data)

**Test**: Include as additional control; β₁ (PSI coefficient) should remain stable.

---

### 7.5 Index Robustness

#### CVAI Sensitivity

1. **Component weights**: Vary weights ±50% for each component; report range of β₁.
2. **Component exclusion**: Drop each component one-at-a-time; re-estimate.
3. **Alternative aggregation**: Compare PCA, CFA, and expert weights (Section 2.3).

**Reporting**: "Multiverse analysis" table showing β₁ across all CVAI specifications.

---

#### PSI Sensitivity

1. **Race inclusion**: Drop each election year one-at-a-time; re-estimate latent factor.
2. **Turnout weighting**: Compare unweighted vs. weighted aggregation.
3. **Geographic aggregation**: Compare population-weighted vs. area-weighted ED→tract.
4. **2025 Mayoral race**: Re-estimate excluding 2025 (check if single race drives results).

**Reporting**: Coefficient plot showing β₁ ± 95% CI across PSI specifications.

---

### 7.6 Measurement Error Simulation

**Problem**: ED→tract crosswalk introduces **classical measurement error** in PSI.

**Test**: Berkson error simulation (Carroll et al. 2006)
1. Estimate σ²_PSI_error from crosswalk variance within tracts
2. Simulate 1,000 datasets with added noise: PSI* = PSI + N(0, σ²_error)
3. Re-estimate model on each; report mean β₁ and SE
4. Compare to baseline (should attenuate toward zero)

**Correction**: If attenuation severe, use simulation-extrapolation (SIMEX) estimator.

---

## 8. Diagnostics and Model Checking

### 8.1 Pre-Estimation Checks

| Check | Test | Action if Failed |
|-------|------|------------------|
| Normality of residuals | Shapiro-Wilk | Spatial quantile regression as alternative |
| Linearity | Partial residual plots | Add splines for distance, density |
| Homoskedasticity | Breusch-Pagan | Use robust SE or WLS |
| Multicollinearity | VIF > 5 | Drop or combine correlated controls |
| Spatial autocorrelation in Y | Moran's I (p<0.05) | Mandatory spatial model |
| Spatial autocorrelation in X | Moran's I on PSI | Include spatial lag of PSI |

---

### 8.2 Post-Estimation Checks

| Check | Test | Criterion |
|-------|------|-----------|
| Residual spatial autocorrelation | Moran's I on residuals | p > 0.10 (no remaining pattern) |
| Influential observations | DFBETAS, Cook's D | No single tract changes β₁ by >20% |
| Outliers | Studentized residuals | Investigate ∣r∣ > 3; report with/without |
| Spatial regime stability | Chow test by borough | No structural break |

---

## 9. Reporting and Interpretation Guidelines

### 9.1 Coefficient Interpretation (Conservative Language)

**Avoid**:
- "Progressive support **causes** cultural accessibility"
- "Broadway attracts progressives"
- "Cultural venues **drive** progressive voting"

**Use**:
- "A one-standard-deviation increase in the Progressive Support Index is **associated with** a [β₁] standard-deviation difference in Cultural Venue Accessibility, conditional on sociodemographic controls and spatial dependence structure."
- "Tracts with higher progressive vote shares **tend to exhibit** greater accessibility to performing arts venues, though this association **may reflect** residential sorting, omitted neighborhood characteristics, or reverse causation."
- "The observed spatial pattern is **consistent with** geographic overlap between progressive constituencies and cultural infrastructure, but **does not imply** individual-level cultural consumption or causal mechanisms."

---

### 9.2 Uncertainty Quantification

**Report**:
1. Point estimates ± 95% CI (Conley SE)
2. Posterior distributions (if Bayesian)
3. Range across robustness tests (min–max β₁)
4. Spatial CV prediction intervals

**Visualization**: Coefficient plot showing:
- Baseline OLS
- Spatial models (SEM, SAR, SDM)
- Robustness variants (LOBO, placebo, sensitivity)
- Clearly indicate overlapping vs. non-overlapping CIs

---

### 9.3 Ecological Fallacy Caveat (Mandatory)

**Standard disclaimer** (include in all outputs):

> "This analysis operates at the Census tract level (median population ~4,000). Observed associations between tract-level progressive voting and cultural venue accessibility **do not** permit inferences about individual behavior. A tract with high progressive vote share and high cultural accessibility may contain individuals who vote progressively but never attend theater, and vice versa. Ecological inference remains a fundamental limitation of aggregate-level spatial analysis (Robinson 1950; Piantadosi et al. 1988)."

---

## 10. Data Pipeline and Reproducibility

### 10.1 Workflow Management (Snakemake)

**Structure**:
```
Snakefile
├── rule download_election_data
├── rule download_acs
├── rule download_osm_venues
├── rule download_gtfs
├── rule harmonize_precincts_to_tracts
├── rule construct_cvai
├── rule construct_psi_latent_factor
├── rule prepare_controls
├── rule estimate_ols_baseline
├── rule estimate_spatial_models
├── rule robustness_tests
├── rule generate_report
└── rule all (master target)
```

**Features**:
- Automatic dependency resolution
- Parallel execution where possible
- Checkpointing (resume on failure)
- Provenance tracking (input file hashes)

---

### 10.2 Data Versioning and Hashing

**All raw data files** → compute SHA-256 hash → store in `data/checksums.txt`

**Example**:
```
election_2025_mayoral.csv: a3f5d9...
acs_2022_tract_data.csv: 8b2e1c...
osm_venues_20241109.geojson: 4d7a2f...
```

**Purpose**: Detect silent data corruption; verify exact replication.

---

### 10.3 Environment Specification

**`environment.yml`** (conda):
```yaml
name: nyc_progressive_spatial
channels:
  - conda-forge
dependencies:
  - python=3.11
  - geopandas=0.14
  - pysal=24.1
  - libpysal=4.9
  - spreg=1.4
  - statsmodels=0.14
  - scikit-learn=1.3
  - pandas=2.1
  - numpy=1.26
  - matplotlib=3.8
  - seaborn=0.13
  - snakemake=7.32
  - pymc=5.10  # for Bayesian latent factor model
  - r5py=0.1  # for transit routing
  - osmnx=1.6
```

**Lockfile**: `conda env export --no-builds > environment_frozen.yml` for exact replication.

---

### 10.4 Code Organization

```
nyc_progressive_spatial/
├── data/
│   ├── raw/              # Never modify
│   ├── processed/        # Intermediate outputs
│   └── final/            # Analysis-ready datasets
├── src/
│   ├── data_acquisition.py
│   ├── geographic_harmonization.py
│   ├── cvai_construction.py
│   ├── psi_latent_factor.py
│   ├── spatial_models.py
│   ├── robustness_tests.py
│   └── visualization.py
├── models/
│   ├── ols_baseline.pkl
│   ├── sem_fitted.pkl
│   └── ...
├── outputs/
│   ├── figures/
│   ├── tables/
│   └── report/
├── Snakefile
├── environment.yml
├── README.md
└── METHODOLOGY.md (this document)
```

---

## 11. Summary of Models to Estimate

| Model | Specification | Purpose | Primary Inference |
|-------|--------------|---------|-------------------|
| **OLS** | Standard linear regression | Benchmark; demonstrate spatial autocorrelation problem | Baseline β₁ (likely biased SE) |
| **SEM** | Spatial error model (λW u) | Control for omitted spatial variables | Efficient β₁ with spatial correlation |
| **SAR** | Spatial lag model (ρW CVAI) | Test for cultural access spillovers | Direct vs. indirect effects |
| **SDM** | Spatial Durbin model (ρW CVAI + θW PSI) | Flexible spatial model | Full effect decomposition |
| **Spatial QR** | Quantile regression with spatial SE | Heterogeneous effects | β₁(τ) across CVAI distribution |
| **Borough FE + Spatial** | Within-borough + spatial structure | Control for borough-level confounding | Robust to unobserved borough characteristics |

---

## 12. Expected Results and Failure Modes

### 12.1 Expected Findings

**Base case**: Modest positive association (β₁ ≈ 0.10–0.25 SD) between PSI and CVAI, attenuated but still significant after spatial controls.

**Mechanism interpretation**: Residential sorting into transit-accessible, culturally-rich neighborhoods by both progressive voters and arts consumers, driven by shared demographic profile (young, educated, renter).

---

### 12.2 Potential Failure Modes

| Failure | Diagnosis | Implication |
|---------|-----------|-------------|
| β₁ ≈ 0 after spatial controls | True association was purely spatial confounding | Cultural access irrelevant for progressive organizing |
| β₁ flips sign across LOBO | Borough-specific heterogeneity; not generalizable | Need borough interaction terms or separate models |
| Residual Moran's I still significant | Spatial model misspecified | Try higher-order W, non-linear spatial process |
| CVAI components don't load on single factor | CVAI is multidimensional | Use multiple outcomes or IRT model |
| PSI latent factor has poor fit | Elections measure different constructs | Drop heterogeneous races; focus on subset |
| Placebo outcomes also significant | Spurious spatial correlation | Re-examine spatial weights; check for data errors |

---

## 13. Literature Foundations (Key Citations)

**Spatial econometrics**:
- Anselin, L. (1988). *Spatial Econometrics: Methods and Models*. Kluwer.
- LeSage, J., & Pace, R. K. (2009). *Introduction to Spatial Econometrics*. CRC Press.
- Conley, T. G. (1999). GMM estimation with cross sectional dependence. *Journal of Econometrics*, 92(1), 1-45.

**Dasymetric mapping**:
- Mennis, J. (2003). Generating surface models of population using dasymetric mapping. *The Professional Geographer*, 55(1), 31-42.

**Cultural consumption**:
- Bourdieu, P. (1984). *Distinction: A Social Critique of the Judgement of Taste*. Harvard University Press.
- Peterson, R. A., & Kern, R. M. (1996). Changing highbrow taste: From snob to omnivore. *American Sociological Review*, 900-907.

**Urban economics**:
- Alonso, W. (1964). *Location and Land Use*. Harvard University Press.
- Fujita, M., & Thisse, J. F. (2002). *Economics of Agglomeration*. Cambridge University Press.

**Accessibility measures**:
- Geurs, K. T., & Van Wee, B. (2004). Accessibility evaluation of land-use and transport strategies. *Journal of Transport Geography*, 12(2), 127-140.

**Ecological fallacy**:
- Robinson, W. S. (1950). Ecological correlations and the behavior of individuals. *American Sociological Review*, 15(3), 351-357.

---

## 14. Reproducibility Checklist

- [ ] All raw data sources publicly accessible or archived
- [ ] SHA-256 checksums computed for all input files
- [ ] Conda environment.yml specifies exact package versions
- [ ] Snakemake workflow automates full pipeline
- [ ] Random seeds set for all stochastic procedures (e.g., k-fold splits, MCMC)
- [ ] Intermediate outputs saved with timestamps and version hashes
- [ ] All figures include code to regenerate (no manual edits)
- [ ] Sensitivity analyses scripted (not ad-hoc)
- [ ] README documents hardware requirements (RAM, CPU for large spatial matrices)
- [ ] Public GitHub repository with DOI (Zenodo archival)

---

## 15. Narrative Guidance for Final Report

### 15.1 Introduction

- State research question as **descriptive/exploratory**, not causal
- Motivate via practical organizing question (where to focus outreach?)
- Acknowledge ecological fallacy upfront

### 15.2 Methods

- Emphasize **transparency** and **robustness**
- Use this methodology document as backbone; condense for publication
- Include directed acyclic graph (DAG) showing assumed confounding structure

### 15.3 Results

- Lead with **spatial diagnostic plots** (Moran scatterplots for CVAI, PSI)
- Present OLS first, then "preferred" spatial model (SEM or SDM based on tests)
- Report effect sizes in **standardized units** (SD of CVAI per SD of PSI)
- Show **coefficient plot** across robustness tests (multiverse)

### 15.4 Discussion

- Interpret in terms of **geographic overlap**, not individual behavior
- Discuss **substantive significance**: Is β₁ = 0.15 SD "large"? (Compare to effect of 1 SD income)
- Acknowledge **limitations**:
  - Omitted variables (unmeasured neighborhood history, qualitative cultural taste)
  - Temporal dynamics (this is cross-sectional)
  - Causal identification impossible without quasi-experimental design
- Suggest **future research**: Panel data, instrumental variables (e.g., theater openings), individual-level survey data

### 15.5 Conclusion

- **Modest claims**: "Spatial association exists; robustness varies; further research needed"
- **Actionable insights**: Map high PSI + low CVAI tracts (organizing opportunities) vs. high CVAI + low PSI tracts (potential expansion)
- **Transparency**: "All code and data available at [DOI]."

---

## Appendix: Pseudocode for Key Functions

### A.1 Population-Weighted Dasymetric Mapping

```python
def precinct_to_tract_dasymetric(precincts_gdf, tracts_gdf, census_blocks_gdf):
    """
    Overlay precincts onto tracts using population weights from blocks.

    Parameters:
    - precincts_gdf: GeoDataFrame with columns [geometry, precinct_id, progressive_votes, total_votes]
    - tracts_gdf: GeoDataFrame with columns [geometry, tract_geoid]
    - census_blocks_gdf: GeoDataFrame with columns [geometry, block_geoid, population]

    Returns:
    - tract_results: DataFrame with [tract_geoid, progressive_share]
    """
    import geopandas as gpd
    from shapely.ops import unary_union

    results = []

    for tract_idx, tract in tracts_gdf.iterrows():
        tract_geom = tract.geometry

        # Find overlapping precincts
        overlapping_precincts = precincts_gdf[precincts_gdf.intersects(tract_geom)]

        tract_prog_votes = 0
        tract_total_votes = 0

        for precinct_idx, precinct in overlapping_precincts.iterrows():
            # Intersection polygon
            intersection = tract_geom.intersection(precinct.geometry)

            # Find blocks within intersection
            blocks_in_intersection = census_blocks_gdf[
                census_blocks_gdf.geometry.within(intersection)
            ]

            intersection_pop = blocks_in_intersection['population'].sum()

            # Find total precinct population
            blocks_in_precinct = census_blocks_gdf[
                census_blocks_gdf.geometry.within(precinct.geometry)
            ]
            precinct_pop = blocks_in_precinct['population'].sum()

            # Weight
            if precinct_pop > 0:
                weight = intersection_pop / precinct_pop
            else:
                weight = intersection.area / precinct.geometry.area  # fallback to area

            # Aggregate votes
            tract_prog_votes += weight * precinct['progressive_votes']
            tract_total_votes += weight * precinct['total_votes']

        # Calculate share
        if tract_total_votes > 0:
            progressive_share = tract_prog_votes / tract_total_votes
        else:
            progressive_share = np.nan

        results.append({
            'tract_geoid': tract['tract_geoid'],
            'progressive_votes': tract_prog_votes,
            'total_votes': tract_total_votes,
            'progressive_share': progressive_share
        })

    return pd.DataFrame(results)
```

---

### A.2 Travel Time Accessibility (r5py)

```python
def compute_transit_accessibility(tracts_gdf, destination_point, gtfs_path):
    """
    Compute transit travel time from each tract centroid to destination.

    Parameters:
    - tracts_gdf: GeoDataFrame with tract geometries
    - destination_point: (lon, lat) tuple for Theater District
    - gtfs_path: Path to MTA GTFS zip file

    Returns:
    - tracts_gdf with added column 'travel_time_minutes'
    """
    import r5py
    from datetime import datetime

    # Initialize routing engine
    transport_network = r5py.TransportNetwork.from_gtfs(gtfs_path)

    # Define origins (tract centroids)
    origins = tracts_gdf.copy()
    origins['lon'] = origins.geometry.centroid.x
    origins['lat'] = origins.geometry.centroid.y
    origins['id'] = origins.index

    # Define destination
    destinations = pd.DataFrame([{
        'id': 'theater_district',
        'lon': destination_point[0],
        'lat': destination_point[1]
    }])

    # Compute travel times
    travel_time_matrix = r5py.TravelTimeMatrixComputer(
        transport_network,
        origins=origins[['id', 'lon', 'lat']],
        destinations=destinations,
        departure=datetime(2024, 11, 13, 19, 0),  # Wednesday 7pm
        transport_modes=[r5py.TransportMode.TRANSIT, r5py.TransportMode.WALK],
        max_time=datetime.timedelta(minutes=90)
    ).compute_travel_times()

    # Merge back
    tracts_gdf = tracts_gdf.merge(
        travel_time_matrix.rename(columns={'travel_time': 'travel_time_minutes'}),
        left_index=True,
        right_on='from_id'
    )

    # Convert to accessibility score (inverse)
    tracts_gdf['transit_accessibility'] = 1 / (1 + tracts_gdf['travel_time_minutes'])

    return tracts_gdf
```

---

### A.3 Latent Factor Model (PyMC)

```python
def estimate_latent_psi(vote_shares_df, tracts_df):
    """
    Estimate latent progressive support factor using Bayesian hierarchical model.

    Parameters:
    - vote_shares_df: Long-format DataFrame [tract_id, race_id, progressive_share, turnout]
    - tracts_df: DataFrame [tract_id, borough]

    Returns:
    - DataFrame with [tract_id, psi_mean, psi_sd]
    """
    import pymc as pm
    import numpy as np

    # Prepare data
    races = vote_shares_df['race_id'].unique()
    tracts = vote_shares_df['tract_id'].unique()
    boroughs = tracts_df.set_index('tract_id').loc[tracts, 'borough'].values
    borough_idx, borough_names = pd.factorize(boroughs)

    # Pivot to matrix: rows=tracts, cols=races
    vote_matrix = vote_shares_df.pivot(
        index='tract_id',
        columns='race_id',
        values='progressive_share'
    ).values

    with pm.Model() as model:
        # Hyperpriors (borough-level)
        mu_borough = pm.Normal('mu_borough', mu=0.5, sigma=0.2, shape=len(borough_names))

        # Latent progressive support (tract-level)
        psi = pm.Normal('psi', mu=mu_borough[borough_idx], sigma=0.15, shape=len(tracts))

        # Factor loadings (race-level)
        loadings = pm.Normal('loadings', mu=1.0, sigma=0.3, shape=len(races))
        intercepts = pm.Normal('intercepts', mu=0.5, sigma=0.1, shape=len(races))

        # Measurement error (race-level)
        sigma_race = pm.HalfNormal('sigma_race', sigma=0.1, shape=len(races))

        # Likelihood
        for r_idx, race in enumerate(races):
            obs_mask = ~np.isnan(vote_matrix[:, r_idx])
            pm.Normal(
                f'obs_{race}',
                mu=intercepts[r_idx] + loadings[r_idx] * psi[obs_mask],
                sigma=sigma_race[r_idx],
                observed=vote_matrix[obs_mask, r_idx]
            )

        # Sample
        trace = pm.sample(2000, tune=1000, return_inferencedata=True)

    # Extract posterior means
    psi_posterior = trace.posterior['psi'].mean(dim=['chain', 'draw']).values
    psi_sd = trace.posterior['psi'].std(dim=['chain', 'draw']).values

    return pd.DataFrame({
        'tract_id': tracts,
        'psi_mean': psi_posterior,
        'psi_sd': psi_sd
    })
```

---

### A.4 Spatial Durbin Model (PySAL)

```python
def estimate_spatial_durbin_model(gdf, outcome_var, treatment_var, controls, W):
    """
    Estimate Spatial Durbin Model with direct/indirect effects.

    Parameters:
    - gdf: GeoDataFrame with all variables
    - outcome_var: Name of dependent variable column
    - treatment_var: Name of main predictor column
    - controls: List of control variable names
    - W: PySAL spatial weights object (row-normalized)

    Returns:
    - dict with coefficients, effects, diagnostics
    """
    from spreg import GM_Lag
    import numpy as np

    # Prepare arrays
    y = gdf[outcome_var].values.reshape(-1, 1)
    X_main = gdf[[treatment_var] + controls].values

    # Create spatially lagged X (WX)
    W_sparse = W.sparse
    WX = W_sparse @ X_main

    # Combine [X, WX]
    X_full = np.hstack([X_main, WX])

    # Column names
    var_names = [treatment_var] + controls
    wx_names = [f'W_{v}' for v in var_names]
    all_names = var_names + wx_names

    # Estimate SDM via GM (generalized moments)
    model = GM_Lag(
        y, X_full, w=W,
        name_y=outcome_var,
        name_x=all_names,
        name_w='W_queen'
    )

    # Extract effects (LeSage & Pace 2009)
    rho = model.rho  # spatial lag parameter
    n = len(y)

    # (I - rho*W)^-1
    I = np.eye(n)
    M_inv = np.linalg.inv(I - rho * W.full()[0])

    # Direct effects: diagonal elements of M_inv @ beta
    beta_main = model.betas[:len(var_names)]  # coefficients on X
    theta_main = model.betas[len(var_names):]  # coefficients on WX

    direct_effects = []
    indirect_effects = []
    total_effects = []

    for k in range(len(var_names)):
        # S_r(W) matrix for variable k
        S_k = M_inv * (beta_main[k] + theta_main[k] * W.full()[0])

        direct = np.trace(S_k) / n
        total = S_k.sum() / n
        indirect = total - direct

        direct_effects.append(direct)
        indirect_effects.append(indirect)
        total_effects.append(total)

    return {
        'model': model,
        'coefficients': dict(zip(all_names, model.betas.flatten())),
        'direct_effects': dict(zip(var_names, direct_effects)),
        'indirect_effects': dict(zip(var_names, indirect_effects)),
        'total_effects': dict(zip(var_names, total_effects)),
        'rho': rho,
        'aic': model.aic,
        'r_squared': model.pr2  # pseudo R-squared
    }
```

---

**END OF METHODOLOGY DOCUMENT**

---

## Document Version Control

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-09 | Initial simple analysis (problematic outcome specification) |
| 2.0 | 2025-11-09 | Full revision: non-leaking CVAI, latent PSI, spatial models, robustness suite |

**Approved for implementation**: 2025-11-09
**Target journal tier**: Regional Science and Urban Economics / Journal of Urban Economics / Political Geography

**Reproducibility statement**: This methodology is designed to be fully reproducible using only public data sources and open-source software. All code will be archived with DOI upon publication.
