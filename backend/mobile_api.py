"""
NEERAKSH mobile API integration
--------------------------------
Registers the NEERAKSH mobile-prototype routes on the existing FastAPI app.

GIS display:
- Uses WGS84-reprojected GeoTIFFs when available.
- Calculates true geographic bounds from the raster CRS.
- Makes NoData/background transparent.
- Provides a time-stepped flood-frame endpoint driven by the actual
  arrival-time and maximum-depth rasters.
- Risk colours are derived from simulated depth/velocity thresholds:
    GREEN  = lower simulated hazard
    YELLOW = moderate simulated hazard
    RED    = extreme simulated hazard

No SPH/Delft3D values are fabricated.
"""

from pathlib import Path
import io
import json
import math
from typing import Any

import numpy as np
from fastapi import HTTPException, Query
from fastapi.responses import Response

try:
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.warp import transform_bounds
except Exception:
    rasterio = None

try:
    from PIL import Image
except Exception:
    Image = None


ROOT = Path(__file__).resolve().parents[1]

SCENARIO_FILE = (
    ROOT
    / "simulations"
    / "scenarios"
    / "mettur"
    / "mettur_source_bounded_scenarios.json"
)

RESULT_DIR = ROOT / "simulations" / "outputs" / "mettur" / "hll_test"

RESULT_JSON_CANDIDATES = [
    RESULT_DIR / "mettur_hypothetical_2d_hll_test.json",
    RESULT_DIR / "mettur_hll_results_summary.json",
]

# Prefer the WGS84 display rasters created from the actual HLL outputs.
# Fall back to the original files if a WGS84 file has not been created yet.
RAW_LAYER_FILES = {
    "max-depth": RESULT_DIR / "mettur_max_depth.tif",
    "max-velocity": RESULT_DIR / "mettur_max_velocity.tif",
    "arrival-time": RESULT_DIR / "mettur_arrival_time.tif",
    "final-depth": RESULT_DIR / "mettur_final_depth.tif",
}

WGS84_LAYER_FILES = {
    "max-depth": RESULT_DIR / "mettur_max_depth_wgs84.tif",
    "max-velocity": RESULT_DIR / "mettur_max_velocity_wgs84.tif",
    "arrival-time": RESULT_DIR / "mettur_arrival_time_wgs84.tif",
    "final-depth": RESULT_DIR / "mettur_final_depth_wgs84.tif",
}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Invalid JSON: {path.name}"
        ) from exc


def _first_result_file() -> Path | None:
    for path in RESULT_JSON_CANDIDATES:
        if path.exists():
            return path
    return None


def _find_value(obj: Any, keys: set[str]) -> Any:
    """Recursively find the first matching key in a JSON-like object."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in keys:
                return v
        for v in obj.values():
            found = _find_value(v, keys)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_value(v, keys)
            if found is not None:
                return found
    return None


def _scenario_rows() -> list[dict[str, Any]]:
    if not SCENARIO_FILE.exists():
        return []

    data = _read_json(SCENARIO_FILE)
    raw = data.get("scenarios", data.get("scenario_set", data))

    if isinstance(raw, dict):
        rows = []
        for key, value in raw.items():
            if isinstance(value, dict):
                row = dict(value)
                row.setdefault("id", key)
                rows.append(row)
        return rows

    return raw if isinstance(raw, list) else []


def _scenario_response() -> list[dict[str, Any]]:
    rows = _scenario_rows()
    output = []

    completed = (RESULT_DIR / "mettur_hypothetical_2d_hll_test.json").exists()

    for row in rows:
        sid = str(row.get("id") or row.get("scenario_id") or "")

        failure = row.get("failure", {})
        if not isinstance(failure, dict):
            failure = {}

        def pick(*names):
            for name in names:
                if name in row:
                    return row[name]
                if name in failure:
                    value = failure[name]
                    if isinstance(value, dict):
                        if "screening_value" in value:
                            return value["screening_value"]
                        if "value" in value:
                            return value["value"]
                    return value
            return None

        width = pick("width_m", "breach_width_m")
        formation = pick(
            "formation_time_hr",
            "formation_time_hours",
        )

        allowed = bool(
            row.get("simulation_allowed", False)
            or row.get("simulation", {}).get("allowed", False)
        )

        if sid == "METTUR_SCREENING_BASE" and completed:
            allowed = True

        output.append(
            {
                "id": sid,
                "width_m": width,
                "formation_time_hr": formation,
                "simulation_allowed": allowed,
                "breach_location_verified": bool(
                    row.get("breach_location_verified", False)
                ),
                "status": (
                    "COMPLETED_HLL_OUTPUT_AVAILABLE"
                    if sid == "METTUR_SCREENING_BASE" and completed
                    else str(row.get("status", "SCREENING_ONLY"))
                ),
            }
        )

    return output


def _layer_path(layer: str) -> Path:
    if layer not in WGS84_LAYER_FILES:
        raise HTTPException(status_code=404, detail="Unknown layer")

    preferred = WGS84_LAYER_FILES[layer]
    fallback = RAW_LAYER_FILES[layer]

    if preferred.exists():
        return preferred

    if fallback.exists():
        return fallback

    raise HTTPException(
        status_code=404,
        detail=f"GIS layer not generated yet: {preferred.name}",
    )


def _raster_stats(path: Path, layer: str) -> dict[str, Any]:
    if rasterio is None:
        raise HTTPException(
            status_code=500,
            detail="rasterio is not installed in backend environment",
        )

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"GIS layer not generated yet: {path.name}",
        )

    with rasterio.open(path) as src:
        arr = src.read(1, masked=True)
        valid = arr.compressed().astype(np.float64)

        if valid.size == 0:
            vmin = vmax = None
        else:
            finite = valid[np.isfinite(valid)]
            vmin = float(np.min(finite)) if finite.size else None
            vmax = float(np.max(finite)) if finite.size else None

        # The WGS84 rasters are already EPSG:4326. This also keeps
        # the endpoint safe if an original projected raster is used.
        b = transform_bounds(
            src.crs,
            "EPSG:4326",
            *src.bounds,
            densify_pts=21,
        )

        return {
            "url": f"/api/layer/{layer}/image.png",
            "bounds": [
                [float(b[1]), float(b[0])],
                [float(b[3]), float(b[2])],
            ],
            "min": vmin,
            "max": vmax,
            "crs": str(src.crs),
            "width": src.width,
            "height": src.height,
        }


def _normalise(values: np.ndarray, valid: np.ndarray) -> np.ndarray:
    out = np.zeros(values.shape, dtype=np.float32)

    if not np.any(valid):
        return out

    vals = values[valid].astype(np.float32)
    finite = vals[np.isfinite(vals)]

    if finite.size == 0:
        return out

    lo = float(np.percentile(finite, 2))
    hi = float(np.percentile(finite, 98))

    if not math.isfinite(lo):
        lo = float(np.min(finite))

    if not math.isfinite(hi) or hi <= lo:
        hi = lo + 1.0

    out = np.clip((values - lo) / (hi - lo), 0.0, 1.0)
    return out


def _colorize(array: np.ndarray, valid: np.ndarray, layer: str) -> bytes:
    """
    Render a transparent GIS overlay.

    max-depth:
        Green  0.02-1.0 m
        Yellow 1.0-3.0 m
        Red    >3.0 m

    max-velocity:
        Green  <1.0 m/s
        Yellow 1.0-2.5 m/s
        Red    >=2.5 m/s

    arrival-time:
        Earlier arrivals are more visible.
    """
    if Image is None:
        raise HTTPException(
            status_code=500,
            detail="Pillow is not installed in backend environment",
        )

    data = array.astype(np.float32)
    finite = valid & np.isfinite(data)

    # Never draw zero-depth/background cells.
    if layer in {"max-depth", "final-depth"}:
        finite &= data >= 0.02

    rgba = np.zeros((data.shape[0], data.shape[1], 4), dtype=np.uint8)

    if not np.any(finite):
        image = Image.fromarray(rgba, mode="RGBA")
        buf = io.BytesIO()
        image.save(buf, format="PNG", optimize=True)
        return buf.getvalue()

    if layer in {"max-depth", "final-depth"}:
        # Actual simulated depth -> risk classification.
        green = finite & (data < 1.0)
        yellow = finite & (data >= 1.0) & (data < 3.0)
        red = finite & (data >= 3.0)

        rgba[green, 0] = 38
        rgba[green, 1] = 166
        rgba[green, 2] = 91
        rgba[green, 3] = 155

        rgba[yellow, 0] = 245
        rgba[yellow, 1] = 190
        rgba[yellow, 2] = 45
        rgba[yellow, 3] = 175

        rgba[red, 0] = 220
        rgba[red, 1] = 38
        rgba[red, 2] = 38
        rgba[red, 3] = 190

    elif layer == "max-velocity":
        green = finite & (data < 1.0)
        yellow = finite & (data >= 1.0) & (data < 2.5)
        red = finite & (data >= 2.5)

        rgba[green, 0] = 38
        rgba[green, 1] = 166
        rgba[green, 2] = 91
        rgba[green, 3] = 145

        rgba[yellow, 0] = 245
        rgba[yellow, 1] = 190
        rgba[yellow, 2] = 45
        rgba[yellow, 3] = 165

        rgba[red, 0] = 220
        rgba[red, 1] = 38
        rgba[red, 2] = 38
        rgba[red, 3] = 185

    else:
        # Arrival-time: earlier cells are stronger.
        norm = _normalise(data, finite)
        intensity = 1.0 - norm

        rgba[..., 0] = np.clip(245 * intensity, 0, 255).astype(np.uint8)
        rgba[..., 1] = np.clip(150 * intensity, 0, 255).astype(np.uint8)
        rgba[..., 2] = np.clip(30 * intensity, 0, 255).astype(np.uint8)
        rgba[..., 3] = np.where(finite, 165, 0).astype(np.uint8)

    image = Image.fromarray(rgba, mode="RGBA")
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _make_result_payload() -> dict[str, Any]:
    result_path = _first_result_file()

    if result_path is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Completed Mettur HLL result is not available yet. "
                "Run the successful HLL solver first."
            ),
        )

    data = _read_json(result_path)

    max_depth = _find_value(
        data,
        {"maximum_depth_m", "max_depth_m", "max_depth", "peak_depth_m"},
    )

    max_velocity = _find_value(
        data,
        {
            "maximum_velocity_mps",
            "max_velocity_mps",
            "max_velocity",
            "peak_velocity_mps",
        },
    )

    wet_cells = _find_value(data, {"wet_cells", "maximum_wet_cells"})
    injected = _find_value(data, {"injected_volume_mcm", "injected_mcm"})
    outflow = _find_value(data, {"boundary_outflow_mcm", "outflow_mcm"})
    final_volume = _find_value(
        data,
        {"final_domain_volume_mcm", "domain_volume_mcm"},
    )
    mass_error = _find_value(
        data,
        {"mass_balance_error_percent", "mass_balance_error_pct"},
    )

    flooded_area_km2 = None

    depth_path = _layer_path("max-depth")

    if rasterio is not None and depth_path.exists():
        with rasterio.open(depth_path) as src:
            arr = src.read(1, masked=True)
            valid = arr.compressed()
            wet = valid[np.isfinite(valid) & (valid >= 0.02)]

            cell_area = abs(src.transform.a * src.transform.e)
            flooded_area_km2 = float(
                wet.size * cell_area / 1_000_000.0
            )

    return {
        "model": "2D HLL shallow-water solver",
        "scenario": "METTUR_SCREENING_BASE",
        "hypothetical": True,
        "validated_forecast": False,
        "source_file": str(result_path.relative_to(ROOT)),
        "derived": {
            "flooded_area_km2": flooded_area_km2,
            "wet_cells": int(wet_cells) if wet_cells is not None else None,
            "max_depth_m": (
                float(max_depth) if max_depth is not None else None
            ),
            "max_velocity_mps": (
                float(max_velocity)
                if max_velocity is not None
                else None
            ),
        },
        "hydraulic": {
            "injected_volume_mcm": (
                float(injected) if injected is not None else None
            ),
            "boundary_outflow_mcm": (
                float(outflow) if outflow is not None else None
            ),
            "final_domain_volume_mcm": (
                float(final_volume)
                if final_volume is not None
                else None
            ),
            "mass_balance_error_percent": (
                float(mass_error) if mass_error is not None else None
            ),
        },
        "comparison": {
            "hll": "COMPLETED",
            "sph": "PENDING",
            "delft3d": "PENDING",
        },
        "notice": (
            "Hypothetical screening run; not a Mettur failure prediction "
            "or validated forecast."
        ),
    }


def _read_wgs84_array(layer: str):
    if rasterio is None:
        raise HTTPException(
            status_code=500,
            detail="rasterio is not installed",
        )

    path = _layer_path(layer)

    with rasterio.open(path) as src:
        arr = src.read(1).astype(np.float32)
        nodata = src.nodata
        transform = src.transform
        bounds = transform_bounds(
            src.crs,
            "EPSG:4326",
            *src.bounds,
            densify_pts=21,
        )

        valid = np.isfinite(arr)

        if nodata is not None:
            valid &= arr != nodata

        return arr, valid, transform, bounds


def _flood_frame_png(time_s: float) -> bytes:
    """
    Build an animated frame from actual HLL outputs.

    A cell appears when its simulated arrival time is <= time_s.
    Its displayed colour is then based on its simulated depth.

    This is visualization of the completed model output, not a new
    simulation or an invented flood path.
    """
    depth, depth_valid, _, _ = _read_wgs84_array("max-depth")
    arrival, arrival_valid, _, _ = _read_wgs84_array("arrival-time")

    if depth.shape != arrival.shape:
        raise HTTPException(
            status_code=500,
            detail="Depth and arrival rasters have incompatible grids",
        )

    # Arrival-time raster convention:
    # finite non-negative values represent cells reached by the flood.
    active = (
        depth_valid
        & arrival_valid
        & np.isfinite(arrival)
        & (arrival >= 0.0)
        & (arrival <= float(time_s))
        & (depth >= 0.02)
    )

    # If the arrival raster uses a large sentinel instead of nodata,
    # only the <= time_s condition above allows cells into the frame.
    return _colorize(depth, active, "max-depth")


def register_mobile_api(app):
    @app.get("/api/scenarios/mettur")
    def mobile_scenarios_mettur():
        return {
            "dam": "Mettur",
            "scenarios": _scenario_response(),
        }

    @app.get("/api/results/mettur")
    def mobile_results_mettur():
        return _make_result_payload()

    @app.get("/api/layer/{layer}/metadata")
    def mobile_layer_metadata(layer: str):
        path = _layer_path(layer)
        return _raster_stats(path, layer)

    @app.get("/api/layer/{layer}/image.png")
    def mobile_layer_png(layer: str):
        path = _layer_path(layer)

        if rasterio is None:
            raise HTTPException(
                status_code=500,
                detail="rasterio is not installed",
            )

        with rasterio.open(path) as src:
            arr = src.read(1)
            nodata = src.nodata

            valid = np.isfinite(arr)

            if nodata is not None:
                valid &= arr != nodata

            png = _colorize(arr, valid, layer)

        return Response(content=png, media_type="image/png")

    @app.get("/api/flood/frame.png")
    def mobile_flood_frame(
        time_s: float = Query(
            0.0,
            ge=0.0,
            le=86400.0,
            description="Simulation time in seconds",
        )
    ):
        png = _flood_frame_png(time_s)

        return Response(
            content=png,
            media_type="image/png",
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate",
            },
        )

    @app.get("/api/flood/timeline")
    def mobile_flood_timeline():
        """
        Return the available simulation timeline based on the actual
        arrival-time raster.
        """
        arrival, valid, _, _ = _read_wgs84_array("arrival-time")

        values = arrival[
            valid
            & np.isfinite(arrival)
            & (arrival >= 0.0)
        ]

        if values.size == 0:
            return {
                "duration_s": 3600.0,
                "start_s": 0.0,
                "end_s": 3600.0,
                "frames_s": [0, 600, 1200, 1800, 2400, 3000, 3600],
            }

        max_time = float(np.max(values))

        # Keep a useful full-run timeline for the mobile player.
        duration = max(60.0, min(max_time, 86400.0))

        frames = np.linspace(
            0.0,
            duration,
            num=13,
        ).round(1).tolist()

        return {
            "duration_s": duration,
            "start_s": 0.0,
            "end_s": duration,
            "frames_s": frames,
        }

    @app.get("/api/mobile/status")
    def mobile_status():
        result_path = _first_result_file()

        layers = {
            key: _layer_path(key).exists()
            if rasterio is not None
            else False
            for key in WGS84_LAYER_FILES
        }

        return {
            "backend": "healthy",
            "mettur_live_route": True,
            "completed_hll_result": result_path is not None,
            "gis_layers": layers,
            "flood_animation": (
                layers.get("max-depth", False)
                and layers.get("arrival-time", False)
            ),
            "sph": False,
            "delft3d": False,
        }

    @app.get("/api/gis/export-list")
    def mobile_export_list():
        files = []

        if RESULT_DIR.exists():
            for p in sorted(RESULT_DIR.iterdir()):
                if p.is_file() and p.suffix.lower() in {
                    ".tif",
                    ".csv",
                    ".json",
                    ".png",
                }:
                    files.append(
                        {
                            "name": p.name,
                            "path": str(p.relative_to(ROOT)),
                            "size_kb": round(
                                p.stat().st_size / 1024,
                                1,
                            ),
                        }
                    )

        return {
            "directory": str(RESULT_DIR.relative_to(ROOT)),
            "files": files,
        }
