import numpy as np
import rasterio

from pathlib import Path
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.crs import CRS


DEM_PATH = Path(
    r"C:\NEERAKSH-1\data\dem\mettur\mettur_correct_dem_30m.tif"
)

GRID_RESOLUTION_M = 60.0


def main():

    print("=" * 72)
    print("NEERAKSH — METTUR NODATA GEOGRAPHIC LOCATION")
    print("=" * 72)

    with rasterio.open(DEM_PATH) as src:

        data = src.read(1).astype(np.float64)

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
            data,
            dem,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=transform,
            dst_crs=CRS.from_epsg(32643),
            resampling=Resampling.bilinear,
            src_nodata=src.nodata,
            dst_nodata=np.nan
        )

    print("\n60 m DEM")
    print("Shape:", dem.shape)
    print("CRS: EPSG:32643")

    # Target hotspot
    r = 415
    c = 387

    x, y = rasterio.transform.xy(
        transform,
        r,
        c
    )

    print("\nHOTSPOT")
    print("Row:", r)
    print("Column:", c)
    print("X:", x)
    print("Y:", y)
    print("Elevation:", dem[r, c])

    # Find NaN cells in local region
    radius = 25

    r0 = max(0, r - radius)
    r1 = min(dem.shape[0], r + radius + 1)

    c0 = max(0, c - radius)
    c1 = min(dem.shape[1], c + radius + 1)

    local = dem[r0:r1, c0:c1]

    nan_positions = np.argwhere(
        np.isnan(local)
    )

    print("\nLOCAL NODATA REGION")

    print(
        "NaN cells:",
        len(nan_positions)
    )

    if len(nan_positions) > 0:

        rows = nan_positions[:, 0] + r0
        cols = nan_positions[:, 1] + c0

        print(
            "Row range:",
            rows.min(),
            "to",
            rows.max()
        )

        print(
            "Column range:",
            cols.min(),
            "to",
            cols.max()
        )

        # Geographic bounding box
        x1, y1 = rasterio.transform.xy(
            transform,
            rows.min(),
            cols.min()
        )

        x2, y2 = rasterio.transform.xy(
            transform,
            rows.max(),
            cols.max()
        )

        print(
            "\nApproximate UTM extent:"
        )

        print(
            "X:",
            min(x1, x2),
            "to",
            max(x1, x2)
        )

        print(
            "Y:",
            min(y1, y2),
            "to",
            max(y1, y2)
        )

    # Convert hotspot back to WGS84
    from rasterio.warp import transform as transform_coords

    lon, lat = transform_coords(
        "EPSG:32643",
        "EPSG:4326",
        [x],
        [y]
    )

    print("\nHOTSPOT GEOGRAPHIC COORDINATES")

    print(
        "Latitude:",
        lat[0]
    )

    print(
        "Longitude:",
        lon[0]
    )

    # Find closest valid cells surrounding the NoData patch
    print("\nBOUNDARY ELEVATIONS")

    boundary = []

    for rr in range(
        max(1, r - radius),
        min(dem.shape[0] - 1, r + radius + 1)
    ):

        for cc in range(
            max(1, c - radius),
            min(dem.shape[1] - 1, c + radius + 1)
        ):

            if not np.isnan(dem[rr, cc]):
                continue

            for dr, dc in [
                (-1,0),
                (1,0),
                (0,-1),
                (0,1)
            ]:

                nr = rr + dr
                nc = cc + dc

                if (
                    0 <= nr < dem.shape[0]
                    and 0 <= nc < dem.shape[1]
                    and not np.isnan(dem[nr,nc])
                ):

                    boundary.append(
                        dem[nr,nc]
                    )

    if boundary:

        print(
            "Boundary valid cells:",
            len(boundary)
        )

        print(
            "Boundary minimum:",
            min(boundary)
        )

        print(
            "Boundary maximum:",
            max(boundary)
        )

        print(
            "Boundary median:",
            np.median(boundary)
        )

    print("\n" + "=" * 72)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 72)


if __name__ == "__main__":
    main()