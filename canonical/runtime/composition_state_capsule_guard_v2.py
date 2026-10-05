"""Closed-path guard binding capability-plan execution to strict capsule v2.

Scope: deterministic capability plans emitted by capability_planner.plan_actions.

This guard adds the system-level premise intentionally excluded by
composition_state_capsule_v2: cross-capability result references are effect-bound
and are resolved only through projected capsule state. Resume reconstructs the
same capsule and rejects trace/head drift.

It does not prove semantic completeness of capability declarations or
completeness of external evidence provenance. Those remain separate premises.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys
from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA = "PROJECT_BRAIN_COMPOSITION_STATE_CAPSULE_GUARD_V2"


class CompositionGuardError(ValueError):
    pass


def _load_capsule():
    path = pathlib.Path(__file__).resolve().with_name("composition_state_capsule_v2.py")
    spec = importlib.util.spec_from_file_location(
        "project_brain_composition_state_capsule_guard_v2_dependency", path
    )
    if spec is None or spec.loader is None:
        raise CompositionGuardError("CAPSULE_MODULE_LOAD_FAILED")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _strings(value: Any, label: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise CompositionGuardError(label + "_INVALID")
    out = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise CompositionGuardError(label + "_INVALID")
        out.append(item.strip())
    if len(out) != len(set(out)):
        raise CompositionGuardError(label + "_DUPLICATE")
    return out


def _result_refs(value: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if isinstance(value, Mapping):
        if set(value) == {"$result"}:
            spec = value["$result"]
            if not isinstance(spec, Mapping) or set(spec) != {"cycle", "field", "effect"}:
                raise CompositionGuardError("RESULT_REFERENCE_NOT_EFFECT_BOUND")
            cycle = spec.get("cycle")
            field = spec.get("field")
            effect = spec.get("effect")
            if not isinstance(cycle, int) or isinstance(cycle, bool) or cycle < 0:
                raise CompositionGuardError("RESULT_REFERENCE_CYCLE_INVALID")
            if not isinstance(field, str) or not field.strip():
                raise CompositionGuardError("RESULT_REFERENCE_FIELD_REQUIRED")
            if not isinstance(effect, str) or not effect.strip():
                raise CompositionGuardError("RESULT_REFERENCE_EFFECT_REQUIRED")
            out.append(
                {"cycle": cycle, "field": field.strip(), "effect": effect.strip()}
            )
            return out
        for item in value.values():
            out.extend(_result_refs(item))
    elif isinstance(value, list):
        for item in value:
            out.extend(_result_refs(item))
    return out


def validate_plan(
    actions: Sequence[Mapping[str, Any]],
    contract: Sequence[Mapping[str, Any]],
    initial_facts: Sequence[str],
) -> dict[str, Any]:
    if not isinstance(actions, Sequence) or isinstance(actions, (str, bytes, bytearray)):
        raise CompositionGuardError("ACTIONS_INVALID")
    if not isinstance(contract, Sequence) or isinstance(contract, (str, bytes, bytearray)):
        raise CompositionGuardError("CONTRACT_INVALID")
    initial = _strings(initial_facts, "INITIAL_FACTS")
    if len(actions) != len(contract) + 1:
        raise CompositionGuardError("CONTRACT_ACTION_COUNT_MISMATCH")
    if (
        not actions
        or not isinstance(actions[-1], Mapping)
        or actions[-1].get("type") != "finish"
    ):
        raise CompositionGuardError("FINAL_FINISH_ACTION_REQUIRED")

    known: dict[str, dict[str, Any] | None] = {fact: None for fact in initial}
    normalized = []
    for index, row in enumerate(contract):
        if not isinstance(row, Mapping):
            raise CompositionGuardError(f"CONTRACT_{index}_INVALID")
        if row.get("cycle") != index:
            raise CompositionGuardError(f"CONTRACT_{index}_CYCLE_MISMATCH")
        cid = row.get("capability_id")
        if not isinstance(cid, str) or not cid.strip():
            raise CompositionGuardError(f"CONTRACT_{index}_CAPABILITY_ID_INVALID")
        cid = cid.strip()
        action = actions[index]
        if not isinstance(action, Mapping) or action.get("capability_id") != cid:
            raise CompositionGuardError(f"CONTRACT_{index}_ACTION_CAPABILITY_MISMATCH")
        requires = _strings(row.get("requires"), f"CONTRACT_{index}_REQUIRES")
        provides = _strings(row.get("provides"), f"CONTRACT_{index}_PROVIDES")
        fields = _strings(row.get("result_fields"), f"CONTRACT_{index}_RESULT_FIELDS")
        missing = [effect for effect in requires if effect not in known]
        if missing:
            raise CompositionGuardError(
                f"CONTRACT_{index}_REQUIRED_EFFECT_UNAVAILABLE:"
                + ",".join(sorted(missing))
            )

        expected_bindings = {}
        for effect in requires:
            provider = known[effect]
            if provider is not None:
                expected_bindings[effect] = {
                    "cycle": provider["cycle"],
                    "capability_id": provider["capability_id"],
                }
        got_bindings = row.get("provider_bindings")
        if not isinstance(got_bindings, Mapping) or dict(got_bindings) != expected_bindings:
            raise CompositionGuardError(
                f"CONTRACT_{index}_PROVIDER_BINDING_MISMATCH"
            )

        for ref in _result_refs(action):
            effect = ref["effect"]
            binding = expected_bindings.get(effect)
            if binding is None:
                raise CompositionGuardError(
                    f"CONTRACT_{index}_RESULT_REFERENCE_BYPASSES_REQUIRED_EFFECT:"
                    + effect
                )
            if binding["cycle"] != ref["cycle"]:
                raise CompositionGuardError(
                    f"CONTRACT_{index}_RESULT_REFERENCE_PROVIDER_MISMATCH:"
                    + effect
                    + ":"
                    + str(ref["cycle"])
                )
            producer = normalized[ref["cycle"]]
            if ref["field"] not in producer["result_fields"]:
                raise CompositionGuardError(
                    f"CONTRACT_{index}_RESULT_REFERENCE_FIELD_UNDECLARED:"
                    + str(ref["cycle"])
                    + ":"
                    + ref["field"]
                )

        normalized_row = {
            "cycle": index,
            "capability_id": cid,
            "requires": requires,
            "provides": provides,
            "result_fields": fields,
            "provider_bindings": expected_bindings,
        }
        normalized.append(normalized_row)
        for effect in provides:
            known[effect] = {"cycle": index, "capability_id": cid}

    return {
        "schema": SCHEMA,
        "status": "PASS",
        "initial_facts": initial,
        "contract": normalized,
        "declared_cross_capability_state_no_bypass": True,
        "effect_identity_bound_on_every_result_reference": True,
        "capsule_version": 2,
        "semantic_declaration_completeness": "UNVERIFIED",
        "external_evidence_channel_completeness": "UNVERIFIED",
        "acceptance_credit_delta": 0,
    }


def seed_capsule(initial_facts: Sequence[str]):
    capsule_mod = _load_capsule()
    initial = _strings(initial_facts, "INITIAL_FACTS")
    cap = capsule_mod.empty_capsule()
    if not initial:
        return cap
    producer_ref = "capability_planner"
    action_ref = "verified_initial_facts"
    return capsule_mod.append_macrostep(
        cap,
        producer_ref=producer_ref,
        producer_descriptor={
            "component": "capability_planner",
            "role": "verified_initial_fact_seed",
        },
        action_ref=action_ref,
        action_descriptor={
            "type": "seed_verified_initial_facts",
            "initial_facts": sorted(initial),
        },
        requires=[],
        provides=initial,
        values={
            fact: {"effect": fact, "source": "verified_initial_fact"}
            for fact in initial
        },
        evidence_values={},
        lineage={
            fact: ["action:" + action_ref, "producer:" + producer_ref]
            for fact in initial
        },
    )


def assert_action_ready(capsule: Mapping[str, Any], row: Mapping[str, Any]) -> dict[str, Any]:
    capsule_mod = _load_capsule()
    requires = _strings(row.get("requires"), "ROW_REQUIRES")
    context = capsule_mod.project_context(capsule, requires)
    return {
        "status": "PASS",
        "cycle": row.get("cycle"),
        "capability_id": row.get("capability_id"),
        "required_effects": requires,
        "capsule_head_hash": context["capsule_head_hash"],
    }


def _result_field(result: Any, field: str) -> Any:
    current = result
    for part in field.split("."):
        if not isinstance(current, Mapping) or part not in current:
            raise CompositionGuardError("RESULT_FIELD_MISSING:" + field)
        current = current[part]
    return current


def _resolve_value(
    value: Any,
    capsule: Mapping[str, Any],
    row: Mapping[str, Any],
    capsule_mod,
) -> Any:
    if isinstance(value, Mapping):
        if set(value) == {"$result"}:
            refs = _result_refs(value)
            ref = refs[0]
            effect = ref["effect"]
            bindings = row.get("provider_bindings")
            if not isinstance(bindings, Mapping):
                raise CompositionGuardError("ROW_PROVIDER_BINDINGS_INVALID")
            binding = bindings.get(effect)
            if (
                not isinstance(binding, Mapping)
                or binding.get("cycle") != ref["cycle"]
            ):
                raise CompositionGuardError(
                    "RESULT_REFERENCE_PROVIDER_MISMATCH:" + effect
                )
            context = capsule_mod.project_context(capsule, [effect])
            state = context["values"][effect]
            if (
                not isinstance(state, Mapping)
                or state.get("producer_cycle") != ref["cycle"]
                or state.get("capability_id") != binding.get("capability_id")
                or "result" not in state
            ):
                raise CompositionGuardError(
                    "RESULT_REFERENCE_CAPSULE_BINDING_MISMATCH:" + effect
                )
            return _result_field(state["result"], ref["field"])
        return {
            key: _resolve_value(item, capsule, row, capsule_mod)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_resolve_value(item, capsule, row, capsule_mod) for item in value]
    return value


def resolve_action(
    capsule: Mapping[str, Any],
    row: Mapping[str, Any],
    raw_action: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(raw_action, Mapping):
        raise CompositionGuardError("ACTION_INVALID")
    capsule_mod = _load_capsule()
    assert_action_ready(capsule, row)
    resolved = _resolve_value(dict(raw_action), capsule, row, capsule_mod)
    if not isinstance(resolved, dict):
        raise CompositionGuardError("RESOLVED_ACTION_INVALID")
    return resolved


def append_action_result(
    capsule: Mapping[str, Any],
    row: Mapping[str, Any],
    resolved_action: Mapping[str, Any],
    result: Any,
):
    capsule_mod = _load_capsule()
    cycle = row.get("cycle")
    cid = str(row.get("capability_id") or "").strip()
    requires = _strings(row.get("requires"), "ROW_REQUIRES")
    provides = _strings(row.get("provides"), "ROW_PROVIDES")
    fields = _strings(row.get("result_fields"), "ROW_RESULT_FIELDS")
    if not isinstance(cycle, int) or cycle < 0 or not cid:
        raise CompositionGuardError("ROW_IDENTITY_INVALID")
    if not isinstance(resolved_action, Mapping):
        raise CompositionGuardError("RESOLVED_ACTION_INVALID")
    for field in fields:
        _result_field(result, field)

    producer_ref = cid
    action_ref = f"capability:{cid}:cycle:{cycle}"
    producer_descriptor = {
        "capability_id": cid,
        "cycle": cycle,
        "requires": requires,
        "provides": provides,
        "result_fields": fields,
        "provider_bindings": dict(row.get("provider_bindings") or {}),
    }
    action_descriptor = dict(resolved_action)
    lineage_refs = (
        ["state:" + effect for effect in requires]
        + ["action:" + action_ref, "producer:" + producer_ref]
    )
    values = {
        effect: {
            "effect": effect,
            "producer_cycle": cycle,
            "capability_id": cid,
            "result": result,
        }
        for effect in provides
    }
    return capsule_mod.append_macrostep(
        capsule,
        producer_ref=producer_ref,
        producer_descriptor=producer_descriptor,
        action_ref=action_ref,
        action_descriptor=action_descriptor,
        requires=requires,
        provides=provides,
        values=values,
        evidence_values={},
        lineage={effect: list(lineage_refs) for effect in provides},
    )


def rebuild_from_trace(
    actions: Sequence[Mapping[str, Any]],
    contract: Sequence[Mapping[str, Any]],
    initial_facts: Sequence[str],
    trace: Sequence[Mapping[str, Any]],
):
    validated = validate_plan(actions, contract, initial_facts)
    cap = seed_capsule(validated["initial_facts"])
    max_capability_records = min(len(trace), len(validated["contract"]))
    for cycle in range(max_capability_records):
        record = trace[cycle]
        if not isinstance(record, Mapping) or record.get("cycle") != cycle:
            raise CompositionGuardError(f"TRACE_{cycle}_INVALID")
        row = validated["contract"][cycle]
        expected_plan = resolve_action(cap, row, actions[cycle])
        observed_plan = record.get("plan")
        if observed_plan != expected_plan:
            raise CompositionGuardError(f"TRACE_{cycle}_PLAN_RESOLUTION_MISMATCH")
        cap = append_action_result(cap, row, expected_plan, record.get("result"))
        expected_head = record.get("composition_capsule_head_hash")
        if expected_head is not None and expected_head != cap.get("head_hash"):
            raise CompositionGuardError(f"TRACE_{cycle}_CAPSULE_HEAD_MISMATCH")
    verdict = _load_capsule().verify_capsule(cap)
    if verdict.get("status") != "PASS":
        raise CompositionGuardError(
            "REBUILT_CAPSULE_INVALID:" + str(verdict.get("reason"))
        )
    return cap


def verify_capsule(capsule: Mapping[str, Any]) -> dict[str, Any]:
    return _load_capsule().verify_capsule(capsule)
