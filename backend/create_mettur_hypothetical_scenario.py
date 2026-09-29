from pathlib import Path
import json


PROJECT_ROOT = Path(r"C:\NEERAKSH-1")

OUTPUT_FILE = (
    PROJECT_ROOT
    / "simulations"
    / "inputs"
    / "mettur"
    / "hypothetical_user_scenario.json"
)


def get_float(prompt, positive=False):
    while True:
        value = input(prompt).strip()

        try:
            number = float(value)

            if positive and number <= 0:
                print("Value must be greater than 0.")
                continue

            return number

        except ValueError:
            print("Please enter a valid numeric value.")


def main():

    print()
    print("=" * 70)
    print("NEERAKSH — METTUR HYPOTHETICAL DAM-BREAK SCENARIO")
    print("=" * 70)

    print()
    print("IMPORTANT")
    print("-" * 70)
    print(
        "These parameters represent a USER-SUPPLIED HYPOTHETICAL "
        "SCENARIO."
    )
    print(
        "They are NOT verified Mettur failure parameters and "
        "are NOT a failure prediction."
    )

    print()
    print("BREACH LOCATION")
    print("-" * 70)

    latitude = get_float(
        "Breach latitude: "
    )

    longitude = get_float(
        "Breach longitude: "
    )

    print()
    print("BREACH GEOMETRY")
    print("-" * 70)

    station_m = get_float(
        "Breach station/chainage (m): ",
        positive=True
    )

    invert_m = get_float(
        "Breach invert elevation (m): "
    )

    crest_m = get_float(
        "Breach crest elevation (m): "
    )

    if invert_m >= crest_m:

        print()
        print(
            "ERROR: Breach invert must be lower than "
            "breach crest."
        )

        return

    width_m = get_float(
        "Final breach width (m): ",
        positive=True
    )

    formation_hr = get_float(
        "Formation time (hours): ",
        positive=True
    )

    side_slope = get_float(
        "Side slope H:V: ",
        positive=True
    )

    scenario = {

        "project": "NEERAKSH",

        "dam": {
            "name": "Mettur",
            "reservoir": "Stanley Reservoir",
            "state": "Tamil Nadu",
            "country": "India"
        },

        "scenario": {

            "name": "METTUR_HYPOTHETICAL_USER_SCENARIO",

            "mode": "HYPOTHETICAL_USER_SUPPLIED",

            "status": "READY",

            "simulation_allowed": True,

            "hypothetical": True,

            "failure_prediction": False,

            "fabricated_values": False
        },

        "failure": {

            "mechanism": {

                "value": "USER_SUPPLIED_HYPOTHETICAL",

                "verified": False
            },

            "breach_location": {

                "latitude": latitude,

                "longitude": longitude,

                "station_m": station_m,

                "verified": False
            },

            "breach_geometry": {

                "invert_elevation_m": invert_m,

                "crest_elevation_m": crest_m,

                "width_m": width_m,

                "formation_time_hr": formation_hr,

                "side_slope_h_to_v": side_slope,

                "verified": False
            }
        },

        "provenance": {

            "source_type": "USER_SUPPLIED_HYPOTHETICAL",

            "observed_data_used": True,

            "official_failure_parameters": False,

            "engineering_parameters_verified": False,

            "disclaimer": (
                "Hypothetical dam-break scenario using "
                "user-supplied engineering assumptions. "
                "Parameters are not verified Mettur dam "
                "failure parameters and must not be "
                "interpreted as a failure prediction."
            )
        }
    }

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            scenario,
            f,
            indent=4
        )

    print()
    print("=" * 70)
    print("SCENARIO CREATED")
    print("=" * 70)

    print()
    print("Mode:")
    print("HYPOTHETICAL_USER_SUPPLIED")

    print()
    print("Breach location:")
    print(f"Latitude : {latitude}")
    print(f"Longitude: {longitude}")

    print()
    print("Breach geometry:")
    print(f"Station       : {station_m} m")
    print(f"Invert        : {invert_m} m")
    print(f"Crest         : {crest_m} m")
    print(f"Width         : {width_m} m")
    print(f"Formation     : {formation_hr} hr")
    print(f"Side slope    : {side_slope}:1")

    print()
    print("Simulation allowed: True")

    print()
    print("IMPORTANT:")
    print(
        "This is a hypothetical scenario, "
        "NOT a prediction of Mettur dam failure."
    )

    print()
    print("Saved:")
    print(OUTPUT_FILE)

    print()


if __name__ == "__main__":
    main()