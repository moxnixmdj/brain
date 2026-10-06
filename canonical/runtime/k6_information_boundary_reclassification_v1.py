from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_K6_INFORMATION_BOUNDARY_RECLASSIFICATION_VERIFIER_V1"

CANDIDATE = "canonical/governance/K6_INFORMATION_BOUNDARY_RECLASSIFICATION_20261006_V1.json"
SOURCES = {
    "k6_projection": ("canonical/governance/K6_SHARED_SEPARATOR_KERNEL_PROJECTION_20261006_V1.json", "6de21878be3f45b318c8715487f03909a6f89e88"),
    "information_cut": ("canonical/governance/MINIMUM_CAPABILITY_KERNEL_INFORMATION_CUT_20261006_V1.json", "2b6c8150db5c635eb34c35c4041b99c7fc9c5dd5"),
    "saturation": ("canonical/governance/S0_G0_ZERO_REALITY_SATURATION_V1.json", "31effb16940e6d5c0c95259871b2e3c00cb5e400"),
    "survivor_authority": ("canonical/governance/ATOMIC_SURVIVOR_EXECUTION_AUTHORITY_RECONCILIATION_V1.json", "19b363f3f6be080b73ba144f82ef5f0a481217b1"),
    "subtraction": ("canonical/governance/ZERO_REALITY_RESIDUAL_SUBTRACTION_RESULT_V2.json", "cbf9dcf8a1fc6d1b813f41396cbf4d1335ed9cbd"),
    "global_graph": ("canonical/governance/GLOBAL_TERMINAL_OBLIGATION_GRAPH_V1.json", "eebdeb6de3b3cfaed30a3bc991dae0548d25e7f5"),
    "shared_basis": ("canonical/governance/SHARED_SEMANTIC_RESIDUAL_BASIS_V2.json", "ca28ce910e0d946bc7f78d556d47d0ac109a36f2"),
}

LATENT = {
    "S0_IMPLICIT_LONG_RANGE_SOURCE_TRACEABLE_RELATION_FORMATION",
    "S0_RAW_VISUAL_MULTIMODAL_SEMANTIC_BINDING",
    "G0_NOVEL_PREDICATE_OPERATOR_OR_EMIT_STRUCTURE",
}


def blob(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load(path: str) -> dict[str, Any]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(path + ":OBJECT_REQUIRED")
    return value


def verify() -> dict[str, Any]:
    errors: list[str] = []
    c = load(CANDIDATE)

    for name, (path, expected) in SOURCES.items():
        actual = blob(path)
        if actual != expected:
            errors.append(f"SOURCE_DRIFT:{name}:{actual}")
        bound = (c.get("source_bindings") or {}).get(name)
        if not isinstance(bound, dict) or bound.get("path") != path or bound.get("git_blob_sha") != expected:
            errors.append("CANDIDATE_SOURCE_BINDING_DRIFT:" + name)

    k6 = load(SOURCES["k6_projection"][0])
    sat = load(SOURCES["saturation"][0])
    auth = load(SOURCES["survivor_authority"][0])
    sub = load(SOURCES["subtraction"][0])
    graph = load(SOURCES["global_graph"][0])
    basis = load(SOURCES["shared_basis"][0])
    cut = load(SOURCES["information_cut"][0])

    if k6.get("candidate_global_compression", {}).get("unbound_semantic_generator") != "K6_TASK_SUFFICIENT_MODEL_AND_SEPARATOR_ACQUISITION":
        errors.append("K6_IDENTITY_DRIFT")

    if "IMPLEMENTATION_FRONTIER_SATURATED" not in str(sat.get("status")):
        errors.append("SATURATION_STATUS_DRIFT")

    facts = auth.get("facts") or {}
    if facts.get("current_preproof_implementation_residual_count") != 0:
        errors.append("PREPROOF_IMPLEMENTATION_RESIDUAL_REOPENED")
    if set(facts.get("current_atomic_diagnostic_classes") or []) != LATENT:
        errors.append("LATENT_DIAGNOSTIC_SET_DRIFT")
    if (auth.get("scheduling_effect") or {}).get("generic_s0_g0_donor_or_mechanism_work_authorized") is not False:
        errors.append("GENERIC_MECHANISM_WORK_REAUTHORIZED")

    if sub.get("implementation_authority") is not False:
        errors.append("SUBTRACTION_IMPLEMENTATION_AUTHORITY_DRIFT")
    if set(sub.get("surviving_atomic_residuals") or []) != LATENT:
        errors.append("SUBTRACTION_LATENT_SET_DRIFT")

    if "ZERO_PREPROOF_IMPLEMENTATION_RESIDUALS" not in str(graph.get("status")):
        errors.append("GLOBAL_GRAPH_PREPROOF_STATUS_DRIFT")

    comp = basis.get("compression_result") or {}
    if comp.get("true_remaining_implementation_classes") != []:
        errors.append("TRUE_IMPLEMENTATION_CLASSES_REOPENED")
    if set(comp.get("latent_diagnostic_classes") or []) != LATENT:
        errors.append("SHARED_BASIS_LATENT_SET_DRIFT")

    if (cut.get("scheduler_consequence") or {}).get("new_primary_object") != "MINIMUM_INFORMATION_AND_OPERATOR_SEPARATOR_KERNEL":
        errors.append("INFORMATION_CUT_PRIMARY_OBJECT_DRIFT")

    current = c.get("current_basis") or {}
    if current.get("current_unbound_implementation_generator_count") != 0:
        errors.append("CANDIDATE_UNBOUND_IMPLEMENTATION_COUNT_NOT_ZERO")
    if set(current.get("latent_diagnostic_classes") or []) != LATENT:
        errors.append("CANDIDATE_LATENT_SET_DRIFT")

    for key in ("execution_authority", "promotion_authority", "fresh_reality_authority"):
        if c.get(key) is not False:
            errors.append("AUTHORITY_OVERCLAIM:" + key)

    ok = not errors
    return {
        "schema": SCHEMA,
        "status": "PASS__K6_IS_CURRENTLY_CONDITIONAL_INFORMATION_BOUNDARY_NOT_PREPROOF_IMPLEMENTATION_GENERATOR__ZERO_CREDIT" if ok else "FAIL_CLOSED",
        "pass": ok,
        "errors": sorted(errors),
        "current_unbound_implementation_generator_count": 0 if ok else None,
        "latent_diagnostic_class_count": 3 if ok else None,
        "k6_information_interface_preserved": True if ok else None,
        "terminal_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


if __name__ == "__main__":
    out = verify()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
