from pathlib import Path
import csv
import re
import PyPDF2


# ============================================================
# NEERAKSH
# CWC Mettur / Stanley Reservoir
# Table 3 - SRS Survey 2019
# ============================================================

PDF_PATH = Path(
    r"C:\NEERAKSH-1\data\raw\CWC_Mettur_Stanley_Sedimentation_2020.pdf"
)

OUTPUT_CSV = Path(
    r"C:\NEERAKSH-1\data\hydrology\mettur\cwc_stage_storage_2020.csv"
)


EXPECTED_LEVELS = [
    204.216,
    205.0,
    206.0,
    207.0,
    208.0,
    209.0,
    210.0,
    211.0,
    212.0,
    213.0,
    214.0,
    215.0,
    216.0,
    217.0,
    218.0,
    219.0,
    219.456,
    220.0,
    221.0,
    222.0,
    223.0,
    224.0,
    225.0,
    226.0,
    227.0,
    228.0,
    229.0,
    230.0,
    231.0,
    232.0,
    233.0,
    234.0,
    235.0,
    236.0,
    237.0,
    238.0,
    239.0,
    240.0,
    240.79,
]


def normalize_number(value: str) -> float:
    """
    Convert PDF-extracted numeric strings into floats.

    Handles cases such as:
        943.3780 728 -> 943.3780728
        496.967 8706 -> 496.9678706
    """

    value = value.strip()

    # Remove internal spaces inside a split decimal number.
    value = re.sub(
        r"(\d+\.\d+)\s+(\d+)$",
        r"\1\2",
        value
    )

    return float(value)


def add_row(rows, elevation, area, segmental, cumulative):
    rows.append({
        "elevation_m": float(elevation),
        "water_spread_area_Mm2": float(area),
        "segmental_live_capacity_MCM": float(segmental),
        "cumulative_live_capacity_MCM": float(cumulative),
        "source": "CWC Mettur Stanley Reservoir Sedimentation Assessment 2020 - Table 3"
    })


def parse_page_26(text, rows):
    """
    Parse CWC PDF page 26 / printed page 20.

    Contains:
        DSL
        205-229
        MDDL 219.456
        220-229
        224 split-number case
    """

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    for line in lines:

        # ----------------------------------------------------
        # DSL 204.216
        # ----------------------------------------------------
        m = re.match(
            r"^DSL\s+204\.216\s+0\s+0\s+0$",
            line,
            re.IGNORECASE
        )

        if m:
            add_row(
                rows,
                204.216,
                0.0,
                0.0,
                0.0
            )
            continue

        # ----------------------------------------------------
        # MDDL 219.456
        #
        # PDF may extract "MDD L"
        # ----------------------------------------------------
        m = re.match(
            r"^MDD\s*L\s+219\.456\s+"
            r"([\d.]+)\s+"
            r"([\d.]+)\s+"
            r"([\d.]+)$",
            line,
            re.IGNORECASE
        )

        if m:
            add_row(
                rows,
                219.456,
                m.group(1),
                m.group(2),
                m.group(3)
            )
            continue

        # ----------------------------------------------------
        # Normal rows
        #
        # Example:
        # 219 41.54889483 39.61364473 239.6148253
        # ----------------------------------------------------
        m = re.match(
            r"^(\d{3})\s+"
            r"([\d.]+)\s+"
            r"([\d.]+)\s+"
            r"([\d.]+(?:\s+\d+)?)$",
            line
        )

        if not m:
            continue

        elevation = float(m.group(1))

        # Page 26 contains only 205-229.
        if elevation < 205 or elevation > 229:
            continue

        area = float(m.group(2))
        segmental = float(m.group(3))
        cumulative = normalize_number(m.group(4))

        add_row(
            rows,
            elevation,
            area,
            segmental,
            cumulative
        )


def parse_page_27(text, rows):
    """
    Parse CWC PDF page 27 / printed page 21.

    Contains:
        230-240
        FRL 240.79
    """

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    for line in lines:

        # ----------------------------------------------------
        # FRL 240.79
        # ----------------------------------------------------
        m = re.match(
            r"^FRL\s+240\.79\s+"
            r"([\d.]+)\s+"
            r"([\d.]+)\s+"
            r"([\d.]+(?:\s+\d+)?)$",
            line,
            re.IGNORECASE
        )

        if m:
            add_row(
                rows,
                240.79,
                m.group(1),
                m.group(2),
                normalize_number(m.group(3))
            )
            continue

        # ----------------------------------------------------
        # Normal 230-240 rows
        #
        # Handles:
        #
        # 230 87.43358716 85.22216465 943.3780 728
        #
        # which becomes:
        #
        # 943.3780728
        # ----------------------------------------------------
        m = re.match(
            r"^(\d{3})\s+"
            r"([\d.]+)\s+"
            r"([\d.]+)\s+"
            r"([\d.]+(?:\s+\d+)?)$",
            line
        )

        if not m:
            continue

        elevation = float(m.group(1))

        if elevation < 230 or elevation > 240:
            continue

        area = float(m.group(2))
        segmental = float(m.group(3))
        cumulative = normalize_number(m.group(4))

        add_row(
            rows,
            elevation,
            area,
            segmental,
            cumulative
        )


def main():

    if not PDF_PATH.exists():
        raise FileNotFoundError(
            f"CWC PDF not found:\n{PDF_PATH}"
        )

    print("=" * 75)
    print("NEERAKSH — CWC TABLE 3 EXTRACTION")
    print("=" * 75)

    reader = PyPDF2.PdfReader(str(PDF_PATH))

    print(f"PDF pages: {len(reader.pages)}")
    print()

    # --------------------------------------------------------
    # Printed pages 20 and 21 correspond to PDF indexes 25,26
    # --------------------------------------------------------

    page26 = reader.pages[25].extract_text() or ""
    page27 = reader.pages[26].extract_text() or ""

    print("Processing PDF page 26")
    print("Processing PDF page 27")
    print()

    rows = []

    parse_page_26(page26, rows)
    parse_page_27(page27, rows)

    # --------------------------------------------------------
    # Remove duplicate elevations if any
    # --------------------------------------------------------

    unique = {}

    for row in rows:
        unique[row["elevation_m"]] = row

    rows = list(unique.values())

    rows.sort(
        key=lambda x: x["elevation_m"]
    )

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    extracted_levels = {
        round(row["elevation_m"], 3)
        for row in rows
    }

    expected_levels = {
        round(level, 3)
        for level in EXPECTED_LEVELS
    }

    missing = sorted(
        expected_levels - extracted_levels
    )

    extra = sorted(
        extracted_levels - expected_levels
    )

    print("=" * 75)
    print("CWC TABLE 3 VALIDATION")
    print("=" * 75)

    print(
        f"Rows extracted: {len(rows)}"
    )

    if rows:
        print(
            f"Minimum elevation: "
            f"{rows[0]['elevation_m']}"
        )

        print(
            f"Maximum elevation: "
            f"{rows[-1]['elevation_m']}"
        )

    print(
        f"Expected CWC levels: "
        f"{len(EXPECTED_LEVELS)}"
    )

    print(
        f"Missing levels: "
        f"{missing if missing else 'NONE'}"
    )

    print(
        f"Unexpected levels: "
        f"{extra if extra else 'NONE'}"
    )

    # --------------------------------------------------------
    # Published-value checks
    # --------------------------------------------------------

    expected_values = {
        219.456: 258.9693612,
        224.0: 496.9678706,
        230.0: 943.3780728,
        235.0: 1436.506494,
        240.0: 2043.943029,
        240.79: 2150.553085,
    }

    print()
    print("Published-value checks:")

    lookup = {
        round(row["elevation_m"], 3): row
        for row in rows
    }

    for elevation, expected in expected_values.items():

        key = round(elevation, 3)

        if key not in lookup:
            print(
                f"{elevation} m -> MISSING"
            )
            continue

        actual = lookup[key][
            "cumulative_live_capacity_MCM"
        ]

        difference = abs(
            actual - expected
        )

        print(
            f"{elevation} m -> "
            f"{actual:.10f} MCM "
            f"(expected {expected:.10f}, "
            f"difference {difference:.10f})"
        )

    # --------------------------------------------------------
    # DO NOT WRITE AN INCOMPLETE TABLE
    # --------------------------------------------------------

    if missing:
        raise RuntimeError(
            "CWC Table 3 extraction is incomplete. "
            f"Missing elevations: {missing}"
        )

    if extra:
        raise RuntimeError(
            "Unexpected elevations detected: "
            f"{extra}"
        )

    if len(rows) != 39:
        raise RuntimeError(
            f"Expected 39 rows, got {len(rows)}."
        )

    # --------------------------------------------------------
    # Final monotonicity validation
    # --------------------------------------------------------

    previous_capacity = -1.0

    for row in rows:

        capacity = row[
            "cumulative_live_capacity_MCM"
        ]

        if capacity < previous_capacity:
            raise RuntimeError(
                "Cumulative capacity is not monotonic "
                f"at elevation {row['elevation_m']}."
            )

        previous_capacity = capacity

    # --------------------------------------------------------
    # Write final CSV
    # --------------------------------------------------------

    OUTPUT_CSV.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUTPUT_CSV.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "elevation_m",
                "water_spread_area_Mm2",
                "segmental_live_capacity_MCM",
                "cumulative_live_capacity_MCM",
                "source",
            ]
        )

        writer.writeheader()

        for row in rows:
            writer.writerow(row)

    print()
    print("=" * 75)
    print("CWC TABLE 3 EXTRACTION COMPLETE")
    print("=" * 75)

    print(
        f"Validated rows: {len(rows)}"
    )

    print(
        f"Output:\n{OUTPUT_CSV}"
    )

    print()
    print("FIRST ROW:")
    print(rows[0])

    print()
    print("MDDL ROW:")
    print(
        lookup[219.456]
    )

    print()
    print("224 m ROW:")
    print(
        lookup[224.0]
    )

    print()
    print("FRL ROW:")
    print(
        lookup[240.79]
    )

    print()
    print(
        "STATUS: OFFICIAL CWC TABLE 3 "
        "EXTRACTED AND VALIDATED."
    )


if __name__ == "__main__":
    main()