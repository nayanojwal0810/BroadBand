# County Broadband Availability and Household Subscription Analysis

This repository contains an end-to-end reproducible econometric study evaluating the relationship between provider-reported fixed broadband availability and household-reported wired broadband subscription across United States counties.

---

## 1. Research Question & Study Scope

### Approved Research Question
> **“How sensitive is the county-level relationship between reported fixed broadband availability and household-reported wired broadband subscription to the availability-speed definition, socioeconomic context, and ACS sampling uncertainty?”**

### Observational and Ecological Scope
This is strictly an **observational, county-level ecological study**. All units of observation and analysis are aggregate geographic entities (counties and county-equivalents).

- **No Causal Inference:** Cross-sectional regression associations cannot establish causal effects of infrastructure deployment on household adoption. Coefficients describe empirical ecological associations across geographic units.
- **Ecological Fallacy Caution:** County-level aggregates cannot be used to infer individual household decision-making or adoption behavior. The difference between aggregate provider availability and aggregate household subscription cannot be characterized as an individual-level "availability–adoption gap."

---

## 2. Data Sources & Raw File Requirements

Raw data files reside in `data/raw/` and are excluded from version control via `.gitignore`.

| Source / Agency | Dataset / Table | Speed Threshold / Variables | Geographic Level | Snapshot / Vintage | Expected Raw Filename |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **FCC Broadband Data Collection (BDC)** | Fixed Broadband Deployment (Total, Residential, All Wired) | $\ge 100$ Mbps DL / $20$ Mbps UL (`percent_coverage`) | County | As of Dec 30, 2025 | `bdc_comparison_fixed_county_total_all_wired_r_100_20_D25.csv` |
| **FCC Broadband Data Collection (BDC)** | Fixed Broadband Deployment (Total, Residential, All Wired) | $\ge 25$ Mbps DL / $3$ Mbps UL (`percent_coverage`) | County | As of Dec 30, 2025 | `bdc_comparison_fixed_county_total_all_wired_r_25_3_D25.csv` |
| **U.S. Census Bureau ACS** | 5-Year Estimates, Table B28002 | `B28002_001E` (Total Households), `B28002_007E` (Broadband: Cable, Fiber, DSL) | County | 2020–2024 (Released Dec 2025) | `acs_b28002_2024_county.json` |
| **U.S. Census Bureau ACS** | 5-Year Estimates, Tables S1701 & S1501 | `S1701_C03_001E` (Poverty Rate %), `S1501_C02_015E` (Bachelor's Degree+ %) | County | 2020–2024 (Released Dec 2025) | `acs_context_2024_county.json` |

### Temporal Mismatch Disclosure
FCC BDC data represents a point-in-time infrastructure snapshot as of December 30, 2025. ACS data represents 5-year survey estimates pooled over the 2020–2024 period. Because broadband deployment expanded rapidly between 2020 and 2025, availability estimates represent recent infrastructure conditions, whereas ACS adoption estimates reflect multi-year pooled household adoption. This cross-sectional observational mismatch is acknowledged as a structural feature of public data releases.

### How to Obtain and Place Raw Data
1. Create directory `data/raw/` in the repository root if it does not already exist:
   ```bash
   mkdir -p data/raw
   ```
2. Place the four validated source files into `data/raw/` using the exact filenames listed above.
3. Verify file presence and schema integrity by running `python scripts/validate_feasibility.py`.

---

## 3. Sample Definitions & Geographic Rules

### Primary Sample ($N = 3,135$ Counties)
The primary analytical sample consists of **3,135 matched county-equivalent entities** across the 49 continental states, Alaska, Hawaii, and the District of Columbia.

- **Connecticut Exclusion (8 Legacy Counties Excluded):** In 2022, the Census Bureau replaced Connecticut's 8 legacy counties with 9 Planning Regions. The FCC Dec 30, 2025 data export retains the 8 legacy county FIPS codes. Because no approved crosswalk or geographic bridging can be performed without introducing measurement error, Connecticut is excluded from the primary sample.
- **Puerto Rico Exclusion from Primary ($78$ Municipios):** Puerto Rico is excluded from the primary sample to avoid severe cluster size asymmetry (a single territory cluster of 78 municipios). It is evaluated separately in a 3,213-observation sensitivity analysis with explicit disclosure of territory cluster limitations.

### Analytical Data Dictionary (`data/processed/county_broadband_analysis.csv`)

| Field Name | Type | Range / Format | Description | Source |
| :--- | :--- | :---: | :--- | :--- |
| `geography_id` | String | 5-digit FIPS | Unique 5-digit county FIPS code | Join Key |
| `geography_name` | String | Text | Legal county description | Census / FCC |
| `state_fips` | String | 2-digit FIPS | State FIPS code (Cluster variable) | Census |
| `state_abbr` | String | 2-letter | Postal state abbreviation | Derived |
| `is_primary_sample` | Integer | {0, 1} | 1 = Primary (49 States + DC, N=3,135); 0 = PR (N=78) | Analysis Rule |
| `subscription_rate_pct` | Float | [0.0, 100.0]% | Household wired broadband subscription rate | ACS B28002 |
| `subscription_rate_moe_pp` | Float | [0.5, 48.82] pp | Derived 90% margin of error | Census Ratio Formula |
| `subscription_rate_se_approx_pp` | Float | [0.3, 29.68] pp | Derived approximate standard error ($\text{MOE} / 1.645$) | Census Formula |
| `avail_100_20_10pp` | Float | [0.0, 10.0] | FCC $\ge 100/20$ Mbps availability in 10 pp increments | FCC BDC |
| `avail_25_3_10pp` | Float | [0.0, 10.0] | FCC $\ge 25/3$ Mbps availability in 10 pp increments | FCC BDC |
| `poverty_pct` | Float | [0.0, 100.0]% | Percent of population below poverty level | ACS S1701 |
| `bachelor_plus_pct` | Float | [0.0, 100.0]% | Percent of population 25+ with bachelor's degree+ | ACS S1501 |

---

## 4. Environment Setup & Pipeline Execution

### Prerequisites
- Python 3.10, 3.11, 3.12, or 3.13 (tested on Python 3.13.3)
- `pip` package manager

### Installation
```bash
git clone https://github.com/nayanojwal0810/BroadBand.git
cd BroadBand
pip install -r requirements.txt
```

### End-to-End Pipeline Commands
Execute scripts from the repository root in the following sequential order:

```bash
# 1. Validate raw data source integrity and feasibility
python scripts/validate_feasibility.py

# 2. Validate Phase 4 analysis plan variable construction and math feasibility
python scripts/validate_analysis_plan.py

# 3. Construct analysis dataset with exact 5-digit joins
python scripts/prepare_analysis_dataset.py

# 4. Generate descriptive statistics and exploratory figures (Figures 1-5)
python scripts/generate_descriptive_analysis.py

# 5. Run baseline OLS models, influence checks, and stacked contrast tests (Figures 6-9)
python scripts/run_baseline_analysis.py

# 6. Run ACS outcome-uncertainty propagation simulation (Figure 10)
python scripts/run_uncertainty_simulation.py
```

---

## 5. Script-to-Output Reproduction Matrix

| Script | Primary Function | Generated Deliverables |
| :--- | :--- | :--- |
| `scripts/validate_feasibility.py` | Audits raw inputs, verifies checksums, headers, and uncertainty math | `reports/project_feasibility_audit.json`<br>`reports/project_feasibility_audit.md` |
| `scripts/validate_analysis_plan.py` | Verifies variable construction rules and Beta feasibility constraints | `reports/analysis_plan_validation.json` |
| `scripts/prepare_analysis_dataset.py` | Joins sources on exact FIPS, computes derived fields, exports CSV | `data/processed/county_broadband_analysis.csv`<br>`reports/analysis_dataset_validation.json` |
| `scripts/generate_descriptive_analysis.py` | Calculates descriptive statistics and exploratory plots | `reports/descriptive_analysis.md`<br>`reports/figures/fig1_subscription_and_moe_distributions.png`<br>`reports/figures/fig2_fcc_availability_distributions.png`<br>`reports/figures/fig3_subscription_vs_availability_scatter.png`<br>`reports/figures/fig4_subscription_vs_socioeconomic_scatter.png`<br>`reports/figures/fig5_primary_vs_puerto_rico_comparison.png` |
| `scripts/run_baseline_analysis.py` | Estimates Models A1, A2, B1, B2, contrast tests, and leave-one-out diagnostics | `reports/baseline_model_results.json`<br>`reports/baseline_model_results.md`<br>`reports/figures/fig6_baseline_model_fit_and_residuals.png`<br>`reports/figures/fig7_baseline_coefficient_comparison.png`<br>`reports/figures/fig8_residual_qq_and_leverage.png`<br>`reports/figures/fig9_threshold_contrast_and_influence.png` |
| `scripts/run_uncertainty_simulation.py` | Propagates ACS sampling error via 1,000 Beta Monte Carlo replicates | `reports/uncertainty_simulation_results.json`<br>`reports/uncertainty_simulation_results.md`<br>`reports/figures/fig10_uncertainty_simulation_distributions.png` |

---

## 6. Key Empirical Findings

### Baseline OLS Models & Speed-Threshold Contrast
Models are estimated on the primary sample ($N = 3,135$ counties, $G = 50$ state clusters). Standard errors are cluster-robust at the state level with finite-sample degrees-of-freedom correction ($df = G - 1 = 49$).

| Model Specification | Availability Slope (pp / 10 pp avail) | State-Clustered SE | 95% Clustered CI | $R^2$ | RMSE (pp) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Model A1:** 100/20 Mbps Unadjusted | +3.8326 | 0.1995 | [+3.4316, +4.2335] | 0.3663 | 9.669 |
| **Model A2:** 100/20 Mbps Adjusted | **+2.9872** | 0.1468 | [+2.6923, +3.2821] | 0.5963 | 7.720 |
| **Model B1:** 25/3 Mbps Unadjusted | +4.4239 | 0.2080 | [+4.0058, +4.8419] | 0.3980 | 9.424 |
| **Model B2:** 25/3 Mbps Adjusted | **+3.4782** | 0.1741 | [+3.1284, +3.8281] | 0.6165 | 7.524 |

- **Socioeconomic Attenuation:** Adding poverty and education attenuates availability slopes by **-22.1%** for 100/20 Mbps and **-21.4%** for 25/3 Mbps, while increasing explained variance from ~37–40% to ~60–62%.
- **Formal Threshold Contrast ($H_0: \beta_B - \beta_A = 0$):**
  - Joint stacked bivariate OLS regression ($2N = 6,270$ stacked rows, $G = 50$ clusters) reproduces separate point estimates within machine precision ($< 10^{-14}$).
  - Slope Difference: **+0.4910 pp** per 10 pp availability increment
  - Cluster-Robust Standard Error: **0.0748**
  - 95% Clustered Confidence Interval: **[+0.3408, +0.6413]**
  - Test Statistic: **$t = 6.5660$** ($p = 3.12 \times 10^{-8}, df = 49$), rejecting slope equality.
- **Influence Sensitivity (Leave-One-Out):** Re-estimating adjusted models omitting each of the top 10 highest Cook's distance counties shifts availability coefficients by $< 1.0\%$ (maximum shift in Model A2 is $+0.0219\text{ pp}$ or $+0.73\%$; maximum shift in Model B2 is $+0.0317\text{ pp}$ or $+0.91\%$).

### ACS Outcome-Uncertainty Propagation Simulation
A 1,000-replicate Monte Carlo simulation (seed = `20261018`) was conducted using county-specific moment-matched Beta distributions:

| Scenario / Metric | Baseline Point Estimate | Monte Carlo Mean | Monte Carlo Median | Empirical 95% Bounds [2.5%, 97.5%] | Proportion > 0 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Model A2 Availability (100/20)** | 2.9872 pp | 2.9843 pp | 2.9849 pp | [2.9130, 3.0594] | 100.0% |
| **Model B2 Availability (25/3)** | 3.4782 pp | 3.4753 pp | 3.4742 pp | [3.3922, 3.5634] | 100.0% |
| **Threshold Difference ($\beta_B - \beta_A$)** | **+0.4910 pp** | **+0.4910 pp** | **+0.4908 pp** | **[+0.4713, +0.5115]** | **100.0%** |
| *Sensitivity: Loving County Point-Held* | +0.4910 pp | +0.4910 pp | +0.4909 pp | [+0.4712, +0.5108] | 100.0% |

- **Loving County, TX (`48301`):** With $y=27, x=23$, and $\text{MOE} = \pm 48.82\text{ pp}$, its moment-matched Beta distribution produces $\alpha \approx 0.3689$ and $\beta \approx 0.0642$, yielding a strictly U-shaped density. Holding its outcome at the observed point estimate in Sensitivity Scenario 2 produces identical findings, proving that its high-variance simulation does not distort aggregate results.

---

## 7. Methodological Limitations & Governance Disclosures

1. **Observational Bounds:** Models describe ecological geographic associations, not individual household adoption behavior or provider deployment decisions.
2. **Outcome Uncertainty Scope:** The Monte Carlo simulation propagates sampling uncertainty in the derived ACS dependent variable only. It does not model uncertainty in provider availability or socioeconomic controls.
3. **Replicate Weights:** This moment-matched Beta procedure is an analytical model-based approximation, not a replacement for Census Bureau design-based replicate-weight microdata inference.
4. **Deferred Methods:** The wild cluster bootstrap and weighted least squares (WLS) procedures remain formally marked as deferred.
