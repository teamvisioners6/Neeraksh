import rasterio
import numpy as np
from math import radians, sin, cos, sqrt, atan2


ACCUMULATION = r"C:\NEERAKSH-1\simulations\terrain\mettur_flow_accumulation.tif"

DAM_LAT = 11.679444
DAM_LON = 77.567222

# Use the 99th percentile as an INSPECTION threshold.
# This is not being presented as a calibrated river threshold.
PERCENTILE = 99.0


def haversine(lat1, lon1, lat2, lon2):

    R = 6371000.0

    p1 = radians(lat1)
    p2 = radians(lat2)

    dp = radians(lat2 - lat1)
    dl = radians(lon2 - lon1)

    a = (
        sin(dp / 2) ** 2
        + cos(p1)
        * cos(p2)
        * sin(dl / 2) ** 2
    )

    return 2 * R * atan2(
        sqrt(a),
        sqrt(1 - a)
    )


def bearing(lat1, lon1, lat2, lon2):

    p1 = radians(lat1)
    p2 = radians(lat2)

    dl = radians(lon2 - lon1)

    y = sin(dl) * cos(p2)

    x = (
        cos(p1) * sin(p2)
        - sin(p1) * cos(p2) * cos(dl)
    )

    angle = np.degrees(
        atan2(y, x)
    )

    return (angle + 360) % 360


with rasterio.open(ACCUMULATION) as src:

    acc = src.read(1, masked=True)

    valid = acc.compressed()

    threshold = np.percentile(
        valid,
        PERCENTILE
    )

    dam_row, dam_col = src.index(
        DAM_LON,
        DAM_LAT
    )

    rows, cols = np.where(
        (~acc.mask)
        & (acc >= threshold)
    )

    print("=" * 70)
    print("NEERAKSH - METTUR HIGH-ACCUMULATION CHANNEL ANALYSIS")
    print("=" * 70)

    print()
    print("DAM")
    print("-" * 70)
    print("Latitude:", DAM_LAT)
    print("Longitude:", DAM_LON)
    print("Row:", dam_row)
    print("Column:", dam_col)

    print()
    print("ACCUMULATION DISTRIBUTION")
    print("-" * 70)
    print("Valid cells:", len(valid))
    print("Percentile:", PERCENTILE)
    print("Inspection threshold:", threshold)
    print("Maximum:", float(valid.max()))

    # ---------------------------------------------------------
    # Find closest high-accumulation cell to dam
    # ---------------------------------------------------------

    best = None

    for r, c in zip(rows, cols):

        lon, lat = src.xy(
            int(r),
            int(c)
        )

        distance = haversine(
            DAM_LAT,
            DAM_LON,
            lat,
            lon
        )

        if best is None or distance < best["distance_m"]:

            best = {
                "row": int(r),
                "col": int(c),
                "lat": lat,
                "lon": lon,
                "accumulation": float(acc[r, c]),
                "distance_m": distance
            }

    print()
    print("NEAREST HIGH-ACCUMULATION CELL")
    print("-" * 70)

    print("Latitude:", best["lat"])
    print("Longitude:", best["lon"])
    print(
        "Accumulation:",
        best["accumulation"]
    )
    print(
        "Distance from dam:",
        round(best["distance_m"], 2),
        "m"
    )

    print(
        "Bearing from dam:",
        round(
            bearing(
                DAM_LAT,
                DAM_LON,
                best["lat"],
                best["lon"]
            ),
            2
        ),
        "degrees"
    )

    # ---------------------------------------------------------
    # Find strongest cell within 5 km
    # ---------------------------------------------------------

    candidate_cells = []

    for r, c in zip(rows, cols):

        lon, lat = src.xy(
            int(r),
            int(c)
        )

        distance = haversine(
            DAM_LAT,
            DAM_LON,
            lat,
            lon
        )

        if distance <= 5000:

            candidate_cells.append(
                (
                    float(acc[r, c]),
                    lat,
                    lon,
                    distance
                )
            )

    candidate_cells.sort(
        reverse=True,
        key=lambda x: x[0]
    )

    print()
    print("STRONGEST HIGH-ACCUMULATION CELLS WITHIN 5 KM")
    print("-" * 70)

    for value, lat, lon, distance in candidate_cells[:15]:

        print(
            f"ACC={value:.0f} "
            f"LAT={lat:.6f} "
            f"LON={lon:.6f} "
            f"DIST={distance:.1f}m"
        )

print()
print("=" * 70)
print("ANALYSIS COMPLETE")
print("=" * 70)