from pathlib import Path
import json


# ============================================================
# NEERAKSH — METTUR SCENARIO SELECTOR
# ============================================================

BASE = Path(r"C:\NEERAKSH-1")

SCENARIO_FILE = (
    BASE
    / "simulations"
    / "scenarios"
    / "mettur"
    / "mettur_source_bounded_scenarios.json"
)

OUTPUT_FILE = (
    BASE
    / "simulations"
    / "scenarios"
    / "mettur"
    / "selected_mettur_scenario.json"
)


def load_json(path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def save_json(path, data):

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )


def main():

    print()
    print("=" * 70)
    print(
        "NEERAKSH — METTUR SCENARIO SELECTOR"
    )
    print("=" * 70)

    if not SCENARIO_FILE.exists():

        raise FileNotFoundError(
            f"Scenario file not found:\n{SCENARIO_FILE}"
        )

    document = load_json(
        SCENARIO_FILE
    )

    scenarios = document.get(
        "scenarios",
        []
    )

    if not scenarios:

        raise ValueError(
            "No scenarios found."
        )

    print()
    print(
        "AVAILABLE SCENARIOS"
    )

    print("-" * 50)

    for index, scenario in enumerate(
        scenarios,
        start=1
    ):

        print(
            f"{index}. "
            f"{scenario['scenario_id']}"
        )

        print(
            "   Purpose:",
            scenario["purpose"]
        )

        print(
            "   Status:",
            scenario["status"]
        )

        print(
            "   Simulation allowed:",
            scenario["simulation_allowed"]
        )

    print()

    # --------------------------------------------------------
    # Default selection
    # --------------------------------------------------------

    selected = scenarios[1]

    print(
        "DEFAULT SELECTION:"
    )

    print(
        selected["scenario_id"]
    )

    # --------------------------------------------------------
    # Preserve execution restrictions
    # --------------------------------------------------------

    selected_output = {

        "project":
            "NEERAKSH",

        "dam":
            "Mettur Dam",

        "selected_scenario":
            selected,

        "selection_policy":
            {

                "selection_only":
                    True,

                "simulation_allowed":
                    selected[
                        "simulation_allowed"
                    ],

                "allow_fabricated_values":
                    False,

                "allow_unverified_breach_location":
                    False,

                "allow_unverified_hydraulic_initial_level":
                    False,

                "allow_screening_values_as_measured":
                    False
            },

        "next_step":
            "Obtain verified engineering breach inputs "
            "before enabling numerical simulation."
    }

    save_json(
        OUTPUT_FILE,
        selected_output
    )

    print()
    print(
        "SELECTION STATUS"
    )

    print("-" * 50)

    print(
        "Selected:",
        selected["scenario_id"]
    )

    print(
        "Simulation allowed:",
        selected["simulation_allowed"]
    )

    print(
        "Fabricated values:",
        False
    )

    print()
    print(
        "Saved:"
    )

    print(
        OUTPUT_FILE
    )


if __name__ == "__main__":

    main()