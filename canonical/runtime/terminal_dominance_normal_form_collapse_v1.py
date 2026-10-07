from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SOURCES = {
    "theorem": (
        "canonical/governance/TERMINAL_DOMINANCE_NORMAL_FORM_COLLAPSE_20261007_V1.json",
        None,
    ),
    "authority_v6": (
        "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V6.json",
        "fafde6e942a423798c8cadd0d2a2ccfe140a9f53",
    ),
    "trace_superset": (
        "canonical/governance/OPUS55_OBSERVABLE_TRACE_SCOPE_SUPERSET_THEOREM_20261006_V1.json",
        "333bdc8306a19f005a600a47b415a4bd9cf9868c",
    ),
    "pullback": (
        "canonical/governance/EVALUATOR_PULLBACK_DOMINANCE_THEOREM_20261007_V1.json",
        "5febbf7c34368dcce354da44201436a49f87c108",
    ),
    "ownership": (
        "canonical/verification/GLOBAL_OWNERSHIP_POSTCONDITIONS_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
        "e0dbd996c18bdb818693ab0d217d751594a03d0f",
    ),
    "cleanroom": (
        "canonical/verification/TERMINAL_V3_DONOR_DELETION_CLEANROOM_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
        "d3144bf0aa618b15ef594d24de54d55cbdb329fd",
    ),
}


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"OBJECT_REQUIRED:{path}")
    return value


def verify() -> dict:
    errors: list[str] = []

    for key, (rel, expected) in SOURCES.items():
        path = ROOT / rel
        if not path.is_file():
            errors.append(f"MISSING:{key}")
            continue
        if expected is not None and git_blob_sha(path) != expected:
            errors.append(f"DRIFT:{key}")

    if errors:
        return {"pass": False, "errors": errors, "terminal": False}

    theorem = load_json(ROOT / SOURCES["theorem"][0])
    trace = load_json(ROOT / SOURCES["trace_superset"][0])
    pullback = load_json(ROOT / SOURCES["pullback"][0])
    ownership = load_json(ROOT / SOURCES["ownership"][0])
    cleanroom = load_json(ROOT / SOURCES["cleanroom"][0])

    if theorem.get("schema") != "PROJECT_BRAIN_TERMINAL_DOMINANCE_NORMAL_FORM_COLLAPSE_V1":
        errors.append("SCHEMA")
    if theorem.get("normal_form", {}).get("conditional_equivalence") != (
        "UNDER_P1_P2_P3_P4_AND_COMPLETE_TERMINAL_SEMANTICS__TERMINAL_IFF_B_star_AND_D_star"
    ):
        errors.append("NORMAL_FORM")
    if "EVERY_EXTERNALLY_USEFUL_OPUS55_CAPABILITY_IS_REPRESENTABLE" not in trace.get("theorem", {}).get("statement", ""):
        errors.append("TRACE_REPRESENTABILITY")
    if "pullback" not in pullback.get("theorem", {}):
        errors.append("PULLBACK_THEOREM")
    if ownership.get("result", {}).get("counters", {}).get("donor_dependent_required_behaviors") != 0:
        errors.append("HISTORICAL_OWNERSHIP")
    if not cleanroom.get("behavior_preserved"):
        errors.append("HISTORICAL_CLEANROOM")

    hard_nonclaims = set(theorem.get("hard_nonclaims", []))
    required_nonclaims = {
        "NO_CLAIM_B_star_IS_CURRENTLY_PROVED",
        "NO_CLAIM_P2_P3_OR_P4_IS_CURRENTLY_PROVED_GLOBALLY",
        "NO_CLAIM_D_star_IS_CLOSED_FOR_ANY_ROUTE_CHANGED_AFTER_THE_BOUND_OWNERSHIP_RECEIPTS",
        "NO_TRUTH_OBLIGATION_DELETED_YET",
        "NO_ACCEPTANCE_FAMILY_CAPABILITY_OWNERSHIP_OR_TERMINAL_CREDIT",
    }
    if not required_nonclaims.issubset(hard_nonclaims):
        errors.append("NONCLAIM_GUARD")

    return {
        "pass": not errors,
        "errors": errors,
        "normal_form": "B_star_AND_D_star" if not errors else None,
        "A_independent_set_enumeration_required": False if not errors else None,
        "C_arbitrary_composition_enumeration_required": False if not errors else None,
        "D_independent_ownership_effect_closure_required": True if not errors else None,
        "B_star_proved": False,
        "terminal": False,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    result = verify()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["pass"] else 1)
