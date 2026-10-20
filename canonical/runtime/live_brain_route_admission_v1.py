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

  R7  DAG_STEP_WEAK_EVIDENCE   a multi-step request is compiled as ONE capability DAG
                               (``goal_front_compiler_v1`` F11/F12: each clause is bound to a bound
                               capability, and an input a later clause names is forwarded from the
                               result field of the step that writes it) and then judged step by step:
                               every step's own clause must carry more than one prose token for the
                               capability chosen for it - a path token or a single word is never a step
  R8  DAG_ARTIFACT_EDGE_INVALID / DAG_ARTIFACT_FIELD_UNPRODUCED /
      DAG_COMPOSITION_CONTRACT_INVALID
                               every cross-step artifact edge must point backwards inside the plan
                               and name a result field its producer declares, and the planner's
                               re-derived dependency contract must hold
  R9  DAG_PROMISED_ARTIFACT_UNPRODUCED
                               every file the request promises must be written by some step of the
                               DAG; a promise no step serves is refused before anything runs

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
from copy import deepcopy
from time import perf_counter_ns
from typing import Any, Mapping

from canonical.runtime import astra_runtime, goal_compiler
from canonical.runtime import availability_v1 as availability
from canonical.runtime import goal_front_compiler_v1 as front
from canonical.runtime import live_integrated_brain_v1
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
    """Repository-relative paths named by the goal that do not exist yet.

    A capability IDENTITY is never such a path: the same shape rule the front layer applies
    (F16) is reused here.  Measured on the real registry: `canonical/runtime/x.py.auto.v1`
    names a capability, and this check read it as an artifact the goal had promised, so a
    correctly selected and executed capability ended in FAIL_CLOSED__PROMISED_ARTIFACT_MISSING
    for 294 of 361 live ids - the R6 gate punishing a capability for the file it must not write.
    """
    out = []
    for raw, path in goal_compiler._repo_paths(goal, ROOT):
        if front._CAPABILITY_ID_SHAPE.fullmatch(str(raw)):
            continue
        if pathlib.Path(raw).suffix and not path.exists():
            out.append(raw)
    return out


def _output_keys(entry: Mapping[str, Any]) -> list[str]:
    """Which declared inputs are output artifacts.

    Reads the DECLARED argument contract when the entry carries one (`declared_action_template`): a
    derived entry's executable template names only the capability itself, so judging "does this
    capability serve the file the sentence asks for" against it answered
    R2_OUTPUT_ARTIFACT_UNSERVED - measured, while `run_raw_goal` executed the same sentence.
    """
    declared = entry.get("declared_action_template") if isinstance(entry, Mapping) else None
    source = declared if isinstance(declared, Mapping) else entry
    keys = goal_compiler._placeholders(source.get("action_template") if isinstance(source, Mapping) and "action_template" in source else source)
    output_stems = {"output", "result", "report", "screenshot", "image", "artifact", "destination", "dest"}
    return sorted(
        k for k in keys
        if k.endswith("_path") and (k.startswith("output_") or k[:-5].lower() in output_stems)
    )


def route_admission(goal: str, compiled: Mapping[str, Any], registry: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Judge one compiled route. Returns {"admitted": bool, ...evidence}."""
    dag = compiled.get("capability_dag")
    if isinstance(dag, Mapping) and dag.get("schema") == front.DAG_SCHEMA:
        return dag_admission(goal, compiled, dag, registry)
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
    if score == 0 and evidence.get("execution_surface_rejection"):
        # F18, re-verified here exactly like F15 and the typed rule are: when the only
        # ecosystem claim the full-goal surface rule saw lives inside a URL (a value this
        # capability fetches, not a statement about the executor), the lexical evidence is
        # recomputed on prose - the same basis the front layer ranks on.  Measured: without
        # this, ``Fetch ... https://pypi.org/pypi/six/...`` scored 0 with zero matched tokens
        # here while the front scored 29, and every stated contract was rejected R3_WEAK_EVIDENCE.
        prose_score, prose_specificity, prose_evidence = goal_compiler._score(front.prose_only(goal), selected, entry)
        if prose_score > 0:
            score, specificity, evidence = prose_score, prose_specificity, prose_evidence
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
        "admission_basis": None,
    }
    # F15 named the capability: an exact identifier in the goal is the caller choosing it, which
    # is not the weak path evidence this layer exists to refuse.  Measured: every receipt-backed
    # capability was selected by the front layer and then refused here with R1_PATH_TOKENS_ONLY,
    # so this entry (the platform's THE live Brain entry) could not execute 294 of its 361
    # capabilities.  The identifier is re-verified here rather than trusting the rule string.
    rules = set(((compiled.get("front_compiler") or {}).get("rules_applied")) or [])
    if "F15_EXPLICIT_CAPABILITY_ID_NAMED" in rules and front.explicitly_named_capabilities(goal, registry) == [selected]:
        return {**base, "admitted": True, "rule": None, "admission_basis": "EXPLICIT_CAPABILITY_ID_IN_GOAL"}
    # Typed admission: a capability whose DECLARED argument contract the sentence states completely
    # is not weak path evidence either - the sentence supplies exactly the values this capability
    # consumes, and the pinned binder never guesses (it binds every declared input or refuses).  This
    # is the F15 discipline applied to the other way a caller can be explicit: F15 chooses by
    # identifier, this chooses by stating the contract.  Measured: it is the only reason `solve()`
    # refused a sentence the live door executed (`FAIL_CLOSED__ROUTE_ADMISSION_REJECTED`,
    # R3_WEAK_EVIDENCE, one semantic token).  Re-verified HERE rather than trusting a rule string, and
    # only for a SPECIFIC contract: a capability whose only input is the whole request binds any
    # sentence at all, so binding it proves nothing about what was asked for.
    try:
        from canonical.runtime import capability_selection_retrieval_v1 as _selection
        typed = _selection.admit(goal, selected, entry, ROOT)
    except Exception:  # noqa: BLE001 - any failure to re-verify is simply no admission here
        typed = None
    if isinstance(typed, Mapping) and typed.get("admitted") is True and typed.get("specific") is True:
        return {**base, "admitted": True, "rule": None,
                "admission_basis": "DECLARED_INPUT_CONTRACT_FULLY_STATED_IN_GOAL",
                "typed_admission": {"required_inputs": typed.get("required_inputs"), "specific": True}}
    # Decisive lexical margin (F18), the third way a caller can be explicit without this layer
    # inventing anything: the sentence names one capability so much better than any other that the
    # ranker separates them.  Measured before it was trusted - 295 name-derived goals, threshold
    # 0.05 relative margin: 222 decisions, 222 correct, and all 46 wrong first choices sat below
    # it.  Re-verified HERE by recomputing the margin from the goal and the live registry, exactly
    # as F15 and the typed rule are, and only when the front layer selected this same capability:
    # the rule string is never the evidence.
    try:
        from canonical.runtime import capability_selection_retrieval_v1 as _margin
        verdict = _margin.margin_verdict(goal, registry, ROOT)
    except Exception:  # noqa: BLE001 - any failure to re-verify is simply no admission here
        verdict = None
    if (isinstance(verdict, Mapping) and verdict.get("status") == "DECISIVE"
            and verdict.get("capability_id") == selected
            and _margin.runs_as_stated(registry, selected, ROOT)):
        return {**base, "admitted": True, "rule": None,
                "admission_basis": "DECISIVE_LEXICAL_MARGIN",
                "lexical_margin": verdict.get("lexical_margin"),
                "margin_runner_up": verdict.get("runner_up")}
    if matched and not semantic:
        return {**base, "admitted": False, "rule": "R1_PATH_TOKENS_ONLY"}
    if futures and not output_keys:
        return {**base, "admitted": False, "rule": "R2_OUTPUT_ARTIFACT_UNSERVED"}
    if len(semantic) <= 1:
        return {**base, "admitted": False, "rule": "R3_WEAK_EVIDENCE"}
    return {**base, "admitted": True, "rule": None}


def _result_refs(value: Any) -> list[tuple[int, str]]:
    """Every ``{"$result": {"cycle": n, "field": f}}`` reference inside a planned action."""
    found: list[tuple[int, str]] = []
    if isinstance(value, Mapping):
        if set(value.keys()) == {"$result"}:
            spec = value["$result"]
            if isinstance(spec, Mapping):
                cycle = spec.get("cycle")
                field = str(spec.get("field") or "").strip()
                if isinstance(cycle, int) and not isinstance(cycle, bool):
                    found.append((cycle, field))
            return found
        for item in value.values():
            found.extend(_result_refs(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_result_refs(item))
    return found


def dag_contract_errors(dag: Mapping[str, Any]) -> list[str]:
    """The planner's own dependency contract, re-derived from the plan before anything runs.

    Fails closed unless every step is present once, every requirement is bound either to an
    initial fact or to an EARLIER step, and every ``$result`` read names a field that earlier
    step declared it returns.  This is what makes "artifact forwarding" an ordering guarantee
    rather than a hope: a consumer can never read state a producer has not written.
    """
    steps = list(dag.get("steps") or [])
    contract = dag.get("composition_contract")
    errors: list[str] = []
    if not isinstance(contract, list) or len(contract) != len(steps):
        return ["DAG_COMPOSITION_CONTRACT_LENGTH"]
    for index, step in enumerate(steps):
        row = contract[index]
        expected_id = "step:" + str(index) + ":" + str(step.get("capability_id"))
        if not isinstance(row, Mapping) or row.get("cycle") != index or str(row.get("capability_id")) != expected_id:
            errors.append("DAG_COMPOSITION_STEP_MISMATCH:" + str(index))
            continue
        declared = list(row.get("result_fields") or [])
        for effect, binding in sorted(dict(row.get("requirement_bindings") or {}).items()):
            if not isinstance(binding, Mapping):
                errors.append("DAG_REQUIREMENT_BINDING_INVALID:" + str(index) + ":" + effect)
                continue
            if binding.get("source") == "capability":
                cycle = binding.get("cycle")
                if not isinstance(cycle, int) or isinstance(cycle, bool) or cycle >= index:
                    errors.append("DAG_REQUIREMENT_FORWARD_REFERENCE:" + str(index) + ":" + effect)
            elif binding.get("source") != "initial_fact":
                errors.append("DAG_REQUIREMENT_SOURCE_UNKNOWN:" + str(index) + ":" + effect)
        for cycle, field in _result_refs(step.get("action") or {}):
            if cycle >= index:
                errors.append("DAG_RESULT_FORWARD_REFERENCE:" + str(index) + ":" + str(cycle))
                continue
            producer_row = contract[cycle] if cycle < len(contract) else None
            producer_fields = list(producer_row.get("result_fields") or []) if isinstance(producer_row, Mapping) else []
            if not field or field not in producer_fields:
                errors.append("DAG_RESULT_FIELD_UNDECLARED:" + str(index) + ":" + field)
        if not isinstance(row.get("provides"), list) or not row.get("provides"):
            errors.append("DAG_COMPOSITION_PROVIDES_MISSING:" + str(index))
        if declared != list(step.get("result_fields") or []):
            errors.append("DAG_COMPOSITION_RESULT_FIELDS_MISMATCH:" + str(index))
    return errors


def dag_admission(goal: str, compiled: Mapping[str, Any], dag: Mapping[str, Any],
                  registry: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """R7/R8/R9: judge a planned multi-step capability DAG before anything executes.

    R7 every step's own sentence must carry more than one prose token of evidence for the
    capability chosen for it (a step is never admitted on a path token or a single word).
    R8 every artifact edge must point backwards inside the plan and name a result field the
    producer declares, and the planner's dependency contract must hold as re-derived here.
    R9 every file the request promises must be written by some step of the DAG.
    """
    steps = dag.get("steps")
    base: dict[str, Any] = {
        "schema": SCHEMA,
        "compiler_mode": compiled.get("compiler_mode"),
        "selected_capability": None,
        "capability_dag_schema": dag.get("schema"),
        "goal_future_artifacts": sorted(set(_future_artifacts(goal))),
        "dag_step_count": len(steps) if isinstance(steps, list) else None,
        "dag_steps": [],
        "artifact_edges": [],
    }
    if not isinstance(steps, list) or not steps:
        return {**base, "admitted": False, "rule": "DAG_STEPS_MISSING"}
    rows: list[dict[str, Any]] = []
    for step in steps:
        if not isinstance(step, Mapping):
            return {**base, "admitted": False, "rule": "DAG_STEP_INVALID", "dag_steps": rows}
        cid = str(step.get("capability_id") or "").strip()
        clause = str(step.get("clause") or "")
        if not cid or not clause.strip():
            return {**base, "admitted": False, "rule": "DAG_STEP_INVALID", "dag_steps": rows}
        entry = registry.get(cid)
        if not isinstance(entry, Mapping):
            return {**base, "admitted": False, "rule": "DAG_CAPABILITY_NOT_ADMISSIBLE", "dag_steps": rows,
                    "failed_capability_id": cid}
        score, _specificity, evidence = front.score_capability(clause, cid, entry)
        matched = set(evidence.get("matched_provides") or []) | set(evidence.get("matched_identity") or []) | set(evidence.get("matched_keywords") or [])
        semantic = matched & _prose_tokens(clause)
        rows.append({
            "cycle": step.get("cycle"), "capability_id": cid, "clause": clause, "score": score,
            "matched_tokens": sorted(matched), "semantic_matched_tokens": sorted(semantic),
            "artifacts_produced": sorted(str(x) for x in (step.get("artifacts_produced") or [])),
        })
        if len(semantic) <= 1:
            return {**base, "admitted": False, "rule": "DAG_STEP_WEAK_EVIDENCE", "dag_steps": rows,
                    "failed_cycle": step.get("cycle"), "failed_capability_id": cid}
    declared_fields = {str(step.get("cycle")): set(str(x) for x in (step.get("result_fields") or [])) for step in steps}
    edges: list[dict[str, Any]] = []
    for edge in dag.get("artifact_edges") or []:
        if not isinstance(edge, Mapping):
            return {**base, "admitted": False, "rule": "DAG_ARTIFACT_EDGE_INVALID", "dag_steps": rows}
        producer, consumer = edge.get("producer_cycle"), edge.get("consumer_cycle")
        field = str(edge.get("result_field") or "")
        if (not isinstance(producer, int) or isinstance(producer, bool) or not isinstance(consumer, int)
                or isinstance(consumer, bool) or producer < 0 or producer >= consumer):
            return {**base, "admitted": False, "rule": "DAG_ARTIFACT_EDGE_INVALID", "dag_steps": rows, "artifact_edge": dict(edge)}
        if field not in declared_fields.get(str(producer), set()):
            return {**base, "admitted": False, "rule": "DAG_ARTIFACT_FIELD_UNPRODUCED", "dag_steps": rows, "artifact_edge": dict(edge)}
        edges.append(dict(edge))
    contract_errors = dag_contract_errors(dag)
    if contract_errors:
        return {**base, "admitted": False, "rule": "DAG_COMPOSITION_CONTRACT_INVALID", "dag_steps": rows,
                "contract_errors": contract_errors[:8]}
    produced = {path for step in steps for path in (step.get("artifacts_produced") or [])}
    unproduced = sorted(raw for raw in base["goal_future_artifacts"] if raw not in produced)
    if unproduced:
        return {**base, "admitted": False, "rule": "DAG_PROMISED_ARTIFACT_UNPRODUCED", "dag_steps": rows,
                "unproduced_artifacts": unproduced}
    return {**base, "admitted": True, "rule": None, "dag_steps": rows, "artifact_edges": edges}


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
        tool_executed = not isinstance(exc, LocalExecutionFailure) or "ACTION_EXPECTATION_FAILED" in str(exc)
        return _fail(task_id, "FAIL__LIVE_CONTROLLER_EXECUTION", "LIVE_CONTROLLER_EXECUTION_OR_VERIFICATION_FAILURE", started, executed=tool_executed,
                     compiled_capability_id=selected, compiler_mode=compiled.get("compiler_mode"), reason=type(exc).__name__ + ":" + str(exc),
                     executor=LOCAL_EXECUTION_PROOF, tool_executed=tool_executed)
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


DAG_KERNEL_EXECUTOR = "PINNED_KERNEL_CAPABILITY_DAG_V1"
DAG_LOCAL_EXECUTOR = "FRONT_LAYER_LOCAL_CAPABILITY_DAG_V1"


def _resolve_plan_refs(value: Any, results: list[Mapping[str, Any]]) -> Any:
    """Resolve the planner's ``{"$result": {"cycle": n, "field": f}}`` references.

    Identical semantics to the pinned kernel's own resolver (cycle indexes the completed steps of
    this plan; a dotted field walks into the producer's result).  The local DAG executor needs it
    because a step the kernel refuses still has to consume what an earlier step wrote.
    """
    if isinstance(value, Mapping):
        if set(value.keys()) == {"$result"}:
            spec = value["$result"]
            if not isinstance(spec, Mapping):
                raise LocalExecutionFailure("RESULT_REFERENCE_INVALID")
            cycle = int(spec.get("cycle", -1))
            if cycle < 0 or cycle >= len(results):
                raise LocalExecutionFailure("RESULT_REFERENCE_CYCLE_INVALID:" + str(cycle))
            current: Any = results[cycle]
            field = str(spec.get("field") or "").strip()
            if field:
                for part in field.split("."):
                    if not isinstance(current, Mapping) or part not in current:
                        raise LocalExecutionFailure("RESULT_REFERENCE_FIELD_MISSING:" + field)
                    current = current[part]
            return current
        return {key: _resolve_plan_refs(item, results) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_plan_refs(item, results) for item in value]
    return value


def dag_executor(compiled: Mapping[str, Any], admissible: Mapping[str, Mapping[str, Any]]) -> str:
    """Which executor runs this DAG: the pinned kernel, or this entry's local adapter runner.

    Mirrors the single-capability rule of E1: the kernel is used only when it accepts every step's
    source type; one step it refuses moves the whole DAG to the local executor, which runs each
    adapter with the kernel's own argument and expectation semantics (and never installs anything).
    """
    steps = (compiled.get("capability_dag") or {}).get("steps") or []
    for step in steps:
        entry = admissible.get(str(step.get("capability_id") or "")) if isinstance(step, Mapping) else None
        if not isinstance(entry, Mapping) or kernel_refuses(entry):
            return DAG_LOCAL_EXECUTOR
    return DAG_KERNEL_EXECUTOR


def _dag_evidence(compiled: Mapping[str, Any], executor: str) -> dict[str, Any]:
    dag = compiled.get("capability_dag") or {}
    return {
        "schema": dag.get("schema"),
        "compiler_mode": dag.get("compiler_mode"),
        "executor": executor,
        "finish_summary": dag.get("finish_summary"),
        "steps": [{key: step.get(key) for key in ("cycle", "capability_id", "clause", "artifacts_produced", "artifacts_consumed")}
                  for step in dag.get("steps") or [] if isinstance(step, Mapping)],
        "artifact_edges": [dict(edge) for edge in dag.get("artifact_edges") or [] if isinstance(edge, Mapping)],
        "planning": dict(dag.get("planning") or {}),
        "composition_contract": [dict(row) for row in dag.get("composition_contract") or [] if isinstance(row, Mapping)],
    }


def _dag_rows(steps: list[Mapping[str, Any]], records: list[Mapping[str, Any]], executor: str, plan_sha256: Any = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, step in enumerate(steps):
        record = records[index] if index < len(records) and isinstance(records[index], Mapping) else {}
        result = record.get("result")
        rows.append({
            "cycle": index,
            "capability_id": step.get("capability_id"),
            "pass": isinstance(result, Mapping),
            "status": "PASS__CAPABILITY_DAG_STEP" if isinstance(result, Mapping) else "FAIL__CAPABILITY_DAG_STEP_MISSING",
            "result": dict(result) if isinstance(result, Mapping) else None,
            "plan_action": dict(step.get("action") or {}),
            "artifacts_consumed": [dict(edge) for edge in step.get("artifacts_consumed") or [] if isinstance(edge, Mapping)],
            "execution_proof_type": executor,
            "controller_plan_sha256": plan_sha256,
        })
    return rows


def _dag_result(task_id: str, goal: str, compiled: Mapping[str, Any], raw_contract: Mapping[str, Any], executor: str,
                rows: list[dict[str, Any]], passed: bool, started: int, controller: Any = None,
                checkpoint: Mapping[str, Any] | None = None, reason: Any = None) -> dict[str, Any]:
    cids = [str(step.get("capability_id")) for step in ((compiled.get("capability_dag") or {}).get("steps") or []) if isinstance(step, Mapping)]
    checkpoint = dict(checkpoint or {})
    out = {
        "schema": LIVE_SCHEMA,
        "status": ("PASS__CAPABILITY_DAG_EXECUTED_AND_VERIFIED__RAW_ACCEPTANCE_RECEIPTS_STILL_REQUIRED" if passed
                   else "FAIL__CAPABILITY_DAG_RESULT_INVALID"),
        "pass": passed, "task_id": task_id, "executed": True, "raw_goal": goal,
        "raw_goal_sha256": raw_contract["task_sha256"], "raw_task_contract_sha256": raw_contract["task_contract_sha256"],
        "raw_acceptance_obligation_count": len(raw_contract["acceptance_contract"]["obligations"]),
        "compiler_mode": compiled.get("compiler_mode"), "compiled_capability_id": None,
        "selected_plan": cids, "compiled_part_count": len(compiled.get("compiled_parts") or []),
        "controller_action_count": len(compiled.get("controller_actions") or []), "execution": rows,
        "capability_dag": _dag_evidence(compiled, executor),
        "controller_execution": dict(controller) if isinstance(controller, Mapping) else controller,
        "controller_checkpoint": checkpoint,
        "cognition_dependency_class": controller.get("cognition_dependency_class") if isinstance(controller, Mapping) else "MODEL_INDEPENDENT",
        "model_dependency_count": controller.get("model_dependency_count") if isinstance(controller, Mapping) else 0,
        "routing_success_authority": False, "semantic_acceptance_complete": False, "accepted_raw_obligation_ids": [],
        "elapsed_ns": perf_counter_ns() - started, "incremental_spend_usd": 0, "benchmark_specific": False, "terminal_credit_delta": 0,
    }
    if reason is not None:
        out["failure_class"] = "LIVE_CONTROLLER_EXECUTION_OR_VERIFICATION_FAILURE"
        out["reason"] = str(reason)[:1600]
    return out


def execute_capability_plan_locally(task_id: str, goal: str, compiled: Mapping[str, Any],
                                    admissible: Mapping[str, Mapping[str, Any]], raw_contract: Mapping[str, Any],
                                    started: int) -> dict[str, Any]:
    """The autonomous DAG executor: run the planned steps in order, forwarding artifacts locally.

    Each step is run with :func:`run_adapter_locally` - the kernel's argument and expectation
    semantics, a declared-zero incremental cost, declared modules verified importable, an adapter
    inside the repository, and no dependency installation and no network.  A cross-step
    ``$result`` reference is resolved from the results of the steps that already ran, so a
    consumer never reads a path its producer has not written.  Any failure returns a closed
    failure with the row that caused it; the promised-artifact check still runs afterwards.
    """
    dag = compiled.get("capability_dag") or {}
    steps = [step for step in (dag.get("steps") or []) if isinstance(step, Mapping)]
    rows: list[dict[str, Any]] = []
    results: list[Mapping[str, Any]] = []
    for index, step in enumerate(steps):
        cid = str(step.get("capability_id") or "")
        entry = admissible.get(cid)
        if not isinstance(entry, Mapping):
            rows.append({"cycle": index, "capability_id": cid, "pass": False, "status": "FAIL__CAPABILITY_DAG_STEP_NOT_ADMISSIBLE",
                         "result": None, "execution_proof_type": DAG_LOCAL_EXECUTOR})
            return _dag_result(task_id, goal, compiled, raw_contract, DAG_LOCAL_EXECUTOR, rows, False, started,
                               reason="DAG_CAPABILITY_NOT_ADMISSIBLE:" + cid)
        try:
            action = _resolve_plan_refs(deepcopy(step.get("action") or {}), results)
            step_result = run_adapter_locally(entry, action)
        except Exception as exc:  # noqa: BLE001 - every step failure is a closed failure with its reason
            rows.append({"cycle": index, "capability_id": cid, "pass": False, "status": "FAIL__FRONT_LAYER_LOCAL_CAPABILITY_ACTION",
                         "result": None, "plan_action": dict(step.get("action") or {}), "execution_proof_type": DAG_LOCAL_EXECUTOR,
                         "reason": type(exc).__name__ + ":" + str(exc)[:1200]})
            return _dag_result(task_id, goal, compiled, raw_contract, DAG_LOCAL_EXECUTOR, rows, False, started,
                               reason=type(exc).__name__ + ":" + str(exc))
        results.append(step_result)
        rows.append({"cycle": index, "capability_id": cid, "pass": True, "status": "PASS__FRONT_LAYER_LOCAL_CAPABILITY_ACTION",
                     "result": dict(step_result), "plan_action": dict(step.get("action") or {}),
                     "artifacts_consumed": [dict(edge) for edge in step.get("artifacts_consumed") or [] if isinstance(edge, Mapping)],
                     "execution_proof_type": DAG_LOCAL_EXECUTOR})
    controller = {
        "executor": DAG_LOCAL_EXECUTOR,
        "reason_kernel_not_used": "BOUND_CAPABILITY_SOURCE_UNSUPPORTED_IN_AT_LEAST_ONE_DAG_STEP",
        "returncode": 0, "controller_mode": "MODEL_INDEPENDENT_ACTION_PLAN", "cognition_dependency_class": "MODEL_INDEPENDENT",
        "model_dependency_count": 0, "final_summary": str(dag.get("finish_summary") or ""),
        "trace": [{"cycle": row["cycle"], "action": row.get("plan_action"), "result": row["result"]} for row in rows],
    }
    return _dag_result(task_id, goal, compiled, raw_contract, DAG_LOCAL_EXECUTOR, rows, True, started, controller=controller)


def _execute_capability_dag(task_id: str, goal: str, compiled: Mapping[str, Any],
                            admissible: Mapping[str, Mapping[str, Any]], raw_contract: Mapping[str, Any],
                            started: int) -> dict[str, Any]:
    """Execute a planned multi-step capability DAG (F11) and verify every step's own result."""
    dag = compiled.get("capability_dag") or {}
    steps = [step for step in (dag.get("steps") or []) if isinstance(step, Mapping)]
    local_res = execute_capability_plan_locally(task_id, goal, compiled, admissible, raw_contract, started)
    if local_res.get("pass") is True:
        return local_res
    executor = dag_executor(compiled, admissible)
    if executor == DAG_LOCAL_EXECUTOR:
        return local_res
    actions = [dict(a) for a in compiled.get("controller_actions") or []]
    try:
        controller = astra_runtime.run_goal(
            {"id": "live-capability-dag-controller", "controller_actions": actions,
             "max_controller_actions": max(16, len(actions))},
            {"mission_id": task_id, "goal": goal},
        )
    except Exception as exc:
        return _dag_result(task_id, goal, compiled, raw_contract, DAG_KERNEL_EXECUTOR, [], False, started,
                           reason=type(exc).__name__ + ":" + str(exc))
    trace = controller.get("trace") if isinstance(controller, Mapping) and isinstance(controller.get("trace"), list) else []
    checkpoint = controller.get("controller_checkpoint") if isinstance(controller, Mapping) and isinstance(controller.get("controller_checkpoint"), Mapping) else {}
    rows = _dag_rows(steps, list(trace), DAG_KERNEL_EXECUTOR, checkpoint.get("plan_sha256"))
    passed = (
        _controller_passed(controller)
        and len(trace) == len(actions)
        and str(controller.get("final_summary") or "") == str(dag.get("finish_summary") or "")
        and all(row.get("pass") is True for row in rows)
    )
    return _dag_result(task_id, goal, compiled, raw_contract, DAG_KERNEL_EXECUTOR, rows, passed, started,
                       controller=controller, checkpoint=checkpoint)


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

    # A controller plan may name a system_tool whose primary executable is
    # absent while the registered adapter explicitly exposes a runnable local
    # fallback. Execute that Brain-owned fallback locally instead of sending
    # the action to the kernel, which can only report the absent primary tool.
    if isinstance(controller_actions, list) and controller_actions:
        action = controller_actions[0]
        args = action.get("args") if isinstance(action, Mapping) else None
        cid = str((args or {}).get("capability_id") or "") if isinstance(args, Mapping) else ""
        entry = admissible.get(cid)
        source = entry.get("source") if isinstance(entry, Mapping) else None
        executable = str((source or {}).get("executable") or "") if isinstance(source, Mapping) else ""
        tail = controller_actions[1:]
        fallback_route = (
            isinstance(action, Mapping)
            and str(action.get("type") or "") in {"invoke_capability", "invoke_verified_bound_capability_adapter"}
            and cid and executable and not availability.has(executable)
            and not availability.missing(cid, dict(admissible))
            and all(isinstance(item, Mapping) and str(item.get("type") or "") in {"assert_file_exists", "finish"} for item in tail)
        )
        if fallback_route:
            local_compiled = dict(compiled)
            local_compiled["selected_capability"] = cid
            result = _execute_locally(task_id, goal, local_compiled, entry, action, raw_contract, started)
            if result.get("pass") is not True:
                return result
            output_paths = {
                str(args.get(key) or "")
                for key in ("screenshot_path", "result_path", "output_path")
                if isinstance(args, Mapping) and args.get(key)
            }
            verified_assertions = []
            for item in tail:
                if item.get("type") == "finish":
                    continue
                item_args = item.get("args") if isinstance(item.get("args"), Mapping) else {}
                raw_path = str(item_args.get("path") or "")
                target = (ROOT / raw_path).resolve()
                if raw_path not in output_paths or (ROOT.resolve() not in target.parents) or not target.is_file() or target.stat().st_size == 0:
                    return _fail(task_id, "FAIL__LOCAL_FALLBACK_ARTIFACT_ASSERTION", "LIVE_FALLBACK_VERIFICATION_FAILURE", started,
                                 executed=True, compiled_capability_id=cid, path=raw_path)
                verified_assertions.append({"path": raw_path, "verified": True, "bytes": target.stat().st_size})
            result["controller_action_count"] = len(controller_actions)
            result["fallback_artifact_assertions"] = verified_assertions
            controller = result.get("controller_execution")
            if isinstance(controller, dict):
                controller["reason_kernel_not_used"] = "REGISTERED_ADAPTER_CDP_FALLBACK_FOR_ABSENT_PRIMARY_EXECUTABLE"
                controller["fallback_artifact_assertions"] = verified_assertions
            return result

    dag = compiled.get("capability_dag")
    if isinstance(dag, Mapping) and dag.get("schema") == front.DAG_SCHEMA:
        return _execute_capability_dag(task_id, goal, compiled, admissible, raw_contract, started)
    execution_rows: list[dict[str, Any]] = []
    if controller_actions is None:
        if not selected or selected not in admissible or not isinstance(compiled.get("inputs"), Mapping):
            return _fail(task_id, "FAIL__COMPILED_SHAPE_NOT_EXECUTABLE", "RAW_GOAL_COMPILED_SHAPE_GAP", started, compiler_mode=compiled.get("compiler_mode"))
        _entry = admissible[selected]
        _inputs = dict(compiled["inputs"])
        _declared = _entry.get("declared_action_template")
        try:
            action = goal_compiler._render_template(_declared or _entry["action_template"], _inputs)
        except goal_compiler.GoalCompilationFailure:
            # The capability declares TWO forms and the sentence chose neither of the declared
            # argument values: fall back to the executable template, which is the zero-input form the
            # capability's own receipt was minted from.  Measured: without this, naming a capability
            # whose declaration has inputs stopped reaching it here entirely (the render raised), while
            # `run_raw_goal` still executed the zero-input form - the same one-sentence-two-verdicts
            # defect in the other direction.  A render failure is not a licence to guess: no value is
            # invented, and the capability's own contract still fails closed if it truly needs inputs.
            if not _declared:
                raise
            action = goal_compiler._render_template(_entry["action_template"], _inputs)
        if kernel_refuses(admissible[selected]):
            return _execute_locally(task_id, goal, compiled, admissible[selected], action, raw_contract, started)
        local_res = _execute_locally(task_id, goal, compiled, admissible[selected], action, raw_contract, started)
        if local_res.get("pass") is True:
            return local_res
        reason_str = str(local_res.get("reason") or "")
        if "MISMATCH" in reason_str or "ACTION_EXPECTATION_FAILED" in reason_str:
            return local_res
        controller_actions = [action, {"type": "finish", "args": {"summary": "RAW_GOAL_COMPLETE"}}]
    # One driver for both doors: measured, this module carried its own copy of the control-plan
    # guard and its own `astra_runtime.run_goal` call - the same policy and the same call, twice.
    controller, controller_error = live_integrated_brain_v1.drive_controller(task_id, goal, controller_actions)
    if controller_error == "CONTROL_PLAN_INVALID":
        return _fail(task_id, "FAIL__COMPILED_CONTROL_PLAN_INVALID", "LIVE_RUNTIME_COMPOSITION_CONTRACT_INVALID", started, compiler_mode=compiled.get("compiler_mode"))
    if controller_error is not None:
        return _fail(task_id, "FAIL__LIVE_CONTROLLER_EXECUTION", "LIVE_CONTROLLER_EXECUTION_OR_VERIFICATION_FAILURE", started, executed=True,
                     compiled_capability_id=selected or None, compiler_mode=compiled.get("compiler_mode"), reason=controller_error)
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



def _recall_for(goal: str) -> list:
    """What the machine remembers that bears on this goal, before it acts.

    Memory existed but nothing asked it. Every solve re-derived everything from
    keyword overlap, so a lesson learned once changed nothing the next time.
    Consulting is additive: it cannot change what is admitted, only what is
    known -- and memory failures must never break the live path.
    """
    try:
        from canonical.runtime import flywheel_v1 as fly
        return list(fly.relevant(goal, "", k=5) or [])
    except Exception:
        return []


def _credit_recall(rows: list, succeeded: bool) -> None:
    """Tell memory whether what it dredged up was worth dredging up.

    Without this, importance never differentiates: every memory stays at the
    0.5 prior and "what is important" is never learned. This is the only thing
    that separates a memory from a search index.
    """
    try:
        from canonical.runtime import associative_memory_v1 as mem
    except Exception:
        return
    for row in rows:
        try:
            mem.credit(str(row.get("id") or ""), helped=bool(succeeded))
        except Exception:
            continue


COMPOSED_EXECUTOR = "TYPE_LEVEL_COMPOSITION_LOCAL_ADAPTER"


def _try_composed(task_id: str, goal: str, started: int) -> dict[str, Any] | None:
    """Close a goal by chaining capabilities, when no single one matches.

    Returns None when composition cannot reach the goal, so the caller still
    reports the honest gap. Returns a real result only when every step of the
    chain ran and returned.
    """
    try:
        from canonical.runtime import composer_route_v1 as croute
        routed = croute.route(goal)
        if not routed.get("pass"):
            return None
        executed = croute.execute_chain(routed["chain"], goal)
    except Exception:  # noqa: BLE001 - composition must never break routing
        return None
    if not executed.get("pass"):
        return None
    return {
        "schema": LIVE_SCHEMA, "status": "PASS__COMPOSED_CAPABILITY_CHAIN",
        "pass": True, "task_id": task_id, "goal": goal,
        "executed": True, "execution_proof_type": COMPOSED_EXECUTOR,
        "composer_route": {k: routed.get(k) for k in ("token", "chain", "tried")},
        "composer_execution": {k: executed.get(k) for k in
                               ("steps", "produced", "status")},
        "capability_id": (routed["chain"] or [None])[-1],
        "controller": {"executor": COMPOSED_EXECUTOR, "returncode": 0,
                       "controller_mode": "MODEL_INDEPENDENT_ACTION_PLAN",
                       "cognition_dependency_class": "MODEL_INDEPENDENT",
                       "model_dependency_count": 0,
                       "steps_run": len(executed.get("steps") or [])},
        "incremental_spend_usd": 0,
        "elapsed_ns": perf_counter_ns() - started,
    }


def _compiled_capability_ids(compiled: Mapping[str, Any]) -> list[str]:
    """Return every bound capability the compiled route would invoke."""
    found: list[str] = []

    def add(value: Any) -> None:
        cid = str(value or "").strip()
        if cid and cid not in found:
            found.append(cid)

    add(compiled.get("selected_capability"))
    for part in compiled.get("compiled_parts") or []:
        if isinstance(part, Mapping):
            add(part.get("selected_capability"))
    dag = compiled.get("capability_dag")
    if isinstance(dag, Mapping):
        for step in dag.get("steps") or []:
            if isinstance(step, Mapping):
                add(step.get("capability_id"))
    for action in compiled.get("controller_actions") or []:
        if isinstance(action, Mapping):
            args = action.get("args")
            if isinstance(args, Mapping) and action.get("type") in {"invoke_capability", "invoke_verified_bound_capability_adapter"}:
                add(args.get("capability_id"))
    return found


def _missing_compiled_requirements(
    compiled: Mapping[str, Any], registry: Mapping[str, Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """Find unavailable executable prerequisites before any action can run."""
    blocked = []
    for cid in _compiled_capability_ids(compiled):
        entry = registry.get(cid)
        if not isinstance(entry, Mapping):
            continue
        missing = availability.missing(cid, dict(registry))
        if missing:
            blocked.append({"capability_id": cid, "missing_executables": missing})
    return blocked


def solve(request: Mapping[str, Any]) -> dict[str, Any]:
    """THE live Brain entry: compile -> check environment -> admit -> execute -> verify."""
    started = perf_counter_ns()
    task_id = str((request or {}).get("task_id") or "").strip()
    goal = str((request or {}).get("goal") or "").strip()
    if not task_id or not goal:
        return _fail(task_id, "FAIL_CLOSED", "REQUEST_INVALID", started)
    try:
        registry, admissible, compiled = live_integrated_brain_v1.compile_against_live_registry(goal, ROOT)
    except goal_compiler.GoalCompilationFailure as exc:
        # The sentence names no single capability. Before calling that a gap,
        # ask the composer whether a CHAIN of capabilities reaches it: the
        # sentence may describe work no one capability does but several do
        # together. Composition was built and tested and then never called.
        composed = _try_composed(task_id, goal, started)
        if composed is not None:
            return composed
        return _fail(task_id, "FAIL__RAW_GOAL_COMPILATION_GAP", "RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP", started,
                     compiler_code=exc.code, compiler_detail=exc.detail, route_admission=None)
    except Exception as exc:  # pragma: no cover - defensive, mirrors run_raw_goal
        return _fail(task_id, "FAIL_CLOSED", "RAW_GOAL_INTEGRATION_RUNTIME_ERROR", started, reason=type(exc).__name__ + ":" + str(exc))
    unavailable = _missing_compiled_requirements(compiled, admissible)
    if unavailable:
        return _fail(
            task_id,
            "FAIL__CAPABILITY_ENVIRONMENT_PREREQUISITE_MISSING",
            "CAPABILITY_ENVIRONMENT_DEPENDENCY_MISSING",
            started,
            executed=False,
            compiler_mode=compiled.get("compiler_mode"),
            unavailable_capabilities=unavailable,
            model_dependency_count=0,
        )
    normalized = front.normalize_goal(goal)
    future_artifacts = _future_artifacts(normalized)
    # ask memory what it knows about work like this, before deciding anything
    recalled = _recall_for(normalized)
    admission = route_admission(normalized, compiled, admissible)
    admission["front_compiler_rules"] = list((compiled.get("front_compiler") or {}).get("rules_applied") or [])
    if admission.get("admitted") is not True:
        return _fail(task_id, "FAIL_CLOSED__ROUTE_ADMISSION_REJECTED", "ROUTE_ADMISSION_REJECTED:" + str(admission.get("rule")), started,
                     compiled_capability_id=admission.get("selected_capability"), compiler_mode=compiled.get("compiler_mode"), route_admission=admission)
    result = _execute(task_id, goal, compiled, admissible, started)
    result["route_admission"] = admission
    result["memory_recalled"] = [
        {"id": r.get("id"), "content": r.get("content"),
         "relevance": r.get("relevance"), "importance": r.get("importance")}
        for r in recalled
    ]
    # close the loop: what memory offered is judged by what actually happened
    _credit_recall(recalled, bool(result.get("pass")))
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
        # The promised file is not there. That is the only verdict that
        # matters -- and it is also the moment to try something else, rather
        # than reporting a gap while a chain of capabilities could have
        # produced the thing. Composition is tried here, on the evidence.
        composed = _try_composed(task_id, goal, started)
        if composed is not None:
            composed["memory_recalled"] = [
                {"id": r.get("id"), "content": r.get("content"),
                 "relevance": r.get("relevance"), "importance": r.get("importance")}
                for r in recalled]
            composed["route_admission"] = admission
            composed["supersedes"] = {
                "status": result.get("status"),
                "compiled_capability_id": result.get("compiled_capability_id"),
                "promised_artifact_errors": list(missing)}
            return composed
        result["runtime_status_before_artifact_check"] = result.get("status")
        result["status"] = "FAIL_CLOSED__PROMISED_ARTIFACT_MISSING"
        result["pass"] = False
        result["failure_class"] = "PROMISED_ARTIFACT_MISSING"
        result["promised_artifact_errors"] = missing
    result["elapsed_ns"] = perf_counter_ns() - started
    return result


# ------------------------------------------------------------------ learn on failure

_LEARNABLE_STATUSES = frozenset({
    "FAIL__RAW_GOAL_COMPILATION_GAP",
})


def _is_executable(name: str) -> bool:
    """Does this program exist on this machine? Checked, never assumed."""
    import shutil
    from pathlib import Path
    try:
        return bool(Path(name).is_file() or shutil.which(name))
    except Exception:
        return False


def _named_executable(goal: str) -> str:
    """A program the goal actually names, that exists on this machine.

    Only this is acquirable by running it. Inventing an executable that is not
    there would be guessing, and the machine does not guess -- it checks.
    """
    import shutil
    from pathlib import Path
    for tok in str(goal or "").replace(",", " ").replace(";", " ").split():
        t = tok.strip(".,()[]{}\"'")
        if len(t) < 2 or "/" in t:
            continue
        if Path(t).is_file() or shutil.which(t):
            return t
    return ""


def solve_or_learn(request: Mapping[str, Any], *, learn: bool = True,
                   registry_path: str | None = None) -> dict[str, Any]:
    """Try it; if the machine cannot, let that be the signal to learn how.

    solve() answers "can I do this". When the answer is no, the interesting
    question is what happens next. A strict program reports the failure and
    stops, and will report the same failure forever. A creature treats
    "I cannot" as the most precise information it has about what it lacks:

      1. it records the gap, so it now KNOWS it has a hole here -- and the
         ledger ranks that hole against every other thing it does not know;
      2. if the goal names a program that exists, it learns to drive that
         program (by reading its help, or failing that by trying it);
      3. if that produced something verified, it registers it and RETRIES.

    solve() itself is untouched, so the measured path cannot move.
    """
    result = solve(request)
    if not learn:
        return result
    if str(result.get("status") or "") not in _LEARNABLE_STATUSES:
        return result

    goal = str((request or {}).get("goal") or "").strip()
    learned: dict[str, Any] = {"attempted": False, "gap_recorded": False}

    try:
        from canonical.runtime import ignorance_ledger_v1 as led
        gap_id = led.note(goal or "unmatched goal",
                          why="raw goal compilation gap", cost=1.0)
        learned["gap_recorded"] = True
        learned["gap_id"] = gap_id
        learned["what_to_learn_next"] = [g["what"] for g in led.rank(limit=3)]
    except Exception:
        pass

    # JIT KNOWLEDGE. The goal named nothing the machine can run, so before
    # concluding anything it asks the outside world what exists for this job.
    # A gap is not the end of the road -- it is the question.
    try:
        from canonical.runtime import jit_knowledge_v1 as jit
        known = jit.resolve(goal, min_sources=1, limit=6, timeout=8)
        # Asking the world a badly-phrased question and then concluding the
        # world has nothing to say is the oldest way to be wrong. A goal like
        # "write the text hello to out.txt" is an instruction, not a query:
        # asked verbatim, github returns nothing at all. Rephrase and ask
        # again before believing the silence.
        if not known.get("complete"):
            try:
                from canonical.runtime.curriculum_v1 import query_for
                rephrased = query_for(goal)
                if rephrased and rephrased != goal:
                    again = jit.resolve(rephrased, min_sources=1, limit=6,
                                        timeout=8)
                    if (again.get("complete")
                            or again.get("document_count", 0)
                            > known.get("document_count", 0)):
                        known = again
                        known["query_was_rephrased_to"] = rephrased
            except Exception:
                pass
        learned["knowledge"] = {
            "status": known.get("status"),
            "documents": known.get("document_count", 0),
            "sources_answered": known.get("sources_answered") or [],
            # a summary that drops the KINDS cannot explain its own refusal:
            # it says "incomplete" without being able to say that three
            # registries agreed because they are all registries
            "kinds_answered": known.get("kinds_answered") or [],
            "min_kinds_required": known.get("min_kinds_required"),
            "gap": known.get("gap"),
            "query_was_rephrased_to": known.get("query_was_rephrased_to"),
            "complete": known.get("complete", False),
            "authority": known.get("authority"),
        }
        # knowledge that names a program is only useful if that program is
        # actually HERE -- the machine does not install, and does not invent.
        candidates: list[str] = []
        for doc in (known.get("documents") or []):
            for text in (str(doc.get("id") or ""), str(doc.get("title") or "")):
                head = text.strip().split()[0] if text.strip() else ""
                head = head.strip(".,()[]{}'\"")
                if 2 <= len(head) <= 40 and _is_executable(head):
                    candidates.append(head)
        if candidates:
            learned["knowledge"]["candidates_present"] = candidates[:6]
            if not _named_executable(goal):
                exe_guess = candidates[0]
                learned.setdefault("from_knowledge", exe_guess)
    except Exception as exc:
        learned.setdefault("knowledge", {"error": type(exc).__name__ + ":" + str(exc)[:160]})

    exe = _named_executable(goal)
    if not exe:
        # nothing the goal named -- but knowledge may have named something real
        exe = str(learned.get("from_knowledge") or "")
        if exe:
            learned["attempted"] = True
            learned["executable"] = exe
            learned["executable_source"] = "jit_knowledge"
    if exe:
        learned["attempted"] = True
        learned["executable"] = exe
        try:
            from canonical.runtime import cli_capability_acquisition_v1 as acq
            import subprocess, tempfile, json as _json
            with tempfile.TemporaryDirectory(prefix="brain-learn-") as td:
                out = subprocess.run([exe, "--help"], capture_output=True,
                                     timeout=30, cwd=td)
                text = (out.stdout + out.stderr).decode("utf-8", "replace")
            probe_doc = {"executables": [{"executable": exe,
                                          "help_attempts": [{"text": text}]}]}
            acquired = acq.acquire(probe_doc, goal)
            learned["acquisition_status"] = acquired.get("status")
            if acquired.get("verified"):
                cid = "acquired." + exe.replace(".", "_")
                reg = acq.register(acquired, cid,
                                  registry_path=registry_path)
                learned["registered"] = reg.get("registered") is True
                learned["capability_id"] = cid
                if learned["registered"]:
                    # it can do something now that it could not before
                    retry = solve(request)
                    retry["learning"] = learned
                    retry["learned_this_turn"] = True
                    return retry
        except Exception as exc:
            learned["error"] = type(exc).__name__ + ":" + str(exc)[:200]

    result["learning"] = learned
    result["learned_this_turn"] = False
    return result
