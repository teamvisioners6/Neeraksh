import geopandas as gpd
import pandas as pd
from pathlib import Path

# ============================================================
# NEERAKSH - Mettur HydroRIVERS Validation
# ============================================================

HYDRORIVERS = Path(
    r"C:\NEERAKSH-1\data\hydrosheds\hydrorivers\asia\HydroRIVERS_v10_shp\HydroRIVERS_v10_as.shp"
)

# Actual path discovered on this machine
HYDRORIVERS = Path(
    r"C:\NEERAKSH-1\data\hydrosheds\hydrorivers\asia\HydroRIVERS_v10_as_shp\HydroRIVERS_v10_as.shp"
)

OUTPUT_DIR = Path(r"C:\NEERAKSH-1\gis\processed\mettur")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Official Mettur / Stanley Reservoir dam coordinate
DAM_LAT = 11.8030556
DAM_LON = 77.8066667

# High-accumulation corridor identified from our CartoDEM analysis
CANDIDATE_LAT = 11.747634
CANDIDATE_LON = 77.787641

# Search radius in degrees (~20 km)
SEARCH_RADIUS_DEG = 0.20

print("=" * 70)
print("NEERAKSH - HYDRORIVERS / METTUR VALIDATION")
print("=" * 70)

print("\nHydroRIVERS:")
print(HYDRORIVERS)

if not HYDRORIVERS.exists():
    raise FileNotFoundError(f"HydroRIVERS file not found: {HYDRORIVERS}")

# ------------------------------------------------------------
# 1. Read only the Mettur-area portion
# ------------------------------------------------------------

bbox = (
    DAM_LON - SEARCH_RADIUS_DEG,
    DAM_LAT - SEARCH_RADIUS_DEG,
    DAM_LON + SEARCH_RADIUS_DEG,
    DAM_LAT + SEARCH_RADIUS_DEG,
)

print("\nReading HydroRIVERS around Mettur...")
print("Bounding box:", bbox)

rivers = gpd.read_file(HYDRORIVERS, bbox=bbox)

print("\nHYDRORIVERS LOADED")
print("Records:", len(rivers))
print("CRS:", rivers.crs)
print("Columns:")
print(list(rivers.columns))

if len(rivers) == 0:
    raise RuntimeError("No HydroRIVERS features found in the Mettur search area.")

# ------------------------------------------------------------
# 2. Ensure geographic CRS
# ------------------------------------------------------------

if rivers.crs is None:
    raise RuntimeError("HydroRIVERS has no CRS information.")

rivers_wgs84 = rivers.to_crs("EPSG:4326")

# ------------------------------------------------------------
# 3. Create official dam point
# ------------------------------------------------------------

dam = gpd.GeoDataFrame(
    {
        "name": ["Stanley Reservoir / Mettur Dam"],
        "latitude": [DAM_LAT],
        "longitude": [DAM_LON],
    },
    geometry=gpd.points_from_xy([DAM_LON], [DAM_LAT]),
    crs="EPSG:4326",
)

candidate = gpd.GeoDataFrame(
    {
        "name": ["CartoDEM high-accumulation candidate"],
        "latitude": [CANDIDATE_LAT],
        "longitude": [CANDIDATE_LON],
    },
    geometry=gpd.points_from_xy(
        [CANDIDATE_LON],
        [CANDIDATE_LAT]
    ),
    crs="EPSG:4326",
)

# ------------------------------------------------------------
# 4. Reproject to UTM 43N for accurate metre distances
# ------------------------------------------------------------

rivers_utm = rivers_wgs84.to_crs("EPSG:32643")
dam_utm = dam.to_crs("EPSG:32643")
candidate_utm = candidate.to_crs("EPSG:32643")

# ------------------------------------------------------------
# 5. Distance from official Mettur Dam
# ------------------------------------------------------------

dam_point = dam_utm.geometry.iloc[0]

rivers_utm["distance_from_dam_m"] = rivers_utm.geometry.distance(dam_point)
rivers_utm["distance_from_dam_km"] = (
    rivers_utm["distance_from_dam_m"] / 1000.0
)

nearest_dam = rivers_utm.sort_values(
    "distance_from_dam_m"
).head(20)

print("\n" + "=" * 70)
print("NEAREST HYDRORIVERS REACHES TO OFFICIAL METTUR DAM")
print("=" * 70)

display_cols = [
    c for c in [
        "HYRIV_ID",
        "NEXT_DOWN",
        "MAIN_RIV",
        "ORD_STRA",
        "ORD_CLAS",
        "DIS_AV_CMS",
        "DIST_DN_KM",
        "distance_from_dam_km",
    ]
    if c in nearest_dam.columns
]

if display_cols:
    print(nearest_dam[display_cols].to_string(index=False))
else:
    print(
        nearest_dam[
            ["distance_from_dam_km"]
        ].to_string(index=False)
    )

# ------------------------------------------------------------
# 6. Distance from CartoDEM high-accumulation candidate
# ------------------------------------------------------------

candidate_point = candidate_utm.geometry.iloc[0]

rivers_utm["distance_from_candidate_m"] = (
    rivers_utm.geometry.distance(candidate_point)
)

rivers_utm["distance_from_candidate_km"] = (
    rivers_utm["distance_from_candidate_m"] / 1000.0
)

nearest_candidate = rivers_utm.sort_values(
    "distance_from_candidate_m"
).head(20)

print("\n" + "=" * 70)
print("NEAREST HYDRORIVERS REACHES TO CARTODEM CANDIDATE")
print("=" * 70)

display_cols_candidate = [
    c for c in [
        "HYRIV_ID",
        "NEXT_DOWN",
        "MAIN_RIV",
        "ORD_STRA",
        "ORD_CLAS",
        "DIS_AV_CMS",
        "DIST_DN_KM",
        "distance_from_candidate_km",
    ]
    if c in nearest_candidate.columns
]

if display_cols_candidate:
    print(
        nearest_candidate[
            display_cols_candidate
        ].to_string(index=False)
    )
else:
    print(
        nearest_candidate[
            ["distance_from_candidate_km"]
        ].to_string(index=False)
    )

# ------------------------------------------------------------
# 7. Save local HydroRIVERS network
# ------------------------------------------------------------

local_output = OUTPUT_DIR / "mettur_hydrorivers_local.shp"

rivers_wgs84.to_file(
    local_output,
    driver="ESRI Shapefile",
)

print("\nSaved local HydroRIVERS:")
print(local_output)

# ------------------------------------------------------------
# 8. Save nearest reaches to dam
# ------------------------------------------------------------

nearest_dam_wgs84 = nearest_dam.to_crs("EPSG:4326")

nearest_dam_output = OUTPUT_DIR / "mettur_nearest_hydrorivers_to_dam.shp"

nearest_dam_wgs84.to_file(
    nearest_dam_output,
    driver="ESRI Shapefile",
)

print("\nSaved nearest reaches to dam:")
print(nearest_dam_output)

# ------------------------------------------------------------
# 9. Save nearest reaches to CartoDEM candidate
# ------------------------------------------------------------

nearest_candidate_wgs84 = nearest_candidate.to_crs("EPSG:4326")

nearest_candidate_output = (
    OUTPUT_DIR /
    "mettur_nearest_hydrorivers_to_cartodem_candidate.shp"
)

nearest_candidate_wgs84.to_file(
    nearest_candidate_output,
    driver="ESRI Shapefile",
)

print("\nSaved nearest reaches to CartoDEM candidate:")
print(nearest_candidate_output)

# ------------------------------------------------------------
# 10. Create machine-readable validation summary
# ------------------------------------------------------------

summary = {
    "hydrorivers_source": str(HYDRORIVERS),
    "hydrorivers_features_in_search_area": int(len(rivers)),
    "dam_latitude": DAM_LAT,
    "dam_longitude": DAM_LON,
    "cartodem_candidate_latitude": CANDIDATE_LAT,
    "cartodem_candidate_longitude": CANDIDATE_LON,
    "nearest_hydrorivers_distance_to_dam_km": float(
        nearest_dam.iloc[0]["distance_from_dam_km"]
    ),
    "nearest_hydrorivers_distance_to_cartodem_candidate_km": float(
        nearest_candidate.iloc[0]["distance_from_candidate_km"]
    ),
}

summary_path = OUTPUT_DIR / "hydrorivers_validation_summary.txt"

with open(summary_path, "w", encoding="utf-8") as f:
    for key, value in summary.items():
        f.write(f"{key}={value}\n")

print("\nSaved validation summary:")
print(summary_path)

print("\n" + "=" * 70)
print("HYDRORIVERS VALIDATION COMPLETE")
print("=" * 70)
