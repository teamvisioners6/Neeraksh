"""
NEERAKSH
CWC Varattupallam Reference Breach Geometry Validator

Purpose
-------
Reconstructs ONLY the published CWC breach-development geometry
for reference validation.

This module does NOT:
- invent a breach coordinate
- use the CWC study point as a breach point
- derive a breach location from DEM
- perform a 2D flood simulation
- transfer parameters to Mettur
- claim independent reproduction of the CWC peak discharge

Source:
Central Water Commission
"Dam Break Analysis of Varattupallam Dam: A Case Study"
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SCENARIO_PATH = (
    PROJECT_ROOT
    / "data"
    / "engineering"
    / "varattupallam"
    / "cwc_hydraulic_scenarios.json"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "simulations"
    / "outputs"
    / "varattupallam"
    / "reference_geometry"
)

OUTPUT_FILE = OUTPUT_DIR / "cwc_piping_breach_geometry.json"


def load_scenario() -> dict:
    """Load the official CWC reference scenario."""

    with SCENARIO_PATH.open(
        "r",
        encoding="utf-8-sig",
    ) as f:
        return json.load(f)


def linear_breach_geometry(
    initial_width_m: float,
    final_width_m: float,
    formation_time_s: float,
    final_side_slope: float,
    breach_invert_m: float,
    reservoir_level_m: float,
    n_steps: int = 101,
) -> dict:
    """
    Generate a linear breach-development reference series.

    The CWC source specifies linear breach development.

    Width is linearly increased from the initial width
    to the published final width.

    Side slope, invert, reservoir level and formation
    time are retained as published reference parameters.
    """

    if formation_time_s <= 0:
        raise ValueError(
            "Formation time must be positive."
        )

    if n_steps < 2:
        raise ValueError(
            "n_steps must be at least 2."
        )

    if final_width_m <= 0:
        raise ValueError(
            "Final breach width must be positive."
        )

    if final_side_slope <= 0:
        raise ValueError(
            "Side slope must be positive."
        )

    if breach_invert_m >= reservoir_level_m:
        raise ValueError(
            "Breach invert must be below reservoir level."
        )

    time_s = np.linspace(
        0.0,
        formation_time_s,
        n_steps,
    )

    fraction = time_s / formation_time_s

    width_m = (
        initial_width_m
        + fraction
        * (
            final_width_m
            - initial_width_m
        )
    )

    opening_height_m = (
        reservoir_level_m
        - breach_invert_m
    )

    bottom_width_m = width_m

    top_width_m = (
        bottom_width_m
        + 2.0
        * final_side_slope
        * opening_height_m
    )

    cross_sectional_area_m2 = (
        (
            bottom_width_m
            + top_width_m
        )
        / 2.0
        * opening_height_m
    )

    records = []

    for i in range(n_steps):

        records.append(
            {
                "time_s": float(time_s[i]),
                "time_hr": float(
                    time_s[i] / 3600.0
                ),
                "formation_fraction": float(
                    fraction[i]
                ),
                "breach_width_m": float(
                    width_m[i]
                ),
                "breach_invert_elevation_m": float(
                    breach_invert_m
                ),
                "reservoir_level_m": float(
                    reservoir_level_m
                ),
                "opening_height_m": float(
                    opening_height_m
                ),
                "side_slope": float(
                    final_side_slope
                ),
                "top_width_m": float(
                    top_width_m[i]
                ),
                "cross_sectional_area_m2": float(
                    cross_sectional_area_m2[i]
                ),
            }
        )

    return {
        "time_series": records,
        "final_geometry": {
            "breach_width_m": float(
                width_m[-1]
            ),
            "breach_invert_elevation_m": float(
                breach_invert_m
            ),
            "reservoir_level_m": float(
                reservoir_level_m
            ),
            "opening_height_m": float(
                opening_height_m
            ),
            "side_slope": float(
                final_side_slope
            ),
            "top_width_m": float(
                top_width_m[-1]
            ),
            "cross_sectional_area_m2": float(
                cross_sectional_area_m2[-1]
            ),
        },
    }


def validate_reference_geometry(
    scenario: dict,
    geometry: dict,
) -> dict:
    """Validate generated geometry against published CWC values."""

    piping = scenario["piping"]

    expected_width = float(
        piping["breach_width_m"]
    )

    expected_formation_hr = float(
        piping["formation_time_hr"]
    )

    expected_formation_s = (
        expected_formation_hr * 3600.0
    )

    expected_invert = float(
        piping["breach_invert_elevation_m"]
    )

    expected_side_slope = float(
        piping["breach_side_slope"]
    )

    expected_reservoir_level = float(
        piping["initial_reservoir_level_m"]
    )

    final = geometry["final_geometry"]

    width_match = np.isclose(
        final["breach_width_m"],
        expected_width,
        rtol=0.0,
        atol=1e-9,
    )

    invert_match = np.isclose(
        final["breach_invert_elevation_m"],
        expected_invert,
        rtol=0.0,
        atol=1e-9,
    )

    slope_match = np.isclose(
        final["side_slope"],
        expected_side_slope,
        rtol=0.0,
        atol=1e-9,
    )

    level_match = np.isclose(
        final["reservoir_level_m"],
        expected_reservoir_level,
        rtol=0.0,
        atol=1e-9,
    )

    actual_final_time = geometry[
        "time_series"
    ][-1]["time_s"]

    formation_match = np.isclose(
        actual_final_time,
        expected_formation_s,
        rtol=0.0,
        atol=1e-9,
    )

    linear_width = all(
        geometry["time_series"][i][
            "breach_width_m"
        ]
        <= geometry["time_series"][i + 1][
            "breach_width_m"
        ]
        for i in range(
            len(geometry["time_series"]) - 1
        )
    )

    return {
        "width_match": bool(width_match),
        "formation_time_match": bool(
            formation_match
        ),
        "breach_invert_match": bool(
            invert_match
        ),
        "side_slope_match": bool(
            slope_match
        ),
        "reservoir_level_match": bool(
            level_match
        ),
        "linear_width_development": bool(
            linear_width
        ),
        "all_reference_geometry_checks_pass": bool(
            width_match
            and formation_match
            and invert_match
            and slope_match
            and level_match
            and linear_width
        ),
    }


def main() -> None:

    print()
    print("=" * 72)
    print(
        "NEERAKSH – CWC VARATTUPALLAM "
        "REFERENCE BREACH GEOMETRY"
    )
    print("=" * 72)

    scenario = load_scenario()

    piping = scenario["piping"]

    formation_time_s = (
        float(
            piping["formation_time_hr"]
        )
        * 3600.0
    )

    print()
    print("[OFFICIAL CWC REFERENCE]")
    print(
        f"  Reservoir level : "
        f"{piping['initial_reservoir_level_m']} m"
    )
    print(
        f"  Breach invert   : "
        f"{piping['breach_invert_elevation_m']} m"
    )
    print(
        f"  Final width     : "
        f"{piping['breach_width_m']} m"
    )
    print(
        f"  Side slope      : "
        f"{piping['breach_side_slope']}"
    )
    print(
        f"  Formation time  : "
        f"{piping['formation_time_hr']} hr"
    )
    print(
        f"  Published peak Q: "
        f"{piping['published_peak_discharge_m3s']} m3/s"
    )

    geometry = linear_breach_geometry(
        initial_width_m=0.0,
        final_width_m=float(
            piping["breach_width_m"]
        ),
        formation_time_s=formation_time_s,
        final_side_slope=float(
            piping["breach_side_slope"]
        ),
        breach_invert_m=float(
            piping["breach_invert_elevation_m"]
        ),
        reservoir_level_m=float(
            piping["initial_reservoir_level_m"]
        ),
        n_steps=101,
    )

    validation = validate_reference_geometry(
        scenario,
        geometry,
    )

    result = {
        "case_id": scenario["case_id"],
        "scenario": "piping",
        "source": scenario["source"],
        "purpose": (
            "Reference-only reconstruction of "
            "published CWC breach-development parameters. "
            "The time-varying 0-to-final-width progression "
            "is a numerical linear-development representation, "
            "not a reported measured initial breach width."
        ),
        "spatial_claims": {
            "breach_coordinate_verified": False,
            "breach_station_verified": False,
            "cwc_study_point_used_as_breach": False,
        },

        "parameter_provenance": {
            "reservoir_level_m": "CWC_PUBLISHED",
            "breach_invert_elevation_m": "CWC_PUBLISHED",
            "final_breach_width_m": "CWC_PUBLISHED",
            "breach_side_slope": "CWC_PUBLISHED",
            "formation_time_hr": "CWC_PUBLISHED",
            "breach_development": "CWC_PUBLISHED",
            "initial_width_m": (
                "NUMERICAL_LINEAR_DEVELOPMENT_CONVENTION"
            ),
            "time_varying_width_series": (
                "DERIVED_FROM_PUBLISHED_FINAL_WIDTH_AND_LINEAR_DEVELOPMENT"
            ),
            "opening_height_series": (
                "DERIVED_FROM_RESERVOIR_LEVEL_AND_BREACH_INVERT"
            ),
            "opening_area_series": (
                "DERIVED_GEOMETRY"
            ),
        },
        "hydraulic_claims": {
            "independent_peak_discharge_reproduced": False,
            "published_peak_discharge_m3s": float(
                piping[
                    "published_peak_discharge_m3s"
                ]
            ),
        },
        "validation": validation,
        "geometry": geometry,
    }

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            result,
            f,
            indent=2,
        )

    print()
    print("[REFERENCE GEOMETRY VALIDATION]")

    print(
        "  Final width check       : "
        + (
            "PASS"
            if validation["width_match"]
            else "FAIL"
        )
    )

    print(
        "  Formation time check    : "
        + (
            "PASS"
            if validation[
                "formation_time_match"
            ]
            else "FAIL"
        )
    )

    print(
        "  Breach invert check     : "
        + (
            "PASS"
            if validation[
                "breach_invert_match"
            ]
            else "FAIL"
        )
    )

    print(
        "  Side slope check        : "
        + (
            "PASS"
            if validation[
                "side_slope_match"
            ]
            else "FAIL"
        )
    )

    print(
        "  Reservoir level check   : "
        + (
            "PASS"
            if validation[
                "reservoir_level_match"
            ]
            else "FAIL"
        )
    )

    print(
        "  Linear development      : "
        + (
            "PASS"
            if validation[
                "linear_width_development"
            ]
            else "FAIL"
        )
    )

    print()

    if validation[
        "all_reference_geometry_checks_pass"
    ]:
        print(
            "STATUS: REFERENCE_GEOMETRY_VALIDATED"
        )
    else:
        print(
            "STATUS: REFERENCE_GEOMETRY_CHECK_FAILED"
        )

    print()
    print(
        "Spatial breach location remains UNVERIFIED."
    )
    print(
        "No 2D flood simulation was executed."
    )

    print()
    print("Output:")
    print(f"  {OUTPUT_FILE}")
    print()


if __name__ == "__main__":
    main()