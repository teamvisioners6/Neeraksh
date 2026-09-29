from pathlib import Path
import json

import numpy as np
import rasterio
from rasterio.features import shapes
import geopandas as gpd
from shapely.geometry import shape


# ============================================================
# NEERAKSH — METTUR GIS OUTPUT EXPORTER
# ============================================================

BASE = Path(r"C:\NEERAKSH-1")

SOLVER_OUTPUT = (
    BASE
    / "simulations"
    / "outputs"
    / "mettur"
    / "solver"
)

GIS_OUTPUT = (
    BASE
    / "gis"
    / "outputs"
    / "mettur"
)

GIS_OUTPUT.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# INPUT / OUTPUT FILES
# ============================================================

MAX_DEPTH = (
    SOLVER_OUTPUT
    / "maximum_flood_depth_m.tif"
)

MAX_VELOCITY = (
    SOLVER_OUTPUT
    / "maximum_velocity_ms.tif"
)

ARRIVAL_TIME = (
    SOLVER_OUTPUT
    / "arrival_time_s.tif"
)

FINAL_WSE = (
    SOLVER_OUTPUT
    / "final_water_surface_elevation_m.tif"
)

FLOOD_SHP = (
    GIS_OUTPUT
    / "mettur_flood_inundation.shp"
)

FLOOD_KML = (
    GIS_OUTPUT
    / "mettur_flood_inundation.kml"
)

GIS_STATUS = (
    GIS_OUTPUT
    / "gis_export_status.json"
)


# ============================================================
# UTILITY
# ============================================================

def write_status(data):

    with open(
        GIS_STATUS,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=2
        )


# ============================================================
# CHECK RASTER
# ============================================================

def inspect_raster(path):

    if not path.exists():

        return None

    with rasterio.open(
        path
    ) as src:

        array = src.read(
            1
        ).astype(
            np.float64
        )

        nodata = src.nodata

        if nodata is not None:

            array[
                array == nodata
            ] = np.nan

        valid = np.isfinite(
            array
        )

        if not np.any(valid):

            return {
                "path":
                    str(path),

                "valid":
                    False,

                "reason":
                    "Raster contains no valid cells."
            }

        return {

            "path":
                str(path),

            "valid":
                True,

            "crs":
                str(
                    src.crs
                ),

            "rows":
                int(
                    src.height
                ),

            "columns":
                int(
                    src.width
                ),

            "min":
                float(
                    np.nanmin(
                        array
                    )
                ),

            "max":
                float(
                    np.nanmax(
                        array
                    )
                ),

            "mean":
                float(
                    np.nanmean(
                        array
                    )
                )
        }


# ============================================================
# FLOOD RASTER → POLYGON
# ============================================================

def flood_raster_to_polygon(
    raster_path,
    threshold=0.01
):

    with rasterio.open(
        raster_path
    ) as src:

        raster = src.read(
            1
        ).astype(
            np.float32
        )

        nodata = src.nodata

        if nodata is not None:

            raster[
                raster == nodata
            ] = np.nan

        flooded = (
            np.isfinite(raster)
            &
            (raster >= threshold)
        )

        if not np.any(
            flooded
        ):

            return None, src.crs

        polygons = []

        for geom, value in shapes(
            raster,
            mask=flooded,
            transform=src.transform
        ):

            if value >= threshold:

                polygons.append(
                    shape(
                        geom
                    )
                )

        if not polygons:

            return None, src.crs

        return (
            polygons,
            src.crs
        )


# ============================================================
# SAVE SHAPEFILE
# ============================================================

def save_shapefile(
    polygons,
    crs
):

    gdf = gpd.GeoDataFrame(
        {
            "class":
                ["flooded"] * len(polygons),

            "source":
                ["NEERAKSH_2D_HLL"] * len(polygons),

            "threshold_m":
                [0.01] * len(polygons)
        },
        geometry=polygons,
        crs=crs
    )

    # Repair minor polygon topology issues.
    gdf["geometry"] = (
        gdf.geometry
        .make_valid()
    )

    # Remove empty geometries.
    gdf = gdf[
        ~gdf.geometry.is_empty
    ].copy()

    if gdf.empty:

        raise RuntimeError(
            "No valid flood polygons remain."
        )

    gdf.to_file(
        FLOOD_SHP,
        driver="ESRI Shapefile"
    )

    return gdf


# ============================================================
# SAVE KML
# ============================================================

def save_kml(
    gdf
):

    # KML expects geographic coordinates.
    kml_gdf = gdf.to_crs(
        epsg=4326
    )

    # GeoPandas may not have KML driver enabled in every
    # environment. Try Fiona first.
    try:

        kml_gdf.to_file(
            FLOOD_KML,
            driver="KML"
        )

        return True

    except Exception as exc:

        print(
            "KML export unavailable:",
            exc
        )

        return False


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print(
        "NEERAKSH — METTUR GIS OUTPUT EXPORTER"
    )
    print("=" * 70)

    print()
    print(
        "Checking hydraulic solver outputs..."
    )

    rasters = {

        "maximum_flood_depth":
            MAX_DEPTH,

        "maximum_velocity":
            MAX_VELOCITY,

        "arrival_time":
            ARRIVAL_TIME,

        "final_water_surface_elevation":
            FINAL_WSE
    }

    raster_status = {}

    for name, path in rasters.items():

        info = inspect_raster(
            path
        )

        raster_status[
            name
        ] = info

        if info is None:

            print(
                f"{name}: NOT AVAILABLE"
            )

        elif not info["valid"]:

            print(
                f"{name}: INVALID"
            )

        else:

            print(
                f"{name}: AVAILABLE"
            )

            print(
                "  CRS:",
                info["crs"]
            )

            print(
                "  Min:",
                info["min"]
            )

            print(
                "  Max:",
                info["max"]
            )

    # ========================================================
    # FLOOD DEPTH REQUIRED
    # ========================================================

    if not MAX_DEPTH.exists():

        status = {

            "status":
                "BLOCKED_NO_SIMULATION_OUTPUT",

            "reason":
                "Maximum flood-depth raster does not exist. "
                "The hydraulic simulation has not produced "
                "a valid flood result.",

            "fabricated_values":
                False,

            "rasters":
                raster_status
        }

        write_status(
            status
        )

        print()
        print(
            "BLOCKED"
        )

        print(
            "No flood-depth raster exists."
        )

        print()
        print(
            "GIS export will NOT create fabricated flood polygons."
        )

        print()
        print(
            "Saved:"
        )

        print(
            GIS_STATUS
        )

        return

    # ========================================================
    # FLOOD POLYGON
    # ========================================================

    print()
    print(
        "CREATING FLOOD INUNDATION POLYGON"
    )

    polygons, crs = (
        flood_raster_to_polygon(
            MAX_DEPTH,
            threshold=0.01
        )
    )

    if polygons is None:

        status = {

            "status":
                "NO_FLOODED_CELLS",

            "reason":
                "The simulation raster contains no cells "
                "with flood depth >= 0.01 m.",

            "fabricated_values":
                False
        }

        write_status(
            status
        )

        print(
            "No flooded cells found."
        )

        return

    print(
        "Flood polygon parts:",
        len(polygons)
    )

    # ========================================================
    # SHAPEFILE
    # ========================================================

    gdf = save_shapefile(
        polygons,
        crs
    )

    print()
    print(
        "SHP CREATED:"
    )

    print(
        FLOOD_SHP
    )

    # ========================================================
    # KML
    # ========================================================

    kml_created = save_kml(
        gdf
    )

    if kml_created:

        print()
        print(
            "KML CREATED:"
        )

        print(
            FLOOD_KML
        )

    # ========================================================
    # FINAL STATUS
    # ========================================================

    status = {

        "status":
            "COMPLETED",

        "source":
            "NEERAKSH_2D_HLL",

        "flood_threshold_m":
            0.01,

        "polygon_count":
            len(gdf),

        "outputs":
            {

                "shapefile":
                    str(
                        FLOOD_SHP
                    ),

                "kml":
                    str(
                        FLOOD_KML
                    )
                    if kml_created
                    else None
            },

        "rasters":
            raster_status,

        "fabricated_values":
            False
    }

    write_status(
        status
    )

    print()
    print(
        "=" * 70
    )

    print(
        "GIS EXPORT COMPLETED"
    )

    print(
        "=" * 70
    )

    print()
    print(
        "Status:"
    )

    print(
        GIS_STATUS
    )


if __name__ == "__main__":

    main()