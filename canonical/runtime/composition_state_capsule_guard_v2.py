"""Fail-closed V2 bridge from capability-graph execution to content-bound composition state.

For deterministic capability plans only:
- validates the planner-emitted dependency contract;
- seeds verified initial facts into capsule V2;
- resolves cross-capability $result reads from capsule state, never raw trace state;
- content-binds producer, resolved action, result/evidence payload, inputs, and outputs;
- validates persisted capsule heads during resume and exposes the longest safe prefix.

This proves declared cross-capability state continuity for the bound execution path.
It does not prove semantic completeness of capability declarations or completeness
of external evidence channels.
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

SCHEMA = "PROJECT_BRAIN_COMPOSITION_STATE_CAPSULE_GUARD_V2"


class CompositionGuardError(ValueError):
    pass


def _load_capsule():
    path = pathlib.Path(__file__).resolve().with_name("composition_state_capsule_v2.py")
    spec = importlib.util.spec_from_file_location(
        "project_brain_composition_state_capsule_guard_v2_dependency", path
    )
    if spec is None or spec.loader is None:
        raise CompositionGuardError("CAPSULE_V2_MODULE_LOAD_FAILED")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _canon(value: Any) -> str:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
    except (TypeError, ValueError) as exc:
        raise CompositionGuardError("NON_CANONICALIZABLE_VALUE") from exc


def _validate_channel_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CompositionGuardError("CHANNEL_RECEIPT_INVALID")
    receipt = copy.deepcopy(dict(value))
    if receipt.get("schema") != "PROJECT_BRAIN_COMPOSITION_RUNTIME_CHANNEL_GUARD_V1":
        raise CompositionGuardError("CHANNEL_RECEIPT_SCHEMA_INVALID")
    supplied = receipt.pop("channel_manifest_sha256", None)
    if not isinstance(supplied, str) or len(supplied) != 64:
        raise CompositionGuardError("CHANNEL_RECEIPT_HASH_INVALID")
    computed = hashlib.sha256(_canon(receipt).encode("utf-8")).hexdigest()
    if supplied != computed:
        raise CompositionGuardError("CHANNEL_RECEIPT_HASH_MISMATCH")
    receipt["channel_manifest_sha256"] = supplied
    return receipt


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
            raise CompositionGuardError(f"CONTRACT_{index}_PROVIDER_BINDING_MISMATCH")

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
        "state_reads_are_capsule_sourced": True,
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
    evidence_id = "verified_initial_fact_declaration"
    return capsule_mod.append_macrostep(
        cap,
        producer_ref=producer_ref,
        producer_descriptor={
            "kind": "capability_planner",
            "role": "verified_initial_fact_source",
            "initial_facts": initial,
        },
        action_ref=action_ref,
        action_descriptor={
            "type": "seed_verified_initial_facts",
            "facts": initial,
        },
        requires=[],
        provides=initial,
        values={
            fact: {"effect": fact, "source": "verified_initial_fact"}
            for fact in initial
        },
        evidence_values={
            evidence_id: {
                "kind": "verified_initial_fact_declaration",
                "facts": initial,
            }
        },
        lineage={
            fact: [
                "evidence:" + evidence_id,
                "action:" + action_ref,
                "producer:" + producer_ref,
            ]
            for fact in initial
        },
    )


def assert_action_ready(
    capsule: Mapping[str, Any], row: Mapping[str, Any]
) -> dict[str, Any]:
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


def _field(value: Any, path: str) -> Any:
    current = value
    for token in path.split("."):
        if isinstance(current, Mapping):
            if token not in current:
                raise CompositionGuardError("RESULT_REFERENCE_FIELD_MISSING:" + path)
            current = current[token]
        elif isinstance(current, list) and token.isdigit():
            index = int(token)
            if index < 0 or index >= len(current):
                raise CompositionGuardError("RESULT_REFERENCE_INDEX_INVALID:" + path)
            current = current[index]
        else:
            raise CompositionGuardError("RESULT_REFERENCE_FIELD_INVALID:" + path)
    return copy.deepcopy(current)


def resolve_action_from_capsule(
    capsule: Mapping[str, Any],
    row: Mapping[str, Any],
    raw_action: Mapping[str, Any],
):
    capsule_mod = _load_capsule()
    if not isinstance(raw_action, Mapping):
        raise CompositionGuardError("RAW_ACTION_INVALID")
    requires = _strings(row.get("requires"), "ROW_REQUIRES")
    context = capsule_mod.project_context(capsule, requires)
    bindings = row.get("provider_bindings")
    if not isinstance(bindings, Mapping):
        raise CompositionGuardError("ROW_PROVIDER_BINDINGS_INVALID")

    def resolve(value: Any) -> Any:
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
                candidates = sorted(
                    effect
                    for effect, provider in bindings.items()
                    if isinstance(provider, Mapping) and provider.get("cycle") == cycle
                )
                if not candidates:
                    raise CompositionGuardError(
                        "RESULT_REFERENCE_HAS_NO_REQUIRED_EFFECT:" + str(cycle)
                    )
                payloads = []
                for effect in candidates:
                    state = context["values"].get(effect)
                    if not isinstance(state, Mapping):
                        raise CompositionGuardError(
                            "CAPSULE_EFFECT_STATE_INVALID:" + effect
                        )
                    provider = bindings[effect]
                    if (
                        state.get("producer_cycle") != cycle
                        or state.get("capability_id") != provider.get("capability_id")
                        or "result" not in state
                    ):
                        raise CompositionGuardError(
                            "CAPSULE_PROVIDER_IDENTITY_MISMATCH:" + effect
                        )
                    payloads.append(state["result"])
                baseline = _canon(payloads[0])
                if any(_canon(item) != baseline for item in payloads[1:]):
                    raise CompositionGuardError(
                        "AMBIGUOUS_PROVIDER_EFFECT_STATE:" + str(cycle)
                    )
                return _field(payloads[0], field.strip())
            return {key: resolve(item) for key, item in value.items()}
        if isinstance(value, list):
            return [resolve(item) for item in value]
        return copy.deepcopy(value)

    resolved = resolve(raw_action)
    if _result_refs(resolved):
        raise CompositionGuardError("UNRESOLVED_RESULT_REFERENCE")
    return resolved


def append_action_result(
    capsule: Mapping[str, Any],
    row: Mapping[str, Any],
    action: Mapping[str, Any],
    result: Any,
    channel_receipt: Mapping[str, Any] | None = None,
):
    capsule_mod = _load_capsule()
    cycle = row.get("cycle")
    cid = str(row.get("capability_id") or "").strip()
    requires = _strings(row.get("requires"), "ROW_REQUIRES")
    provides = _strings(row.get("provides"), "ROW_PROVIDES")
    result_fields = _strings(row.get("result_fields"), "ROW_RESULT_FIELDS")
    if not isinstance(cycle, int) or cycle < 0 or not cid:
        raise CompositionGuardError("ROW_IDENTITY_INVALID")
    if not isinstance(action, Mapping):
        raise CompositionGuardError("RESOLVED_ACTION_INVALID")
    if isinstance(result, Mapping):
        missing_fields = [field for field in result_fields if field not in result]
        if missing_fields:
            raise CompositionGuardError(
                "DECLARED_RESULT_FIELD_MISSING:" + ",".join(sorted(missing_fields))
            )
    elif result_fields:
        raise CompositionGuardError("RESULT_OBJECT_REQUIRED_FOR_DECLARED_FIELDS")

    producer_ref = cid
    action_ref = f"capability:{cid}:cycle:{cycle}"
    evidence_id = f"execution_result:{cycle}"
    lineage_refs = (
        ["state:" + effect for effect in requires]
        + ["evidence:" + evidence_id, "action:" + action_ref, "producer:" + producer_ref]
    )
    if channel_receipt is not None:
        channel_receipt = _validate_channel_receipt(channel_receipt)
    values = {
        effect: {
            "effect": effect,
            "producer_cycle": cycle,
            "capability_id": cid,
            "result": copy.deepcopy(result),
            "channel_manifest_sha256": (
                channel_receipt.get("channel_manifest_sha256")
                if channel_receipt is not None
                else None
            ),
        }
        for effect in provides
    }
    execution_evidence = {
        "kind": "executed_capability_result",
        "cycle": cycle,
        "capability_id": cid,
        "result": copy.deepcopy(result),
    }
    if channel_receipt is not None:
        execution_evidence["runtime_channel_receipt"] = copy.deepcopy(dict(channel_receipt))
    return capsule_mod.append_macrostep(
        capsule,
        producer_ref=producer_ref,
        producer_descriptor={
            "kind": "capability_contract_row",
            "capability_id": cid,
            "cycle": cycle,
            "requires": requires,
            "provides": provides,
            "result_fields": result_fields,
            "provider_bindings": copy.deepcopy(dict(row.get("provider_bindings") or {})),
        },
        action_ref=action_ref,
        action_descriptor=copy.deepcopy(dict(action)),
        requires=requires,
        provides=provides,
        values=values,
        evidence_values={evidence_id: execution_evidence},
        lineage={effect: list(lineage_refs) for effect in provides},
    )


def rebuild_valid_prefix(
    actions: Sequence[Mapping[str, Any]],
    contract: Sequence[Mapping[str, Any]],
    initial_facts: Sequence[str],
    trace: Sequence[Mapping[str, Any]],
):
    validated = validate_plan(actions, contract, initial_facts)
    cap = seed_capsule(validated["initial_facts"])
    valid_count = 0
    reason = None
    max_capability_records = min(len(trace), len(validated["contract"]))

    for cycle in range(max_capability_records):
        try:
            record = trace[cycle]
            if not isinstance(record, Mapping) or record.get("cycle") != cycle:
                raise CompositionGuardError(f"TRACE_{cycle}_INVALID")
            row = validated["contract"][cycle]
            assert_action_ready(cap, row)
            expected_action = resolve_action_from_capsule(cap, row, actions[cycle])
            if _canon(record.get("plan")) != _canon(expected_action):
                raise CompositionGuardError(f"TRACE_{cycle}_RESOLVED_ACTION_DRIFT")
            cap = append_action_result(
                cap,
                row,
                expected_action,
                record.get("result"),
                record.get("composition_channel_receipt"),
            )
            expected_head = cap.get("head_hash")
            if record.get("composition_capsule_head_hash") != expected_head:
                raise CompositionGuardError(f"TRACE_{cycle}_CAPSULE_HEAD_MISMATCH")
            valid_count += 1
        except Exception as exc:
            reason = type(exc).__name__ + ":" + str(exc)
            break

    verdict = _load_capsule().verify_capsule(cap)
    if verdict.get("status") != "PASS":
        raise CompositionGuardError(
            "REBUILT_CAPSULE_INVALID:" + str(verdict.get("reason"))
        )
    return {
        "schema": SCHEMA,
        "capsule": cap,
        "valid_count": valid_count,
        "reason": reason,
        "trace_count": len(trace),
        "contract_count": len(validated["contract"]),
    }


def verify_capsule(capsule: Mapping[str, Any]) -> dict[str, Any]:
    return _load_capsule().verify_capsule(capsule)
