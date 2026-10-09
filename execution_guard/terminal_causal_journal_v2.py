#!/usr/bin/env python3
"""Append-only causal journal for irreversible terminal execution.

V2-compatible implementation extends the event vocabulary for cognition-only
evidence retrieval and candidate rejection while preserving the V1 wire format,
namespace, create-once keys, and replay semantics.

The journal records only compact controller facts and evidence hashes, never raw
secret-bearing material. Each sequence position has one create-once remote key.
A conflicting event at the same sequence is a fork and is rejected.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Protocol

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
SCHEMA = "PROJECT_BRAIN_TERMINAL_CAUSAL_JOURNAL_EVENT_V1"
NAMESPACE = "terminal-journal-v1"
MAX_EVENT_BYTES = 32768
MAX_SEQUENCE = 4095
ALLOWED_KINDS = {
    "PLANNER_PROPOSAL_ACTION_INTENT",
    "ACTION_VERIFY_STATE_COMMIT",
    "PLANNER_NO_ACTION",
    "CONTROLLER_TERMINAL",
    "FAULT",
    "PLANNER_EVIDENCE_REQUEST_FULFILLED",
    "PLANNER_CANDIDATE_REJECTED",
}
_SECRET_KEYS = {
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "authorization",
    "password",
    "secret",
    "cookie",
    "set-cookie",
    "gh_token",
    "github_token",
}


class JournalError(RuntimeError):
    pass


class AtomicStore(Protocol):
    def create(self, key: str, value: dict[str, Any]) -> bool: ...
    def read(self, key: str) -> dict[str, Any] | None: ...


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _hex64(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _reject_secrets(value: Any, path: str = "payload") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            name = str(key).strip().lower()
            if (
                name in _SECRET_KEYS
                or name.endswith("_password")
                or name.endswith("_secret")
                or name.endswith("_api_key")
            ):
                raise JournalError("SECRET_BEARING_KEY_REJECTED:" + path + "." + str(key))
            _reject_secrets(child, path + "." + str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_secrets(child, path + f"[{index}]")


def event_key(logical_attempt_id: str, sequence: int) -> str:
    if not _hex64(logical_attempt_id):
        raise JournalError("LOGICAL_ATTEMPT_ID_INVALID")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or not 0 <= sequence <= MAX_SEQUENCE:
        raise JournalError("SEQUENCE_INVALID")
    return f"terminal-journal/{logical_attempt_id}/{sequence:04d}"


def make_event(
    *,
    logical_attempt_id: str,
    sequence: int,
    predecessor_sha256: str | None,
    kind: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    event_key(logical_attempt_id, sequence)
    if sequence == 0:
        if predecessor_sha256 is not None:
            raise JournalError("SEQUENCE_ZERO_PREDECESSOR_MUST_BE_NULL")
    elif not _hex64(predecessor_sha256):
        raise JournalError("PREDECESSOR_SHA256_INVALID")
    if kind not in ALLOWED_KINDS:
        raise JournalError("EVENT_KIND_INVALID:" + str(kind))
    if not isinstance(payload, dict):
        raise JournalError("PAYLOAD_OBJECT_REQUIRED")
    _reject_secrets(payload)
    payload_sha256 = _sha256(payload)
    core = {
        "schema": SCHEMA,
        "logical_attempt_id": logical_attempt_id,
        "sequence": sequence,
        "predecessor_sha256": predecessor_sha256,
        "kind": kind,
        "payload_sha256": payload_sha256,
        "payload": payload,
    }
    event_sha256 = _sha256(core)
    event = {**core, "event_sha256": event_sha256}
    if len(_canon(event)) > MAX_EVENT_BYTES:
        raise JournalError("EVENT_TOO_LARGE")
    return event


def validate_event(event: Any) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise JournalError("EVENT_OBJECT_REQUIRED")
    if event.get("schema") != SCHEMA:
        raise JournalError("EVENT_SCHEMA_INVALID")
    logical = event.get("logical_attempt_id")
    sequence = event.get("sequence")
    event_key(logical, sequence)
    predecessor = event.get("predecessor_sha256")
    if sequence == 0:
        if predecessor is not None:
            raise JournalError("SEQUENCE_ZERO_PREDECESSOR_MUST_BE_NULL")
    elif not _hex64(predecessor):
        raise JournalError("PREDECESSOR_SHA256_INVALID")
    if event.get("kind") not in ALLOWED_KINDS:
        raise JournalError("EVENT_KIND_INVALID")
    payload = event.get("payload")
    if not isinstance(payload, dict):
        raise JournalError("PAYLOAD_OBJECT_REQUIRED")
    _reject_secrets(payload)
    if event.get("payload_sha256") != _sha256(payload):
        raise JournalError("PAYLOAD_SHA256_MISMATCH")
    core = {
        "schema": event["schema"],
        "logical_attempt_id": logical,
        "sequence": sequence,
        "predecessor_sha256": predecessor,
        "kind": event["kind"],
        "payload_sha256": event["payload_sha256"],
        "payload": payload,
    }
    if event.get("event_sha256") != _sha256(core):
        raise JournalError("EVENT_SHA256_MISMATCH")
    if len(_canon(event)) > MAX_EVENT_BYTES:
        raise JournalError("EVENT_TOO_LARGE")
    return event


def _exact_same(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return _canon(left) == _canon(right)


def append_once(store: AtomicStore, event: dict[str, Any]) -> dict[str, Any]:
    event = validate_event(event)
    key = event_key(event["logical_attempt_id"], event["sequence"])
    try:
        created = store.create(key, event)
    except Exception as create_exc:
        try:
            existing = store.read(key)
        except Exception as read_exc:
            raise JournalError("APPEND_OUTCOME_UNCONFIRMED") from read_exc
        if existing is None:
            raise JournalError("APPEND_NOT_PRESENT_AFTER_CREATE_ERROR") from create_exc
        existing = validate_event(existing)
        if not _exact_same(existing, event):
            raise JournalError("JOURNAL_FORK_REJECTED_AFTER_CREATE_ERROR")
        return {
            "status": "COMMITTED_RECONCILED_AFTER_CREATE_ERROR",
            "key": key,
            "event_sha256": event["event_sha256"],
        }

    if created is False:
        try:
            existing = store.read(key)
        except Exception as exc:
            raise JournalError("EXISTING_EVENT_READ_UNCONFIRMED") from exc
        if existing is None:
            raise JournalError("CREATE_FALSE_BUT_EVENT_MISSING")
        existing = validate_event(existing)
        if not _exact_same(existing, event):
            raise JournalError("JOURNAL_FORK_REJECTED")
        return {
            "status": "COMMITTED_IDEMPOTENT",
            "key": key,
            "event_sha256": event["event_sha256"],
        }

    try:
        persisted = store.read(key)
    except Exception as exc:
        raise JournalError("POSTWRITE_READ_UNCONFIRMED") from exc
    if persisted is None:
        raise JournalError("POSTWRITE_EVENT_MISSING")
    persisted = validate_event(persisted)
    if not _exact_same(persisted, event):
        raise JournalError("POSTWRITE_EVENT_MISMATCH")
    return {
        "status": "COMMITTED",
        "key": key,
        "event_sha256": event["event_sha256"],
    }


def recover_prefix(
    store: AtomicStore,
    logical_attempt_id: str,
    *,
    limit: int = MAX_SEQUENCE + 1,
) -> list[dict[str, Any]]:
    if not _hex64(logical_attempt_id):
        raise JournalError("LOGICAL_ATTEMPT_ID_INVALID")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= MAX_SEQUENCE + 1:
        raise JournalError("RECOVERY_LIMIT_INVALID")

    out: list[dict[str, Any]] = []
    previous: str | None = None
    for sequence in range(limit):
        try:
            event = store.read(event_key(logical_attempt_id, sequence))
        except Exception as exc:
            raise JournalError("RECOVERY_READ_UNCONFIRMED:" + str(sequence)) from exc
        if event is None:
            break
        event = validate_event(event)
        if event["logical_attempt_id"] != logical_attempt_id:
            raise JournalError("RECOVERY_LOGICAL_ATTEMPT_MISMATCH")
        if event["sequence"] != sequence:
            raise JournalError("RECOVERY_SEQUENCE_MISMATCH")
        if event["predecessor_sha256"] != previous:
            raise JournalError("RECOVERY_CHAIN_MISMATCH:" + str(sequence))
        out.append(event)
        previous = event["event_sha256"]
    return out


def next_event(
    prefix: list[dict[str, Any]],
    *,
    logical_attempt_id: str,
    kind: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    if prefix:
        last = validate_event(prefix[-1])
        if last["logical_attempt_id"] != logical_attempt_id:
            raise JournalError("PREFIX_LOGICAL_ATTEMPT_MISMATCH")
        sequence = last["sequence"] + 1
        predecessor = last["event_sha256"]
    else:
        sequence = 0
        predecessor = None
    return make_event(
        logical_attempt_id=logical_attempt_id,
        sequence=sequence,
        predecessor_sha256=predecessor,
        kind=kind,
        payload=payload,
    )
