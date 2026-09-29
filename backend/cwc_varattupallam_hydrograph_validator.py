from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone


# ============================================================
# NEERAKSH
# CWC VARATTUPALLAM HYDROGRAPH VALIDATOR
#
# Purpose:
#   Validate the official CWC Varattupallam piping scenario
#   parameters and establish what can / cannot be independently
#   reproduced from the available published information.
#
# IMPORTANT:
#   This module does NOT invent:
#       - breach coordinates
#       - breach chainage
#       - inflow hydrograph
#       - discharge coefficient
#       - reservoir geometry
#       - hydraulic boundary conditions
#
#   Therefore it does NOT manufacture a fake hydrograph.
# ============================================================


PROJECT_ROOT = Path(
    r"C:\NEERAKSH-1"
)


CWC_SCENARIO_PATH = (
    PROJECT_ROOT
    / "data"
    / "engineering"
    / "varattupallam"
    / "cwc_hydraulic_scenarios.json"
)


AUDIT_PATH = (
    PROJECT_ROOT
    / "simulations"
    / "outputs"
    / "varattupallam"
    / "cwc_parameter_audit.json"
)


OUTPUT_DIR = (
    PROJECT_ROOT
    / "simulations"
    / "outputs"
    / "varattupallam"
    / "hydrograph_validation"
)


OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


OUTPUT_JSON = (
    OUTPUT_DIR
    / "cwc_piping_hydrograph_validation.json"
)


OUTPUT_TXT = (
    OUTPUT_DIR
    / "cwc_piping_hydrograph_validation.txt"
)


# ============================================================
# EXPECTED OFFICIAL CWC VALUES
#
# These are the values already recorded in the NEERAKSH
# official-reference configuration.
# ============================================================

EXPECTED = {

    "initial_reservoir_level_m":
        315.0,

    "inflow_m3s":
        0.0,

    "breach_invert_elevation_m":
        17.0,

    "breach_width_m":
        26.13,

    "breach_side_slope":
        0.6,

    "formation_time_hr":
        0.62,

    "published_peak_discharge_m3s":
        1970.38,

    "breach_development":
        "linear",
}


# ============================================================
# UTILITIES
# ============================================================

def utc_now():

    return datetime.now(
        timezone.utc
    ).isoformat()


def load_json(path: Path):

    if not path.exists():

        raise FileNotFoundError(
            f"File not found:\n{path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8-sig",
    ) as f:

        return json.load(f)

def save_json(path: Path, data):

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            data,
            f,
            indent=2,
        )
def nearly_equal(
    actual,
    expected,
    tolerance=1e-6,
):

    try:

        return (
            abs(
                float(actual)
                - float(expected)
            )
            <= tolerance
        )

    except (
        TypeError,
        ValueError,
    ):

        return False


def write_text(
    path,
    text,
):

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as f:

        f.write(text)


# ============================================================
# LOAD CWC SCENARIO
# ============================================================

def load_cwc_piping():

    data = load_json(
        CWC_SCENARIO_PATH
    )

    if "piping" not in data:

        raise RuntimeError(
            "The CWC scenario file does not contain "
            "the 'piping' section."
        )

    return data, data["piping"]


# ============================================================
# NORMALIZE EXISTING CWC JSON
# ============================================================

def normalize_piping(
    piping
):

    inflow_assumption = piping.get(
        "inflow_assumption"
    )

    # The CWC source states "zero inflow".
    if (
        isinstance(
            inflow_assumption,
            str,
        )
        and inflow_assumption.strip().lower()
        == "zero inflow"
    ):

        inflow_m3s = 0.0

    else:

        inflow_m3s = None

    return {

        "initial_reservoir_level_m":
            piping.get(
                "initial_reservoir_level_m"
            ),

        "inflow_m3s":
            inflow_m3s,

        "inflow_assumption":
            inflow_assumption,

        "breach_invert_elevation_m":
            piping.get(
                "breach_invert_elevation_m"
            ),

        "breach_width_m":
            piping.get(
                "breach_width_m"
            ),

        "breach_side_slope":
            piping.get(
                "breach_side_slope"
            ),

        "formation_time_hr":
            piping.get(
                "formation_time_hr"
            ),

        "published_peak_discharge_m3s":
            piping.get(
                "published_peak_discharge_m3s"
            ),

        "breach_development":
            piping.get(
                "breach_development"
            ),
    }


# ============================================================
# PARAMETER VALIDATION
# ============================================================

def validate_parameters(
    actual
):

    results = {}

    for key, expected in EXPECTED.items():

        actual_value = actual.get(
            key
        )

        if isinstance(
            expected,
            (int, float),
        ):

            passed = nearly_equal(
                actual_value,
                expected,
            )

        else:

            passed = (
                actual_value
                == expected
            )

        results[key] = {

            "expected":
                expected,

            "actual":
                actual_value,

            "status":
                "PASS"
                if passed
                else "FAIL",
        }

    return results


# ============================================================
# AUDIT CROSS-CHECK
# ============================================================

def validate_existing_audit():

    if not AUDIT_PATH.exists():

        return {

            "available":
                False,

            "status":
                "NOT_AVAILABLE",

            "message":
                (
                    "Existing CWC parameter audit file "
                    "was not found."
                ),
        }

    audit = load_json(
        AUDIT_PATH
    )

    overall_status = audit.get(
        "overall_status"
    )

    return {

        "available":
            True,

        "status":
            overall_status,

        "path":
            str(AUDIT_PATH),

        "message":
            (
                "Existing CWC parameter audit was "
                "loaded for cross-checking."
            ),
    }


# ============================================================
# SPATIAL VALIDATION
# ============================================================

def inspect_spatial_information(
    data
):

    spatial = data.get(
        "spatial_parameters",
        {}
    )

    breach_location_verified = spatial.get(
        "breach_location_verified",
        False,
    )

    breach_station_verified = spatial.get(
        "breach_station_verified",
        False,
    )

    latitude = spatial.get(
        "cwc_study_latitude"
    )

    longitude = spatial.get(
        "cwc_study_longitude"
    )

    return {

        "cwc_study_latitude":
            latitude,

        "cwc_study_longitude":
            longitude,

        "breach_location_verified":
            breach_location_verified,

        "breach_station_verified":
            breach_station_verified,

        "spatial_simulation_allowed":
            (
                breach_location_verified
                and breach_station_verified
            ),
    }


# ============================================================
# REPRODUCIBILITY ASSESSMENT
# ============================================================

def assess_reproducibility(
    data
):

    policy = data.get(
        "simulation_policy",
        {}
    )

    # The NEERAKSH source configuration explicitly records
    # that the breach location is not verified.
    spatial = data.get(
        "spatial_parameters",
        {}
    )

    breach_location_verified = spatial.get(
        "breach_location_verified",
        False,
    )

    breach_station_verified = spatial.get(
        "breach_station_verified",
        False,
    )

    simulation_ready = policy.get(
        "simulation_ready",
        False,
    )

    return {

        "published_peak_available":
            True,

        "published_hydrograph_timeseries_available":
            False,

        "numerical_overtopping_inflow_timeseries_available":
            False,

        "verified_breach_coordinate_available":
            breach_location_verified,

        "verified_breach_station_available":
            breach_station_verified,

        "complete_spatial_hydraulic_boundary_available":
            False,

        "independent_hydrograph_reproduction":
            False,

        "spatial_2d_reproduction":
            False,

        "simulation_ready_in_source":
            simulation_ready,

        "reason":
            (
                "The available reference information contains "
                "published breach parameters and published peak "
                "discharge, but does not provide a complete "
                "verified spatial breach definition and numerical "
                "hydrograph time series required for an independent "
                "reproduction."
            ),
    }


# ============================================================
# BUILD REPORT
# ============================================================

def build_report():

    print()
    print("=" * 72)
    print(
        "NEERAKSH – CWC VARATTUPALLAM "
        "HYDROGRAPH VALIDATOR"
    )
    print("=" * 72)
    print()

    print(
        "[SOURCE]"
    )

    print(
        f"  {CWC_SCENARIO_PATH}"
    )

    print()

    data, piping = load_cwc_piping()

    actual = normalize_piping(
        piping
    )

    print(
        "[OFFICIAL CWC PIPING VALUES]"
    )

    print(
        f"  Initial level : "
        f"{actual['initial_reservoir_level_m']} m"
    )

    print(
        f"  Inflow        : "
        f"{actual['inflow_m3s']} m3/s"
    )

    print(
        f"  Breach invert : "
        f"{actual['breach_invert_elevation_m']} m"
    )

    print(
        f"  Width         : "
        f"{actual['breach_width_m']} m"
    )

    print(
        f"  Side slope    : "
        f"{actual['breach_side_slope']}"
    )

    print(
        f"  Formation     : "
        f"{actual['formation_time_hr']} hr"
    )

    print(
        f"  Published Q   : "
        f"{actual['published_peak_discharge_m3s']} m3/s"
    )

    print(
        f"  Development   : "
        f"{actual['breach_development']}"
    )

    print()

    # --------------------------------------------------------
    # Parameter validation
    # --------------------------------------------------------

    parameter_results = (
        validate_parameters(
            actual
        )
    )

    parameter_failures = [
        key
        for key, result
        in parameter_results.items()
        if result["status"] != "PASS"
    ]

    print(
        "[PARAMETER VALIDATION]"
    )

    for key, result in (
        parameter_results.items()
    ):

        print(
            f"  {key}: "
            f"{result['status']}"
        )

    print()

    # --------------------------------------------------------
    # Existing audit
    # --------------------------------------------------------

    audit_result = (
        validate_existing_audit()
    )

    print(
        "[EXISTING CWC AUDIT]"
    )

    print(
        f"  Status: "
        f"{audit_result['status']}"
    )

    print()

    # --------------------------------------------------------
    # Spatial information
    # --------------------------------------------------------

    spatial_result = (
        inspect_spatial_information(
            data
        )
    )

    print(
        "[SPATIAL INFORMATION]"
    )

    print(
        f"  Study latitude : "
        f"{spatial_result['cwc_study_latitude']}"
    )

    print(
        f"  Study longitude: "
        f"{spatial_result['cwc_study_longitude']}"
    )

    print(
        f"  Breach location verified: "
        f"{spatial_result['breach_location_verified']}"
    )

    print(
        f"  Breach station verified: "
        f"{spatial_result['breach_station_verified']}"
    )

    print()

    # --------------------------------------------------------
    # Reproducibility
    # --------------------------------------------------------

    reproducibility = (
        assess_reproducibility(
            data
        )
    )

    print(
        "[REPRODUCIBILITY ASSESSMENT]"
    )

    print(
        "  Published peak available: "
        f"{reproducibility['published_peak_available']}"
    )

    print(
        "  Published hydrograph time series available: "
        f"{reproducibility['published_hydrograph_timeseries_available']}"
    )

    print(
        "  Verified breach coordinate available: "
        f"{reproducibility['verified_breach_coordinate_available']}"
    )

    print(
        "  Independent hydrograph reproduction: "
        f"{reproducibility['independent_hydrograph_reproduction']}"
    )

    print(
        "  Spatial 2D reproduction: "
        f"{reproducibility['spatial_2d_reproduction']}"
    )

    print()

    # --------------------------------------------------------
    # Overall status
    # --------------------------------------------------------

    if parameter_failures:

        overall_status = (
            "FAIL"
        )

        conclusion = (
            "One or more official CWC reference "
            "parameters do not match the configured "
            "NEERAKSH reference values."
        )

    else:

        overall_status = (
            "REFERENCE_PARAMETERS_VALIDATED"
        )

        conclusion = (
            "The configured CWC piping parameters match "
            "the official reference values stored in "
            "NEERAKSH. The published peak discharge is "
            "available as a validation target, but a "
            "complete independent hydrograph reproduction "
            "is not claimed because the required numerical "
            "time-series and verified spatial breach "
            "definition are unavailable."
        )

    report = {

        "status":
            overall_status,

        "timestamp_utc":
            utc_now(),

        "case_id":
            data.get(
                "case_id"
            ),

        "source":
            data.get(
                "source"
            ),

        "scenario":
            "piping",

        "parameters":
            parameter_results,

        "existing_parameter_audit":
            audit_result,

        "spatial_information":
            spatial_result,

        "reproducibility":
            reproducibility,

        "integrity": {

            "fabricated_values_used":
                False,

            "invented_breach_coordinate":
                False,

            "invented_breach_station":
                False,

            "invented_inflow_hydrograph":
                False,

            "invented_discharge_coefficient":
                False,

            "mettur_parameters_used":
                False,
        },

        "conclusion":
            conclusion,
    }

    return report


# ============================================================
# HUMAN-READABLE REPORT
# ============================================================

def make_text_report(
    report
):

    lines = []

    lines.append(
        "NEERAKSH – CWC VARATTUPALLAM "
        "HYDROGRAPH VALIDATION REPORT"
    )

    lines.append(
        "=" * 64
    )

    lines.append(
        f"Status: {report['status']}"
    )

    lines.append(
        f"Case: {report['case_id']}"
    )

    lines.append(
        f"Generated UTC: "
        f"{report['timestamp_utc']}"
    )

    lines.append("")

    lines.append(
        "OFFICIAL CWC PARAMETER CHECK"
    )

    lines.append(
        "-" * 64
    )

    for key, result in (
        report["parameters"].items()
    ):

        lines.append(
            f"{key}: "
            f"{result['status']} | "
            f"expected={result['expected']} | "
            f"actual={result['actual']}"
        )

    lines.append("")

    lines.append(
        "SPATIAL STATUS"
    )

    lines.append(
        "-" * 64
    )

    spatial = (
        report[
            "spatial_information"
        ]
    )

    lines.append(
        f"CWC study latitude: "
        f"{spatial['cwc_study_latitude']}"
    )

    lines.append(
        f"CWC study longitude: "
        f"{spatial['cwc_study_longitude']}"
    )

    lines.append(
        "Breach location verified: "
        f"{spatial['breach_location_verified']}"
    )

    lines.append(
        "Breach station verified: "
        f"{spatial['breach_station_verified']}"
    )

    lines.append("")

    lines.append(
        "REPRODUCIBILITY"
    )

    lines.append(
        "-" * 64
    )

    repro = (
        report[
            "reproducibility"
        ]
    )

    lines.append(
        "Published peak available: "
        f"{repro['published_peak_available']}"
    )

    lines.append(
        "Published hydrograph time series available: "
        f"{repro['published_hydrograph_timeseries_available']}"
    )

    lines.append(
        "Independent hydrograph reproduction: "
        f"{repro['independent_hydrograph_reproduction']}"
    )

    lines.append(
        "Spatial 2D reproduction: "
        f"{repro['spatial_2d_reproduction']}"
    )

    lines.append("")

    lines.append(
        "INTEGRITY"
    )

    lines.append(
        "-" * 64
    )

    integrity = (
        report[
            "integrity"
        ]
    )

    for key, value in integrity.items():

        lines.append(
            f"{key}: {value}"
        )

    lines.append("")

    lines.append(
        "CONCLUSION"
    )

    lines.append(
        "-" * 64
    )

    lines.append(
        report["conclusion"]
    )

    lines.append("")

    return "\n".join(
        lines
    )


# ============================================================
# MAIN
# ============================================================

def main():

    try:

        report = build_report()

        save_json(
            OUTPUT_JSON,
            report,
        )

        text_report = (
            make_text_report(
                report
            )
        )

        write_text(
            OUTPUT_TXT,
            text_report,
        )

        print(
            "=" * 72
        )

        print(
            "VALIDATION COMPLETE"
        )

        print(
            "=" * 72
        )

        print()

        print(
            f"Status: "
            f"{report['status']}"
        )

        print()

        print(
            "Reports:"
        )

        print(
            f"  {OUTPUT_JSON}"
        )

        print(
            f"  {OUTPUT_TXT}"
        )

        print()

        return 0

    except Exception as exc:

        print()
        print(
            "=" * 72
        )

        print(
            "VALIDATOR ERROR"
        )

        print(
            "=" * 72
        )

        print()

        print(
            str(exc)
        )

        print()

        return 1


if __name__ == "__main__":

    raise SystemExit(
        main()
    )