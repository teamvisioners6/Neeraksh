from pathlib import Path
import json

import numpy as np
import geopandas as gpd
import rasterio
from pyproj import Transformer
from shapely.geometry import Point, LineString

ROOT = Path(r"C:\NEERAKSH-1")
DEM_PATH = ROOT / "data" / "dem" / "mettur" / "mettur_correct_dem_30m.tif"
RIVERS_PATH = ROOT / "data" / "hydrosheds" / "hydrorivers" / "asia" / "HydroRIVERS_v10_as_shp" / "HydroRIVERS_v10_as.shp"
OUT_DIR = ROOT / "simulations" / "sph" / "mettur_profile"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CSV_PATH = OUT_DIR / "mettur_sph_bathymetry.csv"
XML_PATH = OUT_DIR / "MetturSPH2D_Def.xml"
META_PATH = OUT_DIR / "mettur_sph_profile_metadata.json"

DAM_LAT = 11.8030555556
DAM_LON = 77.8066666667
WSE_M = 233.493766515

PROFILE_LENGTH_M = 3000.0
SAMPLE_STEP_M = 30.0
DP_M = 10.0
DOMAIN_TOP_MARGIN_M = 15.0


def orient_reach(geom, start_xy):
    if geom is None or geom.is_empty:
        return None
    if geom.geom_type == "MultiLineString":
        parts = list(geom.geoms)
        if not parts:
            return None
        target = Point(start_xy)
        geom = min(parts, key=lambda g: g.distance(target))
    if geom.geom_type != "LineString":
        return None
    coords = list(geom.coords)
    if len(coords) < 2:
        return None
    target = Point(start_xy)
    if Point(coords[-1]).distance(target) < Point(coords[0]).distance(target):
        coords.reverse()
    return LineString(coords)


def orient_next(geom, previous_xy):
    if geom is None or geom.is_empty:
        return None
    if geom.geom_type == "MultiLineString":
        parts = list(geom.geoms)
        if not parts:
            return None
        target = Point(previous_xy)
        geom = min(
            parts,
            key=lambda g: min(
                Point(g.coords[0]).distance(target),
                Point(g.coords[-1]).distance(target),
            ),
        )
    if geom.geom_type != "LineString":
        return None
    coords = list(geom.coords)
    if len(coords) < 2:
        return None
    target = Point(previous_xy)
    if Point(coords[-1]).distance(target) < Point(coords[0]).distance(target):
        coords.reverse()
    return LineString(coords)


def main():
    print("=" * 72)
    print("NEERAKSH - METTUR SPH 2D TERRAIN PROFILE PREPARATION")
    print("=" * 72)

    if not DEM_PATH.exists():
        raise FileNotFoundError(f"DEM not found: {DEM_PATH}")
    if not RIVERS_PATH.exists():
        raise FileNotFoundError(f"HydroRIVERS not found: {RIVERS_PATH}")

    print("\n[1] Loading HydroRIVERS...")
    rivers = gpd.read_file(RIVERS_PATH)

    required = {"HYRIV_ID", "NEXT_DOWN", "geometry"}
    missing = required - set(rivers.columns)
    if missing:
        raise RuntimeError(f"Missing HydroRIVERS fields: {sorted(missing)}")

    rivers_utm = rivers.to_crs("EPSG:32643")
    dam_utm = gpd.GeoSeries(
        [Point(DAM_LON, DAM_LAT)], crs="EPSG:4326"
    ).to_crs("EPSG:32643").iloc[0]

    rivers_utm["_dist_dam_m"] = rivers_utm.geometry.distance(dam_utm)
    first = rivers_utm.sort_values("_dist_dam_m").iloc[0]
    first_id = int(first["HYRIV_ID"])

    print(f"Nearest HydroRIVERS reach: {first_id}")
    print(f"Distance from Mettur reference point: {first['_dist_dam_m']:.1f} m")

    by_id = {}
    for _, row in rivers_utm.iterrows():
        try:
            by_id[int(row["HYRIV_ID"])] = row
        except Exception:
            pass

    selected_ids = []
    selected_geoms = []
    current_id = first_id
    previous_xy = (dam_utm.x, dam_utm.y)
    visited = set()
    accumulated = 0.0

    while current_id and current_id not in visited and accumulated < PROFILE_LENGTH_M:
        visited.add(current_id)
        row = by_id.get(current_id)
        if row is None:
            break

        geom = orient_reach(row.geometry, previous_xy) if not selected_geoms else orient_next(row.geometry, previous_xy)
        if geom is None:
            break

        selected_ids.append(current_id)
        selected_geoms.append(geom)
        accumulated += geom.length
        previous_xy = geom.coords[-1]

        try:
            next_id = int(row["NEXT_DOWN"])
        except Exception:
            next_id = 0

        if next_id == current_id:
            break
        current_id = next_id

    if not selected_geoms:
        raise RuntimeError("Could not construct a downstream HydroRIVERS path.")

    path_coords = []
    for geom in selected_geoms:
        coords = list(geom.coords)
        if not path_coords:
            path_coords.extend(coords)
        elif Point(path_coords[-1]).distance(Point(coords[0])) < 1.0:
            path_coords.extend(coords[1:])
        else:
            path_coords.extend(coords)

    river_path = LineString(path_coords)
    total_length = min(PROFILE_LENGTH_M, river_path.length)

    distances = np.arange(0.0, total_length + SAMPLE_STEP_M * 0.5, SAMPLE_STEP_M)
    distances = distances[distances <= total_length + 1e-6]
    sample_points_utm = [river_path.interpolate(float(d)) for d in distances]

    print(f"Connected downstream reaches: {selected_ids}")
    print(f"Profile length: {total_length:.1f} m")
    print(f"Profile samples: {len(distances)}")

    with rasterio.open(DEM_PATH) as src:
        to_dem = Transformer.from_crs("EPSG:32643", src.crs, always_xy=True)
        dem_xy = [to_dem.transform(p.x, p.y) for p in sample_points_utm]
        values = [v[0] for v in src.sample(dem_xy)]
        nodata = src.nodata

    elevations = np.asarray(values, dtype=float)
    valid = np.isfinite(elevations)
    if nodata is not None:
        valid &= np.abs(elevations - float(nodata)) > 1e-9

    if valid.sum() < max(5, len(elevations) // 2):
        raise RuntimeError(f"Too many invalid DEM samples: {valid.sum()}/{len(elevations)}")

    if not valid.all():
        x = np.arange(len(elevations))
        elevations[~valid] = np.interp(x[~valid], x[valid], elevations[valid])

    base_z = float(np.min(elevations) - 2.0)
    z_rel = elevations - base_z
    wse_rel = WSE_M - base_z

    print(f"DEM elevation range: {np.min(elevations):.2f} - {np.max(elevations):.2f} m")
    print(f"Relative CWC WSE: {wse_rel:.2f} m")

    if wse_rel <= float(np.max(z_rel)):
        print("WARNING: CWC WSE is not above the maximum sampled terrain.")

    x_values = [round(float(d), 3) for d in distances]
    lines = [
        "# NEERAKSH Mettur downstream SPH pilot bathymetry",
        "# X values are cumulative downstream distance in metres",
        "# Z values are CartoDEM elevations shifted by a constant base",
        "Y \\ X => Z;" + ";".join(str(x) for x in x_values),
        "0;" + ";".join(f"{float(z):.6f}" for z in z_rel),
    ]
    CSV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    x_max = float(distances[-1])
    z_max = max(float(np.max(z_rel)) + DOMAIN_TOP_MARGIN_M, wse_rel + 10.0)

    xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<case app="NEERAKSH-Mettur-SPH-Pilot">
<casedef requiredversion="v5.4.354.01">
  <constantsdef>
    <gravity x="0" y="0" z="-9.81" />
    <rhop0 value="1000" />
    <rhopgradient value="2" />
    <hswl value="{wse_rel:.6f}" auto="false" />
    <gamma value="7" />
    <speedsystem value="0" auto="true" />
    <coefsound value="20" />
    <speedsound value="0" auto="true" />
    <coefh value="1.0" />
    <cflnumber value="0.2" />
  </constantsdef>

  <mkconfig boundcount="240" fluidcount="9" />

  <geometry>
    <definition dp="{DP_M}" units_comment="metres (m)">
      <pointref x="0" y="0" z="0" />
      <pointmin x="-{DP_M}" y="0" z="-{DP_M}" />
      <pointmax x="{x_max + DP_M:.3f}" y="0" z="{z_max:.3f}" />
    </definition>

    <commands>
      <mainlist>
        <setmkbound mk="0" />
        <setdrawmode mode="face" />
        <drawfilecsv file="{CSV_PATH.name}" mode="bathymetry" />

        <setdrawmode mode="full" />
        <setmkbound mk="1" />

        <drawbox>
          <boxfill>left</boxfill>
          <point x="0" y="0" z="0" />
          <size x="{DP_M}" y="0.2" z="{z_max:.3f}" />
        </drawbox>

        <drawbox>
          <boxfill>right</boxfill>
          <point x="{x_max - DP_M:.3f}" y="0" z="0" />
          <size x="{2 * DP_M:.3f}" y="0.2" z="{z_max:.3f}" />
        </drawbox>

        <setmkfluid mk="0" />
        <fillbox x="{min(2 * DP_M, x_max / 2):.3f}" y="0" z="{max(0.5 * DP_M, wse_rel / 2):.3f}">
          <modefill>void</modefill>
          <point x="0" y="0" z="0" />
          <size x="{x_max:.3f}" y="0.2" z="{wse_rel:.3f}" />
        </fillbox>

        <shapeout file="MetturSPH2D" reset="true" />
      </mainlist>
    </commands>
  </geometry>

  <execution>
    <parameters>
      <parameter key="SavePosDouble" value="0" />
      <parameter key="StepAlgorithm" value="1" />
      <parameter key="VerletSteps" value="40" />
      <parameter key="Kernel" value="2" />
      <parameter key="CoefDtMin" value="0.05" />
      <parameter key="DtIni" value="0" />
      <parameter key="DtMin" value="0" />
      <parameter key="DtFixed" value="0" />
      <parameter key="TimeMax" value="5" />
      <parameter key="TimeOut" value="0.5" />
      <parameter key="RhopOutMin" value="700" />
      <parameter key="RhopOutMax" value="1300" />
      <simulationdomain>
        <posmin x="default" y="default" z="default" />
        <posmax x="default" y="default" z="default + 20%" />
      </simulationdomain>
    </parameters>
  </execution>
</case>
"""
    XML_PATH.write_text(xml, encoding="utf-8")

    metadata = {
        "project": "NEERAKSH",
        "model": "SPH (DualSPHysics)",
        "purpose": "Mettur downstream 2D longitudinal SPH pilot",
        "status": "PILOT_PREPARATION",
        "not_a_flood_forecast": True,
        "not_a_verified_breach_location": True,
        "mettur_reference": {"lat": DAM_LAT, "lon": DAM_LON},
        "cwc_initial_wse_m": WSE_M,
        "dem": str(DEM_PATH),
        "hydrorivers": str(RIVERS_PATH),
        "nearest_hyriv_id": first_id,
        "downstream_reaches": selected_ids,
        "profile_length_m": total_length,
        "sample_step_m": SAMPLE_STEP_M,
        "particle_spacing_m": DP_M,
        "base_elevation_m": base_z,
        "raw_dem_elevation_min_m": float(np.min(elevations)),
        "raw_dem_elevation_max_m": float(np.max(elevations)),
        "relative_wse_m": wse_rel,
        "outputs": {
            "bathymetry_csv": str(CSV_PATH),
            "definition_xml": str(XML_PATH),
        },
    }

    META_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print("\n[3] Files written:")
    print(f"  {CSV_PATH}")
    print(f"  {XML_PATH}")
    print(f"  {META_PATH}")
    print("\nDONE.")
    print("Next: run GenCase on MetturSPH2D_Def.xml.")
    print("Do NOT run DualSPHysics until the generated particle geometry is inspected.")


if __name__ == "__main__":
    main()
