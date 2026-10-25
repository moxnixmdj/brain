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

import hashlib
import pathlib
import re
import importlib.util
import sys
from copy import deepcopy
from time import perf_counter_ns
from typing import Any, Mapping

from canonical.runtime import astra_runtime, goal_compiler
from canonical.runtime import composer_route_v1 as composer_route
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


_FILE_TOKEN = re.compile(r"[\w.~-]+\.[A-Za-z0-9]{1,8}|/[\w./~-]+|~[\w./~-]+")


def _goal_names_a_file(goal: str) -> bool:
    """True when the sentence contains anything that could name a file or a path.

    Deliberately generous: a dotted token, an absolute path, or a home-relative path all count, so
    this only returns False for a request that mentions no file at all. Being generous is the safe
    direction - a false negative here refuses a goal that could have run.
    """
    return bool(_FILE_TOKEN.search(str(goal or "")))


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
    # The same verdict read the other way.  `admit` had only ever been allowed to
    # GRANT admission; when it refused, its reason was thrown away and the route
    # fell through to a lexical rule that could not see it.  So a capability whose
    # declared input the sentence could never supply was still the selected route,
    # and the refusal that reached the caller named a weak-evidence rule instead of
    # the real one.  Recorded here so the caller can tell "this capability could
    # not be bound to this sentence" from "this sentence is thin evidence".
    if isinstance(typed, Mapping) and str(typed.get("reason") or "").startswith("BINDING_REFUSED:"):
        base["typed_binding_refused"] = True
        base["typed_binding_reason"] = typed.get("reason")
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
    # R9: a capability that consumes a FILE cannot run on a request that names no file.  Measured:
    # `extract text from a pdf file` selected pdf.extract.text.pypdf, whose only declared input is
    # pdf_path, with goal_future_artifacts empty and no path token anywhere in the sentence - and
    # this layer admitted it, so the front reported
    # PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED while writing zero files.
    # The same capability, given a path that does not exist, already refuses with
    # GOAL_INPUT_BINDING_REQUIRED.  Supplying LESS information was being treated as MORE
    # admissible, which is backwards: an unbindable path fails, so no path at all must fail too.
    # Only a FILE input is checked, and only when nothing in the request could ever name one, so a
    # capability whose inputs are text or numbers is untouched.
    # An OUTPUT is not a file the capability consumes.  Where a result lands is
    # ours to choose, so counting output_path/result_path here made R9 refuse a
    # capability for missing a file it never needed to be given -- measured on
    # 3b9e6a0d, all five of the remaining opaque refusals over the 72 verified
    # capabilities named in prose reported `output_path` as the unbound input,
    # which is a diagnosis pointing the caller at the one thing they were never
    # supposed to supply.
    _owned_outputs = ("output_path", "result_path")
    file_inputs = sorted(k for k in input_keys
                         if (k.endswith("_path") or k.endswith("_file") or k in ("path", "file"))
                         and k not in _owned_outputs
                         and not k.endswith("_output_path")
                         and not k.endswith("_result_path"))
    if file_inputs and not futures and not _goal_names_a_file(goal):
        return {**base, "admitted": False, "rule": "R9_REQUIRED_FILE_INPUT_UNBOUND",
                "unbound_file_inputs": file_inputs}
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


# Every field that has ever carried the reason a result failed, most specific
# first.  Which one is populated depends on which layer refused.
FAILURE_REASON_FIELDS = ("compiler_detail", "reason", "tool_truth_errors", "blocker")


def failure_reason(result: Mapping[str, Any]) -> str:
    """The one answer to "why did this fail", whatever shape the result has.

    The diagnosis lives in a different field depending on which layer refused:
    the compiler boundary writes `compiler_detail`, the controller writes
    `reason`, the truth check writes `tool_truth_errors`.  Measured on bcb5661a
    over the 72 verified capabilities named in prose, all 70 failures carried a
    diagnosis -- but reading only `compiler_detail` made 4 of them look silent
    when they were in fact reporting BOUND_APT_METADATA_NOT_FOUND in `reason`.

    A caller that must first work out which layer refused in order to read the
    reason will eventually read the wrong one, and a failure that is fully
    diagnosed will look like a failure with no cause at all.  So there is one
    accessor, and it never returns empty for a result that failed.
    """
    if not isinstance(result, Mapping):
        return ""
    for field in FAILURE_REASON_FIELDS:
        value = result.get(field)
        if value is None or value == "" or value == [] or value == {}:
            continue
        if isinstance(value, (list, tuple)):
            value = "; ".join(str(item) for item in value if str(item).strip())
        text = str(value).strip()
        if text:
            return _with_tool_own_reason(text, result)
    return str(result.get("failure_class") or result.get("status") or "")


def _with_tool_own_reason(text: str, result: Mapping[str, Any]) -> str:
    """Attach the tool's own explanation to a truth-check refusal.

    `TOOL_REPORTED_PASS_FALSE:<cid>` says a capability ran and said "no" but not
    why.  The why is in that capability's own result (`reason`), which the truth
    check reads only to decide pass/fail and then discards.  Measured on cc3bd40
    across all 367 admissible capabilities, 74 failures were reported this way,
    and the tools had already named their cause in every case where they had one:
    CONTEXT_ID_REQUIRED (13), V3_INPUT_REQUIRED (10), PREDICATE_ALIAS_REQUIRED (5),
    OBJECTIVE_REQUIRED (4), INPUT_SCHEMA_INVALID (4), OBLIGATION_ID_REQUIRED (3),
    TEXT_REQUIRED (1), PROMPT_REQUIRED (1).  The same 74 all declare zero input
    roles in their action_template, so the capability is structurally unservable --
    no goal wording can supply an input the registry never declared.  That is a
    different fact from "the tool judged the answer wrong", and this accessor is
    the only place a caller can see either.  Appending rather than replacing keeps
    every existing consumer of the prefix working.
    """
    if not text.startswith(("TOOL_REPORTED_PASS_FALSE:", "TOOL_REPORTED_NON_SUCCESS_STATUS:")):
        return text
    for row in list(result.get("execution") or []) + list((result.get("controller_execution") or {}).get("trace") or []):
        if not isinstance(row, Mapping):
            continue
        inner = row.get("result") if isinstance(row.get("result"), Mapping) else {}
        cause = inner.get("reason")
        if isinstance(cause, str) and cause.strip():
            return text + ":" + cause.strip()[:64]
    return text


# An uncaught programming error inside a bound-capability adapter, as opposed to a
# refusal the adapter raised on purpose.  Measured on d1ad8da across the 72 verified
# capabilities with nine hostile-but-valid fixtures (392 clean outcomes), exactly
# one site crashes: evidence_decision_verify.py:101, reachable as
# decision.synthesis.verify.stdlib, given a document whose top level is a list,
# null or a number.  That file cannot be repaired in place -- its exact bytes are
# pinned as the capability's verifier_git_blob -- and neither can the single
# invocation site in astra_runtime.py, pinned as subject.astra_runtime.git_blob_sha.
# So the defect cannot be removed here; the least that is true is that it must be
# LABELLED as a defect.  Today it is reported as
# LIVE_CONTROLLER_EXECUTION_OR_VERIFICATION_FAILURE, the same class as a correct
# refusal, which means a caller and the learning loop cannot tell "the adapter
# refused, correctly" from "the adapter is broken" -- and those need opposite
# responses.  The marker requires the type name followed by a colon, because a
# bare substring could appear inside an ordinary path or message.
_ADAPTER_FAULT_RE = re.compile(
    r"\b(AttributeError|TypeError|KeyError|IndexError|UnboundLocalError|NameError)\b\s*:")

_ENVIRONMENT_MARKERS = (
    "NOT_FOUND", "NOT_INSTALLED", "APT_METADATA", "INSTALL_FAILED",
    "ModuleNotFoundError", "No module named",
)
# A named error in this codebase has a recognisable SHAPE, not a recognisable word:
# "RuntimeError:JSON_DOCX_SPEC_UNRESOLVED", "TOOL_REPORTED_PASS_FALSE:...",
# "web.browser.rendered.capture.chromedriver:0", "FileNotFoundError:[Errno 2] ...".
# Enumerating the names cannot work -- the adapters raise RuntimeError at 355 sites
# and ValueError at 72 -- and a marker list measured 17 of 60 failures as UNKNOWN
# that were in fact perfectly well named.  So the test is the shape: an identifier
# followed by a colon, or an UPPER_SNAKE token.
_NAMED_ERROR_RE = re.compile(
    r"(?:^[A-Za-z_][A-Za-z0-9_.]*\d*\s*:)|(?:\b[A-Z][A-Z0-9_]{3,}\b)")

FAILURE_KIND_ADAPTER_FAULT = "ADAPTER_FAULT"
FAILURE_KIND_ENVIRONMENT = "ENVIRONMENT_BLOCKER"
FAILURE_KIND_CONTRACT = "CONTRACT_REFUSAL"
FAILURE_KIND_UNKNOWN = "UNKNOWN"


def failure_kind(result: Mapping[str, Any]) -> str:
    """What KIND of failure this is, so a defect is never mistaken for a refusal.

    ``failure_reason`` answers *why*; this answers *whose fault it is*, and the two
    are not the same thing.  A refusal means the system behaved correctly and the
    request was under-specified or the machine lacks a dependency; an adapter fault
    means the system has a bug.  Treating them alike is how a real defect hides
    inside a wall of legitimate refusals.
    """
    reason = failure_reason(result)
    if not reason:
        return FAILURE_KIND_UNKNOWN
    if _ADAPTER_FAULT_RE.search(reason):
        return FAILURE_KIND_ADAPTER_FAULT
    if any(marker in reason for marker in _ENVIRONMENT_MARKERS):
        return FAILURE_KIND_ENVIRONMENT
    if _NAMED_ERROR_RE.search(reason):
        return FAILURE_KIND_CONTRACT
    return FAILURE_KIND_UNKNOWN


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
    """True when this entry carries a source type THIS ENTRY executes locally rather than delegating.

    Historically these were exactly the types the pinned kernel refused with
    BOUND_CAPABILITY_SOURCE_UNSUPPORTED, and E1 below was written as the bridge over that gap.  The
    kernel now resolves all five of them itself (see ``astra_runtime.LOCAL_SOURCE_BASE_TYPE``), so
    this predicate no longer describes a kernel limitation -- it names the set this entry keeps on
    its own pinned, measured local path.  Kept deliberately: E1's local execution is the path the
    29/29 family measurement was taken on, and moving these to the kernel is a separate, separately
    measured decision.  ``astra_runtime.LOCAL_SOURCE_BASE_TYPE`` is the authority on what the
    kernel supports; this set is the authority on what this entry runs itself.
    """
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
    # The controller writes its trace rows as {"cycle", "plan", "result"} and closes the
    # trace with a row whose result.type is "finish" (astra_runtime.py:6795 and :6844).
    # This path wrote the same information under the key "action" and never closed the
    # trace, so the one consumer of a trace -- raw_goal_trace_acceptance_v1, which reads
    # row["plan"] at :164 and :181 and requires a finish row -- saw an empty trace:
    #
    #     _action_rows(trace)       -> 0      (reads "plan"; the row had "action")
    #     _trace_is_finished(trace) -> False  (no row carried result.type == "finish")
    #
    # Measured on 82c30fd over all 367 admissible capabilities named in prose: 223 pass,
    # and 222 of those 223 produced a trace the acceptance verifier could not read.  So
    # the only verdict it could ever return was TRACE_HAS_NO_CAPABILITY_ACTIONS, which
    # was untrue -- there was exactly one capability action.
    #
    # Nothing here is invented.  The capability really was the planned action, it really
    # ran, and run_adapter_locally verified its declared expectation before this line.
    # "action" is kept alongside "plan" so a reader of the old key is unaffected.
    _summary = "%s executed by the front layer local adapter and its declared expectation verified" % selected
    _trace = [
        {"cycle": 0, "plan": dict(action), "action": dict(action), "result": dict(tool_result)},
        {"cycle": 1, "phase": "front_layer_local_finalization",
         "plan": {"type": "finish", "args": {"summary": _summary},
                  "why": "front layer local adapter executed and its declared expectation verified"},
         "result": {"type": "finish", "summary": _summary}},
    ]
    row = {"capability_id": selected, "pass": True, "status": "PASS__FRONT_LAYER_LOCAL_ADAPTER_ACTION", "result": dict(tool_result),
           "execution_proof_type": LOCAL_EXECUTION_PROOF, "controller_plan_sha256": None, "controller_trace": _trace}
    out = {
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
        "routing_success_authority": False,
        "elapsed_ns": perf_counter_ns() - started, "incremental_spend_usd": 0, "benchmark_specific": False, "terminal_credit_delta": 0,
    }
    out.update(_exact_acceptance(goal, compiled, _trace, raw_contract))
    if out["semantic_acceptance_complete"]:
        out["status"] = "PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED"
    return out


def _exact_acceptance(goal: str, compiled: Mapping[str, Any], trace: Any,
                      raw_contract: Mapping[str, Any]) -> dict[str, Any]:
    """Ask the real acceptance verifier, and report what it says.

    This path hard-coded ``semantic_acceptance_complete: False`` and
    ``accepted_raw_obligation_ids: []`` and never called the verifier, so a
    front-layer execution reported itself provisional with no reason at all -- all
    223 passes measured on 82c30fd carried no acceptance verdict.

    The verdict is not decided here.  ``raw_goal_trace_acceptance_v1.verify``
    re-opens every artifact from disk, recomputes its digest and requires every
    obligation the goal stated to be met.  This only hands it the execution and
    reports the answer, so a provisional pass now says WHY it is provisional.
    Measured, that answer is NO_INDEPENDENT_REINSPECTION_FOR:<path> for every one of
    them: these executions print to stdout and leave no artifact to re-inspect, so
    the refusal is correct and this change does not upgrade a single pass class.
    """
    base: dict[str, Any] = {"semantic_acceptance_complete": False, "accepted_raw_obligation_ids": []}
    try:
        from canonical.runtime.raw_goal_trace_acceptance_v1 import verify as _verify_trace
    except Exception:  # noqa: BLE001 - without the verifier the answer stays provisional
        return base
    try:
        acceptance = _verify_trace(goal=goal, compiled_plan=compiled, execution=trace,
                                   raw_contract=raw_contract,
                                   root=pathlib.Path(__file__).resolve().parents[2])
    except Exception:  # noqa: BLE001 - a verifier fault must not turn a pass into a crash
        return base
    if not isinstance(acceptance, Mapping):
        return base
    accepted = [str(x) for x in (acceptance.get("accepted_obligation_ids") or [])]
    obligations = ((raw_contract.get("acceptance_contract") or {}).get("obligations") or [])
    complete = (acceptance.get("semantic_acceptance_complete") is True
                and len(accepted) == len(obligations) and len(obligations) > 0)
    return {"semantic_acceptance_complete": complete, "accepted_raw_obligation_ids": accepted,
            "raw_goal_acceptance": dict(acceptance)}


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
    out = {
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
        "routing_success_authority": False,
        "elapsed_ns": perf_counter_ns() - started, "incremental_spend_usd": 0, "benchmark_specific": False, "terminal_credit_delta": 0,
    }
    if passed:
        # Same defect as the front-layer path fixed in PR #6111, on its sibling: the
        # verdict was hard-coded and the verifier was never asked.  The difference is
        # that this trace already carries the controller's canonical shape, so nothing
        # about it needs repairing -- only asking.  Measured on bf2799b: two
        # capabilities (auto.npm.dfinity-cbor, auto.npm.msgpack-msgpack) pass here,
        # write the artifact they promised, declare 3 obligations, accept 0, and carry
        # no acceptance verdict at all.
        out.update(_exact_acceptance(goal, compiled, trace, raw_contract))
        if out["semantic_acceptance_complete"]:
            out["status"] = "PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED"
    return out


def promised_artifact_errors(goal: str, future_artifacts: list[str]) -> list[str]:
    """R6: every output file the goal named must now exist.

    It must also be non-empty -- but only when the sentence promised content.  The
    non-empty clause exists to catch a producer that writes nothing and reports
    success, so it is only evidence of failure when there was something to write.
    Measured: "Run the shell command touch X" creates X correctly as 0 bytes --
    an empty file IS the stated result -- and was refused with
    PROMISED_ARTIFACT_EMPTY:X.  The rule was measuring a promise the sentence
    never made.  composer_route_v1.extract_content already answers "what text did
    this sentence state" and is reused here rather than a second rule being
    invented; when it returns nothing, existence is the whole of the claim.

    A guard must be scoped to the claim the sentence actually makes.
    """
    states_content = composer_route.extract_content(goal) is not None
    errors = []
    for raw in future_artifacts:
        p = ROOT / raw
        if not p.is_file():
            errors.append("PROMISED_ARTIFACT_MISSING:" + raw)
        elif states_content and p.stat().st_size == 0:
            errors.append("PROMISED_ARTIFACT_EMPTY:" + raw)
    return errors


def promised_artifact_class(errors: list[str]) -> str:
    """Name the error that actually fired, not a constant.

    Measured: a 0-byte artifact the sentence never asked to be non-empty was
    reported to the caller as PROMISED_ARTIFACT_MISSING while the file sat on
    disk -- the refusal named a reason its own evidence list contradicted.
    """
    if not errors:
        return "PROMISED_ARTIFACT_MISSING"
    return str(errors[0]).split(":", 1)[0]



_REPAIR_VERB_RE = re.compile(r"\b(?:repair|fix|patch|correct)\b", re.IGNORECASE)


def _promised_source_files(goal: str) -> list[str]:
    """Source files the goal asked to have CHANGED, not merely read.

    "Repair the python source file X" promises X is different afterwards.  Reading
    X promises nothing about its bytes, so only a goal carrying a repair verb
    counts, and only files that already exist -- a file the goal asks to create is
    a promised artifact, which R6 already covers.
    """
    text = str(goal or "")
    candidates = [(raw, path) for raw, path in goal_compiler._repo_paths(goal, ROOT)
                  if path.is_file() and path.suffix.lower() == ".py"]
    if not candidates:
        return []
    # Only the file the repair verb governs.  "Repair the source file X so that
    # the test Y passes" names Y as the WITNESS; demanding Y change too would
    # fail a goal that did exactly what it said.  So take the nearest source file
    # after each repair verb, not every source file in the sentence.
    out = []
    for m in _REPAIR_VERB_RE.finditer(text):
        best = None
        best_at = None
        for raw, path in candidates:
            for spelling in (raw, str(path)):
                at = text.find(spelling, m.end())
                if at >= 0 and (best_at is None or at < best_at):
                    best_at = at
                    best = raw
        if best is not None and best not in out:
            out.append(best)
    return out


def _source_digest(raw: str) -> str:
    try:
        return hashlib.sha256((ROOT / raw).read_bytes()).hexdigest()
    except Exception:  # noqa: BLE001 - unreadable is its own error, reported below
        return ""


def promised_source_change_errors(goal: str, before: Mapping[str, str]) -> list[str]:
    """Every source file the goal asked to repair must actually be different now.

    The repair loops find a patch, verify it, replay the verification, then restore
    the source, declaring NO_SOURCE_WRITE_OR_PROMOTION_AUTHORITY.  That is the right
    boundary for a capability to hold -- but the front door was reporting PASS for a
    file that is still broken.  That is the over-claim R6 exists to stop, one layer
    down: the goal promised a change and no change happened.
    """
    errors = []
    for raw, digest in (before or {}).items():
        now = _source_digest(raw)
        if not now:
            errors.append("PROMISED_SOURCE_UNREADABLE:" + raw)
        elif now == digest:
            errors.append("PROMISED_SOURCE_UNCHANGED:" + raw)
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


def _composed_holds_up(composed: dict[str, Any], goal: str, future_artifacts: list[str]) -> dict[str, Any]:
    """A fallback must be held to the same evidence as the path it replaces.

    Composition is attempted at exactly two moments, and both of them are
    moments where the primary path has already failed: the sentence named no
    single capability, or it named a capability whose promised file never
    appeared.  Both call sites returned the chain's own verdict untouched, so a
    chain that declared success was believed without looking at the disk.

    Measured: "Write the text 'hello patch' to the file X and save the report to
    Y" returned status PASS__COMPOSED_CAPABILITY_CHAIN, pass=True, having written
    those 11 bytes into Y.  X -- the file the goal actually named -- was never
    created, and the front door reported the goal done.  The gate that catches
    this already existed and already ran; its result was simply discarded on the
    way out.
    """
    still = promised_artifact_errors(goal, future_artifacts)
    if not still:
        return composed
    composed["composer_status_before_artifact_check"] = composed.get("status")
    cls = promised_artifact_class(still)
    composed["status"] = "FAIL_CLOSED__" + cls
    composed["pass"] = False
    composed["failure_class"] = cls
    composed["promised_artifact_errors"] = still
    composed["composer_ran_but_left_the_artifact_missing"] = True
    return composed


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
        # The chain ALREADY RAN.  execute_chain does not roll back, so returning
        # None here throws away the only record that work happened and lets the
        # caller report FAIL__RAW_GOAL_COMPILATION_GAP -- "I could not turn this
        # into an executable contract" -- about a command that executed and
        # changed the repository.
        #
        # Measured on b364795: "Run the shell command rm A" deleted A and was
        # then reported as a compilation gap.  The report denied a side effect
        # that had already happened, which is the one direction a false report
        # must never go.
        #
        # Scoped to the claim this record can actually make: a step is only
        # reported as having run when it carries a result.  A chain that failed
        # before reaching any command still returns None, so the caller keeps
        # reporting the honest gap rather than claiming work that never started.
        #
        # pass stays False.  This is not acceptance -- it is a truthful account
        # of work that ran and could not be certified.
        steps = executed.get("steps") or []
        dispatched = [st for st in steps
                      if isinstance(st, Mapping)
                      and (st.get("adapter_raised") is not None
                           or st.get("result") is not None)]
        if not dispatched:
            return None
        return {
            "schema": LIVE_SCHEMA,
            "status": "FAIL_CLOSED__COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN",
            "pass": False, "task_id": task_id, "goal": goal,
            "executed": True, "execution_proof_type": COMPOSED_EXECUTOR,
            "failure_class": "STEP_RAISED_OUTCOME_UNKNOWN",
            "steps_dispatched": len(dispatched),
            "adapter_raised": [st.get("adapter_raised") for st in dispatched
                               if st.get("adapter_raised")],
            "composer_route": {k: routed.get(k) for k in ("token", "chain", "tried")},
            "composer_execution": {k: executed.get(k) for k in
                                   ("steps", "produced", "status")},
            "capability_id": (routed["chain"] or [None])[-1],
            "elapsed_ns": perf_counter_ns() - started,
        }
    out = {
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
    # The third and last path that never asked.  The front-layer local adapter
    # path was fixed in PR #6111 and the model-independent controller path in
    # #6112; this one is where a NATURAL sentence lands -- "Write the text X to
    # the file Y", which names no capability, so no single one matches and the
    # composer answers instead.  It reported pass=True on the strength of the
    # chain having run, with no acceptance verdict of any kind, so the route
    # ordinary requests take was the one route that was never checked.
    #
    # It could not be checked before, for two concrete reasons, both now gone:
    # the step records were {"raw": null} so there was no evidence to inspect
    # (fixed in PR #6115), and no acceptance contract was ever built here.  The
    # contract is derived from the sentence alone by compile_contract, and the
    # only thing it needs that the sentence does not supply is the set of files
    # the request touches -- which the chain now reports, because each step's
    # own args are recorded.
    out.update(_composed_acceptance(goal, routed.get("chain") or [], executed))
    if out.get("semantic_acceptance_complete"):
        out["status"] = "PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED"
        return out
    # The verifier spoke and said no.  A composed chain claimed pass=True on the
    # strength of having run, and the verdict sitting beside it was never read --
    # so the one route ordinary sentences take was the one route that could report
    # success over its own verifier's refusal.  Measured on a8d35d7: `tee` wrote
    # its file, solve() said pass=True, and raw_goal_acceptance said pass=False
    # with COMMAND_NOT_RE_RUNNABLE_WITHOUT_SIDE_EFFECTS.  A report that outranks
    # the check meant to catch it is not a report.
    #
    # Scoped to an explicit False.  When there is no verdict at all -- a goal no
    # acceptance path covers -- nothing changes, because turning an absence of
    # evidence into a refusal is a different decision and is not this one.
    verdict = out.get("raw_goal_acceptance")
    if out.get("pass") is True and isinstance(verdict, Mapping) and verdict.get("pass") is False:
        out["status"] = "FAIL_CLOSED__COMPOSED_CHAIN_NOT_VERIFIED"
        out["pass"] = False
        out["failure_class"] = "COMPOSED_CHAIN_NOT_VERIFIED"
        out["unverified_reason"] = verdict.get("reason")
    return out


def _composed_acceptance(goal: str, chain: Any, executed: Mapping[str, Any]) -> dict[str, Any]:
    """Ask the acceptance verifier about a composed chain, and report the answer.

    Three things have to be handed over in the shape the verifier reads, none of
    which the composer produces on its own:

      * an acceptance contract.  ``compile_contract`` derives one from the
        sentence, but refuses with ROUTING_TARGET_EFFECTS_EMPTY unless it is
        told which files the request touches.  Measured: the same sentence gives
        0 obligations with an empty effect set and 2 with the step's own
        output_path, so the effects are taken from the steps the chain actually
        ran -- not guessed, and not widened to anything the chain did not write.
      * a trace in the canonical row shape.  The verifier reads each row's
        ``plan.args`` and requires a trailing ``finish`` row; the composer emits
        ``index``/``capability_id``/``args``/``result`` and no finish row.
      * a plan whose chain matches what ran, or the verifier refuses with
        COMPILED_PLAN_HAS_NO_SELECTED_CAPABILITY before it inspects anything.

    A verifier fault must never turn a pass into a crash, and must never turn a
    pass into a failure either: the honest fallback is the provisional verdict
    this path already gave, now carrying the reason.
    """
    base: dict[str, Any] = {"semantic_acceptance_complete": False,
                            "accepted_raw_obligation_ids": []}
    steps = [row for row in (executed.get("steps") or []) if isinstance(row, Mapping)]
    if not steps:
        return base
    trace: list[dict[str, Any]] = []
    effects: list[str] = []
    for row in steps:
        args = dict(row.get("args") or {})
        args.setdefault("capability_id", str(row.get("capability_id") or ""))
        trace.append({"plan": {"args": args},
                      "result": dict(row.get("result") or {})})
        for key in ("output_path", "result_path"):
            value = args.get(key)
            if isinstance(value, str) and value.strip() and value not in effects:
                effects.append(value)
    if not effects:
        # Nothing the chain wrote, so there is no effect to accept against and
        # compile_contract would refuse on an empty set anyway.
        return base
    trace.append({"plan": {"args": {}}, "result": {"type": "finish"}})
    try:
        raw_contract = compile_contract(goal, source_id="user",
                                        routing_target_effects=effects)
    except Exception:  # noqa: BLE001 - a contract fault leaves the verdict provisional
        return base
    plan = {"compiled_parts": [{"selected_capability": str(cid)} for cid in chain]}
    return _exact_acceptance(goal, plan, trace, raw_contract)


def solve(request: Mapping[str, Any]) -> dict[str, Any]:
    """THE live Brain entry: front-compile -> admit -> execute -> tool truth -> promised artifacts."""
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
        # The chain may still have missed the file the sentence named.  The
        # artifact list is derived here for the same reason it is derived
        # below: it comes from the sentence, not from the capability.
        #
        # It is read BEFORE the chain runs, which is the only order in which it
        # means anything.  _future_artifacts answers "which paths does this
        # sentence name that do not exist YET", and "yet" means before the work.
        # It was being evaluated as an argument to _composed_holds_up, so it ran
        # after _try_composed had already executed the chain -- and a file the
        # work legitimately removed came back as a promise the chain had failed
        # to keep.  Measured on 6411cf6: "Run the shell command mv A B" moved A
        # to B correctly, and was then refused with
        # PROMISED_ARTIFACT_MISSING:A, naming the source the sentence asked to
        # have gone.  The main path below has always read this list before
        # _execute; this branch did not.
        gap_normalized = front.normalize_goal(goal)
        gap_future_artifacts = _future_artifacts(gap_normalized)
        composed = _try_composed(task_id, goal, started)
        if composed is not None:
            return _composed_holds_up(composed, gap_normalized,
                                      gap_future_artifacts)
        return _fail(task_id, "FAIL__RAW_GOAL_COMPILATION_GAP", "RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP", started,
                     compiler_code=exc.code, compiler_detail=exc.detail, route_admission=None)
    except Exception as exc:  # pragma: no cover - defensive, mirrors run_raw_goal
        return _fail(task_id, "FAIL_CLOSED", "RAW_GOAL_INTEGRATION_RUNTIME_ERROR", started, reason=type(exc).__name__ + ":" + str(exc))
    normalized = front.normalize_goal(goal)
    future_artifacts = _future_artifacts(normalized)
    # ask memory what it knows about work like this, before deciding anything
    recalled = _recall_for(normalized)
    admission = route_admission(normalized, compiled, admissible)
    admission["front_compiler_rules"] = list((compiled.get("front_compiler") or {}).get("rules_applied") or [])
    if admission.get("admitted") is not True:
        # Name the capability and what it is missing, in the same language the
        # compiler boundary uses.  The rule already computed both -- R9 returns
        # `unbound_file_inputs` and the base carries `selected_capability` -- but
        # the message carried neither, so measured on 3b9e6a0d five of the six
        # remaining opaque refusals over the 72 verified capabilities named in
        # prose were `ROUTE_ADMISSION_REJECTED:R9_REQUIRED_FILE_INPUT_UNBOUND`
        # with no capability and no input in it.  A refusal the caller cannot
        # read is a refusal they cannot close.
        _rejected = admission.get("selected_capability")
        _unbound = admission.get("unbound_file_inputs") or []
        _detail = None
        if _rejected:
            _detail = "%s:contract_not_stated:%s" % (_rejected, ",".join(_unbound)) \
                if _unbound else "%s:not_admitted:%s" % (_rejected, admission.get("rule"))
        _extra: dict[str, Any] = {
            "compiled_capability_id": _rejected,
            "compiler_mode": compiled.get("compiler_mode"),
            "route_admission": admission,
        }
        if _detail is not None:
            _extra["compiler_detail"] = _detail
            _extra["compiler_code"] = "GOAL_INPUT_BINDING_REQUIRED"
        # A route refused because the SELECTED capability could not be bound to
        # this sentence is not a dead end -- the sentence may still be servable by
        # a chain, and the chain is held to the same evidence by _composed_holds_up.
        #
        # Measured on b018600: "Write the text 'hello patch' to the file out.txt
        # and save the report to out.txt.done.json" selected
        # document.convert.markdown_pdf.pandoc_weasyprint on the single word
        # "report", whose own binder said
        # BINDING_REFUSED:markdown_path:0_type_compatible_existing_files_named.
        # The route was refused R3_WEAK_EVIDENCE and nothing was written, although
        # the sentence is an ordinary write that composition serves.  With the
        # chain tried, the report is written, the file the sentence named is not,
        # and the gate names exactly that file -- which is the truthful answer.
        #
        # Scoped to the one case the binder actually refuted.  A thin-evidence
        # refusal with no binding verdict still fails closed exactly as before.
        # And only when the sentence states WHAT to write.  Measured while
        # building this: opening the fallthrough on every binding refusal let
        # "Check the file X" -- a request that names a file and states no text --
        # reach composition, where PATH_OUTPUT binds the only path in the sentence
        # and the chain overwrote the file with a JSON report, reporting pass=True.
        # That is the data-destruction class closed in PR #6119, reopened.  A
        # sentence that states no content has nothing to compose into a write, so
        # it keeps failing closed exactly as it did before.
        # The same gate widened to the other thing a sentence can state.  A
        # command line is grounded content in exactly the sense a payload is: it
        # is something the request actually says, token for token, and the
        # acceptance layer re-derives it and stops a step whose argv the sentence
        # does not contain with STEP_COMMAND_NOT_IN_THE_REQUEST.  So a stated
        # command is as safe to compose as a stated payload, and refusing it
        # fails a request the machine can do.
        #
        # Measured without this, on "Compute the sha256 of the file <t>/a1.txt":
        # the front compiler ranked shell.command.run FIRST at score 8, could not
        # bind its argv slot from prose (argv:not_stated), moved on to
        # finance.saccr.credit.addon.v1 on the single matched word "compute",
        # and route admission fail-closed that as R3_WEAK_EVIDENCE -- while the
        # composer route reached the request with the one-step chain
        # ['shell.command.run'].  The capability was ranked correctly and then
        # thrown away for want of a binder.
        #
        # The #6119 hazard this gate was scoped against stays closed: "Check the
        # file X" states neither a payload nor a command line, so extract_content
        # and extract_argv are both None and it keeps failing closed.
        #
        # One further case, measured.  A sentence can state a complete command
        # line and STILL be refused -- not for want of a binder, but because two
        # CAPABILITIES tied and ambiguity refuses.  "Show the files in the
        # directory <d>" ranked shell.command.run and
        # source.candidates.enumerate.stdlib at 4 each, on the word "files", so
        # admission fail-closed R3_WEAK_EVIDENCE with typed_binding_refused
        # unset and this gate never fired.  "List the directory <d>" and "Show
        # the contents of the directory <d>" -- the same command, the same
        # operand, phrased without the word that draws a tie -- both ran and
        # were exact-verified.  One ordinary word was the whole difference.
        #
        # A tie between capabilities says nothing about the COMMAND, and the
        # command is what would be executed.  extract_argv refuses on ambiguity
        # by construction, so a non-None result is one settled argv, and the
        # acceptance layer re-derives it and stops any step whose argv the
        # sentence does not contain with STEP_COMMAND_NOT_IN_THE_REQUEST.  The
        # #6119 hazard stays closed for the reason it always has: "Check the
        # file X" states no command line, so extract_argv is None and it keeps
        # failing closed.
        stated_a_command_line = composer_route.extract_argv(normalized) is not None
        if stated_a_command_line or (
                admission.get("typed_binding_refused") is True
                and composer_route.extract_content(normalized) is not None):
            composed = _try_composed(task_id, goal, started)
            if composed is not None:
                return _composed_holds_up(composed, normalized, future_artifacts)
        return _fail(task_id, "FAIL_CLOSED__ROUTE_ADMISSION_REJECTED",
                     "ROUTE_ADMISSION_REJECTED:" + str(admission.get("rule")), started, **_extra)
    promised_sources = _promised_source_files(normalized)
    source_digests_before = {raw: _source_digest(raw) for raw in promised_sources}
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
            # Composition was tried BECAUSE the artifact was missing, so it is
            # the one path that must be re-measured before it may report success.
            return _composed_holds_up(composed, normalized, future_artifacts)
        result["runtime_status_before_artifact_check"] = result.get("status")
        cls = promised_artifact_class(missing)
        result["status"] = "FAIL_CLOSED__" + cls
        result["pass"] = False
        result["failure_class"] = cls
        result["promised_artifact_errors"] = missing
    unchanged = promised_source_change_errors(normalized, source_digests_before) \
        if result.get("pass") is True else []
    if unchanged:
        result["runtime_status_before_source_change_check"] = result.get("status")
        result["status"] = "FAIL_CLOSED__PROMISED_SOURCE_CHANGE_NOT_APPLIED"
        result["pass"] = False
        result["failure_class"] = "PROMISED_SOURCE_CHANGE_NOT_APPLIED"
        result["promised_source_change_errors"] = unchanged
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
