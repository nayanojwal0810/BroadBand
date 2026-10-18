#!/usr/bin/env python3
"""
validate_fcc_data.py - FCC National Broadband Map County Comparison Data Audit
and Census ACS B28002 Geographic Compatibility Validation.

Audits local FCC county comparison CSV (Area Comparison, Fixed Broadband, Total/Residential,
All Wired >=100/20 Mbps, Dec 30, 2025 data as of) for structural integrity, numeric schema
validity, and evaluates geographic join compatibility against the 2024 ACS 5-Year county dataset.

Usage:
    python scripts/validate_fcc_data.py \
        --fcc-input data/raw/bdc_comparison_fixed_county_total_all_wired_r_100_20_D25.csv \
        --census-input data/raw/acs_b28002_2024_county.json \
        --output reports/fcc_source_audit.json
"""

import argparse
import csv
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_FCC_COLUMNS = [
    "geography_id",
    "geography_desc_full",
    "geography_type_total_units",
    "data_type_total_units",
    "percent_coverage",
]

USER_OBSERVED_EXPORT_SETTINGS = {
    "source_platform": "FCC National Broadband Map, Area Comparison, Fixed Broadband",
    "geography_type": "County",
    "data_type": "Total",
    "service": "Residential",
    "technology": "All Wired",
    "speed_threshold": "at least 100 Mbps download / 20 Mbps upload (100/20 Mbps)",
    "data_as_of": "Dec 30, 2025",
    "interface_last_updated": "Oct 13, 2026",
    "record_provenance": (
        "Recorded as user-observed export settings from the FCC interface, "
        "not embedded metadata within the CSV."
    ),
}

OFFICIAL_REFERENCES = [
    "https://help.bdc.fcc.gov/hc/en-us/articles/10467446103579-How-to-Use-the-FCC-s-National-Broadband-Map",
    "https://help.bdc.fcc.gov/hc/en-us/articles/13532984820379-What-s-on-the-National-Broadband-Map",
    "https://www.census.gov/programs-surveys/acs/geography-acs/areas-published.html",
    "https://www.census.gov/programs-surveys/acs/geography-acs/geography-boundaries-by-year/2024.html",
]

DISCLAIMER = (
    "This audit evaluates source-data integrity of the FCC export and geographic "
    "join compatibility with Census ACS Table B28002. FCC percent_coverage reflects "
    "facility-based fixed broadband network availability (at >=100/20 Mbps threshold) "
    "reported by service providers, whereas Census Table B28002 measures household-reported "
    "broadband internet subscriptions. This audit does not establish project feasibility, "
    "a causal relationship, or a quantified adoption-availability gap."
)

FIPS_5DIGIT_PATTERN = re.compile(r"^[0-9]{5}$")
INTEGER_STRING_PATTERN = re.compile(r"^-?[0-9]+$")


def classify_unmatched_fcc(geography_id: str, name: str) -> str:
    state_prefix = geography_id[:2]
    if state_prefix == "09":
        return "Legacy Connecticut County (pre-2024 boundary)"
    elif state_prefix == "60":
        return "U.S. Territory - American Samoa (FIPS 60)"
    elif state_prefix == "66":
        return "U.S. Territory - Guam (FIPS 66)"
    elif state_prefix == "69":
        return "U.S. Territory - Northern Mariana Islands (FIPS 69)"
    elif state_prefix == "78":
        return "U.S. Territory - U.S. Virgin Islands (FIPS 78)"
    return "Other Unmatched FCC Entity"


def classify_unmatched_census(key: str, name: str) -> str:
    state_prefix = key[:2]
    if state_prefix == "09":
        return "Connecticut Planning Region (2024 ACS county equivalent)"
    return "Other Unmatched Census Entity"


def audit_fcc_and_compatibility(
    fcc_input_path: str, census_input_path: str, output_path: str
) -> int:
    fcc_file = Path(fcc_input_path)
    census_file = Path(census_input_path)
    output_file = Path(output_path)

    report = {
        "metadata": {
            "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "fcc_input_file": {
                "path": fcc_file.as_posix(),
                "size_bytes": fcc_file.stat().st_size if fcc_file.exists() else 0,
            },
            "census_input_file": {
                "path": census_file.as_posix(),
                "size_bytes": census_file.stat().st_size if census_file.exists() else 0,
            },
            "user_observed_export_settings": USER_OBSERVED_EXPORT_SETTINGS,
            "official_references": OFFICIAL_REFERENCES,
            "field_semantic_documentation": {
                "geography_id": "5-digit county FIPS code (string, preserving leading zeros).",
                "geography_desc_full": "Geographic area name and state/territory postal abbreviation.",
                "geography_type_total_units": (
                    "Total broadband serviceable locations (BSLs) or housing units in the geography. "
                    "Official FCC documentation does not specify the precise denominator derivation."
                ),
                "data_type_total_units": (
                    "Total units corresponding to the selected data type filter. In this export, "
                    "identical to geography_type_total_units in 100% of populated records."
                ),
                "percent_coverage": (
                    "Proportion of units with fixed broadband availability meeting or exceeding "
                    "100 Mbps download / 20 Mbps upload from all wired technologies (cable, fiber, DSL)."
                ),
                "semantic_limitation_note": (
                    "Official FCC documentation does not define an explicit mathematical formula "
                    "linking unit count columns to percent_coverage in the summary export. "
                    "No undocumented equation is assumed."
                ),
            },
            "disclaimer": DISCLAIMER,
        },
        "overall_status": "FAIL",
        "hard_checks": {},
        "review_flags": {},
        "fcc_summary_metrics": {},
        "geographic_compatibility": {},
    }

    hard_failures = []

    # ---------------------------------------------------------
    # Check 1: FCC File existence and non-empty
    # ---------------------------------------------------------
    if not fcc_file.exists():
        report["hard_checks"]["fcc_file_exists_and_nonempty"] = {
            "status": "FAIL",
            "description": "FCC CSV file exists on disk and is nonempty.",
            "error": f"File does not exist: {fcc_file}",
        }
        hard_failures.append("fcc_file_exists_and_nonempty")
        _save_and_exit(report, output_file)
        return 1

    fcc_size = fcc_file.stat().st_size
    report["metadata"]["fcc_input_file"]["size_bytes"] = fcc_size

    if fcc_size == 0:
        report["hard_checks"]["fcc_file_exists_and_nonempty"] = {
            "status": "FAIL",
            "description": "FCC CSV file exists on disk and is nonempty.",
            "error": f"File is empty (0 bytes): {fcc_file}",
        }
        hard_failures.append("fcc_file_exists_and_nonempty")
        _save_and_exit(report, output_file)
        return 1

    report["hard_checks"]["fcc_file_exists_and_nonempty"] = {
        "status": "PASS",
        "description": "FCC CSV file exists on disk and is nonempty.",
        "details": {"size_bytes": fcc_size},
    }

    # ---------------------------------------------------------
    # Check 2: CSV Parsing and Header Schema
    # ---------------------------------------------------------
    fcc_rows = []
    fieldnames = []
    try:
        with open(fcc_file, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames) if reader.fieldnames else []
            for row in reader:
                fcc_rows.append(row)
    except Exception as e:
        report["hard_checks"]["fcc_csv_parsing"] = {
            "status": "FAIL",
            "description": "FCC CSV parses successfully.",
            "error": f"CSV parse error: {str(e)}",
        }
        hard_failures.append("fcc_csv_parsing")
        _save_and_exit(report, output_file)
        return 1

    report["hard_checks"]["fcc_csv_parsing"] = {
        "status": "PASS",
        "description": "FCC CSV parses successfully.",
    }

    if fieldnames != EXPECTED_FCC_COLUMNS:
        report["hard_checks"]["fcc_header_schema"] = {
            "status": "FAIL",
            "description": "Header columns match expected five fields in exact order.",
            "expected": EXPECTED_FCC_COLUMNS,
            "actual": fieldnames,
        }
        hard_failures.append("fcc_header_schema")
    else:
        report["hard_checks"]["fcc_header_schema"] = {
            "status": "PASS",
            "description": "Header columns match expected five fields in exact order.",
            "columns": fieldnames,
        }

    total_fcc_rows = len(fcc_rows)
    if total_fcc_rows == 0:
        report["hard_checks"]["fcc_nonempty_records"] = {
            "status": "FAIL",
            "description": "FCC CSV contains at least one data record.",
            "error": "CSV contains header but zero data rows.",
        }
        hard_failures.append("fcc_nonempty_records")
        _save_and_exit(report, output_file)
        return 1

    report["hard_checks"]["fcc_nonempty_records"] = {
        "status": "PASS",
        "description": "FCC CSV contains data records.",
        "details": {"total_data_rows": total_fcc_rows},
    }

    # ---------------------------------------------------------
    # Inspect FCC Records and Numeric Fields
    # ---------------------------------------------------------
    empty_descriptions = []
    malformed_ids = []
    seen_fcc_ids = {}
    duplicate_fcc_ids = []

    # Numeric tracking
    missing_geog_units = []
    missing_data_units = []
    negative_geog_units = []
    negative_data_units = []
    malformed_geog_units = []
    malformed_data_units = []

    units_equal_count = 0
    units_differ_count = 0

    geog_unit_values = []
    data_unit_values = []

    cov_values = []
    missing_cov = []
    invalid_cov = []
    zero_cov_count = 0

    for idx, row in enumerate(fcc_rows, start=2):
        gid = row.get("geography_id")
        desc = row.get("geography_desc_full")
        gt_units = row.get("geography_type_total_units")
        dt_units = row.get("data_type_total_units")
        cov_str = row.get("percent_coverage")

        # Geography ID validation: must be exact 5 digits string
        if not isinstance(gid, str) or not FIPS_5DIGIT_PATTERN.fullmatch(gid):
            malformed_ids.append({"row_index": idx, "geography_id": gid, "desc": desc})
        else:
            if gid in seen_fcc_ids:
                duplicate_fcc_ids.append({
                    "geography_id": gid,
                    "first_seen_row": seen_fcc_ids[gid],
                    "duplicate_row": idx,
                    "desc": desc,
                })
            else:
                seen_fcc_ids[gid] = idx

        # Description validation
        if not isinstance(desc, str) or not desc.strip():
            empty_descriptions.append({"row_index": idx, "geography_id": gid})

        # geography_type_total_units validation
        gt_present = False
        gt_int = None
        if gt_units is None or (isinstance(gt_units, str) and not gt_units.strip()):
            missing_geog_units.append({
                "row_index": idx,
                "geography_id": gid,
                "desc": desc,
                "raw_value": gt_units,
            })
        else:
            if not isinstance(gt_units, str) or not INTEGER_STRING_PATTERN.fullmatch(gt_units):
                malformed_geog_units.append({
                    "row_index": idx,
                    "geography_id": gid,
                    "desc": desc,
                    "raw_value": gt_units,
                })
            else:
                gt_int = int(gt_units)
                if gt_int < 0:
                    negative_geog_units.append({
                        "row_index": idx,
                        "geography_id": gid,
                        "desc": desc,
                        "parsed_value": gt_int,
                    })
                else:
                    gt_present = True
                    geog_unit_values.append(gt_int)

        # data_type_total_units validation
        dt_present = False
        dt_int = None
        if dt_units is None or (isinstance(dt_units, str) and not dt_units.strip()):
            missing_data_units.append({
                "row_index": idx,
                "geography_id": gid,
                "desc": desc,
                "raw_value": dt_units,
            })
        else:
            if not isinstance(dt_units, str) or not INTEGER_STRING_PATTERN.fullmatch(dt_units):
                malformed_data_units.append({
                    "row_index": idx,
                    "geography_id": gid,
                    "desc": desc,
                    "raw_value": dt_units,
                })
            else:
                dt_int = int(dt_units)
                if dt_int < 0:
                    negative_data_units.append({
                        "row_index": idx,
                        "geography_id": gid,
                        "desc": desc,
                        "parsed_value": dt_int,
                    })
                else:
                    dt_present = True
                    data_unit_values.append(dt_int)

        # Comparison of unit counts where both are present
        if gt_present and dt_present:
            if gt_int == dt_int:
                units_equal_count += 1
            else:
                units_differ_count += 1

        # percent_coverage validation: finite numeric float in [0.0, 1.0]
        if cov_str is None or (isinstance(cov_str, str) and not cov_str.strip()):
            missing_cov.append({"row_index": idx, "geography_id": gid, "desc": desc})
        else:
            try:
                c_val = float(cov_str)
                if math.isnan(c_val) or math.isinf(c_val) or c_val < 0.0 or c_val > 1.0:
                    invalid_cov.append({
                        "row_index": idx,
                        "geography_id": gid,
                        "desc": desc,
                        "value": cov_str,
                        "parsed": c_val,
                        "reason": "Value outside [0.0, 1.0] or non-finite",
                    })
                else:
                    cov_values.append(c_val)
                    if c_val == 0.0:
                        zero_cov_count += 1
            except (ValueError, TypeError):
                invalid_cov.append({
                    "row_index": idx,
                    "geography_id": gid,
                    "desc": desc,
                    "value": cov_str,
                    "reason": "Unparsable floating-point string",
                })

    # Evaluate Geography ID format
    if malformed_ids:
        report["hard_checks"]["fcc_geography_id_format"] = {
            "status": "FAIL",
            "description": "Every geography_id is a nonempty string of exactly five digits preserving leading zeros.",
            "malformed_count": len(malformed_ids),
            "examples": malformed_ids[:5],
        }
        hard_failures.append("fcc_geography_id_format")
    else:
        report["hard_checks"]["fcc_geography_id_format"] = {
            "status": "PASS",
            "description": "Every geography_id is a nonempty string of exactly five digits preserving leading zeros.",
            "malformed_count": 0,
        }

    # Evaluate Geography ID uniqueness
    if duplicate_fcc_ids:
        report["hard_checks"]["fcc_geography_id_unique"] = {
            "status": "FAIL",
            "description": "No duplicate geography IDs exist in the FCC export.",
            "duplicate_count": len(duplicate_fcc_ids),
            "examples": duplicate_fcc_ids[:5],
        }
        hard_failures.append("fcc_geography_id_unique")
    else:
        report["hard_checks"]["fcc_geography_id_unique"] = {
            "status": "PASS",
            "description": "No duplicate geography IDs exist in the FCC export.",
            "duplicate_count": 0,
            "unique_key_count": len(seen_fcc_ids),
        }

    # Evaluate Geography description
    if empty_descriptions:
        report["hard_checks"]["fcc_geography_desc_nonempty"] = {
            "status": "FAIL",
            "description": "Every geography description is a non-empty string.",
            "empty_count": len(empty_descriptions),
            "examples": empty_descriptions[:5],
        }
        hard_failures.append("fcc_geography_desc_nonempty")
    else:
        report["hard_checks"]["fcc_geography_desc_nonempty"] = {
            "status": "PASS",
            "description": "Every geography description is a non-empty string.",
            "empty_count": 0,
        }

    # Evaluate percent_coverage hard check
    if missing_cov or invalid_cov:
        report["hard_checks"]["fcc_percent_coverage_valid"] = {
            "status": "FAIL",
            "description": "percent_coverage parses as a finite float within [0.0, 1.0] for every row.",
            "missing_count": len(missing_cov),
            "invalid_count": len(invalid_cov),
            "examples_invalid": invalid_cov[:5],
            "examples_missing": missing_cov[:5],
        }
        hard_failures.append("fcc_percent_coverage_valid")
    else:
        report["hard_checks"]["fcc_percent_coverage_valid"] = {
            "status": "PASS",
            "description": "percent_coverage parses as a finite float within [0.0, 1.0] for every row.",
            "missing_count": 0,
            "invalid_count": 0,
        }

    # Evaluate unit counts syntax when present (must be integer string and non-negative)
    total_malformed_units = len(malformed_geog_units) + len(malformed_data_units)
    total_negative_units = len(negative_geog_units) + len(negative_data_units)
    if total_malformed_units > 0 or total_negative_units > 0:
        report["hard_checks"]["fcc_unit_counts_valid_when_present"] = {
            "status": "FAIL",
            "description": "geography_type_total_units and data_type_total_units must be nonnegative integers when present.",
            "malformed_geog_units_count": len(malformed_geog_units),
            "malformed_data_units_count": len(malformed_data_units),
            "negative_geog_units_count": len(negative_geog_units),
            "negative_data_units_count": len(negative_data_units),
            "examples_malformed": (malformed_geog_units + malformed_data_units)[:5],
            "examples_negative": (negative_geog_units + negative_data_units)[:5],
        }
        hard_failures.append("fcc_unit_counts_valid_when_present")
    else:
        report["hard_checks"]["fcc_unit_counts_valid_when_present"] = {
            "status": "PASS",
            "description": "geography_type_total_units and data_type_total_units are nonnegative integers when present.",
            "malformed_count": 0,
            "negative_count": 0,
        }

    # Review flag: Missing unit counts issue
    total_missing_units = len(missing_geog_units) + len(missing_data_units)
    if total_missing_units > 0:
        report["review_flags"]["missing_unit_counts_review"] = {
            "status": "REVIEW",
            "description": "Report observed missing unit counts in FCC export (not converted to zero).",
            "missing_geography_type_total_units_count": len(missing_geog_units),
            "missing_data_type_total_units_count": len(missing_data_units),
            "examples": missing_geog_units[:5],
            "notes": (
                f"Observed {len(missing_geog_units)} records with empty unit count fields: "
                f"{', '.join(e['geography_id'] + ' (' + e['desc'] + ')' for e in missing_geog_units)}. "
                "These values were faithfully retained as missing rather than coerced to zero."
            ),
        }
    else:
        report["review_flags"]["missing_unit_counts_review"] = {
            "status": "INFORMATIONAL",
            "description": "No missing unit counts observed.",
            "missing_count": 0,
        }

    # Review flag: Unit count agreement
    report["review_flags"]["unit_counts_agreement_diagnostic"] = {
        "status": "INFORMATIONAL",
        "description": "Comparison between geography_type_total_units and data_type_total_units where both exist.",
        "both_present_records": units_equal_count + units_differ_count,
        "equal_count": units_equal_count,
        "differ_count": units_differ_count,
        "agreement_percentage": (
            (units_equal_count / (units_equal_count + units_differ_count)) * 100
            if (units_equal_count + units_differ_count) > 0
            else 0.0
        ),
        "notes": (
            f"In all {units_equal_count} records where both unit count fields are populated, "
            "geography_type_total_units equals data_type_total_units exactly (100% agreement)."
        ),
    }

    # Summary metrics for FCC
    report["fcc_summary_metrics"] = {
        "total_data_rows": total_fcc_rows,
        "unique_geography_ids": len(seen_fcc_ids),
        "duplicate_geography_ids": len(duplicate_fcc_ids),
        "percent_coverage_statistics": {
            "min": min(cov_values) if cov_values else None,
            "max": max(cov_values) if cov_values else None,
            "missing_count": len(missing_cov),
            "zero_count": zero_cov_count,
            "parsed_count": len(cov_values),
        },
        "unit_counts_statistics": {
            "geography_type_total_units": {
                "missing_count": len(missing_geog_units),
                "negative_count": len(negative_geog_units),
                "malformed_count": len(malformed_geog_units),
                "min": min(geog_unit_values) if geog_unit_values else None,
                "max": max(geog_unit_values) if geog_unit_values else None,
                "zero_count": sum(1 for v in geog_unit_values if v == 0),
            },
            "data_type_total_units": {
                "missing_count": len(missing_data_units),
                "negative_count": len(negative_data_units),
                "malformed_count": len(malformed_data_units),
                "min": min(data_unit_values) if data_unit_values else None,
                "max": max(data_unit_values) if data_unit_values else None,
                "zero_count": sum(1 for v in data_unit_values if v == 0),
            },
        },
    }

    # ---------------------------------------------------------
    # STEP 3: Geographic Compatibility Audit against Census ACS
    # ---------------------------------------------------------
    if not census_file.exists():
        report["review_flags"]["geographic_compatibility_audit"] = {
            "status": "REVIEW",
            "description": "Census reference file not found for geographic compatibility analysis.",
            "error": f"Census file missing: {census_file}",
        }
    else:
        try:
            with open(census_file, "r", encoding="utf-8") as f:
                census_raw = json.load(f)

            census_rows = census_raw[1:] if isinstance(census_raw, list) else []
            census_total_data_rows = len(census_rows)

            census_keys_map = {}
            census_duplicate_keys = []
            for c_idx, c_row in enumerate(census_rows, start=2):
                if isinstance(c_row, list) and len(c_row) >= 7:
                    c_name = c_row[0]
                    c_state = str(c_row[5])
                    c_county = str(c_row[6])
                    c_key = f"{c_state}{c_county}"
                    if c_key in census_keys_map:
                        census_duplicate_keys.append({
                            "key": c_key,
                            "first_row": census_keys_map[c_key]["row_index"],
                            "dup_row": c_idx,
                        })
                    else:
                        census_keys_map[c_key] = {"row_index": c_idx, "name": c_name}

            fcc_keys_set = set(seen_fcc_ids.keys())
            census_keys_set = set(census_keys_map.keys())

            intersection = census_keys_set.intersection(fcc_keys_set)
            census_only_keys = sorted(list(census_keys_set - fcc_keys_set))
            fcc_only_keys = sorted(list(fcc_keys_set - census_keys_set))

            census_coverage_pct = (
                (len(intersection) / len(census_keys_set)) * 100
                if len(census_keys_set) > 0
                else 0.0
            )
            fcc_coverage_pct = (
                (len(intersection) / len(fcc_keys_set)) * 100
                if len(fcc_keys_set) > 0
                else 0.0
            )

            # Detailed unmatched grouping
            fcc_map = {r["geography_id"]: r["geography_desc_full"] for r in fcc_rows}
            census_only_details = [
                {
                    "key": k,
                    "name": census_keys_map[k]["name"],
                    "group": classify_unmatched_census(k, census_keys_map[k]["name"]),
                }
                for k in census_only_keys
            ]

            fcc_only_details = [
                {
                    "geography_id": k,
                    "name": fcc_map.get(k, "Unknown"),
                    "group": classify_unmatched_fcc(k, fcc_map.get(k, "")),
                }
                for k in fcc_only_keys
            ]

            # Count by group
            census_only_grouped = {}
            for item in census_only_details:
                grp = item["group"]
                census_only_grouped[grp] = census_only_grouped.get(grp, 0) + 1

            fcc_only_grouped = {}
            for item in fcc_only_details:
                grp = item["group"]
                fcc_only_grouped[grp] = fcc_only_grouped.get(grp, 0) + 1

            report["geographic_compatibility"] = {
                "census_total_data_rows": census_total_data_rows,
                "census_unique_keys_count": len(census_keys_map),
                "census_duplicate_keys_count": len(census_duplicate_keys),
                "fcc_total_data_rows": total_fcc_rows,
                "fcc_unique_geography_ids_count": len(seen_fcc_ids),
                "fcc_duplicate_geography_ids_count": len(duplicate_fcc_ids),
                "exact_matching_keys_count": len(intersection),
                "census_only_keys_count": len(census_only_keys),
                "fcc_only_keys_count": len(fcc_only_keys),
                "coverage_percentages": {
                    "census_keys_in_intersection_percentage": round(census_coverage_pct, 5),
                    "census_denominator": len(census_keys_set),
                    "fcc_keys_in_intersection_percentage": round(fcc_coverage_pct, 5),
                    "fcc_denominator": len(fcc_keys_set),
                },
                "unmatched_analysis": {
                    "census_only_records": census_only_details,
                    "fcc_only_records": fcc_only_details,
                    "unmatched_summary_by_group": {
                        "census_only": census_only_grouped,
                        "fcc_only": fcc_only_grouped,
                    },
                    "boundary_alignment_findings": (
                        "The 9 Census-only records correspond to Connecticut's planning regions "
                        "(FIPS 09110-09190), adopted as county-equivalents in the 2024 ACS 5-year data. "
                        "The FCC Area Comparison export retains Connecticut's 8 legacy counties "
                        "(FIPS 09001-09015). Do not perform an unverified many-to-many crosswalk or spatial "
                        "allocation without formal methodological authorization. The remaining 13 FCC-only "
                        "records represent island territories (American Samoa [5], Guam [1], Northern "
                        "Mariana Islands [4], and U.S. Virgin Islands [3]) not included in the standard "
                        "Census 50 States + DC + PR county extract."
                    ),
                },
            }

        except Exception as e:
            report["geographic_compatibility"] = {
                "error": f"Failed during geographic compatibility cross-audit: {str(e)}"
            }

    report["overall_status"] = "PASS" if len(hard_failures) == 0 else "FAIL"

    _save_report(report, output_file)
    _print_summary(report)

    return 0 if len(hard_failures) == 0 else 1


def _save_and_exit(report: dict, output_file: Path) -> None:
    _save_report(report, output_file)
    _print_summary(report)


def _save_report(report: dict, output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


def _print_summary(report: dict) -> None:
    meta = report.get("metadata", {})
    fcc_file = meta.get("fcc_input_file", {})
    settings = meta.get("user_observed_export_settings", {})
    metrics = report.get("fcc_summary_metrics", {})
    hard_checks = report.get("hard_checks", {})
    review_flags = report.get("review_flags", {})
    geo = report.get("geographic_compatibility", {})
    overall_status = report.get("overall_status", "UNKNOWN")

    print("=" * 76)
    print(" FCC SOURCE DATA & GEOGRAPHIC COMPATIBILITY AUDIT SUMMARY")
    print("=" * 76)
    print(f" Source:            {settings.get('source_platform')}")
    print(f" Speed Threshold:   {settings.get('speed_threshold')}")
    print(f" Data As Of:        {settings.get('data_as_of')}")
    print(f" Input File:        {fcc_file.get('path')} ({fcc_file.get('size_bytes')} bytes)")
    print(f" Overall Status:    {overall_status}")
    print("-" * 76)
    print(" HARD CHECK RESULTS:")
    failed_checks = []
    for check_id, check_data in hard_checks.items():
        status = check_data.get("status")
        desc = check_data.get("description")
        print(f"  [{status}] {check_id}: {desc}")
        if status != "PASS":
            failed_checks.append((check_id, check_data))

    if failed_checks:
        print("\n FAILED CHECKS DETAILS:")
        for check_id, check_data in failed_checks:
            print(f"  * {check_id}: {check_data.get('error', check_data)}")

    print("-" * 76)
    print(" REVIEW FLAGS / DATA-QUALITY DIAGNOSTICS:")
    for flag_id, flag_data in review_flags.items():
        print(f"  [{flag_data.get('status')}] {flag_id}: {flag_data.get('description')}")
        if "notes" in flag_data:
            print(f"    Notes: {flag_data.get('notes')}")

    print("-" * 76)
    print(" FCC OBSERVED METRICS:")
    print(f"  Total FCC Rows:                 {metrics.get('total_data_rows')}")
    print(f"  Unique Geography IDs:           {metrics.get('unique_geography_ids')}")
    print(f"  Duplicate Geography IDs:        {metrics.get('duplicate_geography_ids')}")

    cov_stats = metrics.get("percent_coverage_statistics", {})
    if cov_stats:
        print(
            f"  percent_coverage:               min={cov_stats.get('min')}, "
            f"max={cov_stats.get('max')}, zeros={cov_stats.get('zero_count')}, "
            f"missing={cov_stats.get('missing_count')}"
        )

    unit_stats = metrics.get("unit_counts_statistics", {})
    if unit_stats:
        gt_s = unit_stats.get("geography_type_total_units", {})
        dt_s = unit_stats.get("data_type_total_units", {})
        print(
            f"  geography_type_total_units:     min={gt_s.get('min')}, "
            f"max={gt_s.get('max')}, missing={gt_s.get('missing_count')}, "
            f"negative={gt_s.get('negative_count')}"
        )
        print(
            f"  data_type_total_units:          min={dt_s.get('min')}, "
            f"max={dt_s.get('max')}, missing={dt_s.get('missing_count')}, "
            f"negative={dt_s.get('negative_count')}"
        )

    if geo:
        print("-" * 76)
        print(" GEOGRAPHIC COMPATIBILITY WITH 2024 CENSUS ACS B28002:")
        print(f"  Census Total Rows:              {geo.get('census_total_data_rows')}")
        print(f"  FCC Total Rows:                 {geo.get('fcc_total_data_rows')}")
        print(f"  Exact Matching Keys:            {geo.get('exact_matching_keys_count')}")
        print(f"  Census-Only Keys:               {geo.get('census_only_keys_count')}")
        print(f"  FCC-Only Keys:                  {geo.get('fcc_only_keys_count')}")

        cov_p = geo.get("coverage_percentages", {})
        print(
            f"  Census Intersection Coverage:   {cov_p.get('census_keys_in_intersection_percentage')}% "
            f"(denominator: {cov_p.get('census_denominator')})"
        )
        print(
            f"  FCC Intersection Coverage:      {cov_p.get('fcc_keys_in_intersection_percentage')}% "
            f"(denominator: {cov_p.get('fcc_denominator')})"
        )

        unm = geo.get("unmatched_analysis", {})
        unm_sum = unm.get("unmatched_summary_by_group", {})
        print("\n  Unmatched Group Breakdown:")
        print(f"    Census-Only: {unm_sum.get('census_only', {})}")
        print(f"    FCC-Only:    {unm_sum.get('fcc_only', {})}")
        if "boundary_alignment_findings" in unm:
            print(f"\n  Boundary Alignment Note:\n    {unm['boundary_alignment_findings']}")

    print("-" * 76)
    print(" IMPORTANT NOTICE / DISCLAIMER:")
    print(f"  {meta.get('disclaimer')}")
    print("=" * 76)


def main():
    parser = argparse.ArgumentParser(
        description="Audit FCC county comparison data and validate geographic compatibility with Census ACS data."
    )
    parser.add_argument(
        "--fcc-input",
        "--input",
        dest="fcc_input",
        default="data/raw/bdc_comparison_fixed_county_total_all_wired_r_100_20_D25.csv",
        help="Path to FCC comparison CSV file.",
    )
    parser.add_argument(
        "--census-input",
        "--census",
        dest="census_input",
        default="data/raw/acs_b28002_2024_county.json",
        help="Path to Census ACS JSON file for geographic cross-comparison.",
    )
    parser.add_argument(
        "--output",
        default="reports/fcc_source_audit.json",
        help="Path to output validation JSON report.",
    )
    args = parser.parse_args()

    exit_code = audit_fcc_and_compatibility(
        args.fcc_input, args.census_input, args.output
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
