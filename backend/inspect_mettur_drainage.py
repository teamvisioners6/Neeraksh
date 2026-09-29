import rasterio
import numpy as np

ACCUMULATION = r"C:\NEERAKSH-1\simulations\terrain\mettur_flow_accumulation.tif"

DAM_LAT = 11.679444
DAM_LON = 77.567222

SEARCH_RADIUS_PIXELS = 120


with rasterio.open(ACCUMULATION) as src:

    acc = src.read(1, masked=True)

    dam_row, dam_col = src.index(
        DAM_LON,
        DAM_LAT
    )

    r0 = max(0, dam_row - SEARCH_RADIUS_PIXELS)
    r1 = min(src.height, dam_row + SEARCH_RADIUS_PIXELS + 1)

    c0 = max(0, dam_col - SEARCH_RADIUS_PIXELS)
    c1 = min(src.width, dam_col + SEARCH_RADIUS_PIXELS + 1)

    local = acc[r0:r1, c0:c1]

    rows, cols = np.where(~local.mask)
    values = local.data[rows, cols]

    order = np.argsort(values)[::-1]

    print("=" * 70)
    print("NEERAKSH - METTUR LOCAL DRAINAGE INSPECTION")
    print("=" * 70)

    print()
    print("DAM COORDINATE")
    print("-" * 70)
    print("Latitude:", DAM_LAT)
    print("Longitude:", DAM_LON)
    print("Raster row:", dam_row)
    print("Raster column:", dam_col)
    print(
        "Accumulation at dam cell:",
        float(acc[dam_row, dam_col])
    )

    print()
    print("LOCAL SEARCH")
    print("-" * 70)
    print(
        "Radius:",
        SEARCH_RADIUS_PIXELS,
        "pixels (~3.6 km)"
    )
    print("Valid cells:", len(values))
    print("Local maximum:", float(values.max()))

    print()
    print("TOP ACCUMULATION CELLS")
    print("-" * 70)

    shown = 0
    seen = set()

    for idx in order:

        r = int(rows[idx] + r0)
        c = int(cols[idx] + c0)

        value = float(acc[r, c])

        lon, lat = src.xy(r, c)

        key = (
            round(lat, 4),
            round(lon, 4)
        )

        if key in seen:
            continue

        seen.add(key)

        print(
            f"ACC={value:.0f} "
            f"ROW={r} "
            f"COL={c} "
            f"LAT={lat:.6f} "
            f"LON={lon:.6f}"
        )

        shown += 1

        if shown >= 20:
            break

print()
print("=" * 70)
print("INSPECTION COMPLETE")
print("=" * 70)