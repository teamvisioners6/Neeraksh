from pathlib import Path
import json
import numpy as np
import rasterio
from rasterio.transform import xy


ROOT = Path(r"C:\NEERAKSH-1")

DEM_PATH = (
    ROOT
    / "data"
    / "dem"
    / "mettur"
    / "mettur_dem_30m.tif"
)

OUTPUT_DIR = ROOT / "simulations" / "terrain"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DAM_LAT = 11.679444
DAM_LON = 77.567222


def calculate_slope(dem, transform):
    """
    Calculate approximate terrain slope in degrees
    from the real DEM.

    The DEM is in geographic coordinates (EPSG:4326),
    so horizontal distances are approximated locally.
    """

    lat = (transform.f + transform.e * dem.shape[0] / 2)

    meters_per_degree_lat = 111320.0
    meters_per_degree_lon = 111320.0 * np.cos(np.radians(lat))

    dx = abs(transform.a) * meters_per_degree_lon
    dy = abs(transform.e) * meters_per_degree_lat

    dz_dy, dz_dx = np.gradient(dem.astype(np.float64), dy, dx)

    slope_rad = np.arctan(
        np.sqrt(dz_dx ** 2 + dz_dy ** 2)
    )

    return np.degrees(slope_rad)


def main():

    if not DEM_PATH.exists():
        raise FileNotFoundError(
            f"DEM not found:\n{DEM_PATH}"
        )

    print("=" * 60)
    print("NEERAKSH - METTUR TERRAIN PROCESSOR")
    print("=" * 60)

    with rasterio.open(DEM_PATH) as src:

        dem = src.read(1, masked=True)

        print("\nDEM")
        print("-" * 60)
        print("CRS:", src.crs)
        print("Width:", src.width)
        print("Height:", src.height)
        print("Resolution:", src.res)
        print("Bounds:", src.bounds)

        valid = dem.compressed()

        print("Valid cells:", len(valid))
        print("Minimum elevation:", float(valid.min()), "m")
        print("Maximum elevation:", float(valid.max()), "m")
        print("Mean elevation:", float(valid.mean()), "m")

        # --------------------------------------------------
        # Locate Mettur dam
        # --------------------------------------------------

        row, col = src.index(DAM_LON, DAM_LAT)

        dam_elevation = float(dem[row, col])

        dam_x, dam_y = xy(
            src.transform,
            row,
            col,
            offset="center"
        )

        print("\nDAM LOCATION")
        print("-" * 60)
        print("Latitude:", DAM_LAT)
        print("Longitude:", DAM_LON)
        print("Raster row:", row)
        print("Raster column:", col)
        print("DEM elevation:", dam_elevation, "m")
        print(
            "Raster coordinate:",
            dam_x,
            dam_y
        )

        # --------------------------------------------------
        # Prepare DEM for terrain calculations
        # --------------------------------------------------

        dem_float = dem.filled(np.nan)

        # Calculate slope
        slope = calculate_slope(
            dem_float,
            src.transform
        )

        slope_valid = slope[np.isfinite(slope)]

        print("\nTERRAIN SLOPE")
        print("-" * 60)
        print(
            "Minimum:",
            float(np.min(slope_valid)),
            "degrees"
        )
        print(
            "Maximum:",
            float(np.max(slope_valid)),
            "degrees"
        )
        print(
            "Mean:",
            float(np.mean(slope_valid)),
            "degrees"
        )

        # --------------------------------------------------
        # Save slope raster
        # --------------------------------------------------

        slope_path = OUTPUT_DIR / "mettur_slope_degrees.tif"

        slope_profile = src.profile.copy()

        slope_profile.update(
            dtype="float32",
            count=1,
            nodata=-9999.0,
            compress="lzw"
        )

        slope_output = np.where(
            np.isfinite(slope),
            slope,
            -9999.0
        ).astype(np.float32)

        with rasterio.open(
            slope_path,
            "w",
            **slope_profile
        ) as dst:

            dst.write(
                slope_output,
                1
            )

        # --------------------------------------------------
        # Save terrain metadata
        # --------------------------------------------------

        metadata = {
            "project": "NEERAKSH",
            "location": "Mettur",
            "dem_source": "ISRO/NRSC CartoDEM 30m",
            "dem_file": str(DEM_PATH),
            "crs": str(src.crs),
            "width": src.width,
            "height": src.height,
            "resolution_x": src.res[0],
            "resolution_y": src.res[1],
            "bounds": {
                "left": src.bounds.left,
                "bottom": src.bounds.bottom,
                "right": src.bounds.right,
                "top": src.bounds.top
            },
            "dam_coordinate": {
                "latitude": DAM_LAT,
                "longitude": DAM_LON
            },
            "dam_dem_elevation_m": dam_elevation,
            "terrain": {
                "min_elevation_m": float(valid.min()),
                "max_elevation_m": float(valid.max()),
                "mean_elevation_m": float(valid.mean()),
                "min_slope_deg": float(np.min(slope_valid)),
                "max_slope_deg": float(np.max(slope_valid)),
                "mean_slope_deg": float(np.mean(slope_valid))
            },
            "note": (
                "Terrain values are derived from the downloaded "
                "ISRO/NRSC CartoDEM raster. They are not fabricated."
            )
        }

        metadata_path = (
            OUTPUT_DIR / "mettur_terrain_metadata.json"
        )

        with open(
            metadata_path,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                metadata,
                f,
                indent=2
            )

    print("\nOUTPUTS")
    print("-" * 60)
    print("Slope raster:")
    print(slope_path)

    print("\nTerrain metadata:")
    print(metadata_path)

    print("\nPROCESSING COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()