"""Compile a deterministic capability execution into a verified state/provenance capsule.

This is the runtime bridge between:
  * capability_planner.py's symbolic require/provide graph,
  * astra_runtime.py's concrete controller trace, and
  * composition_state_capsule_v1.py's append-only provenance normal form.

The verifier is deliberately fail-closed.  It grants no capability credit and
does not claim semantic correctness beyond the already-verified bound capability
contracts.  Its job is narrower: prove that every accepted planned transition
has a witnessed result, that every declared prerequisite has an earlier witness
(or verified initial-fact origin), that every explicit prior-result data edge
points backward to a declared provider field, and that the complete executed
history compiles to one content-addressed capsule.
"""
from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from canonical.runtime.composition_state_capsule_v1 import (
    append_macrostep,
    empty_capsule,
    verify_capsule,
)

SCHEMA = "PROJECT_BRAIN_CAPABILITY_EXECUTION_TRACE_CAPSULE_V1"


class TraceCapsuleError(ValueError):
    pass


def _canon_sha256(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _tokens(value: Any, label: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise TraceCapsuleError(label + "_INVALID")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise TraceCapsuleError(label + "_ITEM_INVALID")
        out.append(item.strip())
    if len(out) != len(set(out)):
        raise TraceCapsuleError(label + "_DUPLICATE")
    return out


def _result_refs(value: Any, path: str = "") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if isinstance(value, Mapping):
        if set(value) == {"$result"}:
            spec = value["$result"]
            if not isinstance(spec, Mapping):
                raise TraceCapsuleError("RESULT_REFERENCE_INVALID:" + path)
            try:
                cycle = int(spec.get("cycle", -1))
            except Exception as exc:
                raise TraceCapsuleError("RESULT_REFERENCE_CYCLE_INVALID:" + path) from exc
            field = str(spec.get("field") or "").strip()
            if cycle < 0 or not field:
                raise TraceCapsuleError("RESULT_REFERENCE_INVALID:" + path)
            out.append({"path": path, "cycle": cycle, "field": field})
            return out
        for key, item in value.items():
            child = str(key) if not path else path + "." + str(key)
            out.extend(_result_refs(item, child))
        return out
    if isinstance(value, list):
        for index, item in enumerate(value):
            child = f"{path}[{index}]" if path else f"[{index}]"
            out.extend(_result_refs(item, child))
    return out


def _resolve_result_refs(value: Any, trace_prefix: Sequence[Mapping[str, Any]]) -> Any:
    if isinstance(value, Mapping):
        if set(value) == {"$result"}:
            spec = value["$result"]
            if not isinstance(spec, Mapping):
                raise TraceCapsuleError("RESULT_REFERENCE_INVALID")
            try:
                cycle = int(spec.get("cycle", -1))
            except Exception as exc:
                raise TraceCapsuleError("RESULT_REFERENCE_CYCLE_INVALID") from exc
            if cycle < 0 or cycle >= len(trace_prefix):
                raise TraceCapsuleError("RESULT_REFERENCE_CYCLE_INVALID:" + str(cycle))
            record = trace_prefix[cycle]
            if not isinstance(record, Mapping):
                raise TraceCapsuleError("TRACE_RECORD_INVALID:" + str(cycle))
            current = record.get("result")
            field = str(spec.get("field") or "").strip()
            if not field:
                raise TraceCapsuleError("RESULT_REFERENCE_FIELD_REQUIRED")
            for part in field.split("."):
                if not isinstance(current, Mapping) or part not in current:
                    raise TraceCapsuleError(
                        "RESULT_REFERENCE_FIELD_MISSING:" + str(cycle) + ":" + field
                    )
                current = current[part]
            return copy.deepcopy(current)
        return {
            str(key): _resolve_result_refs(item, trace_prefix)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_resolve_result_refs(item, trace_prefix) for item in value]
    return copy.deepcopy(value)


def _expectation_passes(action: Mapping[str, Any], result: Mapping[str, Any]) -> bool:
    expect = action.get("expect")
    if not isinstance(expect, Mapping):
        return False
    field = str(expect.get("field") or "").strip()
    if not field:
        return False
    value = result.get(field)
    typ = str(expect.get("type") or "field_nonempty")
    if typ == "field_nonempty":
        return value not in (None, "", [], {})
    if typ == "field_contains":
        return str(expect.get("value", "")) in str(value or "")
    if typ == "field_equals":
        return value == expect.get("value")
    return False


def verify_and_compile(
    problem: Mapping[str, Any],
    planned: Mapping[str, Any],
    execution: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        if not isinstance(problem, Mapping):
            raise TraceCapsuleError("PROBLEM_INVALID")
        if not isinstance(planned, Mapping):
            raise TraceCapsuleError("PLANNED_INVALID")
        if not isinstance(execution, Mapping):
            raise TraceCapsuleError("EXECUTION_INVALID")

        raw_capabilities = problem.get("capabilities")
        if not isinstance(raw_capabilities, list) or not raw_capabilities:
            raise TraceCapsuleError("CAPABILITIES_INVALID")
        caps: dict[str, Mapping[str, Any]] = {}
        for raw in raw_capabilities:
            if not isinstance(raw, Mapping):
                raise TraceCapsuleError("CAPABILITY_NOT_OBJECT")
            cid = str(raw.get("id") or "").strip()
            if not cid or cid in caps:
                raise TraceCapsuleError("CAPABILITY_ID_INVALID_OR_DUPLICATE:" + cid)
            _tokens(raw.get("requires") or [], cid + "_REQUIRES")
            provides = _tokens(raw.get("provides") or [], cid + "_PROVIDES")
            if not provides:
                raise TraceCapsuleError("CAPABILITY_PROVIDES_EMPTY:" + cid)
            _tokens(raw.get("result_fields") or [], cid + "_RESULT_FIELDS")
            if not isinstance(raw.get("action"), Mapping):
                raise TraceCapsuleError("CAPABILITY_ACTION_INVALID:" + cid)
            caps[cid] = raw

        planning = planned.get("planning")
        raw_actions = planned.get("actions")
        if not isinstance(planning, Mapping) or not isinstance(raw_actions, list):
            raise TraceCapsuleError("PLANNING_SHAPE_INVALID")
        plan_ids = _tokens(planning.get("plan") or [], "PLAN")
        if len(raw_actions) != len(plan_ids) + 1:
            raise TraceCapsuleError("PLANNED_ACTION_COUNT_MISMATCH")

        trace = execution.get("trace")
        if not isinstance(trace, list) or len(trace) != len(raw_actions):
            raise TraceCapsuleError("EXECUTION_TRACE_COUNT_MISMATCH")

        facts = set(_tokens(problem.get("initial_facts") or [], "INITIAL_FACTS"))
        targets = set(_tokens(problem.get("target_effects") or [], "TARGET_EFFECTS"))
        if not targets:
            raise TraceCapsuleError("TARGET_EFFECTS_EMPTY")

        providers: dict[str, dict[str, Any]] = {
            effect: {
                "origin": "VERIFIED_INITIAL_FACT",
                "cycle": None,
                "capability_id": None,
                "result_sha256": None,
            }
            for effect in facts
        }

        capsule = empty_capsule()
        transition_receipts: list[dict[str, Any]] = []
        explicit_result_edge_count = 0

        for cycle, raw_action in enumerate(raw_actions):
            if not isinstance(raw_action, Mapping):
                raise TraceCapsuleError("RAW_ACTION_NOT_OBJECT:" + str(cycle))
            record = trace[cycle]
            if not isinstance(record, Mapping) or record.get("cycle") != cycle:
                raise TraceCapsuleError("TRACE_CYCLE_INVALID:" + str(cycle))
            result = record.get("result")
            resolved_action = record.get("plan")
            if not isinstance(result, Mapping) or not isinstance(resolved_action, Mapping):
                raise TraceCapsuleError("TRACE_PLAN_OR_RESULT_INVALID:" + str(cycle))

            expected_resolved = _resolve_result_refs(raw_action, trace[:cycle])
            if resolved_action != expected_resolved:
                raise TraceCapsuleError("RESOLVED_ACTION_MISMATCH:" + str(cycle))

            action_type = str(raw_action.get("type") or "").strip()
            if cycle == len(raw_actions) - 1:
                if action_type != "finish":
                    raise TraceCapsuleError("FINAL_ACTION_NOT_FINISH")
                summary = str(result.get("summary") or "").strip()
                if not summary:
                    raise TraceCapsuleError("FINISH_SUMMARY_EMPTY")
                continue

            if action_type == "finish":
                raise TraceCapsuleError("EARLY_FINISH:" + str(cycle))

            cid = str(raw_action.get("capability_id") or "").strip()
            if cid != plan_ids[cycle]:
                raise TraceCapsuleError("PLAN_CAPABILITY_ID_MISMATCH:" + str(cycle))
            cap = caps.get(cid)
            if cap is None:
                raise TraceCapsuleError("PLANNED_CAPABILITY_UNKNOWN:" + cid)

            requires = _tokens(cap.get("requires") or [], cid + "_REQUIRES")
            provides = _tokens(cap.get("provides") or [], cid + "_PROVIDES")
            result_fields = _tokens(
                cap.get("result_fields") or [], cid + "_RESULT_FIELDS"
            )
            missing = sorted(set(requires) - facts)
            if missing:
                raise TraceCapsuleError(
                    "RUNTIME_PRECONDITION_WITNESS_MISSING:"
                    + cid
                    + ":"
                    + ",".join(missing)
                )

            if result.get("error"):
                raise TraceCapsuleError("ACTION_RESULT_ERROR:" + cid)
            if not _expectation_passes(raw_action, result):
                raise TraceCapsuleError("ACTION_EFFECT_EXPECTATION_NOT_WITNESSED:" + cid)

            refs = _result_refs(raw_action)
            explicit_edges: list[dict[str, Any]] = []
            for ref in refs:
                source_cycle = int(ref["cycle"])
                field = str(ref["field"])
                if source_cycle >= cycle:
                    raise TraceCapsuleError(
                        "RESULT_REFERENCE_NOT_STRICTLY_PRIOR:"
                        + cid
                        + ":"
                        + str(source_cycle)
                    )
                producer_cid = plan_ids[source_cycle]
                producer = caps.get(producer_cid)
                if producer is None:
                    raise TraceCapsuleError(
                        "RESULT_REFERENCE_PRODUCER_UNKNOWN:" + producer_cid
                    )
                producer_fields = set(
                    _tokens(
                        producer.get("result_fields") or [],
                        producer_cid + "_RESULT_FIELDS",
                    )
                )
                if field.split(".")[0] not in producer_fields:
                    raise TraceCapsuleError(
                        "RESULT_REFERENCE_FIELD_UNDECLARED:"
                        + producer_cid
                        + ":"
                        + field
                    )
                shared = sorted(
                    set(_tokens(producer.get("provides") or [], producer_cid + "_PROVIDES"))
                    & set(requires)
                )
                if not shared:
                    raise TraceCapsuleError(
                        "RESULT_REFERENCE_WITHOUT_DECLARED_EFFECT_EDGE:"
                        + producer_cid
                        + "->"
                        + cid
                    )
                current: Any = trace[source_cycle]["result"]
                for part in field.split("."):
                    if not isinstance(current, Mapping) or part not in current:
                        raise TraceCapsuleError(
                            "RESULT_REFERENCE_FIELD_MISSING:"
                            + producer_cid
                            + ":"
                            + field
                        )
                    current = current[part]
                explicit_edges.append(
                    {
                        "consumer_path": ref["path"],
                        "producer_cycle": source_cycle,
                        "producer_capability_id": producer_cid,
                        "field": field,
                        "value_sha256": _canon_sha256(current),
                        "shared_required_effects": shared,
                    }
                )
            explicit_result_edge_count += len(explicit_edges)

            result_sha = _canon_sha256(result)
            resolved_action_sha = _canon_sha256(resolved_action)
            raw_action_sha = _canon_sha256(raw_action)
            requirement_witnesses = {
                effect: copy.deepcopy(providers[effect]) for effect in requires
            }

            state_required_effects = [
                effect
                for effect in requires
                if requirement_witnesses[effect]["origin"] != "VERIFIED_INITIAL_FACT"
            ]
            initial_required_effects = [
                effect
                for effect in requires
                if requirement_witnesses[effect]["origin"] == "VERIFIED_INITIAL_FACT"
            ]
            state_requires = ["effect:" + effect for effect in state_required_effects]
            state_provides = ["effect:" + effect for effect in provides]
            values = {
                "effect:" + effect: {
                    "effect": effect,
                    "cycle": cycle,
                    "capability_id": cid,
                    "raw_action_sha256": raw_action_sha,
                    "resolved_action_sha256": resolved_action_sha,
                    "result_sha256": result_sha,
                    "expectation": copy.deepcopy(raw_action.get("expect")),
                }
                for effect in provides
            }
            result_evidence_ref = "result_sha256:" + result_sha
            initial_evidence_refs = [
                "verified_initial_fact:" + _canon_sha256({"effect": effect})
                for effect in initial_required_effects
            ]
            evidence_refs = [result_evidence_ref] + initial_evidence_refs
            action_ref = resolved_action_sha
            lineage_refs = (
                ["state:effect:" + effect for effect in state_required_effects]
                + ["evidence:" + ref for ref in initial_evidence_refs]
                + ["evidence:" + result_evidence_ref, "action:" + action_ref]
            )
            lineage = {
                "effect:" + effect: list(lineage_refs) for effect in provides
            }
            capsule = append_macrostep(
                capsule,
                producer=cid,
                action_ref=action_ref,
                requires=state_requires,
                provides=state_provides,
                values=values,
                evidence_refs=evidence_refs,
                lineage=lineage,
            )

            witness = {
                "origin": "WITNESSED_CAPABILITY_TRANSITION",
                "cycle": cycle,
                "capability_id": cid,
                "raw_action_sha256": raw_action_sha,
                "resolved_action_sha256": resolved_action_sha,
                "result_sha256": result_sha,
                "capsule_head_hash": capsule["head_hash"],
            }
            for effect in provides:
                providers[effect] = copy.deepcopy(witness)
                facts.add(effect)

            transition_receipts.append(
                {
                    "cycle": cycle,
                    "capability_id": cid,
                    "requires": requires,
                    "provides": provides,
                    "requirement_witnesses": requirement_witnesses,
                    "explicit_result_edges": explicit_edges,
                    "raw_action_sha256": raw_action_sha,
                    "resolved_action_sha256": resolved_action_sha,
                    "result_sha256": result_sha,
                    "capsule_head_hash": capsule["head_hash"],
                }
            )

        missing_targets = sorted(targets - facts)
        if missing_targets:
            raise TraceCapsuleError(
                "TARGET_EFFECT_WITNESS_MISSING:" + ",".join(missing_targets)
            )

        capsule_verdict = verify_capsule(capsule)
        if capsule_verdict.get("status") != "PASS":
            raise TraceCapsuleError(
                "CAPSULE_VERIFICATION_FAILED:" + str(capsule_verdict.get("reason"))
            )

        return {
            "schema": SCHEMA,
            "status": "PASS",
            "plan_capability_count": len(plan_ids),
            "trace_action_count": len(trace),
            "initial_fact_count": len(
                _tokens(problem.get("initial_facts") or [], "INITIAL_FACTS")
            ),
            "target_effect_count": len(targets),
            "explicit_result_edge_count": explicit_result_edge_count,
            "all_target_effects_have_witnesses": True,
            "all_planned_nonfinish_actions_have_runtime_expectation_witnesses": True,
            "all_declared_runtime_preconditions_have_prior_or_initial_witnesses": True,
            "all_explicit_cross_role_result_edges_are_backward_and_declared": True,
            "transition_receipts": transition_receipts,
            "capsule": capsule,
            "capsule_head_hash": capsule["head_hash"],
            "capsule_record_count": capsule_verdict["record_count"],
            "acceptance_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
            "acceptance_credit_delta": 0,
        }
