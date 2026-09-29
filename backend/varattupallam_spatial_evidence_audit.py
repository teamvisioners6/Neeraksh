from pathlib import Path
import json
from datetime import datetime, timezone


ROOT = Path(r"C:\NEERAKSH-1")

OUTPUT_DIR = (
    ROOT
    / "simulations"
    / "outputs"
    / "varattupallam"
    / "spatial_audit"
)

OUTPUT = (
    OUTPUT_DIR
    / "spatial_evidence_audit.json"
)


def utc_now():
    return datetime.now(
        timezone.utc
    ).isoformat()


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    findings = {

        "cwc_study_point_available": True,

        "cwc_study_point": {
            "latitude": 11.6755867,
            "longitude": 77.5608833,
        },

        "dam_reference_location_available": True,

        "dam_reference_location": {
            "latitude": 11.6755867,
            "longitude": 77.5608833,
            "source": "CWC_VARATTUPALLAM_STUDY_REFERENCE",
        },

        "verified_breach_coordinate_available": False,

        "verified_breach_chainage_available": False,

        "verified_breach_cross_section_available": False,

        "verified_downstream_cross_sections_available": False,

        "study_point_accepted_as_breach_point": False,

        "dam_point_accepted_as_breach_point": False,

        "solver_unlock_allowed": False,

        "reason": (
            "Available sources establish the Varattupallam "
            "study/dam reference location but do not provide "
            "a verified breach coordinate, breach chainage, "
            "or breach cross-section suitable for unlocking "
            "the NEERAKSH spatial 2D solver."
        ),
    }

    report = {

        "status":
            "SPATIAL_EVIDENCE_INCOMPLETE",

        "timestamp_utc":
            utc_now(),

        "case_id":
            "CWC_VARATTUPALLAM_2019",

        "findings":
            findings,

        "policy":
            {
                "do_not_invent_breach_location":
                    True,

                "do_not_use_study_point_as_breach":
                    True,

                "do_not_use_dam_reference_as_breach":
                    True,

                "do_not_unlock_2d_solver":
                    True,

                "do_not_transfer_to_mettur":
                    True,
            },
    }

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

    print()
    print("=" * 72)
    print(
        "NEERAKSH – VARATTUPALLAM "
        "SPATIAL EVIDENCE AUDIT"
    )
    print("=" * 72)
    print()

    print(
        "CWC study point available       : TRUE"
    )

    print(
        "Verified breach coordinate      : FALSE"
    )

    print(
        "Verified breach chainage        : FALSE"
    )

    print(
        "Verified breach cross-section   : FALSE"
    )

    print(
        "Downstream cross-sections       : FALSE"
    )

    print(
        "Study point used as breach      : FALSE"
    )

    print(
        "2D solver unlock                : FALSE"
    )

    print()

    print(
        "=" * 72
    )

    print(
        "STATUS: SPATIAL_EVIDENCE_INCOMPLETE"
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

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )