"""Live integrated Brain V1.

Runs a compiled real task through the existing verified bound-capability registry,
minimum-cost capability planner, promoted executor, and independent execution
trace verifier. This is a construction runtime, not a benchmark scorer.

V1 intentionally accepts an already-compiled task contract. Raw natural-language
task compilation remains outside this file and is surfaced as a precise failure
instead of guessed.
"""
from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter_ns
from typing import Any, Mapping

from canonical.runtime.capability_planner import PlanningFailure, plan_capabilities
from canonical.runtime.verified_bound_capability_execution_adapter_v1 import execute
from canonical.runtime import goal_compiler
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.raw_goal_archive_acceptance_v1 import verify as verify_raw_archive_acceptance

SCHEMA = "PROJECT_BRAIN_LIVE_INTEGRATED_BRAIN_V1"
ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"


class LiveBrainError(ValueError):
    pass


def _tokens(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list):
        raise LiveBrainError(label + "_MUST_BE_LIST")
    out = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise LiveBrainError(label + "_ITEM_INVALID")
        token = item.strip()
        if token in out:
            raise LiveBrainError(label + "_DUPLICATE:" + token)
        out.append(token)
    if not allow_empty and not out:
        raise LiveBrainError(label + "_EMPTY")
    return out


def load_verified_registry() -> dict[str, Mapping[str, Any]]:
    doc = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if doc.get("schema") != "PROJECT_BRAIN_BOUND_CAPABILITY_REGISTRY_V1":
        raise LiveBrainError("BOUND_CAPABILITY_REGISTRY_SCHEMA_INVALID")
    raw = doc.get("capabilities")
    if not isinstance(raw, Mapping):
        raise LiveBrainError("BOUND_CAPABILITY_REGISTRY_INVALID")
    out: dict[str, Mapping[str, Any]] = {}
    for cid, entry in raw.items():
        if not isinstance(cid, str) or not isinstance(entry, Mapping):
            continue
        if entry.get("status") != "VERIFIED_BOUND_CAPABILITY":
            continue
        if float(entry.get("incremental_spend_usd", 0)) != 0:
            continue
        out[cid] = entry
    if not out:
        raise LiveBrainError("NO_VERIFIED_ZERO_SPEND_CAPABILITIES")
    return out


def compile_capability_graph(
    *,
    initial_facts: list[str],
    target_effects: list[str],
    registry: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    capabilities = []
    for cid, entry in registry.items():
        requires = list(entry.get("requires") or [])
        provides = list(entry.get("provides") or [])
        if not provides:
            continue
        capabilities.append(
            {
                "id": cid,
                "requires": requires,
                "provides": provides,
                "cost": float(entry.get("cost", 1)),
                "action": {"type": "verified_bound_capability"},
                "result_fields": list(entry.get("result_fields") or []),
            }
        )
    return {
        "initial_facts": list(initial_facts),
        "target_effects": list(target_effects),
        "capabilities": capabilities,
        "max_expansions": 100000,
    }


def run(request: Mapping[str, Any]) -> dict[str, Any]:
    started = perf_counter_ns()
    try:
        if not isinstance(request, Mapping):
            raise LiveBrainError("REQUEST_NOT_OBJECT")
        task_id = str(request.get("task_id") or "").strip()
        if not task_id:
            raise LiveBrainError("TASK_ID_REQUIRED")
        initial = _tokens(request.get("initial_facts", []), "INITIAL_FACTS")
        targets = _tokens(request.get("target_effects", []), "TARGET_EFFECTS", allow_empty=False)
        capability_inputs = request.get("capability_inputs", {})
        if not isinstance(capability_inputs, Mapping):
            raise LiveBrainError("CAPABILITY_INPUTS_NOT_OBJECT")

        registry = load_verified_registry()
        allowed = request.get("allowed_capability_ids")
        if allowed is not None:
            allowed_ids = _tokens(allowed, "ALLOWED_CAPABILITY_IDS", allow_empty=False)
            unknown = sorted(set(allowed_ids) - set(registry))
            if unknown:
                raise LiveBrainError("ALLOWED_CAPABILITY_UNKNOWN:" + ",".join(unknown))
            registry = {cid: registry[cid] for cid in allowed_ids}
        problem = compile_capability_graph(
            initial_facts=initial,
            target_effects=targets,
            registry=registry,
        )
        try:
            planned = plan_capabilities(problem)
        except PlanningFailure as exc:
            return {
                "schema": SCHEMA,
                "status": "FAIL__CAPABILITY_OR_TASK_CONTRACT_GAP",
                "pass": False,
                "task_id": task_id,
                "failure_class": "MISSING_CAPABILITY_OR_COMPILED_TASK_CONTRACT",
                "planner_code": exc.code,
                "planner_detail": exc.detail,
                "verified_registry_capability_count": len(registry),
                "elapsed_ns": perf_counter_ns() - started,
                "incremental_spend_usd": 0,
            }

        current = set(initial)
        execution = []
        for cid in planned["plan"]:
            entry = registry[cid]
            inputs = capability_inputs.get(cid)
            if not isinstance(inputs, Mapping):
                return {
                    "schema": SCHEMA,
                    "status": "FAIL__MISSING_CAPABILITY_INPUTS",
                    "pass": False,
                    "task_id": task_id,
                    "failure_class": "TASK_CONTRACT_COMPILATION_GAP",
                    "capability_id": cid,
                    "selected_plan": list(planned["plan"]),
                    "verified_registry_capability_count": len(registry),
                    "elapsed_ns": perf_counter_ns() - started,
                    "incremental_spend_usd": 0,
                }
            out = execute(
                cid,
                inputs=dict(inputs),
                instance_id=cid,
                requires=list(entry.get("requires") or []),
                provides=list(entry.get("provides") or []),
                result_fields=list(entry.get("result_fields") or []),
            )
            execution.append(
                {
                    "capability_id": cid,
                    "pass": out.get("pass") is True,
                    "status": out.get("status"),
                    "composition_capsule_head_hash": out.get("composition_capsule_head_hash"),
                    "result": out.get("result"),
                    "errors": out.get("errors"),
                }
            )
            if out.get("pass") is not True:
                return {
                    "schema": SCHEMA,
                    "status": "FAIL__VERIFIED_CAPABILITY_EXECUTION",
                    "pass": False,
                    "task_id": task_id,
                    "failure_class": "EXECUTION_OR_BOUND_CONTRACT_FAILURE",
                    "capability_id": cid,
                    "selected_plan": list(planned["plan"]),
                    "execution": execution,
                    "elapsed_ns": perf_counter_ns() - started,
                    "incremental_spend_usd": 0,
                }
            current.update(entry.get("provides") or [])

        missing = sorted(set(targets) - current)
        if missing:
            raise LiveBrainError("POST_EXECUTION_TARGETS_MISSING:" + ",".join(missing))

        return {
            "schema": SCHEMA,
            "status": "PASS__REAL_TASK_PLANNED_EXECUTED_AND_REVERIFIED",
            "pass": True,
            "task_id": task_id,
            "selected_plan": list(planned["plan"]),
            "planner_total_cost": planned["total_cost"],
            "planner_expanded_states": planned["expanded_states"],
            "verified_registry_capability_count": len(registry),
            "execution": execution,
            "verified_target_effects": sorted(targets),
            "elapsed_ns": perf_counter_ns() - started,
            "incremental_spend_usd": 0,
            "benchmark_specific": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "failure_class": "INTEGRATION_RUNTIME_ERROR",
            "reason": type(exc).__name__ + ":" + str(exc),
            "elapsed_ns": perf_counter_ns() - started,
            "incremental_spend_usd": 0,
        }



def run_raw_goal(request: Mapping[str, Any]) -> dict[str, Any]:
    """Compile one raw plain-language goal into the live verified runtime.

    Raw text is preserved losslessly as acceptance obligations. The deterministic
    goal compiler may choose routing/execution, but routing never becomes success
    authority. V1 supports the existing single-capability compiled shape; richer
    controller/composition shapes fail closed instead of being guessed.
    """
    started = perf_counter_ns()
    try:
        if not isinstance(request, Mapping):
            raise LiveBrainError("REQUEST_NOT_OBJECT")
        task_id = str(request.get("task_id") or "").strip()
        goal = str(request.get("goal") or "").strip()
        if not task_id:
            raise LiveBrainError("TASK_ID_REQUIRED")
        if not goal:
            raise LiveBrainError("RAW_GOAL_REQUIRED")

        registry = load_verified_registry()
        admissible = goal_compiler._platform_admissible_registry(dict(registry))
        try:
            compiled = goal_compiler.compile_goal(goal, admissible, ROOT)
        except goal_compiler.GoalCompilationFailure as exc:
            return {
                "schema": SCHEMA,
                "status": "FAIL__RAW_GOAL_COMPILATION_GAP",
                "pass": False,
                "task_id": task_id,
                "failure_class": "RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP",
                "compiler_code": exc.code,
                "compiler_detail": exc.detail,
                "elapsed_ns": perf_counter_ns() - started,
                "incremental_spend_usd": 0,
            }

        if compiled.get("controller_actions") is not None:
            return {
                "schema": SCHEMA,
                "status": "FAIL__COMPILED_CONTROL_PLAN_NOT_BOUND",
                "pass": False,
                "task_id": task_id,
                "failure_class": "LIVE_RUNTIME_COMPOSITION_BINDING_GAP",
                "compiler_mode": compiled.get("compiler_mode"),
                "elapsed_ns": perf_counter_ns() - started,
                "incremental_spend_usd": 0,
            }

        selected = str(compiled.get("selected_capability") or "").strip()
        inputs = compiled.get("inputs")
        targets = compiled.get("target_effects")
        initial = compiled.get("initial_facts")
        if (
            not selected
            or selected not in admissible
            or not isinstance(inputs, Mapping)
            or not isinstance(targets, list)
            or not targets
            or not isinstance(initial, list)
        ):
            return {
                "schema": SCHEMA,
                "status": "FAIL__COMPILED_SHAPE_NOT_EXECUTABLE",
                "pass": False,
                "task_id": task_id,
                "failure_class": "RAW_GOAL_COMPILED_SHAPE_GAP",
                "compiler_mode": compiled.get("compiler_mode"),
                "elapsed_ns": perf_counter_ns() - started,
                "incremental_spend_usd": 0,
            }

        raw_contract = compile_contract(
            goal,
            source_id="user",
            routing_target_effects=targets,
        )
        if raw_contract.get("pass") is not True:
            return {
                "schema": SCHEMA,
                "status": "FAIL__LOSSLESS_RAW_TASK_CONTRACT",
                "pass": False,
                "task_id": task_id,
                "failure_class": "RAW_TASK_OBLIGATION_ENVELOPE_FAILURE",
                "errors": raw_contract.get("errors"),
                "elapsed_ns": perf_counter_ns() - started,
                "incremental_spend_usd": 0,
            }

        out = run({
            "task_id": task_id,
            "initial_facts": list(initial),
            "target_effects": list(targets),
            "capability_inputs": {selected: dict(inputs)},
            "allowed_capability_ids": [selected],
        })
        result = dict(out)
        result["raw_goal"] = goal
        result["raw_goal_sha256"] = raw_contract["task_sha256"]
        result["raw_task_contract_sha256"] = raw_contract["task_contract_sha256"]
        result["raw_acceptance_obligation_count"] = len(
            raw_contract["acceptance_contract"]["obligations"]
        )
        result["raw_source_coverage_complete"] = raw_contract[
            "nonwhitespace_source_coverage_complete"
        ]
        result["compiled_capability_id"] = selected
        result["compiler_mode"] = compiled.get("compiler_mode")
        # Execution success alone is not raw-goal acceptance. For the one
        # explicit archive semantics currently understood, independently inspect
        # the artifact and bind all exact source obligations to the receipt.
        acceptance = None
        rows = result.get("execution")
        if (
            result.get("pass") is True
            and selected == "archive.tar_gz.create_from_manifest"
            and isinstance(rows, list)
            and len(rows) == 1
        ):
            acceptance = verify_raw_archive_acceptance(
                goal=goal,
                capability_id=selected,
                inputs=inputs,
                execution=rows[0],
                raw_contract=raw_contract,
                root=ROOT,
            )
        result["raw_goal_acceptance"] = acceptance
        result["accepted_raw_obligation_ids"] = (
            list(acceptance.get("accepted_obligation_ids") or [])
            if isinstance(acceptance, Mapping) else []
        )
        result["routing_success_authority"] = False
        result["semantic_acceptance_complete"] = (
            isinstance(acceptance, Mapping)
            and acceptance.get("semantic_acceptance_complete") is True
            and len(result["accepted_raw_obligation_ids"])
                == result["raw_acceptance_obligation_count"]
        )
        result["elapsed_ns"] = perf_counter_ns() - started
        if result.get("pass") is True:
            result["status"] = (
                "PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED"
                if result["semantic_acceptance_complete"] else
                "PASS__RAW_GOAL_COMPILED_PLANNED_EXECUTED_REVERIFIED__"
                "RAW_ACCEPTANCE_RECEIPTS_STILL_REQUIRED"
            )
        return result
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "failure_class": "RAW_GOAL_INTEGRATION_RUNTIME_ERROR",
            "reason": type(exc).__name__ + ":" + str(exc),
            "elapsed_ns": perf_counter_ns() - started,
            "incremental_spend_usd": 0,
        }
