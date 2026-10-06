from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_ASTRA_SCARCE_SEMANTIC_PACKET_V5_VERIFIER"

PACKET = "canonical/governance/ASTRA_SCARCE_ACCESS_TARGET_SEMANTICS_CLASSIFICATION_PACKET_20261006_V5.json"
UNIT = "canonical/governance/PRE_ASTRA_BEHAVIOR_CONTEXT_SEMANTIC_UNIT_REDUCTION_20261006_V1.json"
REGISTRY = "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
LAW = "canonical/laws/BEHAVIORAL_CONTRACT_AND_SEMANTIC_PURGE_LAW_V1.md"
MAP = "canonical/capabilities/opus55/ATOMIC_CAUSAL_INTELLIGENCE_MAP_V1.json"
PREFILTER = "canonical/governance/PRE_ASTRA_ATOMIC_FAMILY_SEMANTIC_PREFILTER_20261006_V1.json"
PUBLIC = "canonical/governance/PUBLIC_EVALUATOR_SEMANTICS_COMPRESSION_20261006_V1.json"
MINCUT = "canonical/governance/PRE_ASTRA_TARGET_INFORMATION_MINCUT_THEOREM_20261006_V1.json"

EXPECTED = {
    UNIT: "d914614f7997aa5d52d4cef76d31740d7ef4e043",
    REGISTRY: "ee187f611a0e82b2de495ee377682f39bc31dd31",
    LAW: "5b70ed776f13194ea02d7df1d878a88386a48b61",
    MAP: "1f86f034a4f34478e3e2cfd82b5d1b0f8e11143d",
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
    unit = load(UNIT)
    registry = load(REGISTRY)
    amap = load(MAP)
    law = (ROOT / LAW).read_text()

    if packet.get("schema") != (
        "PROJECT_BRAIN_ASTRA_SCARCE_ACCESS_TARGET_SEMANTICS_CLASSIFICATION_PACKET_V5"
    ):
        errors.append("PACKET_SCHEMA_INVALID")

    registry_ids = {
        str(row.get("behavior_id"))
        for row in registry.get("active_contracted_residuals") or []
        if isinstance(row, Mapping)
    }
    unit_ids = set(
        ((unit.get("current_active_contract_basis") or {}).get("behavior_ids") or [])
    )
    packet_ids = set(
        ((packet.get("current_behavioral_basis") or {}).get("behavior_ids") or [])
    )
    if len(registry_ids) != 12:
        errors.append("REGISTRY_ACTIVE_BEHAVIOR_COUNT_NOT_12")
    if registry_ids != unit_ids:
        errors.append("UNIT_BEHAVIOR_SET_MISMATCH")
    if registry_ids != packet_ids:
        errors.append("PACKET_BEHAVIOR_SET_MISMATCH")

    sem = registry.get("semantic_classes") or {}
    if sem.get("opus55_family_rows") != "ACCOUNTING_LABEL":
        errors.append("REGISTRY_FAMILY_LABEL_NOT_ACCOUNTING_ONLY")

    amap_interp = amap.get("interpretation") or {}
    if amap_interp.get("family_labels") != (
        "ACCOUNTING_LABEL_ONLY__NO_INTERNAL_MODULE_OR_MECHANISM_IMPLIED"
    ):
        errors.append("ATOMIC_MAP_FAMILY_LABEL_SEMANTICS_DRIFT")

    for phrase in (
        "The 19 Opus 5.5 capability families are acceptance/evaluation surfaces only.",
        "Only contracted behavioral leaves may drive implementation or promotion.",
    ):
        if phrase not in law:
            errors.append("SEMANTIC_PURGE_LAW_PHRASE_MISSING:" + phrase)

    theorem = unit.get("theorem") or {}
    if theorem.get("id") != "E_M_U_CLASSIFICATION_UNIT_IS_BEHAVIOR_CONTEXT_NOT_FAMILY_LABEL":
        errors.append("UNIT_THEOREM_ID_DRIFT")
    if "BEHAVIORAL_CONTRACT_AND_A_CONTEXT_EQUIVALENCE_CLASS" not in str(
        theorem.get("statement") or ""
    ):
        errors.append("UNIT_THEOREM_STATEMENT_WEAK")

    bound = packet.get("bound_reductions") or {}
    expected_packet_bindings = {
        "atomic_family_prefilter": EXPECTED[PREFILTER],
        "public_evaluator_compression": EXPECTED[PUBLIC],
        "pre_astra_information_mincut": EXPECTED[MINCUT],
        "behavior_context_unit_reduction": EXPECTED[UNIT],
        "behavioral_contract_registry": EXPECTED[REGISTRY],
        "semantic_purge_law": EXPECTED[LAW],
        "atomic_causal_map": EXPECTED[MAP],
    }
    for key, expected in expected_packet_bindings.items():
        if (bound.get(key) or {}).get("git_blob_sha") != expected:
            errors.append("PACKET_BINDING_MISMATCH:" + key)

    semantic_unit = packet.get("semantic_unit") or {}
    if semantic_unit.get("unit") != "BEHAVIORAL_CONTRACT_X_CONTEXT_EQUIVALENCE_CLASS":
        errors.append("PACKET_SEMANTIC_UNIT_INVALID")
    if semantic_unit.get("family_role") != (
        "PROJECT_CERTIFIED_BEHAVIOR_CONTEXT_RESULTS_BACK_TO_FAMILY_ACCEPTANCE_SURFACES_ONLY_AFTER_SEMANTIC_CERTIFICATION."
    ):
        errors.append("PACKET_FAMILY_ROLE_DRIFT")

    truth = set(packet.get("truth_boundary") or [])
    for required in {
        "CURRENT_12_BEHAVIOR_CONTRACTS_NOT_ASSUMED_COMPLETE",
        "FAMILY_LABELS_ACCOUNTING_ONLY",
        "NO_FAMILY_E_M_OR_U_WITHOUT_UNIFORMITY_THEOREM",
        "NO_E_WITHOUT_COMPLETE_EXPLICIT_SEMANTICS",
        "NO_M_WITHOUT_PROVED_ALL_UTILITY_MONOTONICITY",
        "NO_PRIVATE_SCORE_INFERENCE",
        "NO_WEAKENING_OF_TERMINAL_OBJECTIVE",
    }:
        if required not in truth:
            errors.append("TRUTH_BOUNDARY_MISSING:" + required)

    known = packet.get("known_information_removed_before_astra") or {}
    expected_counts = {
        "unresolved_atomic_acceptance_contracts_already_partitioned": 24,
        "fixed_score_target_tuples_already_bound": 14,
        "public_evaluator_families_already_researched": 10,
        "current_open_family_labels_for_accounting_only": 14,
        "current_active_contracted_residual_behaviors": 12,
        "astra_access_consumed": 0,
    }
    for key, expected in expected_counts.items():
        if known.get(key) != expected:
            errors.append("KNOWN_COUNT_DRIFT:" + key)
    if known.get("family_label_semantic_authority") is not False:
        errors.append("FAMILY_LABEL_AUTHORITY_OVERCLAIM")

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
            "PASS__BEHAVIOR_CONTEXT_IS_SEMANTIC_UNIT__12_ACTIVE_CONTRACTS__FAMILY_LABELS_ACCOUNTING_ONLY__ZERO_ASTRA_ACCESS"
            if ok else "FAIL_CLOSED"
        ),
        "pass": ok,
        "errors": sorted(errors),
        "active_behavior_contract_count": 12 if ok else None,
        "family_label_semantic_authority": False,
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
