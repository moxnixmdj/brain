"""Typed durable-write boundary for ASTRA runtime state and evidence.

This module grants no arbitrary repository-write authority. It supports only:
- replace of one JSON object directly under canonical/astra_runtime/state;
- replace of one JSON object directly under canonical/astra_runtime/evidence;
- compare-and-append of one JSON object line under the evidence directory.

Every commit binds exact payload bytes, exact expected pre-state, destination
class/path, and a content-addressed plan. Commits use same-directory atomic
replace and fail closed on path, class, payload, pre-state, or symlink drift.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Mapping

PLAN_SCHEMA = "PROJECT_BRAIN_TYPED_DURABLE_ADMIN_WRITE_PLAN_V1"
RECEIPT_SCHEMA = "PROJECT_BRAIN_TYPED_DURABLE_ADMIN_WRITE_RECEIPT_V1"
MAX_PAYLOAD = 8_000_000
MAX_POST = 64_000_000
SHA256 = re.compile(r"^[0-9a-f]{64}$")

RULES = {
    "ASTRA_STATE_JSON": (
        "REPLACE",
        re.compile(r"^canonical/astra_runtime/state/[A-Za-z0-9_.-]{1,240}[.]json$"),
        Path("canonical/astra_runtime/state"),
    ),
    "ASTRA_EVIDENCE_JSON": (
        "REPLACE",
        re.compile(r"^canonical/astra_runtime/evidence/[A-Za-z0-9_.-]{1,240}[.]json$"),
        Path("canonical/astra_runtime/evidence"),
    ),
    "ASTRA_EVIDENCE_JSONL": (
        "APPEND_JSONL",
        re.compile(r"^canonical/astra_runtime/evidence/[A-Za-z0-9_.-]{1,239}[.]jsonl$"),
        Path("canonical/astra_runtime/evidence"),
    ),
}


class DurableWriteDenied(RuntimeError):
    pass


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canon(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _check_payload(operation: str, payload: bytes) -> None:
    label = "JSONL_PAYLOAD_INVALID" if operation == "APPEND_JSONL" else "JSON_PAYLOAD_INVALID"
    if not isinstance(payload, bytes) or not payload or len(payload) > MAX_PAYLOAD:
        raise DurableWriteDenied(label)
    if not payload.endswith(b"\n"):
        raise DurableWriteDenied(label)
    if operation == "APPEND_JSONL" and payload.count(b"\n") != 1:
        raise DurableWriteDenied(label)
    try:
        value = json.loads(payload.decode("utf-8"))
    except Exception as exc:
        raise DurableWriteDenied(label) from exc
    if not isinstance(value, dict):
        raise DurableWriteDenied(label)


def _check_pre(value: Any) -> str:
    if value == "ABSENT":
        return value
    if not isinstance(value, str) or SHA256.fullmatch(value) is None:
        raise DurableWriteDenied("EXPECTED_PRESTATE_INVALID")
    return value


def _check_core(core: Mapping[str, Any], payload: bytes) -> dict[str, Any]:
    keys = {
        "schema", "operation", "destination_class", "path",
        "payload_sha256", "payload_bytes", "expected_pre_sha256",
    }
    if not isinstance(core, Mapping) or set(core) != keys:
        raise DurableWriteDenied("PLAN_FIELDS_INVALID")
    if core.get("schema") != PLAN_SCHEMA:
        raise DurableWriteDenied("PLAN_SCHEMA_INVALID")
    cls = str(core.get("destination_class") or "")
    rule = RULES.get(cls)
    if rule is None or core.get("operation") != rule[0]:
        raise DurableWriteDenied("OPERATION_CLASS_MISMATCH")
    path = core.get("path")
    if (
        not isinstance(path, str)
        or not path
        or chr(0) in path
        or "\\" in path
        or rule[1].fullmatch(path) is None
    ):
        raise DurableWriteDenied("PATH_NOT_ALLOWED")
    _check_payload(rule[0], payload)
    if core.get("payload_bytes") != len(payload):
        raise DurableWriteDenied("PAYLOAD_LENGTH_MISMATCH")
    if core.get("payload_sha256") != _sha(payload):
        raise DurableWriteDenied("PAYLOAD_HASH_MISMATCH")
    return {
        "schema": PLAN_SCHEMA,
        "operation": rule[0],
        "destination_class": cls,
        "path": path,
        "payload_sha256": _sha(payload),
        "payload_bytes": len(payload),
        "expected_pre_sha256": _check_pre(core.get("expected_pre_sha256")),
    }


def build_plan(
    *,
    operation: str,
    destination_class: str,
    path: str,
    payload: bytes,
    expected_pre_sha256: str,
) -> dict[str, Any]:
    core = {
        "schema": PLAN_SCHEMA,
        "operation": operation,
        "destination_class": destination_class,
        "path": path,
        "payload_sha256": _sha(payload),
        "payload_bytes": len(payload),
        "expected_pre_sha256": expected_pre_sha256,
    }
    core = _check_core(core, payload)
    return {**core, "plan_sha256": _sha(_canon(core))}


def _target(repo_root: Path, core: Mapping[str, Any]) -> Path:
    root = repo_root.resolve(strict=True)
    rule = RULES[core["destination_class"]]
    allowed = root / rule[2]
    if allowed.is_symlink():
        raise DurableWriteDenied("SYMLINK_PARENT_DENIED")
    allowed = allowed.resolve(strict=True)
    if not allowed.is_dir() or (allowed != root and root not in allowed.parents):
        raise DurableWriteDenied("PATH_NOT_ALLOWED")
    target = root.joinpath(*Path(core["path"]).parts)
    if target.parent != allowed:
        raise DurableWriteDenied("PATH_NOT_ALLOWED")
    if target.is_symlink():
        raise DurableWriteDenied("SYMLINK_TARGET_DENIED")
    if target.exists() and not target.is_file():
        raise DurableWriteDenied("TARGET_NOT_REGULAR_FILE")
    return target


def _current(target: Path) -> tuple[str, bytes]:
    if not target.exists():
        return "ABSENT", b""
    data = target.read_bytes()
    if len(data) > MAX_POST:
        raise DurableWriteDenied("PRESTATE_TOO_LARGE")
    return _sha(data), data


def _check_jsonl(data: bytes) -> None:
    if not data:
        return
    if not data.endswith(b"\n"):
        raise DurableWriteDenied("EXISTING_JSONL_INVALID")
    for line in data.splitlines():
        try:
            value = json.loads(line.decode("utf-8"))
        except Exception as exc:
            raise DurableWriteDenied("EXISTING_JSONL_INVALID") from exc
        if not isinstance(value, dict):
            raise DurableWriteDenied("EXISTING_JSONL_INVALID")


def _replace(target: Path, data: bytes) -> None:
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=target.parent,
            prefix="." + target.name + ".project-brain.", suffix=".tmp", delete=False,
        ) as fh:
            temp_name = fh.name
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp_name, target)
        temp_name = None
        try:
            fd = os.open(target.parent, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        except OSError:
            pass
    finally:
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass


def commit(
    repo_root: str | os.PathLike[str],
    plan: Mapping[str, Any],
    payload: bytes,
) -> dict[str, Any]:
    if not isinstance(plan, Mapping) or set(plan) != {
        "schema", "operation", "destination_class", "path",
        "payload_sha256", "payload_bytes", "expected_pre_sha256", "plan_sha256",
    }:
        raise DurableWriteDenied("PLAN_FIELDS_INVALID")
    core = {k: plan[k] for k in plan if k != "plan_sha256"}
    core = _check_core(core, payload)
    if plan.get("plan_sha256") != _sha(_canon(core)):
        raise DurableWriteDenied("PLAN_HASH_MISMATCH")

    target = _target(Path(repo_root), core)
    lock = target.parent / ("." + target.name + ".project-brain.lock")
    fd = None
    try:
        try:
            fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            raise DurableWriteDenied("WRITE_LOCK_BUSY") from exc

        pre_sha, old = _current(target)
        if pre_sha != core["expected_pre_sha256"]:
            raise DurableWriteDenied("PRESTATE_MISMATCH")
        if core["operation"] == "APPEND_JSONL":
            _check_jsonl(old)
            post = old + payload
            appended = True
        else:
            post = payload
            appended = False
        if len(post) > MAX_POST:
            raise DurableWriteDenied("POSTSTATE_TOO_LARGE")

        _replace(target, post)
        observed = target.read_bytes()
        if observed != post:
            raise DurableWriteDenied("POSTSTATE_BYTE_MISMATCH")
        return {
            "schema": RECEIPT_SCHEMA,
            "status": "COMMITTED",
            "plan_sha256": plan["plan_sha256"],
            "operation": core["operation"],
            "destination_class": core["destination_class"],
            "path": core["path"],
            "pre_sha256": pre_sha,
            "payload_sha256": core["payload_sha256"],
            "post_sha256": _sha(observed),
            "post_bytes": len(observed),
            "atomic_replace": True,
            "compare_and_append": appended,
            "acceptance_credit_delta": 0,
        }
    finally:
        if fd is not None:
            os.close(fd)
        try:
            os.unlink(lock)
        except FileNotFoundError:
            pass
