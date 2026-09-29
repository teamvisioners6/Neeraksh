from pathlib import Path
import json
import math
import time

import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
import geopandas as gpd


# ============================================================
# NEERAKSH — METTUR HYPOTHETICAL 2D HLL SOLVER
# ============================================================
#
# IMPORTANT:
# This is a HYPOTHETICAL DAM-BREAK SCENARIO.
#
# It is NOT:
#   - a prediction of Mettur Dam failure
#   - an actual breach geometry
#   - an officially verified breach location
#   - a validated flood forecast
#
# The breach width and formation time come from the project's
# engineering SCREENING scenario only.
#
# Reservoir hydraulic state:
#   CWC stage-storage relationship
#
# Downstream terrain:
#   Official CartoDEM 30 m
#
# Numerical method:
#   2D shallow-water equations
#   HLL finite-volume flux
#   Hydrostatic reconstruction
#   Manning friction
#   Open outward-flow boundaries
#
# ============================================================


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(r"C:\NEERAKSH-1")

DEM_PATH = (
    PROJECT_ROOT
    / "data"
    / "dem"
    / "mettur"
    / "mettur_correct_dem_30m.tif"
)

RESERVOIR_PATH = (
    PROJECT_ROOT
    / "gis"
    / "raw"
    / "reservoirs"
    / "stanley_reservoir_mettur.shp"
)

HYDRORIVERS_PATH = (
    PROJECT_ROOT
    / "data"
    / "hydrosheds"
    / "hydrorivers"
    / "asia"
    / "HydroRIVERS_v10_as_shp"
    / "HydroRIVERS_v10_as.shp"
)

HYDROGRAPH_PATH = (
    PROJECT_ROOT
    / "simulations"
    / "outputs"
    / "mettur"
    / "hydrograph"
    / "mettur_breach_hydrograph.csv"
)
HYDRAULIC_STATE_PATH = (
    PROJECT_ROOT
    / "simulations"
    / "outputs"
    / "mettur"
    / "reservoir_state"
    / "mettur_reservoir_state.json"
)

SCENARIO_PATH = (
    PROJECT_ROOT
    / "simulations"
    / "scenarios"
    / "mettur"
    / "mettur_source_bounded_scenarios.json"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "simulations"
    / "outputs"
    / "mettur"
    / "hll_test"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_JSON = OUTPUT_DIR / "mettur_hypothetical_2d_hll_test.json"


# ============================================================
# OFFICIAL METTUR REFERENCE
# ============================================================

METTUR_LAT = 11.8030555556
METTUR_LON = 77.8066666667


# ============================================================
# NUMERICAL SETTINGS
# ============================================================

GRID_RESOLUTION_M = 60.0

TEST_DURATION_SECONDS = 3600.0

MANNING_N = 0.040

GRAVITY = 9.81

MIN_DEPTH = 1.0e-5

# Robust wet/dry thresholds for the numerical solver.
# These are numerical stabilization parameters, not physical flood limits.
DRY_DEPTH_CUTOFF = 0.02
SHALLOW_DEPTH_LIMIT = 0.10
SHALLOW_VELOCITY_CAP = 20.0
NUMERICAL_VELOCITY_CAP = float("inf")

# Hydraulic preprocessing: remove isolated DEM spikes without changing
# the raw DEM file used for project display/source documentation.
HYDRAULIC_TERRAIN_MEDIAN_FILTER = True

MAX_DEPTH_ALLOWED = 30.0

# Diagnostic stop: identify the first problematic hydraulic cell before
# attempting a full 3600 s routing run. This is NOT a physical threshold.
DIAGNOSTIC_STOP_DEPTH_M = 20.0

MAX_VELOCITY_ALLOWED = 150.0

CFL_NUMBER = 0.15

MAX_DT = 1.0

MIN_DT = 0.005

SOURCE_LENGTH_M = 1200.0

MCFT_TO_MCM = 0.028316846592


# ============================================================
# UTILITY
# ============================================================

def banner(text):
    print()
    print("=" * 72)
    print(text)
    print("=" * 72)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# HOTSPOT DIAGNOSTIC
# ============================================================

def print_hotspot_diagnostic(
    mr,
    mc,
    terrain,
    h,
    hu,
    hv,
    valid_terrain,
    face_valid_x,
    face_valid_y,
    source_mask=None,
    radius=3,
):
    """Diagnostic only. Does not modify solver state."""

    print()
    print("=" * 90)
    print("HOTSPOT LOCAL DIAGNOSTIC")
    print("=" * 90)

    r0 = max(0, mr - radius)
    r1 = min(terrain.shape[0], mr + radius + 1)
    c0 = max(0, mc - radius)
    c1 = min(terrain.shape[1], mc + radius + 1)

    depth_center = max(float(h[mr, mc]), MIN_DEPTH)
    u_center = float(hu[mr, mc]) / depth_center
    v_center = float(hv[mr, mc]) / depth_center
    speed_center = math.hypot(u_center, v_center)

    print(f"Hotspot cell      : row={mr}, col={mc}")
    print(f"Window            : rows {r0}:{r1}, cols {c0}:{c1}")
    print(f"Center terrain    : {terrain[mr, mc]:.3f} m")
    print(f"Center depth      : {h[mr, mc]:.3f} m")
    print(f"Center WSE        : {terrain[mr, mc] + h[mr, mc]:.3f} m")
    print(f"Center velocity   : {speed_center:.3f} m/s")
    print(f"Center valid      : {bool(valid_terrain[mr, mc])}")

    if source_mask is not None:
        print(f"Center source     : {bool(source_mask[mr, mc])}")

    print()
    print("LOCAL TERRAIN / DEPTH / WSE / VELOCITY")
    print("-" * 90)

    for r in range(r0, r1):
        for c in range(c0, c1):
            valid = bool(valid_terrain[r, c])

            if valid:
                terr = float(terrain[r, c])
                depth = float(h[r, c])
                wse = terr + depth
                denom = max(depth, MIN_DEPTH)
                speed = math.hypot(
                    float(hu[r, c]) / denom,
                    float(hv[r, c]) / denom,
                )
                source = (
                    bool(source_mask[r, c])
                    if source_mask is not None
                    else False
                )
                marker = " <-- HOTSPOT" if (r == mr and c == mc) else ""

                print(
                    f"({r:4d},{c:4d}) "
                    f"T={terr:8.3f} "
                    f"H={depth:8.3f} "
                    f"WSE={wse:8.3f} "
                    f"V={speed:8.3f} "
                    f"VALID=1 "
                    f"SOURCE={int(source)}"
                    f"{marker}"
                )
            else:
                print(
                    f"({r:4d},{c:4d}) "
                    f"T=     NaN "
                    f"H={float(h[r,c]):8.3f} "
                    f"WSE=     NaN "
                    f"V=     NaN "
                    f"VALID=0 "
                    f"SOURCE=0 <-- INVALID / NODATA"
                )

    print()
    print("VALID NEIGHBOUR ANALYSIS")
    print("-" * 90)

    neighbours = {
        "N": (mr - 1, mc),
        "S": (mr + 1, mc),
        "W": (mr, mc - 1),
        "E": (mr, mc + 1),
        "NW": (mr - 1, mc - 1),
        "NE": (mr - 1, mc + 1),
        "SW": (mr + 1, mc - 1),
        "SE": (mr + 1, mc + 1),
    }

    valid_count = 0

    for name, (r, c) in neighbours.items():
        if 0 <= r < terrain.shape[0] and 0 <= c < terrain.shape[1]:
            is_valid = bool(valid_terrain[r, c])
            if is_valid:
                valid_count += 1
                print(
                    f"{name:>2}: VALID   "
                    f"terrain={terrain[r,c]:.3f} m, "
                    f"depth={h[r,c]:.3f} m, "
                    f"WSE={terrain[r,c] + h[r,c]:.3f} m"
                )
            else:
                print(f"{name:>2}: INVALID / NODATA")
        else:
            print(f"{name:>2}: OUTSIDE DOMAIN")

    print(f"\nValid immediate neighbours: {valid_count}/8")

    print()
    print("FACE VALIDITY AROUND HOTSPOT")
    print("-" * 90)

    x_west = bool(face_valid_x[mr, mc]) if 0 <= mc < face_valid_x.shape[1] else False
    x_east = bool(face_valid_x[mr, mc + 1]) if 0 <= mc + 1 < face_valid_x.shape[1] else False
    y_north = bool(face_valid_y[mr, mc]) if 0 <= mr < face_valid_y.shape[0] else False
    y_south = bool(face_valid_y[mr + 1, mc]) if 0 <= mr + 1 < face_valid_y.shape[0] else False

    print(f"West face  : {x_west}")
    print(f"East face  : {x_east}")
    print(f"North face : {y_north}")
    print(f"South face : {y_south}")

    blocked_faces = sum([not x_west, not x_east, not y_north, not y_south])
    print(f"Blocked surrounding faces: {blocked_faces}/4")

    local_valid = valid_terrain[r0:r1, c0:c1]
    local_terrain = terrain[r0:r1, c0:c1][local_valid]
    local_depth = h[r0:r1, c0:c1][local_valid]

    if len(local_terrain) > 0:
        print()
        print("LOCAL STATISTICS")
        print("-" * 90)
        print(
            f"Terrain min/max : {np.min(local_terrain):.3f} / "
            f"{np.max(local_terrain):.3f} m"
        )
        print(
            f"Depth min/max   : {np.min(local_depth):.3f} / "
            f"{np.max(local_depth):.3f} m"
        )
        print(
            f"Terrain range   : "
            f"{np.max(local_terrain) - np.min(local_terrain):.3f} m"
        )
        print(
            f"Local valid cells: {np.sum(local_valid)} / {local_valid.size}"
        )

    print("=" * 90)


# ============================================================
# HYDRAULIC STATE
# ============================================================

def load_hydraulic_state():

    state = load_json(HYDRAULIC_STATE_PATH)

    reservoir = state.get(
        "reservoir_observation",
        {}
    )

    # ========================================================
    # 1. FIND OBSERVED STORAGE
    # ========================================================

    storage_mcft = None

    storage_keys = [
        "storage_mcft",
        "storage_m_cft",
        "current_storage_mcft",
        "observed_storage_mcft",
        "storage",
        "current_storage",
    ]

    # Search reservoir object
    for key in storage_keys:

        if key in reservoir:

            storage_mcft = reservoir[key]
            break

    # Search root object
    if storage_mcft is None:

        for key in storage_keys:

            if key in state:

                storage_mcft = state[key]
                break

    # Search observed_state
    if storage_mcft is None:

        observed = state.get(
            "observed_state",
            {}
        )

        for key in storage_keys:

            if key in observed:

                storage_mcft = observed[key]
                break

    if storage_mcft is None:

        raise RuntimeError(
            "Observed Mettur storage not found "
            "in hydraulic state."
        )

    storage_mcft = float(
        storage_mcft
    )

    # ========================================================
    # 2. CONVERT M.CFT -> MCM
    # ========================================================

    storage_mcm = (
        storage_mcft
        * MCFT_TO_MCM
    )

    # ========================================================
    # 3. LOAD CWC STAGE-STORAGE CURVE
    # ========================================================

    CWC_STAGE_STORAGE_PATH = (
        PROJECT_ROOT
        / "data"
        / "hydrology"
        / "mettur"
        / "cwc_stage_storage_2020.csv"
    )

    if not CWC_STAGE_STORAGE_PATH.exists():

        raise RuntimeError(
            "CWC stage-storage CSV not found:\n"
            f"{CWC_STAGE_STORAGE_PATH}"
        )

    import csv

    elevations = []
    cumulative_storage = []

    with open(
        CWC_STAGE_STORAGE_PATH,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:

            elevation = row.get(
                "elevation_m"
            )

            storage = row.get(
                "cumulative_live_capacity_MCM"
            )

            if (
                elevation is None
                or storage is None
            ):
                continue

            try:

                elevations.append(
                    float(elevation)
                )

                cumulative_storage.append(
                    float(storage)
                )

            except ValueError:

                continue

    if len(elevations) < 2:

        raise RuntimeError(
            "CWC stage-storage curve does not "
            "contain enough valid points."
        )

    elevations = np.asarray(
        elevations,
        dtype=np.float64,
    )

    cumulative_storage = np.asarray(
        cumulative_storage,
        dtype=np.float64,
    )

    # ========================================================
    # 4. SORT CURVE
    # ========================================================

    order = np.argsort(
        cumulative_storage
    )

    cumulative_storage = (
        cumulative_storage[order]
    )

    elevations = (
        elevations[order]
    )

    # ========================================================
    # 5. CHECK STORAGE RANGE
    # ========================================================

    min_storage = float(
        cumulative_storage[0]
    )

    max_storage = float(
        cumulative_storage[-1]
    )

    if (
        storage_mcm < min_storage
        or storage_mcm > max_storage
    ):

        raise RuntimeError(
            "Observed storage is outside the "
            "CWC stage-storage curve range.\n"
            f"Observed: {storage_mcm:.6f} MCM\n"
            f"Curve range: "
            f"{min_storage:.6f} - "
            f"{max_storage:.6f} MCM"
        )

    # ========================================================
    # 6. STORAGE -> WSE INTERPOLATION
    # ========================================================

    hydraulic_wse = float(
        np.interp(
            storage_mcm,
            cumulative_storage,
            elevations,
        )
    )

    # ========================================================
    # 7. DISPLAY
    # ========================================================

    print()
    print(
        "HYDRAULIC STATE LOADED"
    )

    print(
        f"Observed storage: "
        f"{storage_mcft:.3f} M.Cft"
    )

    print(
        f"Converted storage: "
        f"{storage_mcm:.6f} MCM"
    )

    print(
        f"CWC storage curve range: "
        f"{min_storage:.6f} - "
        f"{max_storage:.6f} MCM"
    )

    print(
        f"Derived hydraulic WSE: "
        f"{hydraulic_wse:.6f} m"
    )

    print(
        "WSE source: "
        "CWC stage-storage interpolation"
    )

    print(
        "Datum note: "
        "This is NOT treated as an independent "
        "vertical datum transformation."
    )

    return {

        "storage_mcft": storage_mcft,

        "storage_mcm": storage_mcm,

        "volume_m3": (
            storage_mcm
            * 1_000_000.0
        ),

        "wse_m": hydraulic_wse,

        "status": state.get(
            "status"
        ),
    }
# ============================================================
# DEM
# ============================================================

def load_dem_metric():

    banner("LOADING METTUR DEM")

    with rasterio.open(DEM_PATH) as src:

        print(f"DEM CRS: {src.crs}")
        print(f"DEM shape: {src.height} x {src.width}")

        dem_raw = src.read(
            1,
            masked=True
        ).filled(
            np.nan
        ).astype(
            np.float32
        )

        print(
            f"DEM minimum: "
            f"{np.nanmin(dem_raw):.3f} m"
        )

        print(
            f"DEM maximum: "
            f"{np.nanmax(dem_raw):.3f} m"
        )

        src_bounds = src.bounds
        src_crs = src.crs

        dst_crs = "EPSG:32643"

        transform, width, height = calculate_default_transform(
            src_crs,
            dst_crs,
            src.width,
            src.height,
            *src_bounds,
            resolution=GRID_RESOLUTION_M,
        )

        # ============================================================
        # ROBUST DEM REPROJECTION
        # ============================================================

        dem_metric = np.full(
            (height, width),
            np.nan,
            dtype=np.float32,
        )

        # ------------------------------------------------------------
        # 1. Bilinear DEM reprojection
        # ------------------------------------------------------------

        reproject(
            source=rasterio.band(src, 1),
            destination=dem_metric,
            src_transform=src.transform,
            src_crs=src.crs,
            src_nodata=src.nodata,
            dst_transform=transform,
            dst_crs=dst_crs,
            dst_nodata=np.nan,
            resampling=Resampling.bilinear,
        )

        # ------------------------------------------------------------
        # 2. Calculate source-validity fraction
        # ------------------------------------------------------------

        source_array = src.read(1)

        source_valid_mask = (
            np.isfinite(source_array)
            & (source_array != src.nodata)
        )

        valid_fraction = np.zeros(
            (height, width),
            dtype=np.float32,
        )

        reproject(
            source=source_valid_mask.astype(np.float32),
            destination=valid_fraction,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=transform,
            dst_crs=dst_crs,
            dst_nodata=0.0,
            resampling=Resampling.average,
        )

        # ------------------------------------------------------------
        # 3. Recover only sufficiently covered cells
        # ------------------------------------------------------------

        partial_valid = (
            (valid_fraction >= 0.25)
            & (~np.isfinite(dem_metric))
        )

        recovered_count = 0

        if np.any(partial_valid):

            nearest_dem = np.full(
                (height, width),
                np.nan,
                dtype=np.float32,
            )

            reproject(
                source=rasterio.band(src, 1),
                destination=nearest_dem,
                src_transform=src.transform,
                src_crs=src.crs,
                src_nodata=src.nodata,
                dst_transform=transform,
                dst_crs=dst_crs,
                dst_nodata=np.nan,
                resampling=Resampling.nearest,
            )

            recover_mask = (
                partial_valid
                & np.isfinite(nearest_dem)
            )

            recovered_count = int(
                np.count_nonzero(recover_mask)
            )

            dem_metric[recover_mask] = (
                nearest_dem[recover_mask]
            )

        # ============================================================
        # QUALITY CONTROL
        # ============================================================

        print()
        print("DEM REPROJECTION QUALITY CONTROL")
        print(
            f"Destination cells: "
            f"{height * width:,}"
        )

        print(
            f"Source-valid coverage cells: "
            f"{np.count_nonzero(valid_fraction > 0):,}"
        )

        print(
            f"Cells recovered from valid source terrain: "
            f"{recovered_count:,}"
        )

        print(
            f"Remaining DEM NoData cells: "
            f"{np.count_nonzero(~np.isfinite(dem_metric)):,}"
        )

        print(
            f"Cells with >=25% valid source coverage: "
            f"{np.count_nonzero(valid_fraction >= 0.25):,}"
        )

        print(
            f"Cells with <25% valid source coverage: "
            f"{np.count_nonzero(valid_fraction < 0.25):,}"
        )

        print(
            f"Metric CRS: {dst_crs}"
        )

        print(
            f"Metric grid: "
            f"{height} x {width}"
        )

        print(
            f"Grid resolution: "
            f"{GRID_RESOLUTION_M:.1f} m"
        )

        valid = np.isfinite(dem_metric)

        if not np.any(valid):

            raise RuntimeError(
                "DEM contains no valid cells."
            )

        print(
            f"Metric DEM minimum: "
            f"{np.nanmin(dem_metric):.3f} m"
        )

        print(
            f"Metric DEM maximum: "
            f"{np.nanmax(dem_metric):.3f} m"
        )

        return (
            dem_metric.astype(np.float64),
            transform,
        )
        # ------------------------------------------------------------------
# ROBUST DEM REPROJECTION
#
# Problem:
# Bilinear resampling with source NoData can discard a destination
# cell even when part of its source footprint contains valid DEM.
#
# Solution:
# 1. Reproject the DEM with bilinear interpolation.
# 2. Reproject a source-validity fraction mask.
# 3. For destination cells with partial valid coverage, recover the
#    elevation using nearest-neighbour sampling from valid source DEM.
#
# No synthetic elevation is created.
# The original CartoDEM values are preserved.
# ------------------------------------------------------------------

    dem_metric = np.full((height, width), np.nan, dtype=np.float32)

    reproject(
        source=rasterio.band(src, 1),
        destination=dem_metric,
        src_transform=src.transform,
        src_crs=src.crs,
        src_nodata=src.nodata,
        dst_transform=transform,
        dst_crs=dst_crs,
        dst_nodata=np.nan,
        resampling=Resampling.bilinear,
    )

    # Reproject source-validity mask using area averaging.
    source_array = src.read(1)

    source_valid_mask = (
        np.isfinite(source_array)
        & (source_array != src.nodata)
    )

    valid_fraction = np.zeros(
        (height, width),
        dtype=np.float32,
    )

    reproject(
        source=source_valid_mask.astype(np.float32),
        destination=valid_fraction,
        src_transform=src.transform,
        src_crs=src.crs,
        dst_transform=transform,
        dst_crs=dst_crs,
        dst_nodata=0.0,
        resampling=Resampling.average,
    )

    # ------------------------------------------------------------------
    # Recover partially covered destination cells
    # ------------------------------------------------------------------

    partial_valid = (
        (valid_fraction > 0.25)
        & (~np.isfinite(dem_metric))
    )

    if np.any(partial_valid):

        nearest_dem = np.full(
            (height, width),
            np.nan,
            dtype=np.float32,
        )

        reproject(
            source=rasterio.band(src, 1),
            destination=nearest_dem,
            src_transform=src.transform,
            src_crs=src.crs,
            src_nodata=src.nodata,
            dst_transform=transform,
            dst_crs=metric_crs,
            dst_nodata=np.nan,
            resampling=Resampling.nearest,
        )

        recovered_count = int(
            np.count_nonzero(
                partial_valid & np.isfinite(nearest_dem)
            )
        )

        dem_metric[
            partial_valid & np.isfinite(nearest_dem)
        ] = nearest_dem[
            partial_valid & np.isfinite(nearest_dem)
        ]

    else:
        recovered_count = 0

    print()
    print("DEM REPROJECTION QUALITY CONTROL")
    print(f"Destination cells: {height * width:,}")
    print(
        f"Source-valid coverage cells: "
        f"{np.count_nonzero(valid_fraction > 0):,}"
    )
    print(
        f"Partially covered cells recovered: "
        f"{recovered_count:,}"
    )
    print(
        f"Remaining DEM NoData cells: "
        f"{np.count_nonzero(~np.isfinite(dem_metric)):,}"
    )

    print(f"Metric CRS: {dst_crs}")
    print(f"Metric grid: {height} x {width}")
    print(f"Grid resolution: {GRID_RESOLUTION_M:.1f} m")

    valid = np.isfinite(dem_metric)

    if not np.any(valid):
        raise RuntimeError("DEM contains no valid cells.")

    print(
        f"Metric DEM minimum: "
        f"{np.nanmin(dem_metric):.3f} m"
    )

    print(
        f"Metric DEM maximum: "
        f"{np.nanmax(dem_metric):.3f} m"
    )

    return dem_metric.astype(np.float64), transform


# ============================================================
# HYDRAULIC TERRAIN CONDITIONING
# ============================================================

def condition_hydraulic_terrain(dem):
    """
    Apply a small 3x3 median filter to the hydraulic copy of the DEM.

    The original DEM file is never modified. This is a numerical
    preprocessing step intended to suppress isolated cell-scale spikes
    that can create unrealistically large shallow-water accelerations.
    It must not be described as surveyed terrain correction.
    """
    if not HYDRAULIC_TERRAIN_MEDIAN_FILTER:
        return dem

    print()
    print("HYDRAULIC TERRAIN CONDITIONING")
    print("Controlled shallow-depression filling: ENABLED")
    print("Raw DEM preserved: YES")
    print("Raw DEM file: PRESERVED")
    print("Purpose: numerical spike suppression only")

    conditioned = fill_small_depressions(
    dem,
    max_fill_depth_m=0.50,
)

    valid = np.isfinite(dem)
    conditioned[~valid] = np.nan

    delta = conditioned[valid] - dem[valid]
    print(f"Median absolute terrain change: {np.median(np.abs(delta)):.3f} m")
    print(f"Maximum absolute terrain change: {np.max(np.abs(delta)):.3f} m")

    return conditioned.astype(np.float64)


# ============================================================
# RESERVOIR
# ============================================================

def load_reservoir():

    banner("LOADING STANLEY RESERVOIR")

    gdf = gpd.read_file(RESERVOIR_PATH)

    print(f"Reservoir CRS: {gdf.crs}")
    print(f"Reservoir features: {len(gdf)}")

    if gdf.crs is None:
        raise RuntimeError(
            "Reservoir shapefile has no CRS."
        )

    reservoir_utm = gdf.to_crs("EPSG:32643")

    dam_point = gpd.GeoSeries(
        gpd.points_from_xy(
            [METTUR_LON],
            [METTUR_LAT],
        ),
        crs="EPSG:4326",
    ).to_crs("EPSG:32643").iloc[0]

    distances = reservoir_utm.geometry.distance(dam_point)

    nearest_distance = float(distances.min())

    print(
        f"Official Mettur reference: "
        f"{METTUR_LAT:.10f}, {METTUR_LON:.10f}"
    )

    print(
        f"Nearest reservoir boundary: "
        f"{nearest_distance:.2f} m"
    )

    print(
        "Reservoir polygon is NOT used to reconstruct "
        "CWC reservoir storage."
    )

    return reservoir_utm, dam_point, nearest_distance


# ============================================================
# SCENARIO
# ============================================================

def load_scenario():

    banner("LOADING METTUR SCREENING SCENARIO")

    data = load_json(SCENARIO_PATH)

    # --------------------------------------------------------
    # Find METTUR_SCREENING_BASE
    # --------------------------------------------------------

    scenarios = data.get("scenarios", [])

    if isinstance(scenarios, dict):

        scenarios = list(
            scenarios.values()
        )

    selected = None

    for scenario in scenarios:

        if not isinstance(scenario, dict):
            continue

        scenario_id = str(
            scenario.get(
                "scenario_id",
                scenario.get(
                    "id",
                    ""
                )
            )
        )

        if (
            scenario_id
            == "METTUR_SCREENING_BASE"
        ):

            selected = scenario
            break

    # --------------------------------------------------------
    # Alternative structure:
    #
    # {
    #   "METTUR_SCREENING_BASE": {...}
    # }
    # --------------------------------------------------------

    if selected is None:

        direct = data.get(
            "METTUR_SCREENING_BASE"
        )

        if isinstance(direct, dict):

            selected = direct

    # --------------------------------------------------------
    # Search recursively as a final structural fallback.
    # --------------------------------------------------------

    def recursive_find(obj):

        if isinstance(obj, dict):

            scenario_id = str(
                obj.get(
                    "scenario_id",
                    obj.get(
                        "id",
                        ""
                    )
                )
            )

            if (
                scenario_id
                == "METTUR_SCREENING_BASE"
            ):

                return obj

            for value in obj.values():

                result = recursive_find(
                    value
                )

                if result is not None:
                    return result

        elif isinstance(obj, list):

            for item in obj:

                result = recursive_find(
                    item
                )

                if result is not None:
                    return result

        return None

    if selected is None:

        selected = recursive_find(
            data
        )

    if selected is None:

        raise RuntimeError(
            "METTUR_SCREENING_BASE not found "
            "in scenario file."
        )

    print(
        "Scenario: "
        f"{selected.get('scenario_id', 'METTUR_SCREENING_BASE')}"
    )

    # ========================================================
    # FIND BREACH PARAMETERS
    # ========================================================

    breach = selected.get(
        "breach",
        {}
    )

    if not isinstance(breach, dict):
        breach = {}

    # --------------------------------------------------------
    # Search known locations for width
    # --------------------------------------------------------

    width = None

    width_keys = [
        "width_m",
        "breach_width_m",
        "width",
    ]

    for key in width_keys:

        if key in breach:

            width = breach[key]
            break

        if key in selected:

            width = selected[key]
            break

    # --------------------------------------------------------
    # Formation time
    # --------------------------------------------------------

    formation_hr = None

    formation_keys = [
        "formation_time_hr",
        "formation_hr",
        "formation_time",
        "breach_formation_time_hr",
    ]

    for key in formation_keys:

        if key in breach:

            formation_hr = breach[key]
            break

        if key in selected:

            formation_hr = selected[key]
            break

    # --------------------------------------------------------
    # Side slope
    # --------------------------------------------------------

    side_slope = None

    side_slope_keys = [
        "side_slope_horizontal_to_vertical",
        "side_slope",
        "side_slope_hv",
    ]

    for key in side_slope_keys:

        if key in breach:

            side_slope = breach[key]
            break

        if key in selected:

            side_slope = selected[key]
            break

    # --------------------------------------------------------
    # Recursive numeric search for width
    # --------------------------------------------------------

    def find_numeric_key(
        obj,
        keys,
    ):

        if isinstance(obj, dict):

            for key in keys:

                if key in obj:

                    value = obj[key]

                    if (
                        isinstance(
                            value,
                            (int, float),
                        )
                        and not isinstance(
                            value,
                            bool,
                        )
                    ):

                        return float(value)

            for value in obj.values():

                result = find_numeric_key(
                    value,
                    keys,
                )

                if result is not None:
                    return result

        elif isinstance(obj, list):

            for item in obj:

                result = find_numeric_key(
                    item,
                    keys,
                )

                if result is not None:
                    return result

        return None

    if width is None:

        width = find_numeric_key(
            selected,
            [
                "width_m",
                "breach_width_m",
            ],
        )

    if formation_hr is None:

        formation_hr = find_numeric_key(
            selected,
            [
                "formation_time_hr",
                "formation_hr",
            ],
        )

    if side_slope is None:

        side_slope = find_numeric_key(
            selected,
            [
                "side_slope_horizontal_to_vertical",
                "side_slope",
            ],
        )

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # These are engineering screening values only.
    # We do not invent them here.
    # --------------------------------------------------------

    if width is None:

        raise RuntimeError(
            "Screening breach width missing.\n"
            "The scenario file does not expose "
            "a usable width_m / breach_width_m value."
        )

    if formation_hr is None:

        raise RuntimeError(
            "Screening formation time missing."
        )

    if side_slope is None:

        side_slope = 0.0

    width = float(width)

    formation_hr = float(
        formation_hr
    )

    side_slope = float(
        side_slope
    )

    # --------------------------------------------------------
    # DISPLAY
    # --------------------------------------------------------

    print(
        f"Breach width: "
        f"{width:.3f} m"
    )

    print(
        f"Formation time: "
        f"{formation_hr:.3f} hr"
    )

    print(
        f"Side slope: "
        f"{side_slope:.3f}:1"
    )

    print()

    print(
        "WARNING: These are engineering "
        "SCREENING parameters only."
    )

    print(
        "They are NOT verified Mettur "
        "failure parameters."
    )

    return {

        "scenario_id": (
            selected.get(
                "scenario_id",
                "METTUR_SCREENING_BASE",
            )
        ),

        "breach_width_m": width,

        "formation_time_hr": formation_hr,

        "side_slope": side_slope,
    }
# ============================================================
# ============================================================
# SCENARIO
# ============================================================

def load_scenario():

    banner("LOADING METTUR SCREENING SCENARIO")

    data = load_json(SCENARIO_PATH)

    # --------------------------------------------------------
    # Find METTUR_SCREENING_BASE
    # --------------------------------------------------------

    scenarios = data.get("scenarios", [])

    if isinstance(scenarios, dict):
        scenarios = list(scenarios.values())

    selected = None

    for scenario in scenarios:

        if not isinstance(scenario, dict):
            continue

        scenario_id = str(
            scenario.get(
                "scenario_id",
                scenario.get("id", "")
            )
        )

        if scenario_id == "METTUR_SCREENING_BASE":
            selected = scenario
            break

    # --------------------------------------------------------
    # Direct structure fallback
    # --------------------------------------------------------

    if selected is None:

        direct = data.get("METTUR_SCREENING_BASE")

        if isinstance(direct, dict):
            selected = direct

    # --------------------------------------------------------
    # Recursive fallback
    # --------------------------------------------------------

    def recursive_find(obj):

        if isinstance(obj, dict):

            scenario_id = str(
                obj.get(
                    "scenario_id",
                    obj.get("id", "")
                )
            )

            if scenario_id == "METTUR_SCREENING_BASE":
                return obj

            for value in obj.values():

                result = recursive_find(value)

                if result is not None:
                    return result

        elif isinstance(obj, list):

            for item in obj:

                result = recursive_find(item)

                if result is not None:
                    return result

        return None

    if selected is None:
        selected = recursive_find(data)

    if selected is None:

        raise RuntimeError(
            "METTUR_SCREENING_BASE not found "
            "in scenario file."
        )

    print(
        "Scenario: "
        f"{selected.get('scenario_id', 'METTUR_SCREENING_BASE')}"
    )

    # ========================================================
    # IMPORTANT:
    # Actual JSON stores screening parameters under:
    #
    # failure:
    #   breach_width_m:
    #       screening_value
    #
    #   formation_time_hr:
    #       screening_value
    #
    #   side_slope_h_to_v:
    #       screening_value
    #
    # ========================================================

    failure = selected.get("failure", {})

    if not isinstance(failure, dict):
        failure = {}

    # --------------------------------------------------------
    # BREACH WIDTH
    # --------------------------------------------------------

    width = None

    width_obj = failure.get(
        "breach_width_m"
    )

    if isinstance(width_obj, dict):

        width = width_obj.get(
            "screening_value"
        )

    elif isinstance(width_obj, (int, float)):

        width = width_obj

    # Fallback: other possible locations
    if width is None:

        for key in [
            "width_m",
            "breach_width_m",
            "width",
        ]:

            value = selected.get(key)

            if isinstance(value, (int, float)):

                width = value
                break

            if isinstance(value, dict):

                candidate = value.get(
                    "screening_value"
                )

                if isinstance(
                    candidate,
                    (int, float)
                ):

                    width = candidate
                    break

    # --------------------------------------------------------
    # FORMATION TIME
    # --------------------------------------------------------

    formation_hr = None

    formation_obj = failure.get(
        "formation_time_hr"
    )

    if isinstance(formation_obj, dict):

        formation_hr = formation_obj.get(
            "screening_value"
        )

    elif isinstance(
        formation_obj,
        (int, float)
    ):

        formation_hr = formation_obj

    # Fallback
    if formation_hr is None:

        for key in [
            "formation_time_hr",
            "formation_hr",
            "formation_time",
            "breach_formation_time_hr",
        ]:

            value = selected.get(key)

            if isinstance(value, (int, float)):

                formation_hr = value
                break

            if isinstance(value, dict):

                candidate = value.get(
                    "screening_value"
                )

                if isinstance(
                    candidate,
                    (int, float)
                ):

                    formation_hr = candidate
                    break

    # --------------------------------------------------------
    # SIDE SLOPE
    # --------------------------------------------------------

    side_slope = None

    side_slope_obj = failure.get(
        "side_slope_h_to_v"
    )

    if isinstance(
        side_slope_obj,
        dict
    ):

        side_slope = side_slope_obj.get(
            "screening_value"
        )

    elif isinstance(
        side_slope_obj,
        (int, float)
    ):

        side_slope = side_slope_obj

    # Fallback
    if side_slope is None:

        for key in [
            "side_slope_horizontal_to_vertical",
            "side_slope",
            "side_slope_hv",
            "side_slope_h_to_v",
        ]:

            value = selected.get(key)

            if isinstance(
                value,
                (int, float)
            ):

                side_slope = value
                break

            if isinstance(value, dict):

                candidate = value.get(
                    "screening_value"
                )

                if isinstance(
                    candidate,
                    (int, float)
                ):

                    side_slope = candidate
                    break

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if width is None:

        raise RuntimeError(
            "Screening breach width missing.\n"
            "Expected failure.breach_width_m."
        )

    if formation_hr is None:

        raise RuntimeError(
            "Screening formation time missing.\n"
            "Expected failure.formation_time_hr."
        )

    if side_slope is None:

        side_slope = 0.0

    width = float(width)

    formation_hr = float(
        formation_hr
    )

    side_slope = float(
        side_slope
    )

    # --------------------------------------------------------
    # DISPLAY
    # --------------------------------------------------------

    print(
        f"Breach width: "
        f"{width:.3f} m"
    )

    print(
        f"Formation time: "
        f"{formation_hr:.3f} hr"
    )

    print(
        f"Side slope: "
        f"{side_slope:.3f}:1"
    )

    print()

    print(
        "WARNING: These are engineering "
        "SCREENING parameters only."
    )

    print(
        "They are NOT verified Mettur "
        "failure parameters."
    )

    return {

        "scenario_id": (
            selected.get(
                "scenario_id",
                "METTUR_SCREENING_BASE",
            )
        ),

        "breach_width_m": width,

        "formation_time_hr": formation_hr,

        "side_slope": side_slope,
    }
# # ============================================================
# HYDROGRAPH
# ============================================================

def load_hydrograph():

    banner("LOADING HYPOTHETICAL BREACH HYDROGRAPH")

    if not HYDROGRAPH_PATH.exists():

        raise RuntimeError(
            "Hydrograph file not found:\n"
            f"{HYDROGRAPH_PATH}"
        )

    import csv

    times = []
    discharges = []

    # --------------------------------------------------------
    # CSV hydrograph
    # --------------------------------------------------------

    with open(
        HYDROGRAPH_PATH,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        if reader.fieldnames is None:

            raise RuntimeError(
                "Hydrograph CSV has no header."
            )

        print(
            "Hydrograph columns:",
            reader.fieldnames
        )

        for row in reader:

            # Time
            t = (
                row.get("time_s")
                or row.get("time")
                or row.get("Time")
                or row.get("seconds")
            )

            # Discharge
            q = (
                row.get("discharge_m3s")
                or row.get("discharge")
                or row.get("Discharge")
                or row.get("Q_m3s")
                or row.get("Q")
            )

            if t is None or q is None:
                continue

            try:

                times.append(
                    float(t)
                )

                discharges.append(
                    float(q)
                )

            except (
                ValueError,
                TypeError
            ):

                continue

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    if len(times) < 2:

        raise RuntimeError(
            "Hydrograph needs at least "
            "two valid time-discharge points."
        )

    times = np.asarray(
        times,
        dtype=np.float64
    )

    discharges = np.asarray(
        discharges,
        dtype=np.float64
    )

    # --------------------------------------------------------
    # Sort by time
    # --------------------------------------------------------

    order = np.argsort(times)

    times = times[order]

    discharges = discharges[order]

    # --------------------------------------------------------
    # Remove duplicate timestamps
    # --------------------------------------------------------

    unique_times, unique_indices = np.unique(
        times,
        return_index=True
    )

    times = unique_times

    discharges = discharges[
        unique_indices
    ]

    if len(times) < 2:

        raise RuntimeError(
            "Hydrograph contains fewer than "
            "two unique timestamps."
        )

    # --------------------------------------------------------
    # Basic validation
    # --------------------------------------------------------

    if np.any(~np.isfinite(times)):

        raise RuntimeError(
            "Hydrograph contains invalid time values."
        )

    if np.any(~np.isfinite(discharges)):

        raise RuntimeError(
            "Hydrograph contains invalid discharge values."
        )

    if np.any(np.diff(times) < 0):

        raise RuntimeError(
            "Hydrograph times are not monotonic."
        )

    if np.any(discharges < 0):

        raise RuntimeError(
            "Hydrograph contains negative discharge."
        )

    # --------------------------------------------------------
    # Peak
    # --------------------------------------------------------

    peak_idx = int(
        np.argmax(discharges)
    )

    peak_q = float(
        discharges[peak_idx]
    )

    peak_time = float(
        times[peak_idx]
    )

    # --------------------------------------------------------
    # Display
    # --------------------------------------------------------

    print(
        f"Hydrograph points: "
        f"{len(times)}"
    )

    print(
        f"Hydrograph duration: "
        f"{times[-1]:.2f} s"
    )

    print(
        f"Peak discharge: "
        f"{peak_q:.3f} m3/s"
    )

    print(
        f"Peak time: "
        f"{peak_time:.2f} s"
    )

    print(
        f"Hydrograph source: "
        f"{HYDROGRAPH_PATH}"
    )

    return times, discharges

# ============================================================
# SOURCE MASK
# ============================================================

def create_source_mask(
    dem,
    transform,
    reservoir_utm,
    dam_point,
    breach_width_m,
):
    """
    Creates a hypothetical source corridor centered on the official
    Mettur reference point and oriented toward the mapped downstream
    HydroRIVERS reach.

    IMPORTANT:
    This is a numerical source representation only. It is NOT an
    actual verified breach section or failure geometry.
    """

    banner("CREATING HYPOTHETICAL SOURCE REGION")

    height, width = dem.shape

    xs = (
        transform.c
        + (np.arange(width) + 0.5) * transform.a
    )

    ys = (
        transform.f
        + (np.arange(height) + 0.5) * transform.e
    )

    X, Y = np.meshgrid(xs, ys)

    dam_x = float(dam_point.x)
    dam_y = float(dam_point.y)

    half_width = breach_width_m / 2.0

    # --------------------------------------------------------
    # FIND THE MAPPED DOWNSTREAM RIVER DIRECTION
    # --------------------------------------------------------
    if not HYDRORIVERS_PATH.exists():
        raise FileNotFoundError(
            f"HydroRIVERS dataset not found: {HYDRORIVERS_PATH}"
        )

    rivers = gpd.read_file(HYDRORIVERS_PATH)

    if rivers.empty:
        raise RuntimeError("HydroRIVERS dataset is empty.")

    if rivers.crs is None:
        raise RuntimeError("HydroRIVERS CRS is missing.")

    rivers_utm = rivers.to_crs("EPSG:32643")

    # Find the mapped reach nearest to the official Mettur point.
    distances = rivers_utm.geometry.distance(dam_point)
    nearest_idx = distances.idxmin()
    nearest_reach = rivers_utm.loc[nearest_idx]

    hyriv_id = nearest_reach.get("HYRIV_ID")
    next_down_id = nearest_reach.get("NEXT_DOWN")

    current_geom = nearest_reach.geometry
    nearest_on_current = current_geom.interpolate(
        current_geom.project(dam_point)
    )

    downstream_target = None

    # Prefer the explicitly linked NEXT_DOWN reach.
    if next_down_id is not None and not (isinstance(next_down_id, float) and np.isnan(next_down_id)):
        try:
            next_id_num = int(next_down_id)
            candidates = rivers_utm[
                rivers_utm["HYRIV_ID"].astype("Int64") == next_id_num
            ]
            if not candidates.empty:
                next_geom = candidates.geometry.iloc[0]
                downstream_target = next_geom.interpolate(
                    next_geom.project(nearest_on_current)
                )
        except Exception:
            downstream_target = None

    # Fallback: use the downstream end of the mapped reach.
    if downstream_target is None:
        start_pt = current_geom.interpolate(0.0)
        end_pt = current_geom.interpolate(current_geom.length)
        # Choose the endpoint farther along the reach from the dam.
        if start_pt.distance(dam_point) <= end_pt.distance(dam_point):
            downstream_target = end_pt
        else:
            downstream_target = start_pt

    vx = float(downstream_target.x - nearest_on_current.x)
    vy = float(downstream_target.y - nearest_on_current.y)
    norm = math.hypot(vx, vy)

    if norm < 1.0:
        raise RuntimeError(
            "Could not determine a valid downstream HydroRIVERS direction."
        )

    direction_x = vx / norm
    direction_y = vy / norm

    print(f"HydroRIVERS reach: HYRIV_ID={hyriv_id}")
    print(f"HydroRIVERS NEXT_DOWN: {next_down_id}")
    print(
        f"Nearest mapped reach distance: "
        f"{float(distances.loc[nearest_idx]):.1f} m"
    )
    print(
        f"Mapped downstream direction vector: "
        f"({direction_x:.4f}, {direction_y:.4f})"
    )
    print(
        "Source anchor: official Mettur reference point "
        f"({METTUR_LAT:.7f}, {METTUR_LON:.7f})"
    )

    # --------------------------------------------------------
    # BUILD SOURCE CORRIDOR
    # --------------------------------------------------------
    dx = X - dam_x
    dy = Y - dam_y

    along = dx * direction_x + dy * direction_y
    across = -dx * direction_y + dy * direction_x

    source_mask = (
        (along >= 0.0)
        & (along <= SOURCE_LENGTH_M)
        & (np.abs(across) <= half_width)
    )

    source_mask &= np.isfinite(dem)

    count = int(np.count_nonzero(source_mask))
    area = count * GRID_RESOLUTION_M * GRID_RESOLUTION_M

    print(f"Source cells: {count}")
    print(f"Source area: {area:.1f} m2")
    print(f"Source length: {SOURCE_LENGTH_M:.1f} m")
    print(f"Source width: {breach_width_m:.3f} m")

    if count == 0:
        raise RuntimeError(
            "Hypothetical source region contains no DEM cells."
        )

    return source_mask


# ============================================================
# HLL FLUX — X DIRECTION
# ============================================================

def hll_flux_x(
    hL,
    huL,
    hvL,
    zL,
    hR,
    huR,
    hvR,
    zR,
):
    """
    HLL flux in the x direction with
    hydrostatic reconstruction.

    Conserved variables:

        U = [h, hu, hv]

    x flux:

        F = [
            hu,
            hu*u + 0.5*g*h^2,
            hu*v
        ]
    """

    etaL = hL + zL
    etaR = hR + zR

    z_face = np.maximum(
        zL,
        zR,
    )

    hLs = np.maximum(
        0.0,
        etaL - z_face,
    )

    hRs = np.maximum(
        0.0,
        etaR - z_face,
    )

    with np.errstate(
        divide="ignore",
        invalid="ignore",
    ):

        uL = np.divide(
            huL,
            hL,
            out=np.zeros_like(hL),
            where=hL > MIN_DEPTH,
        )

        vL = np.divide(
            hvL,
            hL,
            out=np.zeros_like(hL),
            where=hL > MIN_DEPTH,
        )

        uR = np.divide(
            huR,
            hR,
            out=np.zeros_like(hR),
            where=hR > MIN_DEPTH,
        )

        vR = np.divide(
            hvR,
            hR,
            out=np.zeros_like(hR),
            where=hR > MIN_DEPTH,
        )

    # Preserve velocity during hydrostatic reconstruction.
    huLs = hLs * uL
    hvLs = hLs * vL

    huRs = hRs * uR
    hvRs = hRs * vR

    cL = np.sqrt(
        GRAVITY * hLs
    )

    cR = np.sqrt(
        GRAVITY * hRs
    )

    SL = np.minimum(
        uL - cL,
        uR - cR,
    )

    SR = np.maximum(
        uL + cL,
        uR + cR,
    )

    FL_h = huLs

    FL_hu = (
        huLs * uL
        + 0.5 * GRAVITY * hLs * hLs
    )

    FL_hv = huLs * vL

    FR_h = huRs

    FR_hu = (
        huRs * uR
        + 0.5 * GRAVITY * hRs * hRs
    )

    FR_hv = huRs * vR

    # HLL denominator
    denominator = SR - SL

    with np.errstate(
        divide="ignore",
        invalid="ignore",
    ):

        hll_h = np.divide(
            SR * FL_h
            - SL * FR_h
            + SL * SR * (
                hRs - hLs
            ),
            denominator,
            out=np.zeros_like(hL),
            where=np.abs(denominator) > 1e-12,
        )

        hll_hu = np.divide(
            SR * FL_hu
            - SL * FR_hu
            + SL * SR * (
                huRs - huLs
            ),
            denominator,
            out=np.zeros_like(hL),
            where=np.abs(denominator) > 1e-12,
        )

        hll_hv = np.divide(
            SR * FL_hv
            - SL * FR_hv
            + SL * SR * (
                hvRs - hvLs
            ),
            denominator,
            out=np.zeros_like(hL),
            where=np.abs(denominator) > 1e-12,
        )

    mask_L = SL >= 0.0
    mask_R = SR <= 0.0

    flux_h = np.where(
        mask_L,
        FL_h,
        np.where(
            mask_R,
            FR_h,
            hll_h,
        ),
    )

    flux_hu = np.where(
        mask_L,
        FL_hu,
        np.where(
            mask_R,
            FR_hu,
            hll_hu,
        ),
    )

    flux_hv = np.where(
        mask_L,
        FL_hv,
        np.where(
            mask_R,
            FR_hv,
            hll_hv,
        ),
    )

    # Hydrostatic reconstruction corrections.
    #
    # These corrections act only on normal momentum.
    correction_L = (
        0.5
        * GRAVITY
        * (
            hL * hL
            - hLs * hLs
        )
    )

    correction_R = (
        0.5
        * GRAVITY
        * (
            hR * hR
            - hRs * hRs
        )
    )

    return (
        flux_h,
        flux_hu,
        flux_hv,
        correction_L,
        correction_R,
    )


# ============================================================
# HLL FLUX — Y DIRECTION
# ============================================================

def hll_flux_y(
    hB,
    huB,
    hvB,
    zB,
    hT,
    huT,
    hvT,
    zT,
):
    """
    HLL flux in the y direction.

    y flux:

        G = [
            hv,
            hv*u,
            hv*v + 0.5*g*h^2
        ]
    """

    etaB = hB + zB
    etaT = hT + zT

    z_face = np.maximum(
        zB,
        zT,
    )

    hBs = np.maximum(
        0.0,
        etaB - z_face,
    )

    hTs = np.maximum(
        0.0,
        etaT - z_face,
    )

    with np.errstate(
        divide="ignore",
        invalid="ignore",
    ):

        uB = np.divide(
            huB,
            hB,
            out=np.zeros_like(hB),
            where=hB > MIN_DEPTH,
        )

        vB = np.divide(
            hvB,
            hB,
            out=np.zeros_like(hB),
            where=hB > MIN_DEPTH,
        )

        uT = np.divide(
            huT,
            hT,
            out=np.zeros_like(hT),
            where=hT > MIN_DEPTH,
        )

        vT = np.divide(
            hvT,
            hT,
            out=np.zeros_like(hT),
            where=hT > MIN_DEPTH,
        )

    huBs = hBs * uB
    hvBs = hBs * vB

    huTs = hTs * uT
    hvTs = hTs * vT

    cB = np.sqrt(
        GRAVITY * hBs
    )

    cT = np.sqrt(
        GRAVITY * hTs
    )

    SB = np.minimum(
        vB - cB,
        vT - cT,
    )

    ST = np.maximum(
        vB + cB,
        vT + cT,
    )

    GB_h = hvBs

    GB_hu = hvBs * uB

    GB_hv = (
        hvBs * vB
        + 0.5 * GRAVITY * hBs * hBs
    )

    GT_h = hvTs

    GT_hu = hvTs * uT

    GT_hv = (
        hvTs * vT
        + 0.5 * GRAVITY * hTs * hTs
    )

    denominator = ST - SB

    with np.errstate(
        divide="ignore",
        invalid="ignore",
    ):

        hll_h = np.divide(
            ST * GB_h
            - SB * GT_h
            + SB * ST * (
                hTs - hBs
            ),
            denominator,
            out=np.zeros_like(hB),
            where=np.abs(denominator) > 1e-12,
        )

        hll_hu = np.divide(
            ST * GB_hu
            - SB * GT_hu
            + SB * ST * (
                huTs - huBs
            ),
            denominator,
            out=np.zeros_like(hB),
            where=np.abs(denominator) > 1e-12,
        )

        hll_hv = np.divide(
            ST * GB_hv
            - SB * GT_hv
            + SB * ST * (
                hvTs - hvBs
            ),
            denominator,
            out=np.zeros_like(hB),
            where=np.abs(denominator) > 1e-12,
        )

    mask_B = SB >= 0.0
    mask_T = ST <= 0.0

    flux_h = np.where(
        mask_B,
        GB_h,
        np.where(
            mask_T,
            GT_h,
            hll_h,
        ),
    )

    flux_hu = np.where(
        mask_B,
        GB_hu,
        np.where(
            mask_T,
            GT_hu,
            hll_hu,
        ),
    )

    flux_hv = np.where(
        mask_B,
        GB_hv,
        np.where(
            mask_T,
            GT_hv,
            hll_hv,
        ),
    )

    correction_B = (
        0.5
        * GRAVITY
        * (
            hB * hB
            - hBs * hBs
        )
    )

    correction_T = (
        0.5
        * GRAVITY
        * (
            hT * hT
            - hTs * hTs
        )
    )

    return (
        flux_h,
        flux_hu,
        flux_hv,
        correction_B,
        correction_T,
    )


# ============================================================
# MANNING FRICTION
# ============================================================

def apply_manning_friction(
    h,
    hu,
    hv,
    dt,
):

    wet = h > MIN_DEPTH

    if not np.any(wet):
        return

    h_safe = np.maximum(
        h,
        MIN_DEPTH,
    )

    with np.errstate(
        divide="ignore",
        invalid="ignore",
    ):

        u = np.divide(
            hu,
            h_safe,
            out=np.zeros_like(h),
            where=wet,
        )

        v = np.divide(
            hv,
            h_safe,
            out=np.zeros_like(h),
            where=wet,
        )

    speed = np.sqrt(
        u * u
        + v * v
    )

    denominator = (
        1.0
        + (
            GRAVITY
            * MANNING_N
            * MANNING_N
            * speed
            * dt
            / np.power(
                h_safe,
                4.0 / 3.0,
            )
        )
    )

    denominator = np.maximum(
        denominator,
        1.0,
    )

    hu[wet] /= denominator[wet]
    hv[wet] /= denominator[wet]


def apply_wet_dry_and_momentum_limiter(h, hu, hv, valid):
    """
    Positivity/wet-dry stabilization after each FV update.

    Water depth is conserved. Only momentum is damped where the
    numerical state becomes excessively energetic. This prevents
    near-dry cells from producing pathological velocities while
    keeping the mass-balance accounting unchanged.

    This is explicitly a NUMERICAL stabilization, not a physical
    velocity constraint or a prediction of real flood velocity.
    """

    active = valid & (h > 0.0)

    # Remove momentum from dry/near-dry cells.
    dry = valid & (h <= DRY_DEPTH_CUTOFF)
    hu[dry] = 0.0
    hv[dry] = 0.0

    wet = active & (h > DRY_DEPTH_CUTOFF)
    if not np.any(wet):
        hu[~valid] = 0.0
        hv[~valid] = 0.0
        return 0

    h_safe = np.maximum(h, DRY_DEPTH_CUTOFF)
    u = np.divide(hu, h_safe, out=np.zeros_like(h), where=wet)
    v = np.divide(hv, h_safe, out=np.zeros_like(h), where=wet)
    speed = np.sqrt(u * u + v * v)

    # Stronger damping in very shallow water.
    shallow = wet & (h < SHALLOW_DEPTH_LIMIT) & (speed > SHALLOW_VELOCITY_CAP)
    clipped = 0
    if np.any(shallow):
        factor = np.divide(
            SHALLOW_VELOCITY_CAP,
            speed,
            out=np.ones_like(speed),
            where=speed > 0.0,
        )
        hu[shallow] *= factor[shallow]
        hv[shallow] *= factor[shallow]
        clipped += int(np.count_nonzero(shallow))

    # IMPORTANT: no global velocity clipping is applied here.
    # The previous 60 m/s cap removed momentum while leaving water depth
    # unchanged, which could artificially trap incoming mass and create the
    # observed depth runaway. The adaptive CFL time step is now the primary
    # numerical stability control.

    hu[~valid] = 0.0
    hv[~valid] = 0.0
    return clipped


# ============================================================
# NoData / COMPUTATIONAL-DOMAIN BOUNDARY HELPERS
# ============================================================

def prepare_open_nodata_x_states(h, hu, hv, terrain, valid):
    """
    Build HLL face states for valid/NoData interfaces.

    A NoData cell is treated as outside the computational domain, not as
    a fabricated terrain cell and not as a permanent hydraulic wall.
    For a valid/NoData face, the valid-cell state is copied to the ghost
    side (zero-gradient/open boundary). The resulting flux is then limited
    to the outward direction only.
    """
    left_valid = valid[:, :-1]
    right_valid = valid[:, 1:]

    active = left_valid | right_valid

    h_l = np.where(left_valid, h[:, :-1], h[:, 1:])
    hu_l = np.where(left_valid, hu[:, :-1], hu[:, 1:])
    hv_l = np.where(left_valid, hv[:, :-1], hv[:, 1:])
    z_l = np.where(left_valid, terrain[:, :-1], terrain[:, 1:])

    h_r = np.where(right_valid, h[:, 1:], h[:, :-1])
    hu_r = np.where(right_valid, hu[:, 1:], hu[:, :-1])
    hv_r = np.where(right_valid, hv[:, 1:], hv[:, :-1])
    z_r = np.where(right_valid, terrain[:, 1:], terrain[:, :-1])

    both_invalid = ~active
    h_l[both_invalid] = 0.0
    hu_l[both_invalid] = 0.0
    hv_l[both_invalid] = 0.0
    z_l[both_invalid] = 0.0
    h_r[both_invalid] = 0.0
    hu_r[both_invalid] = 0.0
    hv_r[both_invalid] = 0.0
    z_r[both_invalid] = 0.0

    return (
        h_l, hu_l, hv_l, z_l,
        h_r, hu_r, hv_r, z_r,
        left_valid, right_valid, active,
    )


def prepare_open_nodata_y_states(h, hu, hv, terrain, valid):
    """
    Same as the x-direction helper, but for horizontal y-faces.
    """
    bottom_valid = valid[:-1, :]
    top_valid = valid[1:, :]

    active = bottom_valid | top_valid

    h_b = np.where(bottom_valid, h[:-1, :], h[1:, :])
    hu_b = np.where(bottom_valid, hu[:-1, :], hu[1:, :])
    hv_b = np.where(bottom_valid, hv[:-1, :], hv[1:, :])
    z_b = np.where(bottom_valid, terrain[:-1, :], terrain[1:, :])

    h_t = np.where(top_valid, h[1:, :], h[:-1, :])
    hu_t = np.where(top_valid, hu[1:, :], hu[:-1, :])
    hv_t = np.where(top_valid, hv[1:, :], hv[:-1, :])
    z_t = np.where(top_valid, terrain[1:, :], terrain[:-1, :])

    both_invalid = ~active
    h_b[both_invalid] = 0.0
    hu_b[both_invalid] = 0.0
    hv_b[both_invalid] = 0.0
    z_b[both_invalid] = 0.0
    h_t[both_invalid] = 0.0
    hu_t[both_invalid] = 0.0
    hv_t[both_invalid] = 0.0
    z_t[both_invalid] = 0.0

    return (
        h_b, hu_b, hv_b, z_b,
        h_t, hu_t, hv_t, z_t,
        bottom_valid, top_valid, active,
    )


def limit_nodata_open_flux_x(fx_h, fx_hu, fx_hv, left_valid, right_valid):
    """
    Keep normal HLL flux on valid-valid faces.
    On valid/NoData faces, permit only outward mass flux.
    """
    left_open = left_valid & ~right_valid
    right_open = ~left_valid & right_valid
    both_invalid = ~left_valid & ~right_valid

    outward_left = left_open & (fx_h > 0.0)
    outward_right = right_open & (fx_h < 0.0)
    valid_flux = (left_valid & right_valid) | outward_left | outward_right

    return (
        np.where(valid_flux, fx_h, 0.0),
        np.where(valid_flux, fx_hu, 0.0),
        np.where(valid_flux, fx_hv, 0.0),
        left_open,
        right_open,
        both_invalid,
    )


def limit_nodata_open_flux_y(fy_h, fy_hu, fy_hv, bottom_valid, top_valid):
    """
    Keep normal HLL flux on valid-valid faces.
    On valid/NoData faces, permit only outward mass flux.
    """
    bottom_open = bottom_valid & ~top_valid
    top_open = ~bottom_valid & top_valid
    both_invalid = ~bottom_valid & ~top_valid

    outward_bottom = bottom_open & (fy_h > 0.0)
    outward_top = top_open & (fy_h < 0.0)
    valid_flux = (bottom_valid & top_valid) | outward_bottom | outward_top

    return (
        np.where(valid_flux, fy_h, 0.0),
        np.where(valid_flux, fy_hu, 0.0),
        np.where(valid_flux, fy_hv, 0.0),
        bottom_open,
        top_open,
        both_invalid,
    )


def calculate_nodata_boundary_outflow_x(fx_h, left_valid, right_valid, dt):
    """Volume leaving the valid domain through internal NoData faces."""
    left_open_out = left_valid & ~right_valid & (fx_h > 0.0)
    right_open_out = ~left_valid & right_valid & (fx_h < 0.0)

    return float(
        (
            np.sum(fx_h[left_open_out])
            - np.sum(fx_h[right_open_out])
        )
        * GRID_RESOLUTION_M
        * dt
    )


def calculate_nodata_boundary_outflow_y(fy_h, bottom_valid, top_valid, dt):
    """Volume leaving the valid domain through internal NoData faces."""
    bottom_open_out = bottom_valid & ~top_valid & (fy_h > 0.0)
    top_open_out = ~bottom_valid & top_valid & (fy_h < 0.0)

    return float(
        (
            np.sum(fy_h[bottom_open_out])
            - np.sum(fy_h[top_open_out])
        )
        * GRID_RESOLUTION_M
        * dt
    )


# ============================================================
# DIAGNOSTICS
# ============================================================

def calculate_diagnostics(
    h,
    hu,
    hv,
    valid,
):

    wet = (
        h > MIN_DEPTH
    ) & valid

    wet_count = int(
        np.count_nonzero(wet)
    )

    if wet_count == 0:

        return {
            "max_depth_m": 0.0,
            "max_velocity_mps": 0.0,
            "wet_cells": 0,
        }

    max_depth = float(
        np.max(
            h[wet]
        )
    )

    h_safe = np.maximum(
        h[wet],
        MIN_DEPTH,
    )

    speed = np.sqrt(
        (
            hu[wet] / h_safe
        ) ** 2
        +
        (
            hv[wet] / h_safe
        ) ** 2
    )

    max_velocity = float(
        np.max(speed)
    )

    return {
        "max_depth_m": max_depth,
        "max_velocity_mps": max_velocity,
        "wet_cells": wet_count,
    }


# ============================================================
# CFL TIME STEP
# ============================================================

def calculate_cfl_dt(
    h,
    hu,
    hv,
    valid,
):

    wet = (
        h > MIN_DEPTH
    ) & valid

    if not np.any(wet):
        return MAX_DT

    h_safe = np.maximum(
        h[wet],
        MIN_DEPTH,
    )

    u = (
        hu[wet]
        / h_safe
    )

    v = (
        hv[wet]
        / h_safe
    )

    c = np.sqrt(
        GRAVITY
        * h_safe
    )

    max_x = float(
        np.max(
            np.abs(u) + c
        )
    )

    max_y = float(
        np.max(
            np.abs(v) + c
        )
    )

    max_signal = max(
        max_x,
        max_y,
    )

    if max_signal <= 1.0e-12:
        return MAX_DT

    dt = (
        CFL_NUMBER
        * GRID_RESOLUTION_M
        / max_signal
    )

    dt = min(
        dt,
        MAX_DT,
    )

    return max(
        dt,
        MIN_DT,
    )


# ============================================================
# OPEN BOUNDARY FLUX
# ============================================================

def apply_open_boundaries(
    h,
    hu,
    hv,
    valid,
    dt,
):

    """
    Outward-only open boundary.

    Left:
        outward direction = -x

    Right:
        outward direction = +x

    Bottom:
        outward direction = -y

    Top:
        outward direction = +y
    """

    boundary_outflow = 0.0

    cell_area_face = GRID_RESOLUTION_M

    # --------------------------------------------------------
    # LEFT
    # --------------------------------------------------------

    wet = (
        h[:, 0] > MIN_DEPTH
    ) & valid[:, 0]

    if np.any(wet):

        hh = np.maximum(
            h[:, 0],
            MIN_DEPTH,
        )

        u = np.divide(
            hu[:, 0],
            hh,
            out=np.zeros_like(hh),
            where=wet,
        )

        v = np.divide(
            hv[:, 0],
            hh,
            out=np.zeros_like(hh),
            where=wet,
        )

        outward_q = -hu[:, 0]

        mask = (
            wet
            & (outward_q > 0.0)
        )

        if np.any(mask):

            q = outward_q[mask]

            boundary_outflow += (
                np.sum(q)
                * cell_area_face
                * dt
            )

            # Physical x flux.
            flux_h = hu[:, 0]
            flux_hu = (
                hu[:, 0] * u
                + 0.5
                * GRAVITY
                * h[:, 0] ** 2
            )
            flux_hv = (
                hu[:, 0] * v
            )

            # Left face contribution:
            # U += F_left * dt/dx
            h[:, 0] += (
                np.where(
                    mask,
                    flux_h,
                    0.0,
                )
                * dt
                / GRID_RESOLUTION_M
            )

            hu[:, 0] += (
                np.where(
                    mask,
                    flux_hu,
                    0.0,
                )
                * dt
                / GRID_RESOLUTION_M
            )

            hv[:, 0] += (
                np.where(
                    mask,
                    flux_hv,
                    0.0,
                )
                * dt
                / GRID_RESOLUTION_M
            )

    # --------------------------------------------------------
    # RIGHT
    # --------------------------------------------------------

    wet = (
        h[:, -1] > MIN_DEPTH
    ) & valid[:, -1]

    if np.any(wet):

        hh = np.maximum(
            h[:, -1],
            MIN_DEPTH,
        )

        u = np.divide(
            hu[:, -1],
            hh,
            out=np.zeros_like(hh),
            where=wet,
        )

        v = np.divide(
            hv[:, -1],
            hh,
            out=np.zeros_like(hh),
            where=wet,
        )

        outward_q = hu[:, -1]

        mask = (
            wet
            & (outward_q > 0.0)
        )

        if np.any(mask):

            q = outward_q[mask]

            boundary_outflow += (
                np.sum(q)
                * cell_area_face
                * dt
            )

            flux_h = hu[:, -1]

            flux_hu = (
                hu[:, -1] * u
                + 0.5
                * GRAVITY
                * h[:, -1] ** 2
            )

            flux_hv = (
                hu[:, -1] * v
            )

            # Right face:
            # U -= F_right * dt/dx
            h[:, -1] -= (
                np.where(
                    mask,
                    flux_h,
                    0.0,
                )
                * dt
                / GRID_RESOLUTION_M
            )

            hu[:, -1] -= (
                np.where(
                    mask,
                    flux_hu,
                    0.0,
                )
                * dt
                / GRID_RESOLUTION_M
            )

            hv[:, -1] -= (
                np.where(
                    mask,
                    flux_hv,
                    0.0,
                )
                * dt
                / GRID_RESOLUTION_M
            )

    # --------------------------------------------------------
    # BOTTOM
    # --------------------------------------------------------

    wet = (
        h[0, :] > MIN_DEPTH
    ) & valid[0, :]

    if np.any(wet):

        hh = np.maximum(
            h[0, :],
            MIN_DEPTH,
        )

        u = np.divide(
            hu[0, :],
            hh,
            out=np.zeros_like(hh),
            where=wet,
        )

        v = np.divide(
            hv[0, :],
            hh,
            out=np.zeros_like(hh),
            where=wet,
        )

        outward_q = -hv[0, :]

        mask = (
            wet
            & (outward_q > 0.0)
        )

        if np.any(mask):

            q = outward_q[mask]

            boundary_outflow += (
                np.sum(q)
                * cell_area_face
                * dt
            )

            flux_h = hv[0, :]

            flux_hu = (
                hv[0, :] * u
            )

            flux_hv = (
                hv[0, :] * v
                + 0.5
                * GRAVITY
                * h[0, :] ** 2
            )

            h[0, :] += (
                np.where(
                    mask,
                    flux_h,
                    0.0,
                )
                * dt
                / GRID_RESOLUTION_M
            )

            hu[0, :] += (
                np.where(
                    mask,
                    flux_hu,
                    0.0,
                )
                * dt
                / GRID_RESOLUTION_M
            )

            hv[0, :] += (
                np.where(
                    mask,
                    flux_hv,
                    0.0,
                )
                * dt
                / GRID_RESOLUTION_M
            )

    # --------------------------------------------------------
    # TOP
    # --------------------------------------------------------

    wet = (
        h[-1, :] > MIN_DEPTH
    ) & valid[-1, :]

    if np.any(wet):

        hh = np.maximum(
            h[-1, :],
            MIN_DEPTH,
        )

        u = np.divide(
            hu[-1, :],
            hh,
            out=np.zeros_like(hh),
            where=wet,
        )

        v = np.divide(
            hv[-1, :],
            hh,
            out=np.zeros_like(hh),
            where=wet,
        )

        outward_q = hv[-1, :]

        mask = (
            wet
            & (outward_q > 0.0)
        )

        if np.any(mask):

            q = outward_q[mask]

            boundary_outflow += (
                np.sum(q)
                * cell_area_face
                * dt
            )

            flux_h = hv[-1, :]

            flux_hu = (
                hv[-1, :] * u
            )

            flux_hv = (
                hv[-1, :] * v
                + 0.5
                * GRAVITY
                * h[-1, :] ** 2
            )

            h[-1, :] -= (
                np.where(
                    mask,
                    flux_h,
                    0.0,
                )
                * dt
                / GRID_RESOLUTION_M
            )

            hu[-1, :] -= (
                np.where(
                    mask,
                    flux_hu,
                    0.0,
                )
                * dt
                / GRID_RESOLUTION_M
            )

            hv[-1, :] -= (
                np.where(
                    mask,
                    flux_hv,
                    0.0,
                )
                * dt
                / GRID_RESOLUTION_M
            )

    return boundary_outflow
def fill_small_depressions(dem, max_fill_depth_m=0.50):
    """
    Controlled shallow-depression filling.

    The TOTAL terrain correction for any cell is limited to
    max_fill_depth_m.

    Raw DEM is never modified.
    """

    print("\n" + "=" * 72)
    print("HYDROLOGICAL DEPRESSION CONDITIONING")
    print("=" * 72)

    print(
        f"Maximum TOTAL permitted depression fill: "
        f"{max_fill_depth_m:.3f} m"
    )

    conditioned = dem.copy()

    # Preserve original terrain so cumulative correction
    # can never exceed the requested limit.
    original = dem.copy()

    rows, cols = dem.shape

    filled_cells = 0
    maximum_fill = 0.0

    for iteration in range(10):

        changes = 0

        for r in range(1, rows - 1):

            for c in range(1, cols - 1):

                center = conditioned[r, c]

                if not np.isfinite(center):
                    continue

                # Current total correction from original DEM.
                current_correction = (
                    center - original[r, c]
                )

                # Never allow cumulative correction
                # beyond the configured limit.
                remaining_fill = (
                    max_fill_depth_m
                    - current_correction
                )

                if remaining_fill <= 0.0:
                    continue

                neighbours = conditioned[
                    r - 1:r + 2,
                    c - 1:c + 2
                ].copy()

                neighbours[1, 1] = np.nan

                valid_neighbours = neighbours[
                    np.isfinite(neighbours)
                ]

                if valid_neighbours.size == 0:
                    continue

                lowest = float(
                    np.min(valid_neighbours)
                )

                required_fill = (
                    lowest - center
                )

                # Only shallow depressions.
                if required_fill > 0.0:

                    applied_fill = min(
                        required_fill,
                        remaining_fill,
                    )

                    if applied_fill > 0.0:

                        conditioned[r, c] = (
                            center + applied_fill
                        )

                        changes += 1
                        filled_cells += 1

                        maximum_fill = max(
                            maximum_fill,
                            applied_fill,
                        )

        print(
            f"Iteration {iteration + 1}: "
            f"{changes} cells adjusted"
        )

        if changes == 0:
            break

    correction = (
        conditioned - original
    )

    valid_correction = correction[
        np.isfinite(correction)
    ]

    if valid_correction.size:

        print(
            f"\nTotal adjusted cells: "
            f"{filled_cells}"
        )

        print(
            f"Maximum TOTAL fill applied: "
            f"{np.max(valid_correction):.3f} m"
        )

        print(
            f"Median absolute correction: "
            f"{np.median(np.abs(valid_correction)):.3f} m"
        )

        print(
            f"Maximum absolute correction: "
            f"{np.max(np.abs(valid_correction)):.3f} m"
        )

    print(
        "\nRaw DEM preserved: YES"
    )

    print(
        "Conditioned DEM used for routing: YES"
    )

    print(
        "Large terrain features preserved: YES"
    )

    return conditioned
# ============================================================
# MAIN HLL ROUTING
# ============================================================

def run_hll_solver():

    banner(
        "NEERAKSH — METTUR HYPOTHETICAL "
        "2D HLL FINITE-VOLUME SOLVER"
    )

    print(
        "STATUS: HYPOTHETICAL ENGINEERING SCENARIO"
    )

    print(
        "This run is NOT an Mettur failure prediction."
    )

    print(
        "No verified Mettur breach location is claimed."
    )

    # --------------------------------------------------------
    # LOAD INPUTS
    # --------------------------------------------------------

    hydraulic = load_hydraulic_state()

    print()
    print("CWC / OBSERVED HYDRAULIC STATE")
    print(
        f"Observed storage: "
        f"{hydraulic['storage_mcft']:.3f} M.Cft"
    )

    print(
        f"Storage basis: "
        f"{hydraulic['storage_mcm']:.6f} MCM"
    )

    print(
        f"Hydraulic WSE: "
        f"{hydraulic['wse_m']:.6f} m"
    )

    print(
        f"Reservoir volume for reporting: "
        f"{hydraulic['volume_m3']:.3f} m3"
    )

    print()
    print(
        "IMPORTANT: CWC stage-storage-derived WSE is "
        "used as hydraulic initialization reference."
    )

    print(
        "It is not treated as an independently verified "
        "vertical datum transformation."
    )

    dem, transform = load_dem_metric()

    dem = condition_hydraulic_terrain(dem)

    reservoir, dam_point, boundary_distance = (
        load_reservoir()
    )

    scenario = load_scenario()

    hydro_times, hydro_q = load_hydrograph()

    # --------------------------------------------------------
    # VALID TERRAIN
    # --------------------------------------------------------

    valid_terrain = np.isfinite(dem)

    # Negative raster artifacts are not treated as
    # downstream terrain cells.
    #
    # This is only a numerical-domain rule.
    valid_terrain &= dem >= 0.0

    terrain = np.where(
        valid_terrain,
        dem,
        0.0,
    )

    rows, cols = terrain.shape

    print()
    print(
        f"Simulation grid: "
        f"{rows} x {cols}"
    )

    print(
        f"Total cells: "
        f"{rows * cols:,}"
    )

    # --------------------------------------------------------
    # SOURCE REGION
    # --------------------------------------------------------

    source_mask = create_source_mask(
        terrain,
        transform,
        reservoir,
        dam_point,
        scenario["breach_width_m"],
    )

    source_cells = int(
        np.count_nonzero(source_mask)
    )

    source_area = (
        source_cells
        * GRID_RESOLUTION_M
        * GRID_RESOLUTION_M
    )

    # --------------------------------------------------------
    # CONSERVED VARIABLES
    # --------------------------------------------------------

    # h  = water depth
    # hu = x momentum
    # hv = y momentum

    h = np.zeros(
        (rows, cols),
        dtype=np.float64,
    )

    hu = np.zeros_like(h)

    hv = np.zeros_like(h)

    # --------------------------------------------------------
    # INITIAL STATE
    # --------------------------------------------------------

    print()
    print(
        "INITIAL DOWNSTREAM STATE:"
    )

    print(
        "Depth: 0.000000 m"
    )

    print(
        "Momentum: 0.000000"
    )

    print(
        "Reservoir storage is NOT dumped "
        "directly into the downstream DEM."
    )

    print(
        "Only the hypothetical breach hydrograph "
        "is injected into the source region."
    )

    # --------------------------------------------------------
    # TIME LOOP
    # --------------------------------------------------------

    current_time = 0.0

    injected_volume = 0.0
    boundary_outflow_volume = 0.0

    diagnostics = []

    simulation_start = time.time()

    last_report_time = -999.0

    print()
    print(
        "STARTING HLL ROUTING"
    )

    print(
        f"Duration: "
        f"{TEST_DURATION_SECONDS:.1f} s"
    )

    print(
        f"Grid: "
        f"{GRID_RESOLUTION_M:.1f} m"
    )

    print(
        f"CFL: "
        f"{CFL_NUMBER:.3f}"
    )

    print(
        f"Manning n: "
        f"{MANNING_N:.3f}"
    )

    while current_time < TEST_DURATION_SECONDS:

        # ----------------------------------------------------
        # CFL DT
        # ----------------------------------------------------

        dt = calculate_cfl_dt(
            h,
            hu,
            hv,
            valid_terrain,
        )

        remaining = (
            TEST_DURATION_SECONDS
            - current_time
        )

        dt = min(
            dt,
            remaining,
        )

        if dt < MIN_DT:

            raise RuntimeError(
                "Time step fell below MIN_DT. "
                "Simulation became numerically stiff."
            )

        # ----------------------------------------------------
        # SOURCE DISCHARGE
        # ----------------------------------------------------

        q = float(
            np.interp(
                current_time,
                hydro_times,
                hydro_q,
            )
        )

        injected_this_step = (
            q * dt
        )

        # ----------------------------------------------------
        # MASS SOURCE
        # ----------------------------------------------------

        if source_cells > 0:

            source_depth_increment = (
                injected_this_step
                / source_area
            )

            h[source_mask] += (
                source_depth_increment
            )

        injected_volume += (
            injected_this_step
        )

        # ----------------------------------------------------
        # PREVIOUS STATE
        # ----------------------------------------------------

        h_before_flux = h.copy()

        # ----------------------------------------------------
        # X-DIRECTION INTERNAL + NoData OPEN FACES
        # ----------------------------------------------------

        (
            hxl, huxl, hvxl, zxl,
            hxr, huxr, hvxr, zxr,
            x_left_valid,
            x_right_valid,
            x_active,
        ) = prepare_open_nodata_x_states(
            h,
            hu,
            hv,
            terrain,
            valid_terrain,
        )

        (
            fx_h,
            fx_hu,
            fx_hv,
            corr_x_left,
            corr_x_right,
        ) = hll_flux_x(
            hxl,
            huxl,
            hvxl,
            zxl,
            hxr,
            huxr,
            hvxr,
            zxr,
        )

        # Valid-valid faces retain normal HLL transport.
        # Valid-NoData faces behave as outward-only open boundaries.
        (
            fx_h,
            fx_hu,
            fx_hv,
            x_left_open,
            x_right_open,
            x_both_invalid,
        ) = limit_nodata_open_flux_x(
            fx_h,
            fx_hu,
            fx_hv,
            x_left_valid,
            x_right_valid,
        )

        # Hydrostatic correction is only meaningful on valid-valid faces.
        normal_x_faces = x_left_valid & x_right_valid
        corr_x_left = np.where(
            normal_x_faces,
            corr_x_left,
            0.0,
        )
        corr_x_right = np.where(
            normal_x_faces,
            corr_x_right,
            0.0,
        )

        # Volume that exits through an internal NoData boundary.
        nodata_boundary_step_x = calculate_nodata_boundary_outflow_x(
            fx_h,
            x_left_valid,
            x_right_valid,
            dt,
        )

        scale_x = dt / GRID_RESOLUTION_M

        # Left cells lose flux.
        h[:, :-1] -= fx_h * scale_x
        hu[:, :-1] -= (fx_hu + corr_x_left) * scale_x
        hv[:, :-1] -= fx_hv * scale_x

        # Right cells gain flux.
        h[:, 1:] += fx_h * scale_x
        hu[:, 1:] += (fx_hu + corr_x_right) * scale_x
        hv[:, 1:] += fx_hv * scale_x

        del (
            hxl, huxl, hvxl, zxl,
            hxr, huxr, hvxr, zxr,
            fx_h, fx_hu, fx_hv,
            corr_x_left, corr_x_right,
        )

        # ----------------------------------------------------
        # Y-DIRECTION INTERNAL + NoData OPEN FACES
        # ----------------------------------------------------

        # ----------------------------------------------------

        (
            hyb, huyb, hvyb, zyb,
            hyt, huyt, hvyt, zyt,
            y_bottom_valid,
            y_top_valid,
            y_active,
        ) = prepare_open_nodata_y_states(
            h,
            hu,
            hv,
            terrain,
            valid_terrain,
        )

        (
            fy_h,
            fy_hu,
            fy_hv,
            corr_y_bottom,
            corr_y_top,
        ) = hll_flux_y(
            hyb,
            huyb,
            hvyb,
            zyb,
            hyt,
            huyt,
            hvyt,
            zyt,
        )

        (
            fy_h,
            fy_hu,
            fy_hv,
            y_bottom_open,
            y_top_open,
            y_both_invalid,
        ) = limit_nodata_open_flux_y(
            fy_h,
            fy_hu,
            fy_hv,
            y_bottom_valid,
            y_top_valid,
        )

        normal_y_faces = y_bottom_valid & y_top_valid
        corr_y_bottom = np.where(
            normal_y_faces,
            corr_y_bottom,
            0.0,
        )
        corr_y_top = np.where(
            normal_y_faces,
            corr_y_top,
            0.0,
        )

        nodata_boundary_step_y = calculate_nodata_boundary_outflow_y(
            fy_h,
            y_bottom_valid,
            y_top_valid,
            dt,
        )

        scale_y = dt / GRID_RESOLUTION_M

        # Bottom cells lose y-positive flux.
        h[:-1, :] -= fy_h * scale_y
        hu[:-1, :] -= fy_hu * scale_y
        hv[:-1, :] -= (fy_hv + corr_y_bottom) * scale_y

        # Top cells gain.
        h[1:, :] += fy_h * scale_y
        hu[1:, :] += fy_hu * scale_y
        hv[1:, :] += (fy_hv + corr_y_top) * scale_y

        del (
            hyb, huyb, hvyb, zyb,
            hyt, huyt, hvyt, zyt,
            fy_h, fy_hu, fy_hv,
            corr_y_bottom, corr_y_top,
        )

        # Count water leaving through NoData boundaries in the mass budget.
        nodata_boundary_step = max(
            0.0,
            nodata_boundary_step_x + nodata_boundary_step_y,
        )
        boundary_outflow_volume += nodata_boundary_step

        # ----------------------------------------------------
        # OPEN BOUNDARIES
        # ----------------------------------------------------

        boundary_step = (
            apply_open_boundaries(
                h,
                hu,
                hv,
                valid_terrain,
                dt,
            )
        )

        boundary_outflow_volume += (
            boundary_step
        )

        # ----------------------------------------------------
        # MANNING FRICTION
        # ----------------------------------------------------

        apply_manning_friction(
            h,
            hu,
            hv,
            dt,
        )

        # ----------------------------------------------------
        # NUMERICAL WET/DRY + MOMENTUM STABILIZATION
        # ----------------------------------------------------

        limiter_cells = apply_wet_dry_and_momentum_limiter(
            h,
            hu,
            hv,
            valid_terrain,
        )

        # ----------------------------------------------------
        # CLEAN SMALL NEGATIVE ROUND-OFF
        # ----------------------------------------------------

        tiny_negative = (
            (h < 0.0)
            & (h > -1.0e-8)
        )

        h[tiny_negative] = 0.0

        # Large negative depth means solver failure.
        min_depth = float(
            np.min(h)
        )

        if min_depth < -1.0e-6:

            raise RuntimeError(
                "Negative water depth detected: "
                f"{min_depth:.6f} m"
            )

        # Invalid terrain remains dry.
        h[~valid_terrain] = 0.0
        hu[~valid_terrain] = 0.0
        hv[~valid_terrain] = 0.0

        # ----------------------------------------------------
        # ADVANCE TIME
        # ----------------------------------------------------

        current_time += dt

        # ----------------------------------------------------
        # DIAGNOSTICS
        # ----------------------------------------------------

        diag = calculate_diagnostics(
            h,
            hu,
            hv,
            valid_terrain,
        )

        domain_volume = float(
            np.sum(h)
            * GRID_RESOLUTION_M
            * GRID_RESOLUTION_M
        )

        expected_volume = (
            injected_volume
            - boundary_outflow_volume
        )

        mass_error = (
            domain_volume
            - expected_volume
        )

        mass_error_pct = 0.0

        if abs(expected_volume) > 1.0:

            mass_error_pct = (
                abs(mass_error)
                / abs(expected_volume)
                * 100.0
            )

        record = {
            "time_s": float(
                current_time
            ),
            "dt_s": float(dt),
            "breach_discharge_m3s": float(q),
            "injected_volume_m3": float(
                injected_volume
            ),
            "boundary_outflow_m3": float(
                boundary_outflow_volume
            ),
            "nodata_boundary_outflow_step_m3": float(
                nodata_boundary_step
            ),
            "domain_water_volume_m3": float(
                domain_volume
            ),
            "mass_balance_error_m3": float(
                mass_error
            ),
            "mass_balance_error_percent": float(
                mass_error_pct
            ),
            "momentum_limiter_cells": int(limiter_cells),
            **diag,
        }

        diagnostics.append(
            record
        )

        # ----------------------------------------------------
        # DIAGNOSTIC CELL LOCATION
        # ----------------------------------------------------

        if diag["max_depth_m"] >= DIAGNOSTIC_STOP_DEPTH_M:
            max_idx = np.unravel_index(
                np.nanargmax(np.where(valid_terrain, h, np.nan)),
                h.shape,
            )
            mr, mc = max_idx
            max_depth_terrain = float(terrain[mr, mc])
            x_m, y_m = rasterio.transform.xy(
                transform, mr, mc, offset="center"
            )
            print()
            print("DIAGNOSTIC STOP — LOCALIZED DEPTH GROWTH")
            print(f"Time: {current_time:.3f} s")
            print(f"Max-depth cell: row={mr}, col={mc}")
            print(f"Projected position: x={x_m:.3f} m, y={y_m:.3f} m")
            print(f"Terrain elevation: {max_depth_terrain:.3f} m")
            print(f"Water depth: {h[mr, mc]:.3f} m")
            print(f"Water surface elevation: {max_depth_terrain + h[mr, mc]:.3f} m")
            print(f"Velocity: {math.hypot(hu[mr, mc]/max(h[mr, mc], MIN_DEPTH), hv[mr, mc]/max(h[mr, mc], MIN_DEPTH)):.3f} m/s")
            print("This identifies the terrain cell where the numerical accumulation begins.")
            print("Do NOT interpret this as a real inundation result.")

            print_hotspot_diagnostic(
                mr=mr,
                mc=mc,
                terrain=terrain,
                h=h,
                hu=hu,
                hv=hv,
                valid_terrain=valid_terrain,
                face_valid_x=face_valid_x,
                face_valid_y=face_valid_y,
                source_mask=source_mask,
                radius=3,
            )
            raise RuntimeError(
                "Diagnostic stop at "
                f"{DIAGNOSTIC_STOP_DEPTH_M:.1f} m depth; inspect localized routing before full run."
            )

        # ----------------------------------------------------
        # SAFETY CHECKS
        # ----------------------------------------------------

        if (
            diag["max_depth_m"]
            > MAX_DEPTH_ALLOWED
        ):

            raise RuntimeError(
                "Maximum depth exceeded numerical "
                "screening threshold: "
                f"{diag['max_depth_m']:.3f} m"
            )

        if (
            diag["max_velocity_mps"]
            > MAX_VELOCITY_ALLOWED
        ):

            raise RuntimeError(
                "Maximum velocity exceeded numerical "
                "screening threshold: "
                f"{diag['max_velocity_mps']:.3f} m/s"
            )

        # ----------------------------------------------------
        # PROGRESS
        # ----------------------------------------------------

        if (
            current_time
            - last_report_time
            >= 10.0
            or current_time
            >= TEST_DURATION_SECONDS
        ):

            print(
                f"t={current_time:7.2f}s | "
                f"dt={dt:7.4f}s | "
                f"Q={q:9.2f} m3/s | "
                f"maxH={diag['max_depth_m']:7.3f}m | "
                f"maxV={diag['max_velocity_mps']:7.3f}m/s | "
                f"wet={diag['wet_cells']:6d} | "
                f"out={boundary_outflow_volume / 1e6:8.4f} MCM | "
                f"err={mass_error_pct:8.4f}%"
            )

            last_report_time = (
                current_time
            )

    # ========================================================
    # FINAL RESULTS
    # ========================================================

    runtime = (
        time.time()
        - simulation_start
    )

    final_diag = calculate_diagnostics(
        h,
        hu,
        hv,
        valid_terrain,
    )

    final_domain_volume = float(
        np.sum(h)
        * GRID_RESOLUTION_M
        * GRID_RESOLUTION_M
    )

    final_expected_volume = (
        injected_volume
        - boundary_outflow_volume
    )

    final_mass_error = (
        final_domain_volume
        - final_expected_volume
    )

    final_mass_error_pct = 0.0

    if abs(final_expected_volume) > 1.0:

        final_mass_error_pct = (
            abs(final_mass_error)
            / abs(final_expected_volume)
            * 100.0
        )

    # ========================================================
    # RESULT OBJECT
    # ========================================================

    result = {

        "project": "NEERAKSH",

        "location": {
            "name": "Mettur Dam / Stanley Reservoir",
            "latitude": METTUR_LAT,
            "longitude": METTUR_LON,
            "reference_status": (
                "OFFICIAL DAM REFERENCE POINT ONLY"
            ),
        },

        "scenario": {

            "scenario_id": scenario[
                "scenario_id"
            ],

            "type": (
                "HYPOTHETICAL ENGINEERING "
                "SCREENING SCENARIO"
            ),

            "breach_width_m": (
                scenario["breach_width_m"]
            ),

            "formation_time_hr": (
                scenario["formation_time_hr"]
            ),

            "side_slope": (
                scenario["side_slope"]
            ),

            "breach_location_status": (
                "NOT VERIFIED"
            ),

            "failure_prediction": False,

            "fabricated_values": False,
        },

        "reservoir_state": {

            "observed_storage_mcft": (
                hydraulic["storage_mcft"]
            ),

            "storage_mcm": (
                hydraulic["storage_mcm"]
            ),

            "storage_volume_m3": (
                hydraulic["volume_m3"]
            ),

            "hydraulic_wse_m": (
                hydraulic["wse_m"]
            ),

            "storage_source_basis": (
                "CWC STAGE-STORAGE "
                "RELATIONSHIP + OFFICIAL "
                "OBSERVED RESERVOIR STORAGE"
            ),

            "datum_note": (
                "Hydraulic WSE is derived by "
                "storage-to-elevation interpolation "
                "from the CWC stage-storage curve. "
                "This is not treated as an independent "
                "vertical datum transformation."
            ),
        },

        "terrain": {

            "dem": str(
                DEM_PATH
            ),

            "crs": "EPSG:32643",

            "grid_resolution_m": (
                GRID_RESOLUTION_M
            ),

            "rows": rows,

            "columns": cols,

            "valid_cells": int(
                np.count_nonzero(
                    valid_terrain
                )
            ),
        },

        "source": {

            "source_type": (
                "HYPOTHETICAL NUMERICAL "
                "BREACH SOURCE"
            ),

            "source_length_m": (
                SOURCE_LENGTH_M
            ),

            "source_width_m": (
                scenario["breach_width_m"]
            ),

            "source_cells": source_cells,

            "source_area_m2": source_area,

            "official_reference_distance_to_"
            "reservoir_boundary_m": (
                boundary_distance
            ),

            "location_warning": (
                "Source region is a numerical "
                "hypothetical representation and "
                "must not be interpreted as the "
                "actual Mettur breach location."
            ),
        },

        "hydrograph": {

            "points": int(
                len(hydro_times)
            ),

            "duration_s": float(
                hydro_times[-1]
            ),

            "peak_discharge_m3s": float(
                np.max(hydro_q)
            ),

            "source": str(
                HYDROGRAPH_PATH
            ),
        },

        "solver": {

            "method": (
                "2D shallow-water "
                "HLL finite-volume"
            ),

            "flux": "HLL",

            "topography_treatment": (
                "Hydrostatic reconstruction"
            ),

            "friction": (
                "Manning semi-implicit friction"
            ),

            "manning_n": MANNING_N,

            "gravity_mps2": GRAVITY,

            "cfl": CFL_NUMBER,
            "hydraulic_terrain_median_filter": HYDRAULIC_TERRAIN_MEDIAN_FILTER,

            "wet_dry_stabilization": True,
            "dry_depth_cutoff_m": DRY_DEPTH_CUTOFF,
            "shallow_depth_limit_m": SHALLOW_DEPTH_LIMIT,
            "shallow_velocity_cap_mps": SHALLOW_VELOCITY_CAP,
            "numerical_velocity_cap_mps": None,
            "stabilization_note": (
                "Momentum-only numerical stabilization; water depth "
                "and mass-balance accounting are unchanged. It is not "
                "a physical flood-velocity limit."
            ),

            "boundary_condition": (
                "Open outward-only outer boundary + "
                "outward-only NoData computational-domain boundary"
            ),

            "simulation_duration_s": (
                TEST_DURATION_SECONDS
            ),

            "diagnostic_stop_depth_m": DIAGNOSTIC_STOP_DEPTH_M,

            "simulation_runtime_s": runtime,
        },

        "mass_balance": {

            "injected_volume_m3": (
                injected_volume
            ),

            "boundary_outflow_m3": (
                boundary_outflow_volume
            ),

            "final_domain_water_volume_m3": (
                final_domain_volume
            ),

            "expected_domain_volume_m3": (
                final_expected_volume
            ),

            "error_m3": (
                final_mass_error
            ),

            "error_percent": (
                final_mass_error_pct
            ),
        },

        "final_diagnostics": final_diag,

        "status": (
            "NUMERICAL DIAGNOSTIC RUN"
        ),

        "interpretation": (
            "This is a hypothetical numerical "
            "routing test using an engineering "
            "screening scenario. Results must not "
            "be presented as a validated Mettur "
            "dam-break forecast."
        ),

        "diagnostics": diagnostics,
    }

    # ========================================================
    # SAVE
    # ========================================================

    with open(
        OUTPUT_JSON,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            result,
            f,
            indent=2,
        )

    # ========================================================
    # FINAL CONSOLE
    # ========================================================

    banner(
        "FINAL HLL SOLVER SUMMARY"
    )

    print(
        f"CWC hydraulic WSE: "
        f"{hydraulic['wse_m']:.6f} m"
    )

    print(
        f"Observed storage: "
        f"{hydraulic['storage_mcm']:.6f} MCM"
    )

    print(
        f"Hypothetical breach width: "
        f"{scenario['breach_width_m']:.3f} m"
    )

    print(
        f"Simulation duration: "
        f"{TEST_DURATION_SECONDS:.1f} s"
    )

    print(
        f"Maximum depth: "
        f"{final_diag['max_depth_m']:.3f} m"
    )

    print(
        f"Maximum velocity: "
        f"{final_diag['max_velocity_mps']:.3f} m/s"
    )

    print(
        f"Wet cells: "
        f"{final_diag['wet_cells']}"
    )

    print(
        f"Injected volume: "
        f"{injected_volume / 1e6:.6f} MCM"
    )

    print(
        f"Boundary outflow: "
        f"{boundary_outflow_volume / 1e6:.6f} MCM"
    )

    print(
        f"Final domain volume: "
        f"{final_domain_volume / 1e6:.6f} MCM"
    )

    print(
        f"Mass balance error: "
        f"{final_mass_error_pct:.6f}%"
    )

    print()
    print(
        f"Output: {OUTPUT_JSON}"
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "Do NOT use this result as a validated "
        "Mettur flood inundation map yet."
    )

    print(
        "Next step is numerical validation and "
        "comparison against an established hydraulic "
        "solver / benchmark."
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    run_hll_solver()