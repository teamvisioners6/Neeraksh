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
    print("NEERAKSH — METTUR DEM NODATA DIAGNOSTIC")
    print("=" * 72)

    with rasterio.open(DEM_PATH) as src:

        print("\nORIGINAL DEM")

        print("CRS:", src.crs)
        print("Shape:", src.height, "x", src.width)
        print("Resolution:", src.res)
        print("NoData value:", src.nodata)

        data = src.read(1)

        print(
            "Raw NoData pixels:",
            np.count_nonzero(
                data == src.nodata
            )
            if src.nodata is not None
            else "No explicit nodata value"
        )

        print(
            "Raw NaN pixels:",
            np.count_nonzero(
                np.isnan(data)
            )
        )

        print(
            "Valid pixels:",
            np.count_nonzero(
                np.isfinite(data)
            )
        )

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
            data.astype(np.float64),
            dem,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=transform,
            dst_crs=CRS.from_epsg(32643),
            resampling=Resampling.bilinear,
            src_nodata=src.nodata,
            dst_nodata=np.nan
        )

    print("\n60 m REPROJECTED DEM")

    print("Shape:", dem.shape)

    print(
        "NaN pixels:",
        np.count_nonzero(
            np.isnan(dem)
        )
    )

    print(
        "Valid pixels:",
        np.count_nonzero(
            np.isfinite(dem)
        )
    )

    print(
        "NaN percentage:",
        100.0
        * np.count_nonzero(np.isnan(dem))
        / dem.size
    )

    print("\n" + "=" * 72)
    print("HOTSPOT NODATA REGION")
    print("=" * 72)

    r = 415
    c = 387

    print(
        f"\nTarget cell: ({r},{c})"
    )

    print(
        f"Target elevation: {dem[r,c]}"
    )

    print("\nSouth direction:")

    for rr in range(
        r,
        min(r + 20, dem.shape[0])
    ):

        value = dem[rr, c]

        print(
            f"({rr},{c}) = {value}"
        )

    print("\nSoutheast direction:")

    for i in range(20):

        rr = r + i
        cc = c + i

        if (
            rr >= dem.shape[0]
            or cc >= dem.shape[1]
        ):
            break

        print(
            f"({rr},{cc}) = "
            f"{dem[rr,cc]}"
        )

    print("\n" + "=" * 72)
    print("NODATA PATCH SIZE")
    print("=" * 72)

    # Local 30 x 30 region

    r0 = max(0, r - 15)
    r1 = min(dem.shape[0], r + 16)

    c0 = max(0, c - 15)
    c1 = min(dem.shape[1], c + 16)

    local = dem[r0:r1, c0:c1]

    nan_count = np.count_nonzero(
        np.isnan(local)
    )

    total_count = local.size

    print(
        "Local window:",
        local.shape
    )

    print(
        "NaN cells:",
        nan_count
    )

    print(
        "Total cells:",
        total_count
    )

    print(
        "NaN percentage:",
        100.0 * nan_count / total_count
    )

    print("\n" + "=" * 72)
    print("VALIDITY MAP")
    print("=" * 72)

    print(
        "V = valid"
    )

    print(
        ". = NoData"
    )

    print(
        "X = hotspot"
    )

    print()

    for rr in range(r0, r1):

        row = ""

        for cc in range(c0, c1):

            if rr == r and cc == c:

                row += "X"

            elif np.isnan(dem[rr,cc]):

                row += "."

            else:

                row += "V"

        print(
            f"{rr:4d} {row}"
        )

    print("\n" + "=" * 72)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 72)


if __name__ == "__main__":
    main()