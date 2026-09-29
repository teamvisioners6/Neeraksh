from pathlib import Path
import json


# ============================================================
# NEERAKSH
# ENGINEERING SCENARIO VALIDATOR
#
# Purpose:
#   Validate dam-break engineering inputs before allowing
#   the hydraulic solver to execute.
#
# Policy:
#   - No fabricated values
#   - Every engineering parameter requires provenance
#   - Official dam reference cannot automatically become
#     breach location
#   - Missing/invalid parameters block simulation
# ============================================================


PROJECT_ROOT = Path(r"C:\NEERAKSH-1")

INPUT_FILE = (
    PROJECT_ROOT
    / "simulations"
    / "inputs"
    / "mettur"
    / "breach_source_definition.json"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "simulations"
    / "outputs"
    / "mettur"
    / "engineering_validation"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


REQUIRED_BREACH_FIELDS = [
    "latitude",
    "longitude",
    "station_m",
    "invert_elevation_m",
    "crest_elevation_m",
    "width_m",
    "formation_time_hr",
]


def load_json(path):

    if not path.exists():

        raise FileNotFoundError(
            f"Input file not found:\n{path}"
        )

    with path.open(
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def get_breach_section(data):

    breach = (
        data
        .get("breach", {})
    )

    if not isinstance(
        breach,
        dict
    ):

        raise RuntimeError(
            "Invalid breach section."
        )

    return breach


def validate_value(
    breach,
    field
):

    value = breach.get(field)

    if value is None:
        return False, "missing"

    if isinstance(value, dict):

        actual = value.get("value")
        source = value.get("source")
        document = value.get("source_document")
        page = value.get("source_page")

    else:

        actual = value
        source = None
        document = None
        page = None

    if actual is None:
        return False, "missing"

    if source in (
        None,
        "",
        "UNKNOWN",
        "UNVERIFIED"
    ):
        return False, "missing_provenance"

    if document in (
        None,
        "",
        "UNKNOWN",
        "UNVERIFIED"
    ):
        return False, "missing_source_document"

    if page in (
        None,
        "",
        "UNKNOWN",
        "UNVERIFIED"
    ):
        return False, "missing_source_page"

    return True, {
        "value": actual,
        "source": source,
        "source_document": document,
        "source_page": page,
    }


def validate(data):

    errors = []
    validated = {}

    breach = get_breach_section(
        data
    )

    # --------------------------------------------------------
    # Failure mechanism
    # --------------------------------------------------------

    mechanism = breach.get(
        "failure_mechanism"
    )

    if isinstance(
        mechanism,
        dict
    ):

        mechanism_value = (
            mechanism.get("value")
        )
        mechanism_source = (
            mechanism.get("source")
        )
    else:

        mechanism_value = mechanism
        mechanism_source = None

    allowed_mechanisms = [
        "overtopping",
        "piping",
        "structural_failure",
        "user_defined",
    ]

    if mechanism_value not in allowed_mechanisms:

        errors.append(
            "Invalid or missing failure mechanism."
        )

    elif mechanism_source in (
        None,
        "",
        "UNKNOWN",
        "UNVERIFIED"
    ):

        errors.append(
            "Failure mechanism has no provenance."
        )

    else:

        validated[
            "failure_mechanism"
        ] = {
            "value":
                mechanism_value,
            "source":
                mechanism_source,
        }

    # --------------------------------------------------------
    # Breach parameters
    # --------------------------------------------------------

    for field in REQUIRED_BREACH_FIELDS:

        ok, result = validate_value(
            breach,
            field
        )

        if not ok:

            errors.append(
                f"{field}: {result}"
            )

        else:

            validated[field] = result

    # --------------------------------------------------------
    # Physical consistency
    # --------------------------------------------------------

    if (
        "width_m" in validated
        and float(
            validated["width_m"]["value"]
        ) <= 0
    ):

        errors.append(
            "Breach width must be greater than zero."
        )

    if (
        "formation_time_hr" in validated
        and float(
            validated[
                "formation_time_hr"
            ]["value"]
        ) <= 0
    ):

        errors.append(
            "Formation time must be greater than zero."
        )

    if (
        "latitude" in validated
    ):

        lat = float(
            validated[
                "latitude"
            ]["value"]
        )

        if not -90 <= lat <= 90:

            errors.append(
                "Breach latitude is invalid."
            )

    if (
        "longitude" in validated
    ):

        lon = float(
            validated[
                "longitude"
            ]["value"]
        )

        if not -180 <= lon <= 180:

            errors.append(
                "Breach longitude is invalid."
            )

    # --------------------------------------------------------
    # Dam reference protection
    # --------------------------------------------------------

    dam_reference = data.get(
        "dam",
        {}
    )

    dam_lat = dam_reference.get(
        "latitude"
    )

    dam_lon = dam_reference.get(
        "longitude"
    )

    if (
        "latitude" in validated
        and "longitude" in validated
        and dam_lat is not None
        and dam_lon is not None
    ):

        if (
            abs(
                float(
                    validated[
                        "latitude"
                    ]["value"]
                )
                -
                float(dam_lat)
            )
            < 1e-8
            and
            abs(
                float(
                    validated[
                        "longitude"
                    ]["value"]
                )
                -
                float(dam_lon)
            )
            < 1e-8
        ):

            errors.append(
                "Breach location is identical "
                "to official dam reference point. "
                "Dam reference cannot automatically "
                "be used as breach location."
            )

    return {
        "status":
            "VALIDATED"
            if not errors
            else "BLOCKED",

        "errors":
            errors,

        "validated_parameters":
            validated,

        "fabricated_values":
            False,

        "provenance_required":
            True,

        "simulation_allowed":
            len(errors) == 0,
    }


def main():

    print("=" * 75)
    print(
        "NEERAKSH — ENGINEERING SCENARIO VALIDATOR"
    )
    print("=" * 75)

    print()
    print(
        f"Input:\n{INPUT_FILE}"
    )

    data = load_json(
        INPUT_FILE
    )

    result = validate(
        data
    )

    print()
    print(
        "VALIDATION STATUS"
    )
    print("-" * 75)

    print(
        f"Status: {result['status']}"
    )

    print(
        f"Simulation allowed: "
        f"{result['simulation_allowed']}"
    )

    print(
        f"Fabricated values: "
        f"{result['fabricated_values']}"
    )

    print()

    if result["errors"]:

        print(
            "BLOCKING REASONS:"
        )

        for error in result["errors"]:

            print(
                f"  - {error}"
            )

    else:

        print(
            "All required engineering parameters "
            "have documented provenance."
        )

        print()
        print(
            "SIMULATION GATE: OPEN"
        )

    output = (
        OUTPUT_DIR
        / "engineering_scenario_validation.json"
    )

    with output.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            result,
            f,
            indent=2
        )

    print()
    print(
        f"Saved:\n{output}"
    )


if __name__ == "__main__":
    main()