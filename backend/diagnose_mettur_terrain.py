from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling


# ============================================================
# NEERAKSH — METTUR TERRAIN DIAGNOSTIC
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

# Problem cell reported by the solver
PROBLEM_ROW = 415
PROBLEM_COL = 387

WINDOW_RADIUS = 5


def load_metric_dem():

    print("=" * 72)
    print("NEERAKSH — METTUR TERRAIN DIAGNOSTIC")
    print("=" * 72)

    print(f"\nDEM:")
    print(DEM_PATH)

    if not DEM_PATH.exists():
        raise FileNotFoundError(f"DEM not found: {DEM_PATH}")

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


def median_condition(dem):

    stack = np.stack(
        [
            np.roll(np.roll(dem, dy, axis=0), dx, axis=1)
            for dy in (-1, 0, 1)
            for dx in (-1, 0, 1)
        ],
        axis=0,
    )

    with np.errstate(all="ignore"):
        conditioned = np.nanmedian(stack, axis=0)

    # Preserve cells where the entire neighborhood is invalid
    valid_count = np.sum(np.isfinite(stack), axis=0)
    conditioned[valid_count == 0] = np.nan

    # Keep invalid original cells invalid
    conditioned[~np.isfinite(dem)] = np.nan

    return conditioned


def print_window(name, array, row, col, radius=5):

    r0 = max(0, row - radius)
    r1 = min(array.shape[0], row + radius + 1)

    c0 = max(0, col - radius)
    c1 = min(array.shape[1], col + radius + 1)

    print(f"\n{'=' * 72}")
    print(name)
    print(f"Rows {r0}:{r1} | Cols {c0}:{c1}")
    print("=" * 72)

    window = array[r0:r1, c0:c1]

    np.set_printoptions(
        precision=2,
        suppress=True,
        linewidth=200,
        nanstr=" NaN",
    )

    print(window)


def analyze_problem_cell(raw, conditioned):

    row = PROBLEM_ROW
    col = PROBLEM_COL

    if not (
        0 <= row < raw.shape[0]
        and 0 <= col < raw.shape[1]
    ):
        raise IndexError(
            f"Problem cell ({row}, {col}) outside DEM "
            f"shape {raw.shape}"
        )

    raw_value = raw[row, col]
    conditioned_value = conditioned[row, col]

    print("\n" + "=" * 72)
    print("PROBLEM CELL")
    print("=" * 72)

    print(f"Row:                 {row}")
    print(f"Column:              {col}")
    print(f"Raw DEM elevation:   {raw_value:.3f} m")
    print(f"Conditioned DEM:     {conditioned_value:.3f} m")

    if np.isfinite(raw_value) and np.isfinite(conditioned_value):
        print(
            f"Terrain correction:  "
            f"{conditioned_value - raw_value:.3f} m"
        )
    else:
        print("Terrain correction:  NaN")

    # Local neighborhood
    r0 = max(0, row - WINDOW_RADIUS)
    r1 = min(raw.shape[0], row + WINDOW_RADIUS + 1)

    c0 = max(0, col - WINDOW_RADIUS)
    c1 = min(raw.shape[1], col + WINDOW_RADIUS + 1)

    raw_window = raw[r0:r1, c0:c1]
    cond_window = conditioned[r0:r1, c0:c1]

    valid_raw = raw_window[np.isfinite(raw_window)]
    valid_cond = cond_window[np.isfinite(cond_window)]

    print("\nLOCAL RAW DEM STATISTICS")

    if valid_raw.size:
        print(f"Minimum: {np.min(valid_raw):.3f} m")
        print(f"Maximum: {np.max(valid_raw):.3f} m")
        print(f"Mean:    {np.mean(valid_raw):.3f} m")
        print(f"Median:  {np.median(valid_raw):.3f} m")

    print("\nLOCAL CONDITIONED DEM STATISTICS")

    if valid_cond.size:
        print(f"Minimum: {np.min(valid_cond):.3f} m")
        print(f"Maximum: {np.max(valid_cond):.3f} m")
        print(f"Mean:    {np.mean(valid_cond):.3f} m")
        print(f"Median:  {np.median(valid_cond):.3f} m")

    # Neighbor comparison
    center = raw_value

    print("\n8-NEIGHBOR COMPARISON")

    for dr in (-1, 0, 1):
        values = []

        for dc in (-1, 0, 1):

            if dr == 0 and dc == 0:
                continue

            rr = row + dr
            cc = col + dc

            if (
                0 <= rr < raw.shape[0]
                and 0 <= cc < raw.shape[1]
            ):
                value = raw[rr, cc]

                if np.isfinite(value):
                    difference = value - center

                    values.append(
                        f"({rr},{cc})={value:.2f}m "
                        f"Δ={difference:+.2f}m"
                    )

        for value in values:
            print(value)

    # Local minimum / maximum test
    if valid_raw.size:

        local_min = np.min(valid_raw)
        local_max = np.max(valid_raw)

        print("\nLOCAL TERRAIN POSITION")

        if np.isclose(center, local_min):
            print("Problem cell is a LOCAL MINIMUM.")

        elif np.isclose(center, local_max):
            print("Problem cell is a LOCAL MAXIMUM.")

        else:
            print("Problem cell is neither local minimum nor local maximum.")

        print(f"Local minimum: {local_min:.3f} m")
        print(f"Local maximum: {local_max:.3f} m")


def analyze_large_corrections(raw, conditioned):

    print("\n" + "=" * 72)
    print("LARGE TERRAIN CORRECTION ANALYSIS")
    print("=" * 72)

    difference = np.abs(conditioned - raw)

    valid = np.isfinite(difference)

    if not np.any(valid):
        print("No valid terrain corrections found.")
        return

    valid_difference = difference[valid]

    print(
        f"Median correction: "
        f"{np.median(valid_difference):.3f} m"
    )

    print(
        f"Maximum correction: "
        f"{np.max(valid_difference):.3f} m"
    )

    # Top 20 corrections
    flat_indices = np.flatnonzero(valid)

    values = difference.flat[flat_indices]

    order = np.argsort(values)[::-1][:20]

    print("\nTOP 20 TERRAIN CORRECTIONS")

    print(
        f"{'Rank':<6}"
        f"{'Row':<8}"
        f"{'Col':<8}"
        f"{'Raw':<14}"
        f"{'Conditioned':<16}"
        f"{'Correction':<14}"
    )

    for rank, idx in enumerate(order, start=1):

        flat_idx = flat_indices[idx]

        row, col = np.unravel_index(
            flat_idx,
            difference.shape,
        )

        raw_value = raw[row, col]
        cond_value = conditioned[row, col]
        correction = difference[row, col]

        print(
            f"{rank:<6}"
            f"{row:<8}"
            f"{col:<8}"
            f"{raw_value:<14.3f}"
            f"{cond_value:<16.3f}"
            f"{correction:<14.3f}"
        )

    # Check whether problem cell is among the large corrections
    problem_correction = difference[
        PROBLEM_ROW,
        PROBLEM_COL,
    ]

    print("\nPROBLEM CELL CORRECTION")

    if np.isfinite(problem_correction):
        print(
            f"Correction at "
            f"({PROBLEM_ROW},{PROBLEM_COL}): "
            f"{problem_correction:.3f} m"
        )

        if problem_correction > 20:
            print(
                "WARNING: Problem cell has a LARGE "
                "terrain correction."
            )
        else:
            print(
                "Problem cell does not have a large "
                "terrain correction."
            )


def main():

    raw, transform = load_metric_dem()

    print("\nMetric DEM loaded successfully.")
    print(f"Shape: {raw.shape}")
    print(f"Resolution: {TARGET_RESOLUTION} m")

    conditioned = median_condition(raw)

    analyze_problem_cell(
        raw,
        conditioned,
    )

    print_window(
        "RAW DEM — 11 x 11 NEIGHBORHOOD",
        raw,
        PROBLEM_ROW,
        PROBLEM_COL,
        WINDOW_RADIUS,
    )

    print_window(
        "CONDITIONED DEM — 11 x 11 NEIGHBORHOOD",
        conditioned,
        PROBLEM_ROW,
        PROBLEM_COL,
        WINDOW_RADIUS,
    )

    correction = conditioned - raw

    print_window(
        "TERRAIN CORRECTION — 11 x 11",
        correction,
        PROBLEM_ROW,
        PROBLEM_COL,
        WINDOW_RADIUS,
    )

    analyze_large_corrections(
        raw,
        conditioned,
    )

    print("\n" + "=" * 72)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 72)

    print(
        "\nDo NOT modify the hydraulic solver yet."
    )

    print(
        "Send the complete terminal output to me."
    )


if __name__ == "__main__":
    main()