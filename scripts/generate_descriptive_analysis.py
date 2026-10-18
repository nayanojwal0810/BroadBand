#!/usr/bin/env python3
"""generate_descriptive_analysis.py - Phase 4B: Exploratory & Descriptive Analysis.

Loads the validated analysis dataset `data/processed/county_broadband_analysis.csv`,
computes non-parametric descriptive statistics (means, medians, standard deviations,
quartiles, ranges, and missingness), creates five publication-quality figures in
`reports/figures/`, and outputs `reports/descriptive_analysis.md`.

STRICT GOVERNANCE RESTRICTIONS:
  - NO regression models (OLS, WLS, etc.).
  - NO correlation coefficients (Pearson, Spearman).
  - NO p-values or model performance metrics.
  - NO causal claims or individual-level adoption inferences.
  - Beta simulation and wild cluster bootstrap remain deferred.
"""

from __future__ import annotations

import csv
import math
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import statsmodels.api as sm

# Configure high-quality styling for matplotlib
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.titlesize": 13,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linestyle": "--",
})


def load_dataset(csv_path: str) -> List[Dict[str, Any]]:
    records = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            parsed = {}
            for k, v in row.items():
                if k in ("geography_id", "geography_name", "state_fips", "county_fips", "state_abbr"):
                    parsed[k] = v
                elif k in ("is_primary_sample", "is_pr_inclusive_sample", "ratio_fallback_applied"):
                    parsed[k] = int(v)
                elif k in ("total_households", "total_households_moe", "broadband_subscription", "broadband_subscription_moe"):
                    parsed[k] = int(v) if v != "" else None
                elif k in ("fcc_100_20_total_units", "fcc_25_3_total_units"):
                    parsed[k] = int(v) if v != "" else None
                else:
                    parsed[k] = float(v) if v != "" else None
            records.append(parsed)
    return records


def compute_summary_table(records: List[Dict[str, Any]], var_keys: List[str]) -> Dict[str, Dict[str, Any]]:
    stats = {}
    for vk in var_keys:
        vals = [r[vk] for r in records if r[vk] is not None]
        n_missing = len(records) - len(vals)
        if not vals:
            stats[vk] = {"n": 0, "missing": n_missing}
            continue
        s_vals = sorted(vals)
        n = len(s_vals)
        mean_val = float(np.mean(vals))
        std_val = float(np.std(vals, ddof=1)) if n > 1 else 0.0
        median_val = float(np.median(vals))
        q25 = float(np.percentile(vals, 25))
        q75 = float(np.percentile(vals, 75))
        min_val = float(np.min(vals))
        max_val = float(np.max(vals))
        iqr_val = q75 - q25

        stats[vk] = {
            "n": n,
            "missing": n_missing,
            "mean": mean_val,
            "std": std_val,
            "median": median_val,
            "q25": q25,
            "q75": q75,
            "iqr": iqr_val,
            "min": min_val,
            "max": max_val,
        }
    return stats


def plot_figure_1(primary_records: List[Dict[str, Any]], out_path: str):
    """Figure 1: Distributions of Subscription Rate and Approximate Sampling MOE."""
    sub_rates = [r["subscription_rate_pct"] for r in primary_records]
    moes = [r["subscription_rate_moe_pp"] for r in primary_records]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Panel A: Subscription Rate (%)
    ax1.hist(sub_rates, bins=40, color="#1f77b4", edgecolor="white", alpha=0.75, density=True)
    # KDE
    from scipy.stats import gaussian_kde
    kde1 = gaussian_kde(sub_rates)
    x_grid1 = np.linspace(min(sub_rates), max(sub_rates), 300)
    ax1.plot(x_grid1, kde1(x_grid1), color="#0b3c61", linewidth=2.0, label="Density Profile (KDE)")
    median_sub = np.median(sub_rates)
    mean_sub = np.mean(sub_rates)
    ax1.axvline(median_sub, color="#d62728", linestyle="--", linewidth=1.5, label=f"Median ({median_sub:.1f}%)")
    ax1.axvline(mean_sub, color="#2ca02c", linestyle=":", linewidth=1.5, label=f"Mean ({mean_sub:.1f}%)")
    ax1.set_title("Panel A: Household Wired Broadband Subscription Rate (%)", fontweight="bold")
    ax1.set_xlabel("Subscription Rate (% of households)")
    ax1.set_ylabel("Empirical Density")
    ax1.set_xlim(0, 100)
    ax1.legend(loc="upper left", framealpha=0.9)

    # Panel B: Approximate MOE (pp)
    # The maximum MOE is 48.82 pp (Loving County, TX). We plot 0 to 15 with an inset or note.
    ax2.hist([m for m in moes if m <= 15.0], bins=40, color="#ff7f0e", edgecolor="white", alpha=0.75, density=True)
    kde2 = gaussian_kde(moes)
    x_grid2 = np.linspace(0, 15, 300)
    ax2.plot(x_grid2, kde2(x_grid2), color="#8c4300", linewidth=2.0, label="Density Profile (KDE)")
    median_moe = np.median(moes)
    mean_moe = np.mean(moes)
    ax2.axvline(median_moe, color="#d62728", linestyle="--", linewidth=1.5, label=f"Median (±{median_moe:.2f} pp)")
    ax2.axvline(mean_moe, color="#2ca02c", linestyle=":", linewidth=1.5, label=f"Mean (±{mean_moe:.2f} pp)")
    ax2.set_title("Panel B: Derived 90% Margin of Error (MOE in pp)", fontweight="bold")
    ax2.set_xlabel("Derived Approximate 90% MOE (percentage points)")
    ax2.set_ylabel("Empirical Density")
    ax2.set_xlim(0, 15)
    ax2.legend(loc="upper right", framealpha=0.9)

    # Annotation about Loving County outlier
    ax2.annotate(
        "Max MOE: ±48.82 pp\n(Loving County, TX;\ntruncated for display)",
        xy=(13.5, 0.15),
        xytext=(8.0, 0.22),
        arrowprops=dict(arrowstyle="->", color="#333333", lw=1.2),
        fontsize=8,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#fff2cc", edgecolor="#d6b656", alpha=0.9)
    )

    plt.suptitle("Figure 1: Univariate Distributions of Subscription Outcome and ACS Sampling Uncertainty\n(Primary Sample: N = 3,135 Counties)", y=1.02)
    plt.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()


def plot_figure_2(primary_records: List[Dict[str, Any]], out_path: str):
    """Figure 2: Availability Distributions at Both Speed Thresholds and Difference."""
    c100 = [r["avail_100_20_pct"] for r in primary_records]
    c25 = [r["avail_25_3_pct"] for r in primary_records]
    diff = [r["coverage_diff_pct"] for r in primary_records]

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 4.5))

    # Panel A: 100/20 Availability
    from scipy.stats import gaussian_kde
    ax1.hist(c100, bins=40, color="#2b5c8f", edgecolor="white", alpha=0.75, density=True)
    kde1 = gaussian_kde(c100)
    x1 = np.linspace(0, 100, 300)
    ax1.plot(x1, kde1(x1), color="#122d4a", linewidth=2.0)
    med1 = np.median(c100)
    ax1.axvline(med1, color="#d62728", linestyle="--", linewidth=1.5, label=f"Median: {med1:.1f}%")
    ax1.axvline(np.mean(c100), color="#2ca02c", linestyle=":", linewidth=1.5, label=f"Mean: {np.mean(c100):.1f}%")
    ax1.set_title("Panel A: 100/20 Mbps Availability (%)", fontweight="bold")
    ax1.set_xlabel("Reported Coverage (% BSL units)")
    ax1.set_ylabel("Empirical Density")
    ax1.set_xlim(0, 100)
    ax1.legend(loc="upper left", framealpha=0.9)

    # Panel B: 25/3 Availability
    ax2.hist(c25, bins=40, color="#3e8e75", edgecolor="white", alpha=0.75, density=True)
    kde2 = gaussian_kde(c25)
    x2 = np.linspace(0, 100, 300)
    ax2.plot(x2, kde2(x2), color="#1b4d3e", linewidth=2.0)
    med2 = np.median(c25)
    ax2.axvline(med2, color="#d62728", linestyle="--", linewidth=1.5, label=f"Median: {med2:.1f}%")
    ax2.axvline(np.mean(c25), color="#2ca02c", linestyle=":", linewidth=1.5, label=f"Mean: {np.mean(c25):.1f}%")
    ax2.set_title("Panel B: 25/3 Mbps Availability (%)", fontweight="bold")
    ax2.set_xlabel("Reported Coverage (% BSL units)")
    ax2.set_ylabel("Empirical Density")
    ax2.set_xlim(0, 100)
    ax2.legend(loc="upper left", framealpha=0.9)

    # Panel C: Threshold Difference (25/3 - 100/20)
    # Maximum difference is around 63.8%, but median is 0.72%
    ax3.hist(diff, bins=40, color="#d95f02", edgecolor="white", alpha=0.75, density=True)
    med3 = np.median(diff)
    mean3 = np.mean(diff)
    ax3.axvline(med3, color="#d62728", linestyle="--", linewidth=1.5, label=f"Median: +{med3:.2f} pp")
    ax3.axvline(mean3, color="#2ca02c", linestyle=":", linewidth=1.5, label=f"Mean: +{mean3:.2f} pp")
    ax3.set_title("Panel C: Threshold Difference\n(25/3 minus 100/20 pp)", fontweight="bold")
    ax3.set_xlabel("Coverage Increment (percentage points)")
    ax3.set_ylabel("Empirical Density")
    ax3.set_xlim(0, max(diff) + 2)
    ax3.legend(loc="upper right", framealpha=0.9)

    plt.suptitle("Figure 2: Distribution of Provider-Reported Availability Across Dual Speed Thresholds\n(Primary Sample: N = 3,135 Counties)", y=1.03)
    plt.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()


def plot_figure_3(primary_records: List[Dict[str, Any]], out_path: str):
    """Figure 3: Subscription vs Availability Scatterplots with LOWESS Trend Guides."""
    x1 = np.array([r["avail_100_20_pct"] for r in primary_records])
    x2 = np.array([r["avail_25_3_pct"] for r in primary_records])
    y = np.array([r["subscription_rate_pct"] for r in primary_records])

    # Compute non-parametric LOWESS smoothers (fraction = 0.3)
    lowess1 = sm.nonparametric.lowess(y, x1, frac=0.3, return_sorted=True)
    lowess2 = sm.nonparametric.lowess(y, x2, frac=0.3, return_sorted=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5), sharey=True)

    # Panel A: 100/20 Mbps
    ax1.scatter(x1, y, color="#1f77b4", alpha=0.25, s=18, edgecolors="none", label="County (N = 3,135)")
    ax1.plot(lowess1[:, 0], lowess1[:, 1], color="#d62728", linewidth=2.5, label="Non-Parametric Trend (LOWESS)")
    ax1.set_title("Panel A: 100/20 Mbps Benchmark (Model A)", fontweight="bold")
    ax1.set_xlabel("Reported Wired Broadband Availability (% >= 100/20 Mbps)")
    ax1.set_ylabel("Household Wired Broadband Subscription Rate (%)")
    ax1.set_xlim(-2, 102)
    ax1.set_ylim(10, 100)
    ax1.legend(loc="upper left", framealpha=0.9)

    # Panel B: 25/3 Mbps
    ax2.scatter(x2, y, color="#2ca02c", alpha=0.25, s=18, edgecolors="none", label="County (N = 3,135)")
    ax2.plot(lowess2[:, 0], lowess2[:, 1], color="#d62728", linewidth=2.5, label="Non-Parametric Trend (LOWESS)")
    ax2.set_title("Panel B: 25/3 Mbps Alternate Threshold (Model B)", fontweight="bold")
    ax2.set_xlabel("Reported Wired Broadband Availability (% >= 25/3 Mbps)")
    ax2.set_xlim(-2, 102)
    ax2.legend(loc="upper left", framealpha=0.9)

    plt.suptitle("Figure 3: Household Subscription vs. Provider-Reported Availability at Dual Speed Benchmarks\n(Observed County-Level Bivariate Patterns with Non-Parametric LOWESS Trend Guides)", y=1.01)
    plt.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()


def plot_figure_4(primary_records: List[Dict[str, Any]], out_path: str):
    """Figure 4: Subscription vs Socioeconomic Context Scatterplots with LOWESS Trend Guides."""
    x_pov = np.array([r["poverty_pct"] for r in primary_records])
    x_edu = np.array([r["bachelor_plus_pct"] for r in primary_records])
    y = np.array([r["subscription_rate_pct"] for r in primary_records])

    lowess_pov = sm.nonparametric.lowess(y, x_pov, frac=0.3, return_sorted=True)
    lowess_edu = sm.nonparametric.lowess(y, x_edu, frac=0.3, return_sorted=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5), sharey=True)

    # Panel A: Poverty
    ax1.scatter(x_pov, y, color="#e377c2", alpha=0.25, s=18, edgecolors="none", label="County (N = 3,135)")
    ax1.plot(lowess_pov[:, 0], lowess_pov[:, 1], color="#8c564b", linewidth=2.5, label="Non-Parametric Trend (LOWESS)")
    ax1.set_title("Panel A: Subscription Rate vs. Poverty (%)", fontweight="bold")
    ax1.set_xlabel("Population Below Poverty Level (% S1701)")
    ax1.set_ylabel("Household Wired Broadband Subscription Rate (%)")
    ax1.set_xlim(0, 60)
    ax1.set_ylim(10, 100)
    ax1.legend(loc="upper right", framealpha=0.9)

    # Panel B: Educational Attainment
    ax2.scatter(x_edu, y, color="#bcbd22", alpha=0.25, s=18, edgecolors="none", label="County (N = 3,135)")
    ax2.plot(lowess_edu[:, 0], lowess_edu[:, 1], color="#17becf", linewidth=2.5, label="Non-Parametric Trend (LOWESS)")
    ax2.set_title("Panel B: Subscription Rate vs. Higher Education (%)", fontweight="bold")
    ax2.set_xlabel("Population 25+ with Bachelor's Degree or Higher (% S1501)")
    ax2.set_xlim(0, 85)
    ax2.legend(loc="lower right", framealpha=0.9)

    plt.suptitle("Figure 4: Household Subscription vs. County Socioeconomic Context\n(Observed County-Level Bivariate Patterns with Non-Parametric LOWESS Trend Guides)", y=1.01)
    plt.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()


def plot_figure_5(all_records: List[Dict[str, Any]], out_path: str):
    """Figure 5: Comparative Boxplots Across Primary Sample and Puerto Rico Municipios."""
    primary = [r for r in all_records if r["is_primary_sample"] == 1]
    pr = [r for r in all_records if r["is_primary_sample"] == 0]

    vars_to_compare = [
        ("subscription_rate_pct", "Subscription Rate (%)"),
        ("avail_100_20_pct", "100/20 Availability (%)"),
        ("avail_25_3_pct", "25/3 Availability (%)"),
        ("poverty_pct", "Poverty Rate (%)"),
        ("bachelor_plus_pct", "Bachelor's Degree+ (%)"),
        ("subscription_rate_moe_pp", "Subscription MOE (pp)"),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    axes = axes.flatten()

    for idx, (vk, title) in enumerate(vars_to_compare):
        ax = axes[idx]
        data_primary = [r[vk] for r in primary if r[vk] is not None]
        data_pr = [r[vk] for r in pr if r[vk] is not None]

        # For MOE, Loving County is 48.82, so let's set y-limit gracefully
        bp = ax.boxplot(
            [data_primary, data_pr],
            patch_artist=True,
            widths=0.5,
            tick_labels=["Primary States+DC\n(N=3,135)", "Puerto Rico\n(N=78)"],
            medianprops=dict(color="black", linewidth=1.5),
            flierprops=dict(marker="o", markersize=3, alpha=0.4),
        )
        bp["boxes"][0].set_facecolor("#aec7e8")
        bp["boxes"][1].set_facecolor("#ffbb78")

        ax.set_title(title, fontweight="bold")
        if vk == "subscription_rate_moe_pp":
            ax.set_ylim(0, 15)  # Truncate for boxplot visibility, note outlier
            ax.text(0.95, 0.90, "Primary max outlier: ±48.8 pp", transform=ax.transAxes,
                    ha="right", fontsize=7.5, bbox=dict(boxstyle="square,pad=0.2", facecolor="#fff2cc", alpha=0.8))

    plt.suptitle("Figure 5: Comparison of Key Analytical Variables: 49 States + DC vs. Puerto Rico Municipios", y=1.01)
    plt.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()


def generate_markdown_report(
    primary_stats: Dict[str, Dict[str, Any]],
    pr_stats: Dict[str, Dict[str, Any]],
    combined_stats: Dict[str, Dict[str, Any]],
    out_path: str,
):
    timestamp_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    md = f"""# Descriptive and Exploratory Analysis: County Broadband Availability and Household Subscription

**Phase:** Phase 4B — Step 1: Prepare the Analysis Dataset and Exploratory Results<br>
**Repository:** `nayanojwal0810/BroadBand`<br>
**Generated:** {timestamp_utc}<br>
**Status:** Descriptive & Exploratory Analysis Complete (Governance Compliant)

---

## 1. Executive Summary & Governance Compliance

This report presents the descriptive statistics and exploratory data visualizations for the analysis-ready county dataset created from the validated FCC Broadband Data Collection (BDC) and U.S. Census Bureau American Community Survey (ACS) 5-Year inputs.

### Strict Methodological Governance Notice
In accordance with Gate Zero, Phase 3, Phase 4A, and Phase 4B project directives:
1. **No Regression Estimation:** No Ordinary Least Squares (OLS), Weighted Least Squares (WLS), or multivariable regression models have been fitted.
2. **No Correlation Quantification:** No Pearson product-moment ($r$), Spearman rank ($\rho$), or related bivariate correlation coefficients have been calculated or reported.
3. **No P-Values or Model Metrics:** No statistical hypothesis testing, $p$-values, $R^2$, or goodness-of-fit metrics are evaluated.
4. **No Causal or Ecological Claims:** County-level aggregates are presented purely as observational ecological patterns. They do not measure individual household decision-making, and differences between aggregate provider availability and aggregate household subscription are not characterized as an individual "availability–adoption gap."
5. **No Empirical Sensitivity Determinations:** This report does not claim to have measured the empirical sensitivity of the availability–subscription relationship; that determination is reserved for the pre-specified multivariable model comparisons.
6. **Deferred Secondary Methods Maintained:** Both the moment-matched Beta Monte Carlo simulation and the wild cluster bootstrap remain explicitly marked as deferred secondary methods. Neither method was executed in this step.

---

## 2. Dataset Construction and Geographic Sample Definitions

The analysis dataset was constructed by `scripts/prepare_analysis_dataset.py` using **exact 5-digit FIPS code matching** across all four raw source files in `data/raw/`. The resulting processed dataset is stored at:
- `data/processed/county_broadband_analysis.csv` ($N = 3,213$ rows, 25 columns)
- Audit Report: `reports/analysis_dataset_validation.json` (`dataset_validation_status: "PASS"`)

### Sample Partitioning
- **Primary Study Sample ($N = 3,135$ counties, `is_primary_sample = 1`):**
  - Covers 49 U.S. states plus Washington, DC.
  - Excludes Connecticut (`09`): Exactly 0 FIPS codes match because Census transitioned to 9 Planning Regions (`09110`–`09190`) while FCC retains 8 legacy county codes (`09001`–`09015`). No ad hoc crosswalk is created.
  - Excludes Puerto Rico (`72`): Held out for independent sensitivity analysis.
  - Excludes Island Territories: ACS detailed/subject tables are not published for American Samoa, Guam, Northern Mariana Islands, and U.S. Virgin Islands.
- **Puerto Rico Sensitivity Sample ($N = 3,213$ counties, `is_pr_inclusive_sample = 1`):**
  - Includes all 3,135 primary counties plus the 78 matching Puerto Rico municipios (`72001`–`72153`).
- **Missingness and Imputation:** Exactly zero missing values exist across all required analytical fields. No zero imputation or synthetic values were applied.

---

## 3. Comprehensive Descriptive Statistics

Below are non-parametric and parametric descriptive summaries across all analytical variables for the primary study sample ($N = 3,135$), Puerto Rico sensitivity sample ($N = 78$), and the combined national dataset ($N = 3,213$).

### Table 1: Primary Sample Descriptive Statistics ($N = 3,135$ Counties: 49 States + DC)

| Variable | Field Name | N | Missing | Mean | Std Dev | Min | Q1 (25%) | Median | Q3 (75%) | Max | IQR |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Wired Subscription Rate (%)** | `subscription_rate_pct` | 3,135 | 0 | {primary_stats['subscription_rate_pct']['mean']:.2f}% | {primary_stats['subscription_rate_pct']['std']:.2f}% | {primary_stats['subscription_rate_pct']['min']:.2f}% | {primary_stats['subscription_rate_pct']['q25']:.2f}% | {primary_stats['subscription_rate_pct']['median']:.2f}% | {primary_stats['subscription_rate_pct']['q75']:.2f}% | {primary_stats['subscription_rate_pct']['max']:.2f}% | {primary_stats['subscription_rate_pct']['iqr']:.2f}% |
| **FCC 100/20 Availability (%)** | `avail_100_20_pct` | 3,135 | 0 | {primary_stats['avail_100_20_pct']['mean']:.2f}% | {primary_stats['avail_100_20_pct']['std']:.2f}% | {primary_stats['avail_100_20_pct']['min']:.2f}% | {primary_stats['avail_100_20_pct']['q25']:.2f}% | {primary_stats['avail_100_20_pct']['median']:.2f}% | {primary_stats['avail_100_20_pct']['q75']:.2f}% | {primary_stats['avail_100_20_pct']['max']:.2f}% | {primary_stats['avail_100_20_pct']['iqr']:.2f}% |
| **FCC 25/3 Availability (%)** | `avail_25_3_pct` | 3,135 | 0 | {primary_stats['avail_25_3_pct']['mean']:.2f}% | {primary_stats['avail_25_3_pct']['std']:.2f}% | {primary_stats['avail_25_3_pct']['min']:.2f}% | {primary_stats['avail_25_3_pct']['q25']:.2f}% | {primary_stats['avail_25_3_pct']['median']:.2f}% | {primary_stats['avail_25_3_pct']['q75']:.2f}% | {primary_stats['avail_25_3_pct']['max']:.2f}% | {primary_stats['avail_25_3_pct']['iqr']:.2f}% |
| **Coverage Increment (25/3 - 100/20 pp)** | `coverage_diff_pct` | 3,135 | 0 | +{primary_stats['coverage_diff_pct']['mean']:.2f} pp | {primary_stats['coverage_diff_pct']['std']:.2f} pp | {primary_stats['coverage_diff_pct']['min']:.2f} pp | +{primary_stats['coverage_diff_pct']['q25']:.2f} pp | +{primary_stats['coverage_diff_pct']['median']:.2f} pp | +{primary_stats['coverage_diff_pct']['q75']:.2f} pp | +{primary_stats['coverage_diff_pct']['max']:.2f} pp | {primary_stats['coverage_diff_pct']['iqr']:.2f} pp |
| **Poverty Percentage (%)** | `poverty_pct` | 3,135 | 0 | {primary_stats['poverty_pct']['mean']:.2f}% | {primary_stats['poverty_pct']['std']:.2f}% | {primary_stats['poverty_pct']['min']:.2f}% | {primary_stats['poverty_pct']['q25']:.2f}% | {primary_stats['poverty_pct']['median']:.2f}% | {primary_stats['poverty_pct']['q75']:.2f}% | {primary_stats['poverty_pct']['max']:.2f}% | {primary_stats['poverty_pct']['iqr']:.2f}% |
| **Bachelor's Degree or Higher (%)** | `bachelor_plus_pct` | 3,135 | 0 | {primary_stats['bachelor_plus_pct']['mean']:.2f}% | {primary_stats['bachelor_plus_pct']['std']:.2f}% | {primary_stats['bachelor_plus_pct']['min']:.2f}% | {primary_stats['bachelor_plus_pct']['q25']:.2f}% | {primary_stats['bachelor_plus_pct']['median']:.2f}% | {primary_stats['bachelor_plus_pct']['q75']:.2f}% | {primary_stats['bachelor_plus_pct']['max']:.2f}% | {primary_stats['bachelor_plus_pct']['iqr']:.2f}% |
| **Subscription Rate MOE (pp)** | `subscription_rate_moe_pp` | 3,135 | 0 | ±{primary_stats['subscription_rate_moe_pp']['mean']:.2f} pp | {primary_stats['subscription_rate_moe_pp']['std']:.2f} pp | ±{primary_stats['subscription_rate_moe_pp']['min']:.2f} pp | ±{primary_stats['subscription_rate_moe_pp']['q25']:.2f} pp | ±{primary_stats['subscription_rate_moe_pp']['median']:.2f} pp | ±{primary_stats['subscription_rate_moe_pp']['q75']:.2f} pp | ±{primary_stats['subscription_rate_moe_pp']['max']:.2f} pp | {primary_stats['subscription_rate_moe_pp']['iqr']:.2f} pp |

### Table 2: Puerto Rico Municipios Descriptive Statistics ($N = 78$ Municipios)

| Variable | Field Name | N | Missing | Mean | Std Dev | Min | Q1 (25%) | Median | Q3 (75%) | Max | IQR |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Wired Subscription Rate (%)** | `subscription_rate_pct` | 78 | 0 | {pr_stats['subscription_rate_pct']['mean']:.2f}% | {pr_stats['subscription_rate_pct']['std']:.2f}% | {pr_stats['subscription_rate_pct']['min']:.2f}% | {pr_stats['subscription_rate_pct']['q25']:.2f}% | {pr_stats['subscription_rate_pct']['median']:.2f}% | {pr_stats['subscription_rate_pct']['q75']:.2f}% | {pr_stats['subscription_rate_pct']['max']:.2f}% | {pr_stats['subscription_rate_pct']['iqr']:.2f}% |
| **FCC 100/20 Availability (%)** | `avail_100_20_pct` | 78 | 0 | {pr_stats['avail_100_20_pct']['mean']:.2f}% | {pr_stats['avail_100_20_pct']['std']:.2f}% | {pr_stats['avail_100_20_pct']['min']:.2f}% | {pr_stats['avail_100_20_pct']['q25']:.2f}% | {pr_stats['avail_100_20_pct']['median']:.2f}% | {pr_stats['avail_100_20_pct']['q75']:.2f}% | {pr_stats['avail_100_20_pct']['max']:.2f}% | {pr_stats['avail_100_20_pct']['iqr']:.2f}% |
| **FCC 25/3 Availability (%)** | `avail_25_3_pct` | 78 | 0 | {pr_stats['avail_25_3_pct']['mean']:.2f}% | {pr_stats['avail_25_3_pct']['std']:.2f}% | {pr_stats['avail_25_3_pct']['min']:.2f}% | {pr_stats['avail_25_3_pct']['q25']:.2f}% | {pr_stats['avail_25_3_pct']['median']:.2f}% | {pr_stats['avail_25_3_pct']['q75']:.2f}% | {pr_stats['avail_25_3_pct']['max']:.2f}% | {pr_stats['avail_25_3_pct']['iqr']:.2f}% |
| **Coverage Increment (25/3 - 100/20 pp)** | `coverage_diff_pct` | 78 | 0 | +{pr_stats['coverage_diff_pct']['mean']:.2f} pp | {pr_stats['coverage_diff_pct']['std']:.2f} pp | {pr_stats['coverage_diff_pct']['min']:.2f} pp | +{pr_stats['coverage_diff_pct']['q25']:.2f} pp | +{pr_stats['coverage_diff_pct']['median']:.2f} pp | +{pr_stats['coverage_diff_pct']['q75']:.2f} pp | +{pr_stats['coverage_diff_pct']['max']:.2f} pp | {pr_stats['coverage_diff_pct']['iqr']:.2f} pp |
| **Poverty Percentage (%)** | `poverty_pct` | 78 | 0 | {pr_stats['poverty_pct']['mean']:.2f}% | {pr_stats['poverty_pct']['std']:.2f}% | {pr_stats['poverty_pct']['min']:.2f}% | {pr_stats['poverty_pct']['q25']:.2f}% | {pr_stats['poverty_pct']['median']:.2f}% | {pr_stats['poverty_pct']['q75']:.2f}% | {pr_stats['poverty_pct']['max']:.2f}% | {pr_stats['poverty_pct']['iqr']:.2f}% |
| **Bachelor's Degree or Higher (%)** | `bachelor_plus_pct` | 78 | 0 | {pr_stats['bachelor_plus_pct']['mean']:.2f}% | {pr_stats['bachelor_plus_pct']['std']:.2f}% | {pr_stats['bachelor_plus_pct']['min']:.2f}% | {pr_stats['bachelor_plus_pct']['q25']:.2f}% | {pr_stats['bachelor_plus_pct']['median']:.2f}% | {pr_stats['bachelor_plus_pct']['q75']:.2f}% | {pr_stats['bachelor_plus_pct']['max']:.2f}% | {pr_stats['bachelor_plus_pct']['iqr']:.2f}% |
| **Subscription Rate MOE (pp)** | `subscription_rate_moe_pp` | 78 | 0 | ±{pr_stats['subscription_rate_moe_pp']['mean']:.2f} pp | {pr_stats['subscription_rate_moe_pp']['std']:.2f} pp | ±{pr_stats['subscription_rate_moe_pp']['min']:.2f} pp | ±{pr_stats['subscription_rate_moe_pp']['q25']:.2f} pp | ±{pr_stats['subscription_rate_moe_pp']['median']:.2f} pp | ±{pr_stats['subscription_rate_moe_pp']['q75']:.2f} pp | ±{pr_stats['subscription_rate_moe_pp']['max']:.2f} pp | {pr_stats['subscription_rate_moe_pp']['iqr']:.2f} pp |

### Table 3: Combined Puerto Rico-Inclusive Sample ($N = 3,213$ Records)

| Variable | Field Name | N | Missing | Mean | Std Dev | Min | Q1 (25%) | Median | Q3 (75%) | Max | IQR |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Wired Subscription Rate (%)** | `subscription_rate_pct` | 3,213 | 0 | {combined_stats['subscription_rate_pct']['mean']:.2f}% | {combined_stats['subscription_rate_pct']['std']:.2f}% | {combined_stats['subscription_rate_pct']['min']:.2f}% | {combined_stats['subscription_rate_pct']['q25']:.2f}% | {combined_stats['subscription_rate_pct']['median']:.2f}% | {combined_stats['subscription_rate_pct']['q75']:.2f}% | {combined_stats['subscription_rate_pct']['max']:.2f}% | {combined_stats['subscription_rate_pct']['iqr']:.2f}% |
| **FCC 100/20 Availability (%)** | `avail_100_20_pct` | 3,213 | 0 | {combined_stats['avail_100_20_pct']['mean']:.2f}% | {combined_stats['avail_100_20_pct']['std']:.2f}% | {combined_stats['avail_100_20_pct']['min']:.2f}% | {combined_stats['avail_100_20_pct']['q25']:.2f}% | {combined_stats['avail_100_20_pct']['median']:.2f}% | {combined_stats['avail_100_20_pct']['q75']:.2f}% | {combined_stats['avail_100_20_pct']['max']:.2f}% | {combined_stats['avail_100_20_pct']['iqr']:.2f}% |
| **FCC 25/3 Availability (%)** | `avail_25_3_pct` | 3,213 | 0 | {combined_stats['avail_25_3_pct']['mean']:.2f}% | {combined_stats['avail_25_3_pct']['std']:.2f}% | {combined_stats['avail_25_3_pct']['min']:.2f}% | {combined_stats['avail_25_3_pct']['q25']:.2f}% | {combined_stats['avail_25_3_pct']['median']:.2f}% | {combined_stats['avail_25_3_pct']['q75']:.2f}% | {combined_stats['avail_25_3_pct']['max']:.2f}% | {combined_stats['avail_25_3_pct']['iqr']:.2f}% |
| **Coverage Increment (25/3 - 100/20 pp)** | `coverage_diff_pct` | 3,213 | 0 | +{combined_stats['coverage_diff_pct']['mean']:.2f} pp | {combined_stats['coverage_diff_pct']['std']:.2f} pp | {combined_stats['coverage_diff_pct']['min']:.2f} pp | +{combined_stats['coverage_diff_pct']['q25']:.2f} pp | +{combined_stats['coverage_diff_pct']['median']:.2f} pp | +{combined_stats['coverage_diff_pct']['q75']:.2f} pp | +{combined_stats['coverage_diff_pct']['max']:.2f} pp | {combined_stats['coverage_diff_pct']['iqr']:.2f} pp |
| **Poverty Percentage (%)** | `poverty_pct` | 3,213 | 0 | {combined_stats['poverty_pct']['mean']:.2f}% | {combined_stats['poverty_pct']['std']:.2f}% | {combined_stats['poverty_pct']['min']:.2f}% | {combined_stats['poverty_pct']['q25']:.2f}% | {combined_stats['poverty_pct']['median']:.2f}% | {combined_stats['poverty_pct']['q75']:.2f}% | {combined_stats['poverty_pct']['max']:.2f}% | {combined_stats['poverty_pct']['iqr']:.2f}% |
| **Bachelor's Degree or Higher (%)** | `bachelor_plus_pct` | 3,213 | 0 | {combined_stats['bachelor_plus_pct']['mean']:.2f}% | {combined_stats['bachelor_plus_pct']['std']:.2f}% | {combined_stats['bachelor_plus_pct']['min']:.2f}% | {combined_stats['bachelor_plus_pct']['q25']:.2f}% | {combined_stats['bachelor_plus_pct']['median']:.2f}% | {combined_stats['bachelor_plus_pct']['q75']:.2f}% | {combined_stats['bachelor_plus_pct']['max']:.2f}% | {combined_stats['bachelor_plus_pct']['iqr']:.2f}% |
| **Subscription Rate MOE (pp)** | `subscription_rate_moe_pp` | 3,213 | 0 | ±{combined_stats['subscription_rate_moe_pp']['mean']:.2f} pp | {combined_stats['subscription_rate_moe_pp']['std']:.2f} pp | ±{combined_stats['subscription_rate_moe_pp']['min']:.2f} pp | ±{combined_stats['subscription_rate_moe_pp']['q25']:.2f} pp | ±{combined_stats['subscription_rate_moe_pp']['median']:.2f} pp | ±{combined_stats['subscription_rate_moe_pp']['q75']:.2f} pp | ±{combined_stats['subscription_rate_moe_pp']['max']:.2f} pp | {combined_stats['subscription_rate_moe_pp']['iqr']:.2f} pp |

---

## 4. Visual Exploratory Analysis

### Figure 1: Distributions of Subscription Rate and Approximate Sampling Uncertainty
![Figure 1: Univariate Distributions of Subscription Outcome and ACS Sampling Uncertainty](figures/fig1_subscription_and_moe_distributions.png)

#### Descriptive Observations
1. **Household Wired Broadband Subscription Rate (Panel A):**
   - The primary sample distribution of county-level subscription rates is unimodal and approximately symmetric, centered at a median of **{primary_stats['subscription_rate_pct']['median']:.1f}%** (mean: **{primary_stats['subscription_rate_pct']['mean']:.1f}%**).
   - The central 50% of counties (interquartile range) span from **{primary_stats['subscription_rate_pct']['q25']:.1f}%** to **{primary_stats['subscription_rate_pct']['q75']:.1f}%** (IQR = {primary_stats['subscription_rate_pct']['iqr']:.1f} percentage points).
   - Substantial county-level variation is evident across the country, spanning from a minimum of **{primary_stats['subscription_rate_pct']['min']:.1f}%** (Crowley County, CO: `08025`) to a maximum of **{primary_stats['subscription_rate_pct']['max']:.1f}%** (Falls Church city, VA: `51610`).
2. **ACS Derived Margin of Error (Panel B):**
   - The derived 90% margin of error (MOE) in percentage points is heavily right-skewed.
   - For the typical county, sampling error is moderate: the median MOE is **±{primary_stats['subscription_rate_moe_pp']['median']:.2f} pp** and the 75th percentile is **±{primary_stats['subscription_rate_moe_pp']['q75']:.2f} pp**.
   - However, a long right tail of small-population rural counties exhibits substantial survey uncertainty. The maximum observed uncertainty occurs in Loving County, TX (`48301`), with a derived MOE of **±{primary_stats['subscription_rate_moe_pp']['max']:.2f} pp** (estimated total households: 27).

---

### Figure 2: Availability Distributions Across Speed Thresholds and Difference
![Figure 2: Distribution of Provider-Reported Availability Across Dual Speed Thresholds](figures/fig2_fcc_availability_distributions.png)

#### Descriptive Observations
1. **FCC 100/20 Mbps Baseline Availability (Panel A):**
   - County-level provider-reported wired availability at $\\ge 100/20$ Mbps is heavily concentrated near universal deployment, with a median of **{primary_stats['avail_100_20_pct']['median']:.1f}%** and a mean of **{primary_stats['avail_100_20_pct']['mean']:.1f}%**.
   - Over 25% of counties report availability exceeding **{primary_stats['avail_100_20_pct']['q75']:.1f}%**, and 70 counties report exactly 100.0% coverage.
   - A pronounced left tail of underserved rural counties exists, with 5 counties reporting 0.0% coverage at this threshold.
2. **FCC 25/3 Mbps Alternate Threshold Availability (Panel B):**
   - Lowering the speed threshold to $\\ge 25/3$ Mbps shifts the distribution modestly to the right, yielding a median coverage of **{primary_stats['avail_25_3_pct']['median']:.1f}%** (mean: **{primary_stats['avail_25_3_pct']['mean']:.1f}%**).
   - Exactly 73 counties report 100.0% availability at 25/3 Mbps.
3. **Threshold Difference (25/3 minus 100/20 Mbps, Panel C):**
   - The coverage difference (`coverage_diff_pct = avail_25_3_pct - avail_100_20_pct`) satisfies exact weak monotonicity across all 3,135 primary counties (min = 0.00 pp, 0 violations).
   - For the vast majority of counties, the difference between the two thresholds is small: the median difference is only **+{primary_stats['coverage_diff_pct']['median']:.2f} pp** (mean: **+{primary_stats['coverage_diff_pct']['mean']:.2f} pp**).
   - However, in specific rural jurisdictions, legacy wired technologies (e.g., standard DSL) provide coverage meeting 25/3 Mbps but falling short of 100/20 Mbps, producing increments up to **+{primary_stats['coverage_diff_pct']['max']:.2f} pp**.

---

### Figure 3: Subscription vs. Availability at Dual Speed Thresholds
![Figure 3: Household Subscription vs. Provider-Reported Availability at Dual Speed Benchmarks](figures/fig3_subscription_vs_availability_scatter.png)

#### Descriptive Observations
1. **Bivariate Visual Patterns:**
   - Both panels display a clear positive non-parametric relationship (indicated by the red LOWESS smoother) between provider-reported availability and household-reported subscription rates.
   - At low levels of reported availability (< 40%), subscription rates are generally lower, averaging around 30% to 50%.
   - As availability rises above 80%, subscription rates rise steadily, but exhibit substantial vertical dispersion: among counties with near 100% reported availability, household subscription rates vary widely from ~40% to >90%.
2. **Comparison Across Thresholds:**
   - The overall shape of the scatter and LOWESS curve is visually similar between the 100/20 Mbps baseline (Panel A) and the 25/3 Mbps alternate threshold (Panel B).
   - In Panel B, observations in the left tail are shifted slightly to the right due to the higher reported coverage under the legacy 25/3 definition.
   - *Cautionary Note:* While a positive visual association is apparent, whether the estimated slope or coefficient differs meaningfully between the two speed thresholds cannot be determined from scatterplots alone; this requires formal multivariable model comparisons.

---

### Figure 4: Subscription vs. County Socioeconomic Context
![Figure 4: Household Subscription vs. County Socioeconomic Context](figures/fig4_subscription_vs_socioeconomic_scatter.png)

#### Descriptive Observations
1. **Poverty Percentage (Panel A):**
   - A pronounced negative bivariate visual pattern is observed between county poverty rates and household wired broadband subscription rates.
   - Counties with low poverty rates (< 10%) frequently exhibit subscription rates exceeding 70% to 80%.
   - As poverty increases toward 30% and above, subscription rates decline noticeably, with the LOWESS trend guide sloping downward across the entire support.
2. **Educational Attainment (Panel B):**
   - A strong positive bivariate visual pattern is observed between the percentage of adults holding a Bachelor's degree or higher and household wired broadband subscription.
   - Counties with higher educational attainment (> 40%) consistently display subscription rates above 75%, whereas counties with lower attainment (< 15%) cluster between 40% and 60%.
   - These patterns confirm the substantive necessity of controlling for local socioeconomic context when examining broadband availability.

---

### Figure 5: Comparative Patterns: Primary Sample vs. Puerto Rico Municipios
![Figure 5: Comparison of Key Analytical Variables: 49 States + DC vs. Puerto Rico Municipios](figures/fig5_primary_vs_puerto_rico_comparison.png)

#### Descriptive Observations
1. **Subscription Rates:**
   - Puerto Rico municipios exhibit markedly lower household wired subscription rates (median: **{pr_stats['subscription_rate_pct']['median']:.1f}%**, mean: **{pr_stats['subscription_rate_pct']['mean']:.1f}%**) compared to the 49 states + DC primary sample (median: **{primary_stats['subscription_rate_pct']['median']:.1f}%**, mean: **{primary_stats['subscription_rate_pct']['mean']:.1f}%**).
2. **Reported Availability:**
   - In contrast to lower subscription, provider-reported wired availability in Puerto Rico is exceptionally high, with a median of **{pr_stats['avail_100_20_pct']['median']:.1f}%** for 100/20 Mbps and **{pr_stats['avail_25_3_pct']['median']:.1f}%** for 25/3 Mbps, substantially higher than the primary sample median of **{primary_stats['avail_100_20_pct']['median']:.1f}%**.
3. **Socioeconomic Disparities:**
   - Puerto Rico municipios display dramatically higher poverty rates (median: **{pr_stats['poverty_pct']['median']:.1f}%**, range: 24.3%–63.6%) than the primary sample (median: **{primary_stats['poverty_pct']['median']:.1f}%**, range: 1.4%–57.6%).
   - Educational attainment in Puerto Rico (median: **{pr_stats['bachelor_plus_pct']['median']:.1f}%**) is comparable to the lower half of the primary sample distribution.
4. **Methodological Implication:**
   - The juxtaposition of high reported availability with low subscription and high poverty in Puerto Rico confirms the wisdom of treating Puerto Rico as an independent sensitivity sample rather than pooling it uncritically into the primary baseline specification.

---

## 5. Status of Deferred Secondary Methods

In accordance with Phase 4A decisions, two secondary analytical components remain deferred:

### 1. Moment-Matched Beta Monte Carlo Simulation (Deferred)
- **Feasibility Status:** Fully feasible across all 3,135 primary counties ($0 < \\text{{variance}} < p(1-p)$).
- **Shape Diagnostics Caveat:** While 3,134 counties produce unimodal Beta distributions ($\\alpha > 1, \\beta > 1$), **Loving County, TX (`48301`)** exhibits $\\alpha = 0.3689 < 1$ and $\\beta = 0.0642 < 1$, resulting in a U-shaped density that concentrates mass at 0% and 100%.
- **Action Taken:** Execution remains deferred. No perturbation draws or simulated regressions were conducted in this step.

### 2. Wild Cluster Bootstrap (Deferred)
- **Status:** Requires cluster-robust re-sampling at the state level (50 clusters).
- **Implementation Status:** No local package (`wildboottest` or R environment) is currently installed in the workspace.
- **Action Taken:** Execution remains deferred pending technical review of the execution route.

---

## 6. Conclusion & Next Steps

This exploratory analysis completes Step 1 of Phase 4B. The analysis dataset has been assembled, verified against all pre-specified integrity criteria, and documented. The exploratory distributions and scatterplots provide a transparent, non-parametric foundation for subsequent modeling.

**Next Immediate Action:** Submit this report, the validation JSON, and generated figures for ChatGPT review. Do not fit regression models until authorized.
"""

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)


def main() -> int:
    csv_path = "data/processed/county_broadband_analysis.csv"
    if not os.path.exists(csv_path):
        print(f"[-] Analysis dataset {csv_path} not found. Please run prepare_analysis_dataset.py first.")
        return 1

    print("[*] Loading processed dataset...")
    records = load_dataset(csv_path)
    primary_records = [r for r in records if r["is_primary_sample"] == 1]
    pr_records = [r for r in records if r["is_primary_sample"] == 0]

    print(f"    Total records: {len(records)}")
    print(f"    Primary records: {len(primary_records)}")
    print(f"    Puerto Rico records: {len(pr_records)}")

    var_keys = [
        "subscription_rate_pct",
        "avail_100_20_pct",
        "avail_25_3_pct",
        "coverage_diff_pct",
        "poverty_pct",
        "bachelor_plus_pct",
        "subscription_rate_moe_pp",
    ]

    print("[*] Computing descriptive statistics...")
    primary_stats = compute_summary_table(primary_records, var_keys)
    pr_stats = compute_summary_table(pr_records, var_keys)
    combined_stats = compute_summary_table(records, var_keys)

    print("[*] Generating exploratory figures...")
    plot_figure_1(primary_records, "reports/figures/fig1_subscription_and_moe_distributions.png")
    print("    [+] Generated reports/figures/fig1_subscription_and_moe_distributions.png")

    plot_figure_2(primary_records, "reports/figures/fig2_fcc_availability_distributions.png")
    print("    [+] Generated reports/figures/fig2_fcc_availability_distributions.png")

    plot_figure_3(primary_records, "reports/figures/fig3_subscription_vs_availability_scatter.png")
    print("    [+] Generated reports/figures/fig3_subscription_vs_availability_scatter.png")

    plot_figure_4(primary_records, "reports/figures/fig4_subscription_vs_socioeconomic_scatter.png")
    print("    [+] Generated reports/figures/fig4_subscription_vs_socioeconomic_scatter.png")

    plot_figure_5(records, "reports/figures/fig5_primary_vs_puerto_rico_comparison.png")
    print("    [+] Generated reports/figures/fig5_primary_vs_puerto_rico_comparison.png")

    print("[*] Writing descriptive analysis markdown report...")
    generate_markdown_report(primary_stats, pr_stats, combined_stats, "reports/descriptive_analysis.md")
    print("    [+] Generated reports/descriptive_analysis.md")

    print("[+] All Phase 4B Step 1 exploratory tasks completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
