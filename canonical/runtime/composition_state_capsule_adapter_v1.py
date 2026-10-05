"""Capsule-authoritative adapter for deterministic capability composition.

This adapter closes the concrete runtime handoff where a later capability can
consume an earlier capability's result.  In capsule mode, raw controller trace
records are never the authority for cross-capability values: the trace is only
an index/provenance witness and the content-addressed capsule is authoritative.

Scope is intentionally narrow.  This proves mechanics for capability-planner
actions carrying the V1 state contract.  It does not claim that every Brain
composition route has been migrated or that external filesystem/environment
channels are globally closed.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import pathlib
import sys
from collections.abc import Mapping, Sequence
from typing import Any

CONTRACT_KEY = "_brain_composition_contract"
CONTRACT_SCHEMA = "PROJECT_BRAIN_CAPABILITY_ACTION_STATE_CONTRACT_V1"


class CompositionAdapterError(RuntimeError):
    pass


def _load_capsule_module():
    path = pathlib.Path(__file__).with_name("composition_state_capsule_v1.py")
    name = "project_brain_composition_state_capsule_adapter_kernel_v1"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise CompositionAdapterError("CAPSULE_KERNEL_LOAD_FAILED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_CAPSULE = _load_capsule_module()


def _sha256(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise CompositionAdapterError(label + "_INVALID")
    out = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise CompositionAdapterError(label + "_ITEM_INVALID")
        out.append(item.strip())
    if len(out) != len(set(out)):
        raise CompositionAdapterError(label + "_DUPLICATE")
    return out


def _contract(action: Mapping[str, Any], *, required: bool = True) -> dict[str, Any] | None:
    raw = action.get(CONTRACT_KEY)
    if raw is None:
        if required:
            raise CompositionAdapterError("COMPOSITION_CONTRACT_MISSING")
        return None
    if not isinstance(raw, Mapping):
        raise CompositionAdapterError("COMPOSITION_CONTRACT_INVALID")
    if raw.get("schema") != CONTRACT_SCHEMA:
        raise CompositionAdapterError("COMPOSITION_CONTRACT_SCHEMA_INVALID")
    capability_id = str(raw.get("capability_id") or "").strip()
    if not capability_id or capability_id != str(action.get("capability_id") or "").strip():
        raise CompositionAdapterError("COMPOSITION_CONTRACT_CAPABILITY_ID_MISMATCH")
    requires = _string_list(raw.get("requires"), "COMPOSITION_REQUIRES")
    internal = _string_list(raw.get("internal_requires"), "COMPOSITION_INTERNAL_REQUIRES")
    external = _string_list(raw.get("external_requires"), "COMPOSITION_EXTERNAL_REQUIRES")
    provides = _string_list(raw.get("provides"), "COMPOSITION_PROVIDES")
    result_fields = _string_list(raw.get("result_fields"), "COMPOSITION_RESULT_FIELDS")
    if set(internal) & set(external):
        raise CompositionAdapterError("COMPOSITION_REQUIREMENT_PARTITION_OVERLAP")
    if set(internal) | set(external) != set(requires):
        raise CompositionAdapterError("COMPOSITION_REQUIREMENT_PARTITION_INCOMPLETE")
    if not provides:
        raise CompositionAdapterError("COMPOSITION_PROVIDES_EMPTY")
    return {
        "schema": CONTRACT_SCHEMA,
        "capability_id": capability_id,
        "requires": requires,
        "internal_requires": internal,
        "external_requires": external,
        "provides": provides,
        "result_fields": result_fields,
    }


def _result_refs(value: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if isinstance(value, Mapping):
        if set(value) == {"$result"}:
            spec = value["$result"]
            if not isinstance(spec, Mapping):
                raise CompositionAdapterError("RESULT_REFERENCE_INVALID")
            out.append(dict(spec))
        else:
            for item in value.values():
                out.extend(_result_refs(item))
    elif isinstance(value, list):
        for item in value:
            out.extend(_result_refs(item))
    return out


def plan_uses_capsule(actions: Sequence[Mapping[str, Any]]) -> bool:
    return any(
        isinstance(action, Mapping) and action.get(CONTRACT_KEY) is not None
        for action in actions
    )


def validate_plan(actions: Sequence[Mapping[str, Any]]) -> bool:
    if not isinstance(actions, Sequence) or isinstance(actions, (str, bytes, bytearray)):
        raise CompositionAdapterError("COMPOSITION_ACTIONS_INVALID")
    enabled = plan_uses_capsule(actions)
    if not enabled:
        return False

    for cycle, action in enumerate(actions):
        if not isinstance(action, Mapping):
            raise CompositionAdapterError("COMPOSITION_ACTION_NOT_OBJECT")
        if action.get("type") == "finish":
            if action.get(CONTRACT_KEY) is not None:
                raise CompositionAdapterError("FINISH_MUST_NOT_CARRY_COMPOSITION_CONTRACT")
            continue

        contract = _contract(action)
        for spec in _result_refs(action.get("args") or {}):
            if set(spec) != {"cycle", "effect", "field"}:
                raise CompositionAdapterError("RESULT_REFERENCE_SCHEMA_INVALID")
            try:
                provider_cycle = int(spec["cycle"])
            except Exception as exc:
                raise CompositionAdapterError("RESULT_REFERENCE_CYCLE_INVALID") from exc
            effect = str(spec.get("effect") or "").strip()
            field = str(spec.get("field") or "").strip()
            if provider_cycle < 0 or provider_cycle >= cycle:
                raise CompositionAdapterError("RESULT_REFERENCE_CYCLE_INVALID")
            if not effect or not field:
                raise CompositionAdapterError("RESULT_REFERENCE_INCOMPLETE")
            if effect not in contract["internal_requires"]:
                raise CompositionAdapterError(
                    "RESULT_REFERENCE_EFFECT_NOT_INTERNAL_REQUIREMENT:" + effect
                )
            provider_action = actions[provider_cycle]
            provider = _contract(provider_action)
            if effect not in provider["provides"]:
                raise CompositionAdapterError(
                    "RESULT_REFERENCE_PROVIDER_EFFECT_MISMATCH:" + effect
                )
            if field not in provider["result_fields"]:
                raise CompositionAdapterError(
                    "RESULT_REFERENCE_PROVIDER_FIELD_UNDECLARED:" + field
                )
    return True


def empty_capsule() -> dict[str, Any]:
    return _CAPSULE.empty_capsule()


def _verified_capsule(capsule: Mapping[str, Any]) -> dict[str, Any]:
    verdict = _CAPSULE.verify_capsule(capsule)
    if verdict.get("status") != "PASS":
        raise CompositionAdapterError(
            "COMPOSITION_CAPSULE_INVALID:" + str(verdict.get("reason") or "UNKNOWN")
        )
    return verdict


def bind_checkpoint(
    actions: Sequence[Mapping[str, Any]],
    checkpoint: Mapping[str, Any],
    trace: Sequence[Mapping[str, Any]],
) -> dict[str, Any] | None:
    if not validate_plan(actions):
        return None

    raw = checkpoint.get("composition_state_capsule")
    if raw is None:
        if trace:
            raise CompositionAdapterError("COMPOSITION_CAPSULE_CHECKPOINT_MISSING")
        capsule = empty_capsule()
    elif not isinstance(raw, Mapping):
        raise CompositionAdapterError("COMPOSITION_CAPSULE_CHECKPOINT_INVALID")
    else:
        capsule = copy.deepcopy(dict(raw))

    verdict = _verified_capsule(capsule)
    contracted = [
        record for record in trace
        if isinstance(record, Mapping)
        and isinstance(record.get("plan"), Mapping)
        and record["plan"].get(CONTRACT_KEY) is not None
    ]

    if int(verdict.get("record_count", -1)) < len(contracted):
        raise CompositionAdapterError("COMPOSITION_CAPSULE_TRACE_RECORD_MISSING")

    if int(verdict.get("record_count", -1)) > len(contracted):
        target = (
            contracted[-1].get("composition_capsule_head_hash")
            if contracted
            else _CAPSULE.GENESIS_HASH
        )
        capsule = _CAPSULE.rollback_to(capsule, str(target))
        verdict = _verified_capsule(capsule)

    records = list(capsule.get("records") or [])
    if len(records) != len(contracted):
        raise CompositionAdapterError("COMPOSITION_CAPSULE_TRACE_COUNT_MISMATCH")

    for index, (trace_record, capsule_record) in enumerate(zip(contracted, records)):
        action = trace_record.get("plan")
        result = trace_record.get("result")
        if not isinstance(action, Mapping) or not isinstance(result, Mapping):
            raise CompositionAdapterError("COMPOSITION_TRACE_RECORD_INVALID")
        contract = _contract(action)
        if trace_record.get("composition_capsule_head_hash") != capsule_record.get("record_hash"):
            raise CompositionAdapterError(
                "COMPOSITION_TRACE_HEAD_MISMATCH:" + str(index)
            )
        if capsule_record.get("action_ref") != contract["capability_id"]:
            raise CompositionAdapterError(
                "COMPOSITION_TRACE_ACTION_MISMATCH:" + str(index)
            )
        result_hash = _sha256(result)
        for effect in contract["provides"]:
            value_hash = (capsule_record.get("value_hashes") or {}).get(effect)
            if value_hash != result_hash:
                raise CompositionAdapterError(
                    "COMPOSITION_TRACE_RESULT_HASH_MISMATCH:" + effect
                )
    return capsule


def ensure_required_state(
    action: Mapping[str, Any],
    capsule: Mapping[str, Any],
) -> None:
    contract = _contract(action)
    if contract["internal_requires"]:
        _CAPSULE.project_context(capsule, contract["internal_requires"])


def _resolve_value(
    value: Any,
    *,
    current_contract: Mapping[str, Any],
    trace: Sequence[Mapping[str, Any]],
    capsule: Mapping[str, Any],
) -> Any:
    if isinstance(value, Mapping):
        if set(value) == {"$result"}:
            spec = value["$result"]
            if not isinstance(spec, Mapping) or set(spec) != {"cycle", "effect", "field"}:
                raise CompositionAdapterError("RESULT_REFERENCE_SCHEMA_INVALID")
            cycle = int(spec["cycle"])
            effect = str(spec["effect"]).strip()
            field = str(spec["field"]).strip()
            if cycle < 0 or cycle >= len(trace):
                raise CompositionAdapterError("RESULT_REFERENCE_CYCLE_INVALID")
            if effect not in current_contract["internal_requires"]:
                raise CompositionAdapterError(
                    "RESULT_REFERENCE_EFFECT_NOT_INTERNAL_REQUIREMENT:" + effect
                )

            provider_record = trace[cycle]
            provider_action = provider_record.get("plan")
            if not isinstance(provider_action, Mapping):
                raise CompositionAdapterError("RESULT_REFERENCE_PROVIDER_PLAN_INVALID")
            provider_contract = _contract(provider_action)
            if effect not in provider_contract["provides"]:
                raise CompositionAdapterError(
                    "RESULT_REFERENCE_PROVIDER_EFFECT_MISMATCH:" + effect
                )
            if field not in provider_contract["result_fields"]:
                raise CompositionAdapterError(
                    "RESULT_REFERENCE_PROVIDER_FIELD_UNDECLARED:" + field
                )

            projected = _CAPSULE.project_context(capsule, [effect])
            latest = _verified_capsule(capsule)["latest"][effect]
            if latest["record_hash"] != provider_record.get("composition_capsule_head_hash"):
                raise CompositionAdapterError(
                    "RESULT_REFERENCE_PROVIDER_CAPSULE_HEAD_MISMATCH:" + effect
                )
            provider_result = provider_record.get("result")
            if not isinstance(provider_result, Mapping):
                raise CompositionAdapterError("RESULT_REFERENCE_PROVIDER_RESULT_INVALID")
            if latest["value_hash"] != _sha256(provider_result):
                raise CompositionAdapterError(
                    "RESULT_REFERENCE_PROVIDER_RESULT_HASH_MISMATCH:" + effect
                )

            current: Any = projected["values"][effect]
            for part in field.split("."):
                if not isinstance(current, Mapping) or part not in current:
                    raise CompositionAdapterError(
                        "RESULT_REFERENCE_FIELD_MISSING:" + field
                    )
                current = current[part]
            return copy.deepcopy(current)
        return {
            key: _resolve_value(
                item,
                current_contract=current_contract,
                trace=trace,
                capsule=capsule,
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _resolve_value(
                item,
                current_contract=current_contract,
                trace=trace,
                capsule=capsule,
            )
            for item in value
        ]
    return copy.deepcopy(value)


def resolve_action(
    raw_action: Mapping[str, Any],
    trace: Sequence[Mapping[str, Any]],
    capsule: Mapping[str, Any],
) -> dict[str, Any]:
    contract = _contract(raw_action)
    ensure_required_state(raw_action, capsule)
    out = copy.deepcopy(dict(raw_action))
    out["args"] = _resolve_value(
        out.get("args") or {},
        current_contract=contract,
        trace=trace,
        capsule=capsule,
    )
    return out


def commit_result(
    capsule: Mapping[str, Any],
    action: Mapping[str, Any],
    result: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(result, Mapping):
        raise CompositionAdapterError("COMPOSITION_RESULT_NOT_OBJECT")
    contract = _contract(action)
    result_value = copy.deepcopy(dict(result))
    result_sha = _sha256(result_value)
    evidence_ref = "result_sha256:" + result_sha
    lineage = {}
    for effect in contract["provides"]:
        lineage[effect] = [
            "action:" + contract["capability_id"],
            *["state:" + key for key in contract["internal_requires"]],
            "evidence:" + evidence_ref,
        ]
    return _CAPSULE.append_macrostep(
        capsule,
        producer=contract["capability_id"],
        action_ref=contract["capability_id"],
        requires=contract["internal_requires"],
        provides=contract["provides"],
        values={effect: result_value for effect in contract["provides"]},
        evidence_refs=[evidence_ref],
        lineage=lineage,
    )
