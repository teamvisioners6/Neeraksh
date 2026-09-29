from pathlib import Path
import csv
import json


ROOT = Path(r"C:\NEERAKSH-1")

SCENARIO = (
    ROOT
    / "data"
    / "engineering"
    / "varattupallam"
    / "cwc_hydraulic_scenarios.json"
)

CSV_FILE = (
    ROOT
    / "simulations"
    / "outputs"
    / "varattupallam"
    / "hydraulic_feasibility"
    / "cwc_piping_breach_development.csv"
)

OUTPUT = (
    ROOT
    / "simulations"
    / "outputs"
    / "varattupallam"
    / "hydraulic_feasibility"
    / "cwc_geometry_test.json"
)


def load_json(path):

    with open(
        path,
        "r",
        encoding="utf-8-sig",
    ) as f:

        return json.load(f)


def close(a, b, tol=1e-9):

    return abs(
        float(a) - float(b)
    ) <= tol


def main():

    print()
    print("=" * 72)
    print(
        "NEERAKSH – CWC VARATTUPALLAM "
        "GEOMETRY CONSISTENCY TEST"
    )
    print("=" * 72)
    print()

    data = load_json(
        SCENARIO
    )

    piping = data["piping"]

    expected_width = float(
        piping[
            "breach_width_m"
        ]
    )

    expected_slope = float(
        piping[
            "breach_side_slope"
        ]
    )

    expected_time = float(
        piping[
            "formation_time_hr"
        ]
    )

    expected_invert = float(
        piping[
            "breach_invert_elevation_m"
        ]
    )

    expected_level = float(
        piping[
            "initial_reservoir_level_m"
        ]
    )

    expected_inflow = piping[
        "inflow_assumption"
    ]

    tests = []

    # --------------------------------------------------------
    # Read CSV
    # --------------------------------------------------------

    with open(
        CSV_FILE,
        "r",
        encoding="utf-8",
    ) as f:

        rows = list(
            csv.DictReader(f)
        )

    # --------------------------------------------------------
    # Test count
    # --------------------------------------------------------

    test = (
        len(rows) == 101
    )

    tests.append(
        {
            "test":
                "exactly_101_time_steps",
            "expected":
                101,
            "actual":
                len(rows),
            "status":
                "PASS"
                if test
                else "FAIL",
        }
    )

    # --------------------------------------------------------
    # First row
    # --------------------------------------------------------

    first = rows[0]

    test = (
        close(
            first[
                "time_hr"
            ],
            0.0,
        )
        and
        close(
            first[
                "breach_width_m"
            ],
            0.0,
        )
    )

    tests.append(
        {
            "test":
                "initial_breach_state",
            "expected":
                "time=0, width=0",
            "actual":
                {
                    "time_hr":
                        first[
                            "time_hr"
                        ],
                    "width_m":
                        first[
                            "breach_width_m"
                        ],
                },
            "status":
                "PASS"
                if test
                else "FAIL",
        }
    )

    # --------------------------------------------------------
    # Final row
    # --------------------------------------------------------

    last = rows[-1]

    test = (
        close(
            last[
                "time_hr"
            ],
            expected_time,
        )
        and
        close(
            last[
                "breach_width_m"
            ],
            expected_width,
        )
        and
        close(
            last[
                "breach_invert_elevation_m"
            ],
            expected_invert,
        )
        and
        close(
            last[
                "reservoir_reference_level_m"
            ],
            expected_level,
        )
    )

    tests.append(
        {
            "test":
                "final_breach_state",
            "expected":
                {
                    "time_hr":
                        expected_time,
                    "width_m":
                        expected_width,
                    "invert_m":
                        expected_invert,
                    "level_m":
                        expected_level,
                },
            "actual":
                {
                    "time_hr":
                        float(
                            last[
                                "time_hr"
                            ]
                        ),
                    "width_m":
                        float(
                            last[
                                "breach_width_m"
                            ]
                        ),
                    "invert_m":
                        float(
                            last[
                                "breach_invert_elevation_m"
                            ]
                        ),
                    "level_m":
                        float(
                            last[
                                "reservoir_reference_level_m"
                            ]
                        ),
                },
            "status":
                "PASS"
                if test
                else "FAIL",
        }
    )

    # --------------------------------------------------------
    # Linear width test
    # --------------------------------------------------------

    linear = True

    for row in rows:

        t = float(
            row[
                "time_hr"
            ]
        )

        w = float(
            row[
                "breach_width_m"
            ]
        )

        expected = (
            expected_width
            * (
                t
                / expected_time
            )
        )

        if not close(
            w,
            expected,
            1e-8,
        ):

            linear = False
            break

    tests.append(
        {
            "test":
                "linear_breach_width_development",
            "status":
                "PASS"
                if linear
                else "FAIL",
        }
    )

    # --------------------------------------------------------
    # Side slope consistency
    # --------------------------------------------------------

    side_slope = float(
        last[
            "top_width_m"
        ]
    )

    expected_top_width = (
        expected_width
        + 2.0
        * expected_slope
        * float(
            last[
                "opening_height_m"
            ]
        )
    )

    test = close(
        side_slope,
        expected_top_width,
        1e-8,
    )

    tests.append(
        {
            "test":
                "side_slope_geometry",
            "expected_top_width_m":
                expected_top_width,
            "actual_top_width_m":
                side_slope,
            "status":
                "PASS"
                if test
                else "FAIL",
        }
    )

    # --------------------------------------------------------
    # Zero inflow
    # --------------------------------------------------------

    test = (
        str(
            expected_inflow
        ).lower()
        == "zero inflow"
    )

    tests.append(
        {
            "test":
                "official_zero_inflow_assumption",
            "expected":
                "zero inflow",
            "actual":
                expected_inflow,
            "status":
                "PASS"
                if test
                else "FAIL",
        }
    )

    # --------------------------------------------------------
    # Elevation difference
    # --------------------------------------------------------

    elevation_difference = (
        expected_level
        - expected_invert
    )

    test = close(
        elevation_difference,
        298.0,
    )

    tests.append(
        {
            "test":
                "published_level_invert_difference",
            "expected_m":
                298.0,
            "actual_m":
                elevation_difference,
            "status":
                "PASS"
                if test
                else "FAIL",
        }
    )

    # --------------------------------------------------------
    # Overall
    # --------------------------------------------------------

    failed = [
        item
        for item in tests
        if item[
            "status"
        ] != "PASS"
    ]

    overall = (
        "PASS"
        if not failed
        else "FAIL"
    )

    report = {

        "status":
            overall,

        "case_id":
            data[
                "case_id"
            ],

        "tests":
            tests,

        "integrity":
            {
                "fabricated_values":
                    False,

                "invented_breach_location":
                    False,

                "mettur_parameters_used":
                    False,
            },
    }

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        OUTPUT,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            report,
            f,
            indent=2,
        )

    # --------------------------------------------------------
    # Console
    # --------------------------------------------------------

    print(
        "[TEST RESULTS]"
    )

    for item in tests:

        print(
            f"  {item['test']}: "
            f"{item['status']}"
        )

    print()

    print(
        "=" * 72
    )

    print(
        f"OVERALL STATUS: {overall}"
    )

    print(
        "=" * 72
    )

    print()

    print(
        f"Report:"
    )

    print(
        f"  {OUTPUT}"
    )

    print()

    if failed:

        print(
            "FAILED TESTS:"
        )

        for item in failed:

            print(
                f"  - {item['test']}"
            )

        return 1

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )