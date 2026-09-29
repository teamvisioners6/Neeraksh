import json
from pathlib import Path
from datetime import datetime, timezone


BASE = Path(r"C:\NEERAKSH-1")

SCENARIO_DIR = (
    BASE /
    "simulations" /
    "scenarios" /
    "mettur"
)

OUTPUT = (
    SCENARIO_DIR /
    "mettur_concrete_gravity_scenarios.json"
)

SCENARIO_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# REAL METTUR DAM DATA
# ============================================================

DAM_LENGTH_M = 1615.44
DAM_HEIGHT_M = 65.53

CURRENT_LEVEL_FT = 83.07
CURRENT_STORAGE_MCFT = 45084.0
CURRENT_INFLOW_CUSECS = 4960.0
CURRENT_OUTFLOW_CUSECS = 12020.0


# ============================================================
# CONCRETE-GRAVITY BREACH GUIDANCE
# ============================================================
#
# These are NOT Mettur-specific measured failure parameters.
#
# They are engineering screening bounds documented by
# HEC-RAS for concrete gravity dams.
#
# Concrete Gravity:
#
#   Breach extent:
#       multiple monoliths
#       generally <= 0.5 * dam crest length
#
#   Side slopes:
#       vertical
#
#   Development time:
#       approximately 0.1 - 0.5 hr
#
# The software therefore creates scenarios rather than
# claiming one deterministic breach.
# ============================================================


BREACH_WIDTH_MIN_M = 0.10 * DAM_LENGTH_M
BREACH_WIDTH_BASE_M = 0.30 * DAM_LENGTH_M
BREACH_WIDTH_MAX_M = 0.50 * DAM_LENGTH_M

FORMATION_MIN_HR = 0.10
FORMATION_BASE_HR = 0.30
FORMATION_MAX_HR = 0.50


def scenario(
    scenario_id,
    description,
    breach_width_m,
    formation_time_hr
):

    return {

        "scenario_id":
            scenario_id,

        "dam":
        {
            "name":
                "Mettur Dam / Stanley Reservoir",

            "river":
                "Cauvery",

            "state":
                "Tamil Nadu",

            "dam_type":
                "Concrete Gravity",

            "dam_length_m":
                DAM_LENGTH_M,

            "dam_height_m":
                DAM_HEIGHT_M
        },

        "classification":
        {
            "type":
                "ENGINEERING_SCREENING_SCENARIO",

            "measured_mettur_breach_parameter":
                False,

            "prediction_of_actual_failure":
                False,

            "purpose":
                "Sensitivity analysis of potential "
                "concrete-gravity dam breach behaviour."
        },

        "failure":
        {
            "mechanism":
            {
                "value":
                    "STRUCTURAL_GRAVITY_DAM_BREACH",

                "source":
                    "HEC-RAS concrete gravity dam "
                    "breach guidance"
            },

            "breach_location":
            {
                "latitude":
                    None,

                "longitude":
                    None,

                "source":
                    "USER_SELECTED_ON_DAM_GEOMETRY"
            },

            "breach_width_m":
            {
                "value":
                    breach_width_m,

                "source":
                    "HEC-RAS concrete gravity screening "
                    "range",

                "measured":
                    False
            },

            "formation_time_hr":
            {
                "value":
                    formation_time_hr,

                "source":
                    "HEC-RAS concrete gravity screening "
                    "range",

                "measured":
                    False
            },

            "side_slope_h_to_v":
            {
                "value":
                    0.0,

                "source":
                    "HEC-RAS concrete gravity guidance",

                "interpretation":
                    "Vertical breach sides"
            }
        },

        "reservoir_initial_condition":
        {
            "level_ft":
            {
                "value":
                    CURRENT_LEVEL_FT,

                "source":
                    "Government of Tamil Nadu "
                    "reservoir observation",

                "observed":
                    True
            },

            "storage_mcft":
            {
                "value":
                    CURRENT_STORAGE_MCFT,

                "source":
                    "Government of Tamil Nadu "
                    "reservoir observation",

                "observed":
                    True
            },

            "inflow_cusecs":
            {
                "value":
                    CURRENT_INFLOW_CUSECS,

                "source":
                    "Government of Tamil Nadu "
                    "reservoir observation",

                "observed":
                    True
            },

            "outflow_cusecs":
            {
                "value":
                    CURRENT_OUTFLOW_CUSECS,

                "source":
                    "Government of Tamil Nadu "
                    "reservoir observation",

                "observed":
                    True
            }
        },

        "hydraulic_model":
        {
            "equations":
                "2D full shallow-water equations",

            "solver":
                "NEERAKSH_2D_HLL",

            "terrain":
                "CartoDEM 30m",

            "river_network":
                "HydroRIVERS",

            "simulation_status":
                "WAITING_FOR_BREACH_LOCATION"
        },

        "description":
            description
    }


scenarios = [

    scenario(
        "METTUR_CG_LOW",
        "Lower structural breach screening case.",
        BREACH_WIDTH_MIN_M,
        FORMATION_MIN_HR
    ),

    scenario(
        "METTUR_CG_BASE",
        "Mid-range structural breach screening case.",
        BREACH_WIDTH_BASE_M,
        FORMATION_BASE_HR
    ),

    scenario(
        "METTUR_CG_HIGH",
        "Upper structural breach screening case.",
        BREACH_WIDTH_MAX_M,
        FORMATION_MAX_HR
    )

]


output = {

    "project":
        "NEERAKSH",

    "dam":
        "Mettur Dam / Stanley Reservoir",

    "created_at":
        datetime.now(
            timezone.utc
        ).isoformat(),

    "methodology":
        "Concrete gravity dam screening scenarios",

    "important_notice":
        "These scenarios are engineering screening "
        "cases based on published concrete-gravity "
        "dam breach guidance. They are not measured "
        "Mettur failure parameters and do not predict "
        "that Mettur Dam will fail.",

    "dam_length_m":
        DAM_LENGTH_M,

    "dam_height_m":
        DAM_HEIGHT_M,

    "breach_width_range_m":
    {
        "minimum":
            BREACH_WIDTH_MIN_M,

        "base":
            BREACH_WIDTH_BASE_M,

        "maximum":
            BREACH_WIDTH_MAX_M
    },

    "formation_time_range_hr":
    {
        "minimum":
            FORMATION_MIN_HR,

        "base":
            FORMATION_BASE_HR,

        "maximum":
            FORMATION_MAX_HR
    },

    "scenarios":
        scenarios
}


with open(
    OUTPUT,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        output,
        f,
        indent=2
    )


print("=" * 70)
print("NEERAKSH METTUR CONCRETE-GRAVITY SCENARIOS")
print("=" * 70)

print()
print("Dam type: Concrete Gravity")
print("Dam length:", DAM_LENGTH_M, "m")
print("Dam height:", DAM_HEIGHT_M, "m")

print()
print("SCREENING WIDTH RANGE")
print(
    "Minimum:",
    BREACH_WIDTH_MIN_M,
    "m"
)
print(
    "Base:",
    BREACH_WIDTH_BASE_M,
    "m"
)
print(
    "Maximum:",
    BREACH_WIDTH_MAX_M,
    "m"
)

print()
print("FORMATION TIME RANGE")
print(
    "Minimum:",
    FORMATION_MIN_HR,
    "hr"
)
print(
    "Base:",
    FORMATION_BASE_HR,
    "hr"
)
print(
    "Maximum:",
    FORMATION_MAX_HR,
    "hr"
)

print()
print("Current observed reservoir:")
print("Level:", CURRENT_LEVEL_FT, "ft")
print("Storage:", CURRENT_STORAGE_MCFT, "M.Cft")
print("Inflow:", CURRENT_INFLOW_CUSECS, "cusecs")
print("Outflow:", CURRENT_OUTFLOW_CUSECS, "cusecs")

print()
print("IMPORTANT:")
print("Breach location is intentionally NOT invented.")
print("User must select/verify breach location.")

print()
print("Saved:")
print(OUTPUT)
