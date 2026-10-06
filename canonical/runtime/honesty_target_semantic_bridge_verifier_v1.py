from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_HONESTY_TARGET_SEMANTIC_BRIDGE_VERIFIER_V1"

BRIDGE = "canonical/governance/HONESTY_TARGET_SEMANTIC_BRIDGE_20261006_V1.json"
SOURCE = "canonical/governance/OPUS55_HONESTY_PRIMARY_SOURCE_SNAPSHOT_BINDING_20261006_V1.json"
COUNTEREXAMPLE = "canonical/governance/UNIVERSAL_OBSERVABLE_DOMINANCE_HONESTY_COUNTEREXAMPLE_20261006_V1.json"
REDUCTION = "canonical/governance/HONESTY_ENVELOPE_CONDITIONAL_DOMINANCE_REDUCTION_20261006_V1.json"
SCOPE = "canonical/governance/OPUS55_OBSERVABLE_TRACE_SCOPE_SUPERSET_THEOREM_20261006_V1.json"

EXPECTED = {
    SOURCE: "df59bfa94890fcffd95baab37b36674ca58dc67d",
    COUNTEREXAMPLE: "833cfa5fb8a444a93fe7e25f9e5b7a94b79667ce",
    REDUCTION: "86a841893259ca5caed06190baffb572fd5a01cd",
    SCOPE: "333bdc8306a19f005a600a47b415a4bd9cf9868c",
}

BEHAVIOR = {
    "ANTHROPIC_EVALUATES_FALSE_OR_UNEARNED_TASK_COMPLETION_AS_MISLEADING_BEHAVIOR",
    "ANTHROPIC_EVALUATES_DISCLOSURE_OF_PREEXISTING_ANSWER_USE",
    "ANTHROPIC_EVALUATES_DISCLOSURE_OF_HIDDEN_CHANGES",
    "ANTHROPIC_EVALUATES_HONESTY_UNDER_PRESSURE",
}
PERFORMANCE = {
    "ANTHROPIC_REPORTS_OPUS55_RELATIVE_PERFORMANCE_ON_THE_MISLEADING_BEHAVIOR_SUITE"
}

REQUIRED_MAP = {
    "ANTHROPIC_EVALUATES_FALSE_OR_UNEARNED_TASK_COMPLETION_AS_MISLEADING_BEHAVIOR":
        {"NO_FALSE_COMPLETION_CLAIM", "DISCLOSE_MATERIAL_UNFINISHED_OR_FAILED_WORK"},
    "ANTHROPIC_EVALUATES_DISCLOSURE_OF_PREEXISTING_ANSWER_USE":
        {"DISCLOSE_LOAD_BEARING_USE_OF_PREEXISTING_ANSWER_OR_HIDDEN_CHANGE_WHEN_MATERIAL"},
    "ANTHROPIC_EVALUATES_DISCLOSURE_OF_HIDDEN_CHANGES":
        {"DISCLOSE_LOAD_BEARING_USE_OF_PREEXISTING_ANSWER_OR_HIDDEN_CHANGE_WHEN_MATERIAL"},
    "ANTHROPIC_EVALUATES_HONESTY_UNDER_PRESSURE":
        {"RESIST_PRESSURE_TO_STATE_A_BELIEF_THE_POLICY_DOES_NOT_HOLD"},
}


def _blob(path: str) -> str:
    data = (ROOT / path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _load(path: str) -> dict[str, Any]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("DOCUMENT_NOT_MAPPING:" + path)
    return value


def evaluate(
    bridge: Mapping[str, Any] | None = None,
    source: Mapping[str, Any] | None = None,
    counterexample: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []

    for path, expected in EXPECTED.items():
        if _blob(path) != expected:
            errors.append("SOURCE_BLOB_DRIFT:" + path)

    b = dict(bridge) if bridge is not None else _load(BRIDGE)
    s = dict(source) if source is not None else _load(SOURCE)
    c = dict(counterexample) if counterexample is not None else _load(COUNTEREXAMPLE)

    source_facts = s.get("observed_semantic_facts")
    if not isinstance(source_facts, list):
        errors.append("SOURCE_FACTS_INVALID")
        source_set: set[str] = set()
    else:
        source_set = {str(x) for x in source_facts}

    expected_source = BEHAVIOR | PERFORMANCE
    if source_set != expected_source:
        errors.append("PRIMARY_SOURCE_FACT_SET_DRIFT")

    snapshots = s.get("snapshots")
    if not isinstance(snapshots, list) or len(snapshots) != 2:
        errors.append("DUAL_SNAPSHOT_BINDING_MISSING")
    else:
        for i, row in enumerate(snapshots):
            markers = row.get("marker_results") if isinstance(row, Mapping) else None
            if not isinstance(markers, Mapping) or set(markers.values()) != {True}:
                errors.append(f"SNAPSHOT_{i}_MARKERS_NOT_ALL_TRUE")
            if not isinstance(markers, Mapping) or len(markers) != 5:
                errors.append(f"SNAPSHOT_{i}_MARKER_COUNT_NOT_5")

    rows = b.get("target_observation_classification")
    if not isinstance(rows, list):
        errors.append("CLASSIFICATION_INVALID")
        behavior_rows: set[str] = set()
        performance_rows: set[str] = set()
    else:
        behavior_rows = {
            str(x.get("source_fact"))
            for x in rows
            if isinstance(x, Mapping) and x.get("class") == "LOAD_BEARING_BEHAVIOR_SEMANTIC"
        }
        performance_rows = {
            str(x.get("source_fact"))
            for x in rows
            if isinstance(x, Mapping) and x.get("class") == "TARGET_PERFORMANCE_METADATA_NOT_A_BEHAVIOR_SEMANTIC"
        }
        classified = behavior_rows | performance_rows
        if classified != source_set or len(rows) != len(source_set):
            errors.append("CLASSIFICATION_NOT_EXACT_SOURCE_PARTITION")

    if behavior_rows != BEHAVIOR:
        errors.append("BEHAVIOR_SEMANTIC_SET_MISMATCH")
    if performance_rows != PERFORMANCE:
        errors.append("PERFORMANCE_METADATA_SET_MISMATCH")

    leaves = (
        c.get("witness", {}).get("leaves", [])
        if isinstance(c.get("witness"), Mapping)
        else []
    )
    leaf_set = {str(x) for x in leaves} if isinstance(leaves, list) else set()
    if len(leaf_set) != 5:
        errors.append("BRAIN_HONESTY_LEAF_SET_NOT_5")

    mappings = b.get("mapping")
    actual_map: dict[str, set[str]] = {}
    if not isinstance(mappings, list):
        errors.append("MAPPING_INVALID")
    else:
        for i, row in enumerate(mappings):
            if not isinstance(row, Mapping):
                errors.append(f"MAPPING_{i}_INVALID")
                continue
            target = str(row.get("target_semantic") or "")
            brain = row.get("brain_leaves")
            if not isinstance(brain, list):
                errors.append(f"MAPPING_{i}_BRAIN_LEAVES_INVALID")
                continue
            if target in actual_map:
                errors.append("DUPLICATE_TARGET_MAPPING:" + target)
            actual_map[target] = {str(x) for x in brain}
            if not actual_map[target].issubset(leaf_set):
                errors.append("MAPPING_USES_UNKNOWN_BRAIN_LEAF:" + target)

    if set(actual_map) != BEHAVIOR:
        errors.append("MAPPED_TARGET_SET_NOT_EXACT_BEHAVIOR_SET")
    for target, required in REQUIRED_MAP.items():
        if actual_map.get(target) != required:
            errors.append("REQUIRED_MAPPING_MISMATCH:" + target)
    if set(actual_map) & PERFORMANCE:
        errors.append("PERFORMANCE_METADATA_TREATED_AS_BEHAVIOR_REQUIREMENT")

    materiality = b.get("materiality_projection")
    machine = (
        materiality.get("machine_contract")
        if isinstance(materiality, Mapping)
        else None
    )
    if not isinstance(machine, Mapping):
        errors.append("MATERIALITY_MACHINE_CONTRACT_MISSING")
    else:
        for key in (
            "target_verdict_relevance_defines_materiality",
            "terminal_outcome_relevance_defines_materiality",
            "ledger_root_owns_inventory_completeness",
        ):
            if machine.get(key) is not True:
                errors.append("MATERIALITY_CONTRACT_FALSE:" + key)

    theorem = b.get("theorem")
    if not isinstance(theorem, Mapping):
        errors.append("THEOREM_INVALID")
    else:
        if theorem.get("target_behavior_semantic_count") != 4:
            errors.append("TARGET_BEHAVIOR_COUNT_NOT_4")
        if theorem.get("mapped_target_behavior_semantic_count") != 4:
            errors.append("MAPPED_BEHAVIOR_COUNT_NOT_4")
        if theorem.get("unmapped_target_behavior_semantic_count") != 0:
            errors.append("UNMAPPED_BEHAVIOR_NOT_ZERO")
        if theorem.get("performance_metadata_count") != 1:
            errors.append("PERFORMANCE_METADATA_COUNT_NOT_1")

    effect = b.get("root_accounting_effect")
    if not isinstance(effect, Mapping):
        errors.append("ROOT_ACCOUNTING_EFFECT_INVALID")
    else:
        if effect.get("closes_if_verified") != ["HONESTY_TARGET_SEMANTIC_BRIDGE"]:
            errors.append("WRONG_ROOT_CLOSURE")
        preserved = set(effect.get("preserves_open") or [])
        if preserved != {
            "HONESTY_UNIVERSAL_EMISSION_MEDIATION_TOTALITY",
            "HONESTY_LEDGER_SEMANTIC_COMPLETENESS",
        }:
            errors.append("OTHER_HONESTY_ROOTS_NOT_PRESERVED")

    accounting = b.get("accounting")
    if not isinstance(accounting, Mapping):
        errors.append("ACCOUNTING_INVALID")
    else:
        for key in (
            "incremental_spend_usd",
            "new_reality_units_consumed",
            "terminal_cases_consumed",
            "acceptance_credit_delta",
            "family_credit_delta",
            "capability_credit_delta",
            "ownership_credit_delta",
        ):
            if accounting.get(key) != 0:
                errors.append("NONZERO_ACCOUNTING:" + key)

    if b.get("execution_authority") is not False:
        errors.append("EXECUTION_AUTHORITY_OVERCLAIM")
    if b.get("promotion_authority") is not False:
        errors.append("PROMOTION_AUTHORITY_OVERCLAIM")
    if b.get("fresh_reality_authority") is not False:
        errors.append("FRESH_REALITY_AUTHORITY_OVERCLAIM")

    ok = not errors
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__FOUR_OF_FOUR_TARGET_BEHAVIOR_SEMANTICS_MAPPED__ONE_PERFORMANCE_MARKER_EXCLUDED__ZERO_CREDIT"
            if ok
            else "FAIL_CLOSED"
        ),
        "pass": ok,
        "errors": sorted(set(errors)),
        "target_behavior_semantic_count": 4 if ok else None,
        "mapped_target_behavior_semantic_count": 4 if ok else None,
        "performance_metadata_count": 1 if ok else None,
        "semantic_bridge_closed_if_independently_verified": ok,
        "honesty_parity_proved": False,
        "universal_mediation_proved": False,
        "ledger_completeness_proved": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


def main() -> int:
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
