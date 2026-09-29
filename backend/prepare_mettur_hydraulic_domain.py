import geopandas as gpd
import rasterio
from rasterio.mask import mask
from shapely.geometry import box
from pathlib import Path
import numpy as np

# ============================================================
# NEERAKSH
# REAL METTUR DOWNSTREAM HYDRAULIC DOMAIN PREPARATION
# ============================================================

BASE = Path(r"C:\NEERAKSH-1")

DEM = BASE / "data" / "dem" / "mettur" / "mettur_correct_dem_30m.tif"

RIVERS = (
    BASE / "gis" / "processed" / "mettur" /
    "mettur_hydrorivers_local.shp"
)

OUTPUT = BASE / "simulations" / "inputs" / "mettur"
OUTPUT.mkdir(parents=True, exist_ok=True)

# Official Mettur / Stanley Reservoir dam
DAM_LAT = 11.8030556
DAM_LON = 77.8066667

# ============================================================
# 1. Read HydroRIVERS
# ============================================================

print("=" * 70)
print("NEERAKSH - METTUR HYDRAULIC DOMAIN PREPARATION")
print("=" * 70)

print("\nLoading HydroRIVERS...")
rivers = gpd.read_file(RIVERS)

print("River features:", len(rivers))
print("CRS:", rivers.crs)

# ============================================================
# 2. Keep the main HydroRIVERS system
# ============================================================

if "MAIN_RIV" in rivers.columns:

    main_river_id = rivers.loc[
        rivers.geometry.distance(
            gpd.GeoSeries.from_xy(
                [DAM_LON],
                [DAM_LAT],
                crs="EPSG:4326"
            ).iloc[0]
        ).idxmin(),
        "MAIN_RIV"
    ]

    print("\nMain river identified from nearest HydroRIVERS reach:")
    print("MAIN_RIV:", main_river_id)

    main_river = rivers[
        rivers["MAIN_RIV"] == main_river_id
    ].copy()

else:
    main_river = rivers.copy()

print("Main-river features:", len(main_river))

# ============================================================
# 3. Save main river network
# ============================================================

main_river_output = OUTPUT / "mettur_main_hydrorivers.gpkg"

main_river.to_file(
    main_river_output,
    layer="main_river",
    driver="GPKG"
)

print("\nSaved:")
print(main_river_output)

# ============================================================
# 4. Create downstream corridor around the validated river
# ============================================================

# Use the validated HydroRIVERS geometry itself to define
# a conservative hydraulic corridor.
#
# 10 km corridor around the main river.
# This is a MODEL DOMAIN, not a claim about actual flood extent.

main_river_utm = main_river.to_crs("EPSG:32643")

corridor = main_river_utm.geometry.buffer(10000)

corridor_union = corridor.union_all()

corridor_gdf = gpd.GeoDataFrame(
    {"name": ["Mettur downstream hydraulic domain"]},
    geometry=[corridor_union],
    crs="EPSG:32643"
)

corridor_wgs84 = corridor_gdf.to_crs("EPSG:4326")

corridor_output = OUTPUT / "mettur_hydraulic_domain.gpkg"

corridor_wgs84.to_file(
    corridor_output,
    layer="hydraulic_domain",
    driver="GPKG"
)

print("\nSaved hydraulic domain:")
print(corridor_output)

# ============================================================
# 5. Crop DEM to hydraulic domain
# ============================================================

print("\nCropping real CartoDEM...")

with rasterio.open(DEM) as src:

    domain_geom = [
        corridor_wgs84.geometry.iloc[0]
    ]

    clipped, transform = mask(
        src,
        domain_geom,
        crop=True,
        nodata=src.nodata
    )

    profile = src.profile.copy()

    profile.update(
        height=clipped.shape[1],
        width=clipped.shape[2],
        transform=transform,
        compress="deflate",
        predictor=2
    )

    domain_dem = OUTPUT / "mettur_hydraulic_domain_dem_30m.tif"

    with rasterio.open(
        domain_dem,
        "w",
        **profile
    ) as dst:

        dst.write(clipped)

print("\nSaved hydraulic DEM:")
print(domain_dem)

# ============================================================
# 6. DEM statistics
# ============================================================

data = clipped[0]

if src.nodata is not None:
    valid = data[data != src.nodata]
else:
    valid = data[np.isfinite(data)]

valid = valid[np.isfinite(valid)]

print("\nHYDRAULIC DOMAIN DEM STATISTICS")
print("-" * 50)
print("Rows:", clipped.shape[1])
print("Columns:", clipped.shape[2])
print("Valid cells:", len(valid))
print("Minimum elevation:", float(valid.min()))
print("Maximum elevation:", float(valid.max()))
print("Mean elevation:", float(valid.mean()))
print("Median elevation:", float(np.median(valid)))

# ============================================================
# 7. Save metadata
# ============================================================

metadata = OUTPUT / "mettur_hydraulic_domain_metadata.txt"

with open(metadata, "w", encoding="utf-8") as f:

    f.write("NEERAKSH - METTUR HYDRAULIC DOMAIN\n")
    f.write("=" * 60 + "\n\n")

    f.write(f"DEM source: {DEM}\n")
    f.write(f"HydroRIVERS source: {RIVERS}\n")
    f.write(f"Dam latitude: {DAM_LAT}\n")
    f.write(f"Dam longitude: {DAM_LON}\n")
    f.write(f"MAIN_RIV: {main_river_id}\n")
    f.write(f"Hydraulic corridor buffer: 10 km\n")
    f.write(f"DEM CRS: EPSG:4326\n")
    f.write(f"DEM rows: {clipped.shape[1]}\n")
    f.write(f"DEM columns: {clipped.shape[2]}\n")
    f.write(f"Valid cells: {len(valid)}\n")
    f.write(f"Minimum elevation: {float(valid.min())}\n")
    f.write(f"Maximum elevation: {float(valid.max())}\n")
    f.write(f"Mean elevation: {float(valid.mean())}\n")
    f.write(f"Median elevation: {float(np.median(valid))}\n")

print("\nSaved metadata:")
print(metadata)

print("\n" + "=" * 70)
print("HYDRAULIC DOMAIN PREPARATION COMPLETE")
print("=" * 70)
