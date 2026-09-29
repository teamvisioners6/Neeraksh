from pathlib import Path

from whitebox.whitebox_tools import WhiteboxTools


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

FILLED_DEM = (
    OUTPUT_DIR
    / "mettur_filled_dem.tif"
)

FLOW_DIRECTION = (
    OUTPUT_DIR
    / "mettur_flow_direction.tif"
)

FLOW_ACCUMULATION = (
    OUTPUT_DIR
    / "mettur_flow_accumulation.tif"
)


def main():

    print("=" * 70)
    print("NEERAKSH - CORRECT METTUR HYDROLOGICAL PROCESSING")
    print("=" * 70)

    if not DEM.exists():
        raise FileNotFoundError(
            f"DEM not found:\n{DEM}"
        )

    wbt = WhiteboxTools()

    wbt.set_verbose_mode(True)

    print("\nINPUT DEM")
    print("-" * 70)
    print(DEM)

    # ----------------------------------------------------------
    # 1. Fill depressions
    # ----------------------------------------------------------

    print("\n1. FILLING DEPRESSIONS")
    print("-" * 70)

    result = wbt.fill_depressions(
        dem=str(DEM),
        output=str(FILLED_DEM)
    )

    if result != 0:
        raise RuntimeError(
            f"FillDepressions failed with code {result}"
        )

    if not FILLED_DEM.exists():
        raise RuntimeError(
            "Filled DEM was not created."
        )

    print("\nFilled DEM created:")
    print(FILLED_DEM)

    # ----------------------------------------------------------
    # 2. D8 flow direction
    # ----------------------------------------------------------

    print("\n2. D8 FLOW DIRECTION")
    print("-" * 70)

    result = wbt.d8_pointer(
        dem=str(FILLED_DEM),
        output=str(FLOW_DIRECTION)
    )

    if result != 0:
        raise RuntimeError(
            f"D8Pointer failed with code {result}"
        )

    if not FLOW_DIRECTION.exists():
        raise RuntimeError(
            "Flow direction raster was not created."
        )

    print("\nFlow direction created:")
    print(FLOW_DIRECTION)

    # ----------------------------------------------------------
    # 3. D8 flow accumulation
    # ----------------------------------------------------------

    print("\n3. D8 FLOW ACCUMULATION")
    print("-" * 70)

    # Use positional argument for the input raster.
    # This avoids the API difference between Whitebox versions.
    result = wbt.d8_flow_accumulation(
        str(FILLED_DEM),
        str(FLOW_ACCUMULATION),
        out_type="cells",
        log=False,
        clip=False
    )

    if result != 0:
        raise RuntimeError(
            f"D8FlowAccumulation failed with code {result}"
        )

    if not FLOW_ACCUMULATION.exists():
        raise RuntimeError(
            "Flow accumulation raster was not created."
        )

    print("\nFlow accumulation created:")
    print(FLOW_ACCUMULATION)

    print("\n" + "=" * 70)
    print("HYDROLOGICAL PROCESSING COMPLETE")
    print("=" * 70)

    print("\nGENERATED:")
    print(FILLED_DEM)
    print(FLOW_DIRECTION)
    print(FLOW_ACCUMULATION)


if __name__ == "__main__":
    main()