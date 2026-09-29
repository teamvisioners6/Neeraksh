import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(r"C:\NEERAKSH-1")

SCENARIO = (
    BASE /
    "simulations" /
    "scenarios" /
    "mettur" /
    "mettur_engineering_scenario_template.json"
)

OUTPUT = (
    BASE /
    "simulations" /
    "outputs" /
    "mettur"
)

OUTPUT.mkdir(parents=True, exist_ok=True)

config = {
    "project": "NEERAKSH",

    "model": {
        "name": "Mettur 2D Dam-Break Hydraulic Model",
        "equations": "2D shallow-water equations",

        "status": "INPUT_VALIDATION_ONLY",

        "solver_backend": {
            "name": "NEERAKSH_2D",
            "type": "finite_volume",
            "status": "IMPLEMENTATION_NEXT"
        },

        "delft3d": {
            "required": True,
            "status": "INTEGRATION_PENDING",
            "executed": False
        },

        "sph": {
            "required": True,
            "status": "INTEGRATION_PENDING",
            "executed": False
        }
    },

    "inputs": {
        "scenario_file": str(SCENARIO),

        "dem": (
            str(
                BASE /
                "simulations" /
                "inputs" /
                "mettur" /
                "mettur_hydraulic_domain_dem_30m.tif"
            )
        ),

        "river_network": (
            str(
                BASE /
                "simulations" /
                "inputs" /
                "mettur" /
                "mettur_main_hydrorivers.gpkg"
            )
        ),

        "hydraulic_domain": (
            str(
                BASE /
                "simulations" /
                "inputs" /
                "mettur" /
                "mettur_hydraulic_domain.gpkg"
            )
        )
    },

    "required_scenario_parameters": [
        "failure.mechanism.value",
        "failure.breach_location.latitude",
        "failure.breach_location.longitude",
        "failure.breach_width_m.value",
        "failure.formation_time_hr.value",
        "failure.side_slope_h_to_v.value",
        "reservoir_initial_condition.level_ft.value"
    ],

    "numerical_parameters": {
        "time_step_seconds": None,
        "simulation_duration_hours": None,

        "manning_n": None,

        "grid_resolution_m": 30,

        "wetting_depth_threshold_m": 0.01
    },

    "outputs": {
        "water_depth": "water_depth_max.tif",
        "water_surface": "water_surface_elevation_max.tif",
        "velocity": "velocity_max.tif",
        "arrival_time": "arrival_time.tif",
        "flood_extent_shp": "maximum_inundation.shp",
        "flood_extent_kml": "maximum_inundation.kml"
    },

    "validation": {
        "missing_parameters_block_execution": True,
        "fabricated_values_allowed": False,
        "provenance_required": True
    },

    "created_at":
        datetime.now(timezone.utc).isoformat()
}

output = OUTPUT / "mettur_hydraulic_solver_config.json"

with open(output, "w", encoding="utf-8") as f:
    json.dump(config, f, indent=2)

print("=" * 70)
print("NEERAKSH - METTUR HYDRAULIC SOLVER CONFIGURATION")
print("=" * 70)

print("\nINPUTS")
print("-" * 50)

for key, value in config["inputs"].items():
    print(key + ":")
    print(value)

print("\nREQUIRED BREACH PARAMETERS")
print("-" * 50)

for parameter in config["required_scenario_parameters"]:
    print("-", parameter)

print("\nSOLVER")
print("-" * 50)
print("Equation system: 2D shallow-water equations")
print("Grid resolution: 30 m")
print("Backend: NEERAKSH_2D")
print("Implementation: NEXT")

print("\nDelft3D:")
print("Integration pending")

print("\nSPH:")
print("Integration pending")

print("\nExecution policy:")
print("Missing scenario parameters = simulation blocked")
print("Fabricated parameters = prohibited")
print("Parameter provenance = required")

print("\nSaved:")
print(output)

print("\n" + "=" * 70)
print("HYDRAULIC SOLVER CONFIGURATION CREATED")
print("=" * 70)
