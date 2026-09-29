from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


# ============================================================
# NEERAKSH
# 2D HYDRAULIC NUMERICAL ENGINE UNIT TEST
#
# IMPORTANT:
# This test does NOT:
#   - use the CWC breach location
#   - unlock the Varattupallam solver
#   - generate a flood map
#   - generate a real-world inundation result
#
# It tests only the numerical components:
#   - HLL flux
#   - Manning friction
#   - bed slope source term
#   - CFL timestep
#   - boundary handling
#   - dry-cell stability
# ============================================================


PROJECT_ROOT = Path(r"C:\NEERAKSH-1")

sys.path.insert(
    0,
    str(PROJECT_ROOT / "backend")
)


import varattupallam_2d_solver as solver


PASS_COUNT = 0
FAIL_COUNT = 0


def check(name, condition, details=""):

    global PASS_COUNT
    global FAIL_COUNT

    if condition:

        PASS_COUNT += 1

        print(
            f"[PASS] {name}"
        )

        if details:
            print(
                f"       {details}"
            )

    else:

        FAIL_COUNT += 1

        print(
            f"[FAIL] {name}"
        )

        if details:
            print(
                f"       {details}"
            )


def test_hll_rest_state():

    result = solver.hll_flux(
        2.0,
        0.0,
        0.0,
        2.0,
        0.0,
        0.0,
        1.0,
        0.0,
    )

    fh, fhu, fhv = result

    check(
        "HLL rest-state mass flux",
        abs(fh) < 1.0e-12,
        f"mass flux = {fh}",
    )

    check(
        "HLL rest-state transverse flux",
        abs(fhv) < 1.0e-12,
        f"transverse flux = {fhv}",
    )

    check(
        "HLL rest-state pressure flux",
        np.isfinite(fhu),
        f"momentum flux = {fhu}",
    )


def test_hll_dry_state():

    result = solver.hll_flux(
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        1.0,
        0.0,
    )

    fh, fhu, fhv = result

    check(
        "HLL dry-state finite",
        all(
            np.isfinite(
                value
            )
            for value in result
        ),
        f"flux = {result}",
    )

    check(
        "HLL dry-state zero mass flux",
        abs(fh) < 1.0e-12,
        f"mass flux = {fh}",
    )


def test_hll_equal_flow():

    result = solver.hll_flux(
        2.0,
        2.0,
        0.0,
        2.0,
        2.0,
        0.0,
        1.0,
        0.0,
    )

    fh, fhu, fhv = result

    expected_mass_flux = 2.0

    check(
        "HLL equal-flow mass conservation",
        abs(
            fh - expected_mass_flux
        ) < 1.0e-10,
        (
            f"expected = "
            f"{expected_mass_flux}, "
            f"actual = {fh}"
        ),
    )

    check(
        "HLL equal-flow finite",
        all(
            np.isfinite(
                value
            )
            for value in result
        ),
        f"flux = {result}",
    )


def test_manning_zero_velocity():

    h = np.full(
        (5, 5),
        2.0,
        dtype=np.float64,
    )

    hu = np.zeros_like(h)
    hv = np.zeros_like(h)

    original_hu = hu.copy()
    original_hv = hv.copy()

    hu_new, hv_new = solver.apply_manning(
        h,
        hu,
        hv,
        1.0,
    )

    check(
        "Manning zero-velocity preservation",
        np.allclose(
            hu_new,
            original_hu,
        ),
        "x-momentum unchanged",
    )

    check(
        "Manning zero-velocity transverse preservation",
        np.allclose(
            hv_new,
            original_hv,
        ),
        "y-momentum unchanged",
    )


def test_manning_finite():

    h = np.full(
        (5, 5),
        2.0,
        dtype=np.float64,
    )

    hu = np.full(
        (5, 5),
        1.0,
        dtype=np.float64,
    )

    hv = np.full(
        (5, 5),
        0.5,
        dtype=np.float64,
    )

    hu_new, hv_new = solver.apply_manning(
        h,
        hu,
        hv,
        0.5,
    )

    check(
        "Manning produces finite momentum",
        np.all(
            np.isfinite(
                hu_new
            )
        )
        and np.all(
            np.isfinite(
                hv_new
            )
        ),
    )

    check(
        "Manning reduces momentum magnitude",
        np.max(
            np.abs(hu_new)
        )
        <= np.max(
            np.abs(hu)
        ),
    )


def test_bed_slope_flat():

    h = np.full(
        (5, 5),
        2.0,
        dtype=np.float64,
    )

    hu = np.zeros_like(h)
    hv = np.zeros_like(h)

    dem = np.full(
        (5, 5),
        100.0,
        dtype=np.float64,
    )

    hu_new, hv_new = solver.apply_bed_slope(
        h,
        hu,
        hv,
        dem,
        30.0,
        30.0,
        1.0,
    )

    check(
        "Flat-bed x momentum unchanged",
        np.allclose(
            hu_new,
            hu,
        ),
    )

    check(
        "Flat-bed y momentum unchanged",
        np.allclose(
            hv_new,
            hv,
        ),
    )


def test_bed_slope_finite():

    h = np.full(
        (5, 5),
        2.0,
        dtype=np.float64,
    )

    hu = np.zeros_like(h)
    hv = np.zeros_like(h)

    dem = np.array(
        [
            [100, 100, 100, 100, 100],
            [99, 99, 99, 99, 99],
            [98, 98, 98, 98, 98],
            [97, 97, 97, 97, 97],
            [96, 96, 96, 96, 96],
        ],
        dtype=np.float64,
    )

    hu_new, hv_new = solver.apply_bed_slope(
        h,
        hu,
        hv,
        dem,
        30.0,
        30.0,
        0.5,
    )

    check(
        "Bed-slope source remains finite",
        np.all(
            np.isfinite(
                hu_new
            )
        )
        and np.all(
            np.isfinite(
                hv_new
            )
        ),
    )

    check(
        "Bed slope generates momentum",
        np.any(
            np.abs(
                hv_new
            ) > 0
        ),
    )


def test_cfl_positive():

    h = np.full(
        (10, 10),
        2.0,
        dtype=np.float64,
    )

    hu = np.full(
        (10, 10),
        1.0,
        dtype=np.float64,
    )

    hv = np.zeros_like(h)

    dt = solver.calculate_timestep(
        h,
        hu,
        hv,
        30.0,
        30.0,
    )

    check(
        "CFL timestep positive",
        np.isfinite(dt)
        and dt > 0,
        f"dt = {dt:.6f} s",
    )


def test_cfl_dry_domain():

    h = np.zeros(
        (10, 10),
        dtype=np.float64,
    )

    hu = np.zeros_like(h)
    hv = np.zeros_like(h)

    dt = solver.calculate_timestep(
        h,
        hu,
        hv,
        30.0,
        30.0,
    )

    check(
        "CFL dry-domain stability",
        np.isfinite(dt)
        and dt > 0,
        f"dt = {dt}",
    )


def test_boundary_enforcement():

    h = np.arange(
        25,
        dtype=np.float64,
    ).reshape(
        5,
        5,
    )

    hu = np.ones_like(h)
    hv = np.ones_like(h) * 2.0

    h_new, hu_new, hv_new = (
        solver.enforce_boundaries(
            h.copy(),
            hu.copy(),
            hv.copy(),
        )
    )

    check(
        "Boundary finite values",
        np.all(
            np.isfinite(
                h_new
            )
        )
        and np.all(
            np.isfinite(
                hu_new
            )
        )
        and np.all(
            np.isfinite(
                hv_new
            )
        ),
    )

    check(
        "Boundary dimensions preserved",
        h_new.shape == (5, 5)
        and hu_new.shape == (5, 5)
        and hv_new.shape == (5, 5),
    )


def test_breach_discharge():

    q_zero = solver.breach_discharge(
        0.0,
        26.13,
    )

    q_positive = solver.breach_discharge(
        10.0,
        26.13,
    )

    check(
        "Zero-head breach discharge",
        q_zero == 0.0,
        f"Q = {q_zero}",
    )

    check(
        "Positive-head breach discharge",
        np.isfinite(q_positive)
        and q_positive > 0,
        f"Q = {q_positive:.6f} m3/s",
    )


def test_no_nan_after_basic_update():

    h = np.full(
        (20, 20),
        1.0,
        dtype=np.float64,
    )

    hu = np.zeros_like(h)
    hv = np.zeros_like(h)

    fx_h, fx_hu, fx_hv = (
        solver.x_fluxes(
            h,
            hu,
            hv,
        )
    )

    fy_h, fy_hu, fy_hv = (
        solver.y_fluxes(
            h,
            hu,
            hv,
        )
    )

    check(
        "X flux arrays finite",
        np.all(
            np.isfinite(
                fx_h
            )
        )
        and np.all(
            np.isfinite(
                fx_hu
            )
        )
        and np.all(
            np.isfinite(
                fx_hv
            )
        ),
    )

    check(
        "Y flux arrays finite",
        np.all(
            np.isfinite(
                fy_h
            )
        )
        and np.all(
            np.isfinite(
                fy_hu
            )
        )
        and np.all(
            np.isfinite(
                fy_hv
            )
        ),
    )


def main():

    print()
    print("=" * 72)
    print(
        "NEERAKSH – 2D HYDRAULIC ENGINE UNIT TEST"
    )
    print("=" * 72)
    print()

    print(
        "IMPORTANT:"
    )

    print(
        "This is a numerical-engine test only."
    )

    print(
        "No real-world inundation simulation is executed."
    )

    print(
        "CWC solver gates remain unchanged."
    )

    print()

    test_hll_rest_state()
    test_hll_dry_state()
    test_hll_equal_flow()

    test_manning_zero_velocity()
    test_manning_finite()

    test_bed_slope_flat()
    test_bed_slope_finite()

    test_cfl_positive()
    test_cfl_dry_domain()

    test_boundary_enforcement()

    test_breach_discharge()

    test_no_nan_after_basic_update()

    print()
    print("=" * 72)
    print(
        f"TOTAL PASS: {PASS_COUNT}"
    )
    print(
        f"TOTAL FAIL: {FAIL_COUNT}"
    )
    print("=" * 72)

    if FAIL_COUNT == 0:

        print()
        print(
            "NUMERICAL ENGINE TEST: PASS"
        )
        print(
            "The tested numerical components "
            "returned finite/stable results."
        )

        return 0

    print()
    print(
        "NUMERICAL ENGINE TEST: FAIL"
    )

    return 1


if __name__ == "__main__":
    raise SystemExit(
        main()
    )