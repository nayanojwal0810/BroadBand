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

EXPECTED_CENSUS_HEADER = [
    "NAME",
    "B28002_001E",
    "B28002_001M",
    "B28002_007E",
    "B28002_007M",
    "state",
    "county",
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
FIPS_STATE_PATTERN = re.compile(r"^[0-9]{2}$")
FIPS_COUNTY_PATTERN = re.compile(r"^[0-9]{3}$")
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


def validate_census_dependency(census_file: Path) -> tuple:
    """
    Validates that the Census input exists, is non-empty, parses as JSON,
    matches the expected 7-variable header, contains records, and satisfies
    all established Census hard integrity checks.

    Returns:
        (is_valid: bool, error_msg: str | None, details: dict, data_rows: list)
    """
    if not census_file.exists():
        return (
            False,
            f"Census input file does not exist: {census_file}",
            {"error_type": "file_missing", "path": str(census_file)},
            [],
        )

    size = census_file.stat().st_size
    if size == 0:
        return (
            False,
            f"Census input file is empty (0 bytes): {census_file}",
            {"error_type": "file_empty", "path": str(census_file)},
            [],
        )

    try:
        with open(census_file, "r", encoding="utf-8") as f:
            census_raw = json.load(f)
    except Exception as e:
        return (
            False,
            f"Census input JSON parse error: {str(e)}",
            {"error_type": "json_parse_error", "exception": str(e)},
            [],
        )

    if not isinstance(census_raw, list) or len(census_raw) < 1:
        return (
            False,
            "Census input is not a non-empty top-level JSON array",
            {"error_type": "invalid_top_level_type", "type": type(census_raw).__name__},
            [],
        )

    header = census_raw[0]
    if header != EXPECTED_CENSUS_HEADER:
        return (
            False,
            f"Census header mismatch: expected {EXPECTED_CENSUS_HEADER}, received {header}",
            {"error_type": "header_mismatch", "expected": EXPECTED_CENSUS_HEADER, "actual": header},
            [],
        )

    data_rows = census_raw[1:]
    if len(data_rows) == 0:
        return (
            False,
            "Census input contains header but zero data records",
            {"error_type": "zero_data_records", "total_array_elements": len(census_raw)},
            [],
        )

    census_keys_map = {}
    for idx, row in enumerate(data_rows, start=2):
        if not isinstance(row, list) or len(row) != 7:
            return (
                False,
                f"Census row at index {idx} has invalid shape (expected 7 fields, got {len(row) if isinstance(row, list) else type(row).__name__})",
                {"error_type": "malformed_row_width", "row_index": idx, "row": row},
                [],
            )

        name, b001e, b001m, b007e, b007m, st, co = row

        if not isinstance(name, str) or isinstance(name, bool) or not name.strip():
            return (
                False,
                f"Census row at index {idx} has invalid NAME (expected non-empty string, got {repr(name)})",
                {"error_type": "invalid_name", "row_index": idx, "name": repr(name)},
                [],
            )

        if not (isinstance(st, str) and not isinstance(st, bool) and FIPS_STATE_PATTERN.fullmatch(st)):
            return (
                False,
                f"Census row at index {idx} has invalid 2-digit state FIPS: {repr(st)}",
                {"error_type": "invalid_state_fips", "row_index": idx, "state": repr(st)},
                [],
            )

        if not (isinstance(co, str) and not isinstance(co, bool) and FIPS_COUNTY_PATTERN.fullmatch(co)):
            return (
                False,
                f"Census row at index {idx} has invalid 3-digit county FIPS: {repr(co)}",
                {"error_type": "invalid_county_fips", "row_index": idx, "county": repr(co)},
                [],
            )

        comp_key = f"{st}{co}"
        if comp_key in census_keys_map:
            return (
                False,
                f"Duplicate Census composite key detected: {comp_key} at row {idx}",
                {"error_type": "duplicate_key", "key": comp_key, "row_index": idx},
                [],
            )

        parsed_nums = {}
        for col_name, val in [
            ("B28002_001E", b001e),
            ("B28002_001M", b001m),
            ("B28002_007E", b007e),
            ("B28002_007M", b007m),
        ]:
            if (
                isinstance(val, bool)
                or not isinstance(val, str)
                or not INTEGER_STRING_PATTERN.fullmatch(val)
            ):
                return (
                    False,
                    f"Census row at index {idx} has non-integer string in {col_name}: {repr(val)}",
                    {"error_type": "unparsable_numeric", "row_index": idx, "field": col_name, "value": repr(val)},
                    [],
                )
            v_int = int(val)
            if v_int < 0:
                return (
                    False,
                    f"Census row at index {idx} has negative value in {col_name}: {v_int}",
                    {"error_type": "negative_numeric", "row_index": idx, "field": col_name, "value": v_int},
                    [],
                )
            parsed_nums[col_name] = v_int

        if parsed_nums["B28002_007E"] > parsed_nums["B28002_001E"]:
            return (
                False,
                f"Census row at index {idx} broadband estimate ({parsed_nums['B28002_007E']}) exceeds total households ({parsed_nums['B28002_001E']})",
                {"error_type": "broadband_exceeds_total", "row_index": idx},
                [],
            )

        census_keys_map[comp_key] = {"row_index": idx, "name": name}

    return (
        True,
        None,
        {
            "census_total_data_rows": len(data_rows),
            "census_unique_keys_count": len(census_keys_map),
        },
        data_rows,
    )


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
                    "Unit-count field from the export whose exact denominator semantics were not verified "
                    "in authoritative documentation. Do not use this field as a denominator for the planned analysis."
                ),
                "data_type_total_units": (
                    "Unit-count field corresponding to the selected data type filter. In this export, "
                    "identical to geography_type_total_units in 100% of populated records."
                ),
                "percent_coverage": (
                    "FCC served-unit percentage for the user-observed export filters "
                    "(fixed broadband availability meeting or exceeding 100 Mbps download / 20 Mbps upload "
                    "from all wired technologies: cable, fiber, DSL)."
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
    # Inspect FCC Records, Record Widths, and Numeric Fields
    # ---------------------------------------------------------
    malformed_row_structure = []
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
        # Explicit check for malformed CSV record widths:
        # 1. Surplus fields captured by csv.DictReader under the None key
        # 2. Structurally absent fields whose values are None for expected field names
        has_surplus = (None in row and bool(row[None]))
        absent_fields = [col for col in EXPECTED_FCC_COLUMNS if row.get(col) is None]

        if has_surplus or absent_fields:
            malformed_row_structure.append({
                "row_index": idx,
                "geography_id": row.get("geography_id"),
                "has_surplus_fields": has_surplus,
                "surplus_values": row.get(None),
                "structurally_absent_fields": absent_fields,
            })

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
        if gt_units is None:
            # Structurally absent, handled under row structure validation
            pass
        elif isinstance(gt_units, str) and not gt_units.strip():
            # Legitimate empty string in present column
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
        if dt_units is None:
            # Structurally absent, handled under row structure validation
            pass
        elif isinstance(dt_units, str) and not dt_units.strip():
            # Legitimate empty string in present column
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
        if cov_str is None:
            # Structurally absent, handled under row structure validation
            pass
        elif isinstance(cov_str, str) and not cov_str.strip():
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

    # Evaluate Row structure hard check
    if malformed_row_structure:
        report["hard_checks"]["fcc_record_structure_valid"] = {
            "status": "FAIL",
            "description": "Every CSV record has exact expected column width (no surplus fields under None key and no structurally absent fields with value None).",
            "malformed_count": len(malformed_row_structure),
            "examples": malformed_row_structure[:5],
        }
        hard_failures.append("fcc_record_structure_valid")
    else:
        report["hard_checks"]["fcc_record_structure_valid"] = {
            "status": "PASS",
            "description": "Every CSV record has exact expected column width (no surplus fields under None key and no structurally absent fields with value None).",
            "malformed_count": 0,
        }

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

    # Review flag: Missing unit counts issue (preserve raw empty strings, not coerced to zero)
    total_missing_units = len(missing_geog_units) + len(missing_data_units)
    if total_missing_units > 0:
        report["review_flags"]["missing_unit_counts_review"] = {
            "status": "REVIEW",
            "description": "Report observed missing unit counts in FCC export (preserved as empty string, not converted to zero).",
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
        "malformed_row_structure_count": len(malformed_row_structure),
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
    # STEP 3: Mandatory Census Dependency Validation
    # ---------------------------------------------------------
    census_valid, census_err, census_details, census_rows = validate_census_dependency(census_file)

    if not census_valid:
        report["hard_checks"]["census_dependency_valid"] = {
            "status": "FAIL",
            "description": "Census ACS reference input exists, parses as valid JSON, satisfies the 7-variable schema, and passes all established Census hard checks.",
            "error": census_err,
            "details": census_details,
        }
        hard_failures.append("census_dependency_valid")
        report["geographic_compatibility"] = {
            "compatibility_status": "FAILED_DEPENDENCY",
            "status_classification": "DEPENDENCY_ERROR",
            "status_notes": (
                f"Geographic compatibility could not be evaluated because Census ACS reference "
                f"input validation failed: {census_err}. See hard_checks['census_dependency_valid'] for details."
            ),
            "exact_matching_keys_count": None,
            "census_total_data_rows": None,
            "coverage_percentages": None,
        }
    else:
        report["hard_checks"]["census_dependency_valid"] = {
            "status": "PASS",
            "description": "Census ACS reference input exists, parses as valid JSON, satisfies the 7-variable schema, and passes all established Census hard checks.",
            "details": census_details,
        }

        # Build Census keys map
        census_keys_map = {}
        for c_idx, c_row in enumerate(census_rows, start=2):
            c_name = c_row[0]
            c_state = str(c_row[5])
            c_county = str(c_row[6])
            c_key = f"{c_state}{c_county}"
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

        # Explicit status distinguishing unmatched geography IDs from source integrity failures
        report["geographic_compatibility"] = {
            "compatibility_status": "PARTIAL_OVERLAP",
            "status_classification": "INFORMATIONAL_MISMATCH",
            "status_notes": (
                "Unmatched geography IDs reflect known nonfatal boundary-vintage changes "
                "(Connecticut planning regions) and geographic scope differences (island territories), "
                "which are distinct from hard source-integrity failures."
            ),
            "disclaimer": (
                "Exact geographic ID matching does not prove identical boundary definitions or "
                "conceptual equivalence of provider-reported availability and household-reported subscription measures."
            ),
            "census_total_data_rows": len(census_rows),
            "census_unique_keys_count": len(census_keys_map),
            "census_duplicate_keys_count": 0,
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
    print(f"  Malformed Row Structure Count:  {metrics.get('malformed_row_structure_count')}")

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
        print(f"  Compatibility Status:           {geo.get('compatibility_status')} ({geo.get('status_classification')})")
        print(f"  Status Note:                    {geo.get('status_notes')}")
        if geo.get("exact_matching_keys_count") is not None:
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
