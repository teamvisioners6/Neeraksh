from pathlib import Path
import json
import csv
import numpy as np
import vtk


# ============================================================
# NEERAKSHA - DualSPHysics SPH POST PROCESSOR
# BREACH50 pilot run
# ============================================================

ROOT = Path(
    r"C:\NEERAKSH-1\simulations\sph\mettur_profile\MetturSPH2D_BREACH50_RUN"
)

VTK_DIR = ROOT / "particles"

BATHY_FILE = Path(
    r"C:\NEERAKSH-1\simulations\sph\mettur_profile\mettur_sph_bathymetry.csv"
)

OUT_DIR = ROOT / "postprocess"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# CONFIGURATION
# ============================================================

DT = 0.2

GRID_DX = 10.0
GRID_DY = 10.0

DAM_X = 500.0
DOWNSTREAM_X = DAM_X + GRID_DX

MIN_DEPTH = 0.05

# DualSPHysics PartVTK output confirmed:
# Type 0 = boundary
# Type 3 = fluid
FLUID_TYPE = 3


# ============================================================
# READ BATHYMETRY
# ============================================================

def load_bathymetry():
    if not BATHY_FILE.exists():
        raise FileNotFoundError(
            f"Bathymetry file not found:\n{BATHY_FILE}"
        )

    with BATHY_FILE.open("r", encoding="utf-8-sig") as f:
        lines = [
            line.strip()
            for line in f
            if line.strip()
        ]

    header_index = None

    for i, line in enumerate(lines):
        if line.startswith("Y \\ X => Z"):
            header_index = i
            break

    if header_index is None:
        raise RuntimeError(
            "Could not find bathymetry X header."
        )

    header_parts = lines[header_index].split(";")

    x_values = []
    for value in header_parts[1:]:
        value = value.strip()
        if value:
            x_values.append(float(value))

    if not x_values:
        raise RuntimeError(
            "Could not read X coordinates from bathymetry CSV."
        )

    if header_index + 1 >= len(lines):
        raise RuntimeError(
            "No bathymetry data row found."
        )

    data_parts = lines[header_index + 1].split(";")

    z_values = []
    for value in data_parts[1:]:
        value = value.strip()
        if value:
            z_values.append(float(value))

    if len(z_values) != len(x_values):
        raise RuntimeError(
            "Bathymetry X/Z length mismatch: "
            f"{len(x_values)} X values vs "
            f"{len(z_values)} Z values."
        )

    x_values = np.asarray(x_values, dtype=np.float64)
    z_values = np.asarray(z_values, dtype=np.float64)

    order = np.argsort(x_values)

    x_values = x_values[order]
    z_values = z_values[order]

    print(f"Bathymetry samples : {len(x_values)}")
    print(
        f"Bathymetry X range : "
        f"{x_values.min():.2f} -> {x_values.max():.2f} m"
    )
    print(
        f"Bathymetry Z range : "
        f"{z_values.min():.2f} -> {z_values.max():.2f} m"
    )

    return x_values, z_values


BATHY_X, BATHY_Z = load_bathymetry()


def bed_elevation(x):
    return np.interp(x, BATHY_X, BATHY_Z)


# ============================================================
# READ VTK
# ============================================================

def read_vtk(path):
    reader = vtk.vtkDataSetReader()
    reader.SetFileName(str(path))
    reader.ReadAllScalarsOn()
    reader.ReadAllVectorsOn()
    reader.Update()

    data = reader.GetOutput()

    if data is None:
        raise RuntimeError(f"Could not read VTK file:\n{path}")

    n = data.GetNumberOfPoints()

    if n == 0:
        raise RuntimeError(
            f"No particles found in {path}"
        )

    point_data = data.GetPointData()

    # Coordinates
    xyz = np.array(
        [data.GetPoint(i) for i in range(n)],
        dtype=np.float64
    )

    # Velocity
    vel_array = point_data.GetArray("Vel")

    if vel_array is None:
        raise RuntimeError(
            f"Vel field missing in {path}"
        )

    velocity = np.array(
        [vel_array.GetTuple3(i) for i in range(n)],
        dtype=np.float64
    )

    speed = np.linalg.norm(velocity, axis=1)

    # Density
    rhop_array = point_data.GetArray("Rhop")

    if rhop_array is not None:
        density = np.array(
            [rhop_array.GetTuple1(i) for i in range(n)],
            dtype=np.float64
        )
    else:
        density = np.full(n, 1000.0, dtype=np.float64)

    # Pressure
    press_array = point_data.GetArray("Press")

    if press_array is not None:
        pressure = np.array(
            [press_array.GetTuple1(i) for i in range(n)],
            dtype=np.float64
        )
    else:
        pressure = np.zeros(n, dtype=np.float64)

    # IMPORTANT:
    # PartVTK writes "Type" with:
    # 0 = boundary
    # 3 = fluid
    type_array = point_data.GetArray("Type")

    if type_array is None:
        raise RuntimeError(
            f"Type field missing in {path}. "
            "The VTK file must contain the DualSPHysics Type array."
        )

    particle_type = np.array(
        [type_array.GetTuple1(i) for i in range(n)],
        dtype=np.int32
    )

    fluid_mask = particle_type == FLUID_TYPE

    if not np.any(fluid_mask):
        raise RuntimeError(
            f"No Type={FLUID_TYPE} fluid particles found in {path}."
        )

    return {
        "xyz": xyz[fluid_mask],
        "velocity": velocity[fluid_mask],
        "speed": speed[fluid_mask],
        "density": density[fluid_mask],
        "pressure": pressure[fluid_mask],
        "particle_type": particle_type[fluid_mask],
        "all_particle_count": n,
    }


# ============================================================
# FIND VTK FRAMES
# ============================================================

files = sorted(
    VTK_DIR.glob("*.vtk")
)

if not files:
    raise RuntimeError(
        f"No VTK files found in:\n{VTK_DIR}"
    )


print()
print("=" * 70)
print("NEERAKSHA - BREACH50 SPH POST PROCESSING")
print("=" * 70)

print(f"Run directory   : {ROOT}")
print(f"VTK directory   : {VTK_DIR}")
print(f"Frames found    : {len(files)}")
print(f"Fluid Type      : {FLUID_TYPE}")
print(f"Dam position    : X = {DAM_X:.1f} m")
print(f"Arrival zone    : X > {DOWNSTREAM_X:.1f} m")
print()


# ============================================================
# LOAD FRAMES
# ============================================================

frames = []

for frame_index, path in enumerate(files):

    frame = read_vtk(path)

    frame["index"] = frame_index
    frame["time_s"] = frame_index * DT
    frame["file"] = str(path)

    frames.append(frame)

    xyz = frame["xyz"]
    speed = frame["speed"]

    downstream = xyz[:, 0] >= DOWNSTREAM_X
    downstream_count = int(np.count_nonzero(downstream))

    if downstream_count:
        downstream_speed = speed[downstream]
        downstream_max = float(downstream_speed.max())
    else:
        downstream_max = 0.0

    print(
        f"Frame {frame_index:02d} | "
        f"time={frame['time_s']:5.2f}s | "
        f"fluid={len(xyz):5d} | "
        f"downstream={downstream_count:5d} | "
        f"Xmax={xyz[:, 0].max():8.2f} m | "
        f"max_speed={speed.max():7.3f} m/s | "
        f"downstream_max={downstream_max:7.3f} m/s"
    )


# ============================================================
# CHECK DOWNSTREAM PROPAGATION
# ============================================================

all_xyz = np.concatenate(
    [frame["xyz"] for frame in frames],
    axis=0
)

downstream_xyz = all_xyz[
    all_xyz[:, 0] >= DOWNSTREAM_X
]

if len(downstream_xyz) == 0:
    raise RuntimeError(
        "No downstream FLUID particles were detected. "
        "The BREACH50 simulation did not produce "
        "detectable downstream propagation."
    )


# ============================================================
# DETERMINE GRID
# ============================================================

xmin = float(
    np.floor(downstream_xyz[:, 0].min() / GRID_DX)
    * GRID_DX
)

xmax = float(
    np.ceil(downstream_xyz[:, 0].max() / GRID_DX)
    * GRID_DX
)

ymin = float(
    np.floor(downstream_xyz[:, 1].min() / GRID_DY)
    * GRID_DY
)

ymax = float(
    np.ceil(downstream_xyz[:, 1].max() / GRID_DY)
    * GRID_DY
)

x_grid = np.arange(
    xmin,
    xmax + GRID_DX,
    GRID_DX
)

y_grid = np.arange(
    ymin,
    ymax + GRID_DY,
    GRID_DY
)

nx = len(x_grid)
ny = len(y_grid)

print()
print(f"Downstream grid X : {xmin:.1f} -> {xmax:.1f} m")
print(f"Downstream grid Y : {ymin:.1f} -> {ymax:.1f} m")
print(f"Grid size         : {nx} x {ny}")


# ============================================================
# OUTPUT ARRAYS
# ============================================================

max_depth = np.zeros(
    (ny, nx),
    dtype=np.float64
)

max_velocity = np.zeros(
    (ny, nx),
    dtype=np.float64
)

final_depth = np.zeros(
    (ny, nx),
    dtype=np.float64
)

arrival_time = np.full(
    (ny, nx),
    np.nan,
    dtype=np.float64
)


# ============================================================
# GRID INDEX
# ============================================================

def grid_indices(xyz):

    ix = np.floor(
        (xyz[:, 0] - xmin) / GRID_DX
    ).astype(int)

    iy = np.floor(
        (xyz[:, 1] - ymin) / GRID_DY
    ).astype(int)

    valid = (
        (ix >= 0)
        & (ix < nx)
        & (iy >= 0)
        & (iy < ny)
    )

    return ix, iy, valid


# ============================================================
# PROCESS EACH FRAME
# ============================================================

for frame_index, frame in enumerate(frames):

    xyz = frame["xyz"]
    speed = frame["speed"]

    downstream = xyz[:, 0] >= DOWNSTREAM_X

    if not np.any(downstream):
        continue

    xyz_d = xyz[downstream]
    speed_d = speed[downstream]

    ix, iy, valid = grid_indices(xyz_d)

    ix = ix[valid]
    iy = iy[valid]
    xyz_d = xyz_d[valid]
    speed_d = speed_d[valid]

    # --------------------------------------------------------
    # WATER SURFACE
    # Highest fluid particle in each grid cell.
    # --------------------------------------------------------

    surface = np.full(
        (ny, nx),
        np.nan,
        dtype=np.float64
    )

    for xidx, yidx, z in zip(
        ix,
        iy,
        xyz_d[:, 2]
    ):
        current = surface[yidx, xidx]

        if np.isnan(current) or z > current:
            surface[yidx, xidx] = z

    # --------------------------------------------------------
    # BED
    # --------------------------------------------------------

    cell_x = (
        xmin
        + (np.arange(nx) + 0.5) * GRID_DX
    )

    bed_x = bed_elevation(cell_x)

    bed = np.tile(
        bed_x,
        (ny, 1)
    )

    # --------------------------------------------------------
    # DEPTH
    # --------------------------------------------------------

    depth = np.zeros(
        (ny, nx),
        dtype=np.float64
    )

    active = np.isfinite(surface)

    depth[active] = np.maximum(
        surface[active] - bed[active],
        0.0
    )

    # --------------------------------------------------------
    # MAXIMUM DEPTH
    # --------------------------------------------------------

    max_depth = np.maximum(
        max_depth,
        depth
    )

    # --------------------------------------------------------
    # VELOCITY
    # Average particle speed per grid cell.
    # --------------------------------------------------------

    velocity_sum = np.zeros(
        (ny, nx),
        dtype=np.float64
    )

    particle_count = np.zeros(
        (ny, nx),
        dtype=np.int32
    )

    for xidx, yidx, velocity in zip(
        ix,
        iy,
        speed_d
    ):
        velocity_sum[yidx, xidx] += velocity
        particle_count[yidx, xidx] += 1

    valid_velocity = particle_count > 0

    frame_velocity = np.zeros(
        (ny, nx),
        dtype=np.float64
    )

    frame_velocity[valid_velocity] = (
        velocity_sum[valid_velocity]
        / particle_count[valid_velocity]
    )

    max_velocity = np.maximum(
        max_velocity,
        frame_velocity
    )

    # --------------------------------------------------------
    # ARRIVAL TIME
    # --------------------------------------------------------

    newly_wet = (
        (depth >= MIN_DEPTH)
        & np.isnan(arrival_time)
    )

    arrival_time[newly_wet] = frame["time_s"]

    # --------------------------------------------------------
    # FINAL FRAME DEPTH
    # --------------------------------------------------------

    if frame_index == len(frames) - 1:
        final_depth = depth.copy()


# ============================================================
# SUMMARY STATISTICS
# ============================================================

wet_max = max_depth >= MIN_DEPTH
wet_final = final_depth >= MIN_DEPTH

valid_arrival = np.isfinite(arrival_time)

max_depth_value = float(max_depth.max())
max_velocity_value = float(max_velocity.max())

if np.any(valid_arrival):
    earliest_arrival = float(
        np.nanmin(arrival_time)
    )
    latest_arrival = float(
        np.nanmax(arrival_time)
    )
else:
    earliest_arrival = None
    latest_arrival = None


# ============================================================
# FRAME SUMMARY CSV
# ============================================================

frame_csv = OUT_DIR / "sph_frame_summary.csv"

with frame_csv.open(
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.writer(f)

    writer.writerow([
        "frame",
        "time_s",
        "fluid_particles",
        "downstream_fluid_particles",
        "fluid_xmax_m",
        "max_speed_mps",
        "downstream_max_speed_mps",
        "downstream_mean_speed_mps"
    ])

    for frame in frames:

        xyz = frame["xyz"]
        speed = frame["speed"]

        downstream = xyz[:, 0] >= DOWNSTREAM_X
        count = int(np.count_nonzero(downstream))

        if count:
            ds_speed = speed[downstream]
            max_speed = float(ds_speed.max())
            mean_speed = float(ds_speed.mean())
        else:
            max_speed = 0.0
            mean_speed = 0.0

        writer.writerow([
            frame["index"],
            frame["time_s"],
            len(xyz),
            count,
            float(xyz[:, 0].max()),
            float(speed.max()),
            max_speed,
            mean_speed
        ])


# ============================================================
# SAVE NUMPY PRODUCTS
# ============================================================

np.save(
    OUT_DIR / "sph_max_depth.npy",
    max_depth
)

np.save(
    OUT_DIR / "sph_max_velocity.npy",
    max_velocity
)

np.save(
    OUT_DIR / "sph_final_depth.npy",
    final_depth
)

np.save(
    OUT_DIR / "sph_arrival_time.npy",
    arrival_time
)


# ============================================================
# SAVE BED
# ============================================================

bed_x = bed_elevation(
    xmin + (np.arange(nx) + 0.5) * GRID_DX
)

bed_grid = np.tile(
    bed_x,
    (ny, 1)
)

np.save(
    OUT_DIR / "sph_bed.npy",
    bed_grid
)


# ============================================================
# SAVE METADATA
# ============================================================

metadata = {
    "project": "NEERAKSHA",
    "model": "SPH",
    "solver": "DualSPHysics",
    "site": "Mettur",
    "scenario": "BREACH50 hypothetical pilot",
    "breach_width_m": 50.0,

    "frames": len(frames),
    "simulation_duration_s": float(
        frames[-1]["time_s"]
    ),
    "frame_interval_s": DT,

    "particles_per_frame": int(
        len(frames[0]["xyz"])
    ),

    "fluid_particle_type": FLUID_TYPE,

    "grid_dx_m": GRID_DX,
    "grid_dy_m": GRID_DY,

    "dam_x_m": DAM_X,
    "downstream_start_x_m": DOWNSTREAM_X,

    "xmin_m": xmin,
    "xmax_m": xmax,
    "ymin_m": ymin,
    "ymax_m": ymax,

    "wet_cells_max": int(
        np.count_nonzero(wet_max)
    ),
    "wet_cells_final": int(
        np.count_nonzero(wet_final)
    ),

    "maximum_depth_m": max_depth_value,
    "maximum_velocity_mps": max_velocity_value,

    "earliest_downstream_arrival_s":
        earliest_arrival,

    "latest_downstream_arrival_s":
        latest_arrival,

    "fluid_front_final_x_m": float(
        frames[-1]["xyz"][:, 0].max()
    ),

    "downstream_fluid_particles_final": int(
        np.count_nonzero(
            frames[-1]["xyz"][:, 0] >= DOWNSTREAM_X
        )
    ),

    "bathymetry_source": str(BATHY_FILE),

    "status": "SPH_PARTICLE_DERIVED_PILOT",

    "scientific_note": (
        "Particle-derived SPH pilot products from "
        "a hypothetical 50 m breach geometry. "
        "Bed reference is taken from the supplied "
        "Mettur SPH bathymetry profile. "
        "This is not a validated Mettur inundation forecast."
    )
}

summary_file = OUT_DIR / "sph_summary.json"

with summary_file.open(
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        metadata,
        f,
        indent=2
    )


# ============================================================
# FINAL REPORT
# ============================================================

print()
print("=" * 70)
print("SPH POST PROCESSING COMPLETE")
print("=" * 70)

print(
    f"Maximum depth             : "
    f"{max_depth_value:.3f} m"
)

print(
    f"Maximum velocity          : "
    f"{max_velocity_value:.3f} m/s"
)

print(
    f"Wet cells (maximum)       : "
    f"{np.count_nonzero(wet_max)}"
)

print(
    f"Wet cells (final)         : "
    f"{np.count_nonzero(wet_final)}"
)

print(
    f"Earliest downstream time  : "
    f"{earliest_arrival}"
)

print(
    f"Latest downstream arrival : "
    f"{latest_arrival}"
)

print(
    f"Final fluid-front X       : "
    f"{frames[-1]['xyz'][:, 0].max():.3f} m"
)

print(
    f"Final downstream fluid    : "
    f"{np.count_nonzero(frames[-1]['xyz'][:, 0] >= DOWNSTREAM_X)} particles"
)

print()
print("Outputs written to:")
print(OUT_DIR)
print()
