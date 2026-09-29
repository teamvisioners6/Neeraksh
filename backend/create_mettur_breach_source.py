import json
from pathlib import Path
from datetime import datetime, timezone


BASE = Path(r"C:\NEERAKSH-1")

INPUT = (
    BASE /
    "gis" /
    "processed" /
    "mettur" /
    "mettur_official_dam_reference.json"
)

OUTPUT = (
    BASE /
    "simulations" /
    "inputs" /
    "mettur" /
    "breach_source_definition.json"
)


def load_json(path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


dam = load_json(INPUT)


definition = {

    "project":
        "NEERAKSH",

    "dam": {

        "pic":
            dam["source"]["pic"],

        "name":
            dam["dam"]["name"],

        "river":
            dam["dam"]["river"],

        "latitude":
            dam["dam"]["latitude"],

        "longitude":
            dam["dam"]["longitude"]
    },

    "source_type":
        "ENGINEERING_BREACH_SECTION",

    "status":
        "WAITING_FOR_VERIFIED_SECTION",

    "breach": {

        "latitude":
            None,

        "longitude":
            None,

        "station_m":
            None,

        "invert_elevation_m":
            None,

        "crest_elevation_m":
            None,

        "width_m":
            None,

        "formation_time_hr":
            None,

        "side_slope_h_to_v":
            0.0
    },

    "provenance": {

        "location_source":
            None,

        "invert_source":
            None,

        "crest_source":
            None,

        "width_source":
            None,

        "formation_time_source":
            None,

        "methodology_source":
            None
    },

    "execution_policy": {

        "allow_missing_parameters":
            False,

        "allow_fabricated_values":
            False,

        "allow_dam_reference_as_breach":
            False,

        "require_parameter_provenance":
            True
    },

    "created_at":
        datetime.now(
            timezone.utc
        ).isoformat()
}


OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True
)

with open(
    OUTPUT,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        definition,
        f,
        indent=2
    )


print("=" * 70)
print("NEERAKSH — BREACH SOURCE DEFINITION")
print("=" * 70)

print()
print("Dam reference:", dam["dam"]["name"])
print("PIC:", dam["source"]["pic"])

print()
print(
    "Status:",
    definition["status"]
)

print()
print(
    "The official dam point is NOT being "
    "used as a breach point."
)

print()
print("Saved:")
print(OUTPUT)
