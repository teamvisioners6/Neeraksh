from pathlib import Path
import json
import math
import traceback

import numpy as np
import rasterio

import engineering_scenario_validator as engineering_validator


# ============================================================
# NEERAKSH 2D FLOOD SOLVER
# ============================================================

BASE = Path(r"C:\NEERAKSH-1")

CONFIG_FILE = (
    BASE
    / "simulations"
    / "outputs"
    / "mettur"
    / "mettur_hydraulic_solver_config.json"
)

OUTPUT_DIR = (
    BASE
    / "simulations"
    / "outputs"
    / "mettur"
    / "solver"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# BASIC JSON UTILITIES
# ============================================================

def load_json(path):
    path = Path(path)

    with open(
        path,
        "r",
        encoding="utf-8-sig"
    ) as f:
        return json.load(f)


def save_json(path, data):
    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )


# ============================================================
# NESTED VALUE ACCESS
# ============================================================

def get_nested(obj, path):

    current = obj

    for part in path.split("."):

        if not isinstance(
            current,
            dict
        ):
            return None

        if part not in current:
            return None

        current = current[part]

    return current


# ============================================================
# SCENARIO VALIDATION
# ============================================================

def validate_scenario(config):

    scenario_file = Path(
        config["inputs"]["scenario_file"]
    )

    if not scenario_file.exists():

        raise FileNotFoundError(
            f"Scenario file not found: {scenario_file}"
        )

    scenario = load_json(
        scenario_file
    )

    required = [

        "failure.mechanism.value",

        "failure.breach_location.latitude",

        "failure.breach_location.longitude",

        "failure.breach_width_m.value",

        "failure.formation_time_hr.value",

        "failure.side_slope_h_to_v.value",

        "reservoir_initial_condition.level_ft.value"
    ]

    missing = []

    for item in required:

        value = get_nested(
            scenario,
            item
        )

        if value is None:
            missing.append(item)

    if missing:

        return (
            False,
            scenario,
            missing
        )

    return (
        True,
        scenario,
        []
    )


# ============================================================
# DEM LOADING
# ============================================================

def load_dem(dem_path):

    dem_path = Path(
        dem_path
    )

    if not dem_path.exists():

        raise FileNotFoundError(
            f"DEM file not found: {dem_path}"
        )

    with rasterio.open(
        dem_path
    ) as src:

        dem = src.read(
            1
        ).astype(
            np.float64
        )

        profile = src.profile.copy()

        transform = src.transform

        bounds = src.bounds

        nodata = src.nodata

    if nodata is not None:

        invalid = (
            dem == nodata
        )

        dem[invalid] = np.nan

    dem[
        ~np.isfinite(dem)
    ] = np.nan

    if not np.any(
        np.isfinite(dem)
    ):

        raise ValueError(
            "DEM contains no valid elevation cells."
        )

    return (
        dem,
        profile,
        transform,
        bounds
    )


# ============================================================
# TERRAIN PROCESSING
# ============================================================

def calculate_terrain_properties(
    dem,
    transform
):

    dx = abs(
        transform.a
    )

    dy = abs(
        transform.e
    )

    valid = np.isfinite(
        dem
    )

    if not np.any(valid):

        raise ValueError(
            "No valid DEM cells."
        )

    filled = dem.copy()

    mean_elevation = float(
        np.nanmean(
            filled
        )
    )

    filled[
        ~np.isfinite(filled)
    ] = mean_elevation

    dz_dy, dz_dx = np.gradient(
        filled,
        dy,
        dx
    )

    slope = np.sqrt(
        dz_dx ** 2
        +
        dz_dy ** 2
    )

    return (
        dx,
        dy,
        slope
    )


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
    g=9.81
):

    eps = 1.0e-8

    u_l = hu_l / max(
        h_l,
        eps
    )

    v_l = hv_l / max(
        h_l,
        eps
    )

    u_r = hu_r / max(
        h_r,
        eps
    )

    v_r = hv_r / max(
        h_r,
        eps
    )

    c_l = math.sqrt(
        g * max(
            h_l,
            0.0
        )
    )

    c_r = math.sqrt(
        g * max(
            h_r,
            0.0
        )
    )

    s_l = min(
        u_l - c_l,
        u_r - c_r
    )

    s_r = max(
        u_l + c_l,
        u_r + c_r
    )

    f_l = np.array(
        [
            hu_l,
            hu_l * u_l
            + 0.5 * g * h_l * h_l,
            hu_l * v_l
        ],
        dtype=np.float64
    )

    f_r = np.array(
        [
            hu_r,
            hu_r * u_r,
            hu_r * v_r
            + 0.5 * g * h_r * h_r
        ],
        dtype=np.float64
    )

    q_l = np.array(
        [
            h_l,
            hu_l,
            hv_l
        ],
        dtype=np.float64
    )

    q_r = np.array(
        [
            h_r,
            hu_r,
            hv_r
        ],
        dtype=np.float64
    )

    if s_l >= 0:

        return f_l

    if s_r <= 0:

        return f_r

    denominator = (
        s_r - s_l
    )

    if abs(
        denominator
    ) < eps:

        return 0.5 * (
            f_l + f_r
        )

    return (
        s_r * f_l
        - s_l * f_r
        + s_l * s_r
        * (q_r - q_l)
    ) / denominator


# ============================================================
# APPLY POSITIVITY
# ============================================================

def enforce_positivity(
    h,
    hu,
    hv,
    minimum_depth=1.0e-6
):

    dry = (
        ~np.isfinite(h)
        |
        (h < minimum_depth)
    )

    h[dry] = 0.0
    hu[dry] = 0.0
    hv[dry] = 0.0

    return (
        h,
        hu,
        hv
    )


# ============================================================
# MANNING FRICTION
# ============================================================

def apply_manning_friction(
    h,
    hu,
    hv,
    dt,
    manning_n=0.035,
    g=9.81
):

    eps = 1.0e-8

    wet = (
        h > eps
    )

    velocity_sq = np.zeros_like(
        h,
        dtype=np.float64
    )

    velocity_sq[wet] = (
        hu[wet] ** 2
        +
        hv[wet] ** 2
    ) / (
        h[wet] ** 2
    )

    speed = np.sqrt(
        velocity_sq
    )

    friction = np.zeros_like(
        h,
        dtype=np.float64
    )

    friction[wet] = (
        g
        * manning_n ** 2
        * speed[wet]
        /
        np.maximum(
            h[wet] ** (4.0 / 3.0),
            eps
        )
    )

    hu[wet] -= (
        friction[wet]
        * hu[wet]
        * dt
    )

    hv[wet] -= (
        friction[wet]
        * hv[wet]
        * dt
    )

    return (
        hu,
        hv
    )


# ============================================================
# CFL TIME STEP
# ============================================================

def calculate_cfl_timestep(
    h,
    hu,
    hv,
    dx,
    dy,
    cfl=0.45,
    g=9.81,
    minimum_dt=0.01,
    maximum_dt=10.0
):

    eps = 1.0e-8

    wet = (
        h > eps
    )

    if not np.any(wet):

        return maximum_dt

    u = np.zeros_like(
        h
    )

    v = np.zeros_like(
        h
    )

    u[wet] = (
        hu[wet]
        /
        h[wet]
    )

    v[wet] = (
        hv[wet]
        /
        h[wet]
    )

    wave_speed = np.sqrt(
        g
        *
        np.maximum(
            h,
            0.0
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

    rate_x = np.nanmax(
        sx[wet]
    ) / max(
        dx,
        eps
    )

    rate_y = np.nanmax(
        sy[wet]
    ) / max(
        dy,
        eps
    )

    maximum_rate = max(
        rate_x,
        rate_y
    )

    if maximum_rate <= eps:

        return maximum_dt

    dt = (
        cfl
        /
        maximum_rate
    )

    return float(
        np.clip(
            dt,
            minimum_dt,
            maximum_dt
        )
    )


# ============================================================
# ONE X-DIRECTION HLL UPDATE
# ============================================================

def x_flux_update(
    h,
    hu,
    hv,
    dx,
    dt
):

    rows, cols = h.shape

    flux_h = np.zeros(
        (rows, cols + 1),
        dtype=np.float64
    )

    flux_hu = np.zeros(
        (rows, cols + 1),
        dtype=np.float64
    )

    flux_hv = np.zeros(
        (rows, cols + 1),
        dtype=np.float64
    )

    for i in range(rows):

        for j in range(
            1,
            cols
        ):

            flx = hll_flux(
                h[i, j - 1],
                hu[i, j - 1],
                hv[i, j - 1],

                h[i, j],
                hu[i, j],
                hv[i, j]
            )

            flux_h[
                i,
                j
            ] = flx[0]

            flux_hu[
                i,
                j
            ] = flx[1]

            flux_hv[
                i,
                j
            ] = flx[2]

    factor = (
        dt / dx
    )

    h_new = h.copy()
    hu_new = hu.copy()
    hv_new = hv.copy()

    h_new -= factor * (
        flux_h[:, 1:]
        -
        flux_h[:, :-1]
    )

    hu_new -= factor * (
        flux_hu[:, 1:]
        -
        flux_hu[:, :-1]
    )

    hv_new -= factor * (
        flux_hv[:, 1:]
        -
        flux_hv[:, :-1]
    )

    return (
        h_new,
        hu_new,
        hv_new
    )


# ============================================================
# ONE Y-DIRECTION HLL UPDATE
# ============================================================

def y_flux_update(
    h,
    hu,
    hv,
    dy,
    dt
):

    rows, cols = h.shape

    flux_h = np.zeros(
        (rows + 1, cols),
        dtype=np.float64
    )

    flux_hu = np.zeros(
        (rows + 1, cols),
        dtype=np.float64
    )

    flux_hv = np.zeros(
        (rows + 1, cols),
        dtype=np.float64
    )

    for i in range(
        1,
        rows
    ):

        for j in range(cols):

            flx = hll_flux(
                h[i - 1, j],
                hv[i - 1, j],
                hu[i - 1, j],

                h[i, j],
                hv[i, j],
                hu[i, j]
            )

            flux_h[
                i,
                j
            ] = flx[0]

            flux_hu[
                i,
                j
            ] = flx[2]

            flux_hv[
                i,
                j
            ] = flx[1]

    factor = (
        dt / dy
    )

    h_new = h.copy()
    hu_new = hu.copy()
    hv_new = hv.copy()

    h_new -= factor * (
        flux_h[1:, :]
        -
        flux_h[:-1, :]
    )

    hu_new -= factor * (
        flux_hu[1:, :]
        -
        flux_hu[:-1, :]
    )

    hv_new -= factor * (
        flux_hv[1:, :]
        -
        flux_hv[:-1, :]
    )

    return (
        h_new,
        hu_new,
        hv_new
    )


# ============================================================
# TERRAIN SOURCE TERM
# ============================================================

def apply_bed_slope_source(
    h,
    hu,
    hv,
    dem,
    dx,
    dy,
    dt,
    g=9.81
):

    filled = dem.copy()

    valid = np.isfinite(
        filled
    )

    if not np.any(valid):

        return (
            hu,
            hv
        )

    mean_elevation = float(
        np.nanmean(
            filled
        )
    )

    filled[
        ~valid
    ] = mean_elevation

    dz_dy, dz_dx = np.gradient(
        filled,
        dy,
        dx
    )

    wet = (
        h > 1.0e-6
    )

    hu[wet] -= (
        g
        * h[wet]
        * dz_dx[wet]
        * dt
    )

    hv[wet] -= (
        g
        * h[wet]
        * dz_dy[wet]
        * dt
    )

    return (
        hu,
        hv
    )


# ============================================================
# VELOCITY
# ============================================================

def calculate_velocity(
    h,
    hu,
    hv
):

    eps = 1.0e-8

    u = np.zeros_like(
        h,
        dtype=np.float64
    )

    v = np.zeros_like(
        h,
        dtype=np.float64
    )

    wet = (
        h > eps
    )

    u[wet] = (
        hu[wet]
        /
        h[wet]
    )

    v[wet] = (
        hv[wet]
        /
        h[wet]
    )

    speed = np.sqrt(
        u ** 2
        +
        v ** 2
    )

    return (
        u,
        v,
        speed
    )


# ============================================================
# SAVE RASTER
# ============================================================

def save_raster(
    path,
    array,
    profile
):

    output_profile = (
        profile.copy()
    )

    output_profile.update(
        dtype="float32",
        count=1,
        compress="deflate",
        predictor=2,
        nodata=-9999.0
    )

    output = np.asarray(
        array,
        dtype=np.float32
    )

    output[
        ~np.isfinite(output)
    ] = -9999.0

    with rasterio.open(
        path,
        "w",
        **output_profile
    ) as dst:

        dst.write(
            output,
            1
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print(
        "=" * 70
    )
    print(
        "NEERAKSH 2D SHALLOW-WATER SOLVER"
    )
    print(
        "=" * 70
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # ========================================================
    # CONFIGURATION
    # ========================================================

    if not CONFIG_FILE.exists():

        raise FileNotFoundError(
            f"Solver configuration missing: {CONFIG_FILE}"
        )

    config = load_json(
        CONFIG_FILE
    )

    # ========================================================
    # ENGINEERING PROVENANCE VALIDATION
    # ========================================================

    print()
    print(
        "ENGINEERING VALIDATION"
    )
    print(
        "-" * 50
    )

    engineering_input = (
        engineering_validator.INPUT_FILE
    )

    if not engineering_input.exists():

        status = {

            "status":
                "BLOCKED_VALIDATOR_INPUT_MISSING",

            "simulation_allowed":
                False,

            "solver":
                "NEERAKSH_2D_HLL",

            "reason":
                "Engineering scenario definition is missing.",

            "fabricated_values":
                False
        }

        status_file = (
            OUTPUT_DIR
            /
            "solver_execution_status.json"
        )

        save_json(
            status_file,
            status
        )

        print(
            "BLOCKED - engineering scenario definition missing."
        )

        print(
            "\nSaved:"
        )

        print(
            status_file
        )

        return

    engineering_data = (
        engineering_validator.load_json(
            engineering_input
        )
    )

    engineering_result = (
        engineering_validator.validate(
            engineering_data
        )
    )

    if not engineering_result[
        "simulation_allowed"
    ]:

        print(
            "BLOCKED - engineering scenario "
            "has not been verified."
        )

        errors = (
            engineering_result.get(
                "errors",
                []
            )
        )

        if errors:

            for error in errors:

                print(
                    "Missing/Invalid:",
                    error
                )

        else:

            print(
                "No verified breach parameters "
                "are available."
            )

        print()
        print(
            "No flood simulation will be generated."
        )

        status = {

            "status":
                "BLOCKED_ENGINEERING_VALIDATION",

            "simulation_allowed":
                False,

            "engineering_validation":
                engineering_result,

            "solver":
                "NEERAKSH_2D_HLL",

            "equations":
                "2D shallow-water equations",

            "fabricated_values":
                False
        }

        status_file = (
            OUTPUT_DIR
            /
            "solver_execution_status.json"
        )

        save_json(
            status_file,
            status
        )

        print()
        print(
            "Saved:"
        )

        print(
            status_file
        )

        return

    print(
        "Engineering validation: PASSED"
    )

    # ========================================================
    # EXISTING SCENARIO VALIDATION
    # ========================================================

    print()
    print(
        "SCENARIO STATUS"
    )
    print(
        "-" * 50
    )

    ready, scenario, missing = (
        validate_scenario(
            config
        )
    )

    if not ready:

        print(
            "BLOCKED - breach scenario is incomplete."
        )

        for item in missing:

            print(
                "Missing:",
                item
            )

        print()
        print(
            "No flood simulation will be generated."
        )

        status = {

            "status":
                "BLOCKED_MISSING_BREACH_PARAMETERS",

            "simulation_allowed":
                False,

            "missing_parameters":
                missing,

            "solver":
                "NEERAKSH_2D_HLL",

            "equations":
                "2D shallow-water equations",

            "fabricated_values":
                False
        }

        status_file = (
            OUTPUT_DIR
            /
            "solver_execution_status.json"
        )

        save_json(
            status_file,
            status
        )

        print()
        print(
            "Saved:"
        )

        print(
            status_file
        )

        return

    print(
        "Scenario validation: PASSED"
    )

    # ========================================================
    # LOAD DEM
    # ========================================================

    dem_path = Path(
        config["inputs"]["dem"]
    )

    print()
    print(
        "HYDRAULIC TERRAIN"
    )
    print(
        "-" * 50
    )

    print(
        "DEM:",
        dem_path
    )

    dem, profile, transform, bounds = (
        load_dem(
            dem_path
        )
    )

    dx = abs(
        transform.a
    )

    dy = abs(
        transform.e
    )

    print(
        "Rows:",
        dem.shape[0]
    )

    print(
        "Columns:",
        dem.shape[1]
    )

    print(
        "Cell width:",
        dx
    )

    print(
        "Cell height:",
        dy
    )

    print(
        "Minimum elevation:",
        float(
            np.nanmin(
                dem
            )
        )
    )

    print(
        "Maximum elevation:",
        float(
            np.nanmax(
                dem
            )
        )
    )

    # ========================================================
    # TERRAIN
    # ========================================================

    (
        terrain_dx,
        terrain_dy,
        slope
    ) = calculate_terrain_properties(
        dem,
        transform
    )

    # ========================================================
    # NUMERICAL PARAMETERS
    # ========================================================

    solver_settings = (
        config.get(
            "solver",
            {}
        )
    )

    gravity = float(
        solver_settings.get(
            "gravity",
            9.81
        )
    )

    manning_n = float(
        solver_settings.get(
            "manning_n",
            0.035
        )
    )

    cfl = float(
        solver_settings.get(
            "cfl",
            0.45
        )
    )

    simulation_seconds = float(
        solver_settings.get(
            "simulation_seconds",
            60.0
        )
    )

    # ========================================================
    # INITIAL WATER DEPTH
    # ========================================================
    #
    # IMPORTANT:
    # A verified hydraulic water-surface elevation is required.
    #
    # We DO NOT derive one from the current TN gauge unless
    # the vertical datum transformation has independently been
    # verified.
    #
    # Therefore this block will stop if the scenario does not
    # contain a verified hydraulic initial elevation.
    # ========================================================

    initial_water_level_m = (
        get_nested(
            scenario,
            "reservoir_initial_condition.level_m.value"
        )
    )

    if initial_water_level_m is None:

        print()
        print(
            "BLOCKED - hydraulic initial water-surface "
            "elevation is not verified."
        )

        status = {

            "status":
                "BLOCKED_MISSING_VERIFIED_HYDRAULIC_INITIAL_LEVEL",

            "simulation_allowed":
                False,

            "reason":
                "A hydraulic water-surface elevation with "
                "verified vertical datum is required.",

            "current_government_gauge_ft":
                get_nested(
                    scenario,
                    "reservoir_initial_condition.level_ft.value"
                ),

            "fabricated_values":
                False,

            "solver":
                "NEERAKSH_2D_HLL"
        }

        status_file = (
            OUTPUT_DIR
            /
            "solver_execution_status.json"
        )

        save_json(
            status_file,
            status
        )

        print()
        print(
            "Saved:"
        )

        print(
            status_file
        )

        return

    initial_water_level_m = float(
        initial_water_level_m
    )

    # ========================================================
    # INITIAL WATER DEPTH
    # ========================================================

    depth = (
        initial_water_level_m
        -
        dem
    )

    depth[
        ~np.isfinite(depth)
    ] = 0.0

    depth = np.maximum(
        depth,
        0.0
    )

    hu = np.zeros_like(
        depth,
        dtype=np.float64
    )

    hv = np.zeros_like(
        depth,
        dtype=np.float64
    )

    (
        depth,
        hu,
        hv
    ) = enforce_positivity(
        depth,
        hu,
        hv
    )

    # ========================================================
    # INITIAL STATE
    # ========================================================

    initial_volume = float(
        np.nansum(
            depth
        )
        *
        terrain_dx
        *
        terrain_dy
    )

    print()
    print(
        "INITIAL HYDRAULIC STATE"
    )
    print(
        "-" * 50
    )

    print(
        "Initial water level:",
        initial_water_level_m,
        "m"
    )

    print(
        "Initial water volume:",
        initial_volume,
        "m3"
    )

    # ========================================================
    # NUMERICAL SOLVER
    # ========================================================

    print()
    print(
        "2D SOLVER"
    )
    print(
        "-" * 50
    )

    print(
        "Method: Finite Volume"
    )

    print(
        "Flux: HLL"
    )

    print(
        "Equations: 2D shallow-water equations"
    )

    print(
        "Gravity:",
        gravity
    )

    print(
        "Manning n:",
        manning_n
    )

    print(
        "CFL:",
        cfl
    )

    print(
        "Simulation duration:",
        simulation_seconds,
        "seconds"
    )

    # ========================================================
    # SOLVER LOOP
    # ========================================================

    current_time = 0.0

    step = 0

    maximum_depth = depth.copy()

    maximum_velocity = np.zeros_like(
        depth
    )

    arrival_time = np.full(
        depth.shape,
        np.nan,
        dtype=np.float64
    )

    # --------------------------------------------------------
    # IMPORTANT
    #
    # A verified breach hydrograph must be connected here.
    # The current scenario architecture does not yet provide
    # an approved breach inflow hydrograph.
    #
    # Therefore we do not inject an artificial source.
    # --------------------------------------------------------

    breach_hydrograph = scenario.get(
        "breach_hydrograph",
        None
    )

    if breach_hydrograph is None:

        print()
        print(
            "BLOCKED - verified breach hydrograph "
            "is not available."
        )

        status = {

            "status":
                "BLOCKED_MISSING_BREACH_HYDROGRAPH",

            "simulation_allowed":
                False,

            "reason":
                "The 2D solver requires a verified breach "
                "inflow hydrograph. No artificial hydrograph "
                "is generated.",

            "solver":
                "NEERAKSH_2D_HLL",

            "fabricated_values":
                False
        }

        status_file = (
            OUTPUT_DIR
            /
            "solver_execution_status.json"
        )

        save_json(
            status_file,
            status
        )

        print()
        print(
            "Saved:"
        )

        print(
            status_file
        )

        return

    # ========================================================
    # FULL NUMERICAL TIME LOOP
    # ========================================================

    while (
        current_time
        <
        simulation_seconds
    ):

        dt = calculate_cfl_timestep(
            depth,
            hu,
            hv,
            terrain_dx,
            terrain_dy,
            cfl=cfl,
            g=gravity,
            minimum_dt=0.001,
            maximum_dt=5.0
        )

        remaining = (
            simulation_seconds
            -
            current_time
        )

        dt = min(
            dt,
            remaining
        )

        # ----------------------------------------------------
        # Breach inflow
        # ----------------------------------------------------

        discharge = 0.0

        if isinstance(
            breach_hydrograph,
            list
        ):

            for point in (
                breach_hydrograph
            ):

                t = float(
                    point["time_s"]
                )

                if t <= current_time:

                    discharge = float(
                        point["discharge_m3s"]
                    )

        # ----------------------------------------------------
        # Numerical fluxes
        # ----------------------------------------------------

        (
            depth_x,
            hu_x,
            hv_x
        ) = x_flux_update(
            depth,
            hu,
            hv,
            terrain_dx,
            dt
        )

        (
            depth_y,
            hu_y,
            hv_y
        ) = y_flux_update(
            depth_x,
            hu_x,
            hv_x,
            terrain_dy,
            dt
        )

        depth = depth_y
        hu = hu_y
        hv = hv_y

        # ----------------------------------------------------
        # Terrain source
        # ----------------------------------------------------

        (
            hu,
            hv
        ) = apply_bed_slope_source(
            depth,
            hu,
            hv,
            dem,
            terrain_dx,
            terrain_dy,
            dt,
            g=gravity
        )

        # ----------------------------------------------------
        # Manning friction
        # ----------------------------------------------------

        (
            hu,
            hv
        ) = apply_manning_friction(
            depth,
            hu,
            hv,
            dt,
            manning_n=manning_n,
            g=gravity
        )

        # ----------------------------------------------------
        # Positivity
        # ----------------------------------------------------

        (
            depth,
            hu,
            hv
        ) = enforce_positivity(
            depth,
            hu,
            hv
        )

        # ----------------------------------------------------
        # Velocity
        # ----------------------------------------------------

        (
            velocity_u,
            velocity_v,
            velocity_speed
        ) = calculate_velocity(
            depth,
            hu,
            hv
        )

        # ----------------------------------------------------
        # Maximum values
        # ----------------------------------------------------

        maximum_depth = np.maximum(
            maximum_depth,
            depth
        )

        maximum_velocity = np.maximum(
            maximum_velocity,
            velocity_speed
        )

        # ----------------------------------------------------
        # Arrival time
        # ----------------------------------------------------

        newly_wet = (
            (depth > 0.01)
            &
            ~np.isfinite(
                arrival_time
            )
        )

        arrival_time[
            newly_wet
        ] = (
            current_time
            +
            dt
        )

        # ----------------------------------------------------
        # Advance
        # ----------------------------------------------------

        current_time += dt

        step += 1

        if step % 10 == 0:

            print(
                f"Step {step:6d} | "
                f"Time {current_time:10.3f} s | "
                f"Max depth "
                f"{np.nanmax(depth):10.4f} m | "
                f"Max velocity "
                f"{np.nanmax(velocity_speed):10.4f} m/s"
            )

    # ========================================================
    # FINAL RESULTS
    # ========================================================

    (
        velocity_u,
        velocity_v,
        velocity_speed
    ) = calculate_velocity(
        depth,
        hu,
        hv
    )

    water_surface_elevation = (
        dem
        +
        depth
    )

    print()
    print(
        "=" * 70
    )

    print(
        "SIMULATION COMPLETED"
    )

    print(
        "=" * 70
    )

    print(
        "Time steps:",
        step
    )

    print(
        "Final time:",
        current_time,
        "s"
    )

    print(
        "Maximum flood depth:",
        float(
            np.nanmax(
                maximum_depth
            )
        ),
        "m"
    )

    print(
        "Maximum velocity:",
        float(
            np.nanmax(
                maximum_velocity
            )
        ),
        "m/s"
    )

    # ========================================================
    # OUTPUT RASTERS
    # ========================================================

    maximum_depth_file = (
        OUTPUT_DIR
        /
        "maximum_flood_depth_m.tif"
    )

    maximum_velocity_file = (
        OUTPUT_DIR
        /
        "maximum_velocity_ms.tif"
    )

    final_depth_file = (
        OUTPUT_DIR
        /
        "final_flood_depth_m.tif"
    )

    final_wse_file = (
        OUTPUT_DIR
        /
        "final_water_surface_elevation_m.tif"
    )

    arrival_time_file = (
        OUTPUT_DIR
        /
        "arrival_time_s.tif"
    )

    save_raster(
        maximum_depth_file,
        maximum_depth,
        profile
    )

    save_raster(
        maximum_velocity_file,
        maximum_velocity,
        profile
    )

    save_raster(
        final_depth_file,
        depth,
        profile
    )

    save_raster(
        final_wse_file,
        water_surface_elevation,
        profile
    )

    save_raster(
        arrival_time_file,
        arrival_time,
        profile
    )

    # ========================================================
    # EXECUTION METADATA
    # ========================================================

    result = {

        "status":
            "COMPLETED",

        "simulation_allowed":
            True,

        "solver":
            "NEERAKSH_2D_HLL",

        "method":
            "Finite Volume HLL",

        "equations":
            "2D shallow-water equations",

        "gravity_m_s2":
            gravity,

        "manning_n":
            manning_n,

        "cfl":
            cfl,

        "grid":

            {
                "rows":
                    int(
                        dem.shape[0]
                    ),

                "columns":
                    int(
                        dem.shape[1]
                    ),

                "dx_m":
                    float(
                        terrain_dx
                    ),

                "dy_m":
                    float(
                        terrain_dy
                    )
            },

        "simulation":

            {
                "duration_s":
                    float(
                        simulation_seconds
                    ),

                "time_steps":
                    int(
                        step
                    )
            },

        "results":

            {
                "maximum_depth_m":
                    float(
                        np.nanmax(
                            maximum_depth
                        )
                    ),

                "maximum_velocity_ms":
                    float(
                        np.nanmax(
                            maximum_velocity
                        )
                    )
            },

        "outputs":

            {
                "maximum_depth":
                    str(
                        maximum_depth_file
                    ),

                "maximum_velocity":
                    str(
                        maximum_velocity_file
                    ),

                "final_depth":
                    str(
                        final_depth_file
                    ),

                "final_water_surface":
                    str(
                        final_wse_file
                    ),

                "arrival_time":
                    str(
                        arrival_time_file
                    )
            },

        "fabricated_values":
            False
    }

    status_file = (
        OUTPUT_DIR
        /
        "solver_execution_status.json"
    )

    save_json(
        status_file,
        result
    )

    print()
    print(
        "Output files:"
    )

    print(
        maximum_depth_file
    )

    print(
        maximum_velocity_file
    )

    print(
        final_depth_file
    )

    print(
        final_wse_file
    )

    print(
        arrival_time_file
    )

    print()
    print(
        "Execution status:"
    )

    print(
        status_file
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except Exception as exc:

        print()
        print(
            "=" * 70
        )

        print(
            "NEERAKSH SOLVER ERROR"
        )

        print(
            "=" * 70
        )

        print(
            str(exc)
        )

        print()
        print(
            traceback.format_exc()
        )

        error_status = {

            "status":
                "ERROR",

            "simulation_allowed":
                False,

            "error":
                str(exc),

            "solver":
                "NEERAKSH_2D_HLL",

            "fabricated_values":
                False
        }

        error_file = (
            OUTPUT_DIR
            /
            "solver_error.json"
        )

        save_json(
            error_file,
            error_status
        )

        print(
            "Error report:"
        )

        print(
            error_file
        )