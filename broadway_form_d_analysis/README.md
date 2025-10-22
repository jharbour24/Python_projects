# Broadway Form D Analysis (2010-2025)

Comprehensive quantitative analysis of SEC Form D filings related to Broadway and commercial theatrical productions from January 1, 2010 through December 31, 2025.

## 📋 Project Overview

This project conducts a **data-driven, quantitative analysis** of Broadway theatrical production financing through SEC Form D filings. The analysis focuses exclusively on financial and structural patterns — not qualitative reporting or external articles.

### Objectives

- Retrieve all Form D filings from SEC EDGAR related to Broadway/theatrical productions
- Extract detailed financial, structural, and investor data from each filing
- Perform comprehensive quantitative analyses to identify trends and patterns
- Generate visualizations and statistical insights
- Track the evolution of Broadway financing from 2010-2025

## 🎯 Scope

### Data Collection Criteria

**Inclusion Filters:**
- Issuers with names/descriptions containing: Broadway, theatrical, theatre, musical, play, production, show, stage
- Offerings under **Rule 506(b)** or **Rule 506(c)** of Regulation D
- Industries: Theatrical production, Entertainment, Arts & Culture
- NAICS Code: 711110 (Theatre companies and dinner theatres)

**Data Fields Extracted (per filing):**
- Entity/Show name and identification
- Filing and amendment dates
- Industry classification (NAICS code)
- Financial metrics (offering amount, amount sold, remaining)
- Investor data (count, accredited status, minimum investment)
- Securities types (equity, debt, partnership interests)
- Exemption rules claimed
- Geographic data (jurisdiction, principal place of business)
- Officer/management information
- Broker/intermediary details

## 📊 Analysis Modules

The analysis pipeline performs seven core quantitative analyses:

### 1. **Capitalization Trends**
- Annual offering size statistics (mean, median, range)
- Top 10 largest offerings by year and overall
- Musical vs. play offering comparisons
- Year-over-year growth rates

### 2. **Investor Base Evolution**
- Average investor counts per filing over time
- Minimum investment threshold trends
- Non-accredited investor participation rates
- Democratization of theatrical investment

### 3. **Post-COVID Shifts (2020-2025)**
- Pre/post COVID comparative analysis
- Changes in offering amounts and structures
- Rule 506(c) adoption rates (general solicitation)
- Offering duration and timeline patterns

### 4. **Structural Patterns**
- Recurring production entities and management groups
- Entity type distribution (LLC, LP, Corporation)
- Amendment frequency and timing
- Securities type preferences

### 5. **Geographic and Legal Trends**
- Jurisdiction of incorporation analysis
- State-by-state offering patterns
- Exemption rule usage by geography
- Principal place of business concentrations

### 6. **Comparative Benchmarks**
- Industry benchmark metrics
- Quartile analysis of offering sizes
- Offering utilization rates
- Statistical distributions

### 7. **Outlier Detection**
- Extreme offerings (>$50M)
- Unusually high investor counts
- Micro-investment offerings
- Major show cross-references (Hamilton, Wicked, Lion King, etc.)

## 🗂️ Project Structure

```
broadway_form_d_analysis/
├── data/
│   ├── raw/                    # Raw SEC EDGAR data
│   └── processed/              # Cleaned, parsed CSV data
│       └── broadway_form_d_2010_2025.csv
├── analysis/
│   └── analysis_results.json   # Quantitative analysis output
├── visuals/
│   ├── annual_offering_trends.png
│   ├── investor_trends.png
│   ├── covid_impact_comparison.png
│   ├── geographic_distribution.png
│   ├── securities_and_exemptions.png
│   ├── correlation_matrix.png
│   └── offering_size_distribution.png
├── scripts/
│   ├── sec_edgar_retriever.py      # SEC EDGAR data retrieval
│   ├── form_d_parser.py            # XML/JSON Form D parser
│   ├── collect_form_d_data.py      # Integrated data collection
│   ├── analyze_form_d_data.py      # Quantitative analysis engine
│   ├── visualize_form_d_data.py    # Visualization generation
│   ├── generate_sample_data.py     # Sample data generator
│   └── run_full_analysis.py        # Main orchestration script
├── requirements.txt
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Internet connection (for live SEC EDGAR data collection)

### Installation

```bash
# Clone or navigate to project directory
cd broadway_form_d_analysis

# Install dependencies
pip install -r requirements.txt
```

### Usage

#### Option 1: Run with Sample Data (Recommended for Testing)

```bash
python scripts/run_full_analysis.py --sample
```

This generates 200 realistic sample Form D filings and runs the complete analysis pipeline.

#### Option 2: Collect Live SEC EDGAR Data

```bash
python scripts/run_full_analysis.py --live
```

**Warning:** Live data collection:
- Requires internet access
- Must comply with SEC rate limits (10 requests/second)
- May take several hours for 15+ years of data
- Requires proper User-Agent header

#### Custom Sample Size

```bash
python scripts/run_full_analysis.py --sample --num-samples 500
```

### Running Individual Components

```bash
# Generate sample data only
python scripts/generate_sample_data.py

# Run analysis only (requires existing data file)
python scripts/analyze_form_d_data.py

# Generate visualizations only
python scripts/visualize_form_d_data.py
```

## 📈 Output Deliverables

### 1. Master Dataset
**File:** `data/processed/broadway_form_d_2010_2025.csv`

Structured CSV with one row per Form D filing containing all extracted fields.

### 2. Analysis Results
**File:** `analysis/analysis_results.json`

Comprehensive JSON containing:
- Annual statistics and trends
- Pre/post COVID comparisons
- Geographic distributions
- Outlier detection results
- 3-5 key insights with quantified findings

### 3. Visualizations
**Directory:** `visuals/`

Seven comprehensive chart sets:
1. Annual offering trends (4 panels)
2. Investor base evolution (4 panels)
3. COVID impact comparison (4 panels)
4. Geographic distribution (4 panels)
5. Securities & exemptions (4 panels)
6. Correlation matrix (heatmap)
7. Offering size distribution (histograms, box plots)

All visualizations saved as high-resolution PNG (300 DPI).

## 📊 Key Findings (Sample Data Example)

When run with sample data, the analysis typically reveals:

1. **Capital Market Scale**: Total capital raised through Form D filings across Broadway productions
2. **Post-COVID Changes**: Shifts in average offering sizes and investor participation after 2020
3. **Democratization**: Trends in minimum investment thresholds over time
4. **Regulatory Preferences**: Rule 506(b) vs 506(c) adoption rates
5. **Geographic Concentration**: Delaware, New York, and California incorporation patterns

## 🛠️ Technical Implementation

### Data Collection
- **SEC EDGAR API**: Full-text search and daily index files
- **Rate Limiting**: 0.1 second delays (10 req/sec compliance)
- **Filtering**: Multi-pattern matching for theatrical productions
- **Parsing**: XML extraction with ElementTree

### Analysis Engine
- **Statistical Methods**: Pandas aggregations, quartile analysis, correlation matrices
- **Temporal Analysis**: Year-over-year growth, pre/post period comparisons
- **Classification**: Entity type categorization, show type inference
- **Outlier Detection**: Percentile-based thresholds

### Visualization
- **Libraries**: Matplotlib, Seaborn
- **Chart Types**: Time series, bar charts, box plots, histograms, heatmaps, pie charts
- **Styling**: Clean, publication-ready aesthetic

## 📝 Data Dictionary

### Core Financial Fields
- `total_offering_amount`: Maximum securities to be sold ($)
- `total_amount_sold`: Securities sold to date ($)
- `total_remaining`: Remaining securities available ($)
- `offering_utilization`: Percentage of offering sold (%)

### Investor Fields
- `total_number_of_investors`: Count of current investors
- `has_non_accredited_investors`: Boolean indicator
- `minimum_investment`: Minimum accepted investment amount ($)

### Legal/Structural Fields
- `rule_506b`: Reg D 506(b) exemption (no general solicitation)
- `rule_506c`: Reg D 506(c) exemption (general solicitation allowed)
- `entity_type`: LLC, LP, Corporation, etc.
- `jurisdiction_of_incorporation`: State/country code

### Temporal Fields
- `filing_date`: SEC submission date
- `offering_date`: First sale date
- `is_amendment`: Amendment vs. initial filing

## 🔍 SEC EDGAR Resources

- **EDGAR Search**: https://www.sec.gov/edgar/searchedgar/companysearch.html
- **Form D Information**: https://www.sec.gov/files/formd.pdf
- **Regulation D**: https://www.sec.gov/smallbusiness/exemptofferings/rule506b
- **EDGAR API Documentation**: https://www.sec.gov/edgar/sec-api-documentation

## ⚠️ Legal and Compliance Notes

- This project is for **research and analysis purposes only**
- All data is publicly available through SEC EDGAR
- Must comply with SEC's fair access policy (rate limits)
- User-Agent headers required for SEC requests
- No proprietary or non-public data is collected

## 🤝 Contributing

This is a research project. Suggested improvements:

1. **Enhanced Show Matching**: Integrate IBDB (Internet Broadway Database) API
2. **Natural Language Processing**: Extract show descriptions from filing narratives
3. **Network Analysis**: Map producer/investor networks
4. **Predictive Modeling**: Success indicators based on offering structure
5. **Real-time Monitoring**: Alert system for new Broadway Form D filings

## 📚 References

### Regulatory Framework
- Securities Act of 1933, Regulation D
- Form D: Notice of Exempt Offering of Securities (SEC)
- Rule 506(b) and 506(c): Private placement exemptions

### Industry Context
- Broadway League: https://www.broadwayleague.com
- Playbill: https://www.playbill.com
- Internet Broadway Database (IBDB): https://www.ibdb.com

## 📄 License

This project analyzes publicly available SEC data. No license restrictions apply to the data itself. Code is provided for educational and research purposes.

## 🔗 Contact

For questions about methodology, data sources, or findings:
- Review the analysis results JSON for detailed statistics
- Check visualization outputs for graphical insights
- Examine the master CSV dataset for raw data

---

**Last Updated:** 2025-10-22
**Analysis Period:** 2010-01-01 to 2025-12-31
**Total Filings:** Variable (depends on collection parameters)
