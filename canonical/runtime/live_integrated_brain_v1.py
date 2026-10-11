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
from canonical.runtime import astra_runtime, goal_compiler
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.raw_goal_archive_acceptance_v1 import verify as verify_raw_archive_acceptance
from canonical.runtime.runtime_cognition_credit_guard_v1 import assert_credit_path_cognition_governance

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
    assert_credit_path_cognition_governance(ROOT)
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

        controller_actions = []
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
            controller_actions.append({
                "type": "invoke_verified_bound_capability_adapter",
                "args": {
                    "capability_id": cid,
                    "inputs": dict(inputs),
                    "instance_id": cid,
                    "requires": list(entry.get("requires") or []),
                    "provides": list(entry.get("provides") or []),
                    "result_fields": list(entry.get("result_fields") or []),
                },
                "expect": {"type": "field_equals", "field": "pass", "value": True},
            })
        controller_actions.append({
            "type": "finish",
            "args": {"summary": "COMPILED_TASK_COMPLETE"},
        })

        try:
            controller = astra_runtime.run_goal(
                {
                    "id": "live-compiled-task-controller",
                    "controller_actions": controller_actions,
                    "max_controller_actions": 64,
                },
                {
                    "mission_id": task_id,
                    "goal": "execute compiled verified capability task",
                },
            )
        except Exception as exc:
            return {
                "schema": SCHEMA,
                "status": "FAIL__VERIFIED_CAPABILITY_EXECUTION",
                "pass": False,
                "task_id": task_id,
                "failure_class": "EXECUTION_OR_BOUND_CONTRACT_FAILURE",
                "selected_plan": list(planned["plan"]),
                "reason": type(exc).__name__ + ":" + str(exc),
                "elapsed_ns": perf_counter_ns() - started,
                "incremental_spend_usd": 0,
            }

        trace = controller.get("trace") if isinstance(controller, Mapping) else None
        if (
            not isinstance(trace, list)
            or len(trace) != len(planned["plan"]) + 1
            or controller.get("returncode") != 0
            or controller.get("controller_mode") != "MODEL_INDEPENDENT_ACTION_PLAN"
            or controller.get("cognition_dependency_class") != "MODEL_INDEPENDENT"
            or controller.get("model_dependency_count") != 0
        ):
            return {
                "schema": SCHEMA,
                "status": "FAIL__VERIFIED_CAPABILITY_EXECUTION",
                "pass": False,
                "task_id": task_id,
                "failure_class": "EXECUTION_OR_BOUND_CONTRACT_FAILURE",
                "selected_plan": list(planned["plan"]),
                "controller_execution": controller,
                "elapsed_ns": perf_counter_ns() - started,
                "incremental_spend_usd": 0,
            }

        current = set(initial)
        execution = []
        for index, cid in enumerate(planned["plan"]):
            row = trace[index]
            out = row.get("result") if isinstance(row, Mapping) else None
            if not isinstance(out, Mapping):
                raise LiveBrainError("CONTROLLER_PROMOTED_CAPABILITY_RESULT_MISSING:" + cid)
            execution.append({
                "capability_id": cid,
                "pass": out.get("pass") is True,
                "status": out.get("status"),
                "composition_capsule_head_hash": out.get("composition_capsule_head_hash"),
                "result": out.get("result"),
                "errors": out.get("errors"),
            })
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
                    "controller_execution": dict(controller),
                    "elapsed_ns": perf_counter_ns() - started,
                    "incremental_spend_usd": 0,
                }
            current.update(registry[cid].get("provides") or [])

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
            "controller_execution": dict(controller),
            "controller_checkpoint": controller.get("controller_checkpoint"),
            "cognition_dependency_class": controller.get("cognition_dependency_class"),
            "model_dependency_count": controller.get("model_dependency_count"),
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
    assert_credit_path_cognition_governance(ROOT)
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

        controller_actions = compiled.get("controller_actions")
        routing_targets = list(compiled.get("target_effects") or [])
        if not routing_targets:
            for part in compiled.get("compiled_parts") or []:
                if isinstance(part, Mapping):
                    for effect in part.get("target_effects") or []:
                        if isinstance(effect, str) and effect and effect not in routing_targets:
                            routing_targets.append(effect)

        raw_contract = compile_contract(
            goal,
            source_id="user",
            routing_target_effects=routing_targets,
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

        if controller_actions is not None:
            if (
                not isinstance(controller_actions, list)
                or not controller_actions
                or len(controller_actions) > 64
                or any(not isinstance(action, Mapping) for action in controller_actions)
            ):
                return {
                    "schema": SCHEMA,
                    "status": "FAIL__COMPILED_CONTROL_PLAN_INVALID",
                    "pass": False,
                    "task_id": task_id,
                    "failure_class": "LIVE_RUNTIME_COMPOSITION_CONTRACT_INVALID",
                    "compiler_mode": compiled.get("compiler_mode"),
                    "elapsed_ns": perf_counter_ns() - started,
                    "incremental_spend_usd": 0,
                }
            try:
                controller = astra_runtime.run_goal(
                    {
                        "id": "live-raw-goal-controller",
                        "controller_actions": [dict(action) for action in controller_actions],
                        "max_controller_actions": 64,
                    },
                    {
                        "mission_id": task_id,
                        "goal": goal,
                    },
                )
            except Exception as exc:
                return {
                    "schema": SCHEMA,
                    "status": "FAIL__LIVE_CONTROLLER_EXECUTION",
                    "pass": False,
                    "task_id": task_id,
                    "failure_class": "LIVE_CONTROLLER_EXECUTION_OR_VERIFICATION_FAILURE",
                    "compiler_mode": compiled.get("compiler_mode"),
                    "reason": type(exc).__name__ + ":" + str(exc),
                    "elapsed_ns": perf_counter_ns() - started,
                    "incremental_spend_usd": 0,
                }
            passed = (
                isinstance(controller, Mapping)
                and controller.get("returncode") == 0
                and controller.get("controller_mode") == "MODEL_INDEPENDENT_ACTION_PLAN"
                and controller.get("cognition_dependency_class") == "MODEL_INDEPENDENT"
                and controller.get("model_dependency_count") == 0
                and isinstance(controller.get("final_summary"), str)
                and bool(controller.get("final_summary").strip())
            )
            return {
                "schema": SCHEMA,
                "status": (
                    "PASS__RAW_GOAL_COMPILED_CONTROLLER_EXECUTED_VERIFIED_AND_CHECKPOINTED__"
                    "RAW_ACCEPTANCE_RECEIPTS_STILL_REQUIRED"
                    if passed else "FAIL__LIVE_CONTROLLER_RESULT_INVALID"
                ),
                "pass": passed,
                "task_id": task_id,
                "raw_goal": goal,
                "raw_goal_sha256": raw_contract["task_sha256"],
                "raw_task_contract_sha256": raw_contract["task_contract_sha256"],
                "raw_acceptance_obligation_count": len(
                    raw_contract["acceptance_contract"]["obligations"]
                ),
                "raw_source_coverage_complete": raw_contract[
                    "nonwhitespace_source_coverage_complete"
                ],
                "compiler_mode": compiled.get("compiler_mode"),
                "compiled_part_count": len(compiled.get("compiled_parts") or []),
                "controller_action_count": len(controller_actions),
                "controller_execution": dict(controller) if isinstance(controller, Mapping) else controller,
                "controller_checkpoint": (
                    controller.get("controller_checkpoint")
                    if isinstance(controller, Mapping) else None
                ),
                "cognition_dependency_class": (
                    controller.get("cognition_dependency_class")
                    if isinstance(controller, Mapping) else None
                ),
                "model_dependency_count": (
                    controller.get("model_dependency_count")
                    if isinstance(controller, Mapping) else None
                ),
                "routing_success_authority": False,
                "semantic_acceptance_complete": False,
                "accepted_raw_obligation_ids": [],
                "elapsed_ns": perf_counter_ns() - started,
                "incremental_spend_usd": 0,
                "benchmark_specific": False,
                "terminal_credit_delta": 0,
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

        entry = admissible[selected]
        action = goal_compiler._render_template(entry["action_template"], dict(inputs))
        controller_actions = [
            action,
            {"type": "finish", "args": {"summary": "RAW_GOAL_COMPLETE"}},
        ]
        try:
            controller = astra_runtime.run_goal(
                {
                    "id": "live-raw-goal-controller",
                    "controller_actions": controller_actions,
                    "max_controller_actions": 64,
                },
                {
                    "mission_id": task_id,
                    "goal": goal,
                },
            )
        except Exception as exc:
            return {
                "schema": SCHEMA,
                "status": "FAIL__LIVE_CONTROLLER_EXECUTION",
                "pass": False,
                "task_id": task_id,
                "failure_class": "LIVE_CONTROLLER_EXECUTION_OR_VERIFICATION_FAILURE",
                "compiled_capability_id": selected,
                "compiler_mode": compiled.get("compiler_mode"),
                "reason": type(exc).__name__ + ":" + str(exc),
                "elapsed_ns": perf_counter_ns() - started,
                "incremental_spend_usd": 0,
            }

        trace = controller.get("trace") if isinstance(controller, Mapping) else None
        first_trace = trace[0] if isinstance(trace, list) and trace else None
        first_result = (
            first_trace.get("result")
            if isinstance(first_trace, Mapping)
            and isinstance(first_trace.get("result"), Mapping)
            else None
        )
        checkpoint = (
            controller.get("controller_checkpoint")
            if isinstance(controller, Mapping)
            and isinstance(controller.get("controller_checkpoint"), Mapping)
            else {}
        )
        passed = (
            isinstance(controller, Mapping)
            and controller.get("returncode") == 0
            and controller.get("controller_mode") == "MODEL_INDEPENDENT_ACTION_PLAN"
            and controller.get("cognition_dependency_class") == "MODEL_INDEPENDENT"
            and controller.get("model_dependency_count") == 0
            and isinstance(controller.get("final_summary"), str)
            and bool(controller.get("final_summary").strip())
            and isinstance(first_result, Mapping)
        )
        execution_row = {
            "capability_id": selected,
            "pass": passed,
            "status": (
                "PASS__MODEL_INDEPENDENT_CONTROLLER_ACTION"
                if passed else "FAIL__MODEL_INDEPENDENT_CONTROLLER_ACTION"
            ),
            "result": dict(first_result) if isinstance(first_result, Mapping) else None,
            "execution_proof_type": "MODEL_INDEPENDENT_CONTROLLER_TRACE_V1",
            "controller_plan_sha256": checkpoint.get("plan_sha256"),
            "controller_trace": list(trace) if isinstance(trace, list) else [],
        }
        result = {
            "schema": SCHEMA,
            "status": (
                "PASS__RAW_GOAL_COMPILED_CONTROLLER_EXECUTED_VERIFIED_AND_CHECKPOINTED__"
                "RAW_ACCEPTANCE_RECEIPTS_STILL_REQUIRED"
                if passed else "FAIL__LIVE_CONTROLLER_RESULT_INVALID"
            ),
            "pass": passed,
            "task_id": task_id,
            "selected_plan": [selected],
            "verified_registry_capability_count": len(admissible),
            "execution": [execution_row],
            "controller_execution": dict(controller) if isinstance(controller, Mapping) else controller,
            "controller_checkpoint": dict(checkpoint),
            "cognition_dependency_class": (
                controller.get("cognition_dependency_class")
                if isinstance(controller, Mapping) else None
            ),
            "model_dependency_count": (
                controller.get("model_dependency_count")
                if isinstance(controller, Mapping) else None
            ),
            "raw_goal": goal,
            "raw_goal_sha256": raw_contract["task_sha256"],
            "raw_task_contract_sha256": raw_contract["task_contract_sha256"],
            "raw_acceptance_obligation_count": len(
                raw_contract["acceptance_contract"]["obligations"]
            ),
            "raw_source_coverage_complete": raw_contract[
                "nonwhitespace_source_coverage_complete"
            ],
            "compiled_capability_id": selected,
            "compiler_mode": compiled.get("compiler_mode"),
            "routing_success_authority": False,
            "semantic_acceptance_complete": False,
            "accepted_raw_obligation_ids": [],
            "elapsed_ns": perf_counter_ns() - started,
            "incremental_spend_usd": 0,
            "benchmark_specific": False,
            "terminal_credit_delta": 0,
        }
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
