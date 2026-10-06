from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_SEMANTIC_STATE_BUS_V1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class StateBusError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise StateBusError("VALUE_NOT_CANONICAL_JSON") from exc


def sha256(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _token(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StateBusError(name + "_INVALID")
    return value.strip()


def _sha64(value: Any, name: str) -> str:
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        raise StateBusError(name + "_INVALID")
    return value


def _shape(value: Any) -> Any:
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "bool"}
    if isinstance(value, int) and not isinstance(value, bool):
        return {"type": "int"}
    if isinstance(value, float):
        return {"type": "float"}
    if isinstance(value, str):
        return {"type": "str"}
    if isinstance(value, list):
        return {
            "type": "list",
            "length": len(value),
            "items": [_shape(x) for x in value],
        }
    if isinstance(value, Mapping):
        return {
            "type": "object",
            "fields": {
                str(k): _shape(v)
                for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))
            },
        }
    raise StateBusError("VALUE_SHAPE_UNSUPPORTED")


def shape_sha256(value: Any) -> str:
    return sha256(_shape(value))


def _state_core(state: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": state.get("schema"),
        "case_id": state.get("case_id"),
        "base_context_sha256": state.get("base_context_sha256"),
        "revision": state.get("revision"),
        "entries": state.get("entries"),
    }


def state_sha256(state: Mapping[str, Any]) -> str:
    return sha256(_state_core(state))


def _validate_state(state: Any) -> dict[str, Any]:
    if not isinstance(state, Mapping):
        raise StateBusError("STATE_INVALID")
    if state.get("schema") != SCHEMA:
        raise StateBusError("STATE_SCHEMA_INVALID")
    _token(state.get("case_id"), "CASE_ID")
    _sha64(state.get("base_context_sha256"), "BASE_CONTEXT_SHA256")
    revision = state.get("revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
        raise StateBusError("STATE_REVISION_INVALID")
    entries = state.get("entries")
    if not isinstance(entries, Mapping):
        raise StateBusError("STATE_ENTRIES_INVALID")
    claimed = state.get("state_sha256")
    if not isinstance(claimed, str) or claimed != state_sha256(state):
        raise StateBusError("STATE_SHA256_MISMATCH")

    for key, entry in entries.items():
        _token(key, "ENTRY_KEY")
        if not isinstance(entry, Mapping):
            raise StateBusError("ENTRY_INVALID:" + str(key))
        value = entry.get("value")
        expected_value_sha = sha256(value)
        if entry.get("value_sha256") != expected_value_sha:
            raise StateBusError("ENTRY_VALUE_SHA256_MISMATCH:" + str(key))
        expected_shape = shape_sha256(value)
        if entry.get("shape_sha256") != expected_shape:
            raise StateBusError("ENTRY_SHAPE_SHA256_MISMATCH:" + str(key))
        _token(entry.get("semantic_type"), "ENTRY_SEMANTIC_TYPE")
        _token(entry.get("producer_stage"), "ENTRY_PRODUCER_STAGE")
        _sha64(entry.get("provenance_sha256"), "ENTRY_PROVENANCE_SHA256")
        version = entry.get("version")
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            raise StateBusError("ENTRY_VERSION_INVALID:" + str(key))
        binding = {
            "key": str(key),
            "semantic_type": entry["semantic_type"],
            "producer_stage": entry["producer_stage"],
            "version": version,
            "value_sha256": expected_value_sha,
            "shape_sha256": expected_shape,
            "provenance_sha256": entry["provenance_sha256"],
        }
        if entry.get("binding_sha256") != sha256(binding):
            raise StateBusError("ENTRY_BINDING_SHA256_MISMATCH:" + str(key))

    return copy.deepcopy(dict(state))


def empty_state(*, case_id: str, base_context_sha256: str) -> dict[str, Any]:
    case_id = _token(case_id, "CASE_ID")
    base = _sha64(base_context_sha256, "BASE_CONTEXT_SHA256")
    state = {
        "schema": SCHEMA,
        "case_id": case_id,
        "base_context_sha256": base,
        "revision": 0,
        "entries": {},
    }
    state["state_sha256"] = state_sha256(state)
    return state


def write(
    state: Mapping[str, Any],
    *,
    key: str,
    value: Any,
    semantic_type: str,
    producer_stage: str,
    provenance_sha256: str,
    expected_state_sha256: str,
    allow_update: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    current = _validate_state(state)
    if expected_state_sha256 != current["state_sha256"]:
        raise StateBusError("STALE_STATE_WRITE")
    key = _token(key, "KEY")
    semantic_type = _token(semantic_type, "SEMANTIC_TYPE")
    producer_stage = _token(producer_stage, "PRODUCER_STAGE")
    provenance = _sha64(provenance_sha256, "PROVENANCE_SHA256")

    existing = current["entries"].get(key)
    if existing is not None and not allow_update:
        raise StateBusError("KEY_ALREADY_EXISTS:" + key)

    version = 1 if existing is None else int(existing["version"]) + 1
    value_sha = sha256(value)
    shape_sha = shape_sha256(value)
    binding = {
        "key": key,
        "semantic_type": semantic_type,
        "producer_stage": producer_stage,
        "version": version,
        "value_sha256": value_sha,
        "shape_sha256": shape_sha,
        "provenance_sha256": provenance,
    }
    entry = {
        "value": copy.deepcopy(value),
        **binding,
        "binding_sha256": sha256(binding),
    }

    before = current["state_sha256"]
    current["entries"][key] = entry
    current["entries"] = dict(sorted(current["entries"].items()))
    current["revision"] = int(current["revision"]) + 1
    current["state_sha256"] = state_sha256(current)
    receipt = {
        "operation": "UPDATE" if existing is not None else "WRITE",
        "case_id": current["case_id"],
        "key": key,
        "version": version,
        "before_state_sha256": before,
        "after_state_sha256": current["state_sha256"],
        "entry_binding_sha256": entry["binding_sha256"],
        "value_sha256": value_sha,
        "shape_sha256": shape_sha,
        "producer_stage": producer_stage,
        "provenance_sha256": provenance,
    }
    receipt["receipt_sha256"] = sha256(receipt)
    return current, receipt


def read(
    state: Mapping[str, Any],
    *,
    keys: Sequence[str],
    consumer_stage: str,
) -> dict[str, Any]:
    current = _validate_state(state)
    consumer = _token(consumer_stage, "CONSUMER_STAGE")
    if not isinstance(keys, Sequence) or isinstance(keys, (str, bytes)):
        raise StateBusError("READ_KEYS_INVALID")
    normalized = [_token(k, "READ_KEY") for k in keys]
    if len(normalized) != len(set(normalized)):
        raise StateBusError("READ_KEY_DUPLICATE")
    missing = sorted(k for k in normalized if k not in current["entries"])
    if missing:
        raise StateBusError("READ_KEY_MISSING:" + ",".join(missing))

    entries = [
        {
            "key": key,
            "semantic_type": current["entries"][key]["semantic_type"],
            "version": current["entries"][key]["version"],
            "value": copy.deepcopy(current["entries"][key]["value"]),
            "value_sha256": current["entries"][key]["value_sha256"],
            "shape_sha256": current["entries"][key]["shape_sha256"],
            "producer_stage": current["entries"][key]["producer_stage"],
            "entry_binding_sha256": current["entries"][key]["binding_sha256"],
        }
        for key in normalized
    ]
    binding = {
        "case_id": current["case_id"],
        "state_sha256": current["state_sha256"],
        "consumer_stage": consumer,
        "keys": normalized,
        "entry_bindings": [x["entry_binding_sha256"] for x in entries],
    }
    return {
        "entries": entries,
        **binding,
        "read_set_sha256": sha256(binding),
    }


def checkpoint(
    state: Mapping[str, Any],
    *,
    label: str,
) -> dict[str, Any]:
    current = _validate_state(state)
    label = _token(label, "CHECKPOINT_LABEL")
    snapshot = copy.deepcopy(current)
    binding = {
        "case_id": current["case_id"],
        "label": label,
        "snapshot_state_sha256": current["state_sha256"],
        "snapshot_revision": current["revision"],
    }
    return {
        **binding,
        "checkpoint_sha256": sha256(binding),
        "snapshot": snapshot,
    }


def rollback(
    state: Mapping[str, Any],
    *,
    checkpoint_record: Mapping[str, Any],
    expected_current_state_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    current = _validate_state(state)
    if expected_current_state_sha256 != current["state_sha256"]:
        raise StateBusError("STALE_STATE_ROLLBACK")
    if not isinstance(checkpoint_record, Mapping):
        raise StateBusError("CHECKPOINT_INVALID")
    snapshot = checkpoint_record.get("snapshot")
    restored = _validate_state(snapshot)
    if restored["case_id"] != current["case_id"]:
        raise StateBusError("CHECKPOINT_CASE_ID_MISMATCH")
    if restored["base_context_sha256"] != current["base_context_sha256"]:
        raise StateBusError("CHECKPOINT_BASE_CONTEXT_MISMATCH")
    if checkpoint_record.get("snapshot_state_sha256") != restored["state_sha256"]:
        raise StateBusError("CHECKPOINT_STATE_SHA256_MISMATCH")
    binding = {
        "case_id": restored["case_id"],
        "label": checkpoint_record.get("label"),
        "snapshot_state_sha256": restored["state_sha256"],
        "snapshot_revision": restored["revision"],
    }
    if checkpoint_record.get("checkpoint_sha256") != sha256(binding):
        raise StateBusError("CHECKPOINT_SHA256_MISMATCH")

    receipt = {
        "operation": "ROLLBACK",
        "case_id": current["case_id"],
        "from_state_sha256": current["state_sha256"],
        "checkpoint_sha256": checkpoint_record["checkpoint_sha256"],
        "restored_state_sha256": restored["state_sha256"],
        "exact_state_restoration": True,
    }
    receipt["receipt_sha256"] = sha256(receipt)
    return restored, receipt


def intervene_same_shape(
    state: Mapping[str, Any],
    *,
    key: str,
    decoy_value: Any,
    intervention_stage: str,
    provenance_sha256: str,
    expected_state_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    current = _validate_state(state)
    key = _token(key, "KEY")
    if key not in current["entries"]:
        raise StateBusError("INTERVENTION_KEY_MISSING:" + key)
    prior = current["entries"][key]
    if sha256(decoy_value) == prior["value_sha256"]:
        raise StateBusError("DECOY_NOT_SEMANTICALLY_DISTINCT")
    if shape_sha256(decoy_value) != prior["shape_sha256"]:
        raise StateBusError("DECOY_SHAPE_MISMATCH")

    updated, write_receipt = write(
        current,
        key=key,
        value=decoy_value,
        semantic_type=prior["semantic_type"],
        producer_stage=_token(intervention_stage, "INTERVENTION_STAGE"),
        provenance_sha256=provenance_sha256,
        expected_state_sha256=expected_state_sha256,
        allow_update=True,
    )
    receipt = {
        "operation": "SAME_SHAPE_SEMANTIC_INTERVENTION",
        "case_id": current["case_id"],
        "key": key,
        "true_value_sha256": prior["value_sha256"],
        "decoy_value_sha256": updated["entries"][key]["value_sha256"],
        "shape_sha256": prior["shape_sha256"],
        "before_state_sha256": current["state_sha256"],
        "after_state_sha256": updated["state_sha256"],
        "write_receipt_sha256": write_receipt["receipt_sha256"],
    }
    receipt["receipt_sha256"] = sha256(receipt)
    return updated, receipt


def bind_downstream_context(
    state: Mapping[str, Any],
    *,
    keys: Sequence[str],
    consumer_stage: str,
    public_task: Mapping[str, Any],
) -> dict[str, Any]:
    read_receipt = read(
        state,
        keys=keys,
        consumer_stage=consumer_stage,
    )
    public_task_sha = sha256(public_task)
    binding = {
        "case_id": state["case_id"],
        "consumer_stage": consumer_stage,
        "public_task_sha256": public_task_sha,
        "read_set_sha256": read_receipt["read_set_sha256"],
        "state_sha256": read_receipt["state_sha256"],
    }
    return {
        "public_task": copy.deepcopy(dict(public_task)),
        "semantic_inputs": copy.deepcopy(read_receipt["entries"]),
        "binding_sha256": sha256(binding),
        "binding": binding,
    }
