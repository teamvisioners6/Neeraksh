from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import xy


ROOT = Path(r"C:\NEERAKSH-1")

DEM = (
    ROOT
    / "data"
    / "dem"
    / "mettur"
    / "mettur_correct_dem_30m.tif"
)

OUTPUT_DIR = (
    ROOT
    / "simulations"
    / "terrain"
    / "mettur_correct"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

SLOPE_OUTPUT = (
    OUTPUT_DIR
    / "mettur_slope_degrees.tif"
)

METADATA_OUTPUT = (
    OUTPUT_DIR
    / "terrain_metadata.txt"
)

DAM_LAT = 11.8030556
DAM_LON = 77.8066667


def main():

    print("=" * 70)
    print("NEERAKSH - CORRECT METTUR TERRAIN PROCESSING")
    print("=" * 70)

    if not DEM.exists():
        raise FileNotFoundError(
            f"DEM not found:\n{DEM}"
        )

    with rasterio.open(DEM) as src:

        elevation = src.read(1).astype(np.float32)

        nodata = src.nodata

        print("\nINPUT DEM")
        print("-" * 70)
        print("CRS:", src.crs)
        print("Size:", src.width, "x", src.height)
        print("Resolution:", src.res)
        print("NoData:", nodata)

        valid_mask = np.isfinite(elevation)

        if nodata is not None:
            valid_mask &= elevation != nodata

        valid = elevation[valid_mask]

        print("Valid cells:", len(valid))
        print("Minimum:", float(valid.min()))
        print("Maximum:", float(valid.max()))
        print("Mean:", float(valid.mean()))

        # ------------------------------------------------------
        # Locate official Mettur dam
        # ------------------------------------------------------

        dam_row, dam_col = src.index(
            DAM_LON,
            DAM_LAT
        )

        dam_elevation = elevation[
            dam_row,
            dam_col
        ]

        dam_x, dam_y = xy(
            src.transform,
            dam_row,
            dam_col
        )

        print("\nDAM LOCATION")
        print("-" * 70)
        print("Latitude:", DAM_LAT)
        print("Longitude:", DAM_LON)
        print("Raster row:", dam_row)
        print("Raster column:", dam_col)
        print("Raster coordinate:", dam_x, dam_y)
        print("DEM elevation:", float(dam_elevation))

        # ------------------------------------------------------
        # Calculate slope
        #
        # Approximate degree conversion for EPSG:4326.
        # We calculate using geographic cell dimensions.
        # ------------------------------------------------------

        pixel_lon = abs(src.res[0])
        pixel_lat = abs(src.res[1])

        mean_lat = float(
            (src.bounds.top + src.bounds.bottom) / 2.0
        )

        meters_per_degree_lat = 111320.0

        meters_per_degree_lon = (
            111320.0
            * np.cos(np.radians(mean_lat))
        )

        dx = pixel_lon * meters_per_degree_lon
        dy = pixel_lat * meters_per_degree_lat

        print("\nCELL SIZE")
        print("-" * 70)
        print("dx:", dx, "meters")
        print("dy:", dy, "meters")

        # Replace invalid cells temporarily with nearest-safe value
        work = elevation.copy()

        if nodata is not None:
            work[~valid_mask] = np.nan

        # Calculate gradients while preserving NaN areas
        gy, gx = np.gradient(
            work,
            dy,
            dx
        )

        slope = np.degrees(
            np.arctan(
                np.sqrt(
                    gx * gx +
                    gy * gy
                )
            )
        ).astype(np.float32)

        slope[~valid_mask] = np.float32(
            nodata if nodata is not None else -9999
        )

        # ------------------------------------------------------
        # Save slope
        # ------------------------------------------------------

        profile = src.profile.copy()

        profile.update(
            dtype="float32",
            count=1,
            compress="lzw",
            nodata=(
                nodata
                if nodata is not None
                else -9999
            )
        )

        with rasterio.open(
            SLOPE_OUTPUT,
            "w",
            **profile
        ) as dst:

            dst.write(
                slope,
                1
            )

        slope_valid = slope[valid_mask]

        print("\nSLOPE")
        print("-" * 70)
        print("Minimum:", float(np.nanmin(slope_valid)))
        print("Maximum:", float(np.nanmax(slope_valid)))
        print("Mean:", float(np.nanmean(slope_valid)))

        # ------------------------------------------------------
        # Save metadata
        # ------------------------------------------------------

        with open(
            METADATA_OUTPUT,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                "NEERAKSH - METTUR TERRAIN METADATA\n"
            )

            f.write(
                f"DEM={DEM}\n"
            )

            f.write(
                f"CRS={src.crs}\n"
            )

            f.write(
                f"WIDTH={src.width}\n"
            )

            f.write(
                f"HEIGHT={src.height}\n"
            )

            f.write(
                f"RESOLUTION_X={src.res[0]}\n"
            )

            f.write(
                f"RESOLUTION_Y={src.res[1]}\n"
            )

            f.write(
                f"DAM_LATITUDE={DAM_LAT}\n"
            )

            f.write(
                f"DAM_LONGITUDE={DAM_LON}\n"
            )

            f.write(
                f"DAM_DEM_ELEVATION={float(dam_elevation)}\n"
            )

            f.write(
                f"DEM_MIN={float(valid.min())}\n"
            )

            f.write(
                f"DEM_MAX={float(valid.max())}\n"
            )

            f.write(
                f"DEM_MEAN={float(valid.mean())}\n"
            )

            f.write(
                f"SLOPE_MIN={float(np.nanmin(slope_valid))}\n"
            )

            f.write(
                f"SLOPE_MAX={float(np.nanmax(slope_valid))}\n"
            )

            f.write(
                f"SLOPE_MEAN={float(np.nanmean(slope_valid))}\n"
            )

    print("\nOUTPUT")
    print("-" * 70)
    print("Slope:", SLOPE_OUTPUT)
    print("Metadata:", METADATA_OUTPUT)

    print("\nPROCESSING COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()