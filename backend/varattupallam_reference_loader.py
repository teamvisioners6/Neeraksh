from pathlib import Path
import json

ROOT = Path(r"C:\NEERAKSH-1")

REFERENCE_FILE = (
    ROOT
    / "data"
    / "engineering"
    / "varattupallam"
    / "cwc_varattupallam_reference.json"
)


def load_reference_case():
    if not REFERENCE_FILE.exists():
        raise FileNotFoundError(
            f"Reference file not found: {REFERENCE_FILE}"
        )

    # utf-8-sig handles both normal UTF-8 and PowerShell UTF-8 BOM files
    with REFERENCE_FILE.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)

    required = [
        "case_id",
        "case_name",
        "dam_name",
        "source",
        "published_reference_results"
    ]

    missing = [key for key in required if key not in data]

    if missing:
        raise ValueError(
            f"Missing required fields: {', '.join(missing)}"
        )

    if data.get("mettur_transfer_allowed") is not False:
        raise ValueError(
            "SAFETY CHECK FAILED: "
            "Varattupallam data cannot be transferred to Mettur."
        )

    return data


def print_case_summary(data):
    print()
    print("=" * 60)
    print("NEERAKSH — VALIDATION CASE")
    print("=" * 60)

    print(f"Case       : {data['case_id']}")
    print(f"Dam        : {data['dam_name']}")
    print(f"State      : {data['state']}")
    print(f"Purpose    : {data['purpose']}")
    print(f"Status     : {data['validation_status']}")

    print()
    print("PUBLISHED CWC REFERENCE RESULTS")
    print("-" * 60)

    for mechanism, values in data["published_reference_results"].items():
        print(f"\n{mechanism.upper()}")

        for key, value in values.items():
            print(f"  {key}: {value}")

    print()
    print("Mettur transfer allowed:", data["mettur_transfer_allowed"])
    print("=" * 60)


if __name__ == "__main__":
    case = load_reference_case()
    print_case_summary(case)
