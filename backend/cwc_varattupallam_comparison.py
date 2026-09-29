from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone


# ============================================================
# NEERAKSH
# CWC VARATTUPALLAM REFERENCE COMPARISON
#
# Purpose:
#   Compare an ACTUAL NEERAKSH solver result against the
#   published CWC Varattupallam reference target.
#
# IMPORTANT:
#   - Never invent solver output.
#   - Never treat published CWC Q as NEERAKSH Q.
#   - Never claim independent reproduction when no solver
#     result exists.
#   - Never use the CWC reference as a Mettur parameter.
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


VALIDATION_REPORT_PATH = (
    PROJECT_ROOT
    / "simulations"
    / "outputs"
    / "varattupallam"
    / "hydrograph_validation"
    / "cwc_piping_hydrograph_validation.json"
)


# This is where a future REAL NEERAKSH hydraulic solver result
# can be placed.
#
# The comparison module will NOT create this file.
NEERAKSH_RESULT_PATH = (
    PROJECT_ROOT
    / "simulations"
    / "outputs"
    / "varattupallam"
    / "solver_2d"
    / "solver_result.json"
)


OUTPUT_DIR = (
    PROJECT_ROOT
    / "simulations"
    / "outputs"
    / "varattupallam"
    / "comparison"
)


OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


OUTPUT_JSON = (
    OUTPUT_DIR
    / "cwc_neeraksh_comparison.json"
)


OUTPUT_TXT = (
    OUTPUT_DIR
    / "cwc_neeraksh_comparison.txt"
)


# ============================================================
# UTILITY
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


def save_json(
    path: Path,
    data,
):

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


# ============================================================
# LOAD OFFICIAL CWC TARGET
# ============================================================

def load_cwc_target():

    data = load_json(
        CWC_SCENARIO_PATH
    )

    piping = data.get(
        "piping"
    )

    if not piping:

        raise RuntimeError(
            "Piping scenario not found "
            "in CWC scenario file."
        )

    inflow_assumption = piping.get(
        "inflow_assumption"
    )

    if (
        isinstance(
            inflow_assumption,
            str,
        )
        and inflow_assumption.lower()
        == "zero inflow"
    ):

        inflow_m3s = 0.0

    else:

        inflow_m3s = None

    return {

        "case_id":
            data.get(
                "case_id"
            ),

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
# LOAD VALIDATION STATUS
# ============================================================

def load_validation_status():

    if not VALIDATION_REPORT_PATH.exists():

        return {

            "available":
                False,

            "status":
                "VALIDATION_REPORT_MISSING",
        }

    report = load_json(
        VALIDATION_REPORT_PATH
    )

    return {

        "available":
            True,

        "status":
            report.get(
                "status"
            ),

        "report":
            report,
    }


# ============================================================
# LOAD ACTUAL NEERAKSH RESULT
# ============================================================

def load_neeraksh_result():

    if not NEERAKSH_RESULT_PATH.exists():

        return {

            "available":
                False,

            "status":
                "SOLVER_RESULT_NOT_AVAILABLE",

            "path":
                str(
                    NEERAKSH_RESULT_PATH
                ),
        }

    result = load_json(
        NEERAKSH_RESULT_PATH
    )

    return {

        "available":
            True,

        "status":
            result.get(
                "status"
            ),

        "result":
            result,

        "path":
            str(
                NEERAKSH_RESULT_PATH
            ),
    }


# ============================================================
# COMPARE
# ============================================================

def compare_peak(
    cwc_peak,
    neeraksh_result,
):

    if not neeraksh_result["available"]:

        return {

            "status":
                "NOT_COMPARABLE",

            "reason":
                "No actual NEERAKSH solver result exists.",

            "cwc_reference_peak_m3s":
                cwc_peak,

            "neeraksh_peak_m3s":
                None,

            "difference_m3s":
                None,

            "difference_percent":
                None,
        }

    simulation = (
        neeraksh_result[
            "result"
        ].get(
            "simulation",
            {}
        )
    )

    numerical_peak = simulation.get(
        "numerical_peak_source_discharge_m3s"
    )

    if numerical_peak is None:

        numerical_peak = simulation.get(
            "peak_numerical_source_discharge_m3s"
        )

    if numerical_peak is None:

        return {

            "status":
                "NOT_COMPARABLE",

            "reason":
                (
                    "NEERAKSH result exists, but "
                    "does not contain a numerical "
                    "peak discharge."
                ),

            "cwc_reference_peak_m3s":
                cwc_peak,

            "neeraksh_peak_m3s":
                None,

            "difference_m3s":
                None,

            "difference_percent":
                None,
        }

    difference = (
        float(numerical_peak)
        - float(cwc_peak)
    )

    if float(cwc_peak) != 0:

        difference_percent = (
            difference
            / float(cwc_peak)
            * 100.0
        )

    else:

        difference_percent = None

    return {

        "status":
            "COMPARABLE",

        "reason":
            "Actual NEERAKSH numerical result available.",

        "cwc_reference_peak_m3s":
            float(cwc_peak),

        "neeraksh_peak_m3s":
            float(numerical_peak),

        "difference_m3s":
            difference,

        "difference_percent":
            difference_percent,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 72)
    print(
        "NEERAKSH – CWC VARATTUPALLAM "
        "REFERENCE COMPARISON"
    )
    print("=" * 72)
    print()

    # --------------------------------------------------------
    # CWC
    # --------------------------------------------------------

    cwc = load_cwc_target()

    print(
        "[OFFICIAL CWC TARGET]"
    )

    print(
        f"  Case              : "
        f"{cwc['case_id']}"
    )

    print(
        f"  Initial level     : "
        f"{cwc['initial_reservoir_level_m']} m"
    )

    print(
        f"  Inflow            : "
        f"{cwc['inflow_m3s']} m3/s"
    )

    print(
        f"  Breach width      : "
        f"{cwc['breach_width_m']} m"
    )

    print(
        f"  Formation time    : "
        f"{cwc['formation_time_hr']} hr"
    )

    print(
        f"  Breach invert     : "
        f"{cwc['breach_invert_elevation_m']} m"
    )

    print(
        f"  Published peak Q  : "
        f"{cwc['published_peak_discharge_m3s']} m3/s"
    )

    print()

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    validation = (
        load_validation_status()
    )

    print(
        "[CWC VALIDATION STATUS]"
    )

    print(
        f"  Available: "
        f"{validation['available']}"
    )

    print(
        f"  Status   : "
        f"{validation['status']}"
    )

    print()

    # --------------------------------------------------------
    # NEERAKSH result
    # --------------------------------------------------------

    neeraksh = (
        load_neeraksh_result()
    )

    print(
        "[NEERAKSH SOLVER RESULT]"
    )

    print(
        f"  Available: "
        f"{neeraksh['available']}"
    )

    print(
        f"  Status   : "
        f"{neeraksh['status']}"
    )

    print(
        f"  Path     : "
        f"{neeraksh['path']}"
    )

    print()

    # --------------------------------------------------------
    # Comparison
    # --------------------------------------------------------

    peak_comparison = (
        compare_peak(
            cwc[
                "published_peak_discharge_m3s"
            ],
            neeraksh,
        )
    )

    print(
        "[PEAK DISCHARGE COMPARISON]"
    )

    print(
        f"  Status: "
        f"{peak_comparison['status']}"
    )

    print(
        f"  CWC reference: "
        f"{peak_comparison['cwc_reference_peak_m3s']}"
        f" m3/s"
    )

    print(
        f"  NEERAKSH result: "
        f"{peak_comparison['neeraksh_peak_m3s']}"
        f" m3/s"
    )

    if (
        peak_comparison[
            "difference_percent"
        ]
        is not None
    ):

        print(
            f"  Difference: "
            f"{peak_comparison['difference_percent']:.3f}%"
        )

    else:

        print(
            "  Difference: "
            "NOT AVAILABLE"
        )

    print()

    # --------------------------------------------------------
    # Overall conclusion
    # --------------------------------------------------------

    if (
        not neeraksh["available"]
    ):

        overall_status = (
            "REFERENCE_READY_NEERAKSH_RESULT_PENDING"
        )

        conclusion = (
            "The official CWC reference has been validated "
            "and is ready for comparison. No actual NEERAKSH "
            "solver result is currently available, so no "
            "independent agreement or error percentage is "
            "claimed."
        )

    elif (
        peak_comparison["status"]
        == "COMPARABLE"
    ):

        overall_status = (
            "COMPARISON_COMPLETED"
        )

        conclusion = (
            "An actual NEERAKSH numerical result was found "
            "and compared against the published CWC peak "
            "discharge. The difference reported here is a "
            "numerical comparison only and is not an overall "
            "validation of spatial inundation."
        )

    else:

        overall_status = (
            "COMPARISON_INCOMPLETE"
        )

        conclusion = (
            "A NEERAKSH solver result exists, but it does not "
            "contain the required numerical peak discharge "
            "field for comparison."
        )

    # --------------------------------------------------------
    # Integrity
    # --------------------------------------------------------

    report = {

        "status":
            overall_status,

        "timestamp_utc":
            utc_now(),

        "case_id":
            cwc["case_id"],

        "official_cwc_reference":
            cwc,

        "cwc_validation":
            validation,

        "neeraksh_solver_result":
            {
                "available":
                    neeraksh[
                        "available"
                    ],

                "status":
                    neeraksh[
                        "status"
                    ],

                "path":
                    neeraksh[
                        "path"
                    ],
            },

        "peak_discharge_comparison":
            peak_comparison,

        "integrity": {

            "fabricated_neeraksh_result":
                False,

            "fabricated_cwc_reference":
                False,

            "invented_breach_location":
                False,

            "mettur_parameters_used":
                False,

            "independent_spatial_validation_claimed":
                False,
        },

        "conclusion":
            conclusion,
    }

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    save_json(
        OUTPUT_JSON,
        report,
    )

    text_lines = [

        "NEERAKSH – CWC VARATTUPALLAM "
        "REFERENCE COMPARISON",

        "=" * 64,

        f"Status: {overall_status}",

        "",

        "CWC REFERENCE",

        "-" * 64,

        f"Case: {cwc['case_id']}",

        f"Initial level: "
        f"{cwc['initial_reservoir_level_m']} m",

        f"Inflow: "
        f"{cwc['inflow_m3s']} m3/s",

        f"Breach width: "
        f"{cwc['breach_width_m']} m",

        f"Formation time: "
        f"{cwc['formation_time_hr']} hr",

        f"Breach invert: "
        f"{cwc['breach_invert_elevation_m']} m",

        f"Published peak: "
        f"{cwc['published_peak_discharge_m3s']} m3/s",

        "",

        "NEERAKSH RESULT",

        "-" * 64,

        f"Available: "
        f"{neeraksh['available']}",

        f"Status: "
        f"{neeraksh['status']}",

        "",

        "PEAK COMPARISON",

        "-" * 64,

        f"Status: "
        f"{peak_comparison['status']}",

        f"CWC peak: "
        f"{peak_comparison['cwc_reference_peak_m3s']} m3/s",

        f"NEERAKSH peak: "
        f"{peak_comparison['neeraksh_peak_m3s']} m3/s",

        f"Difference: "
        f"{peak_comparison['difference_percent']}",

        "",

        "INTEGRITY",

        "-" * 64,

        "No fabricated NEERAKSH result.",

        "No fabricated CWC reference.",

        "No invented breach location.",

        "No Mettur parameters transferred.",

        "No independent spatial validation claimed.",

        "",

        "CONCLUSION",

        "-" * 64,

        conclusion,

        "",
    ]

    with open(
        OUTPUT_TXT,
        "w",
        encoding="utf-8",
    ) as f:

        f.write(
            "\n".join(
                text_lines
            )
        )

    print(
        "=" * 72
    )

    print(
        "COMPARISON MODULE COMPLETE"
    )

    print(
        "=" * 72
    )

    print()

    print(
        f"Status: {overall_status}"
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


if __name__ == "__main__":

    raise SystemExit(
        main()
    )