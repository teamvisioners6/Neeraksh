from __future__ import annotations

import json
import math
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import rasterio


# ============================================================
# NEERAKSH
# VARATTUPALLAM 2D HYDRODYNAMIC VALIDATION SOLVER
#
# Uses:
#   - Official CWC Varattupallam parameters
#   - Official CartoDEM 30 m DEM
#   - 2D shallow-water equations
#   - HLL finite-volume flux
#
# IMPORTANT:
#   This solver does NOT invent a breach coordinate.
#   CWC study point is NOT automatically treated as breach point.
# ============================================================


PROJECT_ROOT = Path(r"C:\NEERAKSH-1")

DEM_PATH = (
    PROJECT_ROOT
    / "data"
    / "dem"
    / "varattupallam"
    / "varattupallam_cartodem_30m_nodata_clean.tif"
)

CWC_SCENARIO_PATH = (
    PROJECT_ROOT
    / "data"
    / "engineering"
    / "varattupallam"
    / "cwc_hydraulic_scenarios.json"
)

SPATIAL_CONFIG_PATH = (
    PROJECT_ROOT
    / "data"
    / "engineering"
    / "varattupallam"
    / "validation_spatial_config.json"
)

REFERENCE_PATH = (
    PROJECT_ROOT
    / "data"
    / "engineering"
    / "varattupallam"
    / "cwc_varattupallam_reference.json"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "simulations"
    / "outputs"
    / "varattupallam"
    / "solver_2d"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# CONSTANTS
# ============================================================

GRAVITY = 9.80665

MANNING_N = 0.035

DRY_DEPTH = 1.0e-5

CFL = 0.45

MAX_SIMULATION_HOURS = 3.0

MAX_CELLS = 600_000


# ============================================================
# UTILITIES
# ============================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path):

    if not path.exists():
        raise FileNotFoundError(
            f"Missing file:\n{path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8-sig",
    ) as f:

        return json.load(f)


def save_json(path: Path, data):

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            data,
            f,
            indent=2,
        )


# ============================================================
# HEADER
# ============================================================

def print_header():

    print()
    print("=" * 72)
    print(
        "NEERAKSH – VARATTUPALLAM "
        "2D HYDRODYNAMIC VALIDATION SOLVER"
    )
    print("=" * 72)
    print()


# ============================================================
# CWC SCENARIO LOADER
# ============================================================
def load_cwc_scenario():

    data = load_json(
        CWC_SCENARIO_PATH
    )

    if "piping" not in data:
        raise RuntimeError(
            "The CWC scenario file does not contain "
            "a 'piping' scenario."
        )

    piping = data["piping"]

    # --------------------------------------------------------
    # Exact field names from the existing official CWC
    # scenario JSON.
    # --------------------------------------------------------

    initial_level = piping.get(
        "initial_reservoir_level_m"
    )

    inflow_assumption = piping.get(
        "inflow_assumption"
    )

    breach_invert = piping.get(
        "breach_invert_elevation_m"
    )

    breach_width = piping.get(
        "breach_width_m"
    )

    side_slope = piping.get(
        "breach_side_slope"
    )

    formation_hr = piping.get(
        "formation_time_hr"
    )

    reference_peak = piping.get(
        "published_peak_discharge_m3s"
    )

    # --------------------------------------------------------
    # Validate official source values.
    # --------------------------------------------------------

    missing = []

    if initial_level is None:
        missing.append(
            "initial_reservoir_level_m"
        )

    if inflow_assumption is None:
        missing.append(
            "inflow_assumption"
        )

    if breach_invert is None:
        missing.append(
            "breach_invert_elevation_m"
        )

    if breach_width is None:
        missing.append(
            "breach_width_m"
        )

    if side_slope is None:
        missing.append(
            "breach_side_slope"
        )

    if formation_hr is None:
        missing.append(
            "formation_time_hr"
        )

    if reference_peak is None:
        missing.append(
            "published_peak_discharge_m3s"
        )

    if missing:

        raise RuntimeError(
            "Missing required official CWC piping "
            "parameters:\n"
            + "\n".join(
                f"  - {field}"
                for field in missing
            )
        )

    # --------------------------------------------------------
    # CWC piping case explicitly specifies zero inflow.
    # --------------------------------------------------------

    normalized_inflow = 0.0

    if (
        isinstance(
            inflow_assumption,
            str,
        )
        and inflow_assumption.strip().lower()
        != "zero inflow"
    ):

        raise RuntimeError(
            "The configured CWC piping scenario does not "
            "state 'zero inflow'. Refusing to reinterpret "
            "the source assumption."
        )

    # --------------------------------------------------------
    # Normalize the official source values for the solver.
    # --------------------------------------------------------

    normalized = {

        "initial_reservoir_level_m":
            float(
                initial_level
            ),

        "inflow_m3s":
            normalized_inflow,

        "inflow_assumption":
            inflow_assumption,

        "breach_width_m":
            float(
                breach_width
            ),

        "side_slope":
            float(
                side_slope
            ),

        "formation_time_hr":
            float(
                formation_hr
            ),

        "breach_invert_m":
            float(
                breach_invert
            ),

        "reference_peak_discharge_m3s":
            float(
                reference_peak
            ),
    }

    return data, normalized
# ============================================================
# SPATIAL CONFIG
# ============================================================

def validate_spatial_configuration():

    spatial = load_json(
        SPATIAL_CONFIG_PATH
    )

    spatial_reference = spatial.get(
        "spatial_reference",
        {}
    )

    study_point = spatial_reference.get(
        "cwc_study_point",
        {}
    )

    hydraulic = spatial.get(
        "hydraulic_interpretation",
        {}
    )

    latitude = study_point.get(
        "latitude"
    )

    longitude = study_point.get(
        "longitude"
    )

    breach_geometry_verified = hydraulic.get(
        "breach_geometry_verified",
        False
    )

    hydraulic_initial_condition_verified = hydraulic.get(
        "hydraulic_initial_condition_verified",
        False
    )

    simulation_ready = hydraulic.get(
        "simulation_ready",
        False
    )

    print(
        "[SPATIAL CONFIGURATION]"
    )

    print(
        f"  CWC study latitude : "
        f"{latitude}"
    )

    print(
        f"  CWC study longitude: "
        f"{longitude}"
    )

    print(
        f"  Breach geometry verified: "
        f"{breach_geometry_verified}"
    )

    print(
        f"  Hydraulic initial condition verified: "
        f"{hydraulic_initial_condition_verified}"
    )

    print(
        f"  Simulation ready: "
        f"{simulation_ready}"
    )

    return {
        "cwc_study_point": {
            "latitude": latitude,
            "longitude": longitude,
        },

        "breach_geometry_verified":
            breach_geometry_verified,

        "hydraulic_initial_condition_verified":
            hydraulic_initial_condition_verified,

        "simulation_ready":
            simulation_ready,

        "source_config":
            spatial,
    }
# ============================================================
# VERIFIED BREACH LOCATION
# ============================================================

def get_verified_source_location(
    spatial
):

    source = spatial.get(
        "verified_breach_location"
    )

    if not source:

        return None, (
            "No verified_breach_location is present."
        )

    if not source.get(
        "verified",
        False
    ):

        return None, (
            "The breach location exists but "
            "is not marked as verified."
        )

    latitude = source.get(
        "latitude"
    )

    longitude = source.get(
        "longitude"
    )

    if latitude is None or longitude is None:

        return None, (
            "Verified breach location is missing "
            "latitude or longitude."
        )

    return {

        "latitude":
            float(latitude),

        "longitude":
            float(longitude),

        "source":
            source.get("source"),

        "verification_method":
            source.get(
                "verification_method"
            ),
    }, None


# ============================================================
# DEM
# ============================================================

def load_dem():

    if not DEM_PATH.exists():

        raise FileNotFoundError(
            f"Clean Varattupallam DEM not found:\n"
            f"{DEM_PATH}"
        )

    print(
        "[DEM] Loading official CartoDEM..."
    )

    with rasterio.open(
        DEM_PATH
    ) as src:

        dem = src.read(
            1
        ).astype(
            np.float64
        )

        transform = src.transform

        crs = src.crs

        nodata = src.nodata

        bounds = src.bounds

        width = src.width

        height = src.height

    valid = np.isfinite(
        dem
    )

    if nodata is not None:

        valid &= (
            dem != nodata
        )

    if not np.any(valid):

        raise RuntimeError(
            "DEM contains no valid cells."
        )

    values = dem[valid]

    print(
        f"  Size       : "
        f"{width} x {height}"
    )

    print(
        f"  CRS        : "
        f"{crs}"
    )

    print(
        f"  Resolution : "
        f"{transform.a} x "
        f"{abs(transform.e)}"
    )

    print(
        f"  Min elev.  : "
        f"{values.min():.3f} m"
    )

    print(
        f"  Max elev.  : "
        f"{values.max():.3f} m"
    )

    print(
        f"  Valid cells: "
        f"{valid.sum()}"
    )

    return (
        dem,
        transform,
        crs,
        nodata,
        bounds,
        valid,
    )


# ============================================================
# LAT/LON → PIXEL
# ============================================================

def latlon_to_pixel(
    transform,
    latitude,
    longitude,
):

    col, row = ~transform * (
        longitude,
        latitude,
    )

    return (
        int(round(row)),
        int(round(col)),
    )


# ============================================================
# SOURCE PIXEL VALIDATION
# ============================================================

def validate_source_pixel(
    dem,
    transform,
    valid_dem,
    source,
):

    row, col = latlon_to_pixel(
        transform,
        source["latitude"],
        source["longitude"],
    )

    if (
        row < 0
        or row >= dem.shape[0]
        or col < 0
        or col >= dem.shape[1]
    ):

        return None, (
            "Verified breach location "
            "falls outside the DEM."
        )

    if not valid_dem[
        row,
        col
    ]:

        return None, (
            "Verified breach location "
            "falls on a NoData DEM cell."
        )

    return {

        "row":
            row,

        "col":
            col,

        "dem_elevation_m":
            float(
                dem[
                    row,
                    col
                ]
            ),
    }, None


# ============================================================
# HLL FLUX
# ============================================================

def hll_flux(
    h_l,
    hu_l,
    hv_l,
    h_r,
    hu_r,
    hv_r,
    nx,
    ny,
):

    h_l = max(
        h_l,
        0.0,
    )

    h_r = max(
        h_r,
        0.0,
    )

    if h_l > DRY_DEPTH:

        u_l = hu_l / h_l
        v_l = hv_l / h_l

    else:

        u_l = 0.0
        v_l = 0.0

    if h_r > DRY_DEPTH:

        u_r = hu_r / h_r
        v_r = hv_r / h_r

    else:

        u_r = 0.0
        v_r = 0.0

    un_l = (
        u_l * nx
        + v_l * ny
    )

    un_r = (
        u_r * nx
        + v_r * ny
    )

    c_l = math.sqrt(
        GRAVITY * h_l
    )

    c_r = math.sqrt(
        GRAVITY * h_r
    )

    s_l = min(
        un_l - c_l,
        un_r - c_r,
    )

    s_r = max(
        un_l + c_l,
        un_r + c_r,
    )

    fl_h = (
        h_l * un_l
    )

    fl_hu = (
        h_l
        * u_l
        * un_l
        + 0.5
        * GRAVITY
        * h_l
        * h_l
        * nx
    )

    fl_hv = (
        h_l
        * v_l
        * un_l
        + 0.5
        * GRAVITY
        * h_l
        * h_l
        * ny
    )

    fr_h = (
        h_r * un_r
    )

    fr_hu = (
        h_r
        * u_r
        * un_r
        + 0.5
        * GRAVITY
        * h_r
        * h_r
        * nx
    )

    fr_hv = (
        h_r
        * v_r
        * un_r
        + 0.5
        * GRAVITY
        * h_r
        * h_r
        * ny
    )

    if s_l >= 0:

        return (
            fl_h,
            fl_hu,
            fl_hv,
        )

    if s_r <= 0:

        return (
            fr_h,
            fr_hu,
            fr_hv,
        )

    denominator = (
        s_r - s_l
    )

    if abs(
        denominator
    ) < 1e-12:

        return (
            0.0,
            0.0,
            0.0,
        )

    fh = (
        s_r * fl_h
        - s_l * fr_h
        + s_l
        * s_r
        * (h_r - h_l)
    ) / denominator

    fhu = (
        s_r * fl_hu
        - s_l * fr_hu
        + s_l
        * s_r
        * (hu_r - hu_l)
    ) / denominator

    fhv = (
        s_r * fl_hv
        - s_l * fr_hv
        + s_l
        * s_r
        * (hv_r - hv_l)
    ) / denominator

    return (
        fh,
        fhu,
        fhv,
    )


# ============================================================
# X FLUX
# ============================================================

def x_fluxes(
    h,
    hu,
    hv,
):

    rows, cols = h.shape

    fh = np.zeros(
        (rows, cols + 1),
        dtype=np.float64,
    )

    fhu = np.zeros_like(
        fh
    )

    fhv = np.zeros_like(
        fh
    )

    for i in range(rows):

        for j in range(
            1,
            cols,
        ):

            result = hll_flux(

                h[
                    i,
                    j - 1
                ],

                hu[
                    i,
                    j - 1
                ],

                hv[
                    i,
                    j - 1
                ],

                h[
                    i,
                    j
                ],

                hu[
                    i,
                    j
                ],

                hv[
                    i,
                    j
                ],

                1.0,
                0.0,
            )

            fh[i, j] = result[0]
            fhu[i, j] = result[1]
            fhv[i, j] = result[2]

    return (
        fh,
        fhu,
        fhv,
    )


# ============================================================
# Y FLUX
# ============================================================

def y_fluxes(
    h,
    hu,
    hv,
):

    rows, cols = h.shape

    fh = np.zeros(
        (rows + 1, cols),
        dtype=np.float64,
    )

    fhu = np.zeros_like(
        fh
    )

    fhv = np.zeros_like(
        fh
    )

    for i in range(
        1,
        rows,
    ):

        for j in range(cols):

            result = hll_flux(

                h[
                    i - 1,
                    j
                ],

                hu[
                    i - 1,
                    j
                ],

                hv[
                    i - 1,
                    j
                ],

                h[
                    i,
                    j
                ],

                hu[
                    i,
                    j
                ],

                hv[
                    i,
                    j
                ],

                0.0,
                1.0,
            )

            fh[i, j] = result[0]
            fhu[i, j] = result[1]
            fhv[i, j] = result[2]

    return (
        fh,
        fhu,
        fhv,
    )


# ============================================================
# MANNING FRICTION
# ============================================================

def apply_manning(
    h,
    hu,
    hv,
    dt,
):

    wet = h > DRY_DEPTH

    if not np.any(wet):

        return hu, hv

    u = np.zeros_like(h)
    v = np.zeros_like(h)

    u[wet] = (
        hu[wet]
        / h[wet]
    )

    v[wet] = (
        hv[wet]
        / h[wet]
    )

    speed = np.sqrt(
        u * u
        + v * v
    )

    friction = (
        GRAVITY
        * MANNING_N
        * MANNING_N
        * speed
        / np.maximum(
            h,
            1.0e-6,
        ) ** (
            4.0 / 3.0
        )
    )

    factor = (
        1.0
        + dt * friction
    )

    hu[wet] /= factor[wet]

    hv[wet] /= factor[wet]

    return hu, hv


# ============================================================
# BED SLOPE
# ============================================================

def apply_bed_slope(
    h,
    hu,
    hv,
    dem,
    dx,
    dy,
    dt,
):

    dzdy, dzdx = np.gradient(
        dem,
        dy,
        dx,
    )

    wet = h > DRY_DEPTH

    hu[wet] += (
        -GRAVITY
        * h[wet]
        * dzdx[wet]
        * dt
    )

    hv[wet] += (
        -GRAVITY
        * h[wet]
        * dzdy[wet]
        * dt
    )

    return (
        hu,
        hv,
    )


# ============================================================
# CFL
# ============================================================

def calculate_timestep(
    h,
    hu,
    hv,
    dx,
    dy,
):

    wet = h > DRY_DEPTH

    if not np.any(wet):

        return 1.0

    u = np.zeros_like(h)
    v = np.zeros_like(h)

    u[wet] = (
        hu[wet]
        / h[wet]
    )

    v[wet] = (
        hv[wet]
        / h[wet]
    )

    wave_speed = np.sqrt(
        GRAVITY
        * np.maximum(
            h,
            0.0,
        )
    )

    sx = (
        np.abs(u)
        + wave_speed
    )

    sy = (
        np.abs(v)
        + wave_speed
    )

    max_x = np.max(sx)
    max_y = np.max(sy)

    dt_x = (
        dx / max_x
        if max_x > 1e-12
        else 999.0
    )

    dt_y = (
        dy / max_y
        if max_y > 1e-12
        else 999.0
    )

    return CFL * min(
        dt_x,
        dt_y,
    )


# ============================================================
# BOUNDARIES
# ============================================================

def enforce_boundaries(
    h,
    hu,
    hv,
):

    h[0, :] = h[1, :]
    h[-1, :] = h[-2, :]

    h[:, 0] = h[:, 1]
    h[:, -1] = h[:, -2]

    hu[0, :] = hu[1, :]
    hu[-1, :] = hu[-2, :]

    hu[:, 0] = hu[:, 1]
    hu[:, -1] = hu[:, -2]

    hv[0, :] = hv[1, :]
    hv[-1, :] = hv[-2, :]

    hv[:, 0] = hv[:, 1]
    hv[:, -1] = hv[:, -2]

    return (
        h,
        hu,
        hv,
    )


# ============================================================
# SOURCE DISCHARGE
# ============================================================

def breach_discharge(
    head,
    width,
):

    if head <= 0:

        return 0.0

    Cd = 0.60

    return (
        Cd
        * width
        * head ** 1.5
        * math.sqrt(
            2.0
            * GRAVITY
        )
    )


# ============================================================
# INITIAL WATER DEPTH
# ============================================================

def initial_depth(
    dem,
    reservoir_level,
):

    return np.maximum(
        reservoir_level
        - dem,
        0.0,
    )


# ============================================================
# SOURCE MASK
# ============================================================

def create_source_mask(
    dem,
    row,
    col,
    width_m,
    dx,
    dy,
):

    pixel_size = min(
        dx,
        dy,
    )

    radius_pixels = max(
        1,
        int(
            math.ceil(
                width_m
                / (
                    2.0
                    * pixel_size
                )
            )
        ),
    )

    mask = np.zeros_like(
        dem,
        dtype=bool,
    )

    r0 = max(
        0,
        row - radius_pixels,
    )

    r1 = min(
        dem.shape[0],
        row + radius_pixels + 1,
    )

    c0 = max(
        0,
        col - radius_pixels,
    )

    c1 = min(
        dem.shape[1],
        col + radius_pixels + 1,
    )

    mask[
        r0:r1,
        c0:c1
    ] = True

    return mask


# ============================================================
# RASTER WRITER
# ============================================================

def write_raster(
    path,
    array,
    transform,
    crs,
    valid_dem,
):

    output = np.asarray(
        array,
        dtype=np.float32,
    ).copy()

    output[
        ~valid_dem
    ] = -9999.0

    profile = {

        "driver":
            "GTiff",

        "height":
            output.shape[0],

        "width":
            output.shape[1],

        "count":
            1,

        "dtype":
            "float32",

        "crs":
            crs,

        "transform":
            transform,

        "nodata":
            -9999.0,

        "compress":
            "deflate",
    }

    with rasterio.open(
        path,
        "w",
        **profile,
    ) as dst:

        dst.write(
            output,
            1,
        )


# ============================================================
# MAIN
# ============================================================

def run_solver():

    print_header()

    # --------------------------------------------------------
    # Reference
    # --------------------------------------------------------

    reference = load_json(
        REFERENCE_PATH
    )

    print(
        "[REFERENCE]"
    )

    print(
        f"  Case   : "
        f"{reference.get('case_id')}"
    )

    print(
        f"  Status : "
        f"{reference.get('status')}"
    )

    print()

    # --------------------------------------------------------
    # CWC
    # --------------------------------------------------------

    _, piping = load_cwc_scenario()

    print(
        "[OFFICIAL CWC PIPING PARAMETERS]"
    )

    print(
        f"  Initial reservoir level : "
        f"{piping['initial_reservoir_level_m']} m"
    )

    print(
        f"  Inflow                  : "
        f"{piping['inflow_m3s']} m3/s"
    )

    print(
        f"  Breach width            : "
        f"{piping['breach_width_m']} m"
    )

    print(
        f"  Side slope              : "
        f"{piping['side_slope']}"
    )

    print(
        f"  Formation time          : "
        f"{piping['formation_time_hr']} hr"
    )

    print(
        f"  Breach invert           : "
        f"{piping['breach_invert_m']} m"
    )

    print(
        f"  CWC reference peak Q    : "
        f"{piping['reference_peak_discharge_m3s']} m3/s"
    )

    print()

    # --------------------------------------------------------
    # Spatial
    # --------------------------------------------------------

    spatial = validate_spatial_configuration()

    source, error = (
        get_verified_source_location(
            spatial
        )
    )

    # --------------------------------------------------------
    # HARD GATE
    # --------------------------------------------------------

    if source is None:

        result = {

            "status":
                "BLOCKED",

            "reason":
                "VERIFIED_BREACH_LOCATION_REQUIRED",

            "timestamp_utc":
                utc_now(),

            "case":
                "CWC_VARATTUPALLAM_PIPING",

            "message":
                (
                    "Official CWC hydraulic parameters "
                    "are available, but a verified breach "
                    "coordinate is not available."
                ),

            "spatial_error":
                error,

            "study_point_used_as_breach":
                False,

            "fabricated_values_used":
                False,

            "mettur_parameters_used":
                False,

            "outputs_generated":
                False,
        }

        path = (
            OUTPUT_DIR
            / "solver_status.json"
        )

        save_json(
            path,
            result,
        )

        print(
            "=" * 72
        )

        print(
            "SOLVER STATUS: BLOCKED"
        )

        print()

        print(
            "Reason: VERIFIED BREACH LOCATION REQUIRED"
        )

        print()

        print(
            "The CWC study point is not being "
            "treated as a breach point."
        )

        print()

        print(
            f"Status file:\n{path}"
        )

        return 0

    # --------------------------------------------------------
    # DEM
    # --------------------------------------------------------

    (
        dem,
        transform,
        crs,
        nodata,
        bounds,
        valid_dem,
    ) = load_dem()

    if dem.size > MAX_CELLS:

        raise RuntimeError(
            f"DEM contains "
            f"{dem.size:,} cells. "
            f"Maximum configured is "
            f"{MAX_CELLS:,}."
        )

    # --------------------------------------------------------
    # Grid dimensions
    # --------------------------------------------------------

    mean_lat = (
        bounds.bottom
        + bounds.top
    ) / 2.0

    meters_lat = 111320.0

    meters_lon = (
        111320.0
        * math.cos(
            math.radians(
                mean_lat
            )
        )
    )

    dx = (
        abs(transform.a)
        * meters_lon
    )

    dy = (
        abs(transform.e)
        * meters_lat
    )

    print()

    print(
        "[GRID]"
    )

    print(
        f"  dx: {dx:.3f} m"
    )

    print(
        f"  dy: {dy:.3f} m"
    )

    # --------------------------------------------------------
    # Source
    # --------------------------------------------------------

    source_pixel, error = (
        validate_source_pixel(
            dem,
            transform,
            valid_dem,
            source,
        )
    )

    if source_pixel is None:

        raise RuntimeError(
            error
        )

    print()

    print(
        "[VERIFIED BREACH SOURCE]"
    )

    print(
        f"  Latitude : "
        f"{source['latitude']}"
    )

    print(
        f"  Longitude: "
        f"{source['longitude']}"
    )

    print(
        f"  Row      : "
        f"{source_pixel['row']}"
    )

    print(
        f"  Column   : "
        f"{source_pixel['col']}"
    )

    print(
        f"  DEM elev.: "
        f"{source_pixel['dem_elevation_m']:.3f} m"
    )

    # --------------------------------------------------------
    # Parameters
    # --------------------------------------------------------

    reservoir_level = (
        piping[
            "initial_reservoir_level_m"
        ]
    )

    breach_invert = (
        piping[
            "breach_invert_m"
        ]
    )

    breach_width = (
        piping[
            "breach_width_m"
        ]
    )

    formation_seconds = (
        piping[
            "formation_time_hr"
        ]
        * 3600.0
    )

    reference_peak = (
        piping[
            "reference_peak_discharge_m3s"
        ]
    )

    # --------------------------------------------------------
    # Initial condition
    # --------------------------------------------------------

    h = initial_depth(
        dem,
        reservoir_level,
    )

    h[
        ~valid_dem
    ] = 0.0

    hu = np.zeros_like(
        h,
        dtype=np.float64,
    )

    hv = np.zeros_like(
        h,
        dtype=np.float64,
    )

    # --------------------------------------------------------
    # Source mask
    # --------------------------------------------------------

    source_mask = (
        create_source_mask(
            dem,
            source_pixel["row"],
            source_pixel["col"],
            breach_width,
            dx,
            dy,
        )
    )

    source_cells = int(
        np.count_nonzero(
            source_mask
        )
    )

    print()

    print(
        f"[SOURCE MASK] "
        f"{source_cells} cells"
    )

    # --------------------------------------------------------
    # Simulation
    # --------------------------------------------------------

    duration = (
        MAX_SIMULATION_HOURS
        * 3600.0
    )

    elapsed = 0.0

    iteration = 0

    peak_q = 0.0

    maximum_depth = np.zeros_like(
        h,
        dtype=np.float32,
    )

    maximum_velocity = np.zeros_like(
        h,
        dtype=np.float32,
    )

    arrival_time = np.full(
        h.shape,
        np.nan,
        dtype=np.float32,
    )

    print()

    print(
        "=" * 72
    )

    print(
        "STARTING 2D SOLVER"
    )

    print(
        "=" * 72
    )

    print()

    while elapsed < duration:

        dt = calculate_timestep(
            h,
            hu,
            hv,
            dx,
            dy,
        )

        dt = min(
            dt,
            duration - elapsed,
        )

        if (
            not np.isfinite(dt)
            or dt <= 0
        ):

            raise RuntimeError(
                "Invalid numerical timestep."
            )

        # ----------------------------------------------------
        # Fluxes
        # ----------------------------------------------------

        fx_h, fx_hu, fx_hv = (
            x_fluxes(
                h,
                hu,
                hv,
            )
        )

        fy_h, fy_hu, fy_hv = (
            y_fluxes(
                h,
                hu,
                hv,
            )
        )

        # ----------------------------------------------------
        # Update
        # ----------------------------------------------------

        h_new = (
            h
            - dt / dx
            * (
                fx_h[:, 1:]
                - fx_h[:, :-1]
            )
            - dt / dy
            * (
                fy_h[1:, :]
                - fy_h[:-1, :]
            )
        )

        hu_new = (
            hu
            - dt / dx
            * (
                fx_hu[:, 1:]
                - fx_hu[:, :-1]
            )
            - dt / dy
            * (
                fy_hu[1:, :]
                - fy_hu[:-1, :]
            )
        )

        hv_new = (
            hv
            - dt / dx
            * (
                fx_hv[:, 1:]
                - fx_hv[:, :-1]
            )
            - dt / dy
            * (
                fy_hv[1:, :]
                - fy_hv[:-1, :]
            )
        )

        h_new = np.maximum(
            h_new,
            0.0,
        )

        # ----------------------------------------------------
        # Bed slope
        # ----------------------------------------------------

        hu_new, hv_new = (
            apply_bed_slope(
                h_new,
                hu_new,
                hv_new,
                dem,
                dx,
                dy,
                dt,
            )
        )

        # ----------------------------------------------------
        # Manning
        # ----------------------------------------------------

        hu_new, hv_new = (
            apply_manning(
                h_new,
                hu_new,
                hv_new,
                dt,
            )
        )

        # ----------------------------------------------------
        # Breach development
        # ----------------------------------------------------

        current_time = (
            elapsed + dt
        )

        if formation_seconds > 0:

            fraction = min(
                1.0,
                current_time
                / formation_seconds,
            )

        else:

            fraction = 1.0

        current_level = (
            reservoir_level
            - (
                reservoir_level
                - breach_invert
            )
            * fraction
        )

        head = max(
            current_level
            - breach_invert,
            0.0,
        )

        q_source = (
            breach_discharge(
                head,
                breach_width,
            )
        )

        peak_q = max(
            peak_q,
            q_source,
        )

        # ----------------------------------------------------
        # Distributed source
        # ----------------------------------------------------

        if (
            source_cells > 0
            and q_source > 0
        ):

            cell_area = (
                dx * dy
            )

            added_volume = (
                q_source * dt
            )

            added_depth = (
                added_volume
                / (
                    source_cells
                    * cell_area
                )
            )

            h_new[
                source_mask
            ] += added_depth

        # ----------------------------------------------------
        # Invalid cells
        # ----------------------------------------------------

        h_new[
            ~valid_dem
        ] = 0.0

        hu_new[
            ~valid_dem
        ] = 0.0

        hv_new[
            ~valid_dem
        ] = 0.0

        h_new = np.maximum(
            h_new,
            0.0,
        )

        # ----------------------------------------------------
        # Boundaries
        # ----------------------------------------------------

        (
            h_new,
            hu_new,
            hv_new,
        ) = enforce_boundaries(
            h_new,
            hu_new,
            hv_new,
        )

        # ----------------------------------------------------
        # State
        # ----------------------------------------------------

        h = h_new

        hu = hu_new

        hv = hv_new

        elapsed = current_time

        iteration += 1

        # ----------------------------------------------------
        # Velocity
        # ----------------------------------------------------

        wet = (
            h > DRY_DEPTH
        )

        velocity = np.zeros_like(
            h,
            dtype=np.float64,
        )

        velocity[wet] = (
            np.sqrt(
                hu[wet] ** 2
                + hv[wet] ** 2
            )
            / h[wet]
        )

        # ----------------------------------------------------
        # Maximum fields
        # ----------------------------------------------------

        maximum_depth = np.maximum(
            maximum_depth,
            h.astype(
                np.float32
            ),
        )

        maximum_velocity = np.maximum(
            maximum_velocity,
            velocity.astype(
                np.float32
            ),
        )

        newly_wet = (
            wet
            & np.isnan(
                arrival_time
            )
        )

        arrival_time[
            newly_wet
        ] = elapsed

        # ----------------------------------------------------
        # Progress every approximately 60 sec
        # ----------------------------------------------------

        if (
            iteration == 1
            or int(elapsed)
            % 60
            < max(1, int(dt))
        ):

            print(
                f"t={elapsed/3600.0:6.3f} hr | "
                f"dt={dt:7.3f} s | "
                f"wet={np.count_nonzero(wet):8d} | "
                f"depth={np.max(h):8.3f} m | "
                f"velocity={np.max(velocity):8.3f} m/s | "
                f"Qsrc={q_source:10.3f} m3/s"
            )

    # ========================================================
    # FINAL PRODUCTS
    # ========================================================

    final_wse = (
        dem + h
    )

    depth_path = (
        OUTPUT_DIR
        / "maximum_depth_m.tif"
    )

    velocity_path = (
        OUTPUT_DIR
        / "maximum_velocity_mps.tif"
    )

    wse_path = (
        OUTPUT_DIR
        / "final_water_surface_elevation_m.tif"
    )

    arrival_path = (
        OUTPUT_DIR
        / "arrival_time_seconds.tif"
    )

    write_raster(
        depth_path,
        maximum_depth,
        transform,
        crs,
        valid_dem,
    )

    write_raster(
        velocity_path,
        maximum_velocity,
        transform,
        crs,
        valid_dem,
    )

    write_raster(
        wse_path,
        final_wse,
        transform,
        crs,
        valid_dem,
    )

    write_raster(
        arrival_path,
        arrival_time,
        transform,
        crs,
        valid_dem,
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    if reference_peak > 0:

        difference_pct = (
            (
                peak_q
                - reference_peak
            )
            / reference_peak
        ) * 100.0

    else:

        difference_pct = None

    wet_cells = int(
        np.count_nonzero(
            maximum_depth
            > DRY_DEPTH
        )
    )

    result = {

        "status":
            "COMPLETED",

        "timestamp_utc":
            utc_now(),

        "case":
            "CWC_VARATTUPALLAM_PIPING",

        "solver": {

            "method":
                "2D finite-volume shallow-water equations",

            "flux":
                "HLL",

            "gravity_mps2":
                GRAVITY,

            "manning_n":
                MANNING_N,

            "cfl":
                CFL,
        },

        "official_cwc_parameters": {

            "initial_reservoir_level_m":
                reservoir_level,

            "inflow_m3s":
                piping["inflow_m3s"],

            "breach_width_m":
                breach_width,

            "side_slope":
                piping["side_slope"],

            "formation_time_hr":
                piping["formation_time_hr"],

            "breach_invert_m":
                breach_invert,

            "reference_peak_discharge_m3s":
                reference_peak,
        },

        "dem": {

            "path":
                str(DEM_PATH),

            "crs":
                str(crs),

            "rows":
                int(dem.shape[0]),

            "cols":
                int(dem.shape[1]),

            "dx_m":
                dx,

            "dy_m":
                dy,
        },

        "verified_source": source,

        "source_pixel":
            source_pixel,

        "simulation": {

            "duration_hr":
                MAX_SIMULATION_HOURS,

            "iterations":
                iteration,

            "numerical_peak_source_discharge_m3s":
                peak_q,

            "cwc_reference_peak_discharge_m3s":
                reference_peak,

            "difference_percent":
                difference_pct,

            "maximum_depth_m":
                float(
                    np.max(
                        maximum_depth
                    )
                ),

            "maximum_velocity_mps":
                float(
                    np.max(
                        maximum_velocity
                    )
                ),

            "wet_cells":
                wet_cells,
        },

        "outputs": {

            "maximum_depth":
                str(depth_path),

            "maximum_velocity":
                str(velocity_path),

            "final_water_surface":
                str(wse_path),

            "arrival_time":
                str(arrival_path),
        },

        "integrity": {

            "official_cwc_parameters_used":
                True,

            "fabricated_values_used":
                False,

            "mettur_parameters_used":
                False,

            "study_point_used_as_breach":
                False,

            "verified_breach_location_used":
                True,
        },
    }

    result_path = (
        OUTPUT_DIR
        / "solver_result.json"
    )

    save_json(
        result_path,
        result,
    )

    print()

    print(
        "=" * 72
    )

    print(
        "2D SOLVER COMPLETED"
    )

    print(
        "=" * 72
    )

    print()

    print(
        f"Iterations       : {iteration}"
    )

    print(
        f"Numerical peak Q : "
        f"{peak_q:.3f} m3/s"
    )

    print(
        f"CWC peak Q       : "
        f"{reference_peak:.3f} m3/s"
    )

    print(
        f"Difference       : "
        f"{difference_pct:.3f}%"
    )

    print(
        f"Maximum depth    : "
        f"{np.max(maximum_depth):.3f} m"
    )

    print(
        f"Maximum velocity : "
        f"{np.max(maximum_velocity):.3f} m/s"
    )

    print(
        f"Wet cells        : "
        f"{wet_cells}"
    )

    print()

    print(
        "OUTPUT FILES:"
    )

    print(
        f"  {depth_path}"
    )

    print(
        f"  {velocity_path}"
    )

    print(
        f"  {wse_path}"
    )

    print(
        f"  {arrival_path}"
    )

    print(
        f"  {result_path}"
    )

    print()

    return 0


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        raise SystemExit(
            run_solver()
        )

    except KeyboardInterrupt:

        print()
        print(
            "Solver interrupted."
        )

        raise SystemExit(
            130
        )

    except Exception as exc:

        error = {

            "status":
                "ERROR",

            "timestamp_utc":
                utc_now(),

            "error_type":
                type(exc).__name__,

            "error":
                str(exc),

            "fabricated_values_used":
                False,

            "mettur_parameters_used":
                False,
        }

        error_path = (
            OUTPUT_DIR
            / "solver_error.json"
        )

        save_json(
            error_path,
            error,
        )

        print()
        print(
            "=" * 72
        )

        print(
            "SOLVER ERROR"
        )

        print(
            "=" * 72
        )

        print()

        print(
            str(exc)
        )

        print()

        print(
            f"Error report: "
            f"{error_path}"
        )

        raise