from pathlib import Path
import zipfile
import shutil

import geopandas as gpd


ROOT = Path(r"C:\NEERAKSH-1")

RESERVOIR_ZIP = Path(r"C:\Users\jeffr\Downloads\Reservoir.zip")

OUTPUT_DIR = ROOT / "gis" / "raw" / "reservoirs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_SHP = OUTPUT_DIR / "stanley_reservoir_mettur.shp"

TARGET_NAME = "Stanley Reservoir/Mettur"


def main():

    print("=" * 70)
    print("NEERAKSH - METTUR GOVERNMENT RESERVOIR GIS EXTRACTION")
    print("=" * 70)

    if not RESERVOIR_ZIP.exists():
        raise FileNotFoundError(
            f"Reservoir.zip not found:\n{RESERVOIR_ZIP}\n\n"
            "Change RESERVOIR_ZIP to the actual location of Reservoir.zip."
        )

    print("\nSOURCE")
    print("-" * 70)
    print(RESERVOIR_ZIP)

    print("\nREADING SHAPEFILE")
    print("-" * 70)

    gdf = gpd.read_file(
        f"zip://{RESERVOIR_ZIP}"
    )

    print("Total reservoir records:", len(gdf))
    print("CRS:", gdf.crs)

    matches = gdf[
        gdf["wbname"]
        .astype(str)
        .str.strip()
        .str.lower()
        == TARGET_NAME.lower()
    ].copy()

    if len(matches) == 0:
        raise RuntimeError(
            f"Could not find reservoir named: {TARGET_NAME}"
        )

    print("\nMATCH")
    print("-" * 70)
    print(matches[[
        "wbcode",
        "wbname",
        "state",
        "area_ha"
    ]].to_string(index=False))

    # Convert to WGS84 for NEERAKSH GIS usage
    matches = matches.to_crs("EPSG:4326")

    # Save only the Mettur reservoir
    matches.to_file(
        OUTPUT_SHP,
        driver="ESRI Shapefile"
    )

    # Correct government dam coordinate
    dam_lat = 11.8030556
    dam_lon = 77.8066667

    bounds = matches.total_bounds

    print("\nRESERVOIR BOUNDS")
    print("-" * 70)
    print("West :", bounds[0])
    print("South:", bounds[1])
    print("East :", bounds[2])
    print("North:", bounds[3])

    print("\nGOVERNMENT DAM COORDINATE")
    print("-" * 70)
    print("Latitude :", dam_lat)
    print("Longitude:", dam_lon)

    print("\nOUTPUT")
    print("-" * 70)
    print(OUTPUT_SHP)

    print("\nCOMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()