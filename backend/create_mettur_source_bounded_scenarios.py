from pathlib import Path
import json
from datetime import datetime, timezone


# ============================================================
# NEERAKSH
# SOURCE-BOUNDED METTUR DAM-BREAK SCENARIO GENERATOR
# ============================================================

BASE = Path(r"C:\NEERAKSH-1")

OUTPUT = (
    BASE
    / "simulations"
    / "scenarios"
    / "mettur"
    / "mettur_source_bounded_scenarios.json"
)

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# OFFICIAL METTUR REFERENCE DATA
# ============================================================

DAM = {
    "name": "Mettur Dam",
    "reservoir": "Stanley Reservoir",
    "river": "Cauvery",
    "state": "Tamil Nadu",
    "district": "Salem",

    "pic": "TN12HH0005",

    "latitude": 11.8030555556,
    "longitude": 77.8066666667,

    "height_m": 65.53,

    "frl_m": 240.79,
    "mwl_m": 242.62,

    "gross_storage_mcm": 2708.79,

    "source": {
        "organization":
            "National Water Data Portal / National Water Informatics Centre",

        "dataset":
            "Official Dam Dataset",

        "record":
            "TN12HH0005",

        "note":
            "Official dam reference point and published dam attributes."
    }
}


# ============================================================
# OBSERVED RESERVOIR STATE
# ============================================================

OBSERVED_STATE = {

    "source":
        "Government of Tamil Nadu Reservoir Portal",

    "status":
        "OBSERVED",

    "water_level_ft":
        83.07,

    "storage_mcft":
        45084.0,

    "inflow_cusecs":
        4960.0,

    "outflow_cusecs":
        12020.0,

    "fetched_at":
        "2026-09-25T00:39:17.243128+00:00",

    "important_note":
        "Observed reservoir values are not converted into a "
        "CWC hydraulic elevation because an independently verified "
        "vertical-datum transformation has not been established."
}


# ============================================================
# CWC RESERVOIR REFERENCE
# ============================================================

CWC_REFERENCE = {

    "organization":
        "Central Water Commission",

    "document":
        "Sedimentation Assessment of Mettur / Stanley Reservoir "
        "through Remote Sensing",

    "year":
        2020,

    "frl_m":
        240.79,

    "mddl_m":
        219.456,

    "dsl_m":
        204.216,

    "live_capacity_at_frl_mcm":
        2150.553085,

    "water_spread_at_frl_sqkm":
        136.80,

    "stage_storage_source":
        "CWC Table-3, SRS Survey 2019",

    "note":
        "Official CWC reservoir elevation-capacity reference."
}


# ============================================================
# ENGINEERING GUIDANCE
# ============================================================

ENGINEERING_GUIDANCE = {

    "dam_class":
        "Concrete / Masonry Gravity",

    "source":
        "USACE HEC-RAS Dam Breach Technical Reference",

    "breach_side_slope_h_to_v":
        {
            "value":
                0.0,

            "interpretation":
                "Vertical sides for concrete gravity screening",

            "status":
                "GUIDANCE",

            "not_mettur_measured_parameter":
                True
        },

    "formation_time_hr":
        {
            "minimum":
                0.1,

            "base_screening":
                0.3,

            "maximum":
                0.5,

            "status":
                "ENGINEERING_SCREENING_RANGE",

            "not_mettur_measured_parameter":
                True
        },

    "breach_width_fraction_of_crest":
        {
            "minimum":
                0.10,

            "base":
                0.30,

            "maximum":
                0.50,

            "status":
                "ENGINEERING_SCREENING_RANGE",

            "not_mettur_measured_parameter":
                True
        },

    "critical_note":
        "These are general concrete-gravity dam-breach screening "
        "guidelines. They are NOT measured or officially assigned "
        "Mettur breach parameters."
}


# ============================================================
# SCENARIO DEFINITIONS
# ============================================================

SCENARIOS = [

    {
        "id":
            "METTUR_SCREENING_LOW",

        "purpose":
            "Lower-bound engineering sensitivity case",

        "breach_width_fraction":
            0.10,

        "formation_time_hr":
            0.5,

        "side_slope_h_to_v":
            0.0
    },

    {
        "id":
            "METTUR_SCREENING_BASE",

        "purpose":
            "Central engineering sensitivity case",

        "breach_width_fraction":
            0.30,

        "formation_time_hr":
            0.3,

        "side_slope_h_to_v":
            0.0
    },

    {
        "id":
            "METTUR_SCREENING_HIGH",

        "purpose":
            "Upper-bound engineering sensitivity case",

        "breach_width_fraction":
            0.50,

        "formation_time_hr":
            0.1,

        "side_slope_h_to_v":
            0.0
    }
]


# ============================================================
# BUILD SCENARIOS
# ============================================================

output_scenarios = []

for item in SCENARIOS:

    width_fraction = float(
        item["breach_width_fraction"]
    )

    width_m = (
        DAM["height_m"] * 0.0
    )

    # Dam crest length is deliberately NOT taken from the
    # NWDP dm_length field because that record reports zero.
    #
    # CWC National Register gives approximately 1615.4 m.
    crest_length_m = 1615.4

    width_m = (
        crest_length_m
        * width_fraction
    )

    scenario = {

        "scenario_id":
            item["id"],

        "status":
            "ENGINEERING_SCREENING_ONLY",

        "simulation_allowed":
            False,

        "purpose":
            item["purpose"],

        "dam":
            DAM,

        "observed_reservoir_state":
            OBSERVED_STATE,

        "cwc_reference":
            CWC_REFERENCE,

        "failure":
            {

                "mechanism":
                    None,

                "mechanism_status":
                    "NOT_VERIFIED_FOR_METTUR",

                "breach_location":
                    {

                        "latitude":
                            None,

                        "longitude":
                            None,

                        "station_m":
                            None,

                        "status":
                            "NOT_PROVIDED"
                    },

                "breach_invert_elevation_m":
                    None,

                "crest_elevation_m":
                    None,

                "breach_width_m":
                    {

                        "screening_value":
                            round(
                                width_m,
                                3
                            ),

                        "fraction_of_cwc_crest_length":
                            width_fraction,

                        "status":
                            "SCREENING_VALUE_ONLY"
                    },

                "formation_time_hr":
                    {

                        "screening_value":
                            item[
                                "formation_time_hr"
                            ],

                        "status":
                            "SCREENING_VALUE_ONLY"
                    },

                "side_slope_h_to_v":
                    {

                        "screening_value":
                            item[
                                "side_slope_h_to_v"
                            ],

                        "status":
                            "SCREENING_VALUE_ONLY"
                    }
            },

        "hydraulic_initial_condition":
            {

                "water_surface_elevation_m":
                    None,

                "status":
                    "NOT_VERIFIED",

                "reason":
                    "Government gauge value has not been "
                    "converted to a verified CWC hydraulic "
                    "vertical datum."
            },

        "breach_hydrograph":
            {

                "status":
                    "NOT_GENERATED",

                "reason":
                    "No verified Mettur breach location, "
                    "invert elevation and failure geometry "
                    "are available."
            },

        "solver":
            {

                "name":
                    "NEERAKSH_2D_HLL",

                "status":
                    "READY_BUT_BLOCKED",

                "execution_allowed":
                    False
            },

        "provenance":
            {

                "dam_reference":
                    "NWDP/NWIC official dam dataset",

                "reservoir_observation":
                    "Government of Tamil Nadu reservoir portal",

                "reservoir_geometry":
                    "Government reservoir GIS dataset",

                "dem":
                    "ISRO/Bhoonidhi CartoDEM 30 m",

                "river_network":
                    "HydroRIVERS",

                "stage_storage":
                    "CWC Mettur sedimentation assessment, Table-3",

                "breach_guidance":
                    "USACE HEC-RAS concrete-gravity dam-breach guidance"
            },

        "fabricated_values":
            False,

        "important":
            "Screening values are not represented as actual "
            "Mettur failure parameters."
    }

    output_scenarios.append(
        scenario
    )


# ============================================================
# FINAL DOCUMENT
# ============================================================

document = {

    "project":
        "NEERAKSH",

    "dataset":
        "Mettur Dam / Stanley Reservoir",

    "created_at":
        datetime.now(
            timezone.utc
        ).isoformat(),

    "status":
        "SOURCE_BOUNDED_ENGINEERING_SCENARIOS",

    "execution_policy":
        {

            "allow_fabricated_values":
                False,

            "allow_unverified_breach_location":
                False,

            "allow_unverified_hydraulic_initial_level":
                False,

            "allow_screening_values_as_measured_values":
                False,

            "require_parameter_provenance":
                True
        },

    "dam":
        DAM,

    "observed_state":
        OBSERVED_STATE,

    "cwc_reference":
        CWC_REFERENCE,

    "engineering_guidance":
        ENGINEERING_GUIDANCE,

    "scenarios":
        output_scenarios,

    "next_required_inputs":
        [

            "Verified Mettur breach location",

            "Verified breach station / chainage",

            "Verified breach invert elevation",

            "Verified crest elevation at selected section",

            "Dam-specific or approved engineering breach width",

            "Dam-specific or approved formation time",

            "Verified hydraulic initial water-surface elevation",

            "Verified breach hydrograph"
        ]
}


# ============================================================
# SAVE
# ============================================================

with open(
    OUTPUT,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        document,
        f,
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# REPORT
# ============================================================

print()
print("=" * 70)
print(
    "NEERAKSH — METTUR SOURCE-BOUNDED SCENARIOS"
)
print("=" * 70)

print()
print(
    "Dam:",
    DAM["name"]
)

print(
    "PIC:",
    DAM["pic"]
)

print(
    "Dam height:",
    DAM["height_m"],
    "m"
)

print(
    "CWC crest length:",
    crest_length_m,
    "m"
)

print()
print(
    "SCENARIOS CREATED"
)

print("-" * 50)

for scenario in output_scenarios:

    failure = scenario["failure"]

    print(
        scenario["scenario_id"]
    )

    print(
        "  Width screening:",
        failure[
            "breach_width_m"
        ]["screening_value"],
        "m"
    )

    print(
        "  Formation screening:",
        failure[
            "formation_time_hr"
        ]["screening_value"],
        "hr"
    )

    print(
        "  Breach location: NOT PROVIDED"
    )

    print(
        "  Hydraulic initial level: NOT VERIFIED"
    )

    print(
        "  Simulation allowed: FALSE"
    )

print()
print(
    "FABRICATED VALUES: FALSE"
)

print(
    "STATUS: SOURCE-BOUNDED SCENARIOS CREATED"
)

print()
print(
    "Saved:"
)

print(
    OUTPUT
)