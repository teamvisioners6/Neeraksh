from pathlib import Path
import rasterio
from rasterio.transform import rowcol

DEM = Path(
    r"C:\NEERAKSH-1\data\dem\varattupallam"
    r"\varattupallam_cartodem_30m_nodata_clean.tif"
)

LAT = 11.6755867
LON = 77.5608833

with rasterio.open(DEM) as src:

    print("=" * 60)
    print("NEERAKSH — VARATTUPALLAM DEM POINT VALIDATION")
    print("=" * 60)

    print("DEM:", DEM)
    print("CRS:", src.crs)
    print("Study latitude:", LAT)
    print("Study longitude:", LON)

    if not (
        src.bounds.left <= LON <= src.bounds.right
        and src.bounds.bottom <= LAT <= src.bounds.top
    ):
        raise RuntimeError(
            "CWC study coordinate is outside the DEM."
        )

    row, col = rowcol(src.transform, LON, LAT)

    value = src.read(1)[row, col]

    print()
    print("Raster row:", row)
    print("Raster column:", col)
    print("DEM elevation at study point:", float(value), "m")

    if value <= -9990:
        raise RuntimeError(
            "Study point falls on NoData."
        )

    lon_center, lat_center = src.xy(row, col)

    print("Cell longitude:", lon_center)
    print("Cell latitude:", lat_center)
    print("Cell elevation:", float(value), "m")

    print()
    print("STATUS: VALID DEM CELL")
    print("=" * 60)
