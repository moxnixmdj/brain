#!/usr/bin/env python3
"""Deterministic model-free typed-evidence -> terminal-decision adapter.

The adapter interprets no natural language. It accepts a closed JSON contract,
compiles weighted facts/rules to ProbLog, evaluates support and contradiction,
applies explicit hard constraints and a fixed decision policy, and emits an
auditable receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any

PROBLOG_COMMIT = "1c0df586a1cb4e276b38bbf222d0578f3db58bde"\nPROBLOG_VERSION = "2.3.0"\nPROBLOG_WHEEL_SHA256 = "8d18beae480bce9f54037dfa9cf8c058da874524c118d8ffae96fd210b68e71e"
SCHEMA = "PROJECT_BRAIN_TYPED_EVIDENCE_DECISION_TASK_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_TYPED_EVIDENCE_DECISION_RESULT_V1"
ALLOWED_TERMINALS = {"ACCEPT", "REJECT", "INSUFFICIENT_EVIDENCE"}
SAFE_ID = re.compile(r"^[a-z][a-z0-9_]*$")


class ContractError(ValueError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def require_id(value: Any, field: str) -> str:
    value = str(value or "")
    if not SAFE_ID.fullmatch(value):
        raise ContractError(f"{field}:INVALID_ID")
    return value


def require_probability(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{field}:NOT_NUMBER")
    value = float(value)
    if not 0.0 <= value <= 1.0:
        raise ContractError(f"{field}:OUT_OF_RANGE")
    return value


def require_provenance(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ContractError(f"{field}:EMPTY")
    out = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ContractError(f"{field}:INVALID_ITEM")
        out.append(item.strip())
    return out


def validate_task(task: dict[str, Any]) -> None:
    if task.get("schema") != SCHEMA:
        raise ContractError("SCHEMA_INVALID")
    require_id(task.get("task_id"), "task_id")
    require_id(task.get("target_claim"), "target_claim")

    evidence = task.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise ContractError("EVIDENCE_EMPTY")
    seen = set()
    for i, item in enumerate(evidence):
        if not isinstance(item, dict):
            raise ContractError(f"evidence[{i}]:NOT_OBJECT")
        eid = require_id(item.get("id"), f"evidence[{i}].id")
        if eid in seen:
            raise ContractError(f"evidence[{i}]:DUPLICATE_ID")
        seen.add(eid)
        require_probability(item.get("probability"), f"evidence[{i}].probability")
        require_provenance(item.get("provenance"), f"evidence[{i}].provenance")

    def validate_rules(key: str) -> None:
        rules = task.get(key)
        if not isinstance(rules, list) or not rules:
            raise ContractError(f"{key}:EMPTY")
        rule_ids = set()
        for i, rule in enumerate(rules):
            if not isinstance(rule, dict):
                raise ContractError(f"{key}[{i}]:NOT_OBJECT")
            rid = require_id(rule.get("id"), f"{key}[{i}].id")
            if rid in rule_ids:
                raise ContractError(f"{key}[{i}]:DUPLICATE_ID")
            rule_ids.add(rid)
            all_of = rule.get("all_of")
            if not isinstance(all_of, list) or not all_of:
                raise ContractError(f"{key}[{i}].all_of:EMPTY")
            for eid in all_of:
                if eid not in seen:
                    raise ContractError(f"{key}[{i}]:UNKNOWN_EVIDENCE:{eid}")

    validate_rules("support_rules")
    validate_rules("contradiction_rules")

    constraints = task.get("hard_constraints")
    if not isinstance(constraints, list):
        raise ContractError("HARD_CONSTRAINTS_NOT_LIST")
    constraint_ids = set()
    for i, item in enumerate(constraints):
        if not isinstance(item, dict):
            raise ContractError(f"hard_constraints[{i}]:NOT_OBJECT")
        cid = require_id(item.get("id"), f"hard_constraints[{i}].id")
        if cid in constraint_ids:
            raise ContractError(f"hard_constraints[{i}]:DUPLICATE_ID")
        constraint_ids.add(cid)
        if not isinstance(item.get("satisfied"), bool):
            raise ContractError(f"hard_constraints[{i}].satisfied:NOT_BOOL")
        outcome = item.get("failure_outcome")
        if outcome not in {"REJECT", "INSUFFICIENT_EVIDENCE"}:
            raise ContractError(f"hard_constraints[{i}].failure_outcome:INVALID")
        require_provenance(
            item.get("provenance"), f"hard_constraints[{i}].provenance"
        )

    policy = task.get("policy")
    if not isinstance(policy, dict):
        raise ContractError("POLICY_NOT_OBJECT")
    for key in (
        "accept_support_min",
        "accept_contradiction_max",
        "reject_contradiction_min",
        "reject_support_max",
        "minimum_margin",
    ):
        require_probability(policy.get(key), f"policy.{key}")


def compile_program(task: dict[str, Any]) -> tuple[str, dict[str, dict[str, Any]]]:
    evidence_index: dict[str, dict[str, Any]] = {}
    lines = [
        "% Generated deterministically by Project Brain typed evidence adapter.",
        f"% ProbLog source commit: {PROBLOG_COMMIT}",
        "0.0::support_seed.",
        "0.0::contradiction_seed.",
        "support_target :- support_seed.",
        "contradiction_target :- contradiction_seed.",
    ]
    for item in task["evidence"]:
        eid = item["id"]
        evidence_index[eid] = item
        p = float(item["probability"])
        lines.append(f"{p:.12g}::ev_{eid}.")

    for rule in task["support_rules"]:
        body = ", ".join(f"ev_{eid}" for eid in rule["all_of"])
        lines.append(f"support_target :- {body}.")
    for rule in task["contradiction_rules"]:
        body = ", ".join(f"ev_{eid}" for eid in rule["all_of"])
        lines.append(f"contradiction_target :- {body}.")

    lines.extend(["query(support_target).", "query(contradiction_target)."])
    return "\n".join(lines) + "\n", evidence_index


def evaluate_program(program: str) -> dict[str, float]:
    try:
        from problog import get_evaluatable
        from problog.program import PrologString
    except Exception as exc:
        raise ContractError(
            "PROBLOG_IMPORT_FAILED:" + type(exc).__name__ + ":" + str(exc)
        ) from exc
    try:
        raw = get_evaluatable().create_from(PrologString(program)).evaluate()
    except Exception as exc:
        raise ContractError(
            "PROBLOG_EVALUATION_FAILED:" + type(exc).__name__ + ":" + str(exc)
        ) from exc
    result = {str(k): float(v) for k, v in raw.items()}
    for name in ("support_target", "contradiction_target"):
        if name not in result:
            raise ContractError("PROBLOG_QUERY_MISSING:" + name)
        if not 0.0 <= result[name] <= 1.0:
            raise ContractError("PROBLOG_QUERY_OUT_OF_RANGE:" + name)
    return result


def terminal_decision(
    task: dict[str, Any], support: float, contradiction: float
) -> tuple[str, str, list[dict[str, Any]]]:
    failed = [x for x in task["hard_constraints"] if not x["satisfied"]]
    if failed:
        # REJECT is stronger than INSUFFICIENT_EVIDENCE when both exist.
        outcomes = {x["failure_outcome"] for x in failed}
        terminal = "REJECT" if "REJECT" in outcomes else "INSUFFICIENT_EVIDENCE"
        return terminal, "HARD_CONSTRAINT_FAILURE", failed

    p = task["policy"]
    margin = support - contradiction
    if (
        support >= float(p["accept_support_min"])
        and contradiction <= float(p["accept_contradiction_max"])
        and margin >= float(p["minimum_margin"])
    ):
        return "ACCEPT", "PROBABILISTIC_POLICY_ACCEPT", []
    if (
        contradiction >= float(p["reject_contradiction_min"])
        and support <= float(p["reject_support_max"])
        and -margin >= float(p["minimum_margin"])
    ):
        return "REJECT", "PROBABILISTIC_POLICY_REJECT", []
    return "INSUFFICIENT_EVIDENCE", "UNRESOLVED_SUPPORT_CONTRADICTION", []


def run(task: dict[str, Any]) -> dict[str, Any]:
    validate_task(task)
    program, evidence_index = compile_program(task)
    probabilities = evaluate_program(program)
    support = probabilities["support_target"]
    contradiction = probabilities["contradiction_target"]
    terminal, reason, failed = terminal_decision(task, support, contradiction)
    if terminal not in ALLOWED_TERMINALS:
        raise ContractError("TERMINAL_INTERNAL_INVALID")

    trace = {
        "task_id": task["task_id"],
        "target_claim": task["target_claim"],
        "evidence": [
            {
                "id": x["id"],
                "probability": float(x["probability"]),
                "provenance": list(x["provenance"]),
            }
            for x in task["evidence"]
        ],
        "support_rules": task["support_rules"],
        "contradiction_rules": task["contradiction_rules"],
        "hard_constraints": task["hard_constraints"],
        "policy": task["policy"],
        "probabilities": {
            "support": support,
            "contradiction": contradiction,
            "margin_support_minus_contradiction": support - contradiction,
        },
        "failed_hard_constraints": failed,
        "decision_reason": reason,
    }
    return {
        "schema": RESULT_SCHEMA,
        "status": "COMPLETE",
        "engine": "ProbLog",
        "problog_commit": PROBLOG_COMMIT,\n        "problog_version": PROBLOG_VERSION,\n        "problog_wheel_sha256": PROBLOG_WHEEL_SHA256,
        "model_dependency_count": 0,
        "task_id": task["task_id"],
        "target_claim": task["target_claim"],
        "terminal_decision": terminal,
        "support_probability": support,
        "contradiction_probability": contradiction,
        "unresolved_conflict": support >= 0.5 and contradiction >= 0.5,
        "input_sha256": sha256_json(task),
        "generated_program_sha256": hashlib.sha256(program.encode("utf-8")).hexdigest(),
        "generated_program": program,
        "trace": trace,
        "trace_sha256": sha256_json(trace),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("task_json")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    path = pathlib.Path(args.task_json)
    task = json.loads(path.read_text(encoding="utf-8"))
    result = run(task)
    out = pathlib.Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print("FAIL_CLOSED:" + str(exc), file=sys.stderr)
        raise SystemExit(2)
