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


def load_dem():

    with rasterio.open(DEM_PATH) as src:

        source = src.read(1).astype(np.float64)

        transform, width, height = calculate_default_transform(
            src.crs,
            CRS.from_epsg(32643),
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
            src_crs=src.crs,
            dst_transform=transform,
            dst_crs=CRS.from_epsg(32643),
            resampling=Resampling.bilinear,
            src_nodata=src.nodata,
            dst_nodata=np.nan
        )

    return dem, transform


def main():

    print("=" * 72)
    print("NEERAKSH — METTUR NaN BOUNDARY DIAGNOSTIC")
    print("=" * 72)

    dem, transform = load_dem()

    r = TARGET_ROW
    c = TARGET_COL

    print("\nTARGET")
    print("Row:", r)
    print("Column:", c)
    print("Elevation:", dem[r, c])

    print("\nVALIDITY MAP")
    print("V = valid terrain")
    print(". = NaN / invalid terrain")
    print("X = hotspot")
    print()

    radius = 15

    r0 = max(0, r - radius)
    r1 = min(dem.shape[0], r + radius + 1)

    c0 = max(0, c - radius)
    c1 = min(dem.shape[1], c + radius + 1)

    print(
        "     "
        + "".join(
            str((cc // 10) % 10)
            for cc in range(c0, c1)
        )
    )

    print(
        "     "
        + "".join(
            str(cc % 10)
            for cc in range(c0, c1)
        )
    )

    for rr in range(r0, r1):

        chars = []

        for cc in range(c0, c1):

            if rr == r and cc == c:

                chars.append("X")

            elif np.isnan(dem[rr, cc]):

                chars.append(".")

            else:

                chars.append("V")

        print(
            f"{rr:4d} "
            + "".join(chars)
        )

    print("\n" + "=" * 72)
    print("VALID → NaN BOUNDARY CELLS")
    print("=" * 72)

    directions = [
        (-1, -1, "NW"),
        (-1,  0, "N"),
        (-1,  1, "NE"),
        ( 0, -1, "W"),
        ( 0,  1, "E"),
        ( 1, -1, "SW"),
        ( 1,  0, "S"),
        ( 1,  1, "SE"),
    ]

    boundary_cells = []

    for rr in range(
        max(1, r - radius),
        min(dem.shape[0] - 1, r + radius + 1)
    ):

        for cc in range(
            max(1, c - radius),
            min(dem.shape[1] - 1, c + radius + 1)
        ):

            if np.isnan(dem[rr, cc]):
                continue

            for dr, dc, direction in directions:

                nr = rr + dr
                nc = cc + dc

                if np.isnan(dem[nr, nc]):

                    boundary_cells.append(
                        (
                            rr,
                            cc,
                            dem[rr, cc],
                            nr,
                            nc,
                            direction
                        )
                    )

                    break

    print(
        "\nValid cell -> NaN neighbor"
    )

    print(
        "Row  Col   Elevation   NaN-neighbor   Direction"
    )

    print("-" * 60)

    for item in boundary_cells[:100]:

        rr, cc, z, nr, nc, direction = item

        print(
            f"{rr:4d} "
            f"{cc:4d} "
            f"{z:10.3f}   "
            f"({nr:4d},{nc:4d})     "
            f"{direction}"
        )

    print(
        f"\nBoundary cells found: "
        f"{len(boundary_cells)}"
    )

    print("\n" + "=" * 72)
    print("TARGET ROW / COLUMN PROFILE")
    print("=" * 72)

    print("\nSouthward profile from hotspot:")

    for rr in range(r, min(r + 20, dem.shape[0])):

        value = dem[rr, c]

        print(
            f"Row {rr:4d}, "
            f"Col {c:4d}, "
            f"Elevation = {value}"
        )

    print("\nSoutheast diagonal profile:")

    for i in range(20):

        rr = r + i
        cc = c + i

        if rr >= dem.shape[0] or cc >= dem.shape[1]:
            break

        print(
            f"({rr:4d},{cc:4d}) = "
            f"{dem[rr,cc]}"
        )

    print("\n" + "=" * 72)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 72)


if __name__ == "__main__":
    main()