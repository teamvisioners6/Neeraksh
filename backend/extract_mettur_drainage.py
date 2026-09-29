from pathlib import Path

import rasterio
import numpy as np


ROOT = Path(r"C:\NEERAKSH-1")

ACCUMULATION = (
    ROOT
    / "simulations"
    / "terrain"
    / "mettur_flow_accumulation.tif"
)

OUTPUT = (
    ROOT
    / "simulations"
    / "terrain"
    / "mettur_drainage_corridor.tif"
)

DAM_LAT = 11.679444
DAM_LON = 77.567222

# 99th percentile from the actual accumulation raster.
# This is a provisional terrain-analysis threshold,
# NOT a calibrated river threshold.
THRESHOLD = 4451.820000000065


def main():

    print("=" * 70)
    print("NEERAKSH - METTUR DRAINAGE CORRIDOR EXTRACTION")
    print("=" * 70)

    if not ACCUMULATION.exists():
        raise FileNotFoundError(
            f"Flow accumulation raster not found:\n{ACCUMULATION}"
        )

    with rasterio.open(ACCUMULATION) as src:

        accumulation = src.read(1, masked=True)

        valid = accumulation.compressed()

        print("\nINPUT")
        print("-" * 70)
        print("Raster:", ACCUMULATION)
        print("CRS:", src.crs)
        print("Width:", src.width)
        print("Height:", src.height)
        print("Resolution:", src.res)
        print("Valid cells:", len(valid))

        print("\nACCUMULATION")
        print("-" * 70)
        print("Minimum:", float(valid.min()))
        print("Maximum:", float(valid.max()))
        print("Mean:", float(valid.mean()))

        print("\nTHRESHOLD")
        print("-" * 70)
        print("Threshold:", THRESHOLD)
        print("Threshold basis: 99th percentile of valid accumulation")

        # --------------------------------------------------
        # Create binary drainage mask
        # --------------------------------------------------

        drainage = np.where(
            (~accumulation.mask)
            & (accumulation >= THRESHOLD),
            1,
            0
        ).astype(np.uint8)

        drainage_count = int(
            np.count_nonzero(drainage)
        )

        print(
            "Drainage cells:",
            drainage_count
        )

        # --------------------------------------------------
        # Dam location
        # --------------------------------------------------

        dam_row, dam_col = src.index(
            DAM_LON,
            DAM_LAT
        )

        print("\nDAM")
        print("-" * 70)
        print("Latitude:", DAM_LAT)
        print("Longitude:", DAM_LON)
        print("Row:", dam_row)
        print("Column:", dam_col)

        # --------------------------------------------------
        # Check whether dam pixel itself is drainage
        # --------------------------------------------------

        print(
            "Dam cell drainage flag:",
            int(drainage[dam_row, dam_col])
        )

        # --------------------------------------------------
        # Save drainage raster
        # --------------------------------------------------

        profile = src.profile.copy()

        profile.update(
            dtype="uint8",
            count=1,
            nodata=0,
            compress="lzw"
        )

        with rasterio.open(
            OUTPUT,
            "w",
            **profile
        ) as dst:

            dst.write(
                drainage,
                1
            )

    print("\nOUTPUT")
    print("-" * 70)
    print(OUTPUT)

    print("\nPROCESSING COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()