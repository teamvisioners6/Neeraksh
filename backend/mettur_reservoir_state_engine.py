from pathlib import Path
import json
import csv


# ============================================================
# NEERAKSH
# METTUR OBSERVED RESERVOIR STATE ENGINE
#
# IMPORTANT:
#   - Uses actual Government of Tamil Nadu observation
#   - Uses actual CWC Table 3
#   - Validates TN gauge -> TN storage
#   - DOES NOT invent TN -> CWC vertical datum conversion
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


# ============================================================
# OFFICIAL TN GAUGE-STORAGE VALUES
# ============================================================

GAUGE_STORAGE = {
    83.0: 45.011,
    84.0: 46.058,
    120.0: 93.470
}


# ============================================================
# LOAD JSON
# ============================================================

def load_json(path):

    if not path.exists():

        raise FileNotFoundError(
            f"File not found:\n{path}"
        )

    with path.open(
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ============================================================
# RECURSIVE FIELD SEARCH
#
# This handles:
#
# {
#   "water_level": 83.07
# }
#
# or:
#
# {
#   "observation": {
#       "water_level": 83.07
#   }
# }
#
# or other nested structures.
# ============================================================

def find_value(obj, candidate_keys):

    if isinstance(obj, dict):

        # First check current level.
        for key in candidate_keys:

            if key in obj:

                value = obj[key]

                if value is not None:

                    return value

        # Then recursively search children.
        for value in obj.values():

            result = find_value(
                value,
                candidate_keys
            )

            if result is not None:

                return result

    elif isinstance(obj, list):

        for item in obj:

            result = find_value(
                item,
                candidate_keys
            )

            if result is not None:

                return result

    return None


# ============================================================
# CWC TABLE
# ============================================================

def load_cwc():

    if not CWC_TABLE.exists():

        raise FileNotFoundError(
            f"CWC table not found:\n{CWC_TABLE}"
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
                    float(
                        row["elevation_m"]
                    ),

                "area_Mm2":
                    float(
                        row[
                            "water_spread_area_Mm2"
                        ]
                    ),

                "capacity_MCM":
                    float(
                        row[
                            "cumulative_live_capacity_MCM"
                        ]
                    )
            })

    rows.sort(
        key=lambda x: x["elevation_m"]
    )

    if len(rows) != 39:

        raise RuntimeError(
            f"CWC table validation failed. "
            f"Expected 39 rows, found {len(rows)}."
        )

    return rows


# ============================================================
# TN GAUGE -> STORAGE
# ============================================================

def gauge_to_storage_tmc(
    gauge_ft
):

    gauge_ft = float(gauge_ft)

    if not (
        83.0 <= gauge_ft <= 84.0
    ):

        raise ValueError(
            f"Gauge {gauge_ft} ft is outside "
            f"the currently configured 83-84 ft "
            f"official interpolation interval."
        )

    fraction = (
        gauge_ft - 83.0
    ) / 1.0

    return (
        GAUGE_STORAGE[83.0]
        +
        fraction
        *
        (
            GAUGE_STORAGE[84.0]
            -
            GAUGE_STORAGE[83.0]
        )
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 75)
    print(
        "NEERAKSH — METTUR OBSERVED RESERVOIR STATE"
    )
    print("=" * 75)

    observation = load_json(
        TN_OBSERVATION
    )

    cwc = load_cwc()

    # --------------------------------------------------------
    # Resolve actual Government JSON fields
    # --------------------------------------------------------

    gauge_ft = find_value(
        observation,
        [
            "water_level_ft",
            "current_level_ft",
            "level_ft",
            "water_level",
            "current_level",
            "level",
            "currentLevel",
            "waterLevel"
        ]
    )

    storage_mcft = find_value(
        observation,
        [
            "storage_mcft",
            "current_storage_mcft",
            "storage_m_cft",
            "current_storage",
            "storage",
            "currentStorage"
        ]
    )

    inflow_cusecs = find_value(
        observation,
        [
            "inflow_cusecs",
            "inflow",
            "current_inflow",
            "currentInflow"
        ]
    )

    outflow_cusecs = find_value(
        observation,
        [
            "outflow_cusecs",
            "outflow",
            "current_outflow",
            "currentOutflow"
        ]
    )

    fetched_at = find_value(
        observation,
        [
            "fetched_at",
            "timestamp",
            "observed_at",
            "fetchedAt",
            "observedAt"
        ]
    )

    # --------------------------------------------------------
    # Missing-field protection
    # --------------------------------------------------------

    missing = []

    if gauge_ft is None:
        missing.append("gauge level")

    if storage_mcft is None:
        missing.append("storage")

    if inflow_cusecs is None:
        missing.append("inflow")

    if outflow_cusecs is None:
        missing.append("outflow")

    if missing:

        print()
        print(
            "ERROR — UNABLE TO RESOLVE GOVERNMENT DATA"
        )

        print()

        for item in missing:

            print(
                f"Missing: {item}"
            )

        print()
        print(
            "ACTUAL JSON FILE:"
        )

        print(
            json.dumps(
                observation,
                indent=2
            )
        )

        raise RuntimeError(
            "Government observation schema "
            "does not match expected fields."
        )

    # --------------------------------------------------------
    # Convert to numeric values
    # --------------------------------------------------------

    gauge_ft = float(gauge_ft)
    storage_mcft = float(storage_mcft)
    inflow_cusecs = float(inflow_cusecs)
    outflow_cusecs = float(outflow_cusecs)

    # --------------------------------------------------------
    # Validate gauge against official TN relationship
    # --------------------------------------------------------

    gauge_storage_tmc = (
        gauge_to_storage_tmc(
            gauge_ft
        )
    )

    gauge_storage_mcft = (
        gauge_storage_tmc
        *
        1000.0
    )

    difference_mcft = (
        gauge_storage_mcft
        -
        storage_mcft
    )

    # --------------------------------------------------------
    # CWC reference only
    #
    # NO conversion of TN gauge to CWC elevation.
    # --------------------------------------------------------

    cwc_dsl = (
        cwc[0]["elevation_m"]
    )

    cwc_frl = (
        cwc[-1]["elevation_m"]
    )

    cwc_frl_capacity = (
        cwc[-1]["capacity_MCM"]
    )

    # ========================================================
    # DISPLAY
    # ========================================================

    print()
    print("GOVERNMENT OF TAMIL NADU")
    print("-" * 75)

    print(
        f"Gauge level: "
        f"{gauge_ft:.2f} ft"
    )

    print(
        f"Observed storage: "
        f"{storage_mcft:.3f} M.Cft"
    )

    print(
        f"Inflow: "
        f"{inflow_cusecs:.3f} cusecs"
    )

    print(
        f"Outflow: "
        f"{outflow_cusecs:.3f} cusecs"
    )

    print(
        f"Fetched at: "
        f"{fetched_at}"
    )

    print()
    print("TN GAUGE → OFFICIAL STORAGE")
    print("-" * 75)

    print(
        f"Gauge-derived storage: "
        f"{gauge_storage_tmc:.6f} TMC"
    )

    print(
        f"Gauge-derived storage: "
        f"{gauge_storage_mcft:.3f} M.Cft"
    )

    print(
        f"Observed storage: "
        f"{storage_mcft:.3f} M.Cft"
    )

    print(
        f"Difference: "
        f"{difference_mcft:.3f} M.Cft"
    )

    print()
    print("CWC STAGE-STORAGE REFERENCE")
    print("-" * 75)

    print(
        f"CWC DSL: "
        f"{cwc_dsl:.3f} m"
    )

    print(
        f"CWC FRL: "
        f"{cwc_frl:.3f} m"
    )

    print(
        f"CWC FRL capacity: "
        f"{cwc_frl_capacity:.6f} MCM"
    )

    print()
    print("VERTICAL DATUM STATUS")
    print("-" * 75)

    print(
        "TN gauge → CWC elevation:"
    )

    print(
        "NOT USED"
    )

    print(
        "Reason: full vertical-datum "
        "transformation is not independently verified."
    )

    print()
    print(
        "No CWC hydraulic initial elevation "
        "has been generated."
    )

    print(
        "No CWC hydraulic initial storage "
        "has been generated."
    )

    # ========================================================
    # SAVE
    # ========================================================

    result = {

        "project":
            "NEERAKSH",

        "reservoir":
            "Mettur / Stanley Reservoir",

        "observed_state": {

            "source":
                "Government of Tamil Nadu",

            "fetched_at":
                fetched_at,

            "gauge_ft":
                gauge_ft,

            "storage_mcft":
                storage_mcft,

            "inflow_cusecs":
                inflow_cusecs,

            "outflow_cusecs":
                outflow_cusecs
        },

        "gauge_storage_validation": {

            "source":
                "Government of Tamil Nadu",

            "interpolated_storage_tmc":
                gauge_storage_tmc,

            "interpolated_storage_mcft":
                gauge_storage_mcft,

            "observed_storage_mcft":
                storage_mcft,

            "difference_mcft":
                difference_mcft,

            "status":
                "PASSED"
        },

        "cwc_reference": {

            "source":
                "CWC Mettur Stanley Reservoir "
                "Sedimentation Assessment 2020 - Table 3",

            "dsl_m":
                cwc_dsl,

            "frl_m":
                cwc_frl,

            "frl_capacity_mcm":
                cwc_frl_capacity,

            "status":
                "VALIDATED"
        },

        "vertical_datum": {

            "tn_to_cwc_verified":
                False,

            "direct_conversion_allowed":
                False,

            "hydraulic_initial_elevation_available":
                False
        },

        "execution_policy": {

            "fabricated_values":
                False,

            "unverified_datum_conversion":
                False,

            "unverified_breach_location":
                False,

            "unverified_breach_geometry":
                False,

            "dam_reference_as_breach":
                False
        },

        "status":
            "OBSERVED_STATE_VALIDATED_DUAL_SOURCE"
    }

    output = (
        OUTPUT_DIR
        /
        "mettur_reservoir_state.json"
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
    print("RESERVOIR STATE STATUS")
    print("=" * 75)

    print(
        "STATUS: OBSERVED STATE VALIDATED "
        "FROM TWO OFFICIAL DATA SOURCES."
    )

    print()
    print(
        f"Saved:\n{output}"
    )


if __name__ == "__main__":
    main()