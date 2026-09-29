import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(r"C:\NEERAKSH-1")

SCENARIO_FILE = (
    BASE /
    "simulations" /
    "scenarios" /
    "mettur" /
    "mettur_concrete_gravity_scenarios.json"
)

OUTPUT_DIR = (
    BASE /
    "simulations" /
    "inputs" /
    "mettur"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_FILE = (
    OUTPUT_DIR /
    "mettur_breach_geometry.json"
)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------
# IMPORTANT:
#
# These fields are intentionally NULL.
#
# They must be populated from an actual dam cross-section /
# engineering assessment / authorized scenario.
#
# The software will refuse to execute the breach hydrograph
# until they are supplied.
# ------------------------------------------------------------

geometry = {

    "project": "NEERAKSH",

    "dam": {
        "name": "Mettur Dam / Stanley Reservoir",
        "dam_type": "Concrete Gravity",
        "river": "Cauvery",
        "state": "Tamil Nadu"
    },

    "status": "INCOMPLETE",

    "breach_definition": {

        "location": {

            "latitude": None,

            "longitude": None,

            "source": None,

            "source_type": None
        },

        "station_m": {

            "value": None,

            "reference": None,

            "source": None
        },

        "invert_elevation_m": {

            "value": None,

            "datum": None,

            "source": None,

            "source_type": None
        },

        "crest_elevation_m": {

            "value": None,

            "datum": None,

            "source": None
        },

        "breach_width_m": {

            "value": None,

            "source": None
        },

        "formation_time_hr": {

            "value": None,

            "source": None
        },

        "side_slope_h_to_v": {

            "value": 0.0,

            "source": (
                "Concrete gravity screening assumption: "
                "vertical breach sides"
            )
        }
    },

    "validation_rules": {

        "location_required": True,

        "invert_required": True,

        "crest_required": True,

        "width_required": True,

        "formation_time_required": True,

        "source_required_for_engineering_parameters":
            True,

        "fabricated_values_allowed":
            False
    },

    "created_at":
        datetime.now(
            timezone.utc
        ).isoformat()
}


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        geometry,
        f,
        indent=2
    )


print("=" * 70)
print("NEERAKSH — METTUR BREACH GEOMETRY")
print("=" * 70)

print()
print("Status: INCOMPLETE")

print()
print("Required engineering inputs:")

print("1. Breach latitude")
print("2. Breach longitude")
print("3. Dam station / chainage")
print("4. Breach invert elevation")
print("5. Dam crest elevation")
print("6. Breach width")
print("7. Formation time")

print()
print("Fabricated values allowed: NO")

print()
print("Saved:")
print(OUTPUT_FILE)
