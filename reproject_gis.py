import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from pathlib import Path

BASE = Path(r"C:\NEERAKSH-1\simulations\outputs\mettur\hll_test")

LAYERS = [
    "mettur_max_depth",
    "mettur_arrival_time",
    "mettur_final_depth",
]

for name in LAYERS:
    src_path = BASE / f"{name}.tif"
    dst_path = BASE / f"{name}_wgs84.tif"

    with rasterio.open(src_path) as src:
        transform, width, height = calculate_default_transform(
            src.crs,
            "EPSG:4326",
            src.width,
            src.height,
            *src.bounds,
        )

        profile = src.profile.copy()
        profile.update(
            crs="EPSG:4326",
            transform=transform,
            width=width,
            height=height,
        )

        with rasterio.open(dst_path, "w", **profile) as dst:
            reproject(
                source=rasterio.band(src, 1),
                destination=rasterio.band(dst, 1),
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=transform,
                dst_crs="EPSG:4326",
                resampling=Resampling.nearest,
            )

    print("CREATED:", dst_path)