from __future__ import annotations

import json
import math
from pathlib import Path
from datetime import datetime, timezone


# ============================================================
# NEERAKSH
# CWC VARATTUPALLAM HYDRAULIC FEASIBILITY ENGINE
#
# Purpose:
#   Calculate the VERIFIED breach-development geometry from
#   the official CWC piping scenario.
#
# IMPORTANT:
#   This module does NOT invent:
#       - discharge coefficient
#       - breach location
#       - breach station
#       - reservoir area curve
#       - hydraulic roughness
#       - arbitrary head assumptions
#
#   Therefore it does NOT claim independent reproduction of
#   the CWC published peak discharge.
#
#   It establishes exactly which hydraulic quantities can be
#   calculated from the verified CWC inputs.
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


VALIDATION_PATH = (
    PROJECT_ROOT
    / "simulations"
    / "outputs"
    / "varattupallam"
    / "hydrograph_validation"
    / "cwc_piping_hydrograph_validation.json"
)


OUTPUT_DIR = (
    PROJECT_ROOT
    / "simulations"
    / "outputs"
    / "varattupallam"
    / "hydraulic_feasibility"
)


OUTPUT_JSON = (
    OUTPUT_DIR
    / "cwc_piping_hydraulic_feasibility.json"
)


OUTPUT_CSV = (
    OUTPUT_DIR
    / "cwc_piping_breach_development.csv"
)


OUTPUT_TXT = (
    OUTPUT_DIR
    / "cwc_piping_hydraulic_feasibility.txt"
)


OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def load_json(path: Path):

    if not path.exists():

        raise FileNotFoundError(
            f"Required file not found:\n{path}"
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


def utc_now():

    return datetime.now(
        timezone.utc
    ).isoformat()


# ============================================================
# LOAD OFFICIAL CWC PIPING SCENARIO
# ============================================================

def load_cwc_piping():

    data = load_json(
        CWC_SCENARIO_PATH
    )

    piping = data.get(
        "piping"
    )

    if not piping:

        raise RuntimeError(
            "Piping scenario missing from "
            "CWC hydraulic scenario file."
        )

    inflow_assumption = (
        piping.get(
            "inflow_assumption"
        )
    )

    if (
        isinstance(
            inflow_assumption,
            str,
        )
        and
        inflow_assumption.lower()
        == "zero inflow"
    ):

        inflow_m3s = 0.0

    else:

        inflow_m3s = None

    required = {

        "initial_reservoir_level_m":
            piping.get(
                "initial_reservoir_level_m"
            ),

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

    missing = [
        key
        for key, value
        in required.items()
        if value is None
    ]

    if missing:

        raise RuntimeError(
            "Missing official CWC parameters:\n"
            + "\n".join(
                f"  - {item}"
                for item in missing
            )
        )

    return {

        "case_id":
            data.get(
                "case_id"
            ),

        **required,

        "inflow_m3s":
            inflow_m3s,

        "inflow_assumption":
            inflow_assumption,
    }


# ============================================================
# VALIDATION REPORT
# ============================================================

def load_validation():

    if not VALIDATION_PATH.exists():

        return {

            "available":
                False,

            "status":
                "VALIDATION_REPORT_MISSING",
        }

    data = load_json(
        VALIDATION_PATH
    )

    return {

        "available":
            True,

        "status":
            data.get(
                "status"
            ),
    }


# ============================================================
# BREACH GEOMETRY
# ============================================================

def calculate_breach_geometry(
    width_final_m: float,
    side_slope: float,
    invert_m: float,
    reservoir_level_m: float,
    formation_time_hr: float,
    sample_count: int = 101,
):

    if formation_time_hr <= 0:

        raise ValueError(
            "Formation time must be > 0."
        )

    if width_final_m <= 0:

        raise ValueError(
            "Breach width must be > 0."
        )

    if invert_m >= reservoir_level_m:

        raise ValueError(
            "Breach invert must be below "
            "initial reservoir level."
        )

    if sample_count < 2:

        raise ValueError(
            "sample_count must be >= 2."
        )

    records = []

    for i in range(
        sample_count
    ):

        fraction = (
            i
            / (sample_count - 1)
        )

        time_hr = (
            fraction
            * formation_time_hr
        )

        # CWC specifies linear breach development.
        width_m = (
            fraction
            * width_final_m
        )

        breach_depth_m = (
            reservoir_level_m
            - invert_m
        )

        # Vertical depth of the breach opening.
        #
        # This is calculated from the published
        # reservoir level and breach invert.
        #
        # It is NOT treated as hydraulic head.
        opening_height_m = (
            fraction
            * breach_depth_m
        )

        # Trapezoidal opening area.
        #
        # Side slope is horizontal:vertical.
        #
        # For a trapezoidal opening:
        #
        # area =
        # depth * (bottom_width
        #          + side_slope * depth)
        #
        # This is purely breach geometry.
        opening_area_m2 = (
            opening_height_m
            * (
                width_m
                + side_slope
                * opening_height_m
            )
        )

        top_width_m = (
            width_m
            + 2.0
            * side_slope
            * opening_height_m
        )

        records.append(
            {

                "time_hr":
                    time_hr,

                "development_fraction":
                    fraction,

                "breach_width_m":
                    width_m,

                "breach_invert_elevation_m":
                    invert_m,

                "reservoir_reference_level_m":
                    reservoir_level_m,

                "opening_height_m":
                    opening_height_m,

                "top_width_m":
                    top_width_m,

                "opening_area_m2":
                    opening_area_m2,
            }
        )

    return records


# ============================================================
# WRITE CSV
# ============================================================

def save_csv(
    records,
):

    import csv

    if not records:

        return

    fieldnames = list(
        records[0].keys()
    )

    with open(
        OUTPUT_CSV,
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        writer.writerows(
            records
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 72)
    print(
        "NEERAKSH – CWC VARATTUPALLAM "
        "HYDRAULIC FEASIBILITY ENGINE"
    )
    print("=" * 72)
    print()

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    cwc = load_cwc_piping()

    validation = (
        load_validation()
    )

    print(
        "[OFFICIAL CWC INPUT]"
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
        f"  Breach invert     : "
        f"{cwc['breach_invert_elevation_m']} m"
    )

    print(
        f"  Final width       : "
        f"{cwc['breach_width_m']} m"
    )

    print(
        f"  Side slope        : "
        f"{cwc['breach_side_slope']}"
    )

    print(
        f"  Formation time    : "
        f"{cwc['formation_time_hr']} hr"
    )

    print(
        f"  Development       : "
        f"{cwc['breach_development']}"
    )

    print(
        f"  CWC peak reference: "
        f"{cwc['published_peak_discharge_m3s']} m3/s"
    )

    print()

    # --------------------------------------------------------
    # Validate linear development
    # --------------------------------------------------------

    development = str(
        cwc[
            "breach_development"
        ]
    ).lower()

    if development != "linear":

        raise RuntimeError(
            "This validator expects the official "
            "CWC linear breach-development assumption."
        )

    if cwc["inflow_m3s"] != 0.0:

        raise RuntimeError(
            "This module is specifically configured "
            "for the official CWC zero-inflow piping case."
        )

    # --------------------------------------------------------
    # Calculate geometry
    # --------------------------------------------------------

    records = (
        calculate_breach_geometry(
            width_final_m=
                float(
                    cwc[
                        "breach_width_m"
                    ]
                ),

            side_slope=
                float(
                    cwc[
                        "breach_side_slope"
                    ]
                ),

            invert_m=
                float(
                    cwc[
                        "breach_invert_elevation_m"
                    ]
                ),

            reservoir_level_m=
                float(
                    cwc[
                        "initial_reservoir_level_m"
                    ]
                ),

            formation_time_hr=
                float(
                    cwc[
                        "formation_time_hr"
                    ]
                ),

            sample_count=101,
        )
    )

    save_csv(
        records
    )

    # --------------------------------------------------------
    # Final geometry
    # --------------------------------------------------------

    final = records[-1]

    initial = records[0]

    print(
        "[BREACH DEVELOPMENT]"
    )

    print(
        f"  Initial width     : "
        f"{initial['breach_width_m']:.3f} m"
    )

    print(
        f"  Final width       : "
        f"{final['breach_width_m']:.3f} m"
    )

    print(
        f"  Initial area      : "
        f"{initial['opening_area_m2']:.3f} m2"
    )

    print(
        f"  Final area        : "
        f"{final['opening_area_m2']:.3f} m2"
    )

    print(
        f"  Final top width   : "
        f"{final['top_width_m']:.3f} m"
    )

    print(
        f"  Opening height    : "
        f"{final['opening_height_m']:.3f} m"
    )

    print()

    # --------------------------------------------------------
    # Hydraulic identifiability
    # --------------------------------------------------------

    missing_hydraulic_inputs = [

        "reservoir stage-storage relationship "
        "for the CWC scenario",

        "verified breach spatial location",

        "verified downstream cross-sections "
        "or 2D computational domain",

        "hydraulic roughness",

        "hydraulic boundary conditions",

        "discharge coefficient / solver-specific "
        "hydraulic formulation required for independent "
        "peak-flow reproduction",
    ]

    print(
        "[HYDRAULIC REPRODUCIBILITY CHECK]"
    )

    print(
        "  Published CWC peak available : TRUE"
    )

    print(
        "  Numerical CWC hydrograph     : FALSE"
    )

    print(
        "  Verified breach coordinate   : FALSE"
    )

    print(
        "  Independent peak reproduction: FALSE"
    )

    print()

    print(
        "[MISSING INFORMATION]"
    )

    for item in missing_hydraulic_inputs:

        print(
            f"  - {item}"
        )

    print()

    # --------------------------------------------------------
    # Status
    # --------------------------------------------------------

    status = (
        "BREACH_GEOMETRY_VALIDATED"
    )

    conclusion = (
        "The official CWC piping breach-development "
        "parameters have been loaded and the time-varying "
        "breach geometry has been calculated. The available "
        "source information is insufficient to independently "
        "reproduce the published peak discharge of "
        f"{cwc['published_peak_discharge_m3s']} m3/s. "
        "No discharge coefficient, breach location, "
        "roughness, boundary condition, or other missing "
        "hydraulic parameter has been invented."
    )

    report = {

        "status":
            status,

        "timestamp_utc":
            utc_now(),

        "case_id":
            cwc["case_id"],

        "source":
            {
                "scenario_file":
                    str(
                        CWC_SCENARIO_PATH
                    ),

                "validation_file":
                    str(
                        VALIDATION_PATH
                    ),

                "validation_status":
                    validation[
                        "status"
                    ],
            },

        "official_parameters":
            cwc,

        "breach_development":
            {

                "development_type":
                    "linear",

                "sample_count":
                    len(
                        records
                    ),

                "initial_geometry":
                    initial,

                "final_geometry":
                    final,

                "csv_output":
                    str(
                        OUTPUT_CSV
                    ),
            },

        "hydraulic_reproducibility":
            {

                "published_peak_available":
                    True,

                "published_hydrograph_available":
                    False,

                "verified_breach_coordinate_available":
                    False,

                "independent_peak_reproduction":
                    False,

                "spatial_2d_reproduction":
                    False,

                "missing_inputs":
                    missing_hydraulic_inputs,
            },

        "integrity":
            {

                "fabricated_values":
                    False,

                "invented_breach_location":
                    False,

                "invented_discharge_coefficient":
                    False,

                "invented_hydraulic_boundary":
                    False,

                "mettur_parameters_used":
                    False,

                "cwc_published_peak_treated_as_solver_output":
                    False,
            },

        "conclusion":
            conclusion,
    }

    save_json(
        OUTPUT_JSON,
        report,
    )

    # --------------------------------------------------------
    # Text report
    # --------------------------------------------------------

    lines = [

        "NEERAKSH – CWC VARATTUPALLAM "
        "HYDRAULIC FEASIBILITY",

        "=" * 64,

        f"Status: {status}",

        "",

        "OFFICIAL CWC PARAMETERS",

        "-" * 64,

        f"Initial reservoir level: "
        f"{cwc['initial_reservoir_level_m']} m",

        f"Inflow: "
        f"{cwc['inflow_m3s']} m3/s",

        f"Breach invert: "
        f"{cwc['breach_invert_elevation_m']} m",

        f"Final breach width: "
        f"{cwc['breach_width_m']} m",

        f"Side slope: "
        f"{cwc['breach_side_slope']}",

        f"Formation time: "
        f"{cwc['formation_time_hr']} hr",

        f"Published CWC peak: "
        f"{cwc['published_peak_discharge_m3s']} m3/s",

        "",

        "CALCULATED BREACH GEOMETRY",

        "-" * 64,

        f"Initial opening area: "
        f"{initial['opening_area_m2']:.6f} m2",

        f"Final opening area: "
        f"{final['opening_area_m2']:.6f} m2",

        f"Final top width: "
        f"{final['top_width_m']:.6f} m",

        f"Final opening height: "
        f"{final['opening_height_m']:.6f} m",

        "",

        "HYDRAULIC REPRODUCIBILITY",

        "-" * 64,

        "Published peak available: TRUE",

        "Published hydrograph available: FALSE",

        "Verified breach coordinate available: FALSE",

        "Independent peak reproduction: FALSE",

        "Spatial 2D reproduction: FALSE",

        "",

        "INTEGRITY",

        "-" * 64,

        "No fabricated values.",

        "No invented breach location.",

        "No invented discharge coefficient.",

        "No invented hydraulic boundary.",

        "No Mettur parameters used.",

        "CWC published peak is NOT treated as NEERAKSH output.",

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
                lines
            )
        )

    print("=" * 72)
    print(
        "HYDRAULIC FEASIBILITY COMPLETE"
    )
    print("=" * 72)
    print()

    print(
        f"Status: {status}"
    )

    print()

    print(
        "Outputs:"
    )

    print(
        f"  {OUTPUT_JSON}"
    )

    print(
        f"  {OUTPUT_CSV}"
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