from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "canonical/governance/K6_POLICY_COVER_INFORMATION_BOUNDARY_CURRENT_20261006_V1.json"

SOURCES = {
    "policy_cover_theorem": ("canonical/governance/K6_MINIMUM_ADEQUATE_POLICY_COVER_THEOREM_20261006_V1.json", "9bc8e53c8e5a59d540dd77ddb69e9f4100812668"),
    "policy_cover_verification": ("canonical/verification/K6_MINIMUM_ADEQUATE_POLICY_COVER_SPRITE_VERIFICATION_20261006_V1.json", "84cc156f7067a6eb2be284727ac1a76f37343f1f"),
    "decision_quotient": ("canonical/governance/K6_TARGET_RELATIVE_DECISION_QUOTIENT_THEOREM_20261006_V1.json", "03baddc27d5ee9dd73656fdd801251e1f4fd8cc6"),
    "decision_quotient_verification": ("canonical/verification/K6_TARGET_RELATIVE_DECISION_QUOTIENT_SPRITE_VERIFICATION_20261006_V1.json", "51a449b74550894a04519ec8e17f008e468506c4"),
    "decision_refinement_compiler": ("canonical/runtime/k6_decision_refinement_compiler_v1.py", "11bd42f006f761670f602d5445da79a5a10683bc"),
    "information_resource_cut": ("canonical/governance/K6_INFORMATION_RESOURCE_CUT_20261006_V1.json", "b5b99aa056011139396ab5358dfe8763ff4d7d7f"),
    "information_resource_cut_verification": ("canonical/verification/K6_INFORMATION_RESOURCE_CUT_SPRITE_VERIFICATION_20261006_V1.json", "0e9ca08804e75fb48f96f9cbeae99dd0f7a0304f"),
    "survivor_execution_authority": ("canonical/governance/ATOMIC_SURVIVOR_EXECUTION_AUTHORITY_RECONCILIATION_V1.json", "19b363f3f6be080b73ba144f82ef5f0a481217b1"),
    "global_obligation_graph": ("canonical/governance/GLOBAL_TERMINAL_OBLIGATION_GRAPH_V1.json", "eebdeb6de3b3cfaed30a3bc991dae0548d25e7f5"),
    "shared_semantic_basis": ("canonical/governance/SHARED_SEMANTIC_RESIDUAL_BASIS_V2.json", "ca28ce910e0d946bc7f78d556d47d0ac109a36f2"),
}

LATENT = {
    "S0_IMPLICIT_LONG_RANGE_SOURCE_TRACEABLE_RELATION_FORMATION",
    "S0_RAW_VISUAL_MULTIMODAL_SEMANTIC_BINDING",
    "G0_NOVEL_PREDICATE_OPERATOR_OR_EMIT_STRUCTURE",
}


def blob(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load(path: Path | str) -> dict[str, Any]:
    p = path if isinstance(path, Path) else ROOT / path
    value = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("OBJECT_REQUIRED:" + str(p))
    return value


def verify() -> dict[str, Any]:
    c = load(CANDIDATE)
    errors: list[str] = []

    for name, (path, expected) in SOURCES.items():
        actual = blob(path)
        if actual != expected:
            errors.append(f"SOURCE_DRIFT:{name}:{actual}")
        bound = (c.get("source_bindings") or {}).get(name)
        if not isinstance(bound, dict) or bound.get("path") != path or bound.get("git_blob_sha") != expected:
            errors.append("CANDIDATE_BINDING_DRIFT:" + name)

    auth = load(SOURCES["survivor_execution_authority"][0])
    graph = load(SOURCES["global_obligation_graph"][0])
    basis = load(SOURCES["shared_semantic_basis"][0])
    cover = load(SOURCES["policy_cover_theorem"][0])

    facts = auth.get("facts") or {}
    if facts.get("current_preproof_implementation_residual_count") != 0:
        errors.append("PREPROOF_IMPLEMENTATION_RESIDUAL_REOPENED")
    if set(facts.get("current_atomic_diagnostic_classes") or []) != LATENT:
        errors.append("LATENT_DIAGNOSTIC_SET_DRIFT")
    if "ZERO_PREPROOF_IMPLEMENTATION_RESIDUALS" not in str(graph.get("status")):
        errors.append("GLOBAL_GRAPH_IMPLEMENTATION_STATUS_DRIFT")
    if (basis.get("compression_result") or {}).get("true_remaining_implementation_classes") != []:
        errors.append("SHARED_BASIS_IMPLEMENTATION_CLASSES_REOPENED")

    norm = c.get("current_normal_form") or {}
    if norm.get("current_unbound_preproof_implementation_generator_count") != 0:
        errors.append("CANDIDATE_GENERIC_K6_REOPENED")
    if set(norm.get("latent_diagnostic_classes") or []) != LATENT:
        errors.append("CANDIDATE_LATENT_SET_DRIFT")
    info = norm.get("conditional_information_interface") or {}
    if info.get("id") != "K6P_RESOURCE_BOUNDED_ADEQUATE_POLICY_INDEX_INFORMATION_BOUNDARY":
        errors.append("K6P_IDENTITY_DRIFT")
    if info.get("not_a_capability_box") is not True:
        errors.append("K6P_CAPABILITY_BOX_DRIFT")

    finite = c.get("finite_information_target") or {}
    if finite.get("exact_minimum_semantic_label_count") != "tau":
        errors.append("TAU_LABEL_BOUND_DRIFT")
    if finite.get("tight_fixed_length_policy_index_bits") != "CEIL_LOG2_tau":
        errors.append("TAU_BIT_BOUND_DRIFT")
    if (cover.get("candidate_compression") or {}).get("new_information_object") != "K6P_RESOURCE_BOUNDED_ADEQUATE_POLICY_INDEX_ACQUISITION":
        errors.append("POLICY_COVER_SOURCE_DRIFT")

    firewall = c.get("first_principles_firewall") or {}
    if "CAPABILITY" not in firewall.get("capability_gap", ""):
        errors.append("CAPABILITY_GAP_FIREWALL_MISSING")
    if "INFORMATION" not in firewall.get("information_gap", ""):
        errors.append("INFORMATION_GAP_FIREWALL_MISSING")

    comp = c.get("candidate_compression") or {}
    if comp.get("owned_implementation_generator_count") != 5:
        errors.append("OWNED_GENERATOR_COUNT_DRIFT")
    if comp.get("unbound_preproof_implementation_generator_count") != 0:
        errors.append("UNBOUND_IMPLEMENTATION_COUNT_DRIFT")
    if comp.get("conditional_information_boundary_count") != 1:
        errors.append("INFORMATION_BOUNDARY_COUNT_DRIFT")

    for key in ("execution_authority", "promotion_authority", "fresh_reality_authority"):
        if c.get(key) is not False:
            errors.append("AUTHORITY_OVERCLAIM:" + key)
    for key, value in (c.get("accounting") or {}).items():
        if key.endswith("_delta") and value != 0:
            errors.append("CREDIT_OVERCLAIM:" + key)

    ok = not errors
    return {
        "status": "PASS__K6_POLICY_COVER_INFORMATION_BOUNDARY_CURRENT__ZERO_PREPROOF_IMPLEMENTATION_RESIDUAL__ZERO_CREDIT" if ok else "FAIL_CLOSED",
        "pass": ok,
        "errors": sorted(errors),
        "owned_implementation_generator_count": 5 if ok else None,
        "unbound_preproof_implementation_generator_count": 0 if ok else None,
        "conditional_information_boundary_count": 1 if ok else None,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    out = verify()
    print(json.dumps(out, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
