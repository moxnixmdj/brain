"""No-bypass guard binding capability-graph execution to the composition state capsule.

Scope: deterministic capability plans emitted by capability_planner.plan_actions.
This module proves/mechanically enforces declared cross-capability state continuity.
It does not prove semantic completeness of capability declarations or external-evidence
completeness; those remain separate premises.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys
from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA = "PROJECT_BRAIN_COMPOSITION_STATE_CAPSULE_GUARD_V1"


class CompositionGuardError(ValueError):
    pass


def _load_capsule():
    path = pathlib.Path(__file__).resolve().with_name("composition_state_capsule_v1.py")
    spec = importlib.util.spec_from_file_location(
        "project_brain_composition_state_capsule_guard_dependency", path
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
            if not isinstance(spec, Mapping):
                raise CompositionGuardError("RESULT_REFERENCE_INVALID")
            cycle = spec.get("cycle")
            field = spec.get("field")
            if not isinstance(cycle, int) or isinstance(cycle, bool) or cycle < 0:
                raise CompositionGuardError("RESULT_REFERENCE_CYCLE_INVALID")
            if not isinstance(field, str) or not field.strip():
                raise CompositionGuardError("RESULT_REFERENCE_FIELD_REQUIRED")
            out.append({"cycle": cycle, "field": field.strip()})
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
    if not actions or not isinstance(actions[-1], Mapping) or actions[-1].get("type") != "finish":
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
                f"CONTRACT_{index}_REQUIRED_EFFECT_UNAVAILABLE:" + ",".join(sorted(missing))
            )

        expected_bindings = {}
        expected_requirement_bindings = {}
        for effect in requires:
            provider = known[effect]
            if provider is None:
                expected_requirement_bindings[effect] = {"source": "initial_fact"}
            else:
                expected_bindings[effect] = {
                    "cycle": provider["cycle"],
                    "capability_id": provider["capability_id"],
                }
                expected_requirement_bindings[effect] = {
                    "source": "capability",
                    "cycle": provider["cycle"],
                    "capability_id": provider["capability_id"],
                }
        got_bindings = row.get("provider_bindings")
        if not isinstance(got_bindings, Mapping) or dict(got_bindings) != expected_bindings:
            raise CompositionGuardError(f"CONTRACT_{index}_PROVIDER_BINDING_MISMATCH")
        got_requirement_bindings = row.get("requirement_bindings")
        if (
            not isinstance(got_requirement_bindings, Mapping)
            or dict(got_requirement_bindings) != expected_requirement_bindings
        ):
            raise CompositionGuardError(
                f"CONTRACT_{index}_REQUIREMENT_BINDING_MISMATCH"
            )

        allowed_provider_cycles = {
            value["cycle"]: value["capability_id"] for value in expected_bindings.values()
        }
        for ref in _result_refs(action):
            provider_cycle = ref["cycle"]
            if provider_cycle not in allowed_provider_cycles:
                raise CompositionGuardError(
                    f"CONTRACT_{index}_RESULT_REFERENCE_BYPASSES_REQUIRED_EFFECT:"
                    + str(provider_cycle)
                )
            producer = normalized[provider_cycle]
            if ref["field"] not in producer["result_fields"]:
                raise CompositionGuardError(
                    f"CONTRACT_{index}_RESULT_REFERENCE_FIELD_UNDECLARED:"
                    + str(provider_cycle) + ":" + ref["field"]
                )

        normalized_row = {
            "cycle": index,
            "capability_id": cid,
            "requires": requires,
            "provides": provides,
            "result_fields": fields,
            "provider_bindings": expected_bindings,
            "requirement_bindings": expected_requirement_bindings,
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
    action_ref = "verified_initial_facts"
    cap = capsule_mod.append_macrostep(
        cap,
        producer="capability_planner",
        action_ref=action_ref,
        requires=[],
        provides=initial,
        values={
            fact: {"effect": fact, "source": "verified_initial_fact"}
            for fact in initial
        },
        evidence_refs=[],
        lineage={fact: ["action:" + action_ref] for fact in initial},
    )
    return cap


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


def append_action_result(
    capsule: Mapping[str, Any],
    row: Mapping[str, Any],
    result: Any,
):
    capsule_mod = _load_capsule()
    cycle = row.get("cycle")
    cid = str(row.get("capability_id") or "").strip()
    requires = _strings(row.get("requires"), "ROW_REQUIRES")
    provides = _strings(row.get("provides"), "ROW_PROVIDES")
    if not isinstance(cycle, int) or cycle < 0 or not cid:
        raise CompositionGuardError("ROW_IDENTITY_INVALID")
    action_ref = f"capability:{cid}:cycle:{cycle}"
    lineage_refs = ["state:" + effect for effect in requires] + ["action:" + action_ref]
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
        producer=cid,
        action_ref=action_ref,
        requires=requires,
        provides=provides,
        values=values,
        evidence_refs=[],
        lineage={effect: list(lineage_refs) for effect in provides},
    )


def _resolve_field(value: Any, field: str) -> Any:
    current = value
    for part in str(field or "").split("."):
        if not part or not isinstance(current, Mapping) or part not in current:
            raise CompositionGuardError("RESULT_REFERENCE_FIELD_MISSING:" + str(field))
        current = current[part]
    return current


def _resolve_capsule_reference(
    capsule: Mapping[str, Any],
    row: Mapping[str, Any],
    spec: Mapping[str, Any],
) -> Any:
    cycle = spec.get("cycle")
    field = spec.get("field")
    if not isinstance(cycle, int) or isinstance(cycle, bool) or cycle < 0:
        raise CompositionGuardError("RESULT_REFERENCE_CYCLE_INVALID")
    if not isinstance(field, str) or not field.strip():
        raise CompositionGuardError("RESULT_REFERENCE_FIELD_REQUIRED")

    bindings = row.get("provider_bindings")
    if not isinstance(bindings, Mapping):
        raise CompositionGuardError("ROW_PROVIDER_BINDINGS_INVALID")
    candidates = [
        (effect, binding)
        for effect, binding in bindings.items()
        if isinstance(binding, Mapping) and binding.get("cycle") == cycle
    ]
    if not candidates:
        raise CompositionGuardError(
            "RESULT_REFERENCE_BYPASSES_REQUIRED_EFFECT:" + str(cycle)
        )

    capsule_mod = _load_capsule()
    context = capsule_mod.project_context(
        capsule, [str(effect) for effect, _ in candidates]
    )
    resolved = []
    for effect, binding in candidates:
        value = context["values"].get(effect)
        if not isinstance(value, Mapping):
            raise CompositionGuardError(
                "CAPSULE_EFFECT_VALUE_INVALID:" + str(effect)
            )
        if value.get("effect") != effect:
            raise CompositionGuardError(
                "CAPSULE_EFFECT_IDENTITY_MISMATCH:" + str(effect)
            )
        if value.get("producer_cycle") != cycle:
            raise CompositionGuardError(
                "CAPSULE_PROVIDER_CYCLE_MISMATCH:" + str(effect)
            )
        if value.get("capability_id") != binding.get("capability_id"):
            raise CompositionGuardError(
                "CAPSULE_PROVIDER_IDENTITY_MISMATCH:" + str(effect)
            )
        resolved.append(_resolve_field(value.get("result"), field.strip()))

    first = resolved[0]
    if any(item != first for item in resolved[1:]):
        raise CompositionGuardError(
            "RESULT_REFERENCE_AMBIGUOUS_REQUIRED_EFFECT:" + str(cycle)
        )
    return first


def _resolve_capsule_value(
    capsule: Mapping[str, Any],
    row: Mapping[str, Any],
    value: Any,
) -> Any:
    if isinstance(value, Mapping):
        if set(value) == {"$result"}:
            spec = value["$result"]
            if not isinstance(spec, Mapping):
                raise CompositionGuardError("RESULT_REFERENCE_INVALID")
            return _resolve_capsule_reference(capsule, row, spec)
        return {
            key: _resolve_capsule_value(capsule, row, item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_resolve_capsule_value(capsule, row, item) for item in value]
    return value


def resolve_action_from_capsule(
    capsule: Mapping[str, Any],
    row: Mapping[str, Any],
    action: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(action, Mapping):
        raise CompositionGuardError("ACTION_INVALID")
    cid = str(row.get("capability_id") or "").strip()
    if not cid or action.get("capability_id") != cid:
        raise CompositionGuardError("ACTION_CAPABILITY_ID_MISMATCH")
    assert_action_ready(capsule, row)
    out = dict(action)
    out["args"] = _resolve_capsule_value(capsule, row, action.get("args") or {})
    return out


def bind_checkpoint(
    actions: Sequence[Mapping[str, Any]],
    contract: Sequence[Mapping[str, Any]],
    initial_facts: Sequence[str],
    checkpoint: Mapping[str, Any],
    trace: Sequence[Mapping[str, Any]],
):
    validated = validate_plan(actions, contract, initial_facts)
    seed = seed_capsule(validated["initial_facts"])
    seed_records = len(seed.get("records") or [])

    raw = checkpoint.get("composition_state_capsule")
    if raw is None:
        if trace:
            raise CompositionGuardError(
                "CHECKPOINT_CAPSULE_MISSING_FOR_EXISTING_TRACE"
            )
        cap = seed
    elif not isinstance(raw, Mapping):
        raise CompositionGuardError("CHECKPOINT_CAPSULE_INVALID")
    else:
        cap = dict(raw)

    capsule_mod = _load_capsule()
    verdict = capsule_mod.verify_capsule(cap)
    if verdict.get("status") != "PASS":
        raise CompositionGuardError(
            "CHECKPOINT_CAPSULE_VERIFY_FAILED:" + str(verdict.get("reason"))
        )

    completed_capabilities = min(len(trace), len(validated["contract"]))
    expected_records = seed_records + completed_capabilities
    observed_records = int(verdict.get("record_count", -1))

    if observed_records > expected_records:
        if completed_capabilities:
            target = trace[completed_capabilities - 1].get(
                "composition_capsule_head_hash"
            )
            if not isinstance(target, str) or not target:
                raise CompositionGuardError(
                    "TRACE_CAPSULE_HEAD_MISSING_FOR_ROLLBACK"
                )
        else:
            target = seed["head_hash"]
        cap = capsule_mod.rollback_to(cap, target)
        verdict = capsule_mod.verify_capsule(cap)
        observed_records = int(verdict.get("record_count", -1))

    if observed_records != expected_records:
        raise CompositionGuardError(
            "CHECKPOINT_CAPSULE_TRACE_COUNT_MISMATCH:"
            + str(observed_records) + ":" + str(expected_records)
        )

    records = list(cap.get("records") or [])
    for cycle in range(completed_capabilities):
        trace_record = trace[cycle]
        if not isinstance(trace_record, Mapping) or trace_record.get("cycle") != cycle:
            raise CompositionGuardError("TRACE_" + str(cycle) + "_INVALID")
        row = validated["contract"][cycle]
        capsule_record = records[seed_records + cycle]
        if (
            trace_record.get("composition_capsule_head_hash")
            != capsule_record.get("record_hash")
        ):
            raise CompositionGuardError(
                "TRACE_CAPSULE_HEAD_MISMATCH:" + str(cycle)
            )
        if (
            capsule_record.get("action_ref")
            != "capability:" + row["capability_id"] + ":cycle:" + str(cycle)
        ):
            raise CompositionGuardError(
                "TRACE_CAPSULE_ACTION_MISMATCH:" + str(cycle)
            )
        result = trace_record.get("result")
        values = capsule_record.get("values")
        if not isinstance(values, Mapping):
            raise CompositionGuardError(
                "TRACE_CAPSULE_VALUES_INVALID:" + str(cycle)
            )
        for effect in row["provides"]:
            value = values.get(effect)
            if (
                not isinstance(value, Mapping)
                or value.get("effect") != effect
                or value.get("producer_cycle") != cycle
                or value.get("capability_id") != row["capability_id"]
                or value.get("result") != result
            ):
                raise CompositionGuardError(
                    "TRACE_CAPSULE_RESULT_MISMATCH:"
                    + str(cycle) + ":" + effect
                )
    return cap


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
        assert_action_ready(cap, row)
        cap = append_action_result(cap, row, record.get("result"))
    capsule_mod = _load_capsule()
    verdict = capsule_mod.verify_capsule(cap)
    if verdict.get("status") != "PASS":
        raise CompositionGuardError("REBUILT_CAPSULE_INVALID:" + str(verdict.get("reason")))
    return cap


def verify_capsule(capsule: Mapping[str, Any]) -> dict[str, Any]:
    return _load_capsule().verify_capsule(capsule)
