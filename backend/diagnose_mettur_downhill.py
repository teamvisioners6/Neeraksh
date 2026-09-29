from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling


# ============================================================
# NEERAKSH — METTUR DOWNHILL PATH DIAGNOSTIC
# ============================================================

PROJECT_ROOT = Path(r"C:\NEERAKSH-1")

DEM_PATH = (
    PROJECT_ROOT
    / "data"
    / "dem"
    / "mettur"
    / "mettur_correct_dem_30m.tif"
)

TARGET_CRS = "EPSG:32643"
TARGET_RESOLUTION = 60.0

# Cell where the solver detected accumulation
START_ROW = 415
START_COL = 387

# Maximum number of downhill steps to trace
MAX_STEPS = 100

# Stop tracing if elevation increases by more than this amount
# relative to the current cell.
MAX_UPHILL_TOLERANCE_M = 0.50


# ============================================================
# LOAD DEM
# ============================================================

def load_metric_dem():

    print("=" * 72)
    print("NEERAKSH — METTUR DOWNHILL PATH DIAGNOSTIC")
    print("=" * 72)

    print(f"\nDEM:")
    print(DEM_PATH)

    if not DEM_PATH.exists():
        raise FileNotFoundError(
            f"DEM not found:\n{DEM_PATH}"
        )

    with rasterio.open(DEM_PATH) as src:

        print(f"\nOriginal CRS: {src.crs}")
        print(f"Original shape: {src.height} x {src.width}")
        print(f"Original resolution: {src.res}")

        transform, width, height = calculate_default_transform(
            src.crs,
            TARGET_CRS,
            src.width,
            src.height,
            *src.bounds,
            resolution=TARGET_RESOLUTION,
        )

        destination = np.full(
            (height, width),
            np.nan,
            dtype=np.float32,
        )

        reproject(
            source=rasterio.band(src, 1),
            destination=destination,
            src_transform=src.transform,
            src_crs=src.crs,
            src_nodata=src.nodata,
            dst_transform=transform,
            dst_crs=TARGET_CRS,
            dst_nodata=np.nan,
            resampling=Resampling.bilinear,
        )

    return destination, transform


# ============================================================
# D8 NEIGHBOR
# ============================================================

NEIGHBORS = [
    (-1, -1),
    (-1,  0),
    (-1,  1),
    ( 0, -1),
    ( 0,  1),
    ( 1, -1),
    ( 1,  0),
    ( 1,  1),
]


def valid_neighbors(dem, row, col):

    result = []

    current = dem[row, col]

    if not np.isfinite(current):
        return result

    for dr, dc in NEIGHBORS:

        rr = row + dr
        cc = col + dc

        if (
            rr < 0
            or rr >= dem.shape[0]
            or cc < 0
            or cc >= dem.shape[1]
        ):
            continue

        elevation = dem[rr, cc]

        if not np.isfinite(elevation):
            continue

        distance = (
            np.sqrt(2.0)
            if dr != 0 and dc != 0
            else 1.0
        )

        slope = (
            (current - elevation)
            / (60.0 * distance)
        )

        result.append(
            {
                "row": rr,
                "col": cc,
                "elevation": float(elevation),
                "drop_m": float(current - elevation),
                "slope": float(slope),
                "distance_m": 60.0 * distance,
            }
        )

    return result


# ============================================================
# TRACE STEEPEST DOWNHILL PATH
# ============================================================

def trace_downhill(dem):

    row = START_ROW
    col = START_COL

    path = []

    visited = set()

    print("\n" + "=" * 72)
    print("START CELL")
    print("=" * 72)

    print(
        f"Row={row}, Col={col}, "
        f"Elevation={dem[row, col]:.3f} m"
    )

    for step in range(MAX_STEPS):

        if (
            row < 0
            or row >= dem.shape[0]
            or col < 0
            or col >= dem.shape[1]
        ):
            print("\nReached DEM boundary.")
            break

        if not np.isfinite(dem[row, col]):
            print("\nReached NoData cell.")
            break

        key = (row, col)

        if key in visited:

            print("\nLOOP DETECTED")
            print(
                f"Returned to row={row}, col={col}"
            )
            break

        visited.add(key)

        current_elevation = float(
            dem[row, col]
        )

        neighbors = valid_neighbors(
            dem,
            row,
            col,
        )

        if not neighbors:

            print("\nNo valid neighboring cells.")
            break

        # Sort by lowest elevation
        neighbors.sort(
            key=lambda x: x["elevation"]
        )

        lowest = neighbors[0]

        # Strictly downhill candidates
        downhill = [
            n
            for n in neighbors
            if n["elevation"] < current_elevation
        ]

        print(
            f"\nSTEP {step:03d} | "
            f"cell=({row},{col}) | "
            f"z={current_elevation:.3f} m"
        )

        print(
            "  Lowest neighbor: "
            f"({lowest['row']},{lowest['col']}) "
            f"z={lowest['elevation']:.3f} m "
            f"drop={lowest['drop_m']:.3f} m"
        )

        if downhill:

            # Steepest downhill = maximum elevation drop
            next_cell = max(
                downhill,
                key=lambda x: x["drop_m"]
            )

            print(
                "  Selected downhill: "
                f"({next_cell['row']},{next_cell['col']}) "
                f"z={next_cell['elevation']:.3f} m "
                f"drop={next_cell['drop_m']:.3f} m"
            )

            path.append(
                {
                    "step": step,
                    "row": row,
                    "col": col,
                    "elevation": current_elevation,
                    "next_row": next_cell["row"],
                    "next_col": next_cell["col"],
                    "next_elevation": next_cell["elevation"],
                    "drop_m": next_cell["drop_m"],
                }
            )

            row = next_cell["row"]
            col = next_cell["col"]

        else:

            print(
                "\n*** LOCAL DEPRESSION / SINK DETECTED ***"
            )

            print(
                f"Current cell: ({row},{col})"
            )

            print(
                f"Current elevation: "
                f"{current_elevation:.3f} m"
            )

            print(
                f"Lowest neighbor: "
                f"{lowest['elevation']:.3f} m"
            )

            print(
                f"Minimum uphill rise required: "
                f"{lowest['elevation'] - current_elevation:.3f} m"
            )

            path.append(
                {
                    "step": step,
                    "row": row,
                    "col": col,
                    "elevation": current_elevation,
                    "next_row": None,
                    "next_col": None,
                    "next_elevation": None,
                    "drop_m": None,
                }
            )

            break

    return path


# ============================================================
# LOCAL FLOW ANALYSIS
# ============================================================

def analyze_start_cell(dem):

    row = START_ROW
    col = START_COL

    print("\n" + "=" * 72)
    print("START-CELL FLOW ANALYSIS")
    print("=" * 72)

    current = dem[row, col]

    print(
        f"Start cell: ({row},{col})"
    )

    print(
        f"Elevation: {current:.3f} m"
    )

    neighbors = valid_neighbors(
        dem,
        row,
        col,
    )

    neighbors.sort(
        key=lambda x: x["elevation"]
    )

    print(
        "\nAll valid neighbors "
        "(lowest first):"
    )

    for n in neighbors:

        direction = (
            n["row"] - row,
            n["col"] - col,
        )

        print(
            f"  ({n['row']:3d},{n['col']:3d}) "
            f"direction={direction} "
            f"z={n['elevation']:8.3f} m "
            f"drop={n['drop_m']:+8.3f} m "
            f"slope={n['slope']:+.6f}"
        )


# ============================================================
# PATH SUMMARY
# ============================================================

def print_summary(path):

    print("\n" + "=" * 72)
    print("DOWNHILL PATH SUMMARY")
    print("=" * 72)

    if not path:
        print("No path generated.")
        return

    first = path[0]

    print(
        f"Starting elevation: "
        f"{first['elevation']:.3f} m"
    )

    last_valid = None

    for item in path:

        if item["next_elevation"] is not None:
            last_valid = item

    if last_valid:

        print(
            f"Last downhill cell: "
            f"({last_valid['next_row']},"
            f"{last_valid['next_col']})"
        )

        print(
            f"Last elevation: "
            f"{last_valid['next_elevation']:.3f} m"
        )

        print(
            f"Total elevation drop: "
            f"{first['elevation'] - last_valid['next_elevation']:.3f} m"
        )

    print(
        f"Steps traced: {len(path)}"
    )

    sink_items = [
        item
        for item in path
        if item["next_elevation"] is None
    ]

    if sink_items:

        sink = sink_items[-1]

        print("\nFINAL STATUS:")
        print("LOCAL SINK / DEPRESSION DETECTED")

        print(
            f"Sink cell: "
            f"({sink['row']},{sink['col']})"
        )

        print(
            f"Sink elevation: "
            f"{sink['elevation']:.3f} m"
        )

    else:

        print("\nFINAL STATUS:")
        print(
            "No local sink encountered "
            "within the traced path."
        )


# ============================================================
# MAIN
# ============================================================

def main():

    dem, transform = load_metric_dem()

    analyze_start_cell(dem)

    path = trace_downhill(dem)

    print_summary(path)

    print("\n" + "=" * 72)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 72)

    print(
        "\nSend me the terminal output."
    )

    print(
        "Do NOT modify the solver yet."
    )


if __name__ == "__main__":
    main()