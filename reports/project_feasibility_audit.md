# Project Feasibility & Data Compatibility Audit Report

**Validator Execution Status:** `SUCCESS`  
**Overall Project Feasibility Gate:** `PASS`  
**Working Research Question:** *How sensitive is the county-level relationship between reported fixed broadband availability and household-reported wired broadband subscription to the availability-speed definition, socioeconomic context, and ACS sampling uncertainty?*  

> **Feasibility Gate Status Note:** All mandatory input source-integrity checks passed, ACS uncertainty calculation verified, FCC threshold comparison monotonicity verified; alternate-speed input feasibility is complete, while empirical relationship sensitivity analysis has not yet been performed.

> **Important Observational Scope Notice:** This project is an observational, county-level ecological study. No causal claims are made, and aggregate differences between FCC facility-based availability and Census household subscription cannot be described as a direct household-level adoption–availability gap.

---

## 1. Validated Data Sources, File Hashes, and Provenance

### File Hashes and Provenance
> [!NOTE]
> **Integrity Notice:** File hashes (SHA-256) verify bit-level file integrity and local reproducibility; they do not represent digital signatures or independent proof of data authenticity or vintage. Source vintage and query routes reflect user-confirmed export parameters and Census API endpoints.

| Dataset | File Path | Format | Records | SHA-256 (64-character hash) | Vintage / As-of Date | Source Platform & Query Route |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **FCC Availability (100/20)** | `data/raw/bdc_comparison_fixed_county_total_all_wired_r_100_20_D25.csv` | CSV | 3234 | `de0058de57e6484519ff180fd32913ffb8950a2c22632e8fdd4edfa30430768a` | Dec 30, 2025 | FCC National Broadband Map (Area Comparison, County, Total, Residential, All Wired, >=100/20 Mbps) |
| **FCC Availability (25/3)** | `data/raw/bdc_comparison_fixed_county_total_all_wired_r_25_3_D25.csv` | CSV | 3234 | `a6649e1dbbbdb4a3d118714115c08bad825694b328362dfb3d0740b0452f1f27` | Dec 30, 2025 | FCC National Broadband Map (Area Comparison, County, Total, Residential, All Wired, >=25/3 Mbps) |
| **Census B28002** | `data/raw/acs_b28002_2024_county.json` | JSON | 3222 | `d2fbb6ab8e9dee59a3a2d747dd43a4f27d48a321855495ee3fe7d0ed4c10d9b7` | 2020–2024 (5-Year Pooled) | U.S. Census API (2024 ACS 5-Year Detailed Table B28002) |
| **Census Context (S1701/S1501)** | `data/raw/acs_context_2024_county.json` | JSON | 3222 | `ad6dba9bbf68a2b4d28593f4b600559195bec3bd20943a70c5f3c51db2a65c82` | 2020–2024 (5-Year Pooled) | U.S. Census API (2024 ACS 5-Year Subject Tables S1701, S1501) |

### Critical Temporal Mismatch Disclosure
> [!WARNING]
> **Time-Period Mismatch:** The Census ACS 2024 5-year estimates represent an **interlocking pooled sampling window spanning 2020 through 2024**, reflecting multi-year average household subscription rates and socioeconomic indicators. In contrast, the FCC Broadband Map file represents a **fixed point-in-time administrative snapshot as of Dec 30, 2025**. The FCC snapshot post-dates the ACS window by 12 months. This temporal lag must be explicitly documented in all subsequent analytical work.

---

## 2. Alternate FCC Speed Threshold (25/3 Mbps) Validation & Cross-Threshold Comparison

### Status Distinction: Input Feasibility vs. Empirical Sensitivity Analysis
- **Alternate-Speed Input Feasibility:** `COMPLETE`  
  *Candidate export file structure, five-digit FIPS formatting, unit count preservation, and pairwise coverage monotonicity against the primary 100/20 export are fully validated on disk.*
- **Empirical Relationship Sensitivity Analysis:** `NOT_YET_PERFORMED`  
  *The actual empirical and econometric relationship between broadband availability and household subscription has not yet been tested at either 100/20 or 25/3 thresholds. Feasibility validation establishes dataset readiness for downstream modeling but does not execute or imply completion of the sensitivity analysis itself.*

- **Validation Status:** `PASS` (Independent structure, FIPS, coverage range, and missing-value checks passed)
- **Candidate File:** `data/raw/bdc_comparison_fixed_county_total_all_wired_r_25_3_D25.csv` (163568 bytes, SHA-256: `a6649e1dbbbdb4a3d118714115c08bad825694b328362dfb3d0740b0452f1f27`)
- **User-Confirmed Provenance Settings:** Fixed broadband, County, Total, Residential, All Wired, >=25/3 Mbps, Data as of Dec 30, 2025. *(Note: Recorded as user-confirmed settings from the FCC interface, not embedded CSV metadata. File hash verifies bit-level file integrity; it does not independently prove vintage or authenticity).*

### Threshold Comparison & Coverage Monotonicity Results
- **Shared County Entities:** `3234` (100% exact alignment with primary 100/20 export; 0 entities only in one file)
- **Geographic Description Alignment:** `0` mismatches
- **Unit Counts Alignment:** `0` mismatches across both unit-count columns
- **Monotonicity Check (Documented Tolerance: $\epsilon = 1e-09$):**
  - **Counties with strictly higher 25/3 coverage ($\Delta > 10^{-9}$):** `2585` (79.93%)
  - **Counties with equal coverage within tolerance ($|\Delta| \le 10^{-9}$):** `649` (20.07%)
  - **Monotonicity Violations (25/3 coverage lower than 100/20 coverage):** `0` violations (`PASS`)
- **Coverage Increase Distribution ($\Delta = \text{cov}_{25/3} - \text{cov}_{100/20}$):**
  - Min = `0.000000` | Q25 = `+0.02%` | Median = `+0.46%` | Q75 = `+1.93%` | Max = `+98.79%` | Mean = `+2.05%`

---

## 3. Socioeconomic ACS Variable Acquisition & Metadata

County-level socioeconomic context data was retrieved from the official 2024 ACS 5-Year Subject Tables API:
- **Retrieval Date:** `2026-10-18`
- **Endpoint:** `https://api.census.gov/data/2024/acs/acs5/subject?get=NAME,S1701_C03_001E,S1701_C03_001M,S1501_C02_015E,S1501_C02_015M&for=county:*`

| Variable ID | Attribute | Concept / Table | Official 2024 Census Label | Min | Median | Max | Mean |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `S1701_C03_001E` | ESTIMATE | Poverty Status in the Past 12 Months (S1701) | Estimate!!Percent below poverty level!!Population for whom poverty status is determined | 1.4 | 13.4 | 63.6 | 14.94 |
| `S1701_C03_001M` | MARGIN_OF_ERROR | Poverty Status in the Past 12 Months (S1701) | Margin of Error!!Percent below poverty level!!Population for whom poverty status is determined | 0.2 | 2.3 | 21.1 | 2.6 |
| `S1501_C02_015E` | ESTIMATE | Educational Attainment (S1501) | Estimate!!Percent!!AGE BY EDUCATIONAL ATTAINMENT!!Population 25 years and over!!Bachelor's degree or higher | 0.0 | 22.3 | 80.5 | 24.7 |
| `S1501_C02_015M` | MARGIN_OF_ERROR | Educational Attainment (S1501) | Margin of Error!!Percent!!AGE BY EDUCATIONAL ATTAINMENT!!Population 25 years and over!!Bachelor's degree or higher | 0.2 | 2.2 | 66.1 | 2.49 |

---

## 4. Geographic Overlap & Exact 5-Digit FIPS Coverage

- **Total FCC Entities:** `3234` (Identical across both 100/20 and 25/3 exports)
- **Total Census ACS Entities:** `3222` (B28002 and Context files match 100% identically across all 3,222 entities)
- **Primary Study Population ($N = 3,135$):** 49 states plus Washington, DC, excluding Connecticut and Puerto Rico.
- **Puerto Rico Municipios ($N = 78$):** All 78 municipios match exactly on 5-digit FIPS.
- **Combined Exact-FIPS Joined Sample ($N = 3,213$):** Represents those 3,135 matches plus Puerto Rico's 78 municipios.
- **Connecticut Exact Matches ($N = 0$):** Connecticut remains excluded from exact-FIPS matching; no crosswalk created.

### Geographic Discrepancies & Exclusions
1. **Connecticut Boundary Incompatibility (0 exact matches):**
   - **FCC Files (8 legacy county FIPS):** `09001` (Fairfield), `09003` (Hartford), `09005` (Litchfield), `09007` (Middlesex), `09009` (New Haven), `09011` (New London), `09013` (Tolland), `09015` (Windham).
   - **Census 2024 ACS (9 planning region FIPS):** `09110` (Capitol), `09120` (Greater Bridgeport), `09130` (Lower CT River Valley), `09140` (Naugatuck Valley), `09150` (Northeastern CT), `09160` (Northwest Hills), `09170` (South Central CT), `09180` (Southeastern CT), `09190` (Western CT).
   - **Policy:** **Connecticut remains excluded from exact-FIPS matching. Do not create a crosswalk.** The primary county-level regression/modeling sample ($N = 3,135$) excludes Connecticut entirely.
2. **Island Territories (FCC-Only, 13 entities):**
   - American Samoa (`60010`–`60050`, 5 entities), Guam (`66010`), Northern Mariana Islands (`69085`–`69120`, 4 entities), U.S. Virgin Islands (`78010`–`78030`, 3 entities).
   - **Policy:** **Exclude island territories** because ACS 5-year data does not publish standard detailed table B28002 or Subject Tables S1701/S1501 for these territories.
3. **Puerto Rico Sensitivity Check (78 municipios):**
   - All 78 Puerto Rico municipios match exactly across FCC and Census.
   - **Policy:** Run the primary analysis on the sample of **49 states plus Washington, DC, excluding Connecticut and Puerto Rico ($N = 3,135$)**, and conduct an explicit **sensitivity check on those 3,135 matches plus Puerto Rico's 78 municipios ($N = 3,213$)** to test whether macroeconomic differences or insular infrastructure systematically shift the availability–subscription relationship.

---

## 5. ACS Subscription-Rate Uncertainty Propagation (Task C)

- **Uncertainty Calculation Check Status:** `PASS` (Explicit checks evaluated: county count match, zero-denominator free, valid proportions, non-negative/finite MOEs, and ratio-fallback complete)

### Mathematical Formulation
For county $i$, let:
- Numerator Estimate: $X = \text{B28002\_007E}$ (Broadband such as cable, fiber optic or DSL), Margin of Error: $\mathrm{MOE}(X) = \text{B28002\_007M}$
- Denominator Estimate: $Y = \text{B28002\_001E}$ (Total households), Margin of Error: $\mathrm{MOE}(Y) = \text{B28002\_001M}$

We clearly distinguish the rate as a proportion from the rate as a percentage:
- **Subscription Rate as a Proportion ($P$):** $P = \frac{X}{Y} \in [0, 1]$
- **Subscription Rate as a Percentage ($P_{\%}$):** $P_{\%} = P \times 100\% \in [0, 100]\%$

Following official Census Bureau methodology for derived proportions where the numerator is a subset of the denominator:
$$\mathrm{MOE}(P) = \frac{1}{Y} \sqrt{\mathrm{MOE}(X)^2 - P^2 \cdot \mathrm{MOE}(Y)^2}$$

The margin of error expressed in percentage points ($\mathrm{MOE}_{\text{pp}}$) is the proportion-scale result multiplied by 100:
$$\mathrm{MOE}_{\text{pp}} = \mathrm{MOE}(P) \times 100$$

### Negative Radicand Ratio-Form Fallback
When $\mathrm{MOE}(X)^2 < P^2 \cdot \mathrm{MOE}(Y)^2$, the expression under the square root is negative. In compliance with official Census Bureau documentation, we substitute the derived ratio-form formula:
$$\mathrm{MOE}_{\text{ratio}}(P) = \frac{1}{Y} \sqrt{\mathrm{MOE}(X)^2 + P^2 \cdot \mathrm{MOE}(Y)^2}$$
$$\mathrm{MOE}_{\text{ratio, pp}} = \mathrm{MOE}_{\text{ratio}}(P) \times 100$$

### Empirical Test Execution on 2024 ACS Data ($N = 3,222$)
- **Counties Evaluated:** `3222` (0 zero-denominator counties)
- **Standard Proportion Formula Applied:** `3217` counties (99.84%)
- **Negative Radicand (Ratio-Form Fallback Applied):** Exactly `5` counties (0.16%):
  - **06055 (Napa County, California):** $P = 0.7732$ (77.32%), radicand = `-1814361.04`, Fallback $\mathrm{MOE}_{\text{ratio}}(P) = 0.0507$ (±5.07 pp)
  - **15005 (Kalawao County, Hawaii):** $P = 0.4250$ (42.50%), radicand = `-55.04`, Fallback $\mathrm{MOE}_{\text{ratio}}(P) = 0.3093$ (±30.93 pp)
  - **27069 (Kittson County, Minnesota):** $P = 0.7401$ (74.01%), radicand = `-4807.88`, Fallback $\mathrm{MOE}_{\text{ratio}}(P) = 0.0728$ (±7.28 pp)
  - **29063 (DeKalb County, Missouri):** $P = 0.5595$ (55.95%), radicand = `-123632.61`, Fallback $\mathrm{MOE}_{\text{ratio}}(P) = 0.1325$ (±13.25 pp)
  - **30009 (Carbon County, Montana):** $P = 0.4951$ (49.51%), radicand = `-828384.89`, Fallback $\mathrm{MOE}_{\text{ratio}}(P) = 0.4592$ (±45.92 pp)

#### Numerical Distributions Across Both Scales

| Metric | Scale | Min | Q25 | Median | Q75 | Max | Mean |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Subscription Rate ($P$)** | Proportion $[0, 1]$ | 0.1362 | 0.5639 | 0.6558 | 0.7315 | 0.9471 | 0.6411 |
| **Subscription Rate ($P_{\%}$)** | Percentage $(\%)$ | 13.62% | 56.39% | 65.58% | 73.15% | 94.71% | 64.11% |
| **90% Margin of Error ($\mathrm{MOE}_P$)** | Proportion $[0, 1]$ | 0.0023 | 0.0190 | 0.0310 | 0.0436 | 0.4882 | 0.0345 |
| **90% Margin of Error ($\mathrm{MOE}_{\text{pp}}$)** | Percentage Points (pp) | ±0.23 pp | ±1.90 pp | ±3.10 pp | ±4.36 pp | ±48.82 pp | ±3.45 pp |

### Methodological Limitations & Official Citation
> **Official Citation:** *U.S. Census Bureau, 'Understanding and Using American Community Survey Data: What All Data Users Need to Know' (ACS General Handbook, Chapter 8: Calculating Measures of Error for Derived Estimates, 2020/2024)*
> 
> **Why this is an approximation:** The Census proportion formula uses a first-order Taylor series linearization (delta method). Because summary table B28002 publishes pre-tabulated aggregate counts rather than microdata with the 80 replicate weights from the Successive Difference Replication (SDR) method, the covariance term is approximated rather than directly computed. In sparsely sampled rural areas (such as Kalawao, HI or Carbon, MT), this approximation can yield inflated variance bounds or negative radicands.

---

## 6. Methodological Recommendations & Decisions for ChatGPT Authorization

### DECISION-01: Alternate FCC Speed Threshold (25/3 Mbps) Validation & Inclusion
- **Status:** `VALIDATED_AND_RECOMMENDED_FOR_ANALYSIS`
- **Description:** The alternate FCC export (25/3 Mbps, Dec 30, 2025) has been validated independently. All 3,234 county entities align perfectly with the 100/20 export with identical unit counts and descriptions. Coverage monotonicity holds across 100% of counties (2,585 higher, 649 equal within 1e-9 tolerance, 0 lower). Alternate-speed input feasibility is complete; empirical relationship sensitivity analysis has not yet been performed.
- **Recommended Decision:** Authorize inclusion of 25/3 Mbps coverage in subsequent Phase 4 availability-speed sensitivity modeling, satisfying the approved research question's multi-threshold requirement. Do not infer that the actual empirical relationship has already been evaluated at both thresholds.

### DECISION-02: Connecticut Geography Policy
- **Status:** `RECOMMENDED_ACTION_DEFINED`
- **Description:** FCC data uses 8 legacy Connecticut counties (09001-09015), whereas 2024 ACS uses 9 planning regions (09110-09190). There are 0 exact FIPS matches.
- **Recommended Decision:** Formally exclude Connecticut (09) from the primary county-level regression/modeling sample (N = 3,135, representing 49 states plus Washington, DC, excluding Connecticut and Puerto Rico). Connecticut remains excluded from exact-FIPS matching; do not create a crosswalk.

### DECISION-03: Puerto Rico Geographic Scope Policy
- **Status:** `RECOMMENDED_ACTION_DEFINED`
- **Description:** All 78 Puerto Rico municipios match exactly across FCC and Census. However, PR exhibits distinct macroeconomic conditions and telecommunications regulatory frameworks.
- **Recommended Decision:** Designate the sample of 49 states plus Washington, DC, excluding Connecticut and Puerto Rico (N = 3,135) as the primary study population, and perform an explicit sensitivity check on those 3,135 matches plus Puerto Rico's 78 municipios (N = 3,213).

### DECISION-04: ACS Sampling Uncertainty Weighting Strategy
- **Status:** `RECOMMENDED_ACTION_DEFINED`
- **Description:** Five counties have negative radicands requiring ratio fallback MOE, and small rural counties (e.g. Loving, TX and Kalawao, HI) show substantial sampling variance (MOE > 30 pp).
- **Recommended Decision:** Evaluate whether downstream regression models should utilize Weighted Least Squares (WLS) using inverse-variance weights derived from percentage-point MOE (1 / MOE_pp^2) or household-count weights (B28002_001E) alongside unweighted OLS as a sensitivity check.

### DECISION-05: Temporal Lag Methodological Caveat
- **Status:** `DOCUMENTED_AND_DISCLOSED`
- **Description:** ACS estimates describe pooled 2020-2024 multi-year averages, while FCC reflects a point snapshot as of Dec 30, 2025.
- **Recommended Decision:** Explicitly report the 12-month post-period gap in all methodology sections. Do not interpret findings as a concurrent point-in-time equilibrium.

---
*Audit generated programmatically by `scripts/validate_feasibility.py`.*
