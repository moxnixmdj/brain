#!/usr/bin/env python3
"""Fail-closed audit of the actually executed terminal P1 instrumentation.

This audit does not alter or erase the immutable terminal-wave receipt. It asks a
narrower question: did the executor used for TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001
actually evaluate every load-bearing semantic required by its frozen P1 binding?

No capability/family credit is granted here.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
P1 = "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
P1_BINDING = "canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"
PARENT_BINDING = "canonical/governance/TERMINAL_PARENT_PORTFOLIO_RUNNER_BINDING_V1.json"
PARENT_RUNNER = "canonical/runtime/terminal_parent_portfolio_runner_v1.py"
SUITE = "canonical/runtime/contract_native_proof_suites.py"
SCHEMA = "PROJECT_BRAIN_P1_TERMINAL_EXECUTION_SCOPE_AUDIT_V1"

EXPECTED_SUITE_BLOB = "0210790c7dd705ef328e1b55d529a30c5c6c3337"
REQUIRED_UNEVALUATED = {
    "FAILURE_MECHANISM_CLASSIFICATION_SUPPORTED_BY_VISIBLE_RECEIPTS",
    "NONIDENTIFIABLE_OR_CAUSALLY_EQUIVALENT_CASE_DOES_NOT_FORCE_UNIQUE_CAUSE",
    "AUTHORITY_SCOPE_TOOL_STATE_PROVENANCE_AND_DEPENDENCY_FAILURE_CLASSES_ARE_LOAD_BEARING_WHEN_PRESENT",
    "MULTISTEP_OR_DELAYED_CAUSAL_INTERACTIONS_ARE_NOT_REDUCED_TO_FIRST_VISIBLE_SYMPTOM",
}


def _load(rel: str) -> dict[str, Any]:
    value = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(rel + ":NOT_OBJECT")
    return value


def _blob(rel: str) -> str:
    data = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _function(tree: ast.AST, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise ValueError("FUNCTION_NOT_FOUND:" + name)


def _dict_literal_keys(node: ast.AST) -> set[str] | None:
    if not isinstance(node, ast.Dict):
        return None
    out: set[str] = set()
    for key in node.keys:
        if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
            return None
        out.add(key.value)
    return out


def _outer_return_dict(fn: ast.FunctionDef) -> ast.Dict:
    returns = [x for x in ast.walk(fn) if isinstance(x, ast.Return) and isinstance(x.value, ast.Dict)]
    if len(returns) != 1:
        raise ValueError("TRAJECTORY_RETURN_SHAPE_NOT_UNIQUE")
    return returns[0].value


def _nested_literal(outer: ast.Dict, key_name: str) -> ast.AST:
    for key, value in zip(outer.keys, outer.values):
        if isinstance(key, ast.Constant) and key.value == key_name:
            return value
    raise ValueError("RETURN_KEY_NOT_FOUND:" + key_name)


def _append_dict_keys(fn: ast.FunctionDef, list_name: str) -> set[str] | None:
    hits: list[set[str]] = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call) or len(node.args) != 1:
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "append"
            and isinstance(func.value, ast.Name)
            and func.value.id == list_name
        ):
            keys = _dict_literal_keys(node.args[0])
            if keys is not None:
                hits.append(keys)
    if len(hits) != 1:
        return None
    return hits[0]


def _candidate_get_keys(fn: ast.FunctionDef) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "get"
            and isinstance(func.value, ast.Name)
            and func.value.id == "candidate"
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            out.add(node.args[0].value)
    return out


def evaluate(root: Path = ROOT) -> dict[str, Any]:
    errors: list[str] = []
    p1 = _load(P1_BINDING)
    parent = _load(PARENT_BINDING)

    required_checks = set(((p1.get("evaluator") or {}).get("required_checks") or []))
    if not REQUIRED_UNEVALUATED <= required_checks:
        errors.append("FROZEN_P1_REQUIRED_CHECK_SET_DRIFT")

    schedule = (parent.get("schedules") or {}).get(P1) or {}
    if schedule.get("mode") != "CONTRACT_NATIVE":
        errors.append("P1_EXECUTED_SCHEDULE_NOT_CONTRACT_NATIVE")
    bound_suite_blob = (parent.get("exact_brain_blobs") or {}).get(SUITE)
    actual_suite_blob = _blob(SUITE)
    if bound_suite_blob != EXPECTED_SUITE_BLOB or actual_suite_blob != EXPECTED_SUITE_BLOB:
        errors.append("EXECUTED_CONTRACT_NATIVE_SUITE_BLOB_DRIFT")

    runner_source = (root / PARENT_RUNNER).read_text(encoding="utf-8")
    if "if behavior_id in {STRUCTURED, P1, P2, P3}:" not in runner_source:
        errors.append("P1_PARENT_RUNNER_DISPATCH_NOT_PROVEN")
    if "return _run_contract_native(behavior_id, portfolio, commitment, beacon, count)" not in runner_source:
        errors.append("P1_CONTRACT_NATIVE_CALL_NOT_PROVEN")

    suite_source = (root / SUITE).read_text(encoding="utf-8")
    tree = ast.parse(suite_source)
    case_fn = _function(tree, "_trajectory_case")
    score_fn = _function(tree, "_score_trajectory")
    outer = _outer_return_dict(case_fn)
    task_keys = _dict_literal_keys(_nested_literal(outer, "task"))
    oracle_keys = _dict_literal_keys(_nested_literal(outer, "_oracle"))
    step_keys = _append_dict_keys(case_fn, "steps")
    candidate_scored_keys = _candidate_get_keys(score_fn)

    expected_task_keys = {"trajectory", "repair_candidates"}
    expected_oracle_keys = {"cause_step", "repair_id"}
    expected_step_keys = {"step", "action", "state", "invariant_pass", "terminal_symptom"}
    expected_candidate_scored = {"cause_step", "repair_id", "evidence_steps"}

    if task_keys != expected_task_keys:
        errors.append("EXECUTED_P1_TASK_SCHEMA_CHANGED")
    if oracle_keys != expected_oracle_keys:
        errors.append("EXECUTED_P1_ORACLE_SCHEMA_CHANGED")
    if step_keys != expected_step_keys:
        errors.append("EXECUTED_P1_STEP_SCHEMA_CHANGED")
    if candidate_scored_keys != expected_candidate_scored:
        errors.append("EXECUTED_P1_SCORER_OUTPUT_KEYS_CHANGED")

    missing_required_semantics = sorted(REQUIRED_UNEVALUATED)
    mismatch = (
        not errors
        and task_keys == expected_task_keys
        and oracle_keys == expected_oracle_keys
        and step_keys == expected_step_keys
        and candidate_scored_keys == expected_candidate_scored
    )

    return {
        "schema": SCHEMA,
        "status": (
            "FAIL_CLOSED__EXECUTED_P1_TERMINAL_INSTRUMENTATION_NARROWER_THAN_FROZEN_P1_BINDING"
            if mismatch and not errors
            else "FAIL_CLOSED__AUDIT_INPUT_DRIFT"
        ),
        "audit_valid": not errors,
        "scope_mismatch_proved": mismatch and not errors,
        "errors": sorted(set(errors)),
        "behavior_id": P1,
        "exact_blobs": {
            P1_BINDING: _blob(P1_BINDING),
            PARENT_BINDING: _blob(PARENT_BINDING),
            PARENT_RUNNER: _blob(PARENT_RUNNER),
            SUITE: actual_suite_blob,
        },
        "executed_route": {
            "schedule_mode": schedule.get("mode"),
            "terminal_case_count_per_bound_parent": schedule.get("case_count"),
            "task_literal_keys": sorted(task_keys or []),
            "oracle_literal_keys": sorted(oracle_keys or []),
            "step_literal_keys": sorted(step_keys or []),
            "candidate_output_keys_scored": sorted(candidate_scored_keys),
        },
        "frozen_required_checks_not_evaluated_by_executed_scorer": missing_required_semantics,
        "preserved": [
            "IMMUTABLE_TERMINAL_V3_EXECUTION_RECEIPT",
            "EXECUTED_LINEAR_SINGLE_CAUSE_P1_ENVELOPE_RESULT",
            "NO_REPLAY_NO_CASE_REPLACEMENT_NO_TUNING_FACTS",
            "TYPED_V4_PREWAVE_PREFLIGHT_FOR_ITS_DECLARED_PREFLIGHT_ROLE",
        ],
        "quarantined": [
            "P1_WHOLE_FROZEN_CONTRACT_PASS_FROM_TERMINAL_V3",
            "P1_TO_RECOVERY_ACCEPTANCE_SEMANTIC_TRANSPORT",
            "P1_AS_FULL_SCOPE_COMPOSITION_COMPONENT_PROOF",
            "POSTWAVE_12_OF_12_CLAIM_UNTIL_P1_IS_SEPARATELY_DISCHARGED_OR_REDUCED_OPEN",
        ],
        "rule": (
            "RAW_EXECUTION_EVIDENCE_IS_PRESERVED__CLAIM_SCOPE_MAY_NOT_EXCEED_THE_ACTUALLY_EXECUTED_SCORER__"
            "PREFLIGHT_COVERAGE_FROM_TYPED_V4_DOES_NOT_RETROACTIVELY_ADD_UNSCORED_TERMINAL_SEMANTICS"
        ),
        "fresh_terminal_evidence_consumed": 0,
        "terminal_results_replayed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["audit_valid"] and out["scope_mismatch_proved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
