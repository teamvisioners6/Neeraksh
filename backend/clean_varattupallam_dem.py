from pathlib import Path
import numpy as np
import rasterio

ROOT = Path(r"C:\NEERAKSH-1")

src_path = (
    ROOT
    / "data"
    / "dem"
    / "varattupallam"
    / "varattupallam_cartodem_30m.tif"
)

out_path = (
    ROOT
    / "data"
    / "dem"
    / "varattupallam"
    / "varattupallam_cartodem_30m_nodata_clean.tif"
)

with rasterio.open(src_path) as src:

    data = src.read(1)

    print("SOURCE DEM")
    print("NoData:", src.nodata)
    print("Shape:", data.shape)
    print("CRS:", src.crs)
    print("Resolution:", src.res)

    nodata_value = src.nodata

    if nodata_value is None:
        nodata_mask = data <= -10000
    else:
        nodata_mask = (
            data == nodata_value
        ) | (
            data <= -10000
        )

    valid = data[~nodata_mask]

    if valid.size == 0:
        raise RuntimeError("DEM contains no valid elevation cells.")

    print()
    print("BEFORE CLEANING")
    print("NoData cells:", int(nodata_mask.sum()))
    print("Valid cells:", int(valid.size))
    print("Valid minimum:", float(valid.min()))
    print("Valid maximum:", float(valid.max()))

    # Preserve NoData explicitly.
    cleaned = data.astype(np.float32)

    output_nodata = -9999.0
    cleaned[nodata_mask] = output_nodata

    profile = src.profile.copy()

    profile.update(
        driver="GTiff",
        dtype="float32",
        nodata=output_nodata,
        compress="deflate",
        predictor=3
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(cleaned, 1)

    print()
    print("CLEANED DEM")
    print("Output:", out_path)
    print("NoData:", output_nodata)
    print("Valid minimum:", float(valid.min()))
    print("Valid maximum:", float(valid.max()))
    print("Valid percentage:", round(100.0 * valid.size / data.size, 3))

print()
print("DEM CLEANING COMPLETE")
