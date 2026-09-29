import numpy as np
import rasterio
from pathlib import Path

from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.crs import CRS


DEM_PATH = Path(
    r"C:\NEERAKSH-1\data\dem\mettur\mettur_correct_dem_30m.tif"
)

TARGET_ROW = 415
TARGET_COL = 387

GRID_RESOLUTION_M = 60.0
RADIUS = 5


def load_dem_60m():

    print("\nREPROJECTING DEM TO SAME 60 m METRIC GRID USED BY SOLVER")

    with rasterio.open(DEM_PATH) as src:

        source = src.read(1).astype(np.float64)

        source_crs = src.crs
        target_crs = CRS.from_epsg(32643)

        transform, width, height = calculate_default_transform(
            source_crs,
            target_crs,
            src.width,
            src.height,
            *src.bounds,
            resolution=GRID_RESOLUTION_M
        )

        dem = np.full(
            (height, width),
            np.nan,
            dtype=np.float64
        )

        reproject(
            source,
            dem,
            src_transform=src.transform,
            src_crs=source_crs,
            dst_transform=transform,
            dst_crs=target_crs,
            resampling=Resampling.bilinear,
            src_nodata=src.nodata,
            dst_nodata=np.nan
        )

    print("Target CRS:", target_crs)
    print("Grid shape:", dem.shape)
    print("Grid resolution:", GRID_RESOLUTION_M, "m")
    print("DEM minimum:", np.nanmin(dem))
    print("DEM maximum:", np.nanmax(dem))

    return dem, transform


def print_neighborhood(dem, transform):

    r = TARGET_ROW
    c = TARGET_COL

    if not (
        0 <= r < dem.shape[0]
        and 0 <= c < dem.shape[1]
    ):
        raise RuntimeError(
            f"Target cell ({r},{c}) outside DEM shape {dem.shape}"
        )

    z0 = dem[r, c]

    x, y = rasterio.transform.xy(
        transform,
        r,
        c
    )

    print("\n" + "=" * 72)
    print("TARGET HOTSPOT")
    print("=" * 72)

    print(f"Row:                 {r}")
    print(f"Column:              {c}")
    print(f"Terrain elevation:   {z0:.3f} m")
    print(f"Projected X:         {x:.3f} m")
    print(f"Projected Y:         {y:.3f} m")

    print("\n" + "=" * 72)
    print("11 x 11 TERRAIN WINDOW")
    print("=" * 72)

    r0 = max(0, r - RADIUS)
    r1 = min(dem.shape[0], r + RADIUS + 1)

    c0 = max(0, c - RADIUS)
    c1 = min(dem.shape[1], c + RADIUS + 1)

    print(
        "        "
        + " ".join(
            f"{cc:9d}"
            for cc in range(c0, c1)
        )
    )

    for rr in range(r0, r1):

        values = []

        for cc in range(c0, c1):

            value = dem[rr, cc]

            if np.isnan(value):

                text = "    NaN   "

            elif rr == r and cc == c:

                text = f"[{value:7.2f}]"

            else:

                text = f" {value:7.2f} "

            values.append(text)

        print(
            f"{rr:5d} "
            + " ".join(values)
        )

    print("\n" + "=" * 72)
    print("8-NEIGHBOR ANALYSIS")
    print("=" * 72)

    neighbors = [
        (-1, -1, "NW"),
        (-1,  0, "N"),
        (-1,  1, "NE"),
        ( 0, -1, "W"),
        ( 0,  1, "E"),
        ( 1, -1, "SW"),
        ( 1,  0, "S"),
        ( 1, 1, "SE"),
    ]

    results = []

    for dr, dc, name in neighbors:

        rr = r + dr
        cc = c + dc

        if not (
            0 <= rr < dem.shape[0]
            and 0 <= cc < dem.shape[1]
        ):
            continue

        zn = dem[rr, cc]

        if np.isnan(zn):
            continue

        drop = z0 - zn

        results.append(
            (
                zn,
                drop,
                name,
                rr,
                cc
            )
        )

    results.sort(
        key=lambda item: item[0]
    )

    print(
        "\nDirection   Row   Col    "
        "Elevation(m)    Drop(m)"
    )

    print("-" * 68)

    for zn, drop, name, rr, cc in results:

        print(
            f"{name:>5}     "
            f"{rr:4d}  "
            f"{cc:4d}      "
            f"{zn:10.3f}    "
            f"{drop:10.3f}"
        )

    if results:

        lowest = results[0]

        print("\nLOWEST IMMEDIATE NEIGHBOR")

        print("Direction:", lowest[2])
        print("Row:", lowest[3])
        print("Column:", lowest[4])
        print(
            f"Elevation: {lowest[0]:.3f} m"
        )
        print(
            f"Drop from target: {lowest[1]:.3f} m"
        )

        if lowest[1] > 0:

            print(
                "\nSTATUS: TARGET HAS A DOWNHILL EXIT"
            )

        elif lowest[1] < 0:

            print(
                "\nSTATUS: TARGET IS LOWER "
                "THAN ALL IMMEDIATE NEIGHBORS"
            )

            print(
                "Possible local depression."
            )

        else:

            print(
                "\nSTATUS: FLAT LOCAL TERRAIN"
            )

    print("\n" + "=" * 72)
    print("LOCAL SINK TEST")
    print("=" * 72)

    valid_neighbor_elevations = []

    for dr, dc, name in neighbors:

        rr = r + dr
        cc = c + dc

        if (
            0 <= rr < dem.shape[0]
            and 0 <= cc < dem.shape[1]
        ):

            value = dem[rr, cc]

            if not np.isnan(value):

                valid_neighbor_elevations.append(
                    value
                )

    if valid_neighbor_elevations:

        min_neighbor = min(
            valid_neighbor_elevations
        )

        max_neighbor = max(
            valid_neighbor_elevations
        )

        print(
            f"Target elevation: {z0:.3f} m"
        )

        print(
            f"Lowest neighbor:  {min_neighbor:.3f} m"
        )

        print(
            f"Highest neighbor: {max_neighbor:.3f} m"
        )

        if z0 < min_neighbor:

            print("\nLOCAL SINK: YES")

        else:

            print("\nLOCAL SINK: NO")

    print("\n" + "=" * 72)
    print("SURROUNDING TERRAIN DROP ANALYSIS")
    print("=" * 72)

    print(
        "\nFor each surrounding cell, "
        "elevation difference from target:"
    )

    for rr in range(r0, r1):

        row_values = []

        for cc in range(c0, c1):

            value = dem[rr, cc]

            if np.isnan(value):

                row_values.append(" NaN ")

            else:

                difference = z0 - value

                row_values.append(
                    f"{difference:6.1f}"
                )

        print(
            f"{rr:5d}: "
            + " ".join(row_values)
        )

    print("\n" + "=" * 72)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 72)


def main():

    print("=" * 72)
    print("NEERAKSH — METTUR HOTSPOT TERRAIN DIAGNOSTIC")
    print("=" * 72)

    with rasterio.open(DEM_PATH) as src:

        print("\nRAW DEM")
        print("CRS:", src.crs)
        print("Resolution:", src.res)
        print(
            "Shape:",
            src.height,
            "x",
            src.width
        )

    dem, transform = load_dem_60m()

    print_neighborhood(
        dem,
        transform
    )


if __name__ == "__main__":
    main()