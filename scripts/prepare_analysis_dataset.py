#!/usr/bin/env python3
"""prepare_analysis_dataset.py - Phase 4B: Analysis Dataset Preparation and Validation.

Constructs the analysis-ready county dataset from the four validated raw inputs,
performs exact 5-digit FIPS joins, derives outcome rates and approximate ACS sampling
uncertainty, and writes:
  - data/processed/county_broadband_analysis.csv
  - reports/analysis_dataset_validation.json

Usage:
    python scripts/prepare_analysis_dataset.py
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Set, Tuple


FIPS_STATE_MAP = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA",
    "08": "CO", "09": "CT", "10": "DE", "11": "DC", "12": "FL",
    "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN",
    "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME",
    "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS",
    "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
    "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI",
    "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
    "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
    "56": "WY", "72": "PR",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 4B: Analysis Dataset Preparation & Validation."
    )
    parser.add_argument(
        "--fcc-100-20",
        default="data/raw/bdc_comparison_fixed_county_total_all_wired_r_100_20_D25.csv",
        help="Path to FCC 100/20 county CSV file",
    )
    parser.add_argument(
        "--fcc-25-3",
        default="data/raw/bdc_comparison_fixed_county_total_all_wired_r_25_3_D25.csv",
        help="Path to FCC 25/3 county CSV file",
    )
    parser.add_argument(
        "--census-b28002",
        default="data/raw/acs_b28002_2024_county.json",
        help="Path to Census ACS B28002 JSON file",
    )
    parser.add_argument(
        "--census-context",
        default="data/raw/acs_context_2024_county.json",
        help="Path to Census ACS Context (S1701/S1501) JSON file",
    )
    parser.add_argument(
        "--output-csv",
        default="data/processed/county_broadband_analysis.csv",
        help="Path to output processed CSV dataset",
    )
    parser.add_argument(
        "--output-json-report",
        default="reports/analysis_dataset_validation.json",
        help="Path to output validation JSON report",
    )
    return parser.parse_args()


def load_json(filepath: str) -> Any:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def build_analysis_dataset(
    fcc_100_path: str,
    fcc_25_path: str,
    b28_path: str,
    ctx_path: str,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Build the analysis dataset with exact FIPS joins and derived variables."""
    # 1. Load Census inputs
    b28_data = load_json(b28_path)
    ctx_data = load_json(ctx_path)

    b28_rows = b28_data[1:]
    ctx_rows = ctx_data[1:]

    b28_dict: Dict[str, List[str]] = {}
    for r in b28_rows:
        if len(r) == 7:
            fips = r[5] + r[6]
            b28_dict[fips] = r

    ctx_dict: Dict[str, List[str]] = {}
    for r in ctx_rows:
        if len(r) == 7:
            fips = r[5] + r[6]
            ctx_dict[fips] = r

    # 2. Load FCC inputs
    fcc_100_dict: Dict[str, Dict[str, str]] = {}
    with open(fcc_100_path, "r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            fcc_100_dict[r["geography_id"]] = r

    fcc_25_dict: Dict[str, Dict[str, str]] = {}
    with open(fcc_25_path, "r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            fcc_25_dict[r["geography_id"]] = r

    # 3. Exact common FIPS keys
    set_b28 = set(b28_dict.keys())
    set_ctx = set(ctx_dict.keys())
    set_100 = set(fcc_100_dict.keys())
    set_25 = set(fcc_25_dict.keys())

    common_fips = sorted(set_b28.intersection(set_ctx).intersection(set_100).intersection(set_25))

    records: List[Dict[str, Any]] = []
    ratio_fallback_fips: List[str] = []

    for fips in common_fips:
        st = fips[:2]
        co = fips[2:]
        is_pr = (st == "72")
        is_primary = 0 if is_pr else 1

        r_b28 = b28_dict[fips]
        r_ctx = ctx_dict[fips]
        r_100 = fcc_100_dict[fips]
        r_25 = fcc_25_dict[fips]

        name = r_b28[0]
        y_str = r_b28[1]
        moe_y_str = r_b28[2]
        x_str = r_b28[3]
        moe_x_str = r_b28[4]

        y = int(y_str)
        moe_y = int(moe_y_str)
        x = int(x_str)
        moe_x = int(moe_x_str)

        # Subscription rate
        p = float(x) / float(y)
        subscription_rate_pct = round(p * 100.0, 6)

        # Derived uncertainty propagation
        radicand = (float(moe_x) ** 2) - ((p ** 2) * (float(moe_y) ** 2))
        if radicand < 0:
            ratio_radicand = (float(moe_x) ** 2) + ((p ** 2) * (float(moe_y) ** 2))
            moe_p = (1.0 / float(y)) * math.sqrt(ratio_radicand)
            ratio_fallback = 1
            ratio_fallback_fips.append(fips)
        else:
            moe_p = (1.0 / float(y)) * math.sqrt(radicand)
            ratio_fallback = 0

        moe_pp = round(moe_p * 100.0, 6)
        se_approx_pp = round(moe_pp / 1.645, 6)

        # Socioeconomic controls
        pe = float(r_ctx[1])
        pm = float(r_ctx[2])
        be = float(r_ctx[3])
        bm = float(r_ctx[4])

        # FCC Availability predictors
        cov_100 = float(r_100["percent_coverage"])
        cov_25 = float(r_25["percent_coverage"])

        avail_100_pct = round(cov_100 * 100.0, 6)
        avail_25_pct = round(cov_25 * 100.0, 6)
        avail_100_10pp = round(cov_100 * 10.0, 6)
        avail_25_10pp = round(cov_25 * 10.0, 6)
        cov_diff_pct = round(avail_25_pct - avail_100_pct, 6)

        record = {
            "geography_id": fips,
            "geography_name": name,
            "state_fips": st,
            "county_fips": co,
            "state_abbr": FIPS_STATE_MAP.get(st, st),
            "is_primary_sample": is_primary,
            "is_pr_inclusive_sample": 1,
            "total_households": y,
            "total_households_moe": moe_y,
            "broadband_subscription": x,
            "broadband_subscription_moe": moe_x,
            "subscription_rate_pct": subscription_rate_pct,
            "subscription_rate_moe_pp": moe_pp,
            "subscription_rate_se_approx_pp": se_approx_pp,
            "ratio_fallback_applied": ratio_fallback,
            "poverty_pct": pe,
            "poverty_moe": pm,
            "bachelor_plus_pct": be,
            "bachelor_plus_moe": bm,
            "avail_100_20_pct": avail_100_pct,
            "avail_25_3_pct": avail_25_pct,
            "avail_100_20_10pp": avail_100_10pp,
            "avail_25_3_10pp": avail_25_10pp,
            "coverage_diff_pct": cov_diff_pct,
            "fcc_100_20_total_units": r_100.get("geography_type_total_units", ""),
            "fcc_25_3_total_units": r_25.get("geography_type_total_units", ""),
        }
        records.append(record)

    metadata = {
        "total_records": len(records),
        "primary_sample_count": sum(1 for r in records if r["is_primary_sample"] == 1),
        "puerto_rico_count": sum(1 for r in records if r["is_primary_sample"] == 0),
        "ratio_fallback_count": len(ratio_fallback_fips),
        "ratio_fallback_fips": ratio_fallback_fips,
    }
    return records, metadata


def validate_analysis_dataset(records: List[Dict[str, Any]], metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Validate all required integrity checks on the constructed analysis dataset."""
    total_count = len(records)
    fips_set = set(r["geography_id"] for r in records)
    primary_records = [r for r in records if r["is_primary_sample"] == 1]
    pr_records = [r for r in records if r["is_primary_sample"] == 0]

    # Required field verification
    required_fields = [
        "geography_id",
        "geography_name",
        "state_fips",
        "county_fips",
        "state_abbr",
        "is_primary_sample",
        "is_pr_inclusive_sample",
        "total_households",
        "total_households_moe",
        "broadband_subscription",
        "broadband_subscription_moe",
        "subscription_rate_pct",
        "subscription_rate_moe_pp",
        "subscription_rate_se_approx_pp",
        "ratio_fallback_applied",
        "poverty_pct",
        "poverty_moe",
        "bachelor_plus_pct",
        "bachelor_plus_moe",
        "avail_100_20_pct",
        "avail_25_3_pct",
        "avail_100_20_10pp",
        "avail_25_3_10pp",
        "coverage_diff_pct",
    ]

    missing_fields_per_record = 0
    out_of_range_sub = 0
    out_of_range_pov = 0
    out_of_range_bach = 0
    out_of_range_avail100 = 0
    out_of_range_avail25 = 0
    negative_moe = 0
    monotonicity_violations = 0
    empty_strings = 0

    for r in records:
        for f in required_fields:
            if f not in r or r[f] is None:
                missing_fields_per_record += 1
            if isinstance(r[f], str) and r[f].strip() == "":
                empty_strings += 1

        sub = r["subscription_rate_pct"]
        if not (0.0 <= sub <= 100.0) or math.isnan(sub):
            out_of_range_sub += 1

        pov = r["poverty_pct"]
        if not (0.0 <= pov <= 100.0) or math.isnan(pov):
            out_of_range_pov += 1

        bach = r["bachelor_plus_pct"]
        if not (0.0 <= bach <= 100.0) or math.isnan(bach):
            out_of_range_bach += 1

        c100 = r["avail_100_20_pct"]
        if not (0.0 <= c100 <= 100.0) or math.isnan(c100):
            out_of_range_avail100 += 1

        c25 = r["avail_25_3_pct"]
        if not (0.0 <= c25 <= 100.0) or math.isnan(c25):
            out_of_range_avail25 += 1

        moe_pp = r["subscription_rate_moe_pp"]
        if moe_pp < 0.0 or math.isnan(moe_pp) or math.isinf(moe_pp):
            negative_moe += 1

        if (c25 - c100) < -1e-6:
            monotonicity_violations += 1

    checks = {
        "expected_total_records_3213": "PASS" if total_count == 3213 else "FAIL",
        "unique_fips_keys_3213": "PASS" if len(fips_set) == 3213 else "FAIL",
        "no_duplicate_records": "PASS" if len(fips_set) == total_count else "FAIL",
        "primary_sample_count_3135": "PASS" if len(primary_records) == 3135 else "FAIL",
        "puerto_rico_count_78": "PASS" if len(pr_records) == 78 else "FAIL",
        "all_required_variables_present": "PASS" if missing_fields_per_record == 0 else "FAIL",
        "subscription_rates_in_range": "PASS" if out_of_range_sub == 0 else "FAIL",
        "poverty_rates_in_range": "PASS" if out_of_range_pov == 0 else "FAIL",
        "bachelor_rates_in_range": "PASS" if out_of_range_bach == 0 else "FAIL",
        "avail_100_20_in_range": "PASS" if out_of_range_avail100 == 0 else "FAIL",
        "avail_25_3_in_range": "PASS" if out_of_range_avail25 == 0 else "FAIL",
        "coverage_monotonicity_verified": "PASS" if monotonicity_violations == 0 else "FAIL",
        "derived_uncertainty_finite_and_nonnegative": "PASS" if negative_moe == 0 else "FAIL",
        "ratio_fallback_count_verified": "PASS" if metadata["ratio_fallback_count"] == 5 else "FAIL",
    }

    status = "PASS" if all(v == "PASS" for v in checks.values()) else "FAIL"

    def dist(vals: List[float], prec: int = 4) -> Dict[str, float]:
        s = sorted(vals)
        n = len(s)
        return {
            "count": n,
            "min": round(s[0], prec),
            "q25": round(s[n // 4], prec),
            "median": round(s[n // 2], prec),
            "q75": round(s[3 * n // 4], prec),
            "max": round(s[-1], prec),
            "mean": round(sum(s) / n, prec),
        }

    return {
        "dataset_validation_status": status,
        "sample_summary": {
            "total_records": total_count,
            "primary_sample_records": len(primary_records),
            "puerto_rico_records": len(pr_records),
            "unique_fips": len(fips_set),
            "duplicate_fips_count": total_count - len(fips_set),
        },
        "ratio_fallback_summary": {
            "count": metadata["ratio_fallback_count"],
            "fips": metadata["ratio_fallback_fips"],
        },
        "primary_sample_distributions": {
            "subscription_rate_pct": dist([r["subscription_rate_pct"] for r in primary_records], 4),
            "subscription_rate_moe_pp": dist([r["subscription_rate_moe_pp"] for r in primary_records], 4),
            "avail_100_20_pct": dist([r["avail_100_20_pct"] for r in primary_records], 4),
            "avail_25_3_pct": dist([r["avail_25_3_pct"] for r in primary_records], 4),
            "poverty_pct": dist([r["poverty_pct"] for r in primary_records], 2),
            "bachelor_plus_pct": dist([r["bachelor_plus_pct"] for r in primary_records], 2),
        },
        "puerto_rico_distributions": {
            "subscription_rate_pct": dist([r["subscription_rate_pct"] for r in pr_records], 4),
            "subscription_rate_moe_pp": dist([r["subscription_rate_moe_pp"] for r in pr_records], 4),
            "avail_100_20_pct": dist([r["avail_100_20_pct"] for r in pr_records], 4),
            "avail_25_3_pct": dist([r["avail_25_3_pct"] for r in pr_records], 4),
            "poverty_pct": dist([r["poverty_pct"] for r in pr_records], 2),
            "bachelor_plus_pct": dist([r["bachelor_plus_pct"] for r in pr_records], 2),
        },
        "checks": checks,
    }


def write_csv(records: List[Dict[str, Any]], output_path: str) -> None:
    """Write records to CSV."""
    if not records:
        return
    fieldnames = list(records[0].keys())
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow(r)


def main() -> int:
    args = parse_args()
    timestamp_utc = datetime.now(timezone.utc).isoformat()

    print("================================================================================")
    print("PHASE 4B: ANALYSIS DATASET PREPARATION & VALIDATION")
    print("================================================================================")

    print("[*] Reading source datasets and joining on exact 5-digit FIPS...")
    records, metadata = build_analysis_dataset(
        args.fcc_100_20,
        args.fcc_25_3,
        args.census_b28002,
        args.census_context,
    )
    print(f"    Total Joined Records: {metadata['total_records']}")
    print(f"    Primary Sample (N=3,135): {metadata['primary_sample_count']}")
    print(f"    Puerto Rico Municipios (N=78): {metadata['puerto_rico_count']}")
    print(f"    Ratio Fallback Counties (N=5): {metadata['ratio_fallback_count']}")

    print("[*] Validating dataset integrity...")
    val_res = validate_analysis_dataset(records, metadata)
    print(f"    Validation Status: {val_res['dataset_validation_status']}")

    print(f"[*] Writing analysis dataset to {args.output_csv}...")
    write_csv(records, args.output_csv)
    print(f"    [+] Saved {len(records)} rows to {args.output_csv}")

    validation_report = {
        "metadata": {
            "validation_timestamp_utc": timestamp_utc,
            "project": "County-Level Broadband Availability and Household Subscription Analysis",
            "phase": "Phase 4B - Step 1 Analysis Dataset Preparation & Validation",
            "output_dataset_csv": args.output_csv,
            "source_inputs": {
                "fcc_100_20": args.fcc_100_20,
                "fcc_25_3": args.fcc_25_3,
                "census_b28002": args.census_b28002,
                "census_context": args.census_context,
            },
            "governance_notice": (
                "Validation certifies exact dataset alignment, valid numeric bounds, and absence of "
                "missing-value imputation. No models or regressions have been estimated."
            ),
        },
        **val_res,
    }

    os.makedirs(os.path.dirname(args.output_json_report), exist_ok=True)
    with open(args.output_json_report, "w", encoding="utf-8") as f:
        json.dump(validation_report, f, indent=2)
    print(f"    [+] Saved validation report to {args.output_json_report}")

    print("================================================================================")
    print(f"PREPARATION & VALIDATION RESULT: {val_res['dataset_validation_status']}")
    print("================================================================================")
    return 0 if val_res["dataset_validation_status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
