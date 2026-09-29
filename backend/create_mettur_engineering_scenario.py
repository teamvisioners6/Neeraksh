import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(r"C:\NEERAKSH-1")

OUT = (
    BASE /
    "simulations" /
    "scenarios" /
    "mettur" /
    "mettur_engineering_scenario_template.json"
)

scenario = {
    "project": "NEERAKSH",

    "scenario_id": "METTUR_BREACH_ENGINEERING_001",

    "dam": {
        "name": "Mettur Dam / Stanley Reservoir",
        "river": "Cauvery",
        "state": "Tamil Nadu",

        "latitude": 11.8030556,
        "longitude": 77.8066667
    },

    "scenario_type": "ENGINEERING_INPUT",

    "status": "NOT_READY_FOR_SIMULATION",

    "failure": {

        "mechanism": {
            "value": None,
            "allowed": [
                "overtopping",
                "piping",
                "structural_failure",
                "user_defined"
            ],
            "source": None
        },

        "breach_location": {
            "latitude": None,
            "longitude": None,
            "chainage_m": None,
            "source": None
        },

        "breach_width_m": {
            "value": None,
            "source": None,
            "provenance": None
        },

        "formation_time_hr": {
            "value": None,
            "source": None,
            "provenance": None
        },

        "side_slope_h_to_v": {
            "value": None,
            "source": None,
            "provenance": None
        }
    },

    "reservoir_initial_condition": {

        "level_ft": {
            "value": None,
            "source": None,
            "observed": False
        },

        "storage_mcft": {
            "value": None,
            "source": None,
            "observed": False
        },

        "inflow_cusecs": {
            "value": None,
            "source": None,
            "observed": False
        },

        "outflow_cusecs": {
            "value": None,
            "source": None,
            "observed": False
        }
    },

    "hydraulic_model": {

        "terrain": (
            "C:\\NEERAKSH-1\\simulations\\inputs\\mettur"
            "\\mettur_hydraulic_domain_dem_30m.tif"
        ),

        "river_network": (
            "C:\\NEERAKSH-1\\simulations\\inputs\\mettur"
            "\\mettur_main_hydrorivers.gpkg"
        ),

        "hydraulic_domain": (
            "C:\\NEERAKSH-1\\simulations\\inputs\\mettur"
            "\\mettur_hydraulic_domain.gpkg"
        ),

        "target_equations": [
            "2D shallow-water equations"
        ],

        "delft3d": {
            "required_by_problem_statement": True,
            "status": "INTEGRATION_PENDING",
            "executed": False
        },

        "sph": {
            "required_by_problem_statement": True,
            "status": "INTEGRATION_PENDING",
            "executed": False
        }
    },

    "outputs": {
        "required": [
            "breach_outflow_hydrograph",
            "water_depth",
            "water_surface_elevation",
            "velocity",
            "arrival_time",
            "maximum_inundation_extent",
            "shp",
            "kml"
        ]
    },

    "validation": {
        "all_parameters_require_provenance": True,
        "fabricated_values_allowed": False,
        "simulation_allowed_when_parameters_missing": False
    },

    "created_at":
        datetime.now(timezone.utc).isoformat()
}

OUT.parent.mkdir(parents=True, exist_ok=True)

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(scenario, f, indent=2)

print("=" * 70)
print("NEERAKSH - METTUR ENGINEERING SCENARIO")
print("=" * 70)

print("\nScenario:", scenario["scenario_id"])
print("Dam:", scenario["dam"]["name"])
print("River:", scenario["dam"]["river"])

print("\nFailure parameters:")
print("Mechanism: NOT PROVIDED")
print("Breach location: NOT PROVIDED")
print("Breach width: NOT PROVIDED")
print("Formation time: NOT PROVIDED")
print("Side slope: NOT PROVIDED")

print("\nSimulation status:")
print("NOT READY")
print("Reason: engineering breach parameters require provenance.")

print("\nTerrain:")
print("READY")

print("\nHydroRIVERS:")
print("READY")

print("\nLive reservoir data:")
print("READY")

print("\nSaved:")
print(OUT)

print("\n" + "=" * 70)
print("METTUR ENGINEERING SCENARIO TEMPLATE READY")
print("=" * 70)
