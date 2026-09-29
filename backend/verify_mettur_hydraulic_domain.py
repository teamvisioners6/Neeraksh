import geopandas as gpd
import rasterio
from rasterio.mask import mask
import numpy as np
from pathlib import Path

BASE = Path(r"C:\NEERAKSH-1")

RIVERS = BASE / "gis" / "processed" / "mettur" / "mettur_hydrorivers_local.shp"
DEM = BASE / "data" / "dem" / "mettur" / "mettur_correct_dem_30m.tif"

OUTPUT = BASE / "simulations" / "inputs" / "mettur"
OUTPUT.mkdir(parents=True, exist_ok=True)

DAM_LAT = 11.8030556
DAM_LON = 77.8066667

print("=" * 70)
print("NEERAKSH - METTUR HYDRAULIC DOMAIN VERIFICATION")
print("=" * 70)

# ------------------------------------------------------------
# 1. Load HydroRIVERS
# ------------------------------------------------------------

rivers = gpd.read_file(RIVERS)

print("\nHydroRIVERS:")
print("Records:", len(rivers))
print("CRS:", rivers.crs)

# ------------------------------------------------------------
# 2. Correct projected-distance calculation
# ------------------------------------------------------------

rivers_utm = rivers.to_crs("EPSG:32643")

dam = gpd.GeoDataFrame(
    {"name": ["Mettur Dam"]},
    geometry=gpd.points_from_xy(
        [DAM_LON],
        [DAM_LAT]
    ),
    crs="EPSG:4326"
)

dam_utm = dam.to_crs("EPSG:32643")

dam_point = dam_utm.geometry.iloc[0]

rivers_utm["distance_to_dam_m"] = (
    rivers_utm.geometry.distance(dam_point)
)

nearest_idx = rivers_utm["distance_to_dam_m"].idxmin()

nearest = rivers_utm.loc[nearest_idx]

main_river_id = nearest["MAIN_RIV"]

print("\nNearest HydroRIVERS reach:")
print("HYRIV_ID:", nearest["HYRIV_ID"])
print("MAIN_RIV:", main_river_id)
print(
    "Distance from dam:",
    round(float(nearest["distance_to_dam_m"]), 2),
    "m"
)

# ------------------------------------------------------------
# 3. Select the complete main river system
# ------------------------------------------------------------

main_river = rivers[
    rivers["MAIN_RIV"] == main_river_id
].copy()

print("\nMain river system:")
print("MAIN_RIV:", main_river_id)
print("Features:", len(main_river))

# ------------------------------------------------------------
# 4. Save validated main river
# ------------------------------------------------------------

main_output = OUTPUT / "mettur_main_hydrorivers.gpkg"

main_river.to_file(
    main_output,
    layer="main_river",
    driver="GPKG"
)

print("\nSaved:")
print(main_output)

# ------------------------------------------------------------
# 5. Build 10 km computational domain
# ------------------------------------------------------------

main_utm = main_river.to_crs("EPSG:32643")

buffer_10km = main_utm.geometry.buffer(10000)

domain_geom = buffer_10km.union_all()

domain = gpd.GeoDataFrame(
    {
        "name": ["Mettur Hydraulic Computational Domain"],
        "source": ["HydroRIVERS + CartoDEM"],
        "buffer_km": [10.0]
    },
    geometry=[domain_geom],
    crs="EPSG:32643"
)

domain_wgs84 = domain.to_crs("EPSG:4326")

domain_output = OUTPUT / "mettur_hydraulic_domain.gpkg"

domain_wgs84.to_file(
    domain_output,
    layer="hydraulic_domain",
    driver="GPKG"
)

print("\nSaved:")
print(domain_output)

# ------------------------------------------------------------
# 6. Crop DEM
# ------------------------------------------------------------

print("\nCropping CartoDEM to hydraulic domain...")

with rasterio.open(DEM) as src:

    geom = [domain_wgs84.geometry.iloc[0]]

    clipped, transform = mask(
        src,
        geom,
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

    output_dem = OUTPUT / "mettur_hydraulic_domain_dem_30m.tif"

    with rasterio.open(
        output_dem,
        "w",
        **profile
    ) as dst:
        dst.write(clipped)

# ------------------------------------------------------------
# 7. Verify DEM
# ------------------------------------------------------------

data = clipped[0]

if src.nodata is not None:
    valid = data[data != src.nodata]
else:
    valid = data[np.isfinite(data)]

valid = valid[np.isfinite(valid)]

print("\nHYDRAULIC DEM")
print("-" * 50)
print("CRS:", profile["crs"])
print("Rows:", clipped.shape[1])
print("Columns:", clipped.shape[2])
print("Resolution:", profile["transform"].a, profile["transform"].e)
print("Valid cells:", len(valid))
print("Minimum:", float(valid.min()))
print("Maximum:", float(valid.max()))
print("Mean:", float(valid.mean()))
print("Median:", float(np.median(valid)))

# ------------------------------------------------------------
# 8. Check dam location against hydraulic DEM
# ------------------------------------------------------------

with rasterio.open(output_dem) as src:

    row, col = src.index(
        DAM_LON,
        DAM_LAT
    )

    if (
        0 <= row < src.height
        and 0 <= col < src.width
    ):
        dam_elevation = float(
            src.read(1)[row, col]
        )

        print("\nDAM LOCATION CHECK")
        print("-" * 50)
        print("Dam latitude:", DAM_LAT)
        print("Dam longitude:", DAM_LON)
        print("Raster row:", row)
        print("Raster column:", col)
        print("DEM elevation:", dam_elevation, "m")
    else:
        print("\nWARNING: Dam coordinate is outside DEM.")

# ------------------------------------------------------------
# 9. Metadata
# ------------------------------------------------------------

metadata = OUTPUT / "mettur_hydraulic_domain_metadata.txt"

with open(metadata, "w", encoding="utf-8") as f:

    f.write("NEERAKSH - METTUR HYDRAULIC DOMAIN\n")
    f.write("=" * 60 + "\n")
    f.write("Data sources\n")
    f.write("- HydroRIVERS\n")
    f.write("- CartoDEM 30 m\n\n")

    f.write(f"Dam latitude={DAM_LAT}\n")
    f.write(f"Dam longitude={DAM_LON}\n")
    f.write(f"Nearest HYRIV_ID={nearest['HYRIV_ID']}\n")
    f.write(f"MAIN_RIV={main_river_id}\n")
    f.write(
        f"Distance from dam={float(nearest['distance_to_dam_m'])} m\n"
    )
    f.write("Hydraulic domain buffer=10 km\n")
    f.write(f"DEM rows={clipped.shape[1]}\n")
    f.write(f"DEM columns={clipped.shape[2]}\n")
    f.write(f"Valid cells={len(valid)}\n")
    f.write(f"Minimum elevation={float(valid.min())}\n")
    f.write(f"Maximum elevation={float(valid.max())}\n")
    f.write(f"Mean elevation={float(valid.mean())}\n")
    f.write(f"Median elevation={float(np.median(valid))}\n")

print("\nMetadata:")
print(metadata)

print("\n" + "=" * 70)
print("HYDRAULIC DOMAIN VERIFIED")
print("=" * 70)
