import json
import math
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(r"C:\NEERAKSH-1")

SCENARIO_FILE = (
    BASE /
    "simulations" /
    "scenarios" /
    "mettur" /
    "mettur_scenario_definition.json"
)

OUTPUT_DIR = (
    BASE /
    "simulations" /
    "outputs" /
    "mettur"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("NEERAKSH - BREACH PARAMETER ENGINE")
print("=" * 70)

# ------------------------------------------------------------
# Load scenario
# ------------------------------------------------------------

with open(SCENARIO_FILE, "r", encoding="utf-8") as f:
    scenario = json.load(f)

failure = scenario["failure_scenario"]

# ------------------------------------------------------------
# Validate required inputs
# ------------------------------------------------------------

required = {
    "failure_type": failure.get("failure_type"),
    "breach_width_m": failure.get("breach_width_m"),
    "breach_formation_time_hr": failure.get(
        "breach_formation_time_hr"
    ),
    "breach_side_slope_h_to_v": failure.get(
        "breach_side_slope_h_to_v"
    ),
    "initial_reservoir_level_m": failure.get(
        "initial_reservoir_level_m"
    ),
}

missing = [
    key
    for key, value in required.items()
    if value is None
]

print("\nSCENARIO VALIDATION")
print("-" * 50)

if missing:

    print("STATUS: PARAMETERS REQUIRED")

    for item in missing:
        print(f"Missing: {item}")

    print("\nNo breach hydrograph has been generated.")
    print(
        "NEERAKSH will not fabricate breach parameters."
    )

    status = {
        "status": "WAITING_FOR_ENGINEERING_PARAMETERS",
        "missing_parameters": missing,
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat()
    }

    status_file = (
        OUTPUT_DIR /
        "breach_engine_status.json"
    )

    with open(
        status_file,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            status,
            f,
            indent=2
        )

    print("\nSaved:")
    print(status_file)

else:

    print("All required breach parameters supplied.")

    # --------------------------------------------------------
    # Basic breach-flow calculation
    # --------------------------------------------------------

    width = float(
        failure["breach_width_m"]
    )

    formation_time = float(
        failure["breach_formation_time_hr"]
    )

    side_slope = float(
        failure["breach_side_slope_h_to_v"]
    )

    reservoir_level = float(
        failure["initial_reservoir_level_m"]
    )

    print("\nINPUTS")
    print("-" * 50)
    print("Failure type:", failure["failure_type"])
    print("Breach width:", width, "m")
    print("Formation time:", formation_time, "hr")
    print("Side slope H:V:", side_slope)
    print("Reservoir level:", reservoir_level, "m")

    # Hydrograph generation will be implemented after
    # the breach geometry and hydraulic head are validated.

    result = {
        "status": "PARAMETERS_ACCEPTED",
        "failure_type": failure["failure_type"],
        "breach_width_m": width,
        "formation_time_hr": formation_time,
        "side_slope_h_to_v": side_slope,
        "initial_reservoir_level_m": reservoir_level,
        "hydrograph_status": "PENDING_HYDRAULIC_HEAD_VALIDATION"
    }

    output = (
        OUTPUT_DIR /
        "breach_parameters_validated.json"
    )

    with open(
        output,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            result,
            f,
            indent=2
        )

    print("\nSaved:")
    print(output)

print("\n" + "=" * 70)
print("BREACH ENGINE CHECK COMPLETE")
print("=" * 70)
