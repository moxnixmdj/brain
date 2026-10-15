"""Fail-closed route admission in front of the live Brain.

Why this exists (measured 2026-10-15, see
``canonical/capabilities/true/LIVE_SOLVER_END_TO_END_MEASUREMENT_20261015_V1.json``):
the deterministic goal compiler selects a bound capability by token overlap.  When a
goal mentions a repository path such as ``canonical/astra_runtime/tmp/x.txt`` the path
components (``runtime``, ``tmp`` ...) become goal tokens, and a capability that needs no
inputs and always reports ``output_verified: true`` (``terminal.kstar.root.assess.stdlib``)
is selected for goals it cannot possibly serve ("Translate ... into French and save it to
.../fr.txt").  The live runtime then executes it and reports PASS.  That is a fail-open.

This module does not change the compiler (its bytes are pinned by governance records).  It
re-derives the compiler's own match evidence and refuses to execute when the evidence is
not about the goal:

  R1  PATH_TOKENS_ONLY         every matched token came from a repository path in the goal
  R2  OUTPUT_ARTIFACT_UNSERVED the goal names a file that does not exist yet (an output the
                               user expects) but the selected capability has no output path
                               input, so it cannot produce it
  R3  WEAK_EVIDENCE            at most one matched prose token: one word is never a goal
  R5  TOOL_TRUTH               after execution, a tool result saying ``pass: false`` or a
                               non-success status (OPEN__, UNRESOLVED, FAIL...) can never
                               surface as an overall PASS

  E1  EXECUTOR_GAP_BRIDGE      the pinned kernel refuses six registry source types outright
                               (``BOUND_CAPABILITY_SOURCE_UNSUPPORTED``: python_stdlib_composition,
                               brain_native_deterministic[_composition], brain_bound_system_tool,
                               brain_owned_python_composition).  Those 16 capabilities are run by
                               this entry itself: same adapter file, same args, same expectation
                               check as the kernel, declared stdlib modules verified first, and an
                               execution row that says so (``FRONT_LAYER_LOCAL_ADAPTER_EXECUTION_V1``).
  R6  PROMISED_ARTIFACT        after execution, every output file the goal named must exist
                               and be non-empty, independently of what the tool reported

Every rejection is a FAIL_CLOSED result with the evidence attached; nothing is executed,
so no side effect happens.  ``solve`` is THE live entry (one mouth): front-compile
(``goal_front_compiler_v1`` - corrects the pinned compiler's measured defects and binds every
registry input from an explicit grammar) -> admit -> execute through the same controller
calls ``run_raw_goal`` makes -> tool-truth check -> promised-artifact check.
Zero credit, zero spend, zero models.
"""
from __future__ import annotations

import pathlib
import re
import importlib.util
import sys
from time import perf_counter_ns
from typing import Any, Mapping

from canonical.runtime import astra_runtime, goal_compiler
from canonical.runtime import goal_front_compiler_v1 as front
from canonical.runtime.live_integrated_brain_v1 import (
    ROOT,
    SCHEMA as LIVE_SCHEMA,
    load_verified_registry,
)
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract

SCHEMA = "PROJECT_BRAIN_LIVE_BRAIN_ROUTE_ADMISSION_V1"
_PATH_RE = re.compile(r"[A-Za-z0-9_./-]+/[A-Za-z0-9_.-]+")


def _prose_tokens(goal: str) -> set[str]:
    """Goal tokens that survive when every repository path is removed from the text.

    A token that occurs only inside a path (``canonical/astra_runtime/tmp/x.txt`` ->
    ``runtime``) is not goal intent.  A token that also occurs in the prose (``archive`` in
    "Create a tar.gz archive ... save it to out.tar.gz") is.
    """
    return goal_compiler._tokens(_PATH_RE.sub(" ", goal))


def _future_artifacts(goal: str) -> list[str]:
    """Repository-relative paths named by the goal that do not exist yet."""
    out = []
    for raw, path in goal_compiler._repo_paths(goal, ROOT):
        if pathlib.Path(raw).suffix and not path.exists():
            out.append(raw)
    return out


def _output_keys(entry: Mapping[str, Any]) -> list[str]:
    keys = goal_compiler._placeholders(entry.get("action_template") or {})
    output_stems = {"output", "result", "report", "screenshot", "image", "artifact", "destination", "dest"}
    return sorted(
        k for k in keys
        if k.endswith("_path") and (k.startswith("output_") or k[:-5].lower() in output_stems)
    )


def route_admission(goal: str, compiled: Mapping[str, Any], registry: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Judge one compiled single-capability route. Returns {"admitted": bool, ...evidence}."""
    selected = str(compiled.get("selected_capability") or "").strip()
    mode = compiled.get("compiler_mode")
    if not selected:
        # Controller plans (literal JSON, exact literal, compound) are shaped by explicit
        # grammar matches, not by token overlap; nothing to re-judge here.
        return {"schema": SCHEMA, "admitted": True, "rule": None, "compiler_mode": mode, "selected_capability": None}
    entry = registry.get(selected)
    if entry is None:
        return {"schema": SCHEMA, "admitted": False, "rule": "SELECTED_CAPABILITY_NOT_ADMISSIBLE", "selected_capability": selected}
    score, specificity, evidence = goal_compiler._score(goal, selected, entry)
    matched = set(evidence.get("matched_provides") or []) | set(evidence.get("matched_identity") or []) | set(evidence.get("matched_keywords") or [])
    prose = _prose_tokens(goal)
    semantic = matched & prose
    input_keys = goal_compiler._placeholders(entry.get("action_template") or {})
    output_keys = _output_keys(entry)
    futures = _future_artifacts(goal)
    base = {
        "schema": SCHEMA,
        "compiler_mode": mode,
        "selected_capability": selected,
        "score": score,
        "matched_tokens": sorted(matched),
        "matched_from_paths_only": sorted(matched - prose),
        "semantic_matched_tokens": sorted(semantic),
        "goal_future_artifacts": futures,
        "capability_input_keys": sorted(input_keys),
        "capability_output_keys": output_keys,
    }
    if matched and not semantic:
        return {**base, "admitted": False, "rule": "R1_PATH_TOKENS_ONLY"}
    if futures and not output_keys:
        return {**base, "admitted": False, "rule": "R2_OUTPUT_ARTIFACT_UNSERVED"}
    if len(semantic) <= 1:
        return {**base, "admitted": False, "rule": "R3_WEAK_EVIDENCE"}
    return {**base, "admitted": True, "rule": None}


_NON_SUCCESS_PREFIXES = ("FAIL", "OPEN", "UNRESOLVED", "ERROR", "BLOCKED", "REJECTED", "INCOMPLETE")


def tool_truth_errors(result: Mapping[str, Any]) -> list[str]:
    """R5: the executed tool's own verdict wins over the controller's "it returned".

    The live runtime marks a raw goal PASS when the controller returned 0 and the first
    trace step produced a mapping.  Several bound tools write a report that says
    ``pass: false`` / ``status: OPEN__...`` / ``UNRESOLVED`` while still setting
    ``output_verified: true`` (they verified that they wrote their own failure report).
    That must never surface as PASS.
    """
    errors: list[str] = []
    rows = list(result.get("execution")) if isinstance(result.get("execution"), list) else []
    if not rows:
        controller = result.get("controller_execution")
        trace = controller.get("trace") if isinstance(controller, Mapping) else None
        for step in trace if isinstance(trace, list) else []:
            if isinstance(step, Mapping) and isinstance(step.get("result"), Mapping):
                action = step.get("action") if isinstance(step.get("action"), Mapping) else {}
                args = action.get("args") if isinstance(action.get("args"), Mapping) else {}
                rows.append({"capability_id": args.get("capability_id") or action.get("type"), "result": step.get("result")})
    for row in rows:
        inner = row.get("result") if isinstance(row, Mapping) else None
        if not isinstance(inner, Mapping):
            continue
        status = str(inner.get("status") or inner.get("outcome") or "").upper()
        if inner.get("pass") is False:
            errors.append("TOOL_REPORTED_PASS_FALSE:" + str(row.get("capability_id")))
        elif status.startswith(_NON_SUCCESS_PREFIXES):
            errors.append("TOOL_REPORTED_NON_SUCCESS_STATUS:" + str(row.get("capability_id")) + ":" + status[:48])
    return errors


def _fail(task_id: str, status: str, failure_class: str, started: int, **extra: Any) -> dict[str, Any]:
    out = {"schema": LIVE_SCHEMA, "status": status, "pass": False, "task_id": task_id, "failure_class": failure_class,
           "executed": extra.pop("executed", False), "elapsed_ns": perf_counter_ns() - started, "incremental_spend_usd": 0}
    out.update(extra)
    return out


def _controller_passed(controller: Any) -> bool:
    return (
        isinstance(controller, Mapping)
        and controller.get("returncode") == 0
        and controller.get("controller_mode") == "MODEL_INDEPENDENT_ACTION_PLAN"
        and controller.get("cognition_dependency_class") == "MODEL_INDEPENDENT"
        and controller.get("model_dependency_count") == 0
        and isinstance(controller.get("final_summary"), str)
        and bool(controller.get("final_summary").strip())
    )


KERNEL_UNSUPPORTED_SOURCE_TYPES = frozenset({
    "python_stdlib_composition", "brain_native_deterministic", "brain_native_deterministic_composition",
    "brain_bound_system_tool", "brain_owned_python_composition",
})
LOCAL_EXECUTION_PROOF = "FRONT_LAYER_LOCAL_ADAPTER_EXECUTION_V1"


def kernel_refuses(entry: Mapping[str, Any]) -> bool:
    """True when the pinned kernel would raise BOUND_CAPABILITY_SOURCE_UNSUPPORTED for this entry."""
    source = entry.get("source") if isinstance(entry.get("source"), Mapping) else {}
    return str(source.get("type") or "") in KERNEL_UNSUPPORTED_SOURCE_TYPES


class LocalExecutionFailure(RuntimeError):
    pass


def _check_expectation(expect: Any, result: Mapping[str, Any]) -> None:
    """The kernel's expectation semantics (field_nonempty / field_contains / field_equals)."""
    if expect is None:
        return
    if not isinstance(expect, Mapping):
        raise LocalExecutionFailure("ACTION_EXPECTATION_INVALID")
    field = str(expect.get("field") or "").strip()
    if not field:
        raise LocalExecutionFailure("ACTION_EXPECTATION_FIELD_REQUIRED")
    value = result.get(field)
    typ = expect.get("type", "field_nonempty")
    if typ == "field_nonempty":
        ok = value not in (None, "", [], {})
    elif typ == "field_contains":
        ok = str(expect.get("value", "")) in str(value or "")
    elif typ == "field_equals":
        ok = value == expect.get("value")
    else:
        raise LocalExecutionFailure("ACTION_EXPECTATION_TYPE_UNKNOWN:" + str(typ))
    if not ok:
        observed = json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else repr(value)
        reason = str(result.get("reason") or result.get("error") or "")[:800]
        raise LocalExecutionFailure("ACTION_EXPECTATION_FAILED:" + field + ":OBSERVED=" + observed[:800] + ((":REASON=" + reason) if reason else ""))


def run_adapter_locally(entry: Mapping[str, Any], action: Mapping[str, Any]) -> dict[str, Any]:
    """E1: execute one bound adapter the way the kernel would, for source types the kernel refuses.

    Fails closed on: non-zero declared cost, a declared stdlib module that does not import, an
    adapter path outside the repository or missing, a missing entrypoint, a non-dict result, or a
    failed expectation.  Never installs anything and never calls a network.
    """
    cid = str(entry.get("capability_id") or (action.get("args") or {}).get("capability_id") or "")
    if float(entry.get("incremental_spend_usd", 0) or 0) != 0:
        raise LocalExecutionFailure("BOUND_CAPABILITY_NONZERO_COST_REJECTED:" + cid)
    source = entry.get("source") if isinstance(entry.get("source"), Mapping) else {}
    modules = source.get("modules") if isinstance(source.get("modules"), list) else []
    for name in modules:
        if not str(name).strip() or importlib.util.find_spec(str(name).split(".")[0]) is None:
            raise LocalExecutionFailure("FRONT_LOCAL_DEPENDENCY_MISSING:" + str(name))
    module_name = str(entry.get("adapter_module") or "")
    if not module_name or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for ch in module_name):
        raise LocalExecutionFailure("BOUND_CAPABILITY_ADAPTER_INVALID")
    declared = str(source.get("adapter_path") or "")
    path = (ROOT / declared).resolve() if declared else (ROOT / "canonical" / "runtime" / "bound_capabilities" / (module_name + ".py")).resolve()
    if ROOT.resolve() not in path.parents or not path.is_file() or path.suffix != ".py":
        raise LocalExecutionFailure("BOUND_CAPABILITY_ADAPTER_MISSING:" + declared)
    spec = importlib.util.spec_from_file_location("project_brain_front_local_" + module_name, path)
    if spec is None or spec.loader is None:
        raise LocalExecutionFailure("BOUND_CAPABILITY_ADAPTER_LOAD_FAILED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    fn = getattr(module, str(entry.get("entrypoint") or "run"), None)
    if not callable(fn):
        raise LocalExecutionFailure("BOUND_CAPABILITY_ENTRYPOINT_MISSING")
    call_args = dict(action.get("args") or {})
    call_args.pop("capability_id", None)
    result = fn(call_args, ROOT)
    if not isinstance(result, dict):
        raise LocalExecutionFailure("BOUND_CAPABILITY_RESULT_INVALID")
    result.setdefault("capability_id", cid)
    result["dependency"] = {"type": str(source.get("type") or ""), "modules": list(modules), "executor": LOCAL_EXECUTION_PROOF}
    _check_expectation(action.get("expect"), result)
    return result


def _execute_locally(task_id: str, goal: str, compiled: Mapping[str, Any], entry: Mapping[str, Any], action: Mapping[str, Any],
                     raw_contract: Mapping[str, Any], started: int) -> dict[str, Any]:
    selected = str(compiled.get("selected_capability") or "")
    try:
        tool_result = run_adapter_locally(entry, action)
    except Exception as exc:  # noqa: BLE001 - every adapter failure is a closed failure with its reason
        return _fail(task_id, "FAIL__LIVE_CONTROLLER_EXECUTION", "LIVE_CONTROLLER_EXECUTION_OR_VERIFICATION_FAILURE", started, executed=True,
                     compiled_capability_id=selected, compiler_mode=compiled.get("compiler_mode"), reason=type(exc).__name__ + ":" + str(exc),
                     executor=LOCAL_EXECUTION_PROOF)
    row = {"capability_id": selected, "pass": True, "status": "PASS__FRONT_LAYER_LOCAL_ADAPTER_ACTION", "result": dict(tool_result),
           "execution_proof_type": LOCAL_EXECUTION_PROOF, "controller_plan_sha256": None, "controller_trace": [{"action": dict(action), "result": dict(tool_result)}]}
    return {
        "schema": LIVE_SCHEMA,
        "status": "PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED__RAW_ACCEPTANCE_RECEIPTS_STILL_REQUIRED",
        "pass": True, "task_id": task_id, "executed": True, "raw_goal": goal,
        "raw_goal_sha256": raw_contract["task_sha256"], "raw_task_contract_sha256": raw_contract["task_contract_sha256"],
        "raw_acceptance_obligation_count": len(raw_contract["acceptance_contract"]["obligations"]),
        "compiler_mode": compiled.get("compiler_mode"), "compiled_capability_id": selected,
        "selected_plan": [selected], "compiled_part_count": len(compiled.get("compiled_parts") or []),
        "controller_action_count": 1, "execution": [row],
        "controller_execution": {"executor": LOCAL_EXECUTION_PROOF, "reason_kernel_not_used": "BOUND_CAPABILITY_SOURCE_UNSUPPORTED:" + str((entry.get("source") or {}).get("type")),
                                  "returncode": 0, "controller_mode": "FRONT_LAYER_LOCAL_ADAPTER", "cognition_dependency_class": "MODEL_INDEPENDENT",
                                  "model_dependency_count": 0, "trace": row["controller_trace"]},
        "controller_checkpoint": {},
        "cognition_dependency_class": "MODEL_INDEPENDENT", "model_dependency_count": 0,
        "routing_success_authority": False, "semantic_acceptance_complete": False, "accepted_raw_obligation_ids": [],
        "elapsed_ns": perf_counter_ns() - started, "incremental_spend_usd": 0, "benchmark_specific": False, "terminal_credit_delta": 0,
    }


def _execute(task_id: str, goal: str, compiled: Mapping[str, Any], admissible: Mapping[str, Mapping[str, Any]], started: int) -> dict[str, Any]:
    """Execute a compiled plan with the same controller calls ``run_raw_goal`` makes."""
    controller_actions = compiled.get("controller_actions")
    selected = str(compiled.get("selected_capability") or "").strip()
    routing_targets = list(compiled.get("target_effects") or [])
    if not routing_targets:
        for part in compiled.get("compiled_parts") or []:
            if isinstance(part, Mapping):
                routing_targets.extend(e for e in part.get("target_effects") or [] if isinstance(e, str) and e not in routing_targets)
    raw_contract = compile_contract(goal, source_id="user", routing_target_effects=routing_targets)
    if raw_contract.get("pass") is not True:
        return _fail(task_id, "FAIL__LOSSLESS_RAW_TASK_CONTRACT", "RAW_TASK_OBLIGATION_ENVELOPE_FAILURE", started, errors=raw_contract.get("errors"))
    execution_rows: list[dict[str, Any]] = []
    if controller_actions is None:
        if not selected or selected not in admissible or not isinstance(compiled.get("inputs"), Mapping):
            return _fail(task_id, "FAIL__COMPILED_SHAPE_NOT_EXECUTABLE", "RAW_GOAL_COMPILED_SHAPE_GAP", started, compiler_mode=compiled.get("compiler_mode"))
        action = goal_compiler._render_template(admissible[selected]["action_template"], dict(compiled["inputs"]))
        if kernel_refuses(admissible[selected]):
            return _execute_locally(task_id, goal, compiled, admissible[selected], action, raw_contract, started)
        controller_actions = [action, {"type": "finish", "args": {"summary": "RAW_GOAL_COMPLETE"}}]
    if not isinstance(controller_actions, list) or not controller_actions or len(controller_actions) > 64 or any(not isinstance(a, Mapping) for a in controller_actions):
        return _fail(task_id, "FAIL__COMPILED_CONTROL_PLAN_INVALID", "LIVE_RUNTIME_COMPOSITION_CONTRACT_INVALID", started, compiler_mode=compiled.get("compiler_mode"))
    try:
        controller = astra_runtime.run_goal(
            {"id": "live-raw-goal-controller", "controller_actions": [dict(a) for a in controller_actions], "max_controller_actions": 64},
            {"mission_id": task_id, "goal": goal},
        )
    except Exception as exc:
        return _fail(task_id, "FAIL__LIVE_CONTROLLER_EXECUTION", "LIVE_CONTROLLER_EXECUTION_OR_VERIFICATION_FAILURE", started, executed=True,
                     compiled_capability_id=selected or None, compiler_mode=compiled.get("compiler_mode"), reason=type(exc).__name__ + ":" + str(exc))
    passed = _controller_passed(controller)
    trace = controller.get("trace") if isinstance(controller, Mapping) and isinstance(controller.get("trace"), list) else []
    checkpoint = controller.get("controller_checkpoint") if isinstance(controller, Mapping) and isinstance(controller.get("controller_checkpoint"), Mapping) else {}
    if selected:
        first_result = trace[0].get("result") if trace and isinstance(trace[0], Mapping) and isinstance(trace[0].get("result"), Mapping) else None
        passed = passed and isinstance(first_result, Mapping)
        execution_rows.append({"capability_id": selected, "pass": passed,
                               "status": "PASS__MODEL_INDEPENDENT_CONTROLLER_ACTION" if passed else "FAIL__MODEL_INDEPENDENT_CONTROLLER_ACTION",
                               "result": dict(first_result) if isinstance(first_result, Mapping) else None,
                               "execution_proof_type": "MODEL_INDEPENDENT_CONTROLLER_TRACE_V1",
                               "controller_plan_sha256": checkpoint.get("plan_sha256"), "controller_trace": list(trace)})
    return {
        "schema": LIVE_SCHEMA,
        "status": "PASS__RAW_GOAL_COMPILED_CONTROLLER_EXECUTED_VERIFIED_AND_CHECKPOINTED__RAW_ACCEPTANCE_RECEIPTS_STILL_REQUIRED" if passed else "FAIL__LIVE_CONTROLLER_RESULT_INVALID",
        "pass": passed, "task_id": task_id, "executed": True, "raw_goal": goal,
        "raw_goal_sha256": raw_contract["task_sha256"], "raw_task_contract_sha256": raw_contract["task_contract_sha256"],
        "raw_acceptance_obligation_count": len(raw_contract["acceptance_contract"]["obligations"]),
        "compiler_mode": compiled.get("compiler_mode"), "compiled_capability_id": selected or None,
        "selected_plan": [selected] if selected else [], "compiled_part_count": len(compiled.get("compiled_parts") or []),
        "controller_action_count": len(controller_actions), "execution": execution_rows,
        "controller_execution": dict(controller) if isinstance(controller, Mapping) else controller,
        "controller_checkpoint": dict(checkpoint),
        "cognition_dependency_class": controller.get("cognition_dependency_class") if isinstance(controller, Mapping) else None,
        "model_dependency_count": controller.get("model_dependency_count") if isinstance(controller, Mapping) else None,
        "routing_success_authority": False, "semantic_acceptance_complete": False, "accepted_raw_obligation_ids": [],
        "elapsed_ns": perf_counter_ns() - started, "incremental_spend_usd": 0, "benchmark_specific": False, "terminal_credit_delta": 0,
    }


def promised_artifact_errors(goal: str, future_artifacts: list[str]) -> list[str]:
    """R6: every output file the goal named must now exist and be non-empty."""
    errors = []
    for raw in future_artifacts:
        p = ROOT / raw
        if not p.is_file():
            errors.append("PROMISED_ARTIFACT_MISSING:" + raw)
        elif p.stat().st_size == 0:
            errors.append("PROMISED_ARTIFACT_EMPTY:" + raw)
    return errors


def solve(request: Mapping[str, Any]) -> dict[str, Any]:
    """THE live Brain entry: front-compile -> admit -> execute -> tool truth -> promised artifacts."""
    started = perf_counter_ns()
    task_id = str((request or {}).get("task_id") or "").strip()
    goal = str((request or {}).get("goal") or "").strip()
    if not task_id or not goal:
        return _fail(task_id, "FAIL_CLOSED", "REQUEST_INVALID", started)
    try:
        registry = load_verified_registry()
        admissible = goal_compiler._platform_admissible_registry(dict(registry))
        compiled = front.compile_goal(goal, admissible, ROOT)
    except goal_compiler.GoalCompilationFailure as exc:
        return _fail(task_id, "FAIL__RAW_GOAL_COMPILATION_GAP", "RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP", started,
                     compiler_code=exc.code, compiler_detail=exc.detail, route_admission=None)
    except Exception as exc:  # pragma: no cover - defensive, mirrors run_raw_goal
        return _fail(task_id, "FAIL_CLOSED", "RAW_GOAL_INTEGRATION_RUNTIME_ERROR", started, reason=type(exc).__name__ + ":" + str(exc))
    normalized = front.normalize_goal(goal)
    future_artifacts = _future_artifacts(normalized)
    admission = route_admission(normalized, compiled, admissible)
    admission["front_compiler_rules"] = list((compiled.get("front_compiler") or {}).get("rules_applied") or [])
    if admission.get("admitted") is not True:
        return _fail(task_id, "FAIL_CLOSED__ROUTE_ADMISSION_REJECTED", "ROUTE_ADMISSION_REJECTED:" + str(admission.get("rule")), started,
                     compiled_capability_id=admission.get("selected_capability"), compiler_mode=compiled.get("compiler_mode"), route_admission=admission)
    result = _execute(task_id, goal, compiled, admissible, started)
    result["route_admission"] = admission
    truth = tool_truth_errors(result)
    if truth and result.get("pass") is True:
        result["runtime_status_before_truth_check"] = result.get("status")
        result["status"] = "FAIL_CLOSED__TOOL_REPORTED_NON_SUCCESS"
        result["pass"] = False
        result["failure_class"] = "TOOL_REPORTED_NON_SUCCESS"
        result["tool_truth_errors"] = truth
        result["side_effects_may_exist"] = True
    missing = promised_artifact_errors(goal, future_artifacts) if result.get("pass") is True else []
    if missing:
        result["runtime_status_before_artifact_check"] = result.get("status")
        result["status"] = "FAIL_CLOSED__PROMISED_ARTIFACT_MISSING"
        result["pass"] = False
        result["failure_class"] = "PROMISED_ARTIFACT_MISSING"
        result["promised_artifact_errors"] = missing
    result["elapsed_ns"] = perf_counter_ns() - started
    return result
