import json
from pathlib import Path

import geopandas as gpd
import rasterio
import numpy as np


# ============================================================
# NEERAKSH — METTUR BREACH → 2D SOLVER INTERFACE
# ============================================================

BASE = Path(r"C:\NEERAKSH-1")

BREACH_SOURCE = (
    BASE
    / "simulations"
    / "inputs"
    / "mettur"
    / "breach_source_definition.json"
)

DAM_REFERENCE = (
    BASE
    / "gis"
    / "processed"
    / "mettur"
    / "mettur_official_dam_reference.geojson"
)

DEM_FILE = (
    BASE
    / "simulations"
    / "inputs"
    / "mettur"
    / "mettur_hydraulic_domain_dem_30m.tif"
)

OUTPUT_DIR = (
    BASE
    / "simulations"
    / "inputs"
    / "mettur"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "mettur_breach_solver_interface.json"
)


# ============================================================
# JSON
# ============================================================

def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )


# ============================================================
# HYPOTHETICAL SCENARIO VALIDATION
# ============================================================

def validate_hypothetical_breach(breach):
    """
    Validates a USER-SUPPLIED hypothetical breach scenario.

    This does NOT verify that the breach parameters represent
    an actual Mettur Dam failure location or engineering design.
    """

    required = [
        "latitude",
        "longitude",
        "station_m",
        "invert_elevation_m",
        "crest_elevation_m",
        "width_m",
        "formation_time_hr"
    ]

    missing = []

    for key in required:
        if breach.get(key) is None:
            missing.append(key)

    if missing:
        return False, {
            "status": "BLOCKED",
            "missing_parameters": missing
        }

    numeric_fields = required + ["side_slope_h_to_v"]

    for key in numeric_fields:
        if key not in breach:
            if key == "side_slope_h_to_v":
                continue

            return False, {
                "status": "BLOCKED",
                "reason": f"Missing parameter: {key}"
            }

        try:
            value = float(breach[key])
        except Exception:
            return False, {
                "status": "BLOCKED",
                "reason": f"Invalid numeric value: {key}"
            }

        if not np.isfinite(value):
            return False, {
                "status": "BLOCKED",
                "reason": f"Non-finite value: {key}"
            }

    if float(breach["width_m"]) <= 0:
        return False, {
            "status": "BLOCKED",
            "reason": "Breach width must be greater than zero."
        }

    if float(breach["formation_time_hr"]) <= 0:
        return False, {
            "status": "BLOCKED",
            "reason": "Formation time must be greater than zero."
        }

    if float(breach["crest_elevation_m"]) <= float(
        breach["invert_elevation_m"]
    ):
        return False, {
            "status": "BLOCKED",
            "reason": "Breach invert must be below crest elevation."
        }

    if not -90 <= float(breach["latitude"]) <= 90:
        return False, {
            "status": "BLOCKED",
            "reason": "Invalid latitude."
        }

    if not -180 <= float(breach["longitude"]) <= 180:
        return False, {
            "status": "BLOCKED",
            "reason": "Invalid longitude."
        }

    if "side_slope_h_to_v" not in breach:
        breach["side_slope_h_to_v"] = 1.0

    return True, {
        "status": "READY",
        "mode": "HYPOTHETICAL_USER_SUPPLIED",
        "fabricated_values_used": False,
        "engineering_verification": False
    }


# ============================================================
# MAIN
# ============================================================

def validate():

    print("=" * 70)
    print("NEERAKSH — BREACH → 2D SOLVER INTERFACE")
    print("=" * 70)

    # --------------------------------------------------------
    # Official dam reference
    # --------------------------------------------------------

    if not DAM_REFERENCE.exists():
        raise FileNotFoundError(
            f"Dam reference missing:\n{DAM_REFERENCE}"
        )

    dam = gpd.read_file(DAM_REFERENCE)

    if len(dam) != 1:
        raise RuntimeError(
            "Expected exactly one official Mettur dam reference."
        )

    geometry = dam.geometry.iloc[0]

    if geometry.geom_type != "Point":
        raise RuntimeError(
            "Official dam reference must be a Point."
        )

    dam_lon = float(geometry.x)
    dam_lat = float(geometry.y)

    print()
    print("OFFICIAL DAM REFERENCE")
    print("-" * 50)
    print("PIC:", dam["PIC"].iloc[0])
    print("Dam:", dam["dm_name"].iloc[0])
    print("Latitude:", dam_lat)
    print("Longitude:", dam_lon)

    # --------------------------------------------------------
    # DEM
    # --------------------------------------------------------

    if not DEM_FILE.exists():
        raise FileNotFoundError(
            f"Hydraulic DEM missing:\n{DEM_FILE}"
        )

    with rasterio.open(DEM_FILE) as src:

        rows = src.height
        cols = src.width
        transform = src.transform
        crs = src.crs
        bounds = src.bounds

    print()
    print("HYDRAULIC TERRAIN")
    print("-" * 50)
    print("CRS:", crs)
    print("Rows:", rows)
    print("Columns:", cols)
    print("Resolution:", abs(transform.a), abs(transform.e))
    print("Bounds:", bounds)

    # --------------------------------------------------------
    # Breach source
    # --------------------------------------------------------

    if not BREACH_SOURCE.exists():
        raise FileNotFoundError(
            f"Breach source missing:\n{BREACH_SOURCE}"
        )

    breach_document = load_json(BREACH_SOURCE)

    breach = breach_document.get(
        "breach",
        {}
    )

    # --------------------------------------------------------
    # Check scenario mode
    # --------------------------------------------------------

    scenario_mode = breach_document.get(
        "scenario_mode",
        "VERIFIED_ENGINEERING"
    )

    print()
    print("SCENARIO MODE")
    print("-" * 50)
    print("Mode:", scenario_mode)

    # ========================================================
    # HYPOTHETICAL MODE
    # ========================================================

    if scenario_mode == "HYPOTHETICAL_USER_SUPPLIED":

        print()
        print("HYPOTHETICAL SCENARIO")
        print("-" * 50)

        valid, validation = validate_hypothetical_breach(
            breach
        )

        if not valid:

            print("STATUS: BLOCKED")

            if "missing_parameters" in validation:
                for item in validation["missing_parameters"]:
                    print("Missing:", item)

            else:
                print(
                    "Reason:",
                    validation.get("reason")
                )

            result = {
                "status": "BLOCKED",
                "scenario_mode": "HYPOTHETICAL_USER_SUPPLIED",
                "simulation_allowed": False,
                "engineering_verification": False,
                "fabricated_values_used": False,
                "reason": validation
            }

            save_json(
                OUTPUT_FILE,
                result
            )

            print()
            print("Saved:")
            print(OUTPUT_FILE)

            return

        breach_lat = float(
            breach["latitude"]
        )

        breach_lon = float(
            breach["longitude"]
        )

        row, col = rasterio.transform.rowcol(
            transform,
            breach_lon,
            breach_lat
        )

        if not (
            0 <= row < rows
            and
            0 <= col < cols
        ):
            raise ValueError(
                "Hypothetical breach location lies "
                "outside the hydraulic DEM."
            )

        result = {
            "status": "READY_FOR_HYDROGRAPH",
            "scenario_mode": "HYPOTHETICAL_USER_SUPPLIED",
            "simulation_allowed": True,
            "engineering_verification": False,
            "fabricated_values_used": False,

            "important_notice": (
                "This is a user-supplied hypothetical dam-break "
                "scenario. The parameters are not represented as "
                "verified Mettur Dam failure parameters and must "
                "not be interpreted as a failure prediction."
            ),

            "dam_reference": {
                "pic": str(
                    dam["PIC"].iloc[0]
                ),
                "latitude": dam_lat,
                "longitude": dam_lon
            },

            "breach": {
                "latitude": breach_lat,
                "longitude": breach_lon,
                "station_m": float(
                    breach["station_m"]
                ),
                "invert_elevation_m": float(
                    breach["invert_elevation_m"]
                ),
                "crest_elevation_m": float(
                    breach["crest_elevation_m"]
                ),
                "width_m": float(
                    breach["width_m"]
                ),
                "formation_time_hr": float(
                    breach["formation_time_hr"]
                ),
                "side_slope_h_to_v": float(
                    breach.get(
                        "side_slope_h_to_v",
                        1.0
                    )
                )
            },

            "raster_cell": {
                "row": int(row),
                "column": int(col)
            },

            "hydraulic_model": {
                "solver": "NEERAKSH_2D_HLL",
                "equations": "2D shallow-water equations",
                "terrain": str(DEM_FILE),
                "input": "Breach hydrograph Q(t)",
                "outputs": [
                    "water_depth_m",
                    "velocity_mps",
                    "water_surface_elevation_m",
                    "arrival_time_s"
                ]
            }
        }

        save_json(
            OUTPUT_FILE,
            result
        )

        print()
        print("STATUS: READY FOR HYDROGRAPH")
        print("Mode: HYPOTHETICAL USER SUPPLIED")
        print()
        print("Breach latitude:", breach_lat)
        print("Breach longitude:", breach_lon)
        print("Raster row:", row)
        print("Raster column:", col)

        print()
        print("Saved:")
        print(OUTPUT_FILE)

        return

    # ========================================================
    # VERIFIED ENGINEERING MODE
    # ========================================================

    required = [
        "latitude",
        "longitude",
        "station_m",
        "invert_elevation_m",
        "crest_elevation_m",
        "width_m",
        "formation_time_hr"
    ]

    missing = []

    for key in required:

        value = breach.get(key)

        if value is None:
            missing.append(key)

    print()
    print("VERIFIED ENGINEERING BREACH")
    print("-" * 50)

    if missing:

        print("STATUS: BLOCKED")

        for key in missing:
            print("Missing:", key)

        print()
        print(
            "The official dam reference point will NOT "
            "be converted into a breach location."
        )

        result = {
            "status": "BLOCKED",
            "scenario_mode": "VERIFIED_ENGINEERING",
            "simulation_allowed": False,
            "reason": (
                "Verified engineering breach section "
                "has not been supplied."
            ),
            "dam_reference": {
                "pic": str(
                    dam["PIC"].iloc[0]
                ),
                "latitude": dam_lat,
                "longitude": dam_lon
            },
            "missing_parameters": missing,
            "solver": "NEERAKSH_2D_HLL",
            "terrain": str(DEM_FILE),
            "fabricated_values_used": False
        }

        save_json(
            OUTPUT_FILE,
            result
        )

        print()
        print("Saved:")
        print(OUTPUT_FILE)

        return

    # --------------------------------------------------------
    # Numeric validation
    # --------------------------------------------------------

    for key in required:

        try:
            value = float(
                breach[key]
            )
        except Exception:

            raise ValueError(
                f"Invalid numeric value: {key}"
            )

        if not np.isfinite(value):

            raise ValueError(
                f"Non-finite value: {key}"
            )

    if breach["width_m"] <= 0:
        raise ValueError(
            "Breach width must be > 0."
        )

    if breach["formation_time_hr"] <= 0:
        raise ValueError(
            "Formation time must be > 0."
        )

    if (
        breach["invert_elevation_m"]
        >=
        breach["crest_elevation_m"]
    ):
        raise ValueError(
            "Breach invert must be below "
            "dam crest elevation."
        )

    # --------------------------------------------------------
    # Raster location
    # --------------------------------------------------------

    breach_lat = float(
        breach["latitude"]
    )

    breach_lon = float(
        breach["longitude"]
    )

    row, col = rasterio.transform.rowcol(
        transform,
        breach_lon,
        breach_lat
    )

    if not (
        0 <= row < rows
        and
        0 <= col < cols
    ):
        raise ValueError(
            "Breach location lies outside "
            "hydraulic DEM."
        )

    result = {
        "status": "READY_FOR_HYDROGRAPH",
        "scenario_mode": "VERIFIED_ENGINEERING",
        "simulation_allowed": True,
        "engineering_verification": True,
        "dam_reference": {
            "pic": str(
                dam["PIC"].iloc[0]
            ),
            "latitude": dam_lat,
            "longitude": dam_lon
        },
        "breach": {
            "latitude": breach_lat,
            "longitude": breach_lon,
            "station_m": float(
                breach["station_m"]
            ),
            "invert_elevation_m": float(
                breach["invert_elevation_m"]
            ),
            "crest_elevation_m": float(
                breach["crest_elevation_m"]
            ),
            "width_m": float(
                breach["width_m"]
            ),
            "formation_time_hr": float(
                breach["formation_time_hr"]
            ),
            "side_slope_h_to_v": float(
                breach.get(
                    "side_slope_h_to_v",
                    1.0
                )
            )
        },
        "raster_cell": {
            "row": int(row),
            "column": int(col)
        },
        "hydraulic_model": {
            "solver": "NEERAKSH_2D_HLL",
            "equations": "2D shallow-water equations",
            "terrain": str(DEM_FILE),
            "input": "Breach hydrograph Q(t)",
            "outputs": [
                "water_depth_m",
                "velocity_mps",
                "water_surface_elevation_m",
                "arrival_time_s"
            ]
        },
        "fabricated_values_used": False
    }

    save_json(
        OUTPUT_FILE,
        result
    )

    print()
    print("STATUS: READY FOR HYDROGRAPH")
    print()
    print("Saved:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    validate()