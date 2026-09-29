import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(r"C:\NEERAKSH-1")
OUT = BASE / "simulations" / "scenarios" / "mettur"
OUT.mkdir(parents=True, exist_ok=True)

# ============================================================
# NEERAKSH - METTUR REAL-DATA SCENARIO DEFINITION
# ============================================================

scenario = {
    "project": "NEERAKSH",

    "dam": {
        "name": "Mettur Dam / Stanley Reservoir",
        "river": "Cauvery",
        "state": "Tamil Nadu",
        "latitude": 11.8030556,
        "longitude": 77.8066667,

        "height_m": 65.23,
        "length_m": 1615.40,

        "gross_storage_bcm": 2.71,
        "effective_storage_bcm": 2.65,

        "reservoir_area_km2": 153.46,

        "designed_spillway_capacity_m3s": 12904.8,

        "full_reservoir_level_m": 240.790
    },

    "terrain": {
        "dem": str(
            BASE /
            "simulations" /
            "inputs" /
            "mettur" /
            "mettur_hydraulic_domain_dem_30m.tif"
        ),

        "dem_resolution_m": 30,

        "hydrorivers": str(
            BASE /
            "simulations" /
            "inputs" /
            "mettur" /
            "mettur_main_hydrorivers.gpkg"
        ),

        "hydraulic_domain": str(
            BASE /
            "simulations" /
            "inputs" /
            "mettur" /
            "mettur_hydraulic_domain.gpkg"
        )
    },

    "observed_reservoir_state": {
        "source": "Government of Tamil Nadu reservoir portal",
        "status": "observed",

        "water_level_ft": 83.07,
        "storage_mcft": 45084.0,
        "inflow_cusecs": 4960.0,
        "outflow_cusecs": 12020.0,

        "fetched_at": "2026-09-25T00:39:17.243128+00:00"
    },

    "failure_scenario": {

        "scenario_id": "METTUR_USER_DEFINED_BREACH_001",

        "status": "PARAMETERS_REQUIRED",

        "failure_type": None,

        "breach_location": {
            "status": "NOT_SPECIFIED",
            "latitude": None,
            "longitude": None,
            "source": None
        },

        "initial_reservoir_level_m": None,

        "initial_reservoir_storage_m3": None,

        "breach_width_m": None,

        "breach_formation_time_hr": None,

        "breach_side_slope_h_to_v": None,

        "peak_breach_discharge_m3s": None,

        "failure_start_time": None,

        "parameter_provenance": {
            "breach_width": None,
            "formation_time": None,
            "side_slope": None,
            "peak_discharge": None
        }
    },

    "solver": {
        "target": "2D shallow-water hydraulic simulation",

        "required_inputs": [
            "terrain DEM",
            "river network",
            "breach geometry",
            "reservoir level/storage",
            "breach hydrograph",
            "roughness parameters",
            "boundary conditions"
        ],

        "delft3d": {
            "status": "INTEGRATION_PENDING",
            "executed": False
        },

        "sph": {
            "status": "INTEGRATION_PENDING",
            "executed": False
        }
    },

    "outputs": {
        "required": [
            "water_depth_m",
            "water_surface_elevation_m",
            "velocity_mps",
            "arrival_time_min",
            "maximum_inundation_extent",
            "SHP",
            "KML"
        ]
    },

    "provenance": {
        "nrld_source": "Central Water Commission - National Register of Large Dams",
        "reservoir_source": "Government of Tamil Nadu",
        "dem_source": "Bhoonidhi / ISRO CartoDEM",
        "river_source": "HydroSHEDS HydroRIVERS",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
}

output = OUT / "mettur_scenario_definition.json"

with open(output, "w", encoding="utf-8") as f:
    json.dump(
        scenario,
        f,
        indent=2
    )

print("=" * 70)
print("NEERAKSH - METTUR SCENARIO DEFINITION")
print("=" * 70)

print("\nCreated:")
print(output)

print("\nREAL DAM PARAMETERS")
print("-" * 50)

for key, value in scenario["dam"].items():
    print(f"{key}: {value}")

print("\nOBSERVED RESERVOIR STATE")
print("-" * 50)

for key, value in scenario["observed_reservoir_state"].items():
    print(f"{key}: {value}")

print("\nFAILURE PARAMETERS")
print("-" * 50)

print("Failure type: NOT SPECIFIED")
print("Breach width: NOT AVAILABLE")
print("Formation time: NOT AVAILABLE")
print("Peak discharge: NOT AVAILABLE")
print("Breach location: NOT AVAILABLE")

print("\nSTATUS")
print("-" * 50)
print("Terrain: READY")
print("HydroRIVERS: READY")
print("Reservoir observation: READY")
print("Dam inventory: READY")
print("Breach parameters: REQUIRED")
print("Hydraulic simulation: WAITING FOR SCENARIO")

print("\n" + "=" * 70)
print("SCENARIO FOUNDATION CREATED")
print("=" * 70)
