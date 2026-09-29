from pathlib import Path
import csv
import json


# ============================================================
# NEERAKSH
# CWC METTUR / STANLEY RESERVOIR
# OFFICIAL STAGE-STORAGE ENGINE
# ============================================================

CSV_PATH = Path(
    r"C:\NEERAKSH-1\data\hydrology\mettur\cwc_stage_storage_2020.csv"
)

OUTPUT_DIR = Path(
    r"C:\NEERAKSH-1\simulations\outputs\mettur\stage_storage"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


class CWCStageStorage:

    def __init__(self, csv_path):

        self.csv_path = Path(csv_path)

        if not self.csv_path.exists():
            raise FileNotFoundError(
                f"CWC stage-storage CSV not found:\n"
                f"{self.csv_path}"
            )

        self.rows = []

        self._load()
        self._validate()

    # --------------------------------------------------------
    # LOAD
    # --------------------------------------------------------

    def _load(self):

        with self.csv_path.open(
            "r",
            encoding="utf-8"
        ) as f:

            reader = csv.DictReader(f)

            for row in reader:

                self.rows.append({
                    "elevation_m": float(
                        row["elevation_m"]
                    ),
                    "area_Mm2": float(
                        row["water_spread_area_Mm2"]
                    ),
                    "segmental_capacity_MCM": float(
                        row[
                            "segmental_live_capacity_MCM"
                        ]
                    ),
                    "cumulative_capacity_MCM": float(
                        row[
                            "cumulative_live_capacity_MCM"
                        ]
                    )
                })

        self.rows.sort(
            key=lambda x: x["elevation_m"]
        )

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    def _validate(self):

        if len(self.rows) != 39:

            raise RuntimeError(
                f"Expected 39 CWC rows, "
                f"found {len(self.rows)}."
            )

        elevations = [
            row["elevation_m"]
            for row in self.rows
        ]

        capacities = [
            row["cumulative_capacity_MCM"]
            for row in self.rows
        ]

        if elevations != sorted(elevations):

            raise RuntimeError(
                "CWC elevations are not sorted."
            )

        for i in range(1, len(capacities)):

            if capacities[i] < capacities[i - 1]:

                raise RuntimeError(
                    "Cumulative storage is not "
                    f"monotonic at row {i}."
                )

        # ----------------------------------------------------
        # Published-value validation
        # ----------------------------------------------------

        checks = {
            219.456: 258.9693612,
            224.0: 496.9678706,
            230.0: 943.3780728,
            235.0: 1436.506494,
            240.0: 2043.943029,
            240.79: 2150.553085
        }

        for elevation, expected in checks.items():

            row = self._exact_row(elevation)

            if row is None:

                raise RuntimeError(
                    f"Missing CWC check level "
                    f"{elevation} m."
                )

            actual = row[
                "cumulative_capacity_MCM"
            ]

            if abs(actual - expected) > 1e-9:

                raise RuntimeError(
                    f"CWC validation failed at "
                    f"{elevation} m."
                )

    # --------------------------------------------------------
    # EXACT ROW
    # --------------------------------------------------------

    def _exact_row(self, elevation):

        for row in self.rows:

            if abs(
                row["elevation_m"] - elevation
            ) < 1e-9:

                return row

        return None

    # --------------------------------------------------------
    # RANGE
    # --------------------------------------------------------

    @property
    def minimum_elevation_m(self):

        return self.rows[0]["elevation_m"]

    @property
    def maximum_elevation_m(self):

        return self.rows[-1]["elevation_m"]

    @property
    def maximum_storage_MCM(self):

        return self.rows[-1][
            "cumulative_capacity_MCM"
        ]

    # --------------------------------------------------------
    # INTERPOLATION
    # --------------------------------------------------------

    def interpolate(self, elevation_m):

        elevation_m = float(elevation_m)

        if elevation_m < self.minimum_elevation_m:

            raise ValueError(
                f"Elevation {elevation_m} m is below "
                f"CWC DSL {self.minimum_elevation_m} m."
            )

        if elevation_m > self.maximum_elevation_m:

            raise ValueError(
                f"Elevation {elevation_m} m is above "
                f"CWC FRL {self.maximum_elevation_m} m."
            )

        # Exact published value
        exact = self._exact_row(elevation_m)

        if exact is not None:

            return {
                "elevation_m": elevation_m,
                "water_spread_area_Mm2":
                    exact["area_Mm2"],
                "segmental_capacity_MCM":
                    exact["segmental_capacity_MCM"],
                "cumulative_capacity_MCM":
                    exact["cumulative_capacity_MCM"],
                "method": "CWC_PUBLISHED_VALUE",
                "source":
                    "CWC Mettur Stanley Reservoir "
                    "Sedimentation Assessment 2020 - Table 3"
            }

        # ----------------------------------------------------
        # Linear interpolation
        # ----------------------------------------------------

        lower = None
        upper = None

        for i in range(len(self.rows) - 1):

            a = self.rows[i]
            b = self.rows[i + 1]

            if (
                a["elevation_m"]
                < elevation_m
                < b["elevation_m"]
            ):

                lower = a
                upper = b
                break

        if lower is None or upper is None:

            raise RuntimeError(
                "Unable to bracket requested elevation."
            )

        e1 = lower["elevation_m"]
        e2 = upper["elevation_m"]

        fraction = (
            (elevation_m - e1)
            /
            (e2 - e1)
        )

        area = (
            lower["area_Mm2"]
            +
            fraction
            *
            (
                upper["area_Mm2"]
                -
                lower["area_Mm2"]
            )
        )

        segmental = (
            lower["segmental_capacity_MCM"]
            +
            fraction
            *
            (
                upper["segmental_capacity_MCM"]
                -
                lower["segmental_capacity_MCM"]
            )
        )

        cumulative = (
            lower["cumulative_capacity_MCM"]
            +
            fraction
            *
            (
                upper["cumulative_capacity_MCM"]
                -
                lower["cumulative_capacity_MCM"]
            )
        )

        return {
            "elevation_m": elevation_m,
            "water_spread_area_Mm2": area,
            "segmental_capacity_MCM": segmental,
            "cumulative_capacity_MCM": cumulative,
            "method": "LINEAR_INTERPOLATION_BETWEEN_CWC_VALUES",
            "lower_elevation_m": e1,
            "upper_elevation_m": e2,
            "source":
                "CWC Mettur Stanley Reservoir "
                "Sedimentation Assessment 2020 - Table 3"
        }


# ============================================================
# VALIDATION TESTS
# ============================================================

def main():

    print("=" * 75)
    print("NEERAKSH — CWC STAGE-STORAGE ENGINE")
    print("=" * 75)

    model = CWCStageStorage(
        CSV_PATH
    )

    print()
    print("SOURCE VALIDATION")
    print("-" * 75)

    print(
        f"CWC rows: {len(model.rows)}"
    )

    print(
        f"Minimum elevation: "
        f"{model.minimum_elevation_m} m"
    )

    print(
        f"Maximum elevation / FRL: "
        f"{model.maximum_elevation_m} m"
    )

    print(
        f"Maximum CWC cumulative storage: "
        f"{model.maximum_storage_MCM:.6f} MCM"
    )

    print()
    print("PUBLISHED VALUE TESTS")
    print("-" * 75)

    test_levels = [
        204.216,
        219.456,
        224.0,
        230.0,
        235.0,
        240.0,
        240.79
    ]

    results = []

    for elevation in test_levels:

        result = model.interpolate(
            elevation
        )

        results.append(result)

        print(
            f"{elevation:8.3f} m -> "
            f"{result['cumulative_capacity_MCM']:.6f} MCM "
            f"[{result['method']}]"
        )

    print()
    print("INTERPOLATION TEST")
    print("-" * 75)

    interpolation_levels = [
        219.5,
        223.5,
        228.5,
        234.5,
        239.5
    ]

    interpolation_results = []

    for elevation in interpolation_levels:

        result = model.interpolate(
            elevation
        )

        interpolation_results.append(
            result
        )

        print(
            f"{elevation:8.3f} m -> "
            f"{result['cumulative_capacity_MCM']:.6f} MCM "
            f"(between "
            f"{result['lower_elevation_m']:.3f} "
            f"and "
            f"{result['upper_elevation_m']:.3f} m)"
        )

    # --------------------------------------------------------
    # IMPORTANT POLICY
    # --------------------------------------------------------

    print()
    print("=" * 75)
    print("RESERVOIR OBSERVATION POLICY")
    print("=" * 75)

    print(
        "TN Government observed reservoir level is NOT "
        "converted into CWC elevation here."
    )

    print(
        "TN Government storage is NOT replaced by "
        "CWC interpolated storage."
    )

    print(
        "A vertical-datum relationship must be verified "
        "before linking the two datasets."
    )

    print(
        "No fabricated reservoir elevation is permitted."
    )

    # --------------------------------------------------------
    # STATUS FILE
    # --------------------------------------------------------

    status = {
        "engine": "NEERAKSH_CWC_STAGE_STORAGE",
        "status": "READY",
        "source": (
            "CWC Mettur Stanley Reservoir "
            "Sedimentation Assessment 2020 - Table 3"
        ),
        "csv": str(CSV_PATH),
        "validated_rows": len(model.rows),
        "minimum_elevation_m":
            model.minimum_elevation_m,
        "maximum_elevation_m":
            model.maximum_elevation_m,
        "maximum_storage_MCM":
            model.maximum_storage_MCM,
        "published_value_checks": "PASSED",
        "interpolation": "LINEAR",
        "fabricated_values": False,
        "tn_portal_level_conversion": "BLOCKED_PENDING_DATUM_VERIFICATION",
        "tn_portal_storage_replacement": "NOT_ALLOWED"
    }

    status_path = (
        OUTPUT_DIR
        /
        "cwc_stage_storage_engine_status.json"
    )

    with status_path.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            status,
            f,
            indent=2
        )

    print()
    print("=" * 75)
    print("ENGINE STATUS")
    print("=" * 75)

    print(
        f"Saved:\n{status_path}"
    )

    print()
    print(
        "STATUS: CWC STAGE-STORAGE ENGINE READY."
    )


if __name__ == "__main__":
    main()