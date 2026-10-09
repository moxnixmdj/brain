#!/usr/bin/env python3
"""Credential-free atomic file bridge for the terminal causal journal.

The agent writes content-addressed request files and waits for exact ACK files.
A trusted parent, which separately owns the durable store, processes requests.
This module never handles repository credentials or network transport.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from execution_guard import terminal_causal_journal_v2 as journal

REQUEST_SCHEMA = "PROJECT_BRAIN_TERMINAL_CAUSAL_JOURNAL_REQUEST_V1"
ACK_SCHEMA = "PROJECT_BRAIN_TERMINAL_CAUSAL_JOURNAL_ACK_V1"
DEFAULT_TIMEOUT_S = 30.0
DEFAULT_POLL_S = 0.05


class JournalFileBridgeError(RuntimeError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    raw = _canon(value) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp." + str(os.getpid()))
    with open(tmp, "wb") as fh:
        fh.write(raw)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise JournalFileBridgeError("JSON_READ_FAILED:" + path.name) from exc
    if not isinstance(value, dict):
        raise JournalFileBridgeError("JSON_OBJECT_REQUIRED:" + path.name)
    return value


def _request_id(event: dict[str, Any]) -> str:
    event = journal.validate_event(event)
    material = {
        "logical_attempt_id": event["logical_attempt_id"],
        "sequence": event["sequence"],
        "event_sha256": event["event_sha256"],
    }
    return hashlib.sha256(_canon(material)).hexdigest()


def request_paths(root: str | Path, event: dict[str, Any]) -> tuple[Path, Path]:
    root = Path(root).resolve()
    rid = _request_id(event)
    return root / ("request-" + rid + ".json"), root / ("ack-" + rid + ".json")


def publish_request(root: str | Path, event: dict[str, Any]) -> tuple[Path, Path]:
    event = journal.validate_event(event)
    request_path, ack_path = request_paths(root, event)
    request = {
        "schema": REQUEST_SCHEMA,
        "event": event,
        "event_sha256": event["event_sha256"],
    }
    if request_path.exists():
        existing = _read_json(request_path)
        if _canon(existing) != _canon(request):
            raise JournalFileBridgeError("REQUEST_ID_COLLISION")
    else:
        _atomic_write(request_path, request)
    return request_path, ack_path


def process_request(store: journal.AtomicStore, request_path: str | Path) -> dict[str, Any]:
    request_path = Path(request_path).resolve()
    request = _read_json(request_path)
    if request.get("schema") != REQUEST_SCHEMA:
        raise JournalFileBridgeError("REQUEST_SCHEMA_INVALID")
    event = journal.validate_event(request.get("event"))
    if request.get("event_sha256") != event["event_sha256"]:
        raise JournalFileBridgeError("REQUEST_EVENT_SHA_MISMATCH")
    result = journal.append_once(store, event)
    ack = {
        "schema": ACK_SCHEMA,
        "status": "COMMITTED",
        "event_sha256": event["event_sha256"],
        "append_status": result["status"],
    }
    _request_path, ack_path = request_paths(request_path.parent, event)
    if _request_path != request_path:
        raise JournalFileBridgeError("REQUEST_PATH_IDENTITY_MISMATCH")
    if ack_path.exists():
        existing = _read_json(ack_path)
        if _canon(existing) != _canon(ack):
            raise JournalFileBridgeError("ACK_ALREADY_EXISTS_WITH_DIFFERENT_BYTES")
    else:
        _atomic_write(ack_path, ack)
    return ack


def process_pending_once(store: journal.AtomicStore, root: str | Path) -> int:
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    count = 0
    for request_path in sorted(root.glob("request-*.json")):
        request = _read_json(request_path)
        event = journal.validate_event(request.get("event"))
        _req, ack_path = request_paths(root, event)
        if ack_path.exists():
            continue
        process_request(store, request_path)
        count += 1
    return count


def wait_for_ack(
    root: str | Path,
    event: dict[str, Any],
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    poll_s: float = DEFAULT_POLL_S,
) -> dict[str, Any]:
    event = journal.validate_event(event)
    _request_path, ack_path = request_paths(root, event)
    if timeout_s <= 0 or poll_s <= 0:
        raise JournalFileBridgeError("WAIT_TIMING_INVALID")
    deadline = time.monotonic() + timeout_s
    while True:
        if ack_path.is_file():
            ack = _read_json(ack_path)
            if ack.get("schema") != ACK_SCHEMA:
                raise JournalFileBridgeError("ACK_SCHEMA_INVALID")
            if ack.get("status") != "COMMITTED":
                raise JournalFileBridgeError("ACK_STATUS_INVALID")
            if ack.get("event_sha256") != event["event_sha256"]:
                raise JournalFileBridgeError("ACK_EVENT_SHA_MISMATCH")
            return ack
        if time.monotonic() >= deadline:
            raise JournalFileBridgeError("ACK_TIMEOUT")
        time.sleep(poll_s)


class JournalSession:
    def __init__(self, root: str | Path, logical_attempt_id: str):
        self.root = Path(root).resolve()
        self.logical_attempt_id = logical_attempt_id
        self.prefix: list[dict[str, Any]] = []

    def append(
        self,
        kind: str,
        payload: dict[str, Any],
        *,
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ) -> dict[str, Any]:
        event = journal.next_event(
            self.prefix,
            logical_attempt_id=self.logical_attempt_id,
            kind=kind,
            payload=payload,
        )
        publish_request(self.root, event)
        wait_for_ack(self.root, event, timeout_s=timeout_s)
        self.prefix.append(event)
        return event
