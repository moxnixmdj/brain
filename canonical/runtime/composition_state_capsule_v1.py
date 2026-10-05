"""Append-only, content-addressed cross-role state/provenance capsule.

This module is a constructive mechanism for two composition premises:
state preservation and content-bound lineage. It is deliberately fail-closed.

It does not prove that every composition path actually uses this capsule.
That integration/no-bypass property is a separate load-bearing premise.
"""
from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA = "PROJECT_BRAIN_COMPOSITION_STATE_CAPSULE_V1"
GENESIS_HASH = hashlib.sha256(
    b"PROJECT_BRAIN_COMPOSITION_STATE_CAPSULE_V1\0GENESIS"
).hexdigest()


class CapsuleError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


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


def empty_capsule() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "genesis_hash": GENESIS_HASH,
        "head_hash": GENESIS_HASH,
        "records": [],
    }


def _record_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "index": record["index"],
        "parent_hash": record["parent_hash"],
        "producer": record["producer"],
        "action_ref": record["action_ref"],
        "requires": record["requires"],
        "input_bindings": record["input_bindings"],
        "provides": record["provides"],
        "value_hashes": record["value_hashes"],
        "evidence_refs": record["evidence_refs"],
        "lineage": record["lineage"],
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

            producer = _token(record.get("producer"), f"RECORD_{index}_PRODUCER")
            action_ref = _token(record.get("action_ref"), f"RECORD_{index}_ACTION")
            requires = _tokens(record.get("requires"), f"RECORD_{index}_REQUIRES")
            provides = _tokens(record.get("provides"), f"RECORD_{index}_PROVIDES")
            evidence_refs = _tokens(
                record.get("evidence_refs"), f"RECORD_{index}_EVIDENCE"
            )

            values = record.get("values")
            if not isinstance(values, Mapping) or set(values) != set(provides):
                raise CapsuleError(f"RECORD_{index}_VALUES_PROVIDES_MISMATCH")

            expected_value_hashes = {
                key: _sha256(values[key]) for key in sorted(provides)
            }
            if record.get("value_hashes") != expected_value_hashes:
                raise CapsuleError(f"RECORD_{index}_VALUE_HASH_MISMATCH")

            input_bindings = record.get("input_bindings")
            if not isinstance(input_bindings, Mapping) or set(input_bindings) != set(requires):
                raise CapsuleError(f"RECORD_{index}_INPUT_BINDINGS_MISMATCH")
            for key in requires:
                if key not in latest:
                    raise CapsuleError(f"RECORD_{index}_MISSING_REQUIRED_STATE:{key}")
                want = {
                    "record_hash": latest[key]["record_hash"],
                    "value_hash": latest[key]["value_hash"],
                }
                if input_bindings[key] != want:
                    raise CapsuleError(f"RECORD_{index}_INPUT_BINDING_DRIFT:{key}")

            lineage = record.get("lineage")
            if not isinstance(lineage, Mapping) or set(lineage) != set(provides):
                raise CapsuleError(f"RECORD_{index}_LINEAGE_PROVIDES_MISMATCH")
            for output_key in provides:
                refs = _tokens(
                    lineage[output_key], f"RECORD_{index}_LINEAGE_{output_key}"
                )
                if not refs:
                    raise CapsuleError(f"RECORD_{index}_EMPTY_LINEAGE:{output_key}")
                for ref in refs:
                    if ref.startswith("state:"):
                        key = ref[6:]
                        if key not in requires:
                            raise CapsuleError(
                                f"RECORD_{index}_UNDECLARED_STATE_LINEAGE:{output_key}:{key}"
                            )
                    elif ref.startswith("evidence:"):
                        evidence = ref[9:]
                        if evidence not in evidence_refs:
                            raise CapsuleError(
                                f"RECORD_{index}_UNBOUND_EVIDENCE_LINEAGE:{output_key}:{evidence}"
                            )
                    elif ref.startswith("action:"):
                        action = ref[7:]
                        if action != action_ref:
                            raise CapsuleError(
                                f"RECORD_{index}_ACTION_LINEAGE_MISMATCH:{output_key}"
                            )
                    else:
                        raise CapsuleError(
                            f"RECORD_{index}_UNKNOWN_LINEAGE_KIND:{output_key}:{ref}"
                        )

            normalized = {
                "index": index,
                "parent_hash": parent,
                "producer": producer,
                "action_ref": action_ref,
                "requires": requires,
                "input_bindings": {
                    k: input_bindings[k] for k in sorted(input_bindings)
                },
                "provides": provides,
                "value_hashes": expected_value_hashes,
                "evidence_refs": evidence_refs,
                "lineage": {k: lineage[k] for k in sorted(lineage)},
            }
            got_record_hash = _sha256(normalized)
            if record.get("record_hash") != got_record_hash:
                raise CapsuleError(f"RECORD_{index}_HASH_MISMATCH")

            for key in provides:
                latest[key] = {
                    "value": copy.deepcopy(values[key]),
                    "value_hash": expected_value_hashes[key],
                    "record_hash": got_record_hash,
                    "record_index": index,
                    "producer": producer,
                    "action_ref": action_ref,
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


def _verified_latest(capsule: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
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
        "values": {key: copy.deepcopy(latest[key]["value"]) for key in required},
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
    producer: str,
    action_ref: str,
    requires: Sequence[str],
    provides: Sequence[str],
    values: Mapping[str, Any],
    evidence_refs: Sequence[str],
    lineage: Mapping[str, Sequence[str]],
) -> dict[str, Any]:
    producer = _token(producer, "PRODUCER")
    action_ref = _token(action_ref, "ACTION_REF")
    required = _tokens(requires, "REQUIRES")
    provided = _tokens(provides, "PROVIDES")
    evidence = _tokens(evidence_refs, "EVIDENCE_REFS")

    latest = _verified_latest(capsule)
    missing = [key for key in required if key not in latest]
    if missing:
        raise CapsuleError("MISSING_REQUIRED_STATE:" + ",".join(missing))
    if not isinstance(values, Mapping) or set(values) != set(provided):
        raise CapsuleError("VALUES_PROVIDES_MISMATCH")
    if not isinstance(lineage, Mapping) or set(lineage) != set(provided):
        raise CapsuleError("LINEAGE_PROVIDES_MISMATCH")

    normalized_lineage: dict[str, list[str]] = {}
    for key in provided:
        refs = _tokens(lineage[key], "LINEAGE_" + key)
        if not refs:
            raise CapsuleError("EMPTY_LINEAGE:" + key)
        for ref in refs:
            if ref.startswith("state:"):
                source_key = ref[6:]
                if source_key not in required:
                    raise CapsuleError("UNDECLARED_STATE_LINEAGE:" + key + ":" + source_key)
            elif ref.startswith("evidence:"):
                source_evidence = ref[9:]
                if source_evidence not in evidence:
                    raise CapsuleError("UNBOUND_EVIDENCE_LINEAGE:" + key + ":" + source_evidence)
            elif ref.startswith("action:"):
                if ref[7:] != action_ref:
                    raise CapsuleError("ACTION_LINEAGE_MISMATCH:" + key)
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
    value_hashes = {key: _sha256(values[key]) for key in sorted(provided)}
    index = len(capsule["records"])
    record_core = {
        "index": index,
        "parent_hash": capsule["head_hash"],
        "producer": producer,
        "action_ref": action_ref,
        "requires": required,
        "input_bindings": {k: input_bindings[k] for k in sorted(input_bindings)},
        "provides": provided,
        "value_hashes": value_hashes,
        "evidence_refs": evidence,
        "lineage": {k: normalized_lineage[k] for k in sorted(normalized_lineage)},
    }
    record = {
        **record_core,
        "values": {key: copy.deepcopy(values[key]) for key in provided},
        "record_hash": _sha256(record_core),
    }
    out = copy.deepcopy(dict(capsule))
    out["records"] = list(out["records"]) + [record]
    out["head_hash"] = record["record_hash"]

    verdict = verify_capsule(out)
    if verdict["status"] != "PASS":
        raise CapsuleError("POST_COMMIT_VERIFICATION_FAILED:" + verdict["reason"])
    return out


def rollback_to(capsule: Mapping[str, Any], target_head_hash: str) -> dict[str, Any]:
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
        raise CapsuleError("ROLLBACK_VERIFICATION_FAILED:" + post["reason"])
    return out
