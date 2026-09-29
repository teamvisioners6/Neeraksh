from pathlib import Path
import rasterio
from rasterio.windows import from_bounds

ROOT = Path(r"C:\NEERAKSH-1")

src_path = (
    ROOT
    / "data"
    / "dem"
    / "varattupallam"
    / "source"
    / "P5_PAN_CD_N11_000_E077_000_30m"
    / "P5_PAN_CD_N11_000_E077_000_DEM_30m.tif"
)

out_path = (
    ROOT
    / "data"
    / "dem"
    / "varattupallam"
    / "varattupallam_cartodem_30m.tif"
)

# CWC study location
CENTER_LAT = 11.6755867
CENTER_LON = 77.5608833

# 20 km x 20 km approximate validation domain
HALF_SIZE_DEG = 0.10

left   = CENTER_LON - HALF_SIZE_DEG
right  = CENTER_LON + HALF_SIZE_DEG
bottom = CENTER_LAT - HALF_SIZE_DEG
top    = CENTER_LAT + HALF_SIZE_DEG

with rasterio.open(src_path) as src:

    print("SOURCE DEM")
    print("CRS:", src.crs)
    print("Bounds:", src.bounds)
    print("Resolution:", src.res)

    if not (
        src.bounds.left <= CENTER_LON <= src.bounds.right
        and
        src.bounds.bottom <= CENTER_LAT <= src.bounds.top
    ):
        raise RuntimeError(
            "CWC Varattupallam study coordinate is outside the DEM."
        )

    window = from_bounds(
        left,
        bottom,
        right,
        top,
        src.transform
    )

    window = window.round_offsets().round_lengths()

    data = src.read(1, window=window)

    transform = src.window_transform(window)

    profile = src.profile.copy()

    profile.update(
        driver="GTiff",
        height=data.shape[0],
        width=data.shape[1],
        transform=transform,
        compress="deflate",
        predictor=2
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(data, 1)

    print()
    print("VARATTUPALLAM VALIDATION DEM")
    print("Output:", out_path)
    print("Width:", data.shape[1])
    print("Height:", data.shape[0])
    print("Bounds:", rasterio.transform.array_bounds(
        data.shape[0],
        data.shape[1],
        transform
    ))
    print("Resolution:", transform.a, abs(transform.e))
    print("Minimum elevation:", float(data.min()))
    print("Maximum elevation:", float(data.max()))
    print()
    print("CWC STUDY LOCATION")
    print("Latitude:", CENTER_LAT)
    print("Longitude:", CENTER_LON)
