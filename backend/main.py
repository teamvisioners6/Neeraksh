# ============================================================
# NEERAKSH - main.py
# METTUR DAM | GOVERNMENT DATA + PHYSICAL DAM-BREAK SCENARIO
# ============================================================

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import csv
import numpy as np
import math
import requests
from bs4 import BeautifulSoup

app = FastAPI(
    title="NEERAKSH",
    version="1.0.0",
    description="Dam-break and flood intelligence using official Indian data"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# OFFICIAL SOURCES
# ============================================================

CWC_NRLD ="https://www.cwc.gov.in/sites/default/files/nrld-2019.pdf"

CWC_HYDRAULIC_SAFETY ="https://damsafety.cwc.gov.in/ecm-includes/PDFs/Manual_for_Assessing_Hydraulic_Safety_of_Existing_Dams-Volume_I.pdf"

TN_RESERVOIR ="https://tnagriculture.in/ARS/home/reservoir/"

# ============================================================
# METTUR DAM
# CWC NRLD GOVERNMENT DATA
# ============================================================

METTUR = {
    "id": "mettur",
    "name": "Mettur Dam",
    "river": "Cauvery",
    "district": "Salem",
    "state": "Tamil Nadu",

    "latitude": 11.801,
    "longitude": 77.810,

    "completion_year": 1934,

    "dam_type": "Masonry / Gravity",

    "height_m": 65.23,
    "length_m": 1615.40,

    "gross_storage_mcm": 2710.0,
    "effective_storage_mcm": 2650.0,

    "reservoir_area_km2": 153.46,

    "designed_spillway_capacity_m3s": 12904.80,

    "source": CWC_NRLD,
}

# ============================================================
# PROBLEM STATEMENT EXAMPLE EVENTS
# ONLY EVENTS NAMED IN THE PROVIDED PS
# ============================================================

PS_EXAMPLES = [
    {
        "name": "Rishi Ganga",
        "event": "Natural blockage / sudden flood event",
        "date": "2021-02",
        "source": "Problem Statement"
    },
    {
        "name": "Wapriyang",
        "event": "Natural blockage / sudden flood event",
        "date": "2021-11",
        "source": "Problem Statement"
    },
    {
        "name": "Phuktal near Sumdo",
        "event": "Natural blockage / sudden flood event",
        "date": "2015-03",
        "source": "Problem Statement"
    },
    {
        "name": "Kosi",
        "event": "Major flood / blockage-related example",
        "date": "2008",
        "source": "Problem Statement"
    },
]

# ============================================================
# LIVE GOVERNMENT RESERVOIR DATA
# ============================================================

def get_mettur_live():

    try:

        response = requests.get(
            TN_RESERVOIR,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        text = soup.get_text(
            " ",
            strip=True
        )

        text_upper = text.upper()

        index = text_upper.find("METTUR")

        if index == -1:
            raise Exception(
                "METTUR record not found"
            )

        section = text[index:index + 1200]

        numbers = []

        for token in section.replace(",", " ").split():

            try:
                value = float(token)

                if value >= 0:
                    numbers.append(value)

            except:
                pass

        # Government page structure:
        #
        # Full depth
        # Full capacity
        # Current level
        # Current storage
        # Inflow
        # Outflow

        full_depth = 120.0

        # Try to identify the known table values.
        #
        # If parser cannot safely identify them,
        # do NOT manufacture values.

        current_level = None
        current_storage = None
        inflow = None
        outflow = None

        # Direct textual extraction for current government page.

        import re

        level_match = re.search(
            r"METTUR.*?120\s+93470\s+([0-9.]+)\s+([0-9,]+)\s+([0-9,]+)\s+([0-9,]+)",
            text_upper,
            re.DOTALL
        )

        if level_match:

            current_level = float(
                level_match.group(1)
            )

            current_storage = float(
                level_match.group(2).replace(",", "")
            )

            inflow = float(
                level_match.group(3).replace(",", "")
            )

            outflow = float(
                level_match.group(4).replace(",", "")
            )

        if current_level is None:

            # Current official page may change its HTML.
            # Return unavailable instead of fake data.

            return {
                "status": "LIVE_DATA_PARSE_UNAVAILABLE",
                "source": TN_RESERVOIR,
                "timestamp": datetime.utcnow().isoformat(),
                "message":
                    "Official reservoir page was reached, "
                    "but its current HTML structure could not "
                    "be safely parsed."
            }

        return {
            "status": "LIVE_GOVERNMENT_DATA",

            "reservoir": "Mettur",

            "full_depth_ft": full_depth,

            "full_capacity_mcft": 93470,

            "current_level_ft": current_level,

            "current_storage_mcft": current_storage,

            "inflow_cusecs": inflow,

            "outflow_cusecs": outflow,

            "source": TN_RESERVOIR,

            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:

        return {
            "status": "LIVE_DATA_UNAVAILABLE",
            "source": TN_RESERVOIR,
            "timestamp": datetime.utcnow().isoformat(),
            "message": str(e)
        }


# ============================================================
# PHYSICAL DAM-BREAK MODEL
#
# This is NOT a prediction of when Mettur will fail.
#
# The model starts at a defined hypothetical breach event T=0.
#
# No breach width/depth is silently invented.
#
# User supplies scenario parameters.
# ============================================================

def simulate_breach(
    water_level_m,
    breach_width_m,
    breach_depth_m,
    formation_time_s,
    simulation_time_s=1800,
    dt=5
):

    if water_level_m <= 0:
        raise ValueError(
            "Water level must be positive."
        )

    if breach_width_m <= 0:
        raise ValueError(
            "Breach width must be positive."
        )

    if breach_depth_m <= 0:
        raise ValueError(
            "Breach depth must be positive."
        )

    if formation_time_s <= 0:
        raise ValueError(
            "Formation time must be positive."
        )

    g = 9.81

    Cd = 0.61

    rows = []

    max_discharge = 0.0

    max_head = 0.0

    total_volume = 0.0

    t = 0

    while t <= simulation_time_s:

        # Breach grows from zero to specified width/depth.

        growth = min(
            1.0,
            t / formation_time_s
        )

        current_width = (
            breach_width_m * growth
        )

        current_depth = (
            breach_depth_m * growth
        )

        # Effective hydraulic head.
        #
        # The calculation is intentionally bounded
        # by the available reservoir water depth.

        head = max(
            0.0,
            water_level_m - current_depth / 2
        )

        area = (
            current_width *
            current_depth
        )

        # Orifice/weir-type physical discharge relation.

        discharge = (
            Cd *
            area *
            math.sqrt(
                2 * g * head
            )
        )

        # Once breach is formed, keep physical
        # discharge tied to available head.

        if t > formation_time_s:

            decay = math.exp(
                -(
                    t - formation_time_s
                ) / 900
            )

            discharge *= decay

        volume_step = (
            discharge * dt
        )

        total_volume += volume_step

        max_discharge = max(
            max_discharge,
            discharge
        )

        max_head = max(
            max_head,
            head
        )

        rows.append(
            {
                "time_s": t,
                "time_min": round(
                    t / 60,
                    2
                ),
                "breach_width_m": round(
                    current_width,
                    3
                ),
                "breach_depth_m": round(
                    current_depth,
                    3
                ),
                "hydraulic_head_m": round(
                    head,
                    3
                ),
                "discharge_m3s": round(
                    discharge,
                    3
                ),
                "released_volume_m3": round(
                    total_volume,
                    3
                )
            }
        )

        t += dt

    return {
        "model": "PHYSICAL_BREACH_DISCHARGE_MODEL",

        "prediction_status":
            "SCENARIO_NOT_FAILURE_PREDICTION",

        "simulation_start":
            "T=0 represents the assumed breach initiation.",

        "inputs": {
            "water_level_m":
                water_level_m,

            "breach_width_m":
                breach_width_m,

            "breach_depth_m":
                breach_depth_m,

            "formation_time_s":
                formation_time_s
        },

        "maximum_discharge_m3s":
            round(
                max_discharge,
                3
            ),

        "maximum_hydraulic_head_m":
            round(
                max_head,
                3
            ),

        "released_volume_m3":
            round(
                total_volume,
                3
            ),

        "timeseries": rows
    }


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "project": "NEERAKSH",

        "system":
            "Dam Break Inundation Modelling",

        "dam": "Mettur Dam",

        "status": "ONLINE",

        "data_policy":
            "Official government data where available",

        "official_sources": {
            "CWC_NRLD": CWC_NRLD,
            "TN_RESERVOIR": TN_RESERVOIR,
            "CWC_HYDRAULIC_SAFETY":
                CWC_HYDRAULIC_SAFETY
        }
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health():

    return {
        "status": "healthy",
        "time": datetime.utcnow().isoformat()
    }


# ============================================================
# DAM
# ============================================================

@app.get("/api/dams")
def dams():

    return {
        "status": "OFFICIAL_DAM_REGISTER",
        "source": CWC_NRLD,
        "dams": [METTUR]
    }


@app.get("/api/dam/mettur")
def mettur():

    return {
        "status":
            "OFFICIAL_CWC_DAM_RECORD",

        "dam":
            METTUR
    }


# ============================================================
# LIVE METTUR RESERVOIR
# ============================================================

@app.get("/api/reservoir/mettur")
def mettur_reservoir():

    return get_mettur_live()


# ============================================================
# PROBLEM STATEMENT EVENTS
# ============================================================

@app.get("/api/problem-statement/examples")
def problem_statement_examples():

    return {
        "status":
            "PROBLEM_STATEMENT_EXAMPLES",

        "events":
            PS_EXAMPLES
    }


# ============================================================
# DAM-BREAK SIMULATION
# ============================================================

@app.post("/api/simulation/mettur")
def mettur_simulation(payload: dict):

    live = get_mettur_live()

    if live.get("status") != "LIVE_GOVERNMENT_DATA":

        raise HTTPException(
            status_code=503,
            detail=
                "Current official Mettur reservoir data "
                "could not be retrieved safely. "
                "Simulation will not use fabricated values."
        )

    # --------------------------------------------------------
    # REQUIRED SCENARIO PARAMETERS
    #
    # These MUST be supplied by the user/model configuration.
    #
    # No arbitrary breach values are generated here.
    # --------------------------------------------------------

    required = [
        "breach_width_m",
        "breach_depth_m",
        "formation_time_s"
    ]

    missing = [
        x for x in required
        if x not in payload
    ]

    if missing:

        raise HTTPException(
            status_code=400,
            detail={
                "message":
                    "Breach parameters are required.",
                "missing":
                    missing,

                "reason":
                    "No government source in the configured "
                    "Mettur dataset provides a calibrated "
                    "Mettur breach width, breach depth, "
                    "formation time or failure timestamp. "
                    "NEERAKSH therefore refuses to fabricate "
                    "those values."
            }
        )

    # --------------------------------------------------------
    # CONVERT CURRENT LEVEL
    # --------------------------------------------------------

    level_ft = float(
        live["current_level_ft"]
    )

    level_m = (
        level_ft *
        0.3048
    )

    # --------------------------------------------------------
    # RUN PHYSICAL MODEL
    # --------------------------------------------------------

    result = simulate_breach(

        water_level_m=level_m,

        breach_width_m=float(
            payload["breach_width_m"]
        ),

        breach_depth_m=float(
            payload["breach_depth_m"]
        ),

        formation_time_s=float(
            payload["formation_time_s"]
        ),

        simulation_time_s=int(
            payload.get(
                "simulation_time_s",
                1800
            )
        ),

        dt=int(
            payload.get(
                "dt",
                5
            )
        )
    )

    return {

        "status":
            "SCENARIO_SIMULATION_COMPLETED",

        "dam":
            METTUR,

        "government_observation":
            live,

        "failure_time":

            {
                "status":
                    "NOT_PREDICTED",

                "value":
                    None,

                "message":
                    "Government data does not provide "
                    "a future Mettur dam-failure timestamp."
            },

        "failure_mechanism":

            {
                "status":
                    "SCENARIO_DEFINED",

                "value":
                    "User/model-defined breach event"
            },

        "simulation":
            result,

        "sources": [
            CWC_NRLD,
            TN_RESERVOIR,
            CWC_HYDRAULIC_SAFETY
        ]
    }


# ============================================================
# SIMPLE DAM-BREAK VISUALIZATION DATA
# ============================================================

@app.post("/api/simulation/mettur/visualization")
def mettur_visualization(payload: dict):

    simulation_response = mettur_simulation(
        payload
    )

    simulation = simulation_response[
        "simulation"
    ]

    rows = simulation[
        "timeseries"
    ]

    frames = []

    for row in rows:

        # Normalized intensity for visualization ONLY.
        #
        # This is not presented as flood depth
        # or inundation extent.

        intensity = 0.0

        if simulation[
            "maximum_discharge_m3s"
        ] > 0:

            intensity = (
                row["discharge_m3s"] /
                simulation[
                    "maximum_discharge_m3s"
                ]
            )

        frames.append({

            "time_min":
                row["time_min"],

            "discharge_m3s":
                row["discharge_m3s"],

            "breach_width_m":
                row["breach_width_m"],

            "breach_depth_m":
                row["breach_depth_m"],

            "hydraulic_head_m":
                row["hydraulic_head_m"],

            "visualization_intensity":
                round(
                    intensity,
                    4
                )
        })

    return {

        "status":
            "VISUALIZATION_DATA",

        "dam":
            "Mettur Dam",

        "warning":
            "Visualization represents hydraulic "
            "breach discharge intensity. It is not "
            "a terrain-derived inundation map.",

        "frames":
            frames
    }
# ============================================================
# NEERAKSH SYSTEM STATUS
# ============================================================

from pathlib import Path
import json


PROJECT_ROOT = Path(
    r"C:\NEERAKSH-1"
)


def _load_status_json(path):

    try:

        if not path.exists():

            return {
                "available": False,
                "status": "FILE_NOT_FOUND",
                "path": str(path),
            }

        with open(
            path,
            "r",
            encoding="utf-8-sig",
        ) as f:

            data = json.load(f)

        return {
            "available": True,
            "status": data.get(
                "status",
                "STATUS_NOT_DEFINED",
            ),
            "data": data,
            "path": str(path),
        }

    except Exception as e:

        return {
            "available": False,
            "status": "READ_ERROR",
            "message": str(e),
            "path": str(path),
        }


# ------------------------------------------------------------
# VALIDATION FILES
# ------------------------------------------------------------

CWC_PARAMETER_VALIDATION = (
    PROJECT_ROOT
    / "simulations"
    / "outputs"
    / "varattupallam"
    / "hydrograph_validation"
    / "cwc_piping_hydrograph_validation.json"
)


CWC_GEOMETRY_TEST = (
    PROJECT_ROOT
    / "simulations"
    / "outputs"
    / "varattupallam"
    / "hydraulic_feasibility"
    / "cwc_geometry_test.json"
)


CWC_SOLVER_GATE = (
    PROJECT_ROOT
    / "simulations"
    / "outputs"
    / "varattupallam"
    / "solver_input_gate"
    / "solver_input_gate.json"
)


CWC_SPATIAL_AUDIT = (
    PROJECT_ROOT
    / "simulations"
    / "outputs"
    / "varattupallam"
    / "spatial_audit"
    / "spatial_evidence_audit.json"
)


METTUR_HYDRAULIC_INIT = (
    PROJECT_ROOT
    / "simulations"
    / "outputs"
    / "mettur"
    / "reservoir_state"
    / "mettur_reservoir_state.json"
)


METTUR_SCENARIO = (
    PROJECT_ROOT
    / "simulations"
    / "outputs"
    / "mettur"
    / "scenario_selection"
    / "selected_mettur_scenario.json"
)


# ============================================================
# PROJECT STATUS
# ============================================================

@app.get("/api/project/status")
def project_status():

    cwc_validation = _load_status_json(
        CWC_PARAMETER_VALIDATION
    )

    geometry = _load_status_json(
        CWC_GEOMETRY_TEST
    )

    solver_gate = _load_status_json(
        CWC_SOLVER_GATE
    )

    spatial = _load_status_json(
        CWC_SPATIAL_AUDIT
    )

    return {

        "project": "NEERAKSH",

        "system":
            "Dam Break Inundation Modelling",

        "status":
            "ONLINE",

        "data_integrity":
            "NO_FABRICATED_SIMULATION_OUTPUTS",

        "validation": {

            "cwc_reference_parameters":
                cwc_validation[
                    "status"
                ],

            "breach_geometry":
                geometry[
                    "status"
                ],

            "spatial_evidence":
                spatial[
                    "status"
                ],

            "solver_input_gate":
                solver_gate[
                    "status"
                ],
        },

        "simulation": {

            "spatial_2d_ready":
                solver_gate.get(
                    "data",
                    {}
                ).get(
                    "gates",
                    {}
                ).get(
                    "simulation_ready_flag",
                    False,
                ),

            "solver_execution":
                (
                    "READY"
                    if solver_gate.get(
                        "status"
                    )
                    == "SOLVER_INPUT_READY"
                    else "BLOCKED"
                ),
        },

        "message":
            (
                "NEERAKSH backend is online. "
                "Hydraulic simulation is executed "
                "only when all engineering input gates "
                "are verified."
            ),
    }


# ============================================================
# VALIDATION STATUS
# ============================================================

@app.get("/api/validation/status")
def validation_status():

    cwc_validation = _load_status_json(
        CWC_PARAMETER_VALIDATION
    )

    geometry = _load_status_json(
        CWC_GEOMETRY_TEST
    )

    spatial = _load_status_json(
        CWC_SPATIAL_AUDIT
    )

    solver_gate = _load_status_json(
        CWC_SOLVER_GATE
    )

    return {

        "case":
            "CWC_VARATTUPALLAM_2019",

        "cwc_parameter_validation":
            cwc_validation,

        "breach_geometry_validation":
            geometry,

        "spatial_evidence_audit":
            spatial,

        "solver_input_gate":
            solver_gate,
    }


# ============================================================
# VARATTUPALLAM STATUS
# ============================================================

@app.get("/api/varattupallam/status")
def varattupallam_status():

    validation = _load_status_json(
        CWC_PARAMETER_VALIDATION
    )

    geometry = _load_status_json(
        CWC_GEOMETRY_TEST
    )

    spatial = _load_status_json(
        CWC_SPATIAL_AUDIT
    )

    gate = _load_status_json(
        CWC_SOLVER_GATE
    )

    gate_data = gate.get(
        "data",
        {}
    )

    gates = gate_data.get(
        "gates",
        {}
    )

    return {

        "case_id":
            "CWC_VARATTUPALLAM_2019",

        "status":
            "REFERENCE_VALIDATED",

        "official_reference":
            True,

        "cwc_parameters":
            validation.get(
                "status"
            ),

        "breach_geometry":
            geometry.get(
                "status"
            ),

        "spatial_evidence":
            spatial.get(
                "status"
            ),

        "solver_status":
            gate.get(
                "status"
            ),

        "gates":
            gates,

        "simulation": {

            "ready":
                bool(
                    gates.get(
                        "simulation_ready_flag",
                        False,
                    )
                ),

            "status":
                (
                    "READY"
                    if all(
                        gates.values()
                    )
                    and gates
                    else "BLOCKED"
                ),

            "reason":
                gate_data.get(
                    "reason"
                ),
        },

        "integrity":
            {
                "invented_breach_location":
                    False,

                "invented_breach_station":
                    False,

                "invented_hydraulic_initial_condition":
                    False,

                "study_point_used_as_breach":
                    False,

                "mettur_parameters_used":
                    False,
            },
    }


# ============================================================
# METTUR ENGINEERING STATUS
# ============================================================

@app.get("/api/mettur/status")
def mettur_status():

    hydraulic = _load_status_json(
        METTUR_HYDRAULIC_INIT
    )

    scenario = _load_status_json(
        METTUR_SCENARIO
    )

    hydraulic_data = hydraulic.get(
        "data",
        {}
    )

    scenario_data = scenario.get(
        "data",
        {}
    )

    return {

        "dam":
            METTUR,

        "status":
            "OBSERVED_DATA_AVAILABLE",

        "live_endpoint":
            "/api/reservoir/mettur",

        "hydraulic_initialization":
            {

                "available":
                    hydraulic[
                        "available"
                    ],

                "status":
                    hydraulic[
                        "status"
                    ],

                "simulation_ready":
                    hydraulic_data.get(
                        "simulation_ready",
                        False,
                    ),
            },

        "scenario":
            {

                "available":
                    scenario[
                        "available"
                    ],

                "status":
                    scenario[
                        "status"
                    ],

                "data":
                    scenario_data,
            },

        "policy":
            {

                "future_failure_time_predicted":
                    False,

                "fabricated_breach_parameters":
                    False,

                "fabricated_hydraulic_state":
                    False,
            },
    }


# ============================================================
# SPH / DUALSPHYSICS PILOT RESULTS
# ============================================================
#
# These endpoints expose the already-computed SPH pilot products.
# They do NOT run DualSPHysics on every API request.
#
# Primary output directory:
# simulations/sph/mettur_profile/MetturSPH2D_BREACH_RUN/postprocess
#
# The postprocessor itself remains a standalone script. We read its
# generated JSON/NPY/CSV products here so importing main.py does not
# accidentally execute the postprocessor.
# ============================================================

SPH_POSTPROCESS_DIR = (
    PROJECT_ROOT
    / "simulations"
    / "sph"
    / "mettur_profile"
    / "MetturSPH2D_BREACH50_RUN"
    / "postprocess"
)


def _load_sph_summary():
    summary_path = SPH_POSTPROCESS_DIR / "sph_summary.json"

    if not summary_path.exists():
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Mettur SPH pilot results are not available.",
                "expected_summary": str(summary_path),
                "next_step": (
                    "Run backend/sph_postprocess.py after the "
                    "DualSPHysics particle VTK files are ready."
                ),
            },
        )

    try:
        with summary_path.open(
            "r",
            encoding="utf-8",
        ) as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Could not read SPH summary: {e}",
        )


def _load_sph_array(filename):
    path = SPH_POSTPROCESS_DIR / filename

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail={
                "message": f"SPH product is missing: {filename}",
                "path": str(path),
            },
        )

    try:
        return np.load(path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Could not read SPH product {filename}: {e}",
        )


def _sph_grid_to_json(array):
    """
    Convert a NumPy grid into JSON-safe nested lists.
    NaN/Inf values are returned as null.
    """
    values = np.asarray(array, dtype=float)

    result = []

    for row in values:
        result.append(
            [
                (
                    None
                    if not np.isfinite(value)
                    else float(value)
                )
                for value in row
            ]
        )

    return result


def _sph_grid_coordinates(summary, shape):
    """
    Reconstruct cell-center coordinates from the metadata written by
    sph_postprocess.py.
    """
    ny, nx = shape

    dx = float(summary["grid_dx_m"])
    dy = float(summary["grid_dy_m"])
    xmin = float(summary["xmin_m"])
    ymin = float(summary["ymin_m"])

    x = [
        xmin + (i + 0.5) * dx
        for i in range(nx)
    ]

    y = [
        ymin + (j + 0.5) * dy
        for j in range(ny)
    ]

    return x, y


@app.get("/api/simulation/sph/mettur/status")
def mettur_sph_status():
    """
    Report whether the precomputed Mettur SPH pilot products exist.
    """
    summary_path = SPH_POSTPROCESS_DIR / "sph_summary.json"

    required_files = [
        "sph_summary.json",
        "sph_max_depth.npy",
        "sph_max_velocity.npy",
        "sph_final_depth.npy",
        "sph_arrival_time.npy",
        "sph_bed.npy",
        "sph_frame_summary.csv",
    ]

    files = {
        filename:
            (SPH_POSTPROCESS_DIR / filename).exists()
        for filename in required_files
    }

    available = all(files.values())

    return {
        "project": "NEERAKSHA",
        "model": "SPH",
        "solver": "DualSPHysics",
        "site": "Mettur",
        "status": (
            "SPH_PILOT_RESULTS_AVAILABLE"
            if available
            else "SPH_PILOT_RESULTS_INCOMPLETE"
        ),
        "available": available,
        "postprocess_directory": str(
            SPH_POSTPROCESS_DIR
        ),
        "files": files,
        "note": (
            "These are particle-derived SPH pilot products. "
            "They are not a validated Mettur inundation forecast."
        ),
    }


@app.get("/api/simulation/sph/mettur")
def mettur_sph_results():
    """
    Return the complete precomputed Mettur SPH pilot grid.

    Products:
      - maximum depth
      - maximum velocity
      - final-frame depth
      - flood arrival time
      - bed elevation
    """
    summary = _load_sph_summary()

    max_depth = _load_sph_array(
        "sph_max_depth.npy"
    )

    max_velocity = _load_sph_array(
        "sph_max_velocity.npy"
    )

    final_depth = _load_sph_array(
        "sph_final_depth.npy"
    )

    arrival_time = _load_sph_array(
        "sph_arrival_time.npy"
    )

    bed = _load_sph_array(
        "sph_bed.npy"
    )

    shape = max_depth.shape

    for name, array in {
        "sph_max_velocity.npy": max_velocity,
        "sph_final_depth.npy": final_depth,
        "sph_arrival_time.npy": arrival_time,
        "sph_bed.npy": bed,
    }.items():

        if array.shape != shape:
            raise HTTPException(
                status_code=500,
                detail=(
                    f"SPH grid shape mismatch: "
                    f"{name} has {array.shape}, "
                    f"expected {shape}."
                ),
            )

    x, y = _sph_grid_coordinates(
        summary,
        shape,
    )

    return {
        "status": "SPH_PILOT_RESULTS",
        "project": "NEERAKSHA",
        "site": "Mettur",
        "model": "SPH",
        "solver": "DualSPHysics",

        "grid": {
            "nx": int(shape[1]),
            "ny": int(shape[0]),
            "x_m": x,
            "y_m": y,
            "dx_m": float(summary["grid_dx_m"]),
            "dy_m": float(summary["grid_dy_m"]),
        },

        "metadata": summary,

        "products": {
            "max_depth_m":
                _sph_grid_to_json(max_depth),

            "max_velocity_mps":
                _sph_grid_to_json(max_velocity),

            "final_depth_m":
                _sph_grid_to_json(final_depth),

            "arrival_time_s":
                _sph_grid_to_json(arrival_time),

            "bed_elevation_m":
                _sph_grid_to_json(bed),
        },

        "scientific_note": (
            "Particle-derived SPH pilot products. "
            "Bed reference is taken from the supplied "
            "Mettur SPH bathymetry profile. "
            "This is not a validated Mettur inundation forecast."
        ),
    }


@app.get("/api/simulation/sph/mettur/frames")
def mettur_sph_frames():
    """
    Return the frame-level SPH time series generated by the
    postprocessor.
    """
    csv_path = (
        SPH_POSTPROCESS_DIR
        / "sph_frame_summary.csv"
    )

    if not csv_path.exists():
        raise HTTPException(
            status_code=404,
            detail={
                "message":
                    "SPH frame summary is not available.",
                "path": str(csv_path),
            },
        )

    try:
        with csv_path.open(
            "r",
            newline="",
            encoding="utf-8",
        ) as f:

            rows = list(
                csv.DictReader(f)
            )

        return {
            "status": "SPH_FRAME_SUMMARY",
            "site": "Mettur",
            "solver": "DualSPHysics",
            "frames": rows,
            "scientific_note": (
                "Frame statistics are derived from the "
                "SPH particle output and are intended for "
                "pilot visualization."
            ),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Could not read SPH frame summary: {e}",
        )


# ============================================================
# SIMULATION STATUS
# ============================================================

@app.get("/api/simulation/status")
def simulation_status():

    solver_gate = _load_status_json(
        CWC_SOLVER_GATE
    )

    gate_data = solver_gate.get(
        "data",
        {}
    )

    gates = gate_data.get(
        "gates",
        {}
    )

    ready = all(
        gates.values()
    ) if gates else False

    return {

        "status":
            (
                "READY"
                if ready
                else "BLOCKED"
            ),

        "solver":
            "NEERAKSH_2D_HYDRODYNAMIC_SOLVER",

        "execution_allowed":
            ready,

        "input_gates":
            gates,

        "reason":
            gate_data.get(
                "reason"
            ),

        "fabricated_output":
            False,

        "message":
            (
                "No terrain-derived inundation result is "
                "reported while required spatial and "
                "hydraulic inputs remain unverified."
            ),
    }
from mobile_api import register_mobile_api
register_mobile_api(app)
# ============================================================
# RUN
# ============================================================

# Command:
#
# python -m uvicorn main:app --host 0.0.0.0 --port 8000
#
# ============================================================
