from pathlib import Path
import json
from datetime import datetime, timezone


ROOT = Path(r"C:\NEERAKSH-1")

SCENARIO = (
    ROOT
    / "data"
    / "engineering"
    / "varattupallam"
    / "cwc_hydraulic_scenarios.json"
)

VALIDATION = (
    ROOT
    / "simulations"
    / "outputs"
    / "varattupallam"
    / "hydrograph_validation"
    / "cwc_piping_hydrograph_validation.json"
)

GEOMETRY_TEST = (
    ROOT
    / "simulations"
    / "outputs"
    / "varattupallam"
    / "hydraulic_feasibility"
    / "cwc_geometry_test.json"
)

SPATIAL_CONFIG = (
    ROOT
    / "data"
    / "engineering"
    / "varattupallam"
    / "validation_spatial_config.json"
)

OUTPUT_DIR = (
    ROOT
    / "simulations"
    / "outputs"
    / "varattupallam"
    / "solver_input_gate"
)

OUTPUT = (
    OUTPUT_DIR
    / "solver_input_gate.json"
)


def load_json(path):

    if not path.exists():

        raise FileNotFoundError(
            f"Missing file:\n{path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8-sig",
    ) as f:

        return json.load(f)


def utc_now():

    return datetime.now(
        timezone.utc
    ).isoformat()


def main():

    print()
    print("=" * 72)
    print(
        "NEERAKSH – CWC VARATTUPALLAM "
        "SOLVER INPUT GATE"
    )
    print("=" * 72)
    print()

    scenario = load_json(
        SCENARIO
    )

    validation = load_json(
        VALIDATION
    )

    geometry = load_json(
        GEOMETRY_TEST
    )

    spatial = load_json(
        SPATIAL_CONFIG
    )

    # --------------------------------------------------------
    # CWC parameter validation
    # --------------------------------------------------------

    parameter_status = (
        validation.get(
            "status"
        )
        == "REFERENCE_PARAMETERS_VALIDATED"
    )

    print(
        "[CWC PARAMETERS]"
    )

    print(
        f"  Status: "
        f"{validation.get('status')}"
    )

    print(
        f"  PASS: "
        f"{parameter_status}"
    )

    print()

    # --------------------------------------------------------
    # Geometry validation
    # --------------------------------------------------------

    geometry_status = (
        geometry.get(
            "status"
        )
        == "PASS"
    )

    print(
        "[BREACH GEOMETRY]"
    )

    print(
        f"  Status: "
        f"{geometry.get('status')}"
    )

    print(
        f"  PASS: "
        f"{geometry_status}"
    )

    print()

    # --------------------------------------------------------
    # Spatial verification
    # --------------------------------------------------------

    spatial_params = (
        spatial.get(
            "spatial_reference",
            {}
        )
    )

    hydraulic = (
        spatial.get(
            "hydraulic_interpretation",
            {}
        )
    )

    breach_location_verified = bool(
        spatial_params.get(
            "breach_location_verified",
            False
        )
    )

    breach_station_verified = bool(
        spatial_params.get(
            "breach_station_verified",
            False
        )
    )

    hydraulic_initial_verified = bool(
        hydraulic.get(
            "hydraulic_initial_condition_verified",
            False
        )
    )

    simulation_ready = bool(
        hydraulic.get(
            "simulation_ready",
            False
        )
    )

    print(
        "[SPATIAL / HYDRAULIC GATES]"
    )

    print(
        f"  Breach location verified: "
        f"{breach_location_verified}"
    )

    print(
        f"  Breach station verified : "
        f"{breach_station_verified}"
    )

    print(
        f"  Hydraulic initial state : "
        f"{hydraulic_initial_verified}"
    )

    print(
        f"  Simulation ready        : "
        f"{simulation_ready}"
    )

    print()

    # --------------------------------------------------------
    # Individual gates
    # --------------------------------------------------------

    gates = {

        "official_cwc_parameters":
            parameter_status,

        "breach_geometry_validation":
            geometry_status,

        "breach_location_verified":
            breach_location_verified,

        "breach_station_verified":
            breach_station_verified,

        "hydraulic_initial_condition_verified":
            hydraulic_initial_verified,

        "simulation_ready_flag":
            simulation_ready,
    }

    # --------------------------------------------------------
    # Solver readiness
    # --------------------------------------------------------

    all_required = all(
        gates.values()
    )

    if all_required:

        status = (
            "SOLVER_INPUT_READY"
        )

        reason = (
            "All required CWC reference, geometry, "
            "spatial and hydraulic gates are verified."
        )

    else:

        status = (
            "BLOCKED_SPATIAL_OR_HYDRAULIC_INPUT"
        )

        missing = [
            key
            for key, value
            in gates.items()
            if not value
        ]

        reason = (
            "Solver execution is blocked because "
            "the following required gates are not verified: "
            + ", ".join(
                missing
            )
        )

    # --------------------------------------------------------
    # Integrity
    # --------------------------------------------------------

    integrity = {

        "fabricated_values":
            False,

        "invented_breach_location":
            False,

        "invented_breach_station":
            False,

        "invented_hydraulic_initial_condition":
            False,

        "mettur_parameters_used":
            False,

        "study_point_used_as_breach_point":
            False,

        "solver_bypass":
            False,
    }

    # --------------------------------------------------------
    # Report
    # --------------------------------------------------------

    report = {

        "status":
            status,

        "timestamp_utc":
            utc_now(),

        "case_id":
            scenario.get(
                "case_id"
            ),

        "gates":
            gates,

        "reason":
            reason,

        "integrity":
            integrity,

        "source_files":
            {

                "scenario":
                    str(
                        SCENARIO
                    ),

                "parameter_validation":
                    str(
                        VALIDATION
                    ),

                "geometry_test":
                    str(
                        GEOMETRY_TEST
                    ),

                "spatial_config":
                    str(
                        SPATIAL_CONFIG
                    ),
            },
    }

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        OUTPUT,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            report,
            f,
            indent=2,
        )

    # --------------------------------------------------------
    # Console
    # --------------------------------------------------------

    print(
        "=" * 72
    )

    print(
        "SOLVER INPUT DECISION"
    )

    print(
        "=" * 72
    )

    print(
        f"Status: {status}"
    )

    print()

    print(
        f"Reason:"
    )

    print(
        f"  {reason}"
    )

    print()

    print(
        "Integrity:"
    )

    for key, value in integrity.items():

        print(
            f"  {key}: {value}"
        )

    print()

    print(
        "Report:"
    )

    print(
        f"  {OUTPUT}"
    )

    print()

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )