import json
from pathlib import Path
from datetime import datetime, timezone


# ============================================================
# NEERAKSH — AUTOMATIC METTUR HYPOTHETICAL SCENARIO
# ============================================================

BASE = Path(r"C:\NEERAKSH-1")


# ============================================================
# OUTPUT
# ============================================================

OUTPUT_FILE = (
    BASE
    / "simulations"
    / "inputs"
    / "mettur"
    / "hypothetical_user_scenario.json"
)


# ============================================================
# KNOWN OFFICIAL METTUR REFERENCE
# ============================================================
#
# Official NWDP/NWIC Mettur record:
#
# PIC  : TN12HH0005
# Dam  : Mettur
#
# These coordinates are used ONLY as the official dam
# reference point.
#
# They are NOT treated as a verified breach location.
#
# ============================================================

METTUR_LATITUDE = 11.8030555556
METTUR_LONGITUDE = 77.8066666667


# ============================================================
# POSSIBLE SCENARIO FILES
# ============================================================

SCENARIO_FILES = [

    BASE
    / "simulations"
    / "scenarios"
    / "mettur"
    / "mettur_source_bounded_scenarios.json",

    BASE
    / "simulations"
    / "scenarios"
    / "mettur"
    / "mettur_concrete_gravity_scenarios.json",
]


# ============================================================
# JSON UTILITIES
# ============================================================

def load_json(path):

    if not path.exists():

        raise FileNotFoundError(
            f"File not found:\n{path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8-sig"
    ) as f:

        return json.load(f)


def save_json(
    path,
    data
):

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
            indent=4,
            ensure_ascii=False
        )


# ============================================================
# FIND METTUR SCREENING SCENARIO
# ============================================================

def find_screening_base():

    print()
    print(
        "SEARCHING FOR METTUR SCREENING SCENARIO"
    )

    print(
        "-" * 70
    )

    for scenario_file in SCENARIO_FILES:

        print(
            f"Checking: {scenario_file}"
        )

        if not scenario_file.exists():

            continue

        try:

            document = load_json(
                scenario_file
            )

        except Exception:

            continue

        scenarios = document.get(
            "scenarios",
            []
        )

        for scenario in scenarios:

            if scenario.get(
                "scenario_id"
            ) == "METTUR_SCREENING_BASE":

                print(
                    "FOUND: METTUR_SCREENING_BASE"
                )

                print(
                    f"Source: {scenario_file}"
                )

                return (
                    scenario,
                    scenario_file
                )

    raise RuntimeError(
        "METTUR_SCREENING_BASE could not be found."
    )


# ============================================================
# EXTRACT SCREENING PARAMETERS
# ============================================================

def extract_screening_parameters(
    scenario
):

    failure = scenario.get(
        "failure",
        {}
    )

    # --------------------------------------------------------
    # WIDTH
    # --------------------------------------------------------

    width_data = failure.get(
        "breach_width_m"
    )

    width = None

    if isinstance(
        width_data,
        dict
    ):

        width = width_data.get(
            "screening_value"
        )

    elif width_data is not None:

        width = width_data

    # --------------------------------------------------------
    # FORMATION TIME
    # --------------------------------------------------------

    formation_data = failure.get(
        "formation_time_hr"
    )

    formation = None

    if isinstance(
        formation_data,
        dict
    ):

        formation = formation_data.get(
            "screening_value"
        )

    elif formation_data is not None:

        formation = formation_data

    # --------------------------------------------------------
    # SIDE SLOPE
    # --------------------------------------------------------

    side_data = failure.get(
        "side_slope_h_to_v"
    )

    side_slope = None

    if isinstance(
        side_data,
        dict
    ):

        side_slope = side_data.get(
            "screening_value"
        )

    elif side_data is not None:

        side_slope = side_data

    # --------------------------------------------------------
    # ALTERNATIVE FIELD NAMES
    # --------------------------------------------------------

    if width is None:

        width_data = failure.get(
            "breach_width"
        )

        if isinstance(
            width_data,
            dict
        ):

            width = width_data.get(
                "screening_value"
            )

    if formation is None:

        formation_data = failure.get(
            "formation_time"
        )

        if isinstance(
            formation_data,
            dict
        ):

            formation = formation_data.get(
                "screening_value"
            )

    if width is None:

        raise RuntimeError(
            "Breach width screening value not found."
        )

    if formation is None:

        raise RuntimeError(
            "Formation-time screening value not found."
        )

    if side_slope is None:

        side_slope = 0.0

    return {

        "width_m":
            float(width),

        "formation_time_hr":
            float(formation),

        "side_slope_h_to_v":
            float(side_slope)
    }


# ============================================================
# BUILD AUTOMATIC SCENARIO
# ============================================================

def build_scenario():

    screening, source_file = (
        find_screening_base()
    )

    parameters = (
        extract_screening_parameters(
            screening
        )
    )

    scenario = {

        "project":
            "NEERAKSH",

        "created_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "dam": {

            "name":
                "Mettur Dam",

            "reservoir":
                "Stanley Reservoir",

            "river":
                "Cauvery",

            "state":
                "Tamil Nadu",

            "district":
                "Salem",

            "pic":
                "TN12HH0005",

            "official_reference": {

                "latitude":
                    METTUR_LATITUDE,

                "longitude":
                    METTUR_LONGITUDE,

                "source":
                    "NWDP/NWIC Official Dam Dataset"
            }
        },

        "scenario": {

            "name":
                "METTUR_AUTOMATIC_HYPOTHETICAL",

            "mode":
                "AUTOMATIC_HYPOTHETICAL",

            "status":
                "READY",

            "simulation_allowed":
                True,

            "hypothetical":
                True,

            "failure_prediction":
                False,

            "fabricated_values":
                False
        },

        "failure": {

            "mechanism": {

                "value":
                    "HYPOTHETICAL_DAM_BREAK",

                "status":
                    "SCENARIO_ONLY",

                "verified":
                    False
            },

            "breach_location": {

                "latitude":
                    METTUR_LATITUDE,

                "longitude":
                    METTUR_LONGITUDE,

                "location_type":
                    "OFFICIAL_DAM_REFERENCE_POINT",

                "status":
                    "AUTOMATIC_SCENARIO_REFERENCE_ONLY",

                "verified":
                    False
            },

            "breach_geometry": {

                "width_m":
                    parameters["width_m"],

                "formation_time_hr":
                    parameters[
                        "formation_time_hr"
                    ],

                "side_slope_h_to_v":
                    parameters[
                        "side_slope_h_to_v"
                    ],

                "invert_elevation_m":
                    None,

                "crest_elevation_m":
                    None,

                "status":
                    "SCREENING_SCENARIO_PARAMETERS",

                "verified":
                    False
            }
        },

        "source": {

            "dam_reference":
                "NWDP/NWIC Official Dam Dataset",

            "screening_scenario":
                "METTUR_SCREENING_BASE",

            "screening_source":
                str(
                    source_file
                )
        },

        "provenance": {

            "official_dam_reference":
                True,

            "screening_parameters":
                True,

            "verified_breach_location":
                False,

            "verified_breach_geometry":
                False,

            "failure_prediction":
                False,

            "disclaimer":
                (
                    "Automatic hypothetical dam-break "
                    "scenario. The official Mettur dam "
                    "reference coordinates are used only "
                    "as the scenario reference point. "
                    "Breach parameters are screening "
                    "values and are not verified Mettur "
                    "failure parameters. Results must "
                    "not be interpreted as a prediction "
                    "of actual dam failure."
                )
        }
    }

    return scenario


# ============================================================
# DISPLAY
# ============================================================

def display_scenario(
    scenario
):

    location = (
        scenario[
            "failure"
        ][
            "breach_location"
        ]
    )

    geometry = (
        scenario[
            "failure"
        ][
            "breach_geometry"
        ]
    )

    print()
    print("=" * 70)
    print(
        "NEERAKSH — AUTOMATIC METTUR HYPOTHETICAL SCENARIO"
    )
    print("=" * 70)

    print()
    print(
        "NO MANUAL INPUT REQUIRED"
    )

    print()
    print(
        "SCENARIO"
    )

    print(
        "-" * 70
    )

    print(
        "Mode: "
        "AUTOMATIC_HYPOTHETICAL"
    )

    print(
        "Simulation allowed: "
        "True"
    )

    print(
        "Failure prediction: "
        "NO"
    )

    print()
    print(
        "OFFICIAL METTUR REFERENCE"
    )

    print(
        "-" * 70
    )

    print(
        f"Latitude : "
        f"{location['latitude']}"
    )

    print(
        f"Longitude: "
        f"{location['longitude']}"
    )

    print(
        "Status: "
        "REFERENCE POINT ONLY"
    )

    print()
    print(
        "AUTOMATIC SCREENING PARAMETERS"
    )

    print(
        "-" * 70
    )

    print(
        f"Breach width: "
        f"{geometry['width_m']} m"
    )

    print(
        f"Formation time: "
        f"{geometry['formation_time_hr']} hr"
    )

    print(
        f"Side slope: "
        f"{geometry['side_slope_h_to_v']}:1"
    )

    print()
    print(
        "UNVERIFIED PARAMETERS"
    )

    print(
        "-" * 70
    )

    print(
        "Breach invert: NOT VERIFIED"
    )

    print(
        "Breach crest: NOT VERIFIED"
    )

    print()
    print(
        "IMPORTANT"
    )

    print(
        "-" * 70
    )

    print(
        "This is an automatic hypothetical scenario."
    )

    print(
        "It is NOT a prediction of Mettur dam failure."
    )


# ============================================================
# MAIN
# ============================================================

def main():

    try:

        scenario = build_scenario()

        display_scenario(
            scenario
        )

        save_json(
            OUTPUT_FILE,
            scenario
        )

        print()
        print(
            "Saved:"
        )

        print(
            OUTPUT_FILE
        )

        print()
        print(
            "=" * 70
        )

        print(
            "AUTOMATIC SCENARIO CREATED"
        )

        print(
            "=" * 70
        )

    except Exception as e:

        print()
        print(
            "=" * 70
        )

        print(
            "AUTOMATIC SCENARIO FAILED"
        )

        print(
            "=" * 70
        )

        print()
        print(
            str(e)
        )


if __name__ == "__main__":

    main()