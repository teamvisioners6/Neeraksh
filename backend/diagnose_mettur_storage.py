from pathlib import Path
import numpy as np
import rasterio
import geopandas as gpd
from rasterio.features import geometry_mask
from rasterio.warp import calculate_default_transform, reproject, Resampling


ROOT = Path(r"C:\NEERAKSH-1")

DEM_PATH = (
    ROOT
    / "data"
    / "dem"
    / "mettur"
    / "mettur_correct_dem_30m.tif"
)

RESERVOIR_PATH = (
    ROOT
    / "gis"
    / "raw"
    / "reservoirs"
    / "stanley_reservoir_mettur.shp"
)

CWC_PATH = (
    ROOT
    / "data"
    / "hydrology"
    / "mettur"
    / "cwc_stage_storage_2020.csv"
)

OUTPUT_PATH = (
    ROOT
    / "simulations"
    / "outputs"
    / "mettur"
    / "storage_diagnostic"
    / "mettur_storage_diagnostic.csv"
)

OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True
)

GRID_RESOLUTION = 60.0


# ============================================================
# LOAD DEM
# ============================================================

print()
print("=" * 70)
print("NEERAKSH — METTUR STORAGE DIAGNOSTIC")
print("=" * 70)

print()
print("LOADING DEM")

with rasterio.open(DEM_PATH) as src:

    dem = src.read(1).astype(np.float64)

    if src.nodata is not None:
        dem[dem == src.nodata] = np.nan

    src_transform = src.transform
    src_crs = src.crs

print(f"Source CRS: {src_crs}")
print(f"Source shape: {dem.shape}")


# ============================================================
# REPROJECT DEM TO METRIC GRID
# ============================================================

print()
print("=" * 70)
print("BUILDING 60 m METRIC GRID")
print("=" * 70)

left = src_transform.c
top = src_transform.f
right = left + src_transform.a * dem.shape[1]
bottom = top + src_transform.e * dem.shape[0]

dst_crs = "EPSG:32643"

dst_transform, dst_width, dst_height = (
    calculate_default_transform(
        src_crs,
        dst_crs,
        dem.shape[1],
        dem.shape[0],
        left,
        bottom,
        right,
        top,
        resolution=GRID_RESOLUTION,
    )
)

metric_dem = np.full(
    (dst_height, dst_width),
    np.nan,
    dtype=np.float64,
)

reproject(
    source=dem,
    destination=metric_dem,
    src_transform=src_transform,
    src_crs=src_crs,
    dst_transform=dst_transform,
    dst_crs=dst_crs,
    resampling=Resampling.bilinear,
    src_nodata=np.nan,
    dst_nodata=np.nan,
)

cell_area = (
    abs(dst_transform.a)
    * abs(dst_transform.e)
)

print(f"Rows: {dst_height}")
print(f"Cols: {dst_width}")
print(f"Cell area: {cell_area:.2f} m2")
print(f"Metric DEM min: {np.nanmin(metric_dem):.3f} m")
print(f"Metric DEM max: {np.nanmax(metric_dem):.3f} m")


# ============================================================
# LOAD RESERVOIR POLYGON
# ============================================================

print()
print("=" * 70)
print("LOADING STANLEY RESERVOIR")
print("=" * 70)

reservoir = gpd.read_file(
    RESERVOIR_PATH
)

print(f"Features: {len(reservoir)}")
print(f"Original CRS: {reservoir.crs}")

reservoir = reservoir.to_crs(
    dst_crs
)

geometry_list = [
    geom.__geo_interface__
    for geom in reservoir.geometry
    if geom is not None
    and not geom.is_empty
]

reservoir_mask = geometry_mask(
    geometry_list,
    transform=dst_transform,
    invert=True,
    out_shape=metric_dem.shape,
)

print(
    f"Reservoir cells: "
    f"{int(reservoir_mask.sum())}"
)

print(
    f"Rasterized area: "
    f"{reservoir_mask.sum() * cell_area / 1e6:.3f} km2"
)


# ============================================================
# DEM INSIDE RESERVOIR
# ============================================================

reservoir_dem = metric_dem[
    reservoir_mask
    & np.isfinite(metric_dem)
]

print()
print("=" * 70)
print("RESERVOIR DEM STATISTICS")
print("=" * 70)

print(
    f"Valid cells: "
    f"{len(reservoir_dem)}"
)

print(
    f"Minimum: "
    f"{np.min(reservoir_dem):.3f} m"
)

print(
    f"P01: "
    f"{np.percentile(reservoir_dem, 1):.3f} m"
)

print(
    f"P05: "
    f"{np.percentile(reservoir_dem, 5):.3f} m"
)

print(
    f"P10: "
    f"{np.percentile(reservoir_dem, 10):.3f} m"
)

print(
    f"P25: "
    f"{np.percentile(reservoir_dem, 25):.3f} m"
)

print(
    f"Median: "
    f"{np.percentile(reservoir_dem, 50):.3f} m"
)

print(
    f"P75: "
    f"{np.percentile(reservoir_dem, 75):.3f} m"
)

print(
    f"P90: "
    f"{np.percentile(reservoir_dem, 90):.3f} m"
)

print(
    f"P95: "
    f"{np.percentile(reservoir_dem, 95):.3f} m"
)

print(
    f"P99: "
    f"{np.percentile(reservoir_dem, 99):.3f} m"
)

print(
    f"Maximum: "
    f"{np.max(reservoir_dem):.3f} m"
)


# ============================================================
# RASTER STORAGE FUNCTION
# ============================================================

def raster_storage(wse):

    valid = (
        reservoir_mask
        & np.isfinite(metric_dem)
        & (metric_dem < wse)
    )

    if not np.any(valid):
        return 0.0

    depth = (
        wse
        - metric_dem[valid]
    )

    volume = (
        np.sum(depth)
        * cell_area
    )

    return float(volume)


# ============================================================
# TEST WSE VALUES
# ============================================================

wse_values = [
    204.216,
    210.0,
    215.0,
    220.0,
    225.0,
    230.0,
    233.493767,
    235.0,
    240.0,
    240.790,
]


print()
print("=" * 70)
print("RASTER STORAGE CURVE")
print("=" * 70)

rows = []

for wse in wse_values:

    volume_m3 = raster_storage(
        wse
    )

    volume_mcm = (
        volume_m3 / 1_000_000.0
    )

    wet_cells = int(
        np.sum(
            reservoir_mask
            & np.isfinite(metric_dem)
            & (metric_dem < wse)
        )
    )

    print(
        f"WSE {wse:10.3f} m | "
        f"Raster {volume_mcm:12.3f} MCM | "
        f"Wet cells {wet_cells:6d}"
    )

    rows.append(
        (
            wse,
            volume_mcm,
            wet_cells,
        )
    )


# ============================================================
# LOAD CWC CURVE
# ============================================================

print()
print("=" * 70)
print("LOADING CWC STAGE-STORAGE CURVE")
print("=" * 70)

cwc = np.genfromtxt(
    CWC_PATH,
    delimiter=",",
    names=True,
    dtype=None,
    encoding="utf-8",
)

print(
    "CWC columns:",
    cwc.dtype.names
)


# ============================================================
# FIND CWC COLUMNS
# ============================================================

names = list(
    cwc.dtype.names
)

elevation_col = None
storage_col = None

for name in names:

    lower = name.lower()

    if (
        elevation_col is None
        and "elevation" in lower
    ):
        elevation_col = name

    if (
        storage_col is None
        and "cumulative_live_capacity" in lower
    ):
        storage_col = name


if elevation_col is None:
    elevation_col = names[0]

if storage_col is None:

    for name in names:

        if "capacity" in name.lower():
            storage_col = name
            break


if storage_col is None:
    raise RuntimeError(
        "Could not identify CWC storage column."
    )


print(
    f"Elevation column: {elevation_col}"
)

print(
    f"Storage column: {storage_col}"
)


# ============================================================
# COMPARE CURVES
# ============================================================

print()
print("=" * 70)
print("CWC VS RASTER COMPARISON")
print("=" * 70)

comparison = []

for row in cwc:

    elevation = float(
        row[elevation_col]
    )

    cwc_storage = float(
        row[storage_col]
    )

    raster_storage_mcm = (
        raster_storage(elevation)
        / 1_000_000.0
    )

    difference = (
        raster_storage_mcm
        - cwc_storage
    )

    comparison.append(
        (
            elevation,
            cwc_storage,
            raster_storage_mcm,
            difference,
        )
    )

    print(
        f"WSE {elevation:9.3f} m | "
        f"CWC {cwc_storage:12.3f} MCM | "
        f"Raster {raster_storage_mcm:12.3f} MCM | "
        f"Diff {difference:12.3f} MCM"
    )


# ============================================================
# SAVE CSV
# ============================================================

with open(
    OUTPUT_PATH,
    "w",
    encoding="utf-8",
) as f:

    f.write(
        "wse_m,"
        "cwc_storage_mcm,"
        "raster_storage_mcm,"
        "difference_mcm\n"
    )

    for row in comparison:

        f.write(
            f"{row[0]:.6f},"
            f"{row[1]:.6f},"
            f"{row[2]:.6f},"
            f"{row[3]:.6f}\n"
        )


# ============================================================
# KEY CHECK
# ============================================================

reference_wse = 233.493767

reference_raster_storage = (
    raster_storage(
        reference_wse
    )
    / 1_000_000.0
)

print()
print("=" * 70)
print("KEY CHECK")
print("=" * 70)

print(
    f"CWC-derived WSE: "
    f"{reference_wse:.6f} m"
)

print(
    f"Raster storage at CWC WSE: "
    f"{reference_raster_storage:.6f} MCM"
)

print(
    "Target hydraulic storage: "
    "1276.636712 MCM"
)

print()
print(
    f"Diagnostic CSV saved to:\n"
    f"{OUTPUT_PATH}"
)

print()
print(
    "STATUS: STORAGE DIAGNOSTIC COMPLETE"
)