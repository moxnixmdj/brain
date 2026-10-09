from typing import Any, Mapping

CCRT_ROOTS = {"R1", "R2", "R3", "R4"}
LEGACY_SUPPORT = {
    "LEGACY_ESCAPE_POLICY_ADEQUACY": {"R3", "R4"},
    "LEGACY_EFFECT_FINALITY": {"R1", "R3", "R4"},
}


def _fail(error: str) -> dict[str, Any]:
    return {
        "pass": False,
        "status": "FAIL_CLOSED",
        "error": error,
        "can_close_ccrt_root": False,
        "terminal_credit_delta": 0,
    }


def classify_root_claim(claim: Mapping[str, Any]) -> dict[str, Any]:
    ns = claim.get("source_namespace")
    src = claim.get("source_root")
    dst = claim.get("asserted_ccrt_root")
    rel = claim.get("relation")

    if dst not in CCRT_ROOTS:
        return _fail("UNKNOWN_CCRT_ROOT")

    if ns == "CCRT":
        if src != dst:
            return _fail("CCRT_ROOT_MISMATCH")
        if rel != "EQUIVALENT":
            return _fail("CCRT_DIRECT_REQUIRES_EQUIVALENT")
        return {
            "pass": True,
            "status": "DIRECT_CCRT_ROOT_CLAIM",
            "can_close_ccrt_root": True,
            "terminal_credit_delta": 0,
        }

    if ns in LEGACY_SUPPORT:
        if rel == "EQUIVALENT":
            return _fail("LEGACY_EQUIVALENCE_FORBIDDEN")
        if rel != "SUPPORTS":
            return _fail("LEGACY_RELATION_MUST_SUPPORT")
        if dst not in LEGACY_SUPPORT[ns]:
            return _fail("LEGACY_SUPPORT_TARGET_NOT_ALLOWED")
        return {
            "pass": True,
            "status": "DERIVED_SUPPORT_ONLY",
            "can_close_ccrt_root": False,
            "terminal_credit_delta": 0,
        }

    return _fail("UNKNOWN_OR_UNNAMESPACED_SOURCE")


def validate_bridge_document(bridge: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    theorem = bridge.get("theorem_namespace") or {}
    legacy = bridge.get("legacy_namespaces") or {}

    if theorem.get("id") != "CCRT":
        errors.append("THEOREM_NAMESPACE_NOT_CCRT")
    if set((theorem.get("roots") or {}).keys()) != CCRT_ROOTS:
        errors.append("CCRT_ROOT_SET_DRIFT")

    for ns in ("LEGACY_ESCAPE_POLICY_ADEQUACY", "LEGACY_EFFECT_FINALITY"):
        entry = legacy.get(ns) or {}
        if entry.get("equivalent_to_ccrt_roots"):
            errors.append(ns + "_EQUIVALENCE_FORBIDDEN")
        if entry.get("can_close_ccrt_root_by_label_identity") is not False:
            errors.append(ns + "_LABEL_CLOSURE_FORBIDDEN")

    return {
        "pass": not errors,
        "status": "PASS" if not errors else "FAIL_CLOSED",
        "errors": errors,
        "terminal_credit_delta": 0,
    }
