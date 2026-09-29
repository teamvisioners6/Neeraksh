import geopandas as gpd
from pathlib import Path
import math
import json


BASE = Path(r"C:\NEERAKSH-1")

INPUT = (
    BASE /
    "gis" /
    "raw" /
    "dam" /
    "mettur_nwdp_dam.shp"
)

OUTPUT_DIR = (
    BASE /
    "gis" /
    "processed" /
    "mettur"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_JSON = (
    OUTPUT_DIR /
    "mettur_official_dam_reference.json"
)


# Official coordinate published in NWDP record
OFFICIAL_LAT = 11.8030555556
OFFICIAL_LON = 77.8066666667


g = gpd.read_file(INPUT)

if len(g) != 1:
    raise RuntimeError(
        f"Expected exactly one Mettur record, got {len(g)}"
    )

row = g.iloc[0]

# Convert geometry to WGS84
g_wgs = g.to_crs(4326)

point = g_wgs.geometry.iloc[0]

geometry_lat = point.y
geometry_lon = point.x


# Haversine distance
R = 6371000.0

lat1 = math.radians(OFFICIAL_LAT)
lat2 = math.radians(geometry_lat)

dlat = math.radians(
    geometry_lat - OFFICIAL_LAT
)

dlon = math.radians(
    geometry_lon - OFFICIAL_LON
)

a = (
    math.sin(dlat / 2) ** 2
    +
    math.cos(lat1)
    * math.cos(lat2)
    * math.sin(dlon / 2) ** 2
)

distance_m = (
    2
    * R
    * math.asin(
        math.sqrt(a)
    )
)


result = {

    "source": {
        "organization":
            "National Water Data Portal / NWIC",

        "dataset":
            "DAM",

        "pic":
            str(row["PIC"])
    },

    "dam": {
        "name":
            str(row["dm_name"]),

        "district":
            str(row["district"]),

        "state":
            str(row["state"]),

        "river":
            str(row["river"]),

        "height_m":
            float(row["ht_found"]),

        "frl_m":
            float(row["frl"]),

        "gross_storage_mcm":
            float(row["gs_st_cap"]),

        "spillway_capacity":
            float(row["ds_sp_cap"]),

        "latitude":
            OFFICIAL_LAT,

        "longitude":
            OFFICIAL_LON
    },

    "geometry_validation": {

        "geometry_type":
            point.geom_type,

        "geometry_latitude":
            geometry_lat,

        "geometry_longitude":
            geometry_lon,

        "distance_between_record_coordinate_and_geometry_m":
            distance_m
    },

    "important_limitations": [

        "NWDP record provides a dam reference point, not a dam crest line.",

        "NWDP dm_length is 0 in the Mettur record and is therefore not used.",

        "The NWDP point is not interpreted as a breach location.",

        "Breach location and breach invert remain engineering scenario inputs.",

        "No breach geometry is inferred from the CartoDEM."
    ]
}


with open(
    OUTPUT_JSON,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        result,
        f,
        indent=2
    )


print("=" * 70)
print("NEERAKSH — OFFICIAL METTUR DAM VALIDATION")
print("=" * 70)

print()
print("PIC:", row["PIC"])
print("Dam:", row["dm_name"])
print("River:", row["river"])
print("District:", row["district"])

print()
print("Official coordinate:")
print(
    OFFICIAL_LAT,
    OFFICIAL_LON
)

print()
print("Geometry coordinate:")
print(
    geometry_lat,
    geometry_lon
)

print()
print(
    "Coordinate difference:",
    distance_m,
    "m"
)

print()
print("Geometry type:", point.geom_type)

print()
print("NWDP dam height:", row["ht_found"], "m")
print("NWDP FRL:", row["frl"], "m")
print("NWDP storage:", row["gs_st_cap"], "MCM")
print("NWDP spillway:", row["ds_sp_cap"])

print()
print("IMPORTANT:")
print(
    "This point is an official dam reference point, "
    "NOT a breach location."
)

print()
print("Saved:")
print(OUTPUT_JSON)
