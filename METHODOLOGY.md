# Methodology and Threats to Validity

## Study Design

### Research Question

Does digital movement density (MDS) predict sales velocity (SV) for Broadway shows?

### Hypothesis

Higher engagement depth and persistence across social platforms (Instagram, TikTok, Reddit, Google Trends) is associated with faster and more durable box office performance.

### Approach

**Correlational study** using public data to test association between MDS and SV across 10 Broadway shows, aligned by relative timeline (weeks from opening).

## Measurement

### Independent Variable: Movement Density Score (MDS)

**Definition**: Composite z-scored metric of social engagement indicating depth and persistence.

**Components**:

1. **Instagram** (public profiles only):
   - Comments per post (depth)
   - Comment-to-like ratio (engagement quality)
   - Repeat commenter rate (persistence) *[currently placeholder due to API limits]*

2. **TikTok** (public hashtag data):
   - Weekly hashtag video count (volume)
   - UGC share (non-official creator fraction) (organic spread)
   - Sound usage count *[placeholder - requires API]*

3. **Reddit** (r/Broadway):
   - Weekly thread count mentioning show
   - Median comments per thread (discussion depth)
   - Repeat contributor rate (persistence)

4. **Google Trends**:
   - 4-week interest slope (momentum)
   - Volatility (std dev) - **negative weight** (stability)

**Standardization**: Each component is z-scored across all shows and weeks, then summed with equal weights (configurable).

**Alternative**: PCA-based MDS for sensitivity analysis.

### Dependent Variable: Sales Velocity (SV)

**Definition**: Composite metric of sales performance using public proxies.

**Components**:

1. **BroadwayWorld Grosses** (when available):
   - Weekly grosses slope (4-week rolling)
   - Weekly attendance slope

2. **Ticket Prices** (SeatGeek/TodayTix):
   - Minimum price slope (higher = stronger demand)
   - Average price slope

3. **Availability** (SeatGeek/TodayTix):
   - Listings count slope - **negative weight** (more listings = weaker demand)

4. **Discounts** (BroadwayBox):
   - Discount count slope - **negative weight** (more discounts = weaker demand)

**Standardization**: Each slope is z-scored, then summed with configured weights.

**Limitation**: These are **proxies**, not actual ticket sales. BroadwayWorld grosses are self-reported and may be delayed or missing.

### Timeline Alignment

Each show's data is aligned to **relative weeks from opening**:
- Week 0 = opening week (or first preview if opening not available)
- Week -4 to -1 = pre-opening
- Week 1 to 12 = post-opening

This controls for seasonality and allows comparison across shows with different opening dates.

## Statistical Tests

### 1. Correlation Analysis

**Pearson r**: Linear association between MDS and SV

**Spearman ρ**: Rank-order association (robust to non-linearity)

**Null Hypothesis**: No correlation (r = 0)

### 2. OLS Regression

**Model**:
```
SV_it = β₀ + β₁ * MDS_it + α_i + γ_t + ε_it
```

Where:
- i = show
- t = relative week
- α_i = show fixed effects (control for show-specific factors)
- γ_t = week fixed effects (control for time trends)
- ε_it = error term

**Coefficient of Interest**: β₁ (MDS effect on SV, controlling for fixed effects)

**Standard Errors**: Heteroskedasticity-robust

### 3. Lead-Lag Analysis

**Test**: Does MDS(t) predict SV(t+L) for L ∈ {1, 2, 3, 4} weeks?

**Method**: Shift SV forward by L weeks, compute correlation with MDS(t)

**Interpretation**: Positive correlation at lag L suggests MDS has **predictive power** L weeks ahead.

### 4. Robustness Tests

1. **Exclude Tony weeks**: Drop weeks 8-10 (Tony nominations/awards period) to test whether results are driven by industry events
2. **Cohort-specific**: Test correlation within CMM cohort and Broad Appeal cohort separately
3. **PCA-based MDS**: Replace equal-weighted MDS with first principal component to test sensitivity to weighting

## Threats to Validity

### Internal Validity (Confounds)

**Problem**: Correlation ≠ Causation. Many factors affect both MDS and SV.

**Major Confounds**:

1. **Marketing Spend**: Paid advertising drives both social engagement and ticket sales
   - *Partial control*: Show fixed effects capture average marketing budgets
   - *Residual confound*: Time-varying marketing spend within show

2. **Critical Reviews**: Positive reviews drive both word-of-mouth and sales
   - *No control*: Review data not collected
   - *Threat level*: High (reviews typically release around opening week)

3. **Star Power**: Celebrity casting drives both social buzz and ticket demand
   - *Partial control*: Show fixed effects
   - *Residual confound*: Cast changes during run

4. **Tony Nominations/Awards**: Industry recognition creates spikes in both metrics
   - *Control*: Robustness test excludes Tony weeks
   - *Limitation*: Exact nomination dates vary by show

5. **Quality of Show**: Better shows generate both organic engagement and repeat sales
   - *No control*: Quality is endogenous
   - *Interpretation*: MDS may be a **proxy** for quality, not independent driver

6. **Seasonality**: Tourist season affects both social activity and ticket sales
   - *Control*: Week fixed effects capture average seasonal patterns
   - *Limitation*: Show-specific seasonal variation not captured

**Conclusion**: This is a **correlational study**. We can test association and predictive power, but **cannot establish causation** without experimental or quasi-experimental design.

### External Validity (Generalizability)

**Problem**: Can results generalize beyond these 10 shows?

**Threats**:

1. **Selection Bias**: Shows chosen based on hypothesis (CMM vs Broad Appeal)
   - Not a random sample of Broadway shows
   - May overstate effect if selection is on dependent variable

2. **Time Period**: Data collected 2015-2025
   - Social media landscape evolving rapidly
   - Results may not generalize to earlier or later periods

3. **Genre Bias**: Sample skews toward musicals
   - Musicals may have different social/sales dynamics than plays
   - Results may not apply to straight plays

4. **Success Bias**: Many shows in sample are hits (Hamilton, Six, Hadestown)
   - Limited variation in SV for hits (ceiling effect)
   - May underestimate MDS-SV relationship for struggling shows

**Conclusion**: Results are **exploratory** and should be validated on larger, more representative samples.

### Measurement Validity (Construct Validity)

**Problem**: Do MDS and SV measure what we claim?

**MDS Validity**:

- **Construct**: "Depth and persistence of digital engagement"
- **Operationalization**: Comments, UGC share, repeat contributors, trends slope
- **Threats**:
  - Instagram/TikTok public data may not capture authentic engagement (bots, paid promotion)
  - Repeat commenter rate is **placeholder** (requires comment-level user IDs)
  - Sound usage count is **placeholder** (requires TikTok API)
  - Reddit r/Broadway may not represent broader audience (self-selected theater fans)

**SV Validity**:

- **Construct**: "Speed and durability of sales performance"
- **Operationalization**: Grosses/attendance slopes, price slopes, discount slopes
- **Threats**:
  - **Not actual ticket sales** - BroadwayWorld grosses are self-reported and may be missing/delayed
  - Price and availability from secondary market (SeatGeek) may not reflect primary sales
  - Discount availability (BroadwayBox) is binary presence, not magnitude
  - Grosses affected by ticket pricing strategy, not just demand
  - Attendance affected by theater capacity, not just demand

**Alternative Metrics**:
- Ideal: Daily ticket sales from Telecharge/Ticketmaster (not publicly available)
- Better proxies: TKTS booth data, Google search volume for "buy [show] tickets"

### Statistical Conclusion Validity

**Problem**: Can we trust the statistical inferences?

**Threats**:

1. **Small Sample**: N=10 shows, varying observations per show
   - Low statistical power to detect effects
   - Large standard errors
   - Risk of Type II error (false negative)

2. **Missing Data**: Instagram/TikTok scrapers may fail to extract data
   - Non-random missingness (missing if show has low engagement)
   - May bias estimates

3. **Non-Independence**: Observations within show are serially correlated
   - OLS standard errors may be understated
   - Should use clustered standard errors (not currently implemented)

4. **Non-Normality**: MDS and SV distributions may be skewed
   - Spearman correlation more robust than Pearson
   - OLS sensitive to outliers

5. **Specification Error**: Linear model may be misspecified
   - Relationship may be non-linear (e.g., threshold effects)
   - Interaction effects not tested (MDS × cohort, MDS × week)

**Mitigation**:
- Report both Pearson and Spearman
- Use robust standard errors in OLS
- Run robustness tests (cohort-specific, excluding outliers)

## Data Provenance and Reproducibility

### Data Collection

**Sources**: All public websites with HTTP GET requests

**Caching**: All responses cached locally for 7 days with MD5 hash keys

**Rate Limiting**: Conservative delays (0.5-2 sec per request) to respect ToS

**Timestamps**: All cached data includes timestamp for auditability

**Robots.txt**: Compliance verified for each domain

### Processing

**Determinism**: No random operations (except optional PCA, which uses fixed seed)

**Versioning**: Package versions pinned in requirements.txt

**Logging**: All warnings and errors logged to console

**Transparency**: All code is open-source with type hints and docstrings

### Reproducibility Challenges

1. **Dynamic Websites**: Instagram/TikTok HTML structure changes frequently
   - Scrapers may break without notice
   - Cached data allows partial reproducibility

2. **Platform Restrictions**: Instagram/TikTok increasingly require authentication
   - Public data availability decreasing over time
   - Results from 2025 may not be reproducible in 2026

3. **Deleted Content**: Social media posts may be deleted
   - Historical data not recoverable if not cached
   - Longitudinal studies difficult

4. **API Rate Limits**: Google Trends rate limits may cause failures
   - Retry logic implemented
   - May still fail under heavy load

**Best Practice**: Clone repository and run immediately. Re-running months later may yield different results due to platform changes.

## Alternative Explanations

### If MDS and SV are positively correlated, possible explanations:

1. **MDS causes SV** (CMM thesis): Organic engagement drives word-of-mouth → sales
   - **Test**: Lead-lag analysis (does MDS predict future SV?)
   - **Evidence needed**: Correlation at t+1..t+4 weeks

2. **SV causes MDS** (reverse causality): High sales → more buzz
   - **Test**: Reverse lead-lag (does SV predict future MDS?)
   - **Not currently implemented**

3. **Common cause** (confound Z causes both): Marketing, quality, reviews
   - **Test**: Control for observables (marketing spend, reviews)
   - **Limitation**: Data not collected

4. **Spurious correlation**: No causal relationship, just coincidence
   - **Test**: Robustness checks, larger sample
   - **Mitigation**: Theory-driven hypothesis reduces risk

### If MDS and SV are **not** correlated:

1. **Social metrics don't predict sales**: CMM thesis is wrong for Broadway
2. **Measurement error**: MDS/SV constructs poorly operationalized
3. **Insufficient power**: True effect exists but sample too small to detect
4. **Non-linear relationship**: Effect exists but not captured by linear correlation

## Recommendations for Future Research

1. **Larger Sample**: Collect data for all Broadway shows (not just 10)
2. **Better Sales Data**: Partner with ticketing platforms for actual sales
3. **Control Variables**: Collect marketing spend, review scores, cast star power
4. **Quasi-Experimental Design**: Natural experiments (e.g., sudden cast changes, social media blackouts)
5. **Longitudinal**: Track shows from pre-production through closing
6. **Mechanism Tests**: Survey audiences to measure word-of-mouth transmission

## Conclusion

This study provides **exploratory correlational evidence** on the MDS-SV relationship. Results should be interpreted as association, not causation. Findings are subject to confounding, measurement error, and limited generalizability. Robustness tests and lead-lag analysis strengthen causal inference, but **experimental validation is needed** to establish CMM thesis definitively.

---

**Document Version**: 1.0

**Last Updated**: 2025-01-11
