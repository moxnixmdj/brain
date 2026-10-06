from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = "canonical/governance/K6_POSITIVE_ADEQUACY_COVER_CERTIFICATE_THEOREM_20261006_V1.json"
SOURCES = {
    "semantic_binding_projection": ("canonical/governance/K6_SEMANTIC_BINDING_RESIDUAL_PROJECTION_20261006_V3.json", "21d9f8551326f9741a5b13e6cc5d1494c23d9e34"),
    "policy_index_compiler": ("canonical/governance/K6_POLICY_INDEX_REFINEMENT_AND_PERSISTENCE_COMPILER_20261006_V1.json", "df1a557bc37eac67ad6446fbcca8f891128f9c94"),
    "policy_index_compiler_verification": ("canonical/verification/K6_POLICY_INDEX_REFINEMENT_PERSISTENCE_SPRITE_VERIFICATION_20261006_V1.json", "d1849b94c6a9119cc789a5e920c3687f18d81ff5"),
    "policy_cover_theorem": ("canonical/governance/K6_MINIMUM_ADEQUATE_POLICY_COVER_THEOREM_20261006_V1.json", "9bc8e53c8e5a59d540dd77ddb69e9f4100812668"),
    "v7_layered_order": ("canonical/governance/V7_LAYERED_DISTRIBUTIONAL_EQUAL_OR_BETTER_ORDER_20261006_V1.json", "af58fd7c48fcd18a86c6b93d8cd58f3fbce0cc74"),
}


def blob(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def verify() -> dict[str, object]:
    d = json.loads((ROOT / CANDIDATE).read_text(encoding="utf-8"))
    errors: list[str] = []
    for name, (path, expected) in SOURCES.items():
        actual = blob(path)
        if actual != expected:
            errors.append(f"SOURCE_DRIFT:{name}:{actual}")
        bound = d["source_bindings"].get(name)
        if not isinstance(bound, dict) or bound.get("path") != path or bound.get("git_blob_sha") != expected:
            errors.append("CANDIDATE_BINDING_DRIFT:" + name)

    theorem = d.get("theorem") or {}
    if "F_cert(w)_IS_A_SUBSET_OF_F_true(w)" not in theorem.get("monotonicity", ""):
        errors.append("POSITIVE_SUBRELATION_MONOTONICITY_MISSING")
    if "DOES_NOT_IMPLY_NO_COVER_EXISTS" not in theorem.get("incompleteness_boundary", ""):
        errors.append("INCOMPLETENESS_FIREWALL_MISSING")
    if "UPPER_BOUND_ON_THE_TRUE_MINIMUM_tau" not in theorem.get("minimality_boundary", ""):
        errors.append("TAU_BOUND_SEMANTICS_MISSING")

    successor = d.get("consequence_for_current_k6_residual") or {}
    if successor.get("candidate_successor") != "K6_SOUND_POLICY_COVER_WITNESS_AND_SELECTED_DISCRIMINATOR_BINDING":
        errors.append("SUCCESSOR_IDENTITY_DRIFT")

    for key in ("execution_authority", "promotion_authority", "fresh_reality_authority"):
        if d.get(key) is not False:
            errors.append("AUTHORITY_OVERCLAIM:" + key)
    for key, value in (d.get("accounting") or {}).items():
        if key.endswith("_delta") and value != 0:
            errors.append("CREDIT_OVERCLAIM:" + key)

    ok = not errors
    return {
        "status": "PASS__K6_POSITIVE_ADEQUACY_COVER_THEOREM_SOURCE_BOUND__ZERO_CREDIT" if ok else "FAIL_CLOSED",
        "pass": ok,
        "errors": sorted(errors),
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    out = verify()
    print(json.dumps(out, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
