from pathlib import Path
import json

ROOT = Path(r"C:\NEERAKSH-1")

INPUT = (
    ROOT
    / "data"
    / "engineering"
    / "varattupallam"
    / "cwc_breach_development_input.json"
)

TARGET = (
    ROOT
    / "data"
    / "engineering"
    / "varattupallam"
    / "cwc_hydrograph_validation_target.json"
)

OUTPUT = (
    ROOT
    / "simulations"
    / "outputs"
    / "varattupallam"
    / "cwc_parameter_audit.json"
)


def load_json(path):
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


inp = load_json(INPUT)
target = load_json(TARGET)

audit = {
    "case_id": inp["case_id"],
    "validation_type": "CWC_PARAMETER_AUDIT",
    "source_type": "OFFICIAL_CWC_CASE_STUDY",
    "scenarios": {},
    "overall_status": "PASS",
    "limitations": []
}


for scenario in ["overtopping", "piping"]:

    source = inp[scenario]
    reference = target["targets"][scenario]

    checks = {
        "breach_width_m": {
            "input": source["breach_width_m"],
            "reference": reference["breach_width_m"]
        },
        "formation_time_hr": {
            "input": source["formation_time_hr"],
            "reference": reference["formation_time_hr"]
        },
        "reference_peak_discharge_m3s": {
            "input": source["reference_peak_discharge_m3s"],
            "reference": reference["reference_peak_discharge_m3s"]
        }
    }

    scenario_status = "PASS"

    for name, values in checks.items():
        if values["input"] != values["reference"]:
            scenario_status = "FAIL"

    audit["scenarios"][scenario] = {
        "status": scenario_status,
        "checks": checks
    }

    if scenario_status != "PASS":
        audit["overall_status"] = "FAIL"


audit["limitations"].append(
    "CWC overtopping inflow hydrograph numerical time series is not "
    "available in the local project files or published searchable text."
)

audit["limitations"].append(
    "Therefore a complete independent overtopping hydrograph reproduction "
    "must not be claimed."
)

audit["limitations"].append(
    "The published CWC peak discharge values are retained as reference "
    "results, not treated as independently reproduced results."
)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

with OUTPUT.open("w", encoding="utf-8") as f:
    json.dump(audit, f, indent=2)

print("=" * 60)
print("NEERAKSH — CWC PARAMETER AUDIT")
print("=" * 60)

print("Case:", audit["case_id"])

for scenario, result in audit["scenarios"].items():
    print()
    print(scenario.upper())
    print("Status:", result["status"])

    for name, values in result["checks"].items():
        print(
            f"  {name}: "
            f"{values['input']} == {values['reference']}"
        )

print()
print("Overall:", audit["overall_status"])
print()
print("Limitation:")
for item in audit["limitations"]:
    print("-", item)

print()
print("Saved:", OUTPUT)
