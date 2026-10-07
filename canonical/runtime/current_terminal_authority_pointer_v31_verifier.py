from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

FILES = {
    "pointer": "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json",
    "theorem": "canonical/governance/PROFESSIONAL_PRESENTATION_PUBLIC_CONTRACT_INFORMATION_LOWER_BOUND_20261007_V1.json",
    "verification": "canonical/verification/PROFESSIONAL_PRESENTATION_PUBLIC_CONTRACT_INFORMATION_LOWER_BOUND_WOLFRAM_VERIFICATION_20261007_V1.json",
}

EXPECTED = {
    "theorem": "ef20a762365f9b4ab79ef695085bc76e35b0351d",
    "verification": "a6d2ed32ec004741950271f9b768ba949a8e9dcc",
}


def blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def load(key: str) -> dict:
    value = json.loads((ROOT / FILES[key]).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("OBJECT_REQUIRED:" + key)
    return value


def verify() -> dict:
    errors: list[str] = []

    for key, expected in EXPECTED.items():
        path = ROOT / FILES[key]
        if not path.is_file():
            errors.append("MISSING:" + key)
        elif blob_sha(path) != expected:
            errors.append("DRIFT:" + key)

    pointer = load("pointer")
    theorem = load("theorem")
    independent = load("verification")

    if pointer.get("schema") != "PROJECT_BRAIN_CURRENT_TERMINAL_AUTHORITY_POINTER_V31":
        errors.append("POINTER_SCHEMA")

    truth = pointer.get("live_truth", {})
    frontier = pointer.get("only_live_ABC_frontier", {})
    accounting = pointer.get("accounting", {})

    if truth.get("open_ABC_refinement_family_count") != 13:
        errors.append("OPEN_REFINEMENT_COUNT_CHANGED")
    if truth.get("current_noncomposition_wake_class_count") != 15:
        errors.append("WAKE_CLASS_COUNT_CHANGED")
    if frontier.get("current_information_wake_cut") != "15_CURRENT_BOUND_NONCOMPOSITION_WAKE_CLASSES_PLUS_1_DEFERRED_LOCAL_C":
        errors.append("INFORMATION_CUT_CHANGED")
    if truth.get("current_U_empty_proved") is not False:
        errors.append("U_EMPTY_OVERCLAIM")
    if truth.get("complete_selected_context_ABC_closed") is not False:
        errors.append("ABC_OVERCLAIM")
    if truth.get("D_finality_closed") is not False:
        errors.append("D_OVERCLAIM")
    if truth.get("terminal") is not False:
        errors.append("TERMINAL_OVERCLAIM")
    if accounting.get("terminal_credit_delta") != 0:
        errors.append("TERMINAL_CREDIT")

    if truth.get("professional_presentation_information_lower_bound_verified") is not True:
        errors.append("LOWER_BOUND_NOT_BOUND")
    if truth.get("professional_presentation_public_contract_order_complete") is not False:
        errors.append("PUBLIC_ORDER_COMPLETENESS_OVERCLAIM")

    if theorem.get("public_contract", {}).get("complete_presentation_utility_function_publicly_bound") is not False:
        errors.append("THEOREM_PUBLIC_UTILITY")
    if theorem.get("accounting", {}).get("terminal_credit_delta") != 0:
        errors.append("THEOREM_CREDIT")

    verified = independent.get("verified", {})
    if verified.get("current_public_contract_underdetermines_unspecified_pairwise_presentation_order") is not True:
        errors.append("INDEPENDENT_LOWER_BOUND")
    if verified.get("U_deletion") is not False:
        errors.append("INDEPENDENT_U_DELETION")
    if verified.get("terminal") is not False:
        errors.append("INDEPENDENT_TERMINAL")

    return {
        "pass": not errors,
        "errors": errors,
        "pointer_schema": pointer.get("schema"),
        "open_refinement_family_count": truth.get("open_ABC_refinement_family_count"),
        "information_wake_class_count": truth.get("current_noncomposition_wake_class_count"),
        "presentation_lower_bound_verified": truth.get("professional_presentation_information_lower_bound_verified"),
        "U_empty_proved": truth.get("current_U_empty_proved"),
        "terminal": truth.get("terminal"),
        "terminal_credit_delta": accounting.get("terminal_credit_delta"),
    }


if __name__ == "__main__":
    result = verify()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["pass"] else 1)
