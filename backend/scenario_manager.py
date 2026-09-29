import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(r"C:\NEERAKSH-1")

SCENARIO_DIR = BASE / "simulations" / "scenarios"
METTUR_DIR = SCENARIO_DIR / "mettur"
REFERENCE_DIR = SCENARIO_DIR / "reference"

METTUR_DIR.mkdir(parents=True, exist_ok=True)
REFERENCE_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# NEERAKSH - SCENARIO MANAGER
# ============================================================

manager = {
    "project": "NEERAKSH",

    "scenario_policy": {
        "rule_1": (
            "Observed reservoir data must remain separate "
            "from hypothetical dam-break parameters."
        ),

        "rule_2": (
            "Mettur breach parameters must not be fabricated."
        ),

        "rule_3": (
            "Reference case-study parameters must never be "
            "labelled as Mettur parameters."
        ),

        "rule_4": (
            "Every simulation parameter must contain provenance."
        )
    },

    "scenario_types": {

        "OFFICIAL_STUDY": {
            "description": (
                "Parameters obtained from an authoritative "
                "Mettur-specific dam-break study."
            ),
            "allowed_for_mettur": True,
            "status": "WAITING_FOR_SOURCE"
        },

        "ENGINEERING_INPUT": {
            "description": (
                "Parameters entered by an authorized engineer "
                "or project operator."
            ),
            "allowed_for_mettur": True,
            "required_provenance": True,
            "status": "READY_FOR_INPUT"
        },

        "REFERENCE_CASE": {
            "description": (
                "Published dam-break case used to validate "
                "the NEERAKSH modelling pipeline."
            ),
            "allowed_for_mettur_prediction": False,
            "allowed_for_pipeline_validation": True,
            "status": "REFERENCE_ONLY"
        }
    },

    "active_scenario": {
        "scenario_type": None,
        "scenario_id": None,
        "dam": "Mettur Dam / Stanley Reservoir",
        "failure_type": None,
        "parameters": {},
        "provenance": {},
        "status": "NO_ACTIVE_BREACH_SCENARIO"
    },

    "reference_cases": {

        "VARATTUPALLAM_CWC_2019": {

            "name": "Varattupallam Dam Break Case Study",

            "source_organization":
                "Central Water Commission",

            "country": "India",

            "purpose":
                "Hydraulic-model pipeline validation",

            "allowed_use": [
                "solver validation",
                "hydrograph validation",
                "inundation workflow validation"
            ],

            "not_allowed_use": [
                "Mettur breach prediction",
                "Mettur breach parameter substitution"
            ]
        }
    },

    "created_at":
        datetime.now(timezone.utc).isoformat()
}

output = METTUR_DIR / "scenario_manager.json"

with open(output, "w", encoding="utf-8") as f:
    json.dump(manager, f, indent=2)

print("=" * 70)
print("NEERAKSH - SCENARIO MANAGER")
print("=" * 70)

print("\nScenario types:")
print("- OFFICIAL_STUDY")
print("- ENGINEERING_INPUT")
print("- REFERENCE_CASE")

print("\nMettur status:")
print("No breach scenario activated.")

print("\nReference case:")
print("Varattupallam CWC case study")
print("Purpose: modelling pipeline validation only")

print("\nSaved:")
print(output)

print("\n" + "=" * 70)
print("SCENARIO MANAGER READY")
print("=" * 70)
