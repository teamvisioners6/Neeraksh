import geopandas as gpd
from pathlib import Path

BASE = Path(r"C:\NEERAKSH-1")

src = (
    BASE /
    "gis" /
    "raw" /
    "dam" /
    "mettur_nwdp_dam.shp"
)

out_dir = (
    BASE /
    "gis" /
    "processed" /
    "mettur"
)

out_dir.mkdir(
    parents=True,
    exist_ok=True
)

g = gpd.read_file(src)

g = g.to_crs(4326)

# Preserve only the official Mettur record.
g = g[g["PIC"].astype(str) == "TN12HH0005"].copy()

if len(g) != 1:
    raise RuntimeError(
        f"Expected one Mettur record, found {len(g)}"
    )

output = (
    out_dir /
    "mettur_official_dam_reference.geojson"
)

g.to_file(
    output,
    driver="GeoJSON"
)

print("=" * 70)
print("NEERAKSH — OFFICIAL METTUR DAM REFERENCE")
print("=" * 70)

print("Records:", len(g))
print("CRS:", g.crs)
print("Geometry:", g.geometry.iloc[0])
print("PIC:", g["PIC"].iloc[0])
print("Dam:", g["dm_name"].iloc[0])

print()
print("Saved:")
print(output)
