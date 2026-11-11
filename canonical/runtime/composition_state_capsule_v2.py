"""Strict content-bound cross-role state/provenance capsule v2.

V2 repairs two provenance holes in v1:
1. evidence references are bound to exact canonical evidence payload hashes;
2. producer and action identities/configurations are bound to exact canonical
   descriptors, and every provided output must explicitly cite both in lineage.

This still does not prove closed-world integration/no-bypass. That remains a
separate system-level premise.
"""
from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA = "PROJECT_BRAIN_COMPOSITION_STATE_CAPSULE_V2"
GENESIS_HASH = hashlib.sha256(
    b"PROJECT_BRAIN_COMPOSITION_STATE_CAPSULE_V2\0GENESIS"
).hexdigest()


class CapsuleError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CapsuleError("NON_CANONICALIZABLE_VALUE") from exc


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CapsuleError(label + "_INVALID")
    return value.strip()


def _tokens(value: Any, label: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise CapsuleError(label + "_INVALID")
    out = [_token(x, label + "_ITEM") for x in value]
    if len(out) != len(set(out)):
        raise CapsuleError(label + "_DUPLICATE")
    return out


def _object(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CapsuleError(label + "_INVALID")
    _canon(value)
    return value


def empty_capsule() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "genesis_hash": GENESIS_HASH,
        "head_hash": GENESIS_HASH,
        "records": [],
    }


def verify_capsule(capsule: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(capsule, Mapping):
            raise CapsuleError("CAPSULE_NOT_OBJECT")
        if capsule.get("schema") != SCHEMA:
            raise CapsuleError("SCHEMA_MISMATCH")
        if capsule.get("genesis_hash") != GENESIS_HASH:
            raise CapsuleError("GENESIS_MISMATCH")
        records = capsule.get("records")
        if not isinstance(records, list):
            raise CapsuleError("RECORDS_INVALID")

        parent = GENESIS_HASH
        latest: dict[str, dict[str, Any]] = {}

        for index, record in enumerate(records):
            if not isinstance(record, Mapping):
                raise CapsuleError(f"RECORD_{index}_NOT_OBJECT")
            if record.get("index") != index:
                raise CapsuleError(f"RECORD_{index}_INDEX_MISMATCH")
            if record.get("parent_hash") != parent:
                raise CapsuleError(f"RECORD_{index}_PARENT_MISMATCH")

            producer_ref = _token(
                record.get("producer_ref"), f"RECORD_{index}_PRODUCER_REF"
            )
            producer_descriptor = _object(
                record.get("producer_descriptor"),
                f"RECORD_{index}_PRODUCER_DESCRIPTOR",
            )
            expected_producer_hash = _sha256(producer_descriptor)
            if record.get("producer_hash") != expected_producer_hash:
                raise CapsuleError(f"RECORD_{index}_PRODUCER_HASH_MISMATCH")

            action_ref = _token(record.get("action_ref"), f"RECORD_{index}_ACTION_REF")
            action_descriptor = _object(
                record.get("action_descriptor"),
                f"RECORD_{index}_ACTION_DESCRIPTOR",
            )
            expected_action_hash = _sha256(action_descriptor)
            if record.get("action_hash") != expected_action_hash:
                raise CapsuleError(f"RECORD_{index}_ACTION_HASH_MISMATCH")

            requires = _tokens(record.get("requires"), f"RECORD_{index}_REQUIRES")
            provides = _tokens(record.get("provides"), f"RECORD_{index}_PROVIDES")

            values = record.get("values")
            if not isinstance(values, Mapping) or set(values) != set(provides):
                raise CapsuleError(f"RECORD_{index}_VALUES_PROVIDES_MISMATCH")
            expected_value_hashes = {
                key: _sha256(values[key]) for key in sorted(provides)
            }
            if record.get("value_hashes") != expected_value_hashes:
                raise CapsuleError(f"RECORD_{index}_VALUE_HASH_MISMATCH")

            evidence_values = record.get("evidence_values")
            if not isinstance(evidence_values, Mapping):
                raise CapsuleError(f"RECORD_{index}_EVIDENCE_VALUES_INVALID")
            evidence_ids = [
                _token(k, f"RECORD_{index}_EVIDENCE_ID") for k in evidence_values
            ]
            if len(evidence_ids) != len(set(evidence_ids)):
                raise CapsuleError(f"RECORD_{index}_EVIDENCE_ID_DUPLICATE")
            expected_evidence_hashes = {
                key: _sha256(evidence_values[key])
                for key in sorted(evidence_values)
            }
            if record.get("evidence_hashes") != expected_evidence_hashes:
                raise CapsuleError(f"RECORD_{index}_EVIDENCE_HASH_MISMATCH")

            input_bindings = record.get("input_bindings")
            if (
                not isinstance(input_bindings, Mapping)
                or set(input_bindings) != set(requires)
            ):
                raise CapsuleError(f"RECORD_{index}_INPUT_BINDINGS_MISMATCH")
            for key in requires:
                if key not in latest:
                    raise CapsuleError(
                        f"RECORD_{index}_MISSING_REQUIRED_STATE:{key}"
                    )
                want = {
                    "record_hash": latest[key]["record_hash"],
                    "value_hash": latest[key]["value_hash"],
                }
                if input_bindings[key] != want:
                    raise CapsuleError(
                        f"RECORD_{index}_INPUT_BINDING_DRIFT:{key}"
                    )

            lineage = record.get("lineage")
            if not isinstance(lineage, Mapping) or set(lineage) != set(provides):
                raise CapsuleError(f"RECORD_{index}_LINEAGE_PROVIDES_MISMATCH")
            for output_key in provides:
                refs = _tokens(
                    lineage[output_key],
                    f"RECORD_{index}_LINEAGE_{output_key}",
                )
                if not refs:
                    raise CapsuleError(
                        f"RECORD_{index}_EMPTY_LINEAGE:{output_key}"
                    )
                required_action = "action:" + action_ref
                required_producer = "producer:" + producer_ref
                if required_action not in refs:
                    raise CapsuleError(
                        f"RECORD_{index}_MISSING_ACTION_LINEAGE:{output_key}"
                    )
                if required_producer not in refs:
                    raise CapsuleError(
                        f"RECORD_{index}_MISSING_PRODUCER_LINEAGE:{output_key}"
                    )
                for ref in refs:
                    if ref.startswith("state:"):
                        key = ref[6:]
                        if key not in requires:
                            raise CapsuleError(
                                f"RECORD_{index}_UNDECLARED_STATE_LINEAGE:"
                                f"{output_key}:{key}"
                            )
                    elif ref.startswith("evidence:"):
                        evidence = ref[9:]
                        if evidence not in evidence_values:
                            raise CapsuleError(
                                f"RECORD_{index}_UNBOUND_EVIDENCE_LINEAGE:"
                                f"{output_key}:{evidence}"
                            )
                    elif ref.startswith("action:"):
                        if ref != required_action:
                            raise CapsuleError(
                                f"RECORD_{index}_ACTION_LINEAGE_MISMATCH:"
                                f"{output_key}"
                            )
                    elif ref.startswith("producer:"):
                        if ref != required_producer:
                            raise CapsuleError(
                                f"RECORD_{index}_PRODUCER_LINEAGE_MISMATCH:"
                                f"{output_key}"
                            )
                    else:
                        raise CapsuleError(
                            f"RECORD_{index}_UNKNOWN_LINEAGE_KIND:"
                            f"{output_key}:{ref}"
                        )

            record_core = {
                "index": index,
                "parent_hash": parent,
                "producer_ref": producer_ref,
                "producer_hash": expected_producer_hash,
                "action_ref": action_ref,
                "action_hash": expected_action_hash,
                "requires": requires,
                "input_bindings": {
                    k: input_bindings[k] for k in sorted(input_bindings)
                },
                "provides": provides,
                "value_hashes": expected_value_hashes,
                "evidence_hashes": expected_evidence_hashes,
                "lineage": {k: lineage[k] for k in sorted(lineage)},
            }
            got_record_hash = _sha256(record_core)
            if record.get("record_hash") != got_record_hash:
                raise CapsuleError(f"RECORD_{index}_HASH_MISMATCH")

            for key in provides:
                latest[key] = {
                    "value": copy.deepcopy(values[key]),
                    "value_hash": expected_value_hashes[key],
                    "record_hash": got_record_hash,
                    "record_index": index,
                    "producer_ref": producer_ref,
                    "producer_hash": expected_producer_hash,
                    "action_ref": action_ref,
                    "action_hash": expected_action_hash,
                    "lineage": list(lineage[key]),
                }
            parent = got_record_hash

        if capsule.get("head_hash") != parent:
            raise CapsuleError("HEAD_HASH_MISMATCH")

        return {
            "schema": SCHEMA,
            "status": "PASS",
            "record_count": len(records),
            "head_hash": parent,
            "latest_key_count": len(latest),
            "latest": latest,
            "state_history_is_append_only": True,
            "evidence_is_content_bound": True,
            "action_is_content_bound": True,
            "producer_is_content_bound": True,
            "output_lineage_binds_action_and_producer": True,
            "rollback_is_exact_prefix": True,
            "acceptance_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
            "acceptance_credit_delta": 0,
        }


def _verified_latest(
    capsule: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    verdict = verify_capsule(capsule)
    if verdict["status"] != "PASS":
        raise CapsuleError(verdict["reason"])
    return verdict["latest"]


def project_context(
    capsule: Mapping[str, Any],
    requires: Sequence[str],
) -> dict[str, Any]:
    required = _tokens(requires, "REQUIRES")
    latest = _verified_latest(capsule)
    missing = [key for key in required if key not in latest]
    if missing:
        raise CapsuleError("MISSING_REQUIRED_STATE:" + ",".join(missing))
    return {
        "capsule_head_hash": capsule["head_hash"],
        "values": {
            key: copy.deepcopy(latest[key]["value"]) for key in required
        },
        "bindings": {
            key: {
                "record_hash": latest[key]["record_hash"],
                "value_hash": latest[key]["value_hash"],
            }
            for key in required
        },
    }


def append_macrostep(
    capsule: Mapping[str, Any],
    *,
    producer_ref: str,
    producer_descriptor: Mapping[str, Any],
    action_ref: str,
    action_descriptor: Mapping[str, Any],
    requires: Sequence[str],
    provides: Sequence[str],
    values: Mapping[str, Any],
    evidence_values: Mapping[str, Any],
    lineage: Mapping[str, Sequence[str]],
) -> dict[str, Any]:
    producer_ref = _token(producer_ref, "PRODUCER_REF")
    producer_descriptor = _object(
        producer_descriptor, "PRODUCER_DESCRIPTOR"
    )
    action_ref = _token(action_ref, "ACTION_REF")
    action_descriptor = _object(action_descriptor, "ACTION_DESCRIPTOR")
    required = _tokens(requires, "REQUIRES")
    provided = _tokens(provides, "PROVIDES")

    latest = _verified_latest(capsule)
    missing = [key for key in required if key not in latest]
    if missing:
        raise CapsuleError("MISSING_REQUIRED_STATE:" + ",".join(missing))
    if not isinstance(values, Mapping) or set(values) != set(provided):
        raise CapsuleError("VALUES_PROVIDES_MISMATCH")
    if not isinstance(evidence_values, Mapping):
        raise CapsuleError("EVIDENCE_VALUES_INVALID")
    for key in evidence_values:
        _token(key, "EVIDENCE_ID")
        _canon(evidence_values[key])
    if not isinstance(lineage, Mapping) or set(lineage) != set(provided):
        raise CapsuleError("LINEAGE_PROVIDES_MISMATCH")

    normalized_lineage: dict[str, list[str]] = {}
    required_action = "action:" + action_ref
    required_producer = "producer:" + producer_ref
    for key in provided:
        refs = _tokens(lineage[key], "LINEAGE_" + key)
        if not refs:
            raise CapsuleError("EMPTY_LINEAGE:" + key)
        if required_action not in refs:
            raise CapsuleError("MISSING_ACTION_LINEAGE:" + key)
        if required_producer not in refs:
            raise CapsuleError("MISSING_PRODUCER_LINEAGE:" + key)
        for ref in refs:
            if ref.startswith("state:"):
                source_key = ref[6:]
                if source_key not in required:
                    raise CapsuleError(
                        "UNDECLARED_STATE_LINEAGE:" + key + ":" + source_key
                    )
            elif ref.startswith("evidence:"):
                source_evidence = ref[9:]
                if source_evidence not in evidence_values:
                    raise CapsuleError(
                        "UNBOUND_EVIDENCE_LINEAGE:"
                        + key
                        + ":"
                        + source_evidence
                    )
            elif ref.startswith("action:"):
                if ref != required_action:
                    raise CapsuleError("ACTION_LINEAGE_MISMATCH:" + key)
            elif ref.startswith("producer:"):
                if ref != required_producer:
                    raise CapsuleError("PRODUCER_LINEAGE_MISMATCH:" + key)
            else:
                raise CapsuleError("UNKNOWN_LINEAGE_KIND:" + key + ":" + ref)
        normalized_lineage[key] = refs

    input_bindings = {
        key: {
            "record_hash": latest[key]["record_hash"],
            "value_hash": latest[key]["value_hash"],
        }
        for key in required
    }
    value_hashes = {
        key: _sha256(values[key]) for key in sorted(provided)
    }
    evidence_hashes = {
        key: _sha256(evidence_values[key])
        for key in sorted(evidence_values)
    }
    producer_hash = _sha256(producer_descriptor)
    action_hash = _sha256(action_descriptor)
    index = len(capsule["records"])
    record_core = {
        "index": index,
        "parent_hash": capsule["head_hash"],
        "producer_ref": producer_ref,
        "producer_hash": producer_hash,
        "action_ref": action_ref,
        "action_hash": action_hash,
        "requires": required,
        "input_bindings": {
            k: input_bindings[k] for k in sorted(input_bindings)
        },
        "provides": provided,
        "value_hashes": value_hashes,
        "evidence_hashes": evidence_hashes,
        "lineage": {
            k: normalized_lineage[k] for k in sorted(normalized_lineage)
        },
    }
    record = {
        **record_core,
        "producer_descriptor": copy.deepcopy(dict(producer_descriptor)),
        "action_descriptor": copy.deepcopy(dict(action_descriptor)),
        "values": {
            key: copy.deepcopy(values[key]) for key in provided
        },
        "evidence_values": {
            key: copy.deepcopy(evidence_values[key])
            for key in evidence_values
        },
        "record_hash": _sha256(record_core),
    }
    out = copy.deepcopy(dict(capsule))
    out["records"] = list(out["records"]) + [record]
    out["head_hash"] = record["record_hash"]

    verdict = verify_capsule(out)
    if verdict["status"] != "PASS":
        raise CapsuleError(
            "POST_COMMIT_VERIFICATION_FAILED:" + verdict["reason"]
        )
    return out


def rollback_to(
    capsule: Mapping[str, Any],
    target_head_hash: str,
) -> dict[str, Any]:
    target = _token(target_head_hash, "TARGET_HEAD_HASH")
    verdict = verify_capsule(capsule)
    if verdict["status"] != "PASS":
        raise CapsuleError(verdict["reason"])

    if target == GENESIS_HASH:
        return empty_capsule()

    records = capsule["records"]
    match = None
    for i, record in enumerate(records):
        if record["record_hash"] == target:
            match = i
            break
    if match is None:
        raise CapsuleError("UNKNOWN_ROLLBACK_TARGET")

    out = {
        "schema": SCHEMA,
        "genesis_hash": GENESIS_HASH,
        "head_hash": target,
        "records": copy.deepcopy(records[: match + 1]),
    }
    post = verify_capsule(out)
    if post["status"] != "PASS":
        raise CapsuleError(
            "ROLLBACK_VERIFICATION_FAILED:" + post["reason"]
        )
    return out
