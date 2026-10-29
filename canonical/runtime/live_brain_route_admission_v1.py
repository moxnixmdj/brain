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

import ast
import hashlib
import json
import pathlib
import re
import subprocess
from pathlib import Path
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
from canonical.runtime.bound_capabilities import python_repair_measured_acceptance_controller_v1 as _acceptance
from canonical.runtime.bound_capabilities.python_test_corpus_discovery_v1 import (
    is_test_file_name as _is_test_file_name,
)

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
    # A sentence that states a settled command line states a COMMAND, and a
    # capability that cannot run a command line cannot answer it -- however many
    # of the sentence's words its keywords happen to contain.  The retrieval
    # layer already applies this rule to the candidates IT ranks, and measured,
    # that was not enough: for "Search the files in the directory X for the exact
    # text 'apple'" the compiler selected
    # evidence.claim_relation.generic_units.stdlib, the retrieval layer refused
    # it, and this function -- which re-judges the compiler's own pick -- admitted
    # it anyway.  It then ran and died, while composer_route.route() had already
    # returned shell.command.run with the exact argv (fgrep -r apple X).
    #
    # extract_argv returns one settled argv or refuses on ambiguity, and the
    # acceptance layer re-derives it, so this is a fact about the sentence rather
    # than a preference about capabilities.
    # A sentence that says "append" promises the file's current content survives.
    # A plain payload write replaces the whole file, so admitting one here turns
    # that promise into a deletion reported as exact semantic acceptance --
    # measured: 'apple\nbanana\n' became 'hello' and passed.  The refusal belongs
    # in this gate as well as in execute_chain, because this gate re-judges the
    # compiler's own pick and has admitted what another layer refused.
    if (str(selected) in composer_route._PLAIN_PAYLOAD_WRITES
            and composer_route.keeps_existing_content(goal)):
        return {"schema": SCHEMA, "admitted": False,
                "rule": "WRITE_WOULD_DISCARD_CONTENT_THE_SENTENCE_PROMISED_TO_KEEP",
                "compiler_mode": mode, "selected_capability": selected}
    if composer_route.extract_argv(goal) is not None:
        _slots = {str(k or "").lower() for k in
                  ((entry.get("action_template") or {}).get("args") or {})}
        # A COMMAND slot is a command slot whatever it is called.  Measured on
        # 7913c4d: "Repair python bug in source <calc.py> with ast patch search
        # guided by test <t.py> using test command \"python3 <t.py>\" and save
        # output_path <o.json>" compiled to the right capability and was then
        # refused NO_COMMAND_SLOT_FOR_THE_STATED_COMMAND, because the entry
        # declares `test_argv` and this test only looked for the literal name
        # `argv`.  bind() fills test_argv from that same sentence, exactly:
        # ["python3", "<t.py>"].  Three repair families never reached a capability
        # because of the spelling of a slot.
        _command_slots = {s for s in _slots
                          if s == "argv" or s.endswith("_argv")
                          or s in ("command", "command_line", "cmd")}
        if _slots and not _command_slots:
            return {"schema": SCHEMA, "admitted": False,
                    "rule": "NO_COMMAND_SLOT_FOR_THE_STATED_COMMAND",
                    "compiler_mode": mode, "selected_capability": selected}
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


def _empty_test_selection(goal: str, result: Mapping[str, Any]) -> bool:
    """The sentence asked which tests to run, and the artifact selected none.

    A capability that REPORTS ``selected_tests`` states the shape of its own answer, so an empty
    list is a measurement of nothing -- not an answer.  Measured 2026-10-30: "Which tests do I need
    to run after changing <f>?" returned PASS with
    ``PROJECT_BRAIN_CHANGE_IMPACT_TEST_SELECTION_V1`` whose ``selected_tests`` was ``[]`` while
    ``affected_modules`` named the module AND its test file.  The same class as the coverage gate's
    ``gate: PASS`` over zero measured lines: the artifact was verified as a file write, never as an
    answer to the question that was asked.  Scoped to the sentence that asks it.
    """
    if not _CHANGE_IMPACT_REQUEST_RE.search(str(goal or "")):
        return False
    # The adapters report the answer two ways: the list itself, or its COUNT in the summary fields
    # (``selected_test_count``).  Both are the capability's own statement about its answer, so both
    # are read -- an empty list and a zero count are the same fact.
    for key in ("selected_tests", "candidate_tests"):
        value = result.get(key)
        if isinstance(value, list) and not value:
            return True
    for key in ("selected_test_count",):
        value = result.get(key)
        if isinstance(value, int) and value == 0:
            return True
    return False


def _execute_locally(task_id: str, goal: str, compiled: Mapping[str, Any], entry: Mapping[str, Any], action: Mapping[str, Any],
                     raw_contract: Mapping[str, Any], started: int) -> dict[str, Any]:
    selected = str(compiled.get("selected_capability") or "")
    try:
        tool_result = run_adapter_locally(entry, action)
        if isinstance(tool_result, Mapping) and _empty_test_selection(goal, tool_result):
            return _fail(task_id, "FAIL_CLOSED__ANSWER_EMPTY__NO_TESTS_SELECTED",
                         "ANSWER_EMPTY:SELECTED_TESTS_IS_EMPTY_WHILE_AFFECTED_MODULES_EXIST", started,
                         executed=True, compiled_capability_id=selected,
                         answer_artifact={k: tool_result.get(k) for k in
                                          ("schema", "selected_tests", "candidate_tests",
                                           "affected_modules", "changed_files")},
                         executor=LOCAL_EXECUTION_PROOF,
                         tool_executed=True)
    # ``SystemExit`` too: this repository's adapters refuse with ``raise SystemExit(1)`` (the
    # ``_systemic`` convention in bound_capabilities/*.py), and a capability that exits must be a
    # closed failure with a reason, never the death of the caller.  Measured 2026-10-29:
    # python_crossfile_edit_choreograph.py on an occupied output path killed the whole
    # 72-capability probe with ``SystemExit: 1`` instead of reporting anything.
    except (Exception, SystemExit) as exc:  # noqa: BLE001 - every adapter failure is a closed failure
        tool_executed = not isinstance(exc, LocalExecutionFailure) or "ACTION_EXPECTATION_FAILED" in str(exc)
        # A REVIEW THAT RAN AND FOUND A PROBLEM IS NOT A BROKEN ADAPTER.
        #
        # The four review gates declare ``expect: gate == PASS``, so a gate that executed
        # perfectly and reported FAIL -- a real finding, e.g. ``subprocess.run(shell=True)`` --
        # came back as FAIL__LIVE_CONTROLLER_EXECUTION, indistinguishable from a crash.  The
        # expectation is about the CODE, not about the review, and the runner may not silently
        # reinterpret either; what it can do is report the two separately.  `pass` stays False
        # (the review did not certify clean code), the status says a review ran, and the verdict
        # the gate emitted is carried in the reason.
        _expect = action.get("expect") if isinstance(action.get("expect"), Mapping) else {}
        _verdict_field = str((_expect or {}).get("field") or "")
        if _verdict_field and "ACTION_EXPECTATION_FAILED" in str(exc):
            # A REVIEW AND A REFACTOR BOTH CARRY THEIR OWN VERDICT, BUT ONLY ONE IS A REVIEW.
            #
            # Measured 2026-10-30: a rename that computed and syntax-checked the whole patch but had
            # no test to verify it came back as "REVIEW_RAN..." -- the right refusal shape, the wrong
            # name, and a caller reading the status would go looking for a review that never existed.
            _is_review = "review" in str(selected)
            return _fail(task_id,
                         ("FAIL_CLOSED__REVIEW_RAN_AND_RETURNED_A_VERDICT" if _is_review
                          else "FAIL_CLOSED__CAPABILITY_RETURNED_A_VERDICT"),
                         ("REVIEW_EXECUTED__VERDICT_IS_THE_ANSWER__CODE_NOT_CERTIFIED" if _is_review
                          else "CAPABILITY_EXECUTED__VERDICT_IS_THE_ANSWER__EXPECTATION_NOT_MET"),
                         started, executed=True, reviewed=_is_review,
                         review_verdict_field=_verdict_field,
                         compiled_capability_id=selected, compiler_mode=compiled.get("compiler_mode"),
                         reason=type(exc).__name__ + ":" + str(exc),
                         executor=LOCAL_EXECUTION_PROOF, tool_executed=True)
        # A STRUCTURED REFUSAL IS NOT A CRASH -- HERE TOO.
        #
        # The composed path has parsed ``raise SystemExit(json.dumps({"error": true, "reason": ...}))``
        # for a while; THIS path, which runs the single selected capability, did not, so the gate's
        # own finding was replaced by a generic controller failure.  Measured 2026-10-30: the
        # mutation gate refused ``BASE_WORLD_RED:no tests ran`` and the caller was told
        # ``BOUND_CAPABILITY_SOURCE_UNSUPPORTED:runtime`` -- a statement about the registry, from the
        # other executor, about a gate that had already answered.
        _payload = str(exc)
        try:
            _decoded = json.loads(_payload)
        except (ValueError, TypeError):
            _decoded = None
        if isinstance(_decoded, Mapping) and _decoded.get("error") is True:
            _why = str(_decoded.get("reason") or "UNSPECIFIED").strip()[:200]
            return _fail(task_id, "FAIL_CLOSED__CAPABILITY_REFUSED_" + _why.split(":")[0][:60],
                         "CAPABILITY_REFUSED:" + _why, started, executed=True,
                         compiled_capability_id=selected, compiler_mode=compiled.get("compiler_mode"),
                         refusal_payload=dict(_decoded), executor=LOCAL_EXECUTION_PROOF,
                         tool_executed=tool_executed)
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
        # THE SENTENCE-PROVED INPUTS BELONG TO THE ROUTE, NOT TO THE TYPED SELECTOR.
        #
        # ``declared_input_derivation_v1`` proves values the sentence states in a different shape (a
        # file where the capability declares a directory, the stated paths of a change set) and the
        # typed-admission path has always merged them.  The PRIMARY execution path never did, so a
        # row the declaration shortlist had correctly chosen was executed with an unbound slot and
        # the adapter raised its own RuntimeError:
        #
        #   "Which tests do I need to run after changing <f>?" -> python.source.change_impact
        #     .testselect.v1 -> RuntimeError:CHANGE_IMPACT_INPUT_REQUIRED
        #
        # A missing slot must never reach an adapter.  Only values the derivation PROVES from the
        # sentence are added (each carries its rule and its evidence), nothing is invented, and a
        # slot the sentence cannot prove stays absent so the capability's own contract still fails
        # closed.
        _exec_entry = _entry
        try:
            from canonical.runtime import declared_input_derivation_v1 as _derivation
            from canonical.runtime import swe_typed_plan_v1 as _typed_plan_module
            if _derivation.is_swe_request(goal) and str(selected).startswith(_derivation.SWE_CID_PREFIXES):
                _shadow, _proven, _report = _derivation.binding_view(goal, _entry, ROOT)
                # SHAPE IS PART OF THE VALUE.  The front binder fills a declared slot with the LAST
                # path it read -- a string -- where the capability declares a LIST of paths, and the
                # mismatch only surfaced inside the adapter
                # (RuntimeError:CHANGE_IMPACT_INPUT_REQUIRED).  When the derivation proves the slot
                # as a list and the bound value is not one, the derivation wins: the sentence stated
                # the paths, and the capability said what shape it wants them in.
                for _key, _value in (_proven or {}).items():
                    _bound = _inputs.get(_key)
                    if _key not in _inputs or (isinstance(_value, list)
                                               and not isinstance(_bound, list)):
                        _inputs[_key] = _value
                if _proven:
                    compiled = dict(compiled, derived_inputs=_report)
                # The adapter owns its defaults, so only THOSE placeholders leave the executable
                # template; the DERIVED slots keep their values because the adapter still has to
                # receive them.  Rendering the declared template as-is against those inputs raises
                # on the defaulted slot (GOAL_INPUT_BINDING_REQUIRED:min_coverage_ratio, which
                # escaped ``solve`` as an uncaught GoalCompilationFailure), and rendering
                # ``binding_view``'s shadow sends the gate out with no anchor at all
                # (MISSING_OR_INVALID_PATH_ARGUMENT).  The typed path already drew this line, so
                # its helper is reused rather than redrawn.
                _exec_entry = dict(_entry)
                _exec_entry["action_template"] = _typed_plan_module._execution_template(
                    _entry, set((_report or {}).get("adapter_defaulted") or {}))
        except Exception:  # noqa: BLE001 - a derivation fault keeps the declared template
            _exec_entry = _entry
        _declared = _exec_entry.get("declared_action_template")
        try:
            action = goal_compiler._render_template(_declared or _exec_entry["action_template"], _inputs)
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
            action = goal_compiler._render_template(_exec_entry["action_template"], _inputs)
        if kernel_refuses(admissible[selected]):
            return _execute_locally(task_id, goal, compiled, admissible[selected], action, raw_contract, started)
        local_res = _execute_locally(task_id, goal, compiled, admissible[selected], action, raw_contract, started)
        if local_res.get("pass") is True:
            return local_res
        if str(local_res.get("status") or "").startswith("FAIL_CLOSED__CAPABILITY_REFUSED"):
            # THE CAPABILITY ANSWERED, AND THE ANSWER WAS A REFUSAL WITH ITS OWN REASON.
            #
            # Falling through to the controller re-ran the SAME action through the other executor,
            # which reported ``Blocker:BOUND_CAPABILITY_SOURCE_UNSUPPORTED:runtime`` -- a statement
            # about the registry's source type that hid the gate's actual finding.  Measured
            # 2026-10-30: the mutation gate refused ``BASE_WORLD_RED:no tests ran`` and the report
            # said the capability's substrate was unsupported.  A structured refusal is an answer;
            # re-running it cannot improve it.
            return local_res
        if str(local_res.get("status") or "").startswith("FAIL_CLOSED__ANSWER_EMPTY"):
            # A JUDGEMENT ABOUT THE ANSWER, NOT A FAILED ATTEMPT AT ROUTING.
            #
            # This branch used to fall through to the generic controller, which re-ran the same
            # action and reported PASS because the adapter had written its artifact -- so the
            # empty-answer verdict was overwritten by a "file was written" verdict, which is the
            # oldest defect in this repository in its purest form.  Measured 2026-10-30:
            # "Which tests do I need to run after changing <f>?" -> selected_test_count 0 ->
            # PASS__...EXACT_SEMANTIC_ACCEPTANCE.  A stated, evidence-carrying refusal ends here.
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



# A rename, a move, an extraction and a reformat are all promises that a file is
# different afterwards; only repair verbs were read, so a refactor that changed nothing
# was never checked.  "add"/"insert" are deliberately absent: they are function names
# far more often than they are instructions.
_REPAIR_VERB_RE = re.compile(r"\b(?:repair|fix|patch|correct|rename|move|extract|inline|"
                            r"refactor|reformat)\b", re.IGNORECASE)
# "a measured acceptance repair report" is a noun phrase naming an artifact,
# not an instruction to mutate a source file.  A file actually named report.py
# is still a repair target: the negative lookahead keeps that distinction.
_REPAIR_REPORT_PHRASE_RE = re.compile(
    r"^\s+(?:a|an|the)?\s*"
    r"(?:measured\s+|semantic\s+|objective\s+|acceptance\s+|candidate\s+|verified\s+)*"
    r"(?:report|receipt|result|output)\b(?!\.py\b)",
    re.IGNORECASE,
)

# The same words name tools as well as actions.  A verb is followed by its object
# ("repair the source"); a tool name is followed by what it is ("repair loop",
# "patch search").  This tuple is the discriminator, and it is a closed list on
# purpose: an open rule here would silently drop real instructions.
_TOOL_NOUNS = ("loop", "search", "tool", "engine", "report", "step", "routine",
               "capability", "pass")

# A bug report states a defect and its witness instead of asking for a verb.
# "Bug: <src> add() returns the wrong value. Failing test: <test>." promised that
# <src> would be different afterwards, but there is no repair verb in it, so the
# promise reader returned nothing, no digest was taken, and a run that did not
# touch a byte reported PASS while the named test was still red.  Measured
# 2026-10-29 on e2d7981 with the real runner as the oracle.
_DEFECT_STATEMENT_RE = re.compile(
    r"\b(?:bug|broken|defect|regression|returns?\s+the\s+wrong|"
    r"wrong\s+(?:value|result|answer|output)|failing\s+tests?|test\s+fails|"
    r"tests?\s+(?:is|are)\s+failing|does\s*n[o']t\s+pass)\b",
    re.IGNORECASE,
)


def _nearest_source_before(text: str, candidates: list[tuple[str, Any]],
                           cut: int) -> str | None:
    """The source file a repair verb governs when the sentence names it FIRST.

    Measured 2026-10-29 on ``e2d7981``: "the add function in <file> is broken, fix
    it so its tests pass" returned PASS with the file byte-identical and its own
    test still red.  The promise was never read at all -- the reader only looked for
    a ``.py`` AFTER the verb, and ordinary English puts the target before it ("the
    add function in X is broken, fix it").  So the gate that exists to stop a
    no-op being reported as a repair had nothing to check.

    A witness test is not a promise: "Bug: <test> fails, fix it" names the test the
    repair must satisfy, not the file that must change, so test names are excluded
    by the repository's OWN rule (``is_test_file_name``, the same pair
    ``python_test_audit`` globs on).  Nothing is added when no non-test source is
    named before the verb: an unstated target keeps failing closed downstream.
    """
    best: str | None = None
    best_at = -1
    for raw, path in candidates:
        if _is_test_file_name(path.name):
            continue
        for spelling in (raw, str(path)):
            at = text.rfind(str(spelling), 0, cut)
            if at > best_at:
                best_at, best = at, str(raw)
    return best


# A QUESTION IS NOT AN ACTION.  "Explain why the test in <T> fails" promises an ANSWER;
# nothing on disk has to change, so not one of the artifact / source-change / observation
# gates can see whether the answer was given.  Measured 2026-10-29: the moment a read
# request stopped overwriting the file it named -- and therefore stopped failing -- the
# router answered that sentence with code.impact.tree_sitter.testselect.v1 (test
# SELECTION) and the door reported PASS with output_verified=True, which is the
# capability's own goal, not the sentence's.  The sentence's effect is read with one
# regex and checked against the capability's own declared surface.
_ANSWER_REQUEST_RE = re.compile(r"\b(?:explain|explanation|diagnose)\b"
                                r"|\bwhy\s+(?:does|do|is|are|did|would)\b",
                                re.IGNORECASE)
_ANSWER_SURFACE_RE = re.compile(r"\b(?:explain\w*|diagnos\w*|fault\w*|locali[sz]\w*"
                                r"|traceback|cause|root_cause|why)\b", re.IGNORECASE)

# The same seam, for every effect a sentence can state.  A capability's own ``expect`` field
# says what ITS OWN goal is, and the door was reading it as the sentence's goal: measured
# 2026-10-29 on a fresh tree, "Run a security audit on <pkg>" returned
# PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE from python.source.audit.ast -- a
# symbol count -- and "Measure the test coverage of <pkg>" returned PASS from
# python.repository.acceptance.measure.v1, which measures the repository and not the tests.
#
# Each row is (what the sentence asked for, what a capability's OWN DECLARATION must contain
# to be an answer to it).  Data, not ids: the surface is the capability id plus the
# ``provides`` and ``keywords`` it declares, so a real security or coverage capability is
# admitted the moment one is bound, and nothing here names a capability.
# "WHICH TESTS DO I NEED TO RUN AFTER CHANGING X" -- one regex, because the declaration gate uses it
# to shortlist and the post-execution gate uses it to judge the answer.
_CHANGE_IMPACT_REQUEST_RE = re.compile(
    r"\bwhich tests?\b[^.\n]{0,60}?\b(?:run|runs|need|needs|affected|impact\w*)\b|"
    r"\baffected tests?\b|\bimpact\w*\b[^.\n]{0,20}\btests?\b|"
    r"\btests?\b[^.\n]{0,30}\baffected\b", re.IGNORECASE)


_STATED_EFFECTS: tuple[tuple[re.Pattern[str], re.Pattern[str], str], ...] = (
    (_ANSWER_REQUEST_RE, _ANSWER_SURFACE_RE, "STATED_ANSWER_NOT_PROVIDED_BY_CAPABILITY"),
    # "for security ISSUES" is how an engineer says it, and the row did not read it: measured
    # 2026-10-29, "Review <f> for security issues" matched no stated effect at all, so the
    # declaration shortlist came back empty and the ranker was free to propose a gate composer.
    (re.compile(r"\bsecurity\s+(?:audit|review|scan|check|analysis)\b"
                r"|\b(?:security|securit\w*)\s+(?:issue|problem|bug|risk|flaw|hole)s?\b"
                r"|\bvulnerabilit\w*\b|\bexploitab\w*\b", re.IGNORECASE),
     re.compile(r"security|vulnerab|injection|secret|taint|bandit|cwe|exploit", re.IGNORECASE),
     "STATED_SECURITY_REVIEW_NOT_PROVIDED_BY_CAPABILITY"),
    (re.compile(r"\b(?:test\s+)?coverage\b", re.IGNORECASE),
     re.compile(r"coverage", re.IGNORECASE),
     "STATED_COVERAGE_NOT_MEASURED_BY_CAPABILITY"),
    # A CALLER MAP IS NOT A PARSE.  Measured 2026-10-29 on this repository: the SAME sentence
    # "Find every caller of the function <f> in <dir>" is answered by python.source.symbols.index.ast
    # (a real ``callers_of`` map) on a 3-file tree and by code.index.tree_sitter.incremental.v1 (a
    # whole-tree parse, ``definition_count`` only, not one caller named) on canonical/tests -- and the
    # door reported PASS for both, because the accepted artifact was verified as a FILE WRITE and
    # never as an answer to the question.  The registry already draws the line: ``callers``/``call
    # graph``/``who calls`` are declared by the symbol index and by nothing else.
    (re.compile(r"\bcallers?\b|\bwho calls\b|\bcall[ _-]?(?:graph|sites?|edges?)\b",
                re.IGNORECASE),
     re.compile(r"\bcallers?\b|\bwho calls\b|\bcall[ _-]?(?:graph|sites?|edges?)\b|"
                r"\bcallers_of\b", re.IGNORECASE),
     "STATED_CALLER_MAP_NOT_PROVIDED_BY_CAPABILITY"),
    # "RUN THE TESTS" REQUIRES SOMETHING TO HAVE RUN.  Measured 2026-10-30: "Run the test suite for
    # <T>" was certified PASS by the same test-selection INDEX that answered the flaky question,
    # while the tree's own suite was never executed -- no return code, no count of tests run, no
    # timing.  A selection is a plan to run; the sentence asks for the run.  The row that runs tests
    # says so in what it provides (a runner, a suite, pytest/unittest, a measured acceptance), which
    # is the same declaration test the other rows use.
    # The verb must be the REQUEST.  "Set up CI to run the tests in <dir>" contains "run the tests"
    # and asks for a workflow file; anchoring the verb at the start of the sentence keeps the CI
    # sentence on the CI side (measured: an unanchored trigger refused a real CI row).
    (re.compile(r"^\s*(?:please\s+|now\s+|can you\s+)*(?:re)?run\b[^.\n]{0,40}"
                r"\b(?:tests?|suite|pytest)\b|^\s*(?:please\s+)?(?:re)?execute\b[^.\n]{0,30}"
                r"\btests?\b|^\s*(?:run|rerun)\s+the\s+tests?\b", re.IGNORECASE),
     re.compile(r"\brun\w*|\bsuite\b|\bpytest\b|\bunittest\b|\bacceptance\b|\bexecut\w*"
                r"|\bharness\b|\bdriver\b", re.IGNORECASE),
     "STATED_TEST_RUN_NOT_EXECUTED_BY_CAPABILITY"),
    # A VERDICT ABOUT FLAKINESS IS NOT A TEST SELECTION.  Measured 2026-10-30 on this repository:
    # "Rerun the failing test <T> three times and tell me if it is flaky" was certified
    # PASS__RAW_GOAL_..._EXACT_SEMANTIC_ACCEPTANCE by code.impact.tree_sitter.testselect.v1 -- a
    # test-selection INDEX.  Nothing was rerun once, let alone three times, and no verdict was
    # formed, but the artifact was verified as a file write and its `selected_tests` entries were
    # read as evidence of the answer.  The capability:impact shortlist matched "test"; the question
    # asked for a stability verdict.  Nothing in the registry declares stability, so the honest
    # outcome today is a NAMED refusal, and a capability that measures flakiness is admitted the
    # moment it is bound -- by this declaration and nothing else.
    (re.compile(r"\bflak(?:y|iness)\b|\b(?:non)?determinis\w*\s+test\b"
                r"|\bintermittent(?:ly)?\s+(?:fail\w*|test\w*)\b", re.IGNORECASE),
     re.compile(r"\bflak\w*|\brerun\w*|\brepeat\w*|\bstabilit\w*|\bvariance\b",
                re.IGNORECASE),
     "STATED_FLAKY_VERDICT_NOT_PROVIDED_BY_CAPABILITY"),
    # A STACK FRAME IS NOT A SYMBOL INDEX.  Same sentence, same run: "Attach a debugger to the
    # failing test <T> and show me the frame where it breaks" was answered by the same index.  A
    # definition list contains no frame, no locals and no traceback; the words "debugger" and
    # "frame" are how the request is stated, and a row that provides debugging says so.
    (re.compile(r"\bdebugger\b|\bbreakpoint\b|\bstack\s+(?:frame|trace)\b|\btraceback\b"
                r"|\bframe\s+where\b", re.IGNORECASE),
     re.compile(r"\bdebug\w*|\bpdb\b|\bbreakpoint|\bframe\b|\btraceback\b",
                re.IGNORECASE),
     "STATED_DEBUGGER_FRAME_NOT_PROVIDED_BY_CAPABILITY"),
    # DEAD CODE.  Nothing in the registry declares it, so this gate's honest outcome today is a
    # refusal -- which is the point: before it, an indexer that lists every definition was certified
    # as "the dead code" because the definition it named appeared in the artifact.  A capability that
    # DOES compute unused symbols is admitted the moment one is bound, by declaration alone.
    (re.compile(r"\bdead\s+code\b|\bunused\s+(?:code|function|symbol|method)s?\b|\bunreferenced\b",
                re.IGNORECASE),
     re.compile(r"\bdead\b|\bunused\b|\bunreferenced\b", re.IGNORECASE),
     "STATED_DEAD_CODE_NOT_IDENTIFIED_BY_CAPABILITY"),
    # WHO CHANGED THIS LINE IS NOT WHAT THIS FILE CONTAINS.  Measured 2026-10-29 on this
    # repository: "Who last changed line 2 of <file>?" was answered by `tail -n 1 <file>` and
    # certified PASS__...EXACT_SEMANTIC_ACCEPTANCE, and once the prose table stopped reading
    # "last ... line" (composer_route_v1._PROVENANCE_RE) the SAME sentence passed on
    # python.source.symbols.index.ast -- a definition list -- because a file's contents were
    # still being accepted as its history.  The request is read with the one regex the
    # command reader already uses, and nothing in the registry declares provenance, so the
    # honest outcome is a refusal until something does.
    (composer_route._PROVENANCE_RE,
     # NOT the bare word "provenance": measured on the live registry, 8 rows carry it and
     # every one means FAULT or ARTIFACT provenance (python.fault.provenance.fusion.v1,
     # pypi.provenance.audit_live_artifact) -- none of them can say who changed a line, and
     # admitting them would be the same false answer this row exists to refuse.
     re.compile(r"\bblame\b|\bauthor(?:ed|ship)?\b|\bcommitter\b|\bshortlog\b|\bchangelog\b|"
                r"\battribution\b", re.IGNORECASE),
     "STATED_PROVENANCE_NOT_ANSWERED_BY_CAPABILITY"),
    # A HISTORY SEARCH IS NOT A TEST SELECTION.  Measured 2026-10-29 on a fresh tree:
    # "Bisect the regression that broke the test in <T>" returned PASS with
    # code.impact.tree_sitter.testselect.v1, which treated <T> itself as the changed file and
    # selected <T> as the candidate test -- an artifact naming one file, no commit, no bisect,
    # no history traversed.  0 of 125 routable rows declare bisect, so the refusal is the
    # honest end state and a real bisect capability is admitted by the same declaration.
    (re.compile(r"\bbisect\b|\bwhich commit\b|\bregression that broke\b|"
                r"\bwhen did\b[^.\n]{0,40}?\bbreak\b", re.IGNORECASE),
     re.compile(r"\bbisect\b", re.IGNORECASE),
     "STATED_BISECT_NOT_PROVIDED_BY_CAPABILITY"),
    # A MEASUREMENT OF THE REPOSITORY IS NOT A DELIVERABLE.  Measured 2026-10-29: "Set up CI to
    # run the tests in <D>" returned PASS from python.repository.acceptance.measure.v1, which
    # measured the tree it was standing in (test_count 0, test_returncode 1, tests_pass false)
    # and wrote that to a spool file.  Nothing was set up: no workflow, no config, no runner.
    # The same seam as S-1 -- the artifact was verified as a FILE WRITE -- and the same answer:
    # the sentence states an effect (a CI definition the repository does not have), a capability
    # that declares no CI surface cannot supply it.
    (re.compile(r"\b(?:set\s+up|setup|add|create|configure|wire)\b[^.\n]{0,40}?"
                r"\b(?:ci|continuous[ _-]?integration|github[ _-]?actions?|workflow|pipeline)\b"
                r"|\b(?:ci|continuous[ _-]?integration)\b[^.\n]{0,40}?\b(?:run|runs|running)\b",
                re.IGNORECASE),
     re.compile(r"\bci\b|continuous[ _-]?integration|github[ _-]?actions?|workflow|"
                r"\bci[._-]?config\b", re.IGNORECASE),
     "STATED_CI_SETUP_NOT_PROVIDED_BY_CAPABILITY"),
    # A TEST SELECTION IS NOT A FLAKINESS VERDICT.  Measured 2026-10-30 on a fresh tree:
    # "Rerun the failing test <T> three times and tell me if it is flaky." returned PASS with
    # code.impact.tree_sitter.testselect.v1, which named <T> as a candidate test once.  Nothing
    # was run three times, no outcome was compared, and no flakiness was decided.  Zero of 125
    # routable rows declare flakiness (census over id+provides+keywords), so the honest end state
    # is a refusal -- and a capability that DOES classify flaky tests is admitted by the same
    # declaration the moment one is bound.
    (re.compile(r"\bflaky\b|\bflakiness\b|\bintermittent\w*\b|\bnondeterministic\b|"
                r"\bnondeterminism\b|\bflake\b", re.IGNORECASE),
     re.compile(r"flak|intermittent|nondetermin", re.IGNORECASE),
     "STATED_FLAKY_VERDICT_NOT_PROVIDED_BY_CAPABILITY"),
    # A DEBUGGER IS NOT AN INDEX.  Measured 2026-10-30: "Attach a debugger to the failing test
    # <T> and show me the frame where it breaks." returned PASS with the same test selection --
    # no process was debugged, no breakpoint was set, no frame was read.  Zero of 125 routable
    # rows declare a debugger, a breakpoint or a frame (census), so this is a refusal until one
    # does; ``python.fault.localize.*`` rows are NOT admitted by it, because localising a fault
    # from a traceback is a different effect from pausing a process and reading its frame.
    (re.compile(r"\bdebugger\b|\bbreakpoint\b|\b(?:pdb|gdb|lldb)\b|\bstack frame\b|"
                r"\bframe where\b|\bthe frame\b", re.IGNORECASE),
     re.compile(r"\bdebugger\b|\bbreakpoint\b|\b(?:pdb|gdb|lldb)\b|\bstack frame\b",
                re.IGNORECASE),
     "STATED_DEBUGGER_FRAME_NOT_PROVIDED_BY_CAPABILITY"),
    # WHICH TESTS A CHANGE BREAKS IS A TEST SELECTION, NOT A REPOSITORY MEASUREMENT.  Measured
    # 2026-10-30: "Which tests do I need to run after changing <f>?" returned PASS from
    # python.repository.acceptance.measure.v1, which ran the repository's suite and reported
    # test_count/tests_pass -- an answer to "do the tests pass here", not "which tests does this
    # change touch".  The rows that DO declare impact analysis exist
    # (code.impact.tree_sitter.testselect.v1 provides change_impact + test selection), so this
    # row is a SHORTLIST, not a refusal: it asks the declaration which rows can select tests.
    (_CHANGE_IMPACT_REQUEST_RE,
     re.compile(r"\bimpact\b|\baffected\b|\btest[._-]?select\w*\b|\bselect\w* tests?\b",
                re.IGNORECASE),
     "STATED_CHANGE_IMPACT_NOT_ANSWERED_BY_CAPABILITY"),
)


# A capability that FINDS a patch is not a capability that MAKES the change.  The registry
# already draws this line in its own ``provides`` declarations --
# python.patch.search.test_guided.ast.v1 provides "python.patch.candidate.test_verified" and
# python.software.repair.apply.verified.v1 provides "...verified_repair_applied" -- and the door
# was accepting the first as an answer to the second.  Measured 2026-10-29 on a fresh tree:
#
#   "The CI is failing because <test_calc.py> fails. Fix the build."
#     -> PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED
#        capability python.patch.search.test_guided.ast.v1
#        payload    PASS__VERIFIED_CANDIDATE_PATCH_FOUND
#        world      calc.py byte-identical, the stated suite still red
#
# The exception is the sentence that states where the REPORT goes: the repair family's own
# contract is "untouched source plus one applicable patch in the report", and a sentence that
# asks for a report asked for exactly that (``_statement_patch_authority``).  So the demand for
# an applied change is scoped to the sentences that name no destination.
_APPLICATION_REQUEST_RE = re.compile(
    r"\b(?:fix|repair|patch|correct)\b|\bmake\b[^.\n]{0,40}\bpass\b", re.IGNORECASE)
_APPLICATION_SURFACE_RE = re.compile(
    r"\b(?:appl(?:y|ied|ies)|in[ _-]?place|writ(?:e|ten|es)|rewr(?:ite|ote)|"
    r"edit(?:ed|s)?|land(?:ed)?|refactor\w*|rename\w*|reformat\w*)\b", re.IGNORECASE)
_REPORT_DESTINATION_RE = re.compile(
    r"\b(?:save|write|output|store|record|put)\b[^.\n]{0,40}\b(?:to|in|into|at)\b",
    re.IGNORECASE)


def stated_application_errors(goal: str, entry: Mapping[str, Any]) -> list[str]:
    """The sentence asks for the change to be MADE; did the capability declare that it makes it?"""
    text = str(goal or "")
    if not _APPLICATION_REQUEST_RE.search(text) or _REPORT_DESTINATION_RE.search(text):
        return []
    cid = str(entry.get("capability_id") or entry.get("id") or "")
    surface = " ".join([cid,
                        " ".join(str(x) for x in (entry.get("provides") or [])),
                        " ".join(str(x) for x in (entry.get("keywords") or []))])
    if _APPLICATION_SURFACE_RE.search(surface):
        return []
    return ["STATED_APPLICATION_NOT_PERFORMED_BY_CAPABILITY:" + (cid or "UNNAMED")]


def _declared_surface(cid: str, entry: Mapping[str, Any]) -> str:
    """The surface a capability is judged by: its id, what it provides, what it names.

    One function, because it was written twice (here and in the answer gate) and two copies of a
    surface is two chances for the gate that refuses and the filter that proposes to disagree.
    """
    return " ".join([str(cid),
                     " ".join(str(x) for x in (entry.get("provides") or [])),
                     " ".join(str(x) for x in (entry.get("keywords") or []))])


def declared_effect_ids(goal: str, registry: Mapping[str, Mapping[str, Any]]) -> list[str]:
    """The rows whose OWN DECLARATION can supply every effect the sentence states.

    THE ROUTER HAD NO "NONE OF THESE".  It ranks 125 routable rows and always returns a top-1, so
    the only thing between a wrong pick and a wrong answer was whether some downstream gate
    happened to apply.  Measured 2026-10-29 on a fresh tree: "Review <f> for security issues"
    reached a gate COMPOSER (and, with a report path, a Pandoc PDF converter) while
    ``python.review.diff_security_gate.v1`` -- 1 of 125 rows, and the only one that declares
    ``security`` -- was never a candidate; the same sentence over a directory reached
    ``python.source.audit.ast``.

    The data for this already existed and was already correct: ``_STATED_EFFECTS`` is the table
    the answer gate uses to REFUSE a capability that cannot supply the stated effect.  Asking it
    one step earlier turns "best of 125" into "these rows declare it, and nobody else does" --
    so a capability is a candidate because of what it says it does, not because of how many of the
    sentence's words appear in its keywords.

    Returns [] when the sentence states no effect, or when NOTHING declares the effect it states
    (dead code, bisect, CI today): an empty answer must not narrow the registry, because the
    honest outcome then is the refusal the answer gate already produces.
    """
    text = str(goal or "")
    if not text.strip():
        return []
    asked = [row for row in _STATED_EFFECTS if row[0].search(text)]
    if not asked:
        return []
    # WHAT IT PRODUCES OUTRANKS WHAT IT IS TAGGED WITH.
    #
    # `provides` is a claim about output; `keywords` are tags, and tags are how a tool name gets
    # attached to a row that does not implement it.  Measured: `software.review.gate.composer.v1`
    # lists `bandit`, `coverage` and `mutation` as KEYWORDS, so it counted as a supplier of a
    # "security issues" review, outranked the one row that provides a security gate, and the
    # sentence was refused by the composer's own weakness.  A row that PRODUCES the effect is a
    # candidate; a row that merely mentions the tool is a candidate only when nothing produces it.
    strong: list[str] = []
    weak: list[str] = []
    for cid, entry in (registry or {}).items():
        if not isinstance(entry, Mapping):
            continue
        produces = " ".join([str(cid), " ".join(str(x) for x in (entry.get("provides") or []))])
        if all(supplied.search(produces) for _ask, supplied, _code in asked):
            strong.append(str(cid))
        elif all(supplied.search(_declared_surface(str(cid), entry))
                 for _ask, supplied, _code in asked):
            weak.append(str(cid))
    return sorted(strong) if strong else sorted(weak)


def stated_answer_errors(goal: str, entry: Mapping[str, Any]) -> list[str]:
    """A sentence that asks for X must be answered by something that declares X.

    Only the sentence and the capability's own declaration are consulted: its id, what it
    says it provides, and its declared keywords.  A capability that neither explains nor
    localizes is not an answer to "why did this fail"; one that declares neither security
    nor coverage is not an answer to a security review or a coverage measurement, whatever
    its own ``expect`` field says.
    """
    text = str(goal or "")
    if not text.strip():
        return []
    cid = str(entry.get("capability_id") or entry.get("id") or "")
    surface = " ".join([cid,
                        " ".join(str(x) for x in (entry.get("provides") or [])),
                        " ".join(str(x) for x in (entry.get("keywords") or []))])
    errors: list[str] = []
    for asked, supplied, code in _STATED_EFFECTS:
        if not asked.search(text) or supplied.search(surface):
            continue
        errors.append(code + ":" + (cid or "UNNAMED"))
    errors.extend(stated_application_errors(text, entry))
    return errors


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
        if _REPAIR_REPORT_PHRASE_RE.match(text[m.end():m.end() + 100]):
            # The next words are "report"/"receipt"/...: the sentence asks for
            # evidence about a candidate, not for an existing source file to be
            # changed.  Demanding a byte change in the nearest .py witness here
            # made a correct measured-acceptance report fail at the front door.
            continue
        # "with the test guided repair LOOP", "with AST patch SEARCH": the word is
        # naming a tool, not asking for a change.  Measured on 18ecf7db: that noun
        # match made the sentence's witness tests the repair target, so the goal
        # "repair the python source X ... so the unit tests in T1, T2 pass" demanded
        # T1 change too and no repair could ever satisfy it -- the reference
        # capability was refused with PROMISED_SOURCE_UNCHANGED:<test file> while
        # the source it repaired was correctly restored.
        if text[m.end():m.end() + 24].lstrip().lower().startswith(_TOOL_NOUNS):
            continue
        best = None
        best_at = None
        for raw, path in candidates:
            for spelling in (raw, str(path)):
                at = text.find(spelling, m.end())
                if at >= 0 and (best_at is None or at < best_at):
                    best_at = at
                    best = raw
        if best is None:
            # English puts the repaired target before the verb as often as after
            # it.  Read the promise from the sentence, not from word order.
            best = _nearest_source_before(text, candidates, m.start())
        if best is None or best in out:
            continue
        # A file inside a stated source ROOT is covered by the root rule below.  The
        # first .py after the verb in "Repair the python source root <dir> ... with
        # test command \"python -B <dir>/test_x.py\"" is the WITNESS test, and
        # demanding that it change refuses a correct repair of the module beside it.
        if any(str(best).startswith(root.rstrip("/") + "/")
               for root in _promised_source_roots(text)):
            continue
        out.append(best)
    if not out and _DEFECT_STATEMENT_RE.search(text):
        # A sentence that reports a defect and names where it lives ("Bug: X
        # returns the wrong value") promised that X change, and names its witness
        # instead of its verb.  Read the promise from the statement rather than
        # from the grammar: every non-test source the sentence names is a target,
        # read with the same rules the verb branch uses (test files are witnesses,
        # files inside a stated root are covered by the root rule).
        for raw, path in candidates:
            if _is_test_file_name(path.name):
                continue
            if any(str(raw).startswith(root.rstrip("/") + "/")
                   for root in _promised_source_roots(text)):
                continue
            if raw not in out:
                out.append(raw)
    return out


def _stated_files(goal: str) -> list[str]:
    """Every path the sentence names that is a FILE or is meant to become one.

    `_future_artifacts` only returns paths that do not exist yet, so on a second run
    in the same directory the stated report already exists and stopped counting as
    evidence -- measured on 7913c4d: the coupled loops wrote their patch report to
    the stated path, the door looked only at `_future_artifacts`, found nothing, and
    refused with PROMISED_SOURCE_CHANGE_NOT_APPLIED.  What a sentence states is a
    fact about the sentence, not about whether an old copy is lying around; that a
    report must be FRESH is checked separately, against the bytes on disk.
    """
    out = []
    for raw, path in goal_compiler._repo_paths(goal, ROOT):
        raw = str(raw)
        if front._CAPABILITY_ID_SHAPE.fullmatch(raw) or path.is_dir():
            continue
        if raw not in out:
            out.append(raw)
    return out


def _promised_source_roots(goal: str) -> list[str]:
    """Directories the sentence asks to REPAIR, as opposed to files.

    "Repair the python source root <dir> with the coupled multi-edit repair loop"
    names a tree.  Treating the first .py after the verb as the target made the
    sentence's WITNESS TEST the thing that had to change -- measured: the coupled
    families were refused with PROMISED_SOURCE_UNCHANGED:<test file> while the
    source the loop had patched sat next to it undischarged.
    """
    text = str(goal or "")
    paths = [(raw, path) for raw, path in goal_compiler._repo_paths(goal, ROOT)
             if not front._CAPABILITY_ID_SHAPE.fullmatch(str(raw))]
    out = []
    for m in _REPAIR_VERB_RE.finditer(text):
        if text[m.end():m.end() + 24].lstrip().lower().startswith(_TOOL_NOUNS):
            continue
        best_raw, best_path, best_pos = None, None, None
        for raw, path in paths:
            for spelling in (str(raw), str(path)):
                at = text.find(spelling, m.end())
                if at >= 0 and (best_pos is None or at < best_pos):
                    best_raw, best_path, best_pos = raw, path, at
        if best_raw is not None and best_path is not None and best_path.is_dir() \
                and str(best_raw) not in out:
            out.append(str(best_raw))
    return out


def _source_digest(raw: str) -> str:
    try:
        return hashlib.sha256((ROOT / raw).read_bytes()).hexdigest()
    except Exception:  # noqa: BLE001 - unreadable is its own error, reported below
        return ""


def _patch_records(report: Any, _depth: int = 0) -> list[Mapping[str, Any]]:
    """Every patch-shaped record a report carries, wherever it puts it.

    Measured on 7913c4d, the three repair families write the same evidence in two
    different shapes: `python.patch.search.test_guided.ast.v1` puts `source_path`
    and `unified_diff` at the TOP LEVEL of its report, while the coupled loops put
    them inside a `patches` list.  Reading only `report["patches"]` therefore
    refused a patch that was sitting in the file, so the family fell back to
    PROMISED_SOURCE_CHANGE_NOT_APPLIED and the work was done but uncredited.

    Bounded on purpose (depth 3, 64 records): a report is data, not a graph, and
    this runs at the door.
    """
    out: list[Mapping[str, Any]] = []
    if _depth > 3:
        return out
    if isinstance(report, Mapping):
        if report.get("source_path") and report.get("unified_diff"):
            out.append(report)
        for value in report.values():
            if isinstance(value, (list, Mapping)) and len(out) < 64:
                out.extend(_patch_records(value, _depth + 1))
    elif isinstance(report, list):
        for item in report[:64]:
            if isinstance(item, (list, Mapping)):
                out.extend(_patch_records(item, _depth + 1))
    return out[:64]


def _statement_patch_authority(raw: str, artifacts: Mapping[str, Any] | None,
                               before_files: Mapping[str, Any] | None = None) -> bool:
    """Does a stated report carry a patch for this source that really applies?

    Measured on 18ecf7db: "Repair the python source X ... so the unit tests in T
    pass, and save the repair report to R" was refused
    PROMISED_SOURCE_CHANGE_NOT_APPLIED although the loop had found, verified and
    replayed the patch and written it to R with the source restored -- which is
    exactly the contract the family oracle at live_solver_families_v3.py:430
    demands (untouched source plus one applicable patch in the report).  The door
    and the bench were each right about a different sentence, so no run could
    satisfy both.

    The promise is read from the sentence, not assumed: a goal that states the
    report's path promised a report.  That promise is only discharged by a patch
    that applies cleanly to the bytes on disk and changes them -- the same bar
    the oracle holds, checked with the applier the capability itself uses rather
    than a second, looser one.
    """
    if not artifacts:
        return False
    target = (ROOT / raw).resolve()
    is_root = target.is_dir()
    for stated in artifacts:
        path = ROOT / str(stated)
        if not path.is_file():
            continue
        if before_files is not None and str(stated) in before_files:
            # The file was already there.  Evidence must be written by THIS run:
            # otherwise a stale report from an earlier attempt credits a run that
            # did nothing, which is the over-claim this gate exists to stop.
            try:
                stat = path.stat()
                if before_files[str(stated)] == (stat.st_size, stat.st_mtime_ns):
                    continue
            except OSError:
                continue
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 - a non-JSON artifact promises no patch
            continue
        for patch in _patch_records(report):
            if not isinstance(patch, Mapping):
                continue
            named = str(patch.get("source_path") or "")
            if not named:
                continue
            try:
                resolved = (ROOT / named).resolve()
                if resolved != target and not (is_root and target in resolved.parents):
                    continue
            except Exception:  # noqa: BLE001
                continue
            diff = str(patch.get("unified_diff") or "")
            if not diff.strip():
                continue
            try:
                # The bytes a patch applies to are the bytes it NAMES: for a stated
                # source root that is the module inside it, never the directory.
                current = resolved.read_text(encoding="utf-8")
            except Exception:  # noqa: BLE001
                continue
            try:
                patched = _acceptance._apply_unified_diff(current, diff)
            except Exception:  # noqa: BLE001 - a patch that does not apply is no promise
                continue
            if patched != current:
                return True
    return False


def _py_files_under(root: str, limit: int = 50) -> list[str]:
    base = ROOT / root
    out: list[str] = []
    try:
        for path in sorted(base.rglob("*.py")):
            out.append(str(path.relative_to(ROOT)))
            if len(out) >= limit:
                break
    except OSError:
        return out
    return out


def promised_source_change_errors(goal: str, before: Mapping[str, str],
                                  artifacts: list[str] | None = None, *,
                                  roots_before: Mapping[str, Mapping[str, str]] | None = None,
                                  before_files: Mapping[str, Any] | None = None) -> list[str]:
    """Every source file the goal asked to repair must actually be different now.

    The repair loops find a patch, verify it, replay the verification, then restore
    the source, declaring NO_SOURCE_WRITE_OR_PROMOTION_AUTHORITY.  That is the right
    boundary for a capability to hold -- but the front door was reporting PASS for a
    file that is still broken.  That is the over-claim R6 exists to stop, one layer
    down: the goal promised a change and no change happened.

    A repair verb is not always a promise to write in place.  When the sentence
    also states where the repair report goes, the promised result is the patch,
    and the file is untouched by design.  Accepting either authority is what lets
    one sentence be satisfiable at all; the unchanged case still fails closed when
    no stated report carries a patch that applies.
    """
    errors = []
    for raw, digest in (before or {}).items():
        now = _source_digest(raw)
        if not now:
            errors.append("PROMISED_SOURCE_UNREADABLE:" + raw)
        elif now == digest:
            if _statement_patch_authority(raw, artifacts, before_files):
                continue
            errors.append("PROMISED_SOURCE_UNCHANGED:" + raw)
    # A stated source ROOT promises that the repair happened somewhere inside it.
    # Requiring every file in the tree to change would refuse a correct repair of
    # one module; requiring nothing would accept a run that touched no file at all.
    for root, files_before in (roots_before or {}).items():
        changed = any(_source_digest(rel) != digest for rel, digest in files_before.items())
        if changed or _statement_patch_authority(root, artifacts, before_files):
            continue
        errors.append("PROMISED_SOURCE_UNCHANGED:" + root)
    return errors


# ------------------------------------------------------------------ observe the world
#
# R6 asks whether the stated artifact exists and the source-change gate asks
# whether the stated bytes moved.  Neither can see the two ways a run lies
# without writing the wrong thing:
#
#   * it does NOTHING and is still reported as an exact acceptance (measured:
#     "Create a git commit ... containing <dir>/util.py with the message ..."
#     returned PASS__...EXACT_SEMANTIC_ACCEPTANCE_VERIFIED with pass=True, no
#     commit, no change, and no artifact named for R6 to look for);
#   * it DELETES the file it was asked to edit and is still reported as an exact
#     acceptance (measured: "Rename the parameter text to value throughout the
#     python source <dir>/util.py" left the file GONE and passed; `rename` is not
#     in the repair verbs, so no digest was ever taken, and the report it wrote
#     satisfied R6).
#
# The kernel already had the machinery for both -- canonical/runtime/execute_v1.py
# snapshots the tree itself and names NO_EFFECT / OUT_OF_BOUNDS -- so this reuses
# its snapshot and diff rather than inventing a second observation.  Only the
# subtrees the sentence names are walked: a full-repository snapshot measured
# 188 ms here, which is more than the repair loop itself costs.
# A no-op is only a broken promise if the sentence promised a change.  Measured on
# 8f7e411c with the first version of this gate, which asked the question of every
# goal that named a path: ARCHIVE_VERIFY_GNU 3/3 -> 1/3, PDF_TEXT_EXTRACT 3/3 -> 0/3
# and SQLITE_VERIFY_RECORDS 3/3 -> 1/3 all became FAIL_CLOSED__NO_OBSERVED_EFFECT,
# because a verification answers with a verdict and writes nothing.  The refusal was
# measuring a promise those sentences never made.
# A no-op is only a broken promise if the sentence promised a FILE.  Two measured
# corrections live here:
#   * the first version asked the question of every goal naming a path, and
#     ARCHIVE_VERIFY_GNU, SQLITE_VERIFY_RECORDS and PDF_TEXT_EXTRACT fell 3/3 -> 0-1/3,
#     because verification answers with a verdict and pypdf answers with text;
#   * the second version asked it of every goal carrying a write-ish word, and
#     "Extract the text from <pdf> with pypdf" still failed for the same reason:
#     "extract" produces content, not a file.
# So the promise must be a FILESYSTEM result, read as one of exactly two things:
# a stated artifact path, or a change verb applied to a path that exists.
_CHANGE_VERB_RE = re.compile(
    r"\b(?:write|create|save|generate|build|add|update|modify|convert|compress|"
    r"repair|fix|patch|correct|commit|rename|move|copy|install|delete|remove|"
    r"refactor|format|reformat|apply|rewrite|replace|edit|produce|emit|make|"
    r"regenerate|restructure|in[- ]place)\b",
    re.IGNORECASE)
_DESTRUCTIVE_VERB_RE = re.compile(r"\b(?:delete|remove|move|rename|relocate|discard)\b", re.IGNORECASE)
# The words that make a move/rename/deletion about a SYMBOL rather than a file.
_SYMBOL_OBJECT_RE = re.compile(
    r"\b(?:function|method|class|symbol|parameter|variable|argument|attribute|"
    r"constant|import|definition|def)\b", re.IGNORECASE)
_OBSERVATION_MAX_FILES = 4000


def _stated_paths(goal: str) -> list[str]:
    """Every repository-relative path the sentence names, stated or to be created."""
    out: list[str] = []
    for raw, _path in goal_compiler._repo_paths(goal, ROOT):
        raw = str(raw)
        if front._CAPABILITY_ID_SHAPE.fullmatch(raw):
            continue
        if raw not in out:
            out.append(raw)
    return out


# A change verb is only an INSTRUCTION when it is used as one.  "Find every caller of the
# function add in <X>" contains the token "add"; reading that as a promise to change <X>
# refused the correct answer with NO_OBSERVED_EFFECT (measured 2026-10-29).  The verb is a
# noun when what follows it is a preposition or a bracket -- "add in", "add(", "insert of" --
# and an instruction when it takes an object: "Add a test", "fix <X>", "add retry ... to <X>".
_NON_IMPERATIVE_NEXT_WORDS = frozenset({
    "in", "of", "on", "at", "for", "with", "to", "from", "by", "as", "that", "which"})


def _sentence_promises_a_change(goal: str) -> bool:
    """Does the sentence USE a change verb, rather than merely contain one?"""
    text = str(goal or "")
    for m in _CHANGE_VERB_RE.finditer(text):
        tail = text[m.end():m.end() + 24].lstrip()
        if not tail:
            continue
        if tail.startswith("("):
            continue
        first = tail.split()[0].strip(",.:;").lower()
        if first in _NON_IMPERATIVE_NEXT_WORDS:
            continue
        return True
    return False


def _destructive_targets(goal: str) -> set[str]:
    """Paths whose ABSENCE the sentence asked for: deletion, or a move to a new name.

    The verb alone is not enough, and getting this wrong would disable the check
    that matters most.  Measured: "Rename the parameter text to value throughout
    the python source <p>" names <p> after the word "rename" but asks for the
    parameter to be renamed, not the file -- treating <p> as a deletion target
    would license the very deletion this gate exists to catch.  So a removal verb
    governs a path when the path is its direct object:

      * delete|remove|discard  - the path follows the verb closely;
      * move|rename|relocate   - the path follows the verb closely AND the
                                 sentence states where it goes ("to"/"into").
    """
    text = str(goal or "")
    paths = _stated_paths(goal)
    out: set[str] = set()
    for m in _DESTRUCTIVE_VERB_RE.finditer(text):
        verb = m.group(0).lower()
        for raw in paths:
            at = text.find(raw, m.end())
            if at < 0:
                continue
            gap = text[m.end():at]
            if len(gap.strip()) > 24 or "\n" in gap:
                continue
            if verb in ("move", "rename", "relocate"):
                tail = text[at + len(raw):at + len(raw) + 40].lstrip().lower()
                if not (tail.startswith("to ") or tail.startswith("into ")):
                    continue
                # The verb must govern the FILE.  "Move the function mul from <A> to <B>"
                # moves a symbol between modules; licensing <A>'s removal on that basis is
                # how a PASS was reported while <A> was deleted and the suite imported a
                # module that no longer existed.  Measured 2026-10-29.
                if _SYMBOL_OBJECT_RE.search(gap):
                    continue
            out.add(raw)
            break
    return out


def _git_head(path: Path) -> str:
    """The commit this path's repository is on, or '' when it is not one."""
    try:
        proc = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=10)
        return proc.stdout.strip() if proc.returncode == 0 else ""
    except Exception:  # noqa: BLE001 - no git is not an effect
        return ""


def _is_python_code(text: str) -> bool:
    """Is this still source, or has a JSON report been written over it?

    Syntax alone cannot answer that.  Measured: a report written over a module
    parses cleanly, because `{"cells": [], "x": 1}` is a valid Python expression --
    so a parse-only check would certify the corruption it exists to catch.  A
    module that is nothing but one literal expression is data, not code; real
    modules define, assign and import.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False
    body = tree.body
    if not body:
        return True
    if len(body) == 1 and isinstance(body[0], ast.Expr) and isinstance(
            body[0].value, (ast.Dict, ast.List, ast.Constant)):
        return False
    return True


def _observation_roots(goal: str) -> list[Path]:
    roots: list[Path] = []
    for raw in _stated_paths(goal) + _future_artifacts(goal):
        parent = (ROOT / raw).parent
        while not parent.is_dir() and parent != ROOT:
            parent = parent.parent
        if parent not in roots:
            roots.append(parent)
    # never walk a directory twice: a root that contains another root is dropped
    return [r for r in roots if not any(o != r and r in o.parents for o in roots)]


def observe_world(goal: str) -> dict[str, Any]:
    """What the filesystem looked like, read here rather than taken on report.

    Bounded on purpose: the walked subtrees are the ones the sentence names, and
    a subtree larger than _OBSERVATION_MAX_FILES is not walked at all (the path
    existence and parseability checks still run).  Nothing in the answer is the
    tool's own claim.
    """
    from canonical.runtime import execute_v1 as _kernel

    stated = _stated_paths(goal)
    files: dict[str, tuple[int, int]] = {}
    walked = []
    for root in _observation_roots(goal):
        try:
            count = sum(1 for _ in root.rglob("*"))
        except OSError:
            continue
        if count > _OBSERVATION_MAX_FILES:
            continue
        walked.append(str(root.relative_to(ROOT)) if root != ROOT else ".")
        for rel, stat_row in _kernel._snapshot(str(root)).items():
            files[str(Path(root, rel).relative_to(ROOT))] = stat_row
    parses: dict[str, bool] = {}
    for raw in stated:
        path = ROOT / raw
        if path.is_file() and path.suffix.lower() == ".py":
            parses[raw] = _is_python_code(path.read_text(encoding="utf-8", errors="replace"))
    head = _git_head(ROOT / stated[0]) if stated else ""
    return {"files": files, "walks": walked, "parses": parses,
            "git_head": head, "stated": stated}


def observed_effect_errors(goal: str, before: Mapping[str, Any],
                           after: Mapping[str, Any], result: Mapping[str, Any],
                           artifacts: list[str] | None = None) -> list[str]:
    """Did the run leave any evidence at all, and did it leave the tree intact?

    Three refusals, each measured on a real run:
      * NAMED_INPUT_REMOVED       - a file the sentence named is gone afterwards
                                    and no destructive verb governs it.
      * NAMED_SOURCE_UNPARSEABLE  - a .py the sentence named parsed before and
                                    does not parse now (writing JSON over a module
                                    makes "the bytes changed" true).
      * NO_OBSERVED_EFFECT        - nothing at all happened: no stated artifact on
                                    disk, no change in the stated subtrees, no new
                                    commit.  Only asked when the sentence names a
                                    path, so a goal that only asks for an answer
                                    is not accused of doing nothing.
    """
    errors: list[str] = []
    exempt = _destructive_targets(goal)
    for raw in before.get("parses") or {}:
        if raw in exempt:
            continue
        if not (ROOT / raw).is_file():
            errors.append("NAMED_INPUT_REMOVED:" + raw)
        elif before["parses"].get(raw) and after.get("parses", {}).get(raw) is False:
            errors.append("NAMED_SOURCE_UNPARSEABLE:" + raw)
    if result.get("pass") is True:
        # "Find every caller of the function ADD in <X>" carries the token "add", so a bare
        # change-verb test promised a file change and then refused a correct answer with
        # NO_OBSERVED_EFFECT.  Measured 2026-10-29: that sentence returned
        # FAIL_CLOSED__NO_OBSERVED_EFFECT from the symbol index -- the capability that answers
        # it -- and returned PASS before this, because writing its report over <X> counted as
        # "something happened".  The promise is read by the one reader that decides what a
        # sentence promised, not by a token scan of the sentence.
        promised_file = bool(artifacts) or bool(_promised_source_files(goal)) \
            or bool(_promised_source_roots(goal)) or _sentence_promises_a_change(goal)
        if promised_file:
            present = any((ROOT / a).is_file() for a in (artifacts or []))
            from canonical.runtime import execute_v1 as _kernel
            moved = _kernel._diff(before.get("files") or {}, after.get("files") or {})["changed"]
            committed = bool(after.get("git_head")) and after.get("git_head") != before.get("git_head")
            if not (present or moved or committed):
                errors.append("NO_OBSERVED_EFFECT")
    return errors


def _close_observations(result: dict[str, Any], goal: str,
                         before: Mapping[str, Any] | None,
                         artifacts: list[str] | None = None) -> dict[str, Any]:
    """Apply the filesystem's verdict to a result, wherever the result came from.

    The composed branch returns before the artifact and source-change gates run, so
    hanging this check only on the single-capability path left the measured lies
    untouched -- both of them were composed runs.  One function, called at every
    exit, is the only placement that cannot be bypassed by a new early return.
    """
    if not isinstance(result, dict) or result.get("pass") is not True or before is None:
        return result
    observed = observed_effect_errors(goal, before, observe_world(goal), result, artifacts)
    if not observed:
        return result
    result["runtime_status_before_observation_check"] = result.get("status")
    cls = observed[0].split(":", 1)[0]
    result["status"] = "FAIL_CLOSED__" + cls
    result["pass"] = False
    result["failure_class"] = cls
    result["observed_effect_errors"] = observed
    return result


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


def _undo_chain_side_effects(record: dict[str, Any], why: str) -> list[str]:
    """Remove the files a failed chain created, and say so in the record.

    `pass=False` must describe the repository as well as the report.  Measured
    2026-10-27 on the public runner, OUT_OF_SCOPE_MUST_FAIL_CLOSED scored 69/100 and
    every miss was `FAIL_OPEN_SIDE_EFFECT: wrote <file> while failing`: the verdict
    was fail-closed and the artifact was still there.
    """
    try:
        from canonical.runtime import composer_route_v1 as croute
        removed = croute.rollback_created(record)
    except Exception as exc:  # noqa: BLE001 - a rollback failure must not break the report
        # Named, never silent: a swallowed rollback error is indistinguishable from
        # "there was nothing to undo", which is exactly the failure this whole branch
        # exists to prevent.  Measured 2026-10-27: a NameError in the rollback was
        # hidden here and the leak looked like a no-op.
        record["side_effects_rollback_error"] = type(exc).__name__ + ":" + str(exc)[:200]
        removed = []
    if removed:
        record["side_effects_rolled_back"] = removed
        record["side_effects_rolled_back_because"] = why
    return removed


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
    # The chain is being declared a failure, so what it created must stop existing.
    # Otherwise the caller reports FAIL_CLOSED while the file it wrote sits on disk,
    # and the next reader cannot tell a refused goal from an executed one.
    _undo_chain_side_effects(composed, "promised_artifact_missing")
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
                                   ("steps", "produced", "status", "created_paths")},
            "capability_id": (routed["chain"] or [None])[-1],
            "elapsed_ns": perf_counter_ns() - started,
        }
    out = {
        "schema": LIVE_SCHEMA, "status": "PASS__COMPOSED_CAPABILITY_CHAIN",
        "pass": True, "task_id": task_id, "goal": goal,
        "executed": True, "execution_proof_type": COMPOSED_EXECUTOR,
        "composer_route": {k: routed.get(k) for k in ("token", "chain", "tried")},
        "composer_execution": {k: executed.get(k) for k in
                               ("steps", "produced", "status", "created_paths")},
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
        # Same rule, one branch later: the verifier refused the chain's output, so
        # the output must not survive the refusal.  This is the branch that scored
        # 31 of 100 out-of-scope goals as fail-open on the public runner
        # (2026-10-27): correct verdict, artifact left behind.
        _undo_chain_side_effects(out, "composed_chain_not_verified")
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


# A failed attempt is not a verdict.  Measured 2026-10-29 on a fresh tree::
#
#   "Rename the parameter old_price to price in the python module <util.py> and save the
#    report to <out.json>"
#     -> FAIL__LIVE_CONTROLLER_EXECUTION, capability document.convert.markdown_pdf.pandoc_weasyprint,
#        reason "Blocker:BOUND_APT_METADATA_NOT_FOUND:pandoc"
#
# The door had routed a Python refactor to a Markdown->PDF converter and failed to find apt
# metadata for pandoc.  A DECISIVE typed plan existed the whole time
# (python.refactor.rename_parameter.v1 -- it renames old_price and rewrites the body, verified
# here) and the retry that would have used it was blocked by `executed is True`.  That flag was
# protecting a real rule -- an honest verdict must never be overwritten by a second guess --
# but "the capability I picked could not run" is not a verdict about the world.
#
# So the retry stays refused for every failure a truth/observation gate produced (each of those
# fields is evidence that the world was judged), and for these classes by name.  Everything
# else is "could not do it yet", and a decisive plan may answer it.
_JUDGED_FAILURE_CLASSES = frozenset({
    "TOOL_REPORTED_NON_SUCCESS", "PROMISED_ARTIFACT_MISSING",
    "PROMISED_SOURCE_CHANGE_NOT_APPLIED", "NAMED_INPUT_REMOVED",
    "NAMED_SOURCE_UNPARSEABLE", "NO_OBSERVED_EFFECT",
    "STATED_ANSWER_NOT_PROVIDED",
    "STATED_SECURITY_REVIEW_NOT_PROVIDED_BY_CAPABILITY",
    "STATED_COVERAGE_NOT_MEASURED_BY_CAPABILITY",
    # A step that RAISED left the world in a state nobody observed
    # (``side_effect_landed: UNKNOWN`` in the composer's own record).  Running a different
    # capability on top of that could compound an edit nobody has seen, so it is not a
    # "could not reach it" failure even though it produced no verdict.
    "COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN",
    "STEP_RAISED_OUTCOME_UNKNOWN", "COMPOSER_STEP_RAISED",
})
# The composer GUESSED a chain, ran it, and then said it could not verify the result
# (``NO_INDEPENDENT_REINSPECTION_FOR:<cid>``).  Measured 2026-10-29 on "Lint the python file X":
# the composer reached code.multilanguage.parse.tree_sitter.v1 -- a parser, not a lint gate -- and
# the door refused with COMPOSED_CHAIN_NOT_VERIFIED while a DECISIVE typed plan for
# python.review.diff_static_triage.v1 existed.  That is a guess that judged nothing about the
# request, so a decisive plan may answer it -- but only when the guess touched NOTHING of the
# caller's: every step completed (nothing raised, no ``side_effect_landed: UNKNOWN``) and every
# artifact it named lives under this repository's own spool directory.  A chain that wrote inside
# the tree the request named is a world nobody has seen, and it stays un-retryable.
#
# ``STEP_RAISED_OUTCOME_UNKNOWN`` belongs to the same class, by its own name: the composer ran a
# step and the outcome is UNKNOWN, i.e. it claims nothing about the request.  Measured 2026-10-29
# on "Measure the test coverage of <file>": the composed chain parsed the file with tree-sitter and
# then ran ``python.repository.acceptance.measure.v1``, which raised
# ``MeasurementError:NO_TEST_FILES_UNDER_SOURCE_ROOT``.  That raise made the attempt "executed and
# un-retryable", so a decisive typed plan for ``python.review.diff_coverage_gate.v1`` was never
# allowed to answer, and the caller was told the outcome was unknown when a capability that
# measures exactly this existed.  A raise is not a side effect; what matters is what landed.
_COMPOSED_UNVERIFIED_CLASSES = frozenset({"COMPOSED_CHAIN_NOT_VERIFIED",
                                          "STEP_RAISED_OUTCOME_UNKNOWN"})
_SPOOL_DIR_PREFIX = "canonical/astra_runtime/tmp/"


def _composed_wrote_only_its_own_scratch(result: Mapping[str, Any]) -> bool:
    steps = list(((result.get("composer_execution") or {}).get("steps") or []))
    if not steps:
        return False
    # Evidence of the world, not of the code path: anything the chain says it CREATED outside the
    # spool is a world nobody has seen, and then it stays un-retryable.
    for created in (((result.get("composer_execution") or {}).get("created_paths")) or []):
        if isinstance(created, str) and created.strip() and not created.startswith(_SPOOL_DIR_PREFIX):
            return False
    for row in steps:
        if not isinstance(row, Mapping):
            return False
        # A raised step is allowed (see above); a step that reports a landed side effect or that
        # produced no result at all is not evidence that nothing happened.
        if row.get("side_effect_landed") or (row.get("result") is None and not row.get("adapter_raised")):
            return False
        args = row.get("args") or {}
        for key in ("output_path", "result_path"):
            value = args.get(key)
            if isinstance(value, str) and value.strip() and not value.startswith(_SPOOL_DIR_PREFIX):
                return False
    return True
_JUDGED_EVIDENCE_FIELDS = (
    "tool_truth_errors", "observed_effect_errors", "promised_source_change_errors",
    "promised_artifact_errors", "stated_answer_errors",
)
# The one executed failure that IS "could not reach it": the adapter stopped on a stated
# precondition before doing any work, and says so with this marker.
_PRECONDITION_BLOCKER_RE = re.compile(r"\bBlocker:")


def _may_supersede_a_failed_attempt(result: Mapping[str, Any]) -> bool:
    """Did this failed attempt actually JUDGE the world, or did it just fail to reach it?

    Two ways to be a verdict, and either one forbids the retry: a named judged failure
    class, or any observation/truth/promise gate that spoke.  Beyond that, an attempt that
    EXECUTED is only re-tryable when it stopped on a stated precondition blocker -- the
    world it left behind is then the world it found.
    """
    if result.get("pass") is True:
        return False
    failure_class = str(result.get("failure_class") or "")
    # THE ANSWER GATE JUDGES ONE CAPABILITY, SO ITS REFUSAL IS NOT A VERDICT ABOUT THE WORLD.
    #
    # ``stated_answer_errors`` is a statement about the row that was about to run: "this row does
    # not provide the effect the sentence states".  When the only evidence in the refusal is that
    # judgement AND nothing executed, the door has learned that its ROUTING was wrong, not that the
    # request cannot be served -- and a decisive typed selection (exactly one row that binds every
    # stated input) is the evidence that a better row exists.  The retry re-enters the SAME gate
    # chain, so the answer gate is asked again about the row that actually answers: nothing can
    # slip through, and the refusal is not weakened, only redirected.
    #
    # Measured 2026-10-29: "Measure the test coverage of <a file whose directory has no tests>"
    # compiled to code.impact.tree_sitter.testselect.v1, which was refused pre-execution with
    # STATED_COVERAGE_NOT_MEASURED_BY_CAPABILITY:UNNAMED, and that refusal -- about the wrong row --
    # stopped the retry from running python.review.diff_coverage_gate.v1, the one capability that
    # measures coverage, whose own honest answer is NO_TESTS_DISCOVERED.
    _only_answer_gate = (result.get("executed") is not True
                         and result.get("refused_before_execution") is True
                         and bool(result.get("stated_answer_errors"))
                         and not any(result.get(field) for field in _JUDGED_EVIDENCE_FIELDS
                                     if field != "stated_answer_errors"))
    if _only_answer_gate:
        return True
    # A REFUSAL THAT MEASURED THE TREE UNCHANGED IS NOT A VERDICT ABOUT THE TREE.
    #
    # ``PROMISED_SOURCE_CHANGE_NOT_APPLIED`` is in the judged set because a repair loop that
    # no-ops must not be re-run on top of a half-edited file.  But when the ONLY promise that
    # failed is ``PROMISED_SOURCE_UNCHANGED:<path>``, the door itself has just proven that no byte
    # moved -- there is nothing to compound, and the request is still unanswered.  Measured
    # 2026-10-30: "Rename the symbol ``mul`` to ``multiply`` in <file>" was answered by a read-only
    # symbol INDEX (which cannot rename anything), and the refusal was read as a verdict, so the
    # typed plan that performs the rename -- verified to edit every referencing file -- never ran.
    if failure_class == "PROMISED_SOURCE_CHANGE_NOT_APPLIED":
        _promises = [str(x) for x in (result.get("promised_source_change_errors") or [])]
        if _promises and all(x.startswith("PROMISED_SOURCE_UNCHANGED:") for x in _promises):
            return True
    if any(result.get(field) for field in _JUDGED_EVIDENCE_FIELDS):
        return False
    if failure_class in _COMPOSED_UNVERIFIED_CLASSES:
        return _composed_wrote_only_its_own_scratch(result)
    if failure_class in _JUDGED_FAILURE_CLASSES:
        return False
    if result.get("executed") is True:
        stated = "%s %s" % (result.get("reason") or "", result.get("failure_reason") or "")
        return bool(_PRECONDITION_BLOCKER_RE.search(stated))
    return True


def solve(request: Mapping[str, Any]) -> dict[str, Any]:
    """THE live Brain entry, now with a scoped, ambiguity-preserving typed-SWE retry.

    The PRIMARY path below (``_solve_body``) is unchanged: front-compile -> admit
    -> execute -> the full observation gate chain.  Only when it FAILS BEFORE
    EXECUTING anything, the request is an explicit software-engineering request,
    and the hidden typed selector ``capability_selection_retrieval_v1.select`` is
    DECISIVE, does a second attempt run -- re-entering the SAME ``_solve_body``
    gate chain with a fully-bound typed plan (see ``swe_typed_plan_v1``).

    Measured 2026-10-27: on five fresh human SWE sentences the primary door
    routed to PDF/document converters and refused; the typed retry reaches the
    capability the sentence actually names and runs the same honesty gates.
    Nothing is widened: a non-decisive (ambiguous) selector returns no plan and
    the original refusal stands; an executed verdict is never overwritten; a
    non-SWE goal never reaches the retry (three pinned front-door refusals were
    verified non-SWE).  Zero model dependency, zero incremental spend.
    """
    result = _solve_body(request)
    if result.get("pass") is True or (request or {}).get("_typed_swe_plan") is not None:
        return result
    # A retry is only for "could not route/bind yet".  An honest verdict -- a truth gate,
    # an observation gate, a promise gate, or a named judged failure class -- already asked
    # the world and got an answer; a second guess must never overwrite it.  An attempt that
    # merely FAILED to reach a capability is not a verdict, and a decisive plan may answer it.
    if result.get("executed") is True and not _may_supersede_a_failed_attempt(result):
        return result
    goal = str((request or {}).get("goal") or "").strip()
    try:
        from canonical.runtime import swe_typed_plan_v1 as _typed_plan
        if not _typed_plan.is_swe_request(goal):
            return result
        plan = _typed_plan.build_plan(goal, ROOT)
        if plan is None:  # ambiguous or no bindable proposal -> keep fail-closed
            return result
        retry_request = dict(request)
        retry_request["_typed_swe_plan"] = plan
        retry = _solve_body(retry_request)
        # A RETRY THAT REACHED A DIFFERENT CAPABILITY IS THE ANSWER, refusal or not.
        #
        # Only a PASS used to be returned.  A capability that refuses for its own reason
        # (``NO_TESTS_DISCOVERED``, a stated precondition) refused with ``executed: False``, so the
        # caller was handed the PRIMARY's status -- a refusal about a row that had nothing to do
        # with the request.  The retry ran the row the sentence actually names and the report said
        # something else.  The primary did not execute anything here (that is a precondition of the
        # retry), so there is no verdict to overwrite.
        _retry_is_the_answer = (
            retry.get("pass") is True
            or retry.get("executed") is True
            or bool(retry.get("refusal_payload"))
            or bool(retry.get("reviewed"))
            or (_capability_id_of(retry) and _capability_id_of(retry) != _capability_id_of(result))
        )
        if _retry_is_the_answer:
            retry["typed_swe_retry"] = {
                "schema": "SWE_TYPED_RETRY_V1",
                "primary_status": result.get("status"),
                "selected_capability": plan[2].get("selected_capability"),
                "admission_basis": "DECISIVE_TYPED_SELECTION_REENTERED_FULL_GATE_CHAIN",
                "returned_because": "THE_RETRY_REACHED_THE_CAPABILITY_THE_SENTENCE_NAMES",
                "model_dependency_count": 0,
                "incremental_spend_usd": 0,
            }
            return retry
        if retry.get("pass") is not True and retry.get("executed") is True:
            # THE RETRY RAN THE WORK AND ITS VERDICT WAS THROWN AWAY.
            #
            # Only a PASS used to be returned, so when the typed plan reached the RIGHT capability
            # and that capability executed but could not certify (measured 2026-10-29: a security
            # review that really ran and really found `shell=True`), the caller was told
            # FAIL__RAW_GOAL_COMPILATION_GAP -- "I could not turn this into an executable
            # contract" -- about a review that had just run.  Same class as the composed-chain
            # fix: the report must not deny work that happened.  `pass` stays False; the retry's
            # own status, reason and evidence are what the caller gets.
            retry["typed_swe_retry"] = {
                "schema": "SWE_TYPED_RETRY_V1",
                "primary_status": result.get("status"),
                "selected_capability": plan[2].get("selected_capability"),
                "admission_basis": "DECISIVE_TYPED_SELECTION_REENTERED_FULL_GATE_CHAIN",
                "returned_because": "THE_RETRY_EXECUTED_AND_ITS_VERDICT_IS_THE_ONE_TO_REPORT",
                "model_dependency_count": 0,
                "incremental_spend_usd": 0,
            }
            return retry
        if retry.get("pass") is True:
            retry["typed_swe_retry"] = {
                "schema": "SWE_TYPED_RETRY_V1",
                "primary_status": result.get("status"),
                "selected_capability": plan[2].get("selected_capability"),
                "admission_basis": "DECISIVE_TYPED_SELECTION_REENTERED_FULL_GATE_CHAIN",
                "model_dependency_count": 0,
                "incremental_spend_usd": 0,
            }
            return retry
    except Exception:  # any fault in the OPTIONAL retry keeps the primary verdict
        pass
    return result


def _capability_id_of(result: Mapping[str, Any]) -> str:
    """The capability a result is ABOUT, whichever key the path used to name it."""
    for key in ("compiled_capability_id", "capability_id", "selected_capability"):
        value = str((result or {}).get(key) or "").strip()
        if value:
            return value
    return ""


def _decisive_typed_plan(goal: str) -> Any:
    """The hidden typed selector's decisive plan for this sentence, or None.

    Advisory only: any fault (or a non-SWE sentence, or an ambiguous shortlist) returns None and
    the caller keeps its original path.
    """
    try:
        from canonical.runtime import swe_typed_plan_v1 as _typed_plan
        if not _typed_plan.is_swe_request(goal):
            return None
        return _typed_plan.build_plan(goal, ROOT)
    except Exception:  # noqa: BLE001 - a working guess beats a broken advisory
        return None


def _solve_body(request: Mapping[str, Any]) -> dict[str, Any]:
    """Primary front-compile -> admit -> execute -> tool truth -> promised artifacts."""
    started = perf_counter_ns()
    task_id = str((request or {}).get("task_id") or "").strip()
    goal = str((request or {}).get("goal") or "").strip()
    if not task_id or not goal:
        return _fail(task_id, "FAIL_CLOSED", "REQUEST_INVALID", started)
    _typed_plan = (request or {}).get("_typed_swe_plan")
    try:
        if _typed_plan is not None:
            registry, admissible, compiled = _typed_plan
        else:
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
        # A DECISIVE TYPED PLAN IS NOT A CHAIN SENTENCE.
        #
        # Composition exists for a sentence no single capability answers.  A decisive typed
        # selection is the opposite evidence: exactly one capability binds every input the
        # sentence states.  Composing anyway means running a GUESS, and a guess that raises
        # records ``side_effect_landed: UNKNOWN`` -- which correctly forbids a later retry, so
        # the decisive plan never got to answer.  Measured 2026-10-29 on "Measure the test
        # coverage of <file>": the guess parsed the file with tree-sitter and then ran
        # ``python.repository.acceptance.measure.v1``, which raised
        # ``MeasurementError:NO_TEST_FILES_UNDER_SOURCE_ROOT``, and the sentence was answered
        # FAIL_CLOSED__COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN while
        # ``python.review.diff_coverage_gate.v1`` bound and executed.  Ask the typed selector
        # BEFORE guessing; a non-decisive selector returns None and composition runs unchanged.
        if _typed_plan is None:
            _pre = _decisive_typed_plan(goal)
            if _pre is not None:
                _pre_request = dict(request)
                _pre_request["_typed_swe_plan"] = _pre
                _pre_result = _solve_body(_pre_request)
                _pre_result["typed_plan_before_composed_guess"] = {
                    "schema": "SWE_TYPED_PLAN_PRECEDES_COMPOSITION_V1",
                    "selected_capability": _pre[2].get("selected_capability"),
                    "why": "A_DECISIVE_TYPED_SELECTION_BINDS_EVERY_STATED_INPUT_SO_NO_CHAIN_IS_NEEDED",
                    "model_dependency_count": 0, "incremental_spend_usd": 0,
                }
                return _pre_result
        gap_normalized = front.normalize_goal(goal)
        gap_future_artifacts = _future_artifacts(gap_normalized)
        # THE SNAPSHOT THE CHAIN IS JUDGED AGAINST HAS TO EXIST BEFORE THE CHAIN RUNS.
        #
        # This branch passed `observe_world(...)` AFTER `_try_composed` had already executed, so
        # "before" and "after" were the same walk of the same tree and every composed run was
        # accused of NO_OBSERVED_EFFECT -- the mirror image of the failure this gate exists to
        # catch: not a report accepted as a change, but a change reported as nothing happening.
        # Measured 2026-10-29: "Format <a badly formatted .py>" ran `ruff format`, rewrote the
        # file (28 -> 32 bytes, output_verified true) and came back
        # FAIL_CLOSED__NO_OBSERVED_EFFECT; the same sentence over an already-formatted file was
        # indistinguishable from it.  The main path below has always taken this snapshot first.
        gap_world_before = observe_world(gap_normalized)
        composed = _try_composed(task_id, goal, started)
        if composed is not None:
            return _close_observations(
                _composed_holds_up(composed, gap_normalized, gap_future_artifacts),
                gap_normalized, gap_world_before, gap_future_artifacts)
        return _fail(task_id, "FAIL__RAW_GOAL_COMPILATION_GAP", "RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP", started,
                     compiler_code=exc.code, compiler_detail=exc.detail, route_admission=None)
    except Exception as exc:  # pragma: no cover - defensive, mirrors run_raw_goal
        return _fail(task_id, "FAIL_CLOSED", "RAW_GOAL_INTEGRATION_RUNTIME_ERROR", started, reason=type(exc).__name__ + ":" + str(exc))
    normalized = front.normalize_goal(goal)
    future_artifacts = _future_artifacts(normalized)
    # ask memory what it knows about work like this, before deciding anything
    recalled = _recall_for(normalized)
    # Taken before ANY branch can execute, so the composed early-returns are held to
    # the same evidence as the single-capability path.
    world_before = observe_world(normalized)
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
        # The symmetric case, measured.  A sentence can state BOTH a payload and
        # the path it goes to, and still be refused for a reason that has
        # nothing to do with the binder -- so this gate, which required
        # typed_binding_refused, never fired and composition never ran:
        #
        #   "Write the text 'PROJECT BRAIN' to the target file X"
        #       -> FAIL_CLOSED__ROUTE_ADMISSION_REJECTED, zero steps, no verdict
        #
        # while the same sentence phrased "to the file X" ran and was verified.
        # The payload and the destination are both re-derived from the sentence
        # here, exactly as the command line is, and both are then independently
        # checked: _payload_runs_to_the_destination refuses a payload the
        # sentence does not actually run to the destination, and the written
        # bytes are compared against the sentence rather than the argument.  So
        # a payload with a stated destination is as grounded as a stated command
        # line, and refusing it fails a request the machine can do.
        #
        # A payload with NO stated destination is deliberately not enough --
        # that is the #6119 shape, where the only path in the sentence becomes
        # the destination by default and a file is overwritten by a report about
        # it.  "Check the file X" states no payload at all, so it keeps failing
        # closed for the reason it always has.
        states_a_payload_and_its_destination = (
            composer_route.extract_content(normalized) is not None
            and composer_route.extract_content_destination(normalized) is not None)
        if (stated_a_command_line or states_a_payload_and_its_destination
                or (admission.get("typed_binding_refused") is True
                    and composer_route.extract_content(normalized) is not None)):
            composed = _try_composed(task_id, goal, started)
            if composed is not None:
                return _close_observations(
                    _composed_holds_up(composed, normalized, future_artifacts),
                    normalized, world_before, future_artifacts)
        return _fail(task_id, "FAIL_CLOSED__ROUTE_ADMISSION_REJECTED",
                     "ROUTE_ADMISSION_REJECTED:" + str(admission.get("rule")), started, **_extra)
    # Ask the DECLARATION before spending the run.  The same gate already exists after execution
    # (``stated_answer_errors`` in the observation chain); asking it first is strictly better, because
    # a capability that cannot answer must not touch the tree at all, and the typed retry is then free
    # to reach the capability that does answer (``executed`` is False, so no verdict is overwritten).
    _declared = str(compiled.get("capability_id") or compiled.get("selected_capability") or "")
    # Only a capability that was actually about to run can be refused for not answering: with no
    # compiled capability there is no claim to reject, and the request keeps its own refusal.
    declared_answer_errors = (stated_answer_errors(normalized, dict(admissible.get(_declared) or {}))
                              if _declared else [])
    if declared_answer_errors:
        refused = _fail(task_id, "FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED",
                        "STATED_ANSWER_NOT_PROVIDED:" + ";".join(declared_answer_errors), started,
                        compiled_capability_id=_declared, executed=False)
        refused["stated_answer_errors"] = declared_answer_errors
        refused["refused_before_execution"] = True
        return refused
    promised_sources = _promised_source_files(normalized)
    source_digests_before = {raw: _source_digest(raw) for raw in promised_sources}
    promised_roots = _promised_source_roots(normalized)
    roots_before = {root: {rel: _source_digest(rel) for rel in _py_files_under(root)}
                    for root in promised_roots}
    try:
        result = _execute(task_id, goal, compiled, admissible, started)
    except SystemExit as exc:
        # Every handler on this path catches Exception, and SystemExit derives from
        # BaseException, so a capability whose adapter calls sys.exit() did not fail
        # closed -- it terminated the CALLER. Measured on
        # "Generate the test scaffold for the python source root D": the capability
        # was selected correctly and then escaped solve() as an uncaught SystemExit.
        # A front door that raises is worse than one that refuses.
        # A STRUCTURED REFUSAL IS NOT A CRASH.
        #
        # The repository's adapters refuse with ``raise SystemExit(json.dumps({"error": true,
        # "reason": ...}))``.  Reporting that as CAPABILITY_EXITED_PROCESS threw the reason away:
        # measured 2026-10-29, "measure the test coverage of <a directory with no tests>" came back
        # with an empty reason while the adapter had said, in JSON, ``NO_TESTS_DISCOVERED``.  The
        # verdict is still a closed failure -- nothing widens -- but it now names what the
        # capability refused for.
        _payload = str(exc)
        try:
            _decoded = json.loads(_payload)
        except (ValueError, TypeError):
            _decoded = None
        if isinstance(_decoded, Mapping) and _decoded.get("error") is True:
            _why = str(_decoded.get("reason") or "UNSPECIFIED").strip()[:200]
            return _fail(task_id, "FAIL_CLOSED__CAPABILITY_REFUSED_" + _why.split(":")[0][:60],
                         "CAPABILITY_REFUSED:" + _why, started,
                         compiled_capability_id=str(compiled.get("capability_id")
                                                    or compiled.get("selected_capability") or ""),
                         refusal_payload=dict(_decoded))
        return _fail(task_id, "FAIL_CLOSED__CAPABILITY_EXITED_PROCESS",
                     "CAPABILITY_EXITED_PROCESS:" + _payload[:300], started,
                     compiled_capability_id=str(compiled.get("capability_id")
                                                or compiled.get("selected_capability") or ""))
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
            return _close_observations(
                _composed_holds_up(composed, normalized, future_artifacts),
                normalized, world_before, future_artifacts)
        result["runtime_status_before_artifact_check"] = result.get("status")
        cls = promised_artifact_class(missing)
        result["status"] = "FAIL_CLOSED__" + cls
        result["pass"] = False
        result["failure_class"] = cls
        result["promised_artifact_errors"] = missing
    stated_files = _stated_files(normalized)
    patch_evidence = future_artifacts + [p for p in stated_files if p not in future_artifacts]
    unchanged = promised_source_change_errors(
        normalized, source_digests_before, patch_evidence,
        roots_before=roots_before, before_files=world_before.get("files")) \
        if result.get("pass") is True else []
    if unchanged:
        result["runtime_status_before_source_change_check"] = result.get("status")
        result["status"] = "FAIL_CLOSED__PROMISED_SOURCE_CHANGE_NOT_APPLIED"
        result["pass"] = False
        result["failure_class"] = "PROMISED_SOURCE_CHANGE_NOT_APPLIED"
        result["promised_source_change_errors"] = unchanged
    _answered_by = str(result.get("compiled_capability_id")
                       or result.get("capability_id") or "")
    unanswered = stated_answer_errors(
        normalized, dict(admissible.get(_answered_by) or {})) \
        if result.get("pass") is True else []
    if unanswered:
        result["runtime_status_before_answer_check"] = result.get("status")
        result["status"] = "FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED"
        result["pass"] = False
        result["failure_class"] = "STATED_ANSWER_NOT_PROVIDED"
        result["stated_answer_errors"] = unanswered
    # The third authority: what the filesystem says, not what the tool says.  A
    # run that did nothing, or that removed the file it was asked to edit, has no
    # claim to an exact acceptance no matter how clean its own report is.
    observed = observed_effect_errors(normalized, world_before, observe_world(normalized),
                                      result, future_artifacts) \
        if result.get("pass") is True else []
    if observed:
        result["runtime_status_before_observation_check"] = result.get("status")
        cls = observed[0].split(":", 1)[0]
        result["status"] = "FAIL_CLOSED__" + cls
        result["pass"] = False
        result["failure_class"] = cls
        result["observed_effect_errors"] = observed
    result["elapsed_ns"] = perf_counter_ns() - started
    return _close_observations(result, normalized, world_before, future_artifacts)


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
