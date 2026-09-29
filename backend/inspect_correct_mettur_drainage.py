from pathlib import Path

import numpy as np
import rasterio
import geopandas as gpd
from shapely.geometry import Point


ROOT = Path(r"C:\NEERAKSH-1")

ACCUMULATION = (
    ROOT
    / "simulations"
    / "terrain"
    / "mettur_correct"
    / "mettur_flow_accumulation.tif"
)

RESERVOIR = (
    ROOT
    / "gis"
    / "raw"
    / "reservoirs"
    / "stanley_reservoir_mettur.shp"
)

DAM_LAT = 11.8030556
DAM_LON = 77.8066667


def main():

    print("=" * 75)
    print("NEERAKSH - CORRECT METTUR DRAINAGE INSPECTION")
    print("=" * 75)

    if not ACCUMULATION.exists():
        raise FileNotFoundError(
            f"Accumulation raster not found:\n{ACCUMULATION}"
        )

    if not RESERVOIR.exists():
        raise FileNotFoundError(
            f"Reservoir shapefile not found:\n{RESERVOIR}"
        )

    # ----------------------------------------------------------
    # Read accumulation raster
    # ----------------------------------------------------------

    with rasterio.open(ACCUMULATION) as src:

        accumulation = src.read(1)

        nodata = src.nodata

        valid_mask = np.isfinite(accumulation)

        if nodata is not None:
            valid_mask &= accumulation != nodata

        valid = accumulation[valid_mask].astype(np.float64)

        print("\nACCUMULATION RASTER")
        print("-" * 75)
        print("CRS:", src.crs)
        print("Size:", src.width, "x", src.height)
        print("Resolution:", src.res)
        print("NoData:", nodata)
        print("Valid cells:", len(valid))

        print("\nACCUMULATION STATISTICS")
        print("-" * 75)
        print("Minimum:", float(np.min(valid)))
        print("Maximum:", float(np.max(valid)))
        print("Mean:", float(np.mean(valid)))
        print("Median:", float(np.median(valid)))

        for percentile in [90, 95, 99, 99.5, 99.9]:

            value = np.percentile(
                valid,
                percentile
            )

            print(
                f"{percentile}th percentile:",
                float(value)
            )

        # ------------------------------------------------------
        # Global maximum
        # ------------------------------------------------------

        max_index = np.argmax(
            np.where(valid_mask, accumulation, -np.inf)
        )

        max_row, max_col = np.unravel_index(
            max_index,
            accumulation.shape
        )

        max_value = accumulation[
            max_row,
            max_col
        ]

        max_lon, max_lat = src.xy(
            max_row,
            max_col
        )

        print("\nGLOBAL MAXIMUM")
        print("-" * 75)
        print("Row:", max_row)
        print("Column:", max_col)
        print("Latitude:", max_lat)
        print("Longitude:", max_lon)
        print("Accumulation:", float(max_value))

        # ------------------------------------------------------
        # Dam cell
        # ------------------------------------------------------

        dam_row, dam_col = src.index(
            DAM_LON,
            DAM_LAT
        )

        dam_accumulation = accumulation[
            dam_row,
            dam_col
        ]

        print("\nOFFICIAL METTUR DAM")
        print("-" * 75)
        print("Latitude:", DAM_LAT)
        print("Longitude:", DAM_LON)
        print("Row:", dam_row)
        print("Column:", dam_col)
        print("Accumulation at dam pixel:",
              float(dam_accumulation))

        # ------------------------------------------------------
        # Search around dam
        # ------------------------------------------------------

        radius_pixels = 200

        row_min = max(
            0,
            dam_row - radius_pixels
        )

        row_max = min(
            src.height,
            dam_row + radius_pixels + 1
        )

        col_min = max(
            0,
            dam_col - radius_pixels
        )

        col_max = min(
            src.width,
            dam_col + radius_pixels + 1
        )

        local = accumulation[
            row_min:row_max,
            col_min:col_max
        ]

        local_valid = np.isfinite(local)

        if nodata is not None:
            local_valid &= local != nodata

        local_values = local[
            local_valid
        ].astype(np.float64)

        print("\nLOCAL SEARCH")
        print("-" * 75)
        print(
            "Radius:",
            radius_pixels,
            "pixels (~6 km)"
        )

        print(
            "Valid local cells:",
            len(local_values)
        )

        print(
            "Local maximum:",
            float(np.max(local_values))
        )

        # ------------------------------------------------------
        # Top 20 local accumulation cells
        # ------------------------------------------------------

        local_copy = local.copy()

        local_copy[
            ~local_valid
        ] = -np.inf

        flat_indices = np.argsort(
            local_copy.ravel()
        )[::-1]

        print("\nTOP 20 LOCAL ACCUMULATION CELLS")
        print("-" * 75)

        shown = 0

        for flat_index in flat_indices:

            if shown >= 20:
                break

            row, col = np.unravel_index(
                flat_index,
                local_copy.shape
            )

            value = local_copy[
                row,
                col
            ]

            if not np.isfinite(value):
                continue

            global_row = row_min + row
            global_col = col_min + col

            lon, lat = src.xy(
                global_row,
                global_col
            )

            print(
                f"{shown + 1:02d}. "
                f"ACC={float(value):.0f} "
                f"LAT={lat:.6f} "
                f"LON={lon:.6f} "
                f"ROW={global_row} "
                f"COL={global_col}"
            )

            shown += 1

    # ----------------------------------------------------------
    # Reservoir polygon
    # ----------------------------------------------------------

    print("\nRESERVOIR GIS")
    print("-" * 75)

    reservoir = gpd.read_file(
        RESERVOIR
    )

    print(
        "Reservoir records:",
        len(reservoir)
    )

    print(
        "CRS:",
        reservoir.crs
    )

    reservoir_wgs84 = reservoir.to_crs(
        "EPSG:4326"
    )

    geometry = reservoir_wgs84.geometry.iloc[0]

    centroid = geometry.centroid

    print(
        "Reservoir centroid:",
        centroid.y,
        centroid.x
    )

    print(
        "Reservoir area:",
        float(geometry.area),
        "square degrees"
    )

    print("\n" + "=" * 75)
    print("DRAINAGE INSPECTION COMPLETE")
    print("=" * 75)


if __name__ == "__main__":
    main()