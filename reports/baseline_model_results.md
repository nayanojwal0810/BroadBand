# Baseline Econometric Analysis: County Fixed Broadband Availability, Socioeconomic Controls, and Threshold Sensitivity

**Phase:** Phase 4B — Step 3: Reconcile Baseline Reporting and Test Threshold Sensitivity<br>
**Repository:** `nayanojwal0810/BroadBand`<br>
**Dataset:** `data/processed/county_broadband_analysis.csv`<br>
**Generated:** 2026-10-18 15:55:04 UTC<br>
**Status:** Baseline Analysis, Influence Diagnostics, and Contrast Testing Complete (Governance Compliant)

---

## 1. Executive Summary & Research Question Findings

This report presents the complete baseline econometric results for the approved research question:
> **“How sensitive is the county-level relationship between reported fixed broadband availability and household-reported wired broadband subscription to the availability-speed definition and socioeconomic context?”**

### Key Empirical Findings
1. **Formal Availability Threshold Contrast (Statistical Test Result):**
   - In adjusted models controlling for poverty and educational attainment, the estimated availability slope increases from **2.987 pp** per 10 pp availability at >= 100/20 Mbps to **3.478 pp** per 10 pp availability at >= 25/3 Mbps.
   - Using a joint stacked bivariate regression with state-clustered covariance ($G = 50$, $df = 49$), the formal linear hypothesis test for slope equality ($H_0: \beta_B - \beta_A = 0$) yields:
     - **Estimated Slope Contrast ($\beta_B - \beta_A$):** **+0.4910 pp** per 10 pp availability increment
     - **Cluster-Robust Standard Error:** **0.0748**
     - **95% Clustered Confidence Interval:** **[0.3408, 0.6413]**
     - **Test Statistic:** **$t = 6.5660$** ($p = 3.1207e-08$)
   - This provides rigorous empirical confirmation that the estimated county-level association between reported availability and household wired subscription is statistically sensitive to the speed threshold definition, rejecting slope equality at $p < 0.0001$.
2. **Socioeconomic Attenuation Effect:**
   - Incorporating county poverty rates and educational attainment substantially attenuates the estimated availability coefficient:
     - For Model A (100/20 Mbps): coefficient attenuates from **3.833** to **2.987 pp / 10 pp** (attenuation of **-0.845 pp**, or **-22.1%**).
     - For Model B (25/3 Mbps): coefficient attenuates from **4.424** to **3.478 pp / 10 pp** (attenuation of **-0.946 pp**, or **-21.4%**).
   - Concurrently, explanatory power increases substantially: $R^2$ rises from **0.366** to **0.596** (Model A) and from **0.398** to **0.616** (Model B).
3. **Influence Sensitivity (Leave-One-Out Diagnostics):**
   - Leave-one-out re-estimation across the ten highest Cook's distance observations in each adjusted model demonstrates that no single county drives the availability estimates.
   - For Model A2, the largest absolute coefficient change upon omitting any single county is **+0.0219 pp** (+0.73% change; Bristol Bay Borough, Alaska).
   - For Model B2, the largest absolute coefficient change is **+0.0317 pp** (+0.91% change; Esmeralda County, Nevada).
   - All leave-one-out shifts remain below 1% of the baseline slope, establishing parameter stability while retaining all observations in accordance with pre-specified sample rules.
4. **State-Clustered Inference and Evidential Limits:**
   - State-clustered standard errors ($G = 50$, finite-sample adjustment $c = 1.0214$) are substantially larger than HC3 standard errors (for Model A2 availability: clustered SE = 0.1468 vs. HC3 SE = 0.1017).
   - *Evidential Limits Clarification:* Clustered standard errors allow for arbitrary intra-state residual correlation across counties within the same state without identifying or proving specific underlying causal mechanisms (such as state broadband grant allocations or regulatory policies). This empirical divergence establishes the necessity of clustering at the state level to avoid overly anti-conservative inference, while acknowledging the limitations of cross-sectional observational data.
5. **Puerto Rico Sensitivity Contrast:**
   - On the Puerto Rico-inclusive sensitivity sample ($N = 3,213$, $G = 51$ clusters), the formal contrast remains virtually identical: beta_B - beta_A = +0.4867 pp (clustered SE = 0.0743, $t = 6.5529$, $p < 0.0001$, 95% CI: [0.3376, 0.6359]).
   - This analysis is reported as a sensitivity check with the explicit limitation that Puerto Rico represents a single territory cluster containing 78 observations (cluster size asymmetry) and cannot be generalized to other U.S. territories.
6. **Observational Scope Reminder:**
   - These estimates represent observational ecological associations across aggregate geographic units. They cannot establish causal effects of infrastructure deployment on household adoption, nor can they measure individual household connectivity decisions (avoiding the ecological fallacy).

---

## 2. Econometric Model Specifications

All models use Ordinary Least Squares (OLS) with the outcome expressed as a percentage:
`subscription_rate_pct_i = 100 * (B28002_007E_i / B28002_001E_i)`

### Primary Model Specifications ($N = 3,135$ Counties: 49 States + DC)
- **Model A1 (100/20 Unadjusted):**
  `subscription_rate_pct_i = alpha_A1 + beta_A1 * avail_100_20_10pp_i + epsilon_A1,i`
- **Model A2 (100/20 Adjusted):**
  `subscription_rate_pct_i = alpha_A2 + beta_A2 * avail_100_20_10pp_i + gamma_1 * poverty_pct_i + gamma_2 * bachelor_plus_pct_i + epsilon_A2,i`
- **Model B1 (25/3 Unadjusted):**
  `subscription_rate_pct_i = alpha_B1 + beta_B1 * avail_25_3_10pp_i + epsilon_B1,i`
- **Model B2 (25/3 Adjusted):**
  `subscription_rate_pct_i = alpha_B2 + beta_B2 * avail_25_3_10pp_i + delta_1 * poverty_pct_i + delta_2 * bachelor_plus_pct_i + epsilon_B2,i`

### Joint Stacked Contrast Specification ($2N = 6,270$ Stacked Rows, $G = 50$ Clusters)
To test $H_0: \beta_B - \beta_A = 0$ while accounting for covariance across equations and intra-state clustering:
`y_si = alpha_A * d_A + beta_A * (avail_100_20_10pp_i * d_A) + gamma_1 * (poverty_pct_i * d_A) + gamma_2 * (bachelor_plus_pct_i * d_A) + alpha_B * d_B + beta_B * (avail_25_3_10pp_i * d_B) + delta_1 * (poverty_pct_i * d_B) + delta_2 * (bachelor_plus_pct_i * d_B) + eta_si`
where $d_A = 1$ for equation A and $0$ for equation B; $d_B = 1$ for equation B and $0$ for equation A.
- This stacked regression reproduces the separate OLS point estimates beta_A and beta_B exactly within machine precision (< 1e-14).
- State-clustered covariance over the stacked system captures both the cross-equation residual correlation for county $i$ and spatial clustering within states.

---

## 3. Baseline Regression Results Table

### Table 1: Baseline OLS Regression Estimates of County Household Broadband Subscription

| Regressor / Metric | Model A1: 100/20 Unadj | Model A2: 100/20 Adj | Model B1: 25/3 Unadj | Model B2: 25/3 Adj | Model A2-PR: 100/20 PR Sens | Model B2-PR: 25/3 PR Sens |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Availability (10 pp increment)** | **3.8326** | **2.9872** | **4.4239** | **3.4782** | **2.9693** | **3.4561** |
| *Clustered SE (G clusters)* | (0.1995) | (0.1468) | (0.2080) | (0.1741) | (0.1424) | (0.1707) |
| *HC3 Robust SE* | [0.1145] | [0.1017] | [0.1201] | [0.1094] | [0.1011] | [0.1084] |
| *95% Clustered CI* | [3.432, 4.234] | [2.692, 3.282] | [4.006, 4.842] | [3.128, 3.828] | [2.683, 3.255] | [3.113, 3.799] |
| *p-value (Clustered)* | < 0.0001 | < 0.0001 | < 0.0001 | < 0.0001 | < 0.0001 | < 0.0001 |
| **Poverty Rate (`poverty_pct`)** | — | **-0.3834** | — | **-0.3811** | **-0.5203** | **-0.5172** |
| *Clustered SE* | — | (0.1016) | — | (0.0946) | (0.0958) | (0.0929) |
| *HC3 Robust SE* | — | [0.0375] | — | [0.0364] | [0.0270] | [0.0263] |
| *p-value (Clustered)* | — | 0.0004 | — | 0.0002 | < 0.0001 | < 0.0001 |
| **Bachelor's Degree+ (`bachelor_plus_pct`)** | — | **0.4527** | — | **0.4395** | **0.4165** | **0.4036** |
| *Clustered SE* | — | (0.0286) | — | (0.0284) | (0.0357) | (0.0359) |
| *HC3 Robust SE* | — | [0.0152] | — | [0.0149] | [0.0145] | [0.0143] |
| *p-value (Clustered)* | — | < 0.0001 | — | < 0.0001 | < 0.0001 | < 0.0001 |
| **Intercept** | **33.3354** | **34.5157** | **27.6527** | **30.1264** | **37.3667** | **33.0025** |
| *Clustered SE* | (1.7783) | (2.2262) | (1.8187) | (2.2444) | (2.2465) | (2.3223) |
| **Counties ($N$)** | **3,135** | **3,135** | **3,135** | **3,135** | **3,213** | **3,213** |
| **Clusters ($G$)** | **50** | **50** | **50** | **50** | **51** | **51** |
| **R-squared ($R^2$)** | **0.3663** | **0.5963** | **0.3980** | **0.6165** | **0.6070** | **0.6262** |
| **Adjusted R-squared** | 0.3661 | 0.5959 | 0.3978 | 0.6161 | 0.6066 | 0.6259 |
| **Residual Std Error (RMSE pp)** | 9.669 | 7.720 | 9.424 | 7.524 | 7.797 | 7.604 |
| **Matrix Rank ($K$)** | 2 (Full) | 4 (Full) | 2 (Full) | 4 (Full) | 4 (Full) | 4 (Full) |

---

## 4. Formal Threshold Sensitivity Contrast Testing

### Table 2: Joint Stacked Contrast Test Results ($H_0: \beta_B - \beta_A = 0$)

| Geographic Sample | Availability Slope $\beta_A$ (100/20) | Availability Slope $\beta_B$ (25/3) | Difference ($\beta_B - \beta_A$) | Clustered SE of Difference | 95% Clustered CI | $t$-statistic | $p$-value ($df$) | Test Decision |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Primary Sample ($N=3,135$, $G=50$)** | **2.9872** | **3.4782** | **+0.4910** | **0.0748** | **[0.3408, 0.6413]** | **6.5660** | **< 0.0001 ($df=49$)** | **Reject $H_0$** |
| **PR-Inclusive Sample ($N=3,213$, $G=51$)** | **2.9693** | **3.4561** | **+0.4867** | **0.0743** | **[0.3376, 0.6359]** | **6.5529** | **< 0.0001 ($df=50$)** | **Reject $H_0$** |

#### Contrast Methodological Notes
1. **Model Stack Structure:** Each county contributes two stacked rows ($2N = 6,270$ total primary observations), paired with a block-diagonal design matrix. The stacked OLS parameter estimates for Model A2 and Model B2 reproduce the separate model estimates within numerical precision ($< 10^-14$).
2. **Covariance Accounting:** The cross-equation covariance between $\beta_A$ and $\beta_B$ under state clustering is Cov($\beta_A, \beta_B$) = 0.023141, yielding a standard error of the difference:
   `SE(beta_B - beta_A) = sqrt(Var(beta_A) + Var(beta_B) - 2 * Cov(beta_A, beta_B)) = 0.0748`
3. **Statistical Decision:** The positive difference of **+0.4910 pp** per 10 pp availability is statistically significant ($t = 6.5660, p = 3.1207e-08$). In county-level observational regressions, wired subscription tracks the broader 25/3 Mbps threshold with a steeper slope than the stricter 100/20 Mbps benchmark.

---

## 5. Influence Sensitivity: Leave-One-Out Diagnostics

To test whether the availability associations are vulnerable to specific high-influence counties, leave-one-out (LOO) regressions were calculated for the ten highest Cook's distance observations in Model A2 and Model B2.

### Table 3A: Model A2 (100/20 Adjusted) Leave-One-Out Diagnostics (Baseline $\beta_A = 2.9872$)

| Rank | FIPS | County Name | State | Cook's Distance | Leave-One-Out beta_A(-i) | Coefficient Change (Delta beta) | Relative Change (%) |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| 1 | `46102` | Oglala Lakota County, South Dakota | SD | 0.05483 | 2.9883 | +0.0011 | +0.04% |
| 2 | `48301` | Loving County, Texas | TX | 0.04048 | 2.9990 | +0.0118 | +0.40% |
| 3 | `46121` | Todd County, South Dakota | SD | 0.03594 | 2.9938 | +0.0066 | +0.22% |
| 4 | `46031` | Corson County, South Dakota | SD | 0.02923 | 2.9882 | +0.0010 | +0.03% |
| 5 | `02060` | Bristol Bay Borough, Alaska | AK | 0.02392 | 3.0091 | +0.0219 | +0.73% |
| 6 | `32009` | Esmeralda County, Nevada | NV | 0.02207 | 3.0087 | +0.0215 | +0.72% |
| 7 | `21237` | Wolfe County, Kentucky | KY | 0.02047 | 2.9800 | -0.0072 | -0.24% |
| 8 | `51045` | Craig County, Virginia | VA | 0.01554 | 3.0047 | +0.0175 | +0.59% |
| 9 | `05101` | Newton County, Arkansas | AR | 0.01490 | 3.0046 | +0.0174 | +0.58% |
| 10 | `08113` | San Miguel County, Colorado | CO | 0.01446 | 2.9807 | -0.0065 | -0.22% |

- **Model A2 Influence Summary:** Largest absolute change is **+0.0219 pp** (+0.73%) when omitting **Bristol Bay Borough, Alaska** (FIPS `02060`).

### Table 3B: Model B2 (25/3 Adjusted) Leave-One-Out Diagnostics (Baseline $\beta_B = 3.4782$)

| Rank | FIPS | County Name | State | Cook's Distance | Leave-One-Out beta_B(-i) | Coefficient Change (Delta beta) | Relative Change (%) |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| 1 | `48301` | Loving County, Texas | TX | 0.04842 | 3.4939 | +0.0156 | +0.45% |
| 2 | `46102` | Oglala Lakota County, South Dakota | SD | 0.04657 | 3.4772 | -0.0010 | -0.03% |
| 3 | `32009` | Esmeralda County, Nevada | NV | 0.04020 | 3.5099 | +0.0317 | +0.91% |
| 4 | `02060` | Bristol Bay Borough, Alaska | AK | 0.03996 | 3.5092 | +0.0309 | +0.89% |
| 5 | `46031` | Corson County, South Dakota | SD | 0.03284 | 3.4801 | +0.0019 | +0.05% |
| 6 | `46121` | Todd County, South Dakota | SD | 0.02491 | 3.4810 | +0.0027 | +0.08% |
| 7 | `28063` | Jefferson County, Mississippi | MS | 0.02301 | 3.4984 | +0.0201 | +0.58% |
| 8 | `32033` | White Pine County, Nevada | NV | 0.02297 | 3.5002 | +0.0220 | +0.63% |
| 9 | `21237` | Wolfe County, Kentucky | KY | 0.02087 | 3.4703 | -0.0080 | -0.23% |
| 10 | `32011` | Eureka County, Nevada | NV | 0.02048 | 3.4996 | +0.0214 | +0.62% |

- **Model B2 Influence Summary:** Largest absolute change is **+0.0317 pp** (+0.91%) when omitting **Esmeralda County, Nevada** (FIPS `32009`).

#### Influence Findings Detail & Evidential Limits
1. **Evidential Limits of Cook's Distance:** Conventional screening thresholds ($D_i < 0.5$) indicate that no single county acts as an extreme global outlier dominating the regression slope by itself. However, conventional cutoffs do not guarantee the absence of localized or subtle distortion.
2. **Explicit Leave-One-Out Confirmation:** The LOO sensitivity diagnostic explicitly verifies that omitting any of the top 10 influential counties shifts the availability coefficient by less than 1.0% in both models.
3. **No Observation Exclusion:** In strict adherence to the analytical plan, all 3,135 primary counties are retained.

---

## 6. Graphical Diagnostics

### Figure 6: Model Fit and Residual Diagnostics
![Figure 6: Baseline OLS Model Fit and Residual Diagnostics](figures/fig6_baseline_model_fit_and_residuals.png)

### Figure 7: Availability Coefficient Comparison Across Models
![Figure 7: Availability Coefficients Across Speed Thresholds, Adjustments, and Geographic Samples](figures/fig7_baseline_coefficient_comparison.png)

### Figure 8: Residual Q-Q and Leverage Diagnostics
![Figure 8: Baseline OLS Influence, Leverage, and Normality Diagnostics](figures/fig8_residual_qq_and_leverage.png)

### Figure 9: Formal Threshold Contrast Testing and Leave-One-Out Influence Sensitivity
![Figure 9: Formal Threshold Contrast Testing and Leave-One-Out Influence Sensitivity](figures/fig9_threshold_contrast_and_influence.png)

---

## 7. Reconciled Loving County Source Metrics & Deferred Methods

### Reconciled Loving County, Texas (`48301`) Metrics
Direct extraction from `data/raw/acs_b28002_2024_county.json` confirms:
- **Total Households Estimate ($y$):** `27`
- **Total Households MOE ($MOE_y$):** `29`
- **Broadband Subscription Estimate ($x$):** `23`
- **Broadband Subscription MOE ($MOE_x$):** `28`
- **Subscription Proportion ($p$):** $23 / 27 \approx 0.851852$ (85.19%)
- **Derived 90% MOE:** +/- 48.816869 percentage points (~ +/- 48.82 pp)
- **Approximate Standard Error:** $0.296759$
- **Beta Moment-Matched Parameters:** $\alpha \approx 0.3689 < 1$ and $\beta \approx 0.0642 < 1$
- **Density Implication:** Produces a strictly U-shaped Beta density with interior antimode, concentrating probability mass near 0% and 100%.

### Analytical Status and Related Methodological Work
1. **Baseline OLS, Diagnostics, and Contrast Testing:** Completed. State-clustered inference with finite-sample adjustment and leave-one-out diagnostics are fully executed.
2. **ACS Outcome-Uncertainty Propagation:** Executed and documented separately in `scripts/run_uncertainty_simulation.py` and `reports/uncertainty_simulation_results.md` (1,000 Beta Monte Carlo replicates).
3. **Wild Cluster Bootstrap:** Maintained as explicitly deferred. Primary inference relies strictly on asymptotic state-clustered covariance with finite-sample degrees-of-freedom adjustment.
4. **Weighting Procedures:** Maintained as explicitly deferred. Unweighted OLS evaluated as specified.

---

## 8. Conclusion & Analytical Verification Status

Step 3 completes the baseline statistical analysis and threshold contrast testing:
- **Threshold Sensitivity:** The formal contrast confirms that the availability coefficient is statistically sensitive to the speed benchmark ($p < 0.0001$).
- **Socioeconomic Controls:** Accounting for poverty and education attenuates availability coefficients by ~21–22% while explaining ~60–62% of outcome variance.
- **Influence Stability:** Leave-one-out diagnostics verify parameter stability across all high-leverage counties within 1%.
- **Next Analytical Component:** See `reports/uncertainty_simulation_results.md` for ACS outcome-uncertainty propagation.
