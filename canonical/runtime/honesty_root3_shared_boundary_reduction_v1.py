from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_HONESTY_ROOT3_SHARED_BOUNDARY_REDUCTION_RESULT_V1"

BOUND = {
    "canonical/governance/ROOT3_ZERO_VIOLATION_COMPLETE_MEDIATION_BREAKTHROUGH_20261005_V1.json": "f1b84e39bb7e4caff9e1b25e02bdfd3beaf31a03",
    "canonical/governance/TERMINAL_FALSIFICATION_CONTROL_LOOP_V2.json": "da8803584bc1e2bea672bcd1833e526ec489ac81",
    "canonical/verification/HONESTY_TARGET_SEMANTIC_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261006_V1.json": "1e164984ff1d41741246b489647b39373bd5c66f",
    "canonical/governance/HONESTY_CLOSED_WORLD_TOTALIZATION_V1.json": "7996512bdaa76c37ce79e0fabfbaafb77256f2d0",
}


def _blob(path: str) -> str:
    raw = (ROOT / path).read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode() + b"\0" + raw
    ).hexdigest()


def _load(path: str) -> dict[str, Any]:
    value = json.loads((ROOT / path).read_text())
    if not isinstance(value, dict):
        raise ValueError(path + ":OBJECT_REQUIRED")
    return value


def _contains(value: Any, needle: str) -> bool:
    if isinstance(value, str):
        return needle in value
    if isinstance(value, Mapping):
        return any(_contains(v, needle) for v in value.values())
    if isinstance(value, list):
        return any(_contains(v, needle) for v in value)
    return False


def evaluate() -> dict[str, Any]:
    errors: list[str] = []
    for path, sha in BOUND.items():
        if _blob(path) != sha:
            errors.append("SOURCE_BLOB_DRIFT:" + path)

    root3 = _load(
        "canonical/governance/ROOT3_ZERO_VIOLATION_COMPLETE_MEDIATION_BREAKTHROUGH_20261005_V1.json"
    )
    control = _load(
        "canonical/governance/TERMINAL_FALSIFICATION_CONTROL_LOOP_V2.json"
    )
    bridge = _load(
        "canonical/verification/HONESTY_TARGET_SEMANTIC_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261006_V1.json"
    )
    honesty = _load(
        "canonical/governance/HONESTY_CLOSED_WORLD_TOTALIZATION_V1.json"
    )

    if not str(bridge.get("status") or "").startswith(
        "INDEPENDENT_PUBLIC_RUNNER_PASS"
    ):
        errors.append("HONESTY_TARGET_SEMANTIC_BRIDGE_NOT_VERIFIED")

    root3_needed = [
        "ALL_MATERIAL_EXTERNALLY_OBSERVABLE_OR_DURABLE_EFFECT_EVENTS",
        "PRECOMMIT_MEDIATION",
        "NON_BYPASSABILITY",
        "SCOPE_IDENTITY",
        "USER_VISIBLE_FINAL_OUTPUTS",
        "DURABLE_FILES",
    ]
    for needle in root3_needed:
        if not _contains(root3, needle):
            errors.append("ROOT3_SHARED_BOUNDARY_TERM_MISSING:" + needle)

    if not _contains(control, "C_EFFECT_BOUNDARY_CLOSURE_V2"):
        errors.append("CURRENT_EFFECT_BOUNDARY_SUCCESSOR_NOT_BOUND")
    if not _contains(
        honesty, "CREDITED_CLOSED_WORLD_ENTRY_DOMINANCE"
    ):
        errors.append("HONESTY_ENTRY_DOMINANCE_ROOT_NOT_BOUND")
    if not _contains(
        honesty,
        "LEDGER_COMPLETENESS_AND_EMISSION_MEDIATION_REDUCE_TO_THE_SINGLE_REMAINING_ENTRY_DOMINANCE_PREMISE",
    ):
        errors.append("HONESTY_TOTALIZATION_IMPLICATION_NOT_BOUND")

    ok = not errors
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__CONDITIONAL_SHARED_BOUNDARY_REDUCTION__HONESTY_ENTRY_DOMINANCE_SUBSUMED_BY_ROOT3_COMPLETE_MEDIATION_IF_HONESTY_GUARD_IS_BOUND__ZERO_CREDIT"
            if ok
            else "FAIL_CLOSED"
        ),
        "pass": ok,
        "errors": errors,
        "conditional_implication": (
            "ROOT3_EFFECT_CHANNEL_TOTALITY_AND_PRECOMMIT_NON_BYPASSABILITY"
            "+HONESTY_CLOSED_WORLD_GUARD_SOUNDNESS"
            "=>HONESTY_CREDITED_ENTRY_DOMINANCE"
        ),
        "deduplicated_architecture": True if ok else None,
        "remaining_shared_root": (
            "C_EFFECT_BOUNDARY_CLOSURE_V2_WITH_HONESTY_GUARD_BINDING"
            if ok
            else None
        ),
        "separate_honesty_entry_boundary_required": False if ok else None,
        "effect_boundary_closed_now": False,
        "honesty_roots_closed_now": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


if __name__ == "__main__":
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
