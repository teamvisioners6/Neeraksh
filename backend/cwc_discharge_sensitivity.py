"""
NEERAKSH
CWC Varattupallam Piping Discharge Sensitivity

Purpose
-------
Evaluate a simple broad-opening/orifice-style discharge relation
using the published CWC breach geometry.
The 315 m - 17 m difference is treated only
as a sensitivity input, not as a verified
instantaneous hydraulic head.

IMPORTANT
---------
The discharge coefficient is NOT published in the available CWC
reference parameters. Therefore Cd values are treated as
NEERAKSH hydraulic assumptions.

This script does NOT:
- claim to reproduce the CWC hydrograph
- claim 1970.38 m3/s as a NEERAKSH result
- invent a CWC discharge coefficient
- determine breach location
- perform a 2D inundation simulation
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path


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
    / "discharge_sensitivity"
)

JSON_OUTPUT = (
    OUTPUT_DIR
    / "cwc_piping_discharge_sensitivity.json"
)

CSV_OUTPUT = (
    OUTPUT_DIR
    / "cwc_piping_discharge_sensitivity.csv"
)


GRAVITY = 9.80665


# These are deliberately assumptions for sensitivity analysis.
# They are NOT CWC-published values.
CD_VALUES = [
    0.40,
    0.45,
    0.50,
    0.55,
    0.60,
    0.65,
    0.70,
    0.75,
    0.80,
]


def load_scenario() -> dict:
    with SCENARIO_PATH.open(
        "r",
        encoding="utf-8-sig",
    ) as f:
        return json.load(f)


def calculate_discharge(
    cd: float,
    width_m: float,
    head_m: float,
) -> float:
    """
    Simple discharge relation used by the current
    NEERAKSH breach-discharge function.

    Q = Cd * B * h^(3/2) * sqrt(2g)
    """

    if cd <= 0:
        raise ValueError(
            "Cd must be positive."
        )

    if width_m <= 0:
        return 0.0

    if head_m <= 0:
        return 0.0

    return (
        cd
        * width_m
        * head_m ** 1.5
        * math.sqrt(
            2.0 * GRAVITY
        )
    )


def main() -> None:

    print()
    print("=" * 72)
    print(
        "NEERAKSH – CWC VARATTUPALLAM "
        "DISCHARGE SENSITIVITY"
    )
    print("=" * 72)

    scenario = load_scenario()

    piping = scenario["piping"]

    reservoir_level = float(
        piping[
            "initial_reservoir_level_m"
        ]
    )

    breach_invert = float(
        piping[
            "breach_invert_elevation_m"
        ]
    )

    final_width = float(
        piping[
            "breach_width_m"
        ]
    )

    published_peak = float(
        piping[
            "published_peak_discharge_m3s"
        ]
    )

    head = (
        reservoir_level
        - breach_invert
    )

    print()
    print("[CWC PUBLISHED INPUTS]")
    print(
        f"  Reservoir level : "
        f"{reservoir_level:.3f} m"
    )
    print(
        f"  Breach invert   : "
        f"{breach_invert:.3f} m"
    )
    print(
        f"  Final width     : "
        f"{final_width:.3f} m"
    )
    print(
        f"  Level difference used for sensitivity : "
        f"{head:.3f} m"
    )
    print(
        f"  CWC peak target : "
        f"{published_peak:.2f} m3/s"
    )

    print()
    print(
        "[HYDRAULIC ASSUMPTION]"
    )
    print(
        "  Discharge coefficient Cd "
        "is NOT published by CWC."
    )
    print(
        "  Cd values below are "
        "NEERAKSH sensitivity assumptions."
    )

    results = []

    for cd in CD_VALUES:

        q = calculate_discharge(
            cd=cd,
            width_m=final_width,
            head_m=head,
        )

        difference = (
            q - published_peak
        )

        percentage_difference = (
            difference
            / published_peak
            * 100.0
        )

        results.append(
            {
                "cd": cd,
                "calculated_peak_discharge_m3s": q,
                "cwc_published_peak_m3s": (
                    published_peak
                ),
                "difference_m3s": difference,
                "difference_percent": (
                    percentage_difference
                ),
            }
        )

    print()
    print(
        "[DISCHARGE SENSITIVITY]"
    )

    print(
        f"{'Cd':>6}"
        f"{'Q (m3/s)':>16}"
        f"{'Difference':>16}"
        f"{'Difference %':>16}"
    )

    print("-" * 56)

    for result in results:

        print(
            f"{result['cd']:>6.2f}"
            f"{result['calculated_peak_discharge_m3s']:>16.3f}"
            f"{result['difference_m3s']:>16.3f}"
            f"{result['difference_percent']:>15.2f}%"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = {
        "case_id": scenario[
            "case_id"
        ],
        "scenario": "piping",
        "purpose": (
            "Sensitivity analysis of a "
            "simple breach discharge relation "
            "using CWC-published geometry."
        ),
        "cwc_published_parameters": {
            "reservoir_level_m": (
                reservoir_level
            ),
            "breach_invert_elevation_m": (
                breach_invert
            ),
            "final_breach_width_m": (
                final_width
            ),
            "published_peak_discharge_m3s": (
                published_peak
            ),
        },
        "derived_parameters": {
            "level_difference_used_for_sensitivity_m": head,
        },
        "model": {
            "equation": (
                "Q = Cd * B * h^(3/2) * sqrt(2g)"
            ),
            "gravity_mps2": GRAVITY,
            "discharge_coefficient_source": (
                "NEERAKSH_SENSITIVITY_ASSUMPTION"
            ),
        },
        "results": results,
        "interpretation": {
            "cwc_peak_is_validation_target": True,
            "cwc_peak_is_neeraksh_output": False,
            "independent_cwc_hydrograph_reproduced": False,
            "breach_location_verified": False,
            "spatial_2d_simulation_executed": False,
        },
    }

    with JSON_OUTPUT.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            output,
            f,
            indent=2,
        )

    with CSV_OUTPUT.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "cd",
                "calculated_peak_discharge_m3s",
                "cwc_published_peak_m3s",
                "difference_m3s",
                "difference_percent",
            ],
        )

        writer.writeheader()

        writer.writerows(
            results
        )

    print()
    print(
        "STATUS: DISCHARGE_SENSITIVITY_COMPLETE"
    )

    print()
    print(
        "The CWC peak remains a validation target."
    )
    print(
        "No Cd value has been treated as CWC-published."
    )
    print(
        "No 2D inundation simulation was executed."
    )

    print()
    print("Outputs:")
    print(
        f"  {JSON_OUTPUT}"
    )
    print(
        f"  {CSV_OUTPUT}"
    )
    print()


if __name__ == "__main__":
    main()