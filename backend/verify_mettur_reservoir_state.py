from pathlib import Path
import json
import csv


# ============================================================
# NEERAKSH
# METTUR RESERVOIR STATE VERIFICATION
#
# Purpose:
#   Keep government observed reservoir data and CWC
#   elevation-storage data separate until the vertical
#   datum relationship is explicitly verified.
#
# NO FABRICATED VALUES
# ============================================================


TN_OBSERVATION = Path(
    r"C:\NEERAKSH-1\data\mettur\latest_official_observation.json"
)

CWC_TABLE = Path(
    r"C:\NEERAKSH-1\data\hydrology\mettur\cwc_stage_storage_2020.csv"
)

OUTPUT_DIR = Path(
    r"C:\NEERAKSH-1\simulations\outputs\mettur\reservoir_state"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ------------------------------------------------------------
# Load TN Government observation
# ------------------------------------------------------------

def load_tn_observation():

    if not TN_OBSERVATION.exists():

        raise FileNotFoundError(
            f"TN Government observation not found:\n"
            f"{TN_OBSERVATION}"
        )

    with TN_OBSERVATION.open(
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)

    return data


# ------------------------------------------------------------
# Load CWC table
# ------------------------------------------------------------

def load_cwc_table():

    if not CWC_TABLE.exists():

        raise FileNotFoundError(
            f"CWC stage-storage table not found:\n"
            f"{CWC_TABLE}"
        )

    rows = []

    with CWC_TABLE.open(
        "r",
        encoding="utf-8"
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:

            rows.append({
                "elevation_m":
                    float(row["elevation_m"]),

                "area_Mm2":
                    float(
                        row["water_spread_area_Mm2"]
                    ),

                "segmental_capacity_MCM":
                    float(
                        row[
                            "segmental_live_capacity_MCM"
                        ]
                    ),

                "cumulative_capacity_MCM":
                    float(
                        row[
                            "cumulative_live_capacity_MCM"
                        ]
                    )
            })

    return rows


# ------------------------------------------------------------
# Main verification
# ------------------------------------------------------------

def main():

    print("=" * 75)
    print(
        "NEERAKSH — METTUR RESERVOIR STATE VERIFICATION"
    )
    print("=" * 75)

    # --------------------------------------------------------
    # TN Government source
    # --------------------------------------------------------

    tn = load_tn_observation()

    print()
    print("SOURCE 1 — GOVERNMENT OF TAMIL NADU")
    print("-" * 75)

    print(
        "Source:",
        tn.get("source", "Not specified")
    )

    print(
        "Reservoir:",
        tn.get("reservoir", "Not specified")
    )

    print(
        "Water level:",
        tn.get("water_level_ft"),
        "ft"
    )

    print(
        "Storage:",
        tn.get("storage_mcft"),
        "M.Cft"
    )

    print(
        "Inflow:",
        tn.get("inflow_cusecs"),
        "cusecs"
    )

    print(
        "Outflow:",
        tn.get("outflow_cusecs"),
        "cusecs"
    )

    print(
        "Fetched at:",
        tn.get("fetched_at")
    )

    # --------------------------------------------------------
    # CWC source
    # --------------------------------------------------------

    cwc = load_cwc_table()

    print()
    print("SOURCE 2 — CENTRAL WATER COMMISSION")
    print("-" * 75)

    print(
        "CWC rows:",
        len(cwc)
    )

    print(
        "Minimum elevation:",
        cwc[0]["elevation_m"],
        "m"
    )

    print(
        "Maximum elevation:",
        cwc[-1]["elevation_m"],
        "m"
    )

    print(
        "FRL storage:",
        cwc[-1]["cumulative_capacity_MCM"],
        "MCM"
    )

    # --------------------------------------------------------
    # Datum verification
    # --------------------------------------------------------

    print()
    print("VERTICAL DATUM VERIFICATION")
    print("-" * 75)

    datum_verified = False

    print(
        "TN portal water-level datum:",
        "NOT VERIFIED"
    )

    print(
        "CWC Table 3 elevation datum:",
        "CWC elevation reference"
    )

    print(
        "Relationship between the two:",
        "NOT ESTABLISHED"
    )

    print()
    print(
        "Therefore:"
    )

    print(
        "83.07 ft MUST NOT be converted directly "
        "into CWC elevation."
    )

    print(
        "TN portal storage MUST NOT be replaced "
        "by interpolated CWC storage."
    )

    print(
        "No absolute reservoir elevation will be "
        "invented."
    )

    # --------------------------------------------------------
    # What is currently usable?
    # --------------------------------------------------------

    usable = {
        "government_observation": True,
        "government_water_level_ft": True,
        "government_storage_mcft": True,
        "government_inflow_cusecs": True,
        "government_outflow_cusecs": True,
        "cwc_stage_storage_curve": True,
        "cwc_elevation_to_storage_interpolation": True,
        "tn_level_to_cwc_elevation": False,
        "verified_initial_elevation_for_hydraulic_model": False,
        "breach_hydrograph_ready": False
    }

    print()
    print("CURRENT DATA READINESS")
    print("-" * 75)

    for key, value in usable.items():

        print(
            f"{key}: {value}"
        )

    # --------------------------------------------------------
    # Required engineering information
    # --------------------------------------------------------

    print()
    print("REQUIRED BEFORE RESERVOIR-STATE LINKING")
    print("-" * 75)

    required = [
        "Verified vertical datum relationship",
        "Verified reservoir gauge datum / benchmark",
        "Verified conversion from TN portal level to CWC elevation",
        "Or a separately sourced absolute reservoir elevation"
    ]

    for index, item in enumerate(
        required,
        start=1
    ):

        print(
            f"{index}. {item}"
        )

    # --------------------------------------------------------
    # Save verification
    # --------------------------------------------------------

    result = {

        "project": "NEERAKSH",

        "reservoir": "Mettur / Stanley Reservoir",

        "government_observation": {
            "source":
                tn.get("source"),

            "water_level_ft":
                tn.get("water_level_ft"),

            "storage_mcft":
                tn.get("storage_mcft"),

            "inflow_cusecs":
                tn.get("inflow_cusecs"),

            "outflow_cusecs":
                tn.get("outflow_cusecs"),

            "fetched_at":
                tn.get("fetched_at")
        },

        "cwc_stage_storage": {
            "source":
                "CWC Mettur Stanley Reservoir "
                "Sedimentation Assessment 2020 - Table 3",

            "rows":
                len(cwc),

            "minimum_elevation_m":
                cwc[0]["elevation_m"],

            "maximum_elevation_m":
                cwc[-1]["elevation_m"],

            "maximum_storage_MCM":
                cwc[-1][
                    "cumulative_capacity_MCM"
                ]
        },

        "vertical_datum": {
            "verified":
                datum_verified,

            "status":
                "NOT_VERIFIED",

            "allow_direct_conversion":
                False
        },

        "execution_policy": {
            "allow_fabricated_values":
                False,

            "allow_unverified_datum_conversion":
                False,

            "allow_tn_storage_replacement":
                False,

            "allow_breach_simulation":
                False
        },

        "status":
            "WAITING_FOR_VERIFIED_VERTICAL_DATUM"
    }

    output = (
        OUTPUT_DIR
        /
        "mettur_reservoir_state_verification.json"
    )

    with output.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            result,
            f,
            indent=2
        )

    print()
    print("=" * 75)
    print("VERIFICATION OUTPUT")
    print("=" * 75)

    print(
        output
    )

    print()
    print(
        "STATUS: WAITING_FOR_VERIFIED_VERTICAL DATUM."
    )


if __name__ == "__main__":
    main()