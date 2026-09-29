from pathlib import Path
import json
import rasterio
from whitebox.whitebox_tools import WhiteboxTools


ROOT = Path(r"C:\NEERAKSH-1")

DEM = (
    ROOT
    / "data"
    / "dem"
    / "mettur"
    / "mettur_dem_30m.tif"
)

OUT = ROOT / "simulations" / "terrain"
OUT.mkdir(parents=True, exist_ok=True)

FILLED_DEM = OUT / "mettur_dem_filled.tif"
FLOW_DIR = OUT / "mettur_flow_direction.tif"
FLOW_ACC = OUT / "mettur_flow_accumulation.tif"

DAM_LAT = 11.679444
DAM_LON = 77.567222


def main():

    print("=" * 70)
    print("NEERAKSH - METTUR HYDROLOGICAL TERRAIN PROCESSOR")
    print("=" * 70)

    if not DEM.exists():
        raise FileNotFoundError(
            f"DEM not found:\n{DEM}"
        )

    print("\nInput DEM:")
    print(DEM)

    # ---------------------------------------------------------
    # Initialize WhiteboxTools
    # ---------------------------------------------------------

    wbt = WhiteboxTools()

    wbt.set_working_dir(str(OUT))
    wbt.set_verbose_mode(True)

    print("\nWhiteboxTools:")
    print(wbt.version())

    # ---------------------------------------------------------
    # Validate DEM
    # ---------------------------------------------------------

    with rasterio.open(DEM) as src:

        print("\nDEM INFORMATION")
        print("-" * 70)
        print("CRS:", src.crs)
        print("Width:", src.width)
        print("Height:", src.height)
        print("Resolution:", src.res)
        print("Bounds:", src.bounds)

        row, col = src.index(
            DAM_LON,
            DAM_LAT
        )

        print("\nMettur Dam raster location")
        print("Row:", row)
        print("Column:", col)
        print(
            "Elevation:",
            float(src.read(1)[row, col]),
            "m"
        )

    # ---------------------------------------------------------
    # STEP 1
    # Fill depressions
    # ---------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("STEP 1 - FILLING TERRAIN DEPRESSIONS")
    print("=" * 70)

    wbt.fill_depressions(
        dem=str(DEM),
        output=str(FILLED_DEM)
    )

    if not FILLED_DEM.exists():
        raise RuntimeError(
            "Filled DEM was not created."
        )

    print("\nFilled DEM created:")
    print(FILLED_DEM)

    # ---------------------------------------------------------
    # STEP 2
    # D8 flow direction
    # ---------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("STEP 2 - D8 FLOW DIRECTION")
    print("=" * 70)

    wbt.d8_pointer(
        dem=str(FILLED_DEM),
        output=str(FLOW_DIR)
    )

    if not FLOW_DIR.exists():
        raise RuntimeError(
            "Flow-direction raster was not created."
        )

    print("\nFlow direction created:")
    print(FLOW_DIR)

    # ---------------------------------------------------------
    # STEP 3
    # Flow accumulation
    # ---------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("STEP 3 - FLOW ACCUMULATION")
    print("=" * 70)

    wbt.d8_flow_accumulation(
        i=str(FILLED_DEM),
        output=str(FLOW_ACC),
        out_type="cells"
    )

    if not FLOW_ACC.exists():
        raise RuntimeError(
            "Flow accumulation raster was not created."
        )

    print("\nFlow accumulation created:")
    print(FLOW_ACC)

    # ---------------------------------------------------------
    # STEP 4
    # Extract statistics
    # ---------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("STEP 4 - RASTER STATISTICS")
    print("=" * 70)

    with rasterio.open(FLOW_ACC) as src:

        accumulation = src.read(1, masked=True)

        valid_accumulation = accumulation.compressed()

        print(
            "Valid cells:",
            len(valid_accumulation)
        )

        print(
            "Minimum:",
            float(valid_accumulation.min())
        )

        print(
            "Maximum:",
            float(valid_accumulation.max())
        )

        print(
            "Mean:",
            float(valid_accumulation.mean())
        )
    # ---------------------------------------------------------
    # Save processing metadata
    # ---------------------------------------------------------

    metadata = {
        "project": "NEERAKSH",
        "location": "Mettur",
        "source_dem": str(DEM),
        "dam_coordinate": {
            "latitude": DAM_LAT,
            "longitude": DAM_LON
        },
        "outputs": {
            "filled_dem": str(FILLED_DEM),
            "flow_direction": str(FLOW_DIR),
            "flow_accumulation": str(FLOW_ACC)
        },
        "method": {
            "depression_filling": "WhiteboxTools FillDepressions",
            "flow_direction": "D8",
            "flow_accumulation": "D8 cell accumulation"
        },
        "data_policy": (
            "Terrain-derived products are calculated "
            "from the downloaded ISRO/NRSC CartoDEM."
        )
    }

    metadata_path = (
        OUT / "mettur_drainage_metadata.json"
    )

    with open(
        metadata_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            metadata,
            f,
            indent=2
        )

    print("\n")
    print("=" * 70)
    print("DRAINAGE PROCESSING COMPLETE")
    print("=" * 70)

    print("\nGenerated files:")

    for path in [
        FILLED_DEM,
        FLOW_DIR,
        FLOW_ACC,
        metadata_path
    ]:

        print(path)

    print("\n")


if __name__ == "__main__":
    main()