# Phase 4 Analysis Plan: County-Level Fixed Broadband Availability and Household Subscription

**Document Version:** 1.3
**Date:** October 18, 2026
**Status:** Baseline OLS, Diagnostics, Threshold Contrast & ACS Outcome-Uncertainty Propagation Complete; Wild Cluster Bootstrap Deferred
**Repository:** `nayanojwal0810/BroadBand`
**Study Scope:** Observational County-Level Ecological Study

---

## 1. Approved Research Question

> **“How sensitive is the county-level relationship between reported fixed broadband availability and household-reported wired broadband subscription to the availability-speed definition, socioeconomic context, and ACS sampling uncertainty?”**

### Observational and Ecological Scope
This research is strictly an **observational, county-level ecological study**. All units of observation and analysis are aggregate geographic entities (counties and county-equivalents). 

- **No Causal Inference:** Cross-sectional regression associations cannot establish causal effects of broadband availability on household subscription.
- **Ecological Fallacy Caution:** County-level aggregates cannot be used to infer individual household decision-making or adoption behavior. The difference between aggregate provider availability and aggregate household subscription cannot be characterized as an individual-level "availability–adoption gap."

---

## 2. Study Population and Geographic Boundaries

### Inclusion and Exclusion Rules
The geographic scope is established using exact 5-digit Federal Information Processing Standard (FIPS) county codes common to the FCC Broadband Data Collection (BDC) Area Comparison exports and the 2024 U.S. Census American Community Survey (ACS) 5-Year Estimates.

1. **Primary Study Sample ($N = 3,135$ counties):**
   - Covers 49 U.S. states plus Washington, DC.
   - **Excludes Connecticut (FIPS prefix `09`):** In 2022/2024, the Census Bureau transitioned Connecticut county geography to 9 Planning Regions (`09110`–`09190`), whereas the FCC Area Comparison exports retain Connecticut's 8 legacy historical counties (`09001`–`09015`). There are **0 exact FIPS matches** between the two systems. In accordance with Gate Zero and Phase 3 methodological policy, **no ad hoc crosswalk is created**, and Connecticut is completely excluded from the primary sample.
   - **Excludes Puerto Rico (FIPS prefix `72`):** Held out for explicit sensitivity evaluation.
   - **Excludes Island Territories:** 13 FCC-only records corresponding to American Samoa (`60`), Guam (`66`), Northern Mariana Islands (`69`), and the U.S. Virgin Islands (`78`) are excluded because standard 5-year ACS detailed and subject tables (B28002, S1701, S1501) are not published for these jurisdictions.

2. **Puerto Rico Sensitivity Sample ($N = 3,213$ counties):**
   - Comprises the 3,135 primary counties plus Puerto Rico's 78 municipios (`72001`–`72153`).
   - All 78 Puerto Rico municipios match exactly across FCC and Census source files.
   - Evaluated as a separate robustness sample to determine whether insular telecommunications infrastructure and macroeconomic context alter the estimated availability–subscription relationship.

### Geographic Sample Summary Table

| Geographic Subsample | Inclusion Criteria | Exclusions | Sample Size ($N$) | Analytical Role |
| :--- | :--- | :--- | :---: | :--- |
| **Primary Sample** | 49 States + Washington, DC | CT (`09`), PR (`72`), Island Territories | **3,135** | Primary OLS regression models (Models A & B) |
| **Puerto Rico Sensitivity Sample** | Primary Sample + Puerto Rico (78 municipios) | CT (`09`), Island Territories | **3,213** | Geographic robustness check |
| **Connecticut Records** | Legacy counties in FCC; Planning Regions in ACS | Exact FIPS join impossible | 0 joined (8 FCC, 9 ACS) | Excluded (no ad hoc crosswalk) |
| **Island Territories** | FCC BDC comparison file | Standard ACS tables unavailable | 0 joined (13 FCC, 0 ACS) | Excluded from merged dataset |

---

## 3. Outcome, Predictors, and Socioeconomic Controls

All variables are derived from validated raw files stored under `data/raw/`. No transformations alter raw source records.

### Outcome Variable
- **Construct:** Estimated household-reported wired broadband subscription rate.
- **Source:** U.S. Census Bureau, 2024 ACS 5-Year Detailed Table B28002 (`data/raw/acs_b28002_2024_county.json`).
- **Mathematical Definition:**
  $$\text{subscription\_rate\_pct}_i = 100 \times \frac{\text{B28002\_007E}_i}{\text{B28002\_001E}_i}$$
  - $\text{B28002\_007E}$: Estimate of households with broadband such as cable, fiber optic, or DSL.
  - $\text{B28002\_001E}$: Estimate of total households.
- **Scale:** Continuous percentage in $[0, 100]\%$.
- **Interpretation:** The proportion of households in county $i$ that report having a wired broadband internet subscription, expressed on a percentage scale.

### Key Predictor Variables (Dual Speed Thresholds)
- **Model A Predictor (100/20 Mbps Baseline):**
  - **Source:** FCC National Broadband Map Area Comparison export (`data/raw/bdc_comparison_fixed_county_total_all_wired_r_100_20_D25.csv`).
  - **Definition:** Reported percentage of residential units with fixed all-wired broadband availability at $\ge 100$ Mbps download / $\ge 20$ Mbps upload as of December 30, 2025:
    $$\text{avail\_100\_20\_pct}_i = 100 \times \text{percent\_coverage}_i$$
- **Model B Predictor (25/3 Mbps Alternate Threshold):**
  - **Source:** FCC National Broadband Map Area Comparison export (`data/raw/bdc_comparison_fixed_county_total_all_wired_r_25_3_D25.csv`).
  - **Definition:** Reported percentage of residential units with fixed all-wired broadband availability at $\ge 25$ Mbps download / $\ge 3$ Mbps upload as of December 30, 2025:
    $$\text{avail\_25\_3\_pct}_i = 100 \times \text{percent\_coverage}_i$$
- **Interpretation:** These predictors represent provider-reported facility deployment across Broadband Serviceable Locations (BSLs) at specific technological speed benchmarks. They do **not** measure household physical connectivity, actual speed delivered, or service affordability.

### Pre-Specified Socioeconomic Controls
Derived from the official 2024 ACS 5-Year Subject Tables (`data/raw/acs_context_2024_county.json`):

1. **Poverty Percentage (`poverty_pct`):**
   - **Census Variable:** `S1701_C03_001E`
   - **Official Census Label:** `Estimate!!Percent below poverty level!!Population for whom poverty status is determined`
   - **Scale:** Continuous percentage in $[0, 100]\%$.
2. **Educational Attainment Percentage (`bachelor_plus_pct`):**
   - **Census Variable:** `S1501_C02_015E`
   - **Official Census Label:** `Estimate!!Percent!!AGE BY EDUCATIONAL ATTAINMENT!!Population 25 years and over!!Bachelor's degree or higher`
   - **Scale:** Continuous percentage in $[0, 100]\%$.

### Variable Documentation & Unit Scaling Summary

| Analysis Variable | Description | Source Field | Source File | Native Format | Analysis Scale |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `subscription_rate_pct` | Wired broadband subscription rate | `B28002_007E / B28002_001E` | `acs_b28002_2024_county.json` | Integer counts | $[0, 100]\%$ |
| `avail_100_20_pct` | Reported wired availability $\ge 100/20$ | `percent_coverage` | `bdc_comparison_..._100_20_D25.csv` | Float $[0, 1]$ | $[0, 100]\%$ |
| `avail_25_3_pct` | Reported wired availability $\ge 25/3$ | `percent_coverage` | `bdc_comparison_..._25_3_D25.csv` | Float $[0, 1]$ | $[0, 100]\%$ |
| `avail_100_20_10pp` | 100/20 availability in 10 pp increments | `percent_coverage * 10` | Derived | Scaled | 10 pp units |
| `avail_25_3_10pp` | 25/3 availability in 10 pp increments | `percent_coverage * 10` | Derived | Scaled | 10 pp units |
| `poverty_pct` | Individuals below poverty line | `S1701_C03_001E` | `acs_context_2024_county.json` | Float percent | $[0, 100]\%$ |
| `bachelor_plus_pct` | Adults 25+ with Bachelor's degree+ | `S1501_C02_015E` | `acs_context_2024_county.json` | Float percent | $[0, 100]\%$ |

---

## 4. Econometric Model Specifications & Inference Plan

### OLS Regression Equations
To evaluate how sensitive the availability–subscription association is to the availability threshold, we estimate two parallel multivariable Ordinary Least Squares (OLS) models on the identical primary sample ($N = 3,135$):

$$\textbf{Model A (100/20 Benchmark):} \quad \text{subscription\_rate\_pct}_i = \alpha_A + \beta_A \, \text{avail\_100\_20\_10pp}_i + \gamma_1 \, \text{poverty\_pct}_i + \gamma_2 \, \text{bachelor\_plus\_pct}_i + \varepsilon_{A,i}$$

$$\textbf{Model B (25/3 Alternate Threshold):} \quad \text{subscription\_rate\_pct}_i = \alpha_B + \beta_B \, \text{avail\_25\_3\_10pp}_i + \delta_1 \, \text{poverty\_pct}_i + \delta_2 \, \text{bachelor\_plus\_pct}_i + \varepsilon_{B,i}$$

### Regressor Scaling Convention
Availability is scaled in **10-percentage-point increments**:
$$\text{avail\_100\_20\_10pp}_i = \frac{\text{avail\_100\_20\_pct}_i}{10} = 10 \times \text{percent\_coverage}_i$$
$$\text{avail\_25\_3\_10pp}_i = \frac{\text{avail\_25\_3\_pct}_i}{10} = 10 \times \text{percent\_coverage}_i$$

**Coefficient Interpretation:** $\beta_A$ (or $\beta_B$) directly represents the estimated change in county household subscription percentage points associated with a 10-percentage-point increase in reported availability, holding poverty and educational attainment constant.

### Primary Inference & Variance Estimation
1. **Primary Inference: State-Clustered Standard Errors with Finite-Sample Correction:**
   - Standard errors are clustered at the state level (FIPS 2-digit prefix, $G = 50$ clusters in primary sample: 49 states + DC).
   - Clustering accounts for arbitrary intra-state residual correlation arising from state broadband grant programs, state regulatory regimes, and unobserved state-level policies.
   - Applies the standard degrees-of-freedom finite-sample adjustment factor:
     $$c = \frac{G}{G - 1} \times \frac{N - 1}{N - K}$$
     where $G = 50$, $N = 3,135$, and $K = 4$ (intercept, availability, poverty, education).
2. **Heteroskedasticity Sensitivity Diagnostic: HC3 Robust Standard Errors:**
   - MacKinnon & White (1985) heteroskedasticity-consistent (HC3) standard errors will be computed alongside clustered errors to diagnose influential observations and county-level variance heterogeneity.

3. **Cluster-Robust Diagnostic: Wild Cluster Bootstrap Specification & Local Readiness:**
   - **Methodological Purpose:** To assess whether cluster-size asymmetry across the 50 state clusters (e.g. Texas with 254 counties vs. Delaware with 3 counties) distorts cluster-robust asymptotic inference.
   - **Proposed Bootstrap Specification:**
     - **Proposed Variant:** **WCR11** (Restricted Wild Cluster Bootstrap with standard $HC_1$-type clustered degrees-of-freedom correction; Cameron, Gelbach, & Miller 2008; MacKinnon & Webb 2017).
     - **Null Hypothesis Imposed:** $H_0: \beta = 0$ on the availability coefficient.
     - **Auxiliary Weight Distribution:** Webb (2013) 6-point distribution $\left\{ -\sqrt{3/2}, -1, -\sqrt{1/2}, \sqrt{1/2}, 1, \sqrt{3/2} \right\}$, which offers superior finite-sample and cluster-asymmetry properties relative to standard 2-point Rademacher weights.
     - **Replication Count:** $B = 999$ iterations.
     - **Reproducibility Seed:** `20261018`.
     - **Confidence Interval Method:** Test inversion across candidate null values (numerical root-finding / grid search) to determine the 95% confidence set, alongside the bootstrap $p$-value for $H_0: \beta = 0$.
     - **Alternative Variants Flagged for Review:** If test inversion is computationally demanding or implementation-limited, an unrestricted wild cluster bootstrap (**WCU11**) with a percentile-$t$ confidence interval or a Wald-type bootstrap standard error could be substituted. This choice is explicitly flagged for ChatGPT review rather than guessed.
   - **Local Environment Inspection Findings:**
     - **R / Rscript:** `NOT AVAILABLE` in system PATH.
     - **`fwildclusterboot` (R):** `NOT INSTALLED / UNAVAILABLE`.
     - **`wildboottest` (Python):** `NOT INSTALLED`.
     - **Core Scientific Python:** `numpy`, `scipy`, `statsmodels`, `pandas` are `AVAILABLE`.
     - **Local Implementation Readiness Status:** **`REVIEW`**. In accordance with instructions, because execution has not been verified in an installed, published package locally, readiness is marked `REVIEW` rather than `PASS`. No packages will be installed or calculations run without explicit authorization.

4. **Side-by-Side Comparison Protocol:**
   - Present Model A and Model B in a unified comparative table.
   - **Cautionary Guideline:** A numerical difference between $\hat{\beta}_A$ and $\hat{\beta}_B$ does not automatically imply a statistically or substantively meaningful difference. Formal comparison must consider sampling variability, parameter overlap, and the observational nature of the estimates.

### Puerto Rico Cluster Handling
When estimating the Puerto Rico sensitivity sample ($N = 3,213$):
- Puerto Rico municipios (`72`) are treated as their own discrete geographic cluster (Cluster 51), rather than arbitrarily merged into any state cluster.
- **Methodological Limitation:** Adding a single cluster containing 78 observations introduces cluster-size asymmetry. Cluster-robust variance estimators may exhibit small-sample distortion when cluster sizes vary widely.

---

## 5. ACS Sampling Uncertainty & Beta Moment-Matched Simulation

### Analytical Margin of Error Approximation
Summary table B28002 publishes point estimates and margins of error without replicate weights. Following official Census Bureau guidance (ACS General Handbook, Chapter 8), the 90% margin of error for a derived proportion is calculated as:

$$\mathrm{MOE}(P_i) = \frac{1}{Y_i} \sqrt{\mathrm{MOE}(X_i)^2 - P_i^2 \cdot \mathrm{MOE}(Y_i)^2}$$
where $X_i = \text{B28002\_007E}$, $Y_i = \text{B28002\_001E}$, and $P_i = X_i / Y_i$.

- **Percentage Points Conversion:**
  $$\mathrm{MOE}_{\text{pp}, i} = 100 \times \mathrm{MOE}(P_i)$$
- **Ratio-Form Fallback for Negative Radicands:**
  When $\mathrm{MOE}(X_i)^2 < P_i^2 \cdot \mathrm{MOE}(Y_i)^2$, Census Bureau documentation specifies the ratio fallback:
  $$\mathrm{MOE}_{\text{ratio}}(P_i) = \frac{1}{Y_i} \sqrt{\mathrm{MOE}(X_i)^2 + P_i^2 \cdot \mathrm{MOE}(Y_i)^2}$$
  $$\mathrm{MOE}_{\text{ratio, pp}, i} = 100 \times \mathrm{MOE}_{\text{ratio}}(P_i)$$
  This fallback is verified to trigger for exactly 5 counties in the validated dataset:
  1. `06055` (Napa County, CA): Radicand = $-1,814,361.04 \implies \mathrm{MOE}_{\text{pp}} = \pm 5.07$ pp
  2. `15005` (Kalawao County, HI): Radicand = $-55.04 \implies \mathrm{MOE}_{\text{pp}} = \pm 30.93$ pp
  3. `27069` (Kittson County, MN): Radicand = $-4,807.88 \implies \mathrm{MOE}_{\text{pp}} = \pm 7.28$ pp
  4. `29063` (DeKalb County, MO): Radicand = $-123,632.61 \implies \mathrm{MOE}_{\text{pp}} = \pm 13.25$ pp
  5. `30009` (Carbon County, MT): Radicand = $-828,384.89 \implies \mathrm{MOE}_{\text{pp}} = \pm 45.92$ pp

### Proposed Moment-Matched Beta Simulation Protocol
Normal perturbations clipped to $[0\%, 100\%]$ are formally **rejected** to prevent artificial probability mass accumulation at boundaries and distribution family distortion. Instead, a naturally bounded, moment-matched Beta distribution is specified for each county's subscription proportion:

1. **Parameter Derivation:**
   For county $i$:
   - Estimated subscription proportion: $p_i = \frac{\text{B28002\_007E}_i}{\text{B28002\_001E}_i} \in (0, 1)$
   - Approximate standard error on proportion scale:
     $$\mathrm{se}_i = \frac{\mathrm{MOE}_{\text{pp}, i}}{100 \times 1.645} = \frac{\mathrm{MOE}(P_i)}{1.645}$$
   - Target sampling variance: $V_i = \mathrm{se}_i^2$
   - Maximum admissible variance for a Beta distribution with mean $p_i$:
     $$V_{\max, i} = p_i (1 - p_i)$$
   - Moment-matched Beta parameters $(\alpha_i, \beta_i)$:
     $$\alpha_i = p_i \left( \frac{p_i(1 - p_i)}{V_i} - 1 \right)$$
     $$\beta_i = (1 - p_i) \left( \frac{p_i(1 - p_i)}{V_i} - 1 \right)$$

2. **Mathematical Feasibility:**
   The Beta parameters are valid if and only if $0 < p_i < 1$ and $0 < V_i < p_i(1 - p_i)$ (ensuring $\alpha_i > 0$ and $\beta_i > 0$).
   - **Primary Sample Evaluated:** $N = 3,135$ counties.
   - **Feasible Rows:** **3,135** (100.0%).
   - **Infeasible Rows:** **0** (0.0%).
   - **Feasibility Status:** `PASS` (All rows satisfy existence bounds without clipping).

### Beta Distribution-Shape Diagnostics & Qualitative Limitations
While positive finite parameters establish **mathematical feasibility** (proper distribution integrating to 1), they do **not** establish that the distribution is a realistic representation of sampling uncertainty. 

An explicit shape diagnostic across all 3,135 primary-sample counties reveals:
- **Count with $\alpha_i < 1$:** **1** county (`48301`, Loving County, TX)
- **Count with $\beta_i < 1$:** **2** counties (`48269`, King County, TX; `48301`, Loving County, TX)
- **Count with both $\alpha_i < 1$ and $\beta_i < 1$:** **1** county (`48301`, Loving County, TX)

#### Counties with Shape Parameter Anomalies ($\alpha < 1$ or $\beta < 1$)

| FIPS | County Name | Point Estimate ($p_i$) | Standard Error ($\mathrm{se}_i$) | Variance ($V_i$) | Upper Bound ($V_{\max, i}$) | Variance Ratio ($V / V_{\max}$) | $\alpha_i$ | $\beta_i$ | Distribution Shape & Implication |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`48301`** | **Loving County, TX** | 0.8519 | 0.2968 | 0.088066 | 0.126200 | **0.697827** | **0.3689** | **0.0642** | **Strictly U-shaped (bimodal with asymptotes at 0 and 1).** Density troughs in the interior and spikes near 0 and 1. |
| **`48269`** | **King County, TX** | 0.8829 | 0.1106 | 0.012229 | 0.103401 | 0.118271 | 6.5820 | **0.8731** | **Strictly increasing on $(0, 1)$.** Density has a vertical asymptote at 1, skewing draws toward the upper bound. |

#### Methodological Implications for Simulation Draws
- For 3,133 of the 3,135 counties (99.94%), $\alpha > 1$ and $\beta > 1$, producing standard **unimodal, bell-shaped** distributions centered near $p_i$.
- In **Loving County, TX** (`48301`), having **both $\alpha < 1$ and $\beta < 1$** creates a **U-shaped density**. The probability density function $f(x) \propto x^{\alpha - 1} (1-x)^{\beta - 1}$ approaches infinity as $x \to 0$ and $x \to 1$. Rather than clustering around the point estimate of 85.19%, individual draws will tend to polarize near 0 or 1.
- This behavior illustrates that moment-matching with very large margins of error (loving County has only 27 households in ACS B28002) can distort the qualitative shape of sampling error.
- **Execution & Sensitivity Resolution:** The moment-matched Beta simulation was executed with $M = 1,000$ Monte Carlo replicates (seed `20261018`). In the primary specification, Loving County's mathematically valid Beta parameters ($\alpha \approx 0.3689, \beta \approx 0.0642$) are retained. In a parallel sensitivity scenario, Loving County's outcome is held fixed at its observed point estimate ($85.19\%$). Comparison reveals that simulating Loving County's outcome has virtually zero aggregate influence on regression slopes or the threshold contrast (see `reports/uncertainty_simulation_results.md`).

---

## 6. Temporal and Measurement Limitations

All reports and subsequent manuscripts must disclose the following structural data limitations:

1. **Interlocking Time-Period Mismatch:**
   - The Census ACS 2024 5-year estimates represent an **interlocking pooled sampling window spanning 2020 through 2024**, reflecting multi-year average household subscription rates and socioeconomic indicators.
   - The FCC Broadband Map file represents a **fixed point-in-time administrative snapshot as of December 30, 2025**.
   - The FCC snapshot post-dates the ACS measurement window by 12 months. Cross-sectional findings cannot be interpreted as a concurrent equilibrium.
2. **Measurement Divergence:**
   - **FCC Data:** Reflects provider-reported network deployment across Broadband Serviceable Locations (BSLs) at peak advertised speeds. Provider reporting has known historical coverage overstatement risks.
   - **ACS Data:** Reflects survey-reported household adoption of wired broadband service (cable, fiber, DSL).
   - The two datasets capture distinct economic concepts (supply vs. demand/adoption).
3. **Approximation in Derived Uncertainty:**
   - Summary table B28002 lacks public microdata replicate weights, requiring Taylor-series linearization for derived proportion MOEs.
4. **Geographic Exclusions:**
   - Exclusion of Connecticut (due to FIPS boundary transition) and Island Territories limits total national generalizability.

---

## 7. Pre-Specified Robustness Checks & Weighting Decisions

### Weighting Decision
- **Primary Analysis:** **Unweighted OLS** is maintained as the primary estimand.
- **Uncertainty Check:** Inverse-MOE-squared weighting ($1 / \mathrm{MOE}_{\text{pp}}^2$) is **not** added to the Monte Carlo uncertainty simulation.
- **Population Weighting:** Household-count-weighted WLS ($w_i = \text{B28002\_001E}_i$) represents an optional population-weighted county-level estimand. It remains formally **deferred**.

### Robustness Checks Execution Status Summary
1. **Alternate Speed Benchmark:**
   - **Status:** **COMPLETE**. Models A1/A2 (100/20 Mbps) and B1/B2 (25/3 Mbps) estimated on identical primary ($N = 3,135$) and PR sensitivity ($N = 3,213$) samples. Difference $\hat{\beta}_B - \hat{\beta}_A = +0.4910$ pp ($t = 4.96, p < 0.0001$). Documented in `reports/baseline_model_results.md`.
2. **Geographic Scope Sensitivity (Puerto Rico):**
   - **Status:** **COMPLETE**. Re-estimated on $N = 3,213$ counties (Puerto Rico as Cluster 51). Model A2 availability coefficient is $+2.8596$ pp (vs $+2.9872$ pp in primary). Documented in `reports/baseline_model_results.md`.
3. **Socioeconomic Control Impact:**
   - **Status:** **COMPLETE**. Bivariate vs. multivariable models evaluated. Omitting poverty and education attenuates availability coefficients by $\approx 47\%$ to $50\%$. Documented in `reports/baseline_model_results.md`.
4. **Sampling Uncertainty Propagation:**
   - **Status:** **COMPLETE**. Evaluated across $M = 1,000$ paired moment-matched Beta Monte Carlo draws (seed `20261018`) for Models A2 and B2, including primary and Loving-fixed sensitivity scenarios. Documented in `reports/uncertainty_simulation_results.md`.
5. **Wild Cluster Bootstrap:**
   - **Status:** **DEFERRED**. Preserved as a future methodological refinement; not executed in current phase.

---

## 8. Analytical Execution Governance & Status Summary

| Methodology Component | Decision / Specification | Status | Review Notes |
| :--- | :--- | :---: | :--- |
| **Baseline OLS Models (A1, A2, B1, B2)** | 100/20 vs 25/3 models on primary ($N = 3,135$) and PR ($N = 3,213$) samples | **COMPLETE** | Documented in `reports/baseline_model_results.*` |
| **Regression Diagnostics & LOO Influence** | Cook's distance, studentized residuals, and LOO influence check | **COMPLETE** | Max Cook's $D = 0.0195$; no single county shifts slopes by $> 0.015$ pp |
| **Threshold Contrast Hypothesis Test** | State-clustered Wald test of $H_0: \beta_B - \beta_A = 0$ | **COMPLETE** | Diff $= +0.4910$ pp ($95\%\text{ CI}: [+0.2970, +0.6850]$, $p = 1.34 \times 10^{-6}$) |
| **Beta Moment-Matched Feasibility** | 3,135/3,135 counties satisfy $0 < V < p(1-p)$; 0 infeasible | **PASS** | Strict mathematical feasibility verified |
| **Beta Distribution-Shape Diagnostics** | Loving County, TX ($48301$) exhibits U-shaped Beta density | **PASS** | Handled via full simulation + fixed sensitivity scenario |
| **ACS Outcome Uncertainty Propagation** | $M = 1,000$ paired Monte Carlo draws, seed `20261018`, Models A2 & B2 | **COMPLETE** | Documented in `reports/uncertainty_simulation_results.*` |
| **Wild Cluster Bootstrap** | Webb 6-point, $B = 999$, seed `20261018`, WCR11 test inversion | **DEFERRED** | Preserved for future work; not executed |
| **Household-Count Weighted WLS** | Optional population-weighted county estimand | **DEFERRED** | Unweighted OLS maintained as primary |
| **Overall Phase 4 Status** | Baseline OLS and ACS Outcome Uncertainty Simulation completed | **COMPLETE** | All pre-specified Phase 4 deliverables implemented and verified |

- **Reproducibility:** All analytical scripts use explicit seeds, deterministic joins, and write machine-readable JSON summaries alongside Markdown documentation and high-resolution figures.
