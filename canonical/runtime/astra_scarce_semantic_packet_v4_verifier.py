from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_ASTRA_SCARCE_SEMANTIC_PACKET_V4_VERIFIER"

PACKET = "canonical/governance/ASTRA_SCARCE_ACCESS_TARGET_SEMANTICS_CLASSIFICATION_PACKET_20261006_V4.json"
PREFILTER = "canonical/governance/PRE_ASTRA_ATOMIC_FAMILY_SEMANTIC_PREFILTER_20261006_V1.json"
PUBLIC = "canonical/governance/PUBLIC_EVALUATOR_SEMANTICS_COMPRESSION_20261006_V1.json"
MINCUT = "canonical/governance/PRE_ASTRA_TARGET_INFORMATION_MINCUT_THEOREM_20261006_V1.json"

EXPECTED = {
    PREFILTER: "f16536e2a7b89686457e004fa63d1ee723a6b42e",
    PUBLIC: "8228493403426407ad773bd1f51bb64552ddf5c1",
    MINCUT: "6622a34c2de805523ac2c87808c13fb6cba1f3fe",
}


def blob(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(data)).encode() + b"\0" + data
    ).hexdigest()


def load(path: str) -> dict[str, Any]:
    value = json.loads((ROOT / path).read_text())
    if not isinstance(value, dict):
        raise ValueError(path + ":OBJECT_REQUIRED")
    return value


def evaluate() -> dict[str, Any]:
    errors: list[str] = []
    for path, expected in EXPECTED.items():
        actual = blob(path)
        if actual != expected:
            errors.append(f"SOURCE_BLOB_DRIFT:{path}:{actual}")

    packet = load(PACKET)
    pre = load(PREFILTER)
    public = load(PUBLIC)

    if packet.get("schema") != (
        "PROJECT_BRAIN_ASTRA_SCARCE_ACCESS_TARGET_SEMANTICS_CLASSIFICATION_PACKET_V4"
    ):
        errors.append("PACKET_SCHEMA_INVALID")

    bindings = {
        "prefilter": (
            (packet.get("bound_prefilter") or {}).get("git_blob_sha"),
            EXPECTED[PREFILTER],
        ),
        "public": (
            (packet.get("bound_public_evaluator_compression") or {}).get("git_blob_sha"),
            EXPECTED[PUBLIC],
        ),
        "mincut": (
            (packet.get("pre_astra_mincut") or {}).get("git_blob_sha"),
            EXPECTED[MINCUT],
        ),
    }
    for name, (actual, expected) in bindings.items():
        if actual != expected:
            errors.append("PACKET_BINDING_MISMATCH:" + name)

    packet_families = set(
        ((packet.get("family_context_residual") or {}).get("families") or [])
    )
    pre_families = set(
        ((pre.get("family_semantic_frontier") or {}).get("families") or {}).keys()
    )
    if packet_families != pre_families:
        errors.append("FAMILY_SET_MISMATCH")
    if len(packet_families) != 14:
        errors.append("FAMILY_COUNT_NOT_14")

    known = packet.get("known_information_already_removed_from_astra_budget") or {}
    if known.get("atomic_acceptance_contract_count") != 24:
        errors.append("ATOMIC_COUNT_NOT_24")
    if known.get("fixed_score_target_tuple_count") != 14:
        errors.append("FIXED_TARGET_TUPLE_COUNT_NOT_14")

    public_findings = {
        str(row.get("target_family"))
        for row in public.get("findings") or []
        if isinstance(row, dict)
    }
    declared_public = set(known.get("public_evaluator_family_research_already_compressed") or [])
    if declared_public != public_findings:
        errors.append("PUBLIC_EVALUATOR_FAMILY_SET_MISMATCH")

    forbidden = set(known.get("forbidden_redundant_work") or [])
    for required in {
        "RESTATING_ATOMIC_THRESHOLDS_OR_MATCHED_ACCEPTANCE_RELATIONS",
        "GUESSING_PRIVATE_BENCHMARK_RESULTS",
        "GENERIC_MOMENT_OR_FINITE_STATISTIC_COMPRESSION_FOR_ARBITRARY_U",
    }:
        if required not in forbidden:
            errors.append("MISSING_SCARCITY_GUARD:" + required)

    truth = set(packet.get("truth_boundary") or [])
    for required in {
        "ATOMIC_E_SHAPE_DOES_NOT_IMPLY_FAMILY_E",
        "PUBLIC_EVALUATOR_E_CANDIDATE_DOES_NOT_IMPLY_FAMILY_E",
        "NO_FAMILY_M_WITHOUT_PROVED_ALL_UTILITY_MONOTONICITY",
        "NO_PRIVATE_SCORE_INFERENCE",
        "NO_WEAKENING_OF_TERMINAL_OBJECTIVE",
    }:
        if required not in truth:
            errors.append("TRUTH_BOUNDARY_MISSING:" + required)

    accounting = packet.get("accounting") or {}
    if accounting.get("astra_access_consumed_by_packet_creation") != 0:
        errors.append("ASTRA_ACCESS_ALREADY_CONSUMED")
    for key in (
        "terminal_credit_delta",
        "acceptance_credit_delta",
        "family_credit_delta",
        "capability_credit_delta",
        "ownership_credit_delta",
    ):
        if accounting.get(key) != 0:
            errors.append("NONZERO_CREDIT:" + key)

    if packet.get("execution_authority") is not False:
        errors.append("EXECUTION_AUTHORITY_OVERCLAIM")
    if packet.get("promotion_authority") is not False:
        errors.append("PROMOTION_AUTHORITY_OVERCLAIM")
    if packet.get("fresh_reality_authority") is not False:
        errors.append("FRESH_REALITY_OVERCLAIM")

    ok = not errors
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__SINGLE_SCARCE_ASTRA_PACKET_BOUND_TO_ATOMIC_AND_PUBLIC_EVALUATOR_COMPRESSION__14_FAMILY_RESIDUAL__ZERO_ACCESS"
            if ok else "FAIL_CLOSED"
        ),
        "pass": ok,
        "errors": sorted(errors),
        "family_count": 14 if ok else None,
        "atomic_contract_count_removed_from_query_budget": 24 if ok else None,
        "fixed_target_tuple_count_removed_from_query_budget": 14 if ok else None,
        "public_evaluator_family_count_removed_from_query_budget": len(public_findings) if ok else None,
        "astra_access_consumed": 0,
        "terminal_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


if __name__ == "__main__":
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
