#!/usr/bin/env python3
"""
validate_census_data.py - Census ACS B28002 Data Integrity & Validation Audit

Audits local Census ACS JSON file (Table B28002, 2024 5-Year ACS county geography)
for structural integrity and strict data validity.

Usage:
    python scripts/validate_census_data.py --input data/raw/acs_b28002_2024_county.json --output reports/census_validation.json
"""

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_HEADER = [
    "NAME",
    "B28002_001E",
    "B28002_001M",
    "B28002_007E",
    "B28002_007M",
    "state",
    "county",
]

NUMERIC_FIELDS = [
    ("B28002_001E", 1),
    ("B28002_001M", 2),
    ("B28002_007E", 3),
    ("B28002_007M", 4),
]

DISCLAIMER = (
    "Structural validity does not establish statistical comparability with "
    "FCC provider-reported availability, geographic representativeness, causality, "
    "or overall project feasibility. A successful basic audit is not an overall "
    "project acceptance."
)

OFFICIAL_GEOGRAPHY_URL = (
    "https://www.census.gov/programs-surveys/acs/geography-acs/areas-published.html"
)
OFFICIAL_5YEAR_COUNTY_COUNT = 3222

INTEGER_STRING_PATTERN = re.compile(r"^-?[0-9]+$")
FIPS_STATE_PATTERN = re.compile(r"^[0-9]{2}$")
FIPS_COUNTY_PATTERN = re.compile(r"^[0-9]{3}$")


def validate_census_file(input_path: str, output_path: str) -> int:
    input_file = Path(input_path)
    output_file = Path(output_path)

    report = {
        "metadata": {
            "source_name": "U.S. Census Bureau, American Community Survey (ACS)",
            "acs_vintage": "2024 (5-Year Estimates)",
            "table_name": "B28002 - PRESENCE AND TYPES OF INTERNET SUBSCRIPTIONS IN HOUSEHOLD",
            "table_universe": "Total households",
            "variables": {
                "NAME": "Geographic Area Name (County and State)",
                "B28002_001E": "Total households (Estimate)",
                "B28002_001M": "Total households (Margin of Error)",
                "B28002_007E": "Broadband such as cable, fiber optic or DSL (Estimate)",
                "B28002_007M": "Broadband such as cable, fiber optic or DSL (Margin of Error)",
                "state": "State FIPS Code (2 digits, zero-padded)",
                "county": "County FIPS Code (3 digits, zero-padded)",
            },
            "input_path": input_file.as_posix(),
            "file_size_bytes": 0,
            "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "validation_scope": (
                "Initial Census-source data integrity audit (structural & basic data validity). "
                "Does not evaluate FCC data comparability or project acceptance."
            ),
            "disclaimer": DISCLAIMER,
            "official_geography_reference": {
                "url": OFFICIAL_GEOGRAPHY_URL,
                "published_county_count_5year_2024": OFFICIAL_5YEAR_COUNTY_COUNT,
            },
        },
        "overall_status": "FAIL",
        "hard_checks": {},
        "review_flags": {},
        "summary_metrics": {},
    }

    hard_failures = []

    # Check 1: File existence and non-empty
    if not input_file.exists():
        report["hard_checks"]["file_exists_and_nonempty"] = {
            "status": "FAIL",
            "description": "File exists on disk and is nonempty.",
            "error": f"Input file does not exist: {input_file}",
        }
        hard_failures.append("file_exists_and_nonempty")
        _save_report(report, output_file)
        _print_summary(report)
        return 1

    file_size = input_file.stat().st_size
    report["metadata"]["file_size_bytes"] = file_size

    if file_size == 0:
        report["hard_checks"]["file_exists_and_nonempty"] = {
            "status": "FAIL",
            "description": "File exists on disk and is nonempty.",
            "error": f"Input file is empty (0 bytes): {input_file}",
        }
        hard_failures.append("file_exists_and_nonempty")
        _save_report(report, output_file)
        _print_summary(report)
        return 1

    report["hard_checks"]["file_exists_and_nonempty"] = {
        "status": "PASS",
        "description": "File exists on disk and is nonempty.",
        "details": {"size_bytes": file_size},
    }

    # Check 2: JSON parsing and top-level array structure
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except Exception as e:
        report["hard_checks"]["valid_json_structure"] = {
            "status": "FAIL",
            "description": "JSON parses successfully.",
            "error": f"JSON parse error: {str(e)}",
        }
        hard_failures.append("valid_json_structure")
        _save_report(report, output_file)
        _print_summary(report)
        return 1

    report["hard_checks"]["valid_json_structure"] = {
        "status": "PASS",
        "description": "JSON parses successfully.",
    }

    if not isinstance(raw_data, list) or len(raw_data) < 1:
        report["hard_checks"]["top_level_is_array"] = {
            "status": "FAIL",
            "description": "Top-level content is an array containing header plus data rows.",
            "error": "Expected top-level JSON array with at least a header row.",
        }
        hard_failures.append("top_level_is_array")
        _save_report(report, output_file)
        _print_summary(report)
        return 1

    # Check 3: Header matches expected
    header = raw_data[0]
    if header != EXPECTED_HEADER:
        report["hard_checks"]["header_matches_expected"] = {
            "status": "FAIL",
            "description": "Header matches exactly, in order: " + ", ".join(EXPECTED_HEADER),
            "expected": EXPECTED_HEADER,
            "actual": header,
        }
        hard_failures.append("header_matches_expected")
    else:
        report["hard_checks"]["header_matches_expected"] = {
            "status": "PASS",
            "description": "Header matches exactly, in order: " + ", ".join(EXPECTED_HEADER),
            "header": header,
        }

    data_rows = raw_data[1:]
    total_data_rows = len(data_rows)

    # Check that dataset contains data rows (not just the header)
    if total_data_rows == 0:
        report["hard_checks"]["top_level_is_array"] = {
            "status": "FAIL",
            "description": "Top-level content is an array containing header plus data rows.",
            "error": "Top-level JSON array contains a header but zero data records.",
            "details": {"total_array_elements": len(raw_data), "data_rows": 0},
        }
        hard_failures.append("top_level_is_array")
        _save_report(report, output_file)
        _print_summary(report)
        return 1

    report["hard_checks"]["top_level_is_array"] = {
        "status": "PASS",
        "description": "Top-level content is an array containing header plus data rows.",
        "details": {"total_array_elements": len(raw_data), "data_rows": total_data_rows},
    }

    # Check 4: Record field counts
    malformed_records = []
    for idx, row in enumerate(data_rows, start=2):
        if not isinstance(row, list) or len(row) != 7:
            malformed_records.append({"row_index": idx, "row_content": row})

    if malformed_records:
        report["hard_checks"]["record_field_counts_valid"] = {
            "status": "FAIL",
            "description": "Every data record has exactly seven fields.",
            "malformed_count": len(malformed_records),
            "examples": malformed_records[:5],
        }
        hard_failures.append("record_field_counts_valid")
    else:
        report["hard_checks"]["record_field_counts_valid"] = {
            "status": "PASS",
            "description": "Every data record has exactly seven fields.",
            "malformed_count": 0,
        }

    # Check 5: Geography integrity
    empty_names = []
    invalid_fips = []
    fips_seen = {}
    duplicate_fips = []
    unique_state_codes = set()

    # Track blanks / unparsable / negatives
    blank_values = []
    unparsable_values = {col_name: [] for col_name, _ in NUMERIC_FIELDS}
    negative_values = {col_name: [] for col_name, _ in NUMERIC_FIELDS}
    numeric_stats = {
        col_name: {"min": None, "max": None, "zero_count": 0, "parsed_count": 0}
        for col_name, _ in NUMERIC_FIELDS
    }
    broadband_exceeds_total = []

    for idx, row in enumerate(data_rows, start=2):
        if not isinstance(row, list) or len(row) < 7:
            continue

        name, b28002_001e, b28002_001m, b28002_007e, b28002_007m, state_fips, county_fips = row[:7]

        # Name check: must be a non-empty string, not boolean
        if not isinstance(name, str) or isinstance(name, bool) or not name.strip():
            empty_names.append({"row_index": idx, "row": row})

        # FIPS format check: exact full-string match on 2 digits (state) and 3 digits (county)
        state_valid = (
            isinstance(state_fips, str)
            and not isinstance(state_fips, bool)
            and bool(FIPS_STATE_PATTERN.fullmatch(state_fips))
        )
        county_valid = (
            isinstance(county_fips, str)
            and not isinstance(county_fips, bool)
            and bool(FIPS_COUNTY_PATTERN.fullmatch(county_fips))
        )
        if not (state_valid and county_valid):
            invalid_fips.append({
                "row_index": idx,
                "name": name if isinstance(name, str) else repr(name),
                "state": state_fips if isinstance(state_fips, str) else repr(state_fips),
                "county": county_fips if isinstance(county_fips, str) else repr(county_fips),
            })
        else:
            unique_state_codes.add(state_fips)
            full_fips = f"{state_fips}{county_fips}"
            if full_fips in fips_seen:
                duplicate_fips.append({
                    "fips": full_fips,
                    "first_row": fips_seen[full_fips],
                    "duplicate_row": idx,
                    "name": name,
                })
            else:
                fips_seen[full_fips] = idx

        # Numeric field parsing and strict validation
        row_id = f"{state_fips}{county_fips} ({name})"
        parsed_row_nums = {}

        for col_name, col_idx in NUMERIC_FIELDS:
            raw_val = row[col_idx]

            # Missing, empty string, or whitespace
            if raw_val is None or (isinstance(raw_val, str) and not raw_val.strip()):
                blank_values.append({
                    "row_index": idx,
                    "identifier": row_id,
                    "field": col_name,
                    "value": repr(raw_val),
                    "value_type": type(raw_val).__name__,
                })
                continue

            # Strict typing: reject booleans and non-string types (float, int literal, etc.)
            if isinstance(raw_val, bool) or not isinstance(raw_val, str):
                unparsable_values[col_name].append({
                    "row_index": idx,
                    "identifier": row_id,
                    "field": col_name,
                    "value": repr(raw_val),
                    "value_type": type(raw_val).__name__,
                    "reason": f"Expected signed integer string, received {type(raw_val).__name__}",
                })
                continue

            # Strict pattern check: complete match against -?[0-9]+
            if not INTEGER_STRING_PATTERN.fullmatch(raw_val):
                unparsable_values[col_name].append({
                    "row_index": idx,
                    "identifier": row_id,
                    "field": col_name,
                    "value": raw_val,
                    "value_type": "str",
                    "reason": "String does not match complete signed integer pattern -?[0-9]+",
                })
                continue

            # Parse integer
            val_int = int(raw_val)
            parsed_row_nums[col_name] = val_int

            # Non-negative check
            if val_int < 0:
                negative_values[col_name].append({
                    "row_index": idx,
                    "identifier": row_id,
                    "field": col_name,
                    "value": val_int,
                })

            # Stats tracking
            st = numeric_stats[col_name]
            st["parsed_count"] += 1
            if val_int == 0:
                st["zero_count"] += 1
            if st["min"] is None or val_int < st["min"]:
                st["min"] = val_int
            if st["max"] is None or val_int > st["max"]:
                st["max"] = val_int

        # Relational check: B28002_007E <= B28002_001E
        if "B28002_001E" in parsed_row_nums and "B28002_007E" in parsed_row_nums:
            tot = parsed_row_nums["B28002_001E"]
            bb = parsed_row_nums["B28002_007E"]
            if bb > tot:
                broadband_exceeds_total.append({
                    "row_index": idx,
                    "identifier": row_id,
                    "total_households_B28002_001E": tot,
                    "broadband_households_B28002_007E": bb,
                    "discrepancy": bb - tot,
                })

    # Evaluate Hard Checks
    # Name integrity
    if empty_names:
        report["hard_checks"]["geography_name_valid"] = {
            "status": "FAIL",
            "description": "NAME is a nonempty string for every record.",
            "empty_name_count": len(empty_names),
            "examples": empty_names[:5],
        }
        hard_failures.append("geography_name_valid")
    else:
        report["hard_checks"]["geography_name_valid"] = {
            "status": "PASS",
            "description": "NAME is a nonempty string for every record.",
            "empty_name_count": 0,
        }

    # FIPS format integrity
    if invalid_fips:
        report["hard_checks"]["fips_format_valid"] = {
            "status": "FAIL",
            "description": "state is exactly 2 digits and county is exactly 3 digits, preserving leading zeros.",
            "invalid_count": len(invalid_fips),
            "examples": invalid_fips[:5],
        }
        hard_failures.append("fips_format_valid")
    else:
        report["hard_checks"]["fips_format_valid"] = {
            "status": "PASS",
            "description": "state is exactly 2 digits and county is exactly 3 digits, preserving leading zeros.",
            "invalid_count": 0,
        }

    # Key uniqueness
    if duplicate_fips:
        report["hard_checks"]["geography_keys_unique"] = {
            "status": "FAIL",
            "description": "State+county FIPS keys are unique across all records.",
            "duplicate_count": len(duplicate_fips),
            "examples": duplicate_fips[:5],
        }
        hard_failures.append("geography_keys_unique")
    else:
        report["hard_checks"]["geography_keys_unique"] = {
            "status": "PASS",
            "description": "State+county FIPS keys are unique across all records.",
            "duplicate_count": 0,
            "unique_key_count": len(fips_seen),
        }

    # Numeric integers strictly parsable check
    total_unparsable = sum(len(v) for v in unparsable_values.values())
    total_blank = len(blank_values)
    if total_unparsable > 0 or total_blank > 0:
        report["hard_checks"]["numeric_fields_parse_integers"] = {
            "status": "FAIL",
            "description": "All four estimate/MOE fields strictly parse as integer strings matching -?[0-9]+.",
            "unparsable_by_column": {k: len(v) for k, v in unparsable_values.items()},
            "blank_values_count": total_blank,
            "examples_unparsable": [ex for v in unparsable_values.values() for ex in v][:5],
            "examples_blank": blank_values[:5],
        }
        hard_failures.append("numeric_fields_parse_integers")
    else:
        report["hard_checks"]["numeric_fields_parse_integers"] = {
            "status": "PASS",
            "description": "All four estimate/MOE fields strictly parse as integer strings matching -?[0-9]+.",
            "unparsable_count": 0,
            "blank_count": 0,
        }

    # Non-negative check
    total_negatives = sum(len(v) for v in negative_values.values())
    if total_negatives > 0:
        report["hard_checks"]["numeric_values_nonnegative"] = {
            "status": "FAIL",
            "description": "All count estimates and margins of error must be nonnegative.",
            "negative_counts_by_column": {k: len(v) for k, v in negative_values.items()},
            "examples": [ex for v in negative_values.values() for ex in v][:5],
        }
        hard_failures.append("numeric_values_nonnegative")
    else:
        report["hard_checks"]["numeric_values_nonnegative"] = {
            "status": "PASS",
            "description": "All count estimates and margins of error must be nonnegative.",
            "negative_count": 0,
        }

    # Relational check: B28002_007E <= B28002_001E
    if broadband_exceeds_total:
        report["hard_checks"]["broadband_estimate_within_total"] = {
            "status": "FAIL",
            "description": "B28002_007E (broadband estimate) must not exceed B28002_001E (total households).",
            "violation_count": len(broadband_exceeds_total),
            "examples": broadband_exceeds_total[:5],
        }
        hard_failures.append("broadband_estimate_within_total")
    else:
        report["hard_checks"]["broadband_estimate_within_total"] = {
            "status": "PASS",
            "description": "B28002_007E (broadband estimate) must not exceed B28002_001E (total households).",
            "violation_count": 0,
        }

    # Step 2: Geography Review / Informational Diagnostic
    is_count_expected = (total_data_rows == OFFICIAL_5YEAR_COUNTY_COUNT)
    report["review_flags"]["county_record_count_review"] = {
        "status": "INFORMATIONAL" if is_count_expected else "REVIEW",
        "description": "Verification of county-or-equivalent record count against official Census ACS publication.",
        "actual_data_rows": total_data_rows,
        "official_published_count": OFFICIAL_5YEAR_COUNTY_COUNT,
        "count_matches_official": is_count_expected,
        "official_source_url": OFFICIAL_GEOGRAPHY_URL,
        "notes": (
            f"Observed count of {total_data_rows} data rows matches the official 3,222 "
            f"county-or-equivalent areas published by the U.S. Census Bureau for the 2024 "
            f"ACS 5-year estimates ({OFFICIAL_GEOGRAPHY_URL}). Per official Census documentation, "
            "county equivalents include geographic entities such as the District of Columbia, "
            "Puerto Rico municipios, and Connecticut planning regions. While the observed "
            "record count aligns with official publication, count agreement alone does not "
            "establish geographic boundary definitions, entity membership, or statistical "
            "comparability with FCC provider-reported availability data."
        ) if is_count_expected else (
            f"Observed count of {total_data_rows} data rows deviates by "
            f"{total_data_rows - OFFICIAL_5YEAR_COUNTY_COUNT} from the official 3,222 "
            f"county-or-equivalent areas published by the U.S. Census Bureau for the 2024 "
            f"ACS 5-year estimates ({OFFICIAL_GEOGRAPHY_URL})."
        ),
    }

    # Summary metrics & traceability
    report["summary_metrics"] = {
        "total_data_rows": total_data_rows,
        "unique_geography_keys": len(fips_seen),
        "unique_state_codes": len(unique_state_codes),
        "duplicate_keys": len(duplicate_fips),
        "malformed_records": len(malformed_records),
        "blank_values": total_blank,
        "unparsable_values": total_unparsable,
        "negative_values": total_negatives,
        "invalid_estimate_relationships": len(broadband_exceeds_total),
        "all_hard_checks_passed": len(hard_failures) == 0,
        "field_statistics": {
            col: {
                "min": numeric_stats[col]["min"],
                "max": numeric_stats[col]["max"],
                "zero_count": numeric_stats[col]["zero_count"],
                "parsed_count": numeric_stats[col]["parsed_count"],
            }
            for col, _ in NUMERIC_FIELDS
        },
    }

    report["overall_status"] = "PASS" if len(hard_failures) == 0 else "FAIL"

    _save_report(report, output_file)
    _print_summary(report)

    return 0 if len(hard_failures) == 0 else 1


def _save_report(report: dict, output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


def _print_summary(report: dict) -> None:
    meta = report.get("metadata", {})
    metrics = report.get("summary_metrics", {})
    hard_checks = report.get("hard_checks", {})
    review_flags = report.get("review_flags", {})
    overall_status = report.get("overall_status", "UNKNOWN")

    print("=" * 72)
    print(" CENSUS ACS B28002 DATA INTEGRITY AUDIT SUMMARY")
    print("=" * 72)
    print(f" Source:            {meta.get('source_name')}")
    print(f" Vintage:           {meta.get('acs_vintage')}")
    print(f" Table:             {meta.get('table_name')}")
    print(f" Input File:        {meta.get('input_path')} ({meta.get('file_size_bytes')} bytes)")
    print(f" Overall Status:    {overall_status}")
    print("-" * 72)
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
            print(f"  * {check_id}:")
            if "error" in check_data:
                print(f"    Error: {check_data['error']}")
            if "examples_unparsable" in check_data:
                print(f"    Examples Unparsable: {check_data['examples_unparsable']}")
            if "examples" in check_data:
                print(f"    Examples: {check_data['examples']}")

    print("-" * 72)
    print(" REVIEW / INFORMATIONAL DIAGNOSTICS:")
    for flag_id, flag_data in review_flags.items():
        print(f"  [{flag_data.get('status')}] {flag_id}: {flag_data.get('description')}")
        print(f"    Notes: {flag_data.get('notes')}")

    print("-" * 72)
    print(" ACTUAL OBSERVED METRICS:")
    print(f"  Total Data Rows:                {metrics.get('total_data_rows')}")
    print(f"  Unique Geography Keys (FIPS):   {metrics.get('unique_geography_keys')}")
    print(f"  Unique State Codes:             {metrics.get('unique_state_codes')}")
    print(f"  Duplicate Keys:                 {metrics.get('duplicate_keys')}")
    print(f"  Malformed Records:              {metrics.get('malformed_records')}")
    print(f"  Blank Values:                   {metrics.get('blank_values')}")
    print(f"  Unparsable Values:              {metrics.get('unparsable_values')}")
    print(f"  Negative Values:                {metrics.get('negative_values')}")
    print(f"  Broadband > Total Violations:   {metrics.get('invalid_estimate_relationships')}")

    field_stats = metrics.get("field_statistics", {})
    if field_stats:
        print("\n NUMERIC FIELD DISTRIBUTIONS:")
        print(f"  {'Field':<15} {'Min':<10} {'Max':<12} {'Zero Count':<12} {'Parsed':<10}")
        for field, stats in field_stats.items():
            print(
                f"  {field:<15} {str(stats.get('min')):<10} {str(stats.get('max')):<12} "
                f"{str(stats.get('zero_count')):<12} {str(stats.get('parsed_count')):<10}"
            )

    print("-" * 72)
    print(" IMPORTANT NOTICE / DISCLAIMER:")
    print(f"  {meta.get('disclaimer')}")
    print("=" * 72)


def main():
    parser = argparse.ArgumentParser(
        description="Audit Census ACS JSON data file for structural integrity and strict data validity."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to input Census ACS JSON file (e.g. data/raw/acs_b28002_2024_county.json)",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to output validation JSON report (e.g. reports/census_validation.json)",
    )
    args = parser.parse_args()

    exit_code = validate_census_file(args.input, args.output)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
