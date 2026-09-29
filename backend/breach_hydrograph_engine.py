import csv
import json
from pathlib import Path
from datetime import datetime, timezone

import numpy as np


# ============================================================
# NEERAKSH — METTUR AUTOMATIC HYPOTHETICAL HYDROGRAPH
# ============================================================
#
# IMPORTANT
# ------------------------------------------------------------
# This engine is for a HYPOTHETICAL scenario only.
#
# It does NOT predict an actual Mettur dam failure.
#
# The breach geometry comes from the existing
# METTUR_SCREENING_BASE scenario.
#
# The breach reference elevation is derived automatically
# from the hydraulic initial WSE for scenario execution.
#
# This derived elevation is NOT a verified dam cross-section
# or verified breach invert.
#
# ============================================================


BASE = Path(r"C:\NEERAKSH-1")


# ============================================================
# INPUTS
# ============================================================

SCENARIO_FILE = (
    BASE
    / "simulations"
    / "inputs"
    / "mettur"
    / "hypothetical_user_scenario.json"
)


HYDRAULIC_FILE = (
    BASE
    / "simulations"
    / "outputs"
    / "mettur"
    / "reservoir_state"
    / "mettur_hydraulic_initialization.json"
)


RESERVOIR_FILE = (
    BASE
    / "simulations"
    / "outputs"
    / "mettur"
    / "reservoir_state"
    / "mettur_reservoir_state.json"
)


OUTPUT_DIR = (
    BASE
    / "simulations"
    / "outputs"
    / "mettur"
    / "hydrograph"
)


OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


STATUS_FILE = (
    OUTPUT_DIR
    / "hydrograph_status.json"
)


OUTPUT_CSV = (
    OUTPUT_DIR
    / "mettur_breach_hydrograph.csv"
)


# ============================================================
# CONSTANTS
# ============================================================

G = 9.80665

C1 = 1.70
C2 = 1.35

MCFT_TO_MCM = 0.028316846592

MCM_TO_M3 = 1_000_000.0


# ============================================================
# JSON
# ============================================================

def load_json(path):

    if not path.exists():

        raise FileNotFoundError(
            f"File not found:\n{path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8-sig"
    ) as f:

        return json.load(f)


def save_json(
    path,
    data
):

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )


# ============================================================
# HYDRAULIC INITIAL CONDITION
# ============================================================

def load_hydraulic_initial_condition():

    data = load_json(
        HYDRAULIC_FILE
    )

    status = data.get(
        "status"
    )

    allowed = data.get(
        "simulation_allowed",
        False
    )

    elevation = data.get(
        "hydraulic_water_surface_elevation_m"
    )

    storage = data.get(
        "hydraulic_initial_storage_mcm"
    )

    # Current project initializer uses:
    #
    # READY_FROM_STORAGE_STAGE_CURVE
    #
    # rather than the old READY status.

    accepted_statuses = {
        "READY",
        "READY_FROM_STORAGE_STAGE_CURVE"
    }

    if status not in accepted_statuses:

        raise RuntimeError(
            "Hydraulic initialization is not ready.\n"
            f"Status: {status}"
        )

    if allowed is not True:

        raise RuntimeError(
            "Hydraulic initialization does not allow "
            "simulation."
        )

    if elevation is None:

        raise RuntimeError(
            "Hydraulic WSE is missing."
        )

    if storage is None:

        raise RuntimeError(
            "Hydraulic storage is missing."
        )

    return {

        "status":
            status,

        "wse_m":
            float(elevation),

        "storage_mcm":
            float(storage)
    }


# ============================================================
# SCENARIO
# ============================================================

def load_hypothetical_scenario():

    scenario = load_json(
        SCENARIO_FILE
    )

    mode = (
        scenario
        .get("scenario", {})
        .get("mode")
    )

    if mode != "AUTOMATIC_HYPOTHETICAL":

        raise RuntimeError(
            "Scenario is not AUTOMATIC_HYPOTHETICAL."
        )

    geometry = (
        scenario
        .get("failure", {})
        .get("breach_geometry", {})
    )

    width = geometry.get(
        "width_m"
    )

    formation = geometry.get(
        "formation_time_hr"
    )

    side_slope = geometry.get(
        "side_slope_h_to_v"
    )

    if width is None:

        raise RuntimeError(
            "Hypothetical breach width is missing."
        )

    if formation is None:

        raise RuntimeError(
            "Hypothetical formation time is missing."
        )

    if side_slope is None:

        side_slope = 0.0

    return {

        "scenario":
            scenario,

        "width_m":
            float(width),

        "formation_time_hr":
            float(formation),

        "side_slope_h_to_v":
            float(side_slope)
    }


# ============================================================
# RESERVOIR OBSERVATION
# ============================================================

def load_reservoir_observation():

    data = load_json(
        RESERVOIR_FILE
    )

    return {

        "level_ft":
            data.get(
                "current_level_ft"
            ),

        "storage_mcft":
            data.get(
                "current_storage_mcft"
            ),

        "inflow_cusecs":
            data.get(
                "current_inflow_cusecs"
            ),

        "outflow_cusecs":
            data.get(
                "current_outflow_cusecs"
            ),

        "fetched_at":
            data.get(
                "fetched_at"
            )
    }


# ============================================================
# AUTOMATIC SCENARIO BREACH ELEVATION
# ============================================================

def derive_hypothetical_breach_elevation(
    hydraulic_wse_m
):

    # --------------------------------------------------------
    # IMPORTANT
    #
    # There is no verified Mettur breach invert in the
    # available project data.
    #
    # Therefore this is explicitly a scenario assumption.
    #
    # We use a small head below the initial WSE so that the
    # hypothetical breach produces a non-zero hydraulic head.
    #
    # This is NOT a physical Mettur breach elevation.
    # --------------------------------------------------------

    scenario_head_m = 5.0

    breach_invert = (
        hydraulic_wse_m
        -
        scenario_head_m
    )

    return {

        "breach_invert_m":
            breach_invert,

        "assumed_head_m":
            scenario_head_m,

        "status":
            "AUTOMATIC_SCENARIO_ASSUMPTION",

        "verified":
            False,

        "reason":
            (
                "No verified Mettur breach invert is "
                "available. A 5 m hydraulic-head "
                "assumption is used only to execute "
                "the hypothetical demonstration."
            )
    }


# ============================================================
# BREACH WIDTH
# ============================================================

def breach_width(
    time_s,
    formation_time_hr,
    final_width_m
):

    formation_seconds = (
        formation_time_hr
        * 3600.0
    )

    if time_s <= 0:

        return 0.0

    if time_s >= formation_seconds:

        return final_width_m

    fraction = (
        time_s
        /
        formation_seconds
    )

    return (
        final_width_m
        *
        fraction
    )


# ============================================================
# BREACH DISCHARGE
# ============================================================

def breach_discharge(
    water_level_m,
    breach_invert_m,
    width_m,
    side_slope_h_to_v
):

    head = (
        water_level_m
        -
        breach_invert_m
    )

    if head <= 0:

        return 0.0

    discharge = (

        C1
        *
        width_m
        *
        head ** 1.5

        +

        C2
        *
        side_slope_h_to_v
        *
        head ** 2.5
    )

    return float(
        max(
            discharge,
            0.0
        )
    )


# ============================================================
# RESERVOIR ROUTING
# ============================================================

def route_reservoir(
    initial_wse,
    initial_storage_mcm,
    breach_invert,
    width_final,
    formation_time_hr,
    side_slope,
    simulation_time_s=3600,
    dt_s=5
):

    # --------------------------------------------------------
    # This is a scenario hydrograph.
    #
    # The available project stage-storage data is not being
    # replaced or fabricated.
    #
    # For this automatic demonstration, reservoir storage is
    # reduced by the computed breach discharge.
    # --------------------------------------------------------

    times = np.arange(
        0.0,
        simulation_time_s + dt_s,
        dt_s
    )

    current_storage_m3 = (
        initial_storage_mcm
        *
        MCM_TO_M3
    )

    current_wse = float(
        initial_wse
    )

    rows = []

    cumulative_volume = 0.0

    peak_q = 0.0

    for t in times:

        width = breach_width(
            t,
            formation_time_hr,
            width_final
        )

        q = breach_discharge(
            current_wse,
            breach_invert,
            width,
            side_slope
        )

        volume_step = (
            q
            *
            dt_s
        )

        available_volume = max(
            current_storage_m3,
            0.0
        )

        actual_volume = min(
            volume_step,
            available_volume
        )

        current_storage_m3 = (
            current_storage_m3
            -
            actual_volume
        )

        cumulative_volume += (
            actual_volume
        )

        # Simple scenario-only water-level decline.
        #
        # This does not replace the full CWC stage-storage
        # routing model.

        storage_fraction = (

            current_storage_m3
            /
            max(
                initial_storage_mcm
                * MCM_TO_M3,
                1.0
            )
        )

        storage_fraction = max(
            0.0,
            min(
                1.0,
                storage_fraction
            )
        )

        current_wse = (

            breach_invert
            +
            (
                initial_wse
                -
                breach_invert
            )
            *
            storage_fraction
        )

        peak_q = max(
            peak_q,
            q
        )

        rows.append({

            "time_s":
                float(t),

            "time_min":
                float(t / 60.0),

            "breach_width_m":
                float(width),

            "water_surface_elevation_m":
                float(current_wse),

            "breach_head_m":
                float(
                    max(
                        current_wse
                        -
                        breach_invert,
                        0.0
                    )
                ),

            "discharge_m3s":
                float(q),

            "storage_m3":
                float(
                    current_storage_m3
                ),

            "cumulative_released_volume_m3":
                float(
                    cumulative_volume
                )
        })

        if current_storage_m3 <= 0:

            break

    return rows, peak_q, cumulative_volume


# ============================================================
# SAVE CSV
# ============================================================

def save_hydrograph_csv(
    rows
):

    if not rows:

        raise RuntimeError(
            "No hydrograph rows generated."
        )

    fields = list(
        rows[0].keys()
    )

    with open(
        OUTPUT_CSV,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print(
        "NEERAKSH — METTUR AUTOMATIC "
        "HYPOTHETICAL HYDROGRAPH ENGINE"
    )
    print("=" * 70)

    # --------------------------------------------------------
    # Scenario
    # --------------------------------------------------------

    scenario = (
        load_hypothetical_scenario()
    )

    print()
    print(
        "SCENARIO"
    )

    print(
        "-" * 70
    )

    print(
        "Mode: "
        "AUTOMATIC_HYPOTHETICAL"
    )

    print(
        "Failure prediction: "
        "NO"
    )

    # --------------------------------------------------------
    # Hydraulic condition
    # --------------------------------------------------------

    hydraulic = (
        load_hydraulic_initial_condition()
    )

    print()
    print(
        "HYDRAULIC INITIAL CONDITION"
    )

    print(
        "-" * 70
    )

    print(
        f"Status: "
        f"{hydraulic['status']}"
    )

    print(
        f"WSE: "
        f"{hydraulic['wse_m']:.6f} m"
    )

    print(
        f"Storage: "
        f"{hydraulic['storage_mcm']:.6f} MCM"
    )

    # --------------------------------------------------------
    # Reservoir observation
    # --------------------------------------------------------

    observation = (
        load_reservoir_observation()
    )

    print()
    print(
        "GOVERNMENT RESERVOIR OBSERVATION"
    )

    print(
        "-" * 70
    )

    print(
        f"Level: "
        f"{observation['level_ft']} ft"
    )

    print(
        f"Storage: "
        f"{observation['storage_mcft']} M.Cft"
    )

    print(
        f"Inflow: "
        f"{observation['inflow_cusecs']} cusecs"
    )

    print(
        f"Outflow: "
        f"{observation['outflow_cusecs']} cusecs"
    )

    # --------------------------------------------------------
    # Breach scenario
    # --------------------------------------------------------

    breach = (
        derive_hypothetical_breach_elevation(
            hydraulic["wse_m"]
        )
    )

    print()
    print(
        "AUTOMATIC HYPOTHETICAL BREACH"
    )

    print(
        "-" * 70
    )

    print(
        f"Width: "
        f"{scenario['width_m']:.3f} m"
    )

    print(
        f"Formation time: "
        f"{scenario['formation_time_hr']:.3f} hr"
    )

    print(
        f"Side slope: "
        f"{scenario['side_slope_h_to_v']:.3f}:1"
    )

    print(
        f"Derived scenario invert: "
        f"{breach['breach_invert_m']:.6f} m"
    )

    print(
        "Invert status: "
        "AUTOMATIC SCENARIO ASSUMPTION"
    )

    # --------------------------------------------------------
    # Route
    # --------------------------------------------------------

    print()
    print(
        "GENERATING HYDROGRAPH..."
    )

    rows, peak_q, released_volume = (
        route_reservoir(

            initial_wse=
                hydraulic["wse_m"],

            initial_storage_mcm=
                hydraulic["storage_mcm"],

            breach_invert=
                breach["breach_invert_m"],

            width_final=
                scenario["width_m"],

            formation_time_hr=
                scenario["formation_time_hr"],

            side_slope=
                scenario["side_slope_h_to_v"],

            simulation_time_s=
                3600,

            dt_s=
                5
        )
    )

    save_hydrograph_csv(
        rows
    )

    # --------------------------------------------------------
    # Status
    # --------------------------------------------------------

    status = {

        "project":
            "NEERAKSH",

        "dam":
            "Mettur",

        "created_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "status":
            "HYPOTHETICAL_HYDROGRAPH_GENERATED",

        "simulation_allowed":
            True,

        "scenario_mode":
            "AUTOMATIC_HYPOTHETICAL",

        "failure_prediction":
            False,

        "fabricated_values":
            False,

        "hydraulic_initial_condition":
            hydraulic,

        "government_observation":
            observation,

        "breach":

            {

                "width_m":
                    scenario["width_m"],

                "formation_time_hr":
                    scenario[
                        "formation_time_hr"
                    ],

                "side_slope_h_to_v":
                    scenario[
                        "side_slope_h_to_v"
                    ],

                "derived_invert_m":
                    breach[
                        "breach_invert_m"
                    ],

                "invert_status":
                    "AUTOMATIC_SCENARIO_ASSUMPTION",

                "verified":
                    False
            },

        "results":

            {

                "number_of_timesteps":
                    len(rows),

                "peak_discharge_m3s":
                    peak_q,

                "released_volume_m3":
                    released_volume,

                "simulation_duration_s":
                    rows[-1]["time_s"]
            },

        "outputs":

            {

                "hydrograph_csv":
                    str(
                        OUTPUT_CSV
                    ),

                "status_json":
                    str(
                        STATUS_FILE
                    )
            },

        "disclaimer":

            (
                "This is a hypothetical demonstration "
                "hydrograph. The breach invert is an "
                "automatic scenario assumption and is "
                "not a verified Mettur dam failure "
                "parameter. The hydrograph must not "
                "be interpreted as a prediction of "
                "actual dam failure."
            )
    }

    save_json(
        STATUS_FILE,
        status
    )

    # --------------------------------------------------------
    # DISPLAY RESULTS
    # --------------------------------------------------------

    print()
    print(
        "=" * 70
    )

    print(
        "HYDROGRAPH GENERATED"
    )

    print(
        "=" * 70
    )

    print()
    print(
        f"Timesteps: "
        f"{len(rows)}"
    )

    print(
        f"Duration: "
        f"{rows[-1]['time_s']:.1f} s"
    )

    print(
        f"Peak discharge: "
        f"{peak_q:.3f} m3/s"
    )

    print(
        f"Released volume: "
        f"{released_volume:.3f} m3"
    )

    print()
    print(
        "CSV:"
    )

    print(
        OUTPUT_CSV
    )

    print()
    print(
        "STATUS:"
    )

    print(
        STATUS_FILE
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "This is a HYPOTHETICAL scenario."
    )

    print(
        "It is NOT a Mettur failure prediction."
    )

    print()


if __name__ == "__main__":

    main()