from pathlib import Path

import rasterio
from rasterio.windows import from_bounds


ROOT = Path(r"C:\NEERAKSH-1")

SOURCE_DEM = (
    ROOT
    / "data"
    / "dem"
    / "original"
    / "mettur_region_cartodem_30m.tif"
)

OUTPUT_DEM = (
    ROOT
    / "data"
    / "dem"
    / "mettur"
    / "mettur_correct_dem_30m.tif"
)

# Correct Mettur simulation domain
WEST = 77.60
SOUTH = 11.55
EAST = 78.00
NORTH = 12.00

DAM_LAT = 11.8030556
DAM_LON = 77.8066667


def main():

    print("=" * 70)
    print("NEERAKSH - CORRECT METTUR CARTODEM DOMAIN")
    print("=" * 70)

    if not SOURCE_DEM.exists():
        raise FileNotFoundError(
            f"Source DEM not found:\n{SOURCE_DEM}"
        )

    with rasterio.open(SOURCE_DEM) as src:

        print("\nSOURCE DEM")
        print("-" * 70)
        print("CRS:", src.crs)
        print("Size:", src.width, "x", src.height)
        print("Resolution:", src.res)
        print("Bounds:", src.bounds)

        window = from_bounds(
            WEST,
            SOUTH,
            EAST,
            NORTH,
            transform=src.transform
        )

        window = window.round_offsets().round_lengths()

        data = src.read(1, window=window)

        transform = src.window_transform(window)

        profile = src.profile.copy()

        profile.update(
            height=data.shape[0],
            width=data.shape[1],
            transform=transform,
            compress="lzw"
        )

        OUTPUT_DEM.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with rasterio.open(
            OUTPUT_DEM,
            "w",
            **profile
        ) as dst:

            dst.write(
                data,
                1
            )

        # Locate official dam coordinate in cropped raster
        dam_row, dam_col = src.index(
            DAM_LON,
            DAM_LAT
        )

        # Convert global source coordinates to crop coordinates
        local_row = dam_row - int(window.row_off)
        local_col = dam_col - int(window.col_off)

        print("\nCORRECT METTUR DOMAIN")
        print("-" * 70)
        print("West :", WEST)
        print("South:", SOUTH)
        print("East :", EAST)
        print("North:", NORTH)

        print("\nOUTPUT SIZE")
        print("-" * 70)
        print("Width :", data.shape[1])
        print("Height:", data.shape[0])

        print("\nOFFICIAL DAM LOCATION")
        print("-" * 70)
        print("Latitude :", DAM_LAT)
        print("Longitude:", DAM_LON)
        print("Raster row:", local_row)
        print("Raster col:", local_col)

        dam_value = data[
            local_row,
            local_col
        ]

        print("DEM elevation:", float(dam_value))

        valid = data[data != src.nodata]

        print("\nELEVATION")
        print("-" * 70)
        print("Minimum:", float(valid.min()))
        print("Maximum:", float(valid.max()))
        print("Mean:", float(valid.mean()))

        print("\nOUTPUT")
        print("-" * 70)
        print(OUTPUT_DEM)

    print("\nCOMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()