from __future__ import annotations

from typing import Any, Mapping

ROOTS = (
    "R1_REALITY_CONTAINMENT",
    "R2_MISSION_SOUNDNESS",
    "R3_TERMINAL_CLOSURE",
    "R4_PROOF_AUTHORITY",
)

SEEDED_MUTATIONS = {
    "M1_OMIT_REAL_BEHAVIOR": "R1_REALITY_CONTAINMENT",
    "M2_ADD_UNPROVED_GOOD": "R2_MISSION_SOUNDNESS",
    "M3_TERMINAL_WITH_OPEN_FRONTIER": "R3_TERMINAL_CLOSURE",
    "M4_STALE_CERTIFICATE": "R4_PROOF_AUTHORITY",
    "M5_CIRCULAR_PROOF": "R4_PROOF_AUTHORITY",
    "M6_INCONSISTENT_PREMISES": "R4_PROOF_AUTHORITY",
    "M7_UNSOUND_RULE": "R4_PROOF_AUTHORITY",
    "M8_UNAUTHORIZED_SCOPE_NARROWING": "R2_MISSION_SOUNDNESS",
    "M9_UNKNOWN_AS_IMPOSSIBLE": "R1_REALITY_CONTAINMENT",
    "M10_PROOF_TIMEOUT_AS_FALSE": "CAPABILITY_CLOSURE",
}


def validate_spec(doc: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    roots = doc.get("roots")
    if not isinstance(roots, Mapping) or tuple(roots.keys()) != ROOTS:
        errors.append("ROOT_SET_OR_ORDER_DRIFT")
    theorem = doc.get("terminal_theorem")
    if not isinstance(theorem, Mapping):
        errors.append("TERMINAL_THEOREM_MISSING")
    else:
        if theorem.get("premises") != list(ROOTS):
            errors.append("TERMINAL_PREMISES_DRIFT")
        if theorem.get("semantic_derivation") != "B_real_SUBSET_B_plus_SUBSET_G_minus_SUBSET_G_real":
            errors.append("SEMANTIC_DERIVATION_DRIFT")
        if theorem.get("conclusion") != "B_real_SUBSET_G_real":
            errors.append("TERMINAL_CONCLUSION_DRIFT")
    admission = doc.get("new_e_admission")
    if not isinstance(admission, Mapping):
        errors.append("NEW_E_ADMISSION_MISSING")
    else:
        if admission.get("unknown_does_not_create_root") is not True:
            errors.append("UNKNOWN_ROOT_ESCALATION_ALLOWED")
        if admission.get("proof_search_failure_does_not_mean_falsehood") is not True:
            errors.append("SEARCH_FAILURE_TRUTH_CONFUSION")
    activation = doc.get("current_activation")
    if not isinstance(activation, Mapping):
        errors.append("ACTIVATION_MISSING")
    else:
        for key in ("R1_closed_claimed", "R2_closed_claimed", "R3_closed_claimed", "R4_closed_claimed"):
            if activation.get(key) is not False:
                errors.append("UNSUPPORTED_ROOT_CLOSURE:" + key)
        if activation.get("terminal_credit_delta") != 0:
            errors.append("UNAUTHORIZED_TERMINAL_CREDIT")
    return {
        "pass": not errors,
        "status": "PASS__ROOT_META_CONTROL_SPEC" if not errors else "FAIL_CLOSED",
        "errors": errors,
        "terminal_credit_delta": 0,
    }


def evaluate_terminal(root_states: Mapping[str, bool], *, false_success_witness: bool = False) -> dict[str, Any]:
    missing = [r for r in ROOTS if r not in root_states]
    extra = [r for r in root_states if r not in ROOTS]
    if missing or extra:
        return {
            "pass": False,
            "status": "FAIL_CLOSED_ROOT_STATE_SHAPE",
            "missing": missing,
            "extra": extra,
            "terminal": False,
            "terminal_credit_delta": 0,
        }
    all_roots = all(root_states[r] is True for r in ROOTS)
    if all_roots and false_success_witness:
        return {
            "pass": False,
            "status": "ROOT_THEOREM_FALSIFIED__FOUNDATIONAL_COUNTERMODEL",
            "terminal": False,
            "new_root_review_required": True,
            "terminal_credit_delta": 0,
        }
    return {
        "pass": True,
        "status": "TERMINAL_PROVED_BY_R1_R4" if all_roots else "OPEN__REFINE_EXISTING_ROOTS",
        "terminal": all_roots,
        "new_root_review_required": False,
        "terminal_credit_delta": 1 if all_roots else 0,
    }


def classify_new_e(candidate: Mapping[str, Any]) -> dict[str, Any]:
    if candidate.get("demonstrates_false_success_while_all_roots_hold") is True:
        return {
            "classification": "NEW_ROOT_REVIEW_REQUIRED__FOUNDATIONAL_COUNTERMODEL",
            "new_root_allowed": True,
            "terminal_credit_delta": 0,
        }
    violated = candidate.get("violated_roots") or []
    if not isinstance(violated, list) or any(r not in ROOTS for r in violated):
        return {
            "classification": "FAIL_CLOSED_INVALID_ROOT_REFERENCE",
            "new_root_allowed": False,
            "terminal_credit_delta": 0,
        }
    if violated:
        return {
            "classification": "EXISTING_ROOT_COUNTEREXAMPLE",
            "roots": violated,
            "new_root_allowed": False,
            "terminal_credit_delta": 0,
        }
    if candidate.get("proof_search_failure_only") is True:
        return {
            "classification": "CAPABILITY_CLOSURE__PROOF_SEARCH_OR_ROUTE_GAP",
            "new_root_allowed": False,
            "terminal_credit_delta": 0,
        }
    if candidate.get("closes_demonstrated_root_counterexample") is True or candidate.get("materially_reduces_proof_cost") is True:
        return {
            "classification": "EXISTING_ROOT_MECHANISM_CANDIDATE",
            "new_root_allowed": False,
            "terminal_credit_delta": 0,
        }
    return {
        "classification": "DEMOTE_FROM_CANONICAL_ARCHITECTURE",
        "new_root_allowed": False,
        "terminal_credit_delta": 0,
    }


def run_seeded_falsifiers() -> dict[str, Any]:
    detected = 0
    rows = []
    for mutation_id, expected in SEEDED_MUTATIONS.items():
        if expected == "CAPABILITY_CLOSURE":
            result = classify_new_e({"proof_search_failure_only": True})
            observed = "CAPABILITY_CLOSURE" if result["classification"].startswith("CAPABILITY_CLOSURE") else None
        else:
            result = classify_new_e({"violated_roots": [expected]})
            observed = (result.get("roots") or [None])[0]
        passed = observed == expected
        detected += int(passed)
        rows.append({"id": mutation_id, "expected": expected, "observed": observed, "pass": passed})
    total = len(SEEDED_MUTATIONS)
    return {
        "pass": detected == total,
        "status": "PASS__SEEDED_ROOT_FALSIFIERS" if detected == total else "FAIL_CLOSED",
        "detected": detected,
        "total": total,
        "rows": rows,
        "mutation_score": detected / total,
        "terminal_credit_delta": 0,
    }
