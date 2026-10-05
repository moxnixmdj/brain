"""Typed parent finalizer for declared artifact bytes.

The finalizer is deliberately dormant under the current production semantic
registry: it calls the canonical final effect authorizer before any mutation,
and that registry currently grants no artifact schema. This module therefore
implements the mechanical finalization carrier without creating semantic
authority.

A future semantic policy may authorize an exact FINAL_OUTPUT request, but the
same plan/payload/prestate/path checks and post-commit readback remain mandatory.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from canonical.runtime.effect_broker_contract_v1 import make_request
from canonical.runtime.effect_broker_final_authorizer_v1 import authorize_effect

PLAN_SCHEMA = "PROJECT_BRAIN_DECLARED_ARTIFACT_FINALIZE_PLAN_V1"
RECEIPT_SCHEMA = "PROJECT_BRAIN_DECLARED_ARTIFACT_FINALIZE_RECEIPT_V1"
DESCRIPTOR_SCHEMA = "PROJECT_BRAIN_DECLARED_ARTIFACT_DESCRIPTOR_V1"

ARTIFACT_ROOT = Path("canonical/astra_runtime/artifacts")
PATH_RE = re.compile(
    r"^canonical/astra_runtime/artifacts/[A-Za-z0-9][A-Za-z0-9_.-]{0,239}$"
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_ARTIFACT_BYTES = 536_870_912


class ArtifactFinalizeDenied(RuntimeError):
    pass


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _token(value: Any, label: str, max_len: int) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > max_len
        or "\x00" in value
    ):
        raise ArtifactFinalizeDenied(label + "_INVALID")
    return value.strip()


def _prestate(value: Any) -> str:
    if value == "ABSENT":
        return value
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise ArtifactFinalizeDenied("EXPECTED_PRESTATE_INVALID")
    return value


def _descriptor(
    *,
    destination_path: str,
    payload: bytes,
    expected_pre_sha256: str,
    content_type: str,
    producer_sha256: str,
    toolchain_sha256: str,
) -> dict[str, Any]:
    path = _token(destination_path, "DESTINATION_PATH", 320)
    if PATH_RE.fullmatch(path) is None:
        raise ArtifactFinalizeDenied("DESTINATION_PATH_NOT_ALLOWED")
    if not isinstance(payload, bytes) or not payload or len(payload) > MAX_ARTIFACT_BYTES:
        raise ArtifactFinalizeDenied("ARTIFACT_PAYLOAD_INVALID")
    ctype = _token(content_type, "CONTENT_TYPE", 256)
    producer = _token(producer_sha256, "PRODUCER_SHA256", 64)
    toolchain = _token(toolchain_sha256, "TOOLCHAIN_SHA256", 64)
    if SHA256_RE.fullmatch(producer) is None:
        raise ArtifactFinalizeDenied("PRODUCER_SHA256_INVALID")
    if SHA256_RE.fullmatch(toolchain) is None:
        raise ArtifactFinalizeDenied("TOOLCHAIN_SHA256_INVALID")
    return {
        "schema": DESCRIPTOR_SCHEMA,
        "destination_path": path,
        "artifact_sha256": _sha(payload),
        "artifact_bytes": len(payload),
        "expected_pre_sha256": _prestate(expected_pre_sha256),
        "content_type": ctype,
        "producer_sha256": producer,
        "toolchain_sha256": toolchain,
    }


def build_plan(
    *,
    mission_id: str,
    capsule_head_sha256: str,
    action_ref: str,
    destination_path: str,
    payload: bytes,
    expected_pre_sha256: str,
    content_type: str,
    producer_sha256: str,
    toolchain_sha256: str,
) -> dict[str, Any]:
    mission = _token(mission_id, "MISSION_ID", 256)
    head = _token(capsule_head_sha256, "CAPSULE_HEAD_SHA256", 64)
    if SHA256_RE.fullmatch(head) is None:
        raise ArtifactFinalizeDenied("CAPSULE_HEAD_SHA256_INVALID")
    action = _token(action_ref, "ACTION_REF", 512)
    descriptor = _descriptor(
        destination_path=destination_path,
        payload=payload,
        expected_pre_sha256=expected_pre_sha256,
        content_type=content_type,
        producer_sha256=producer_sha256,
        toolchain_sha256=toolchain_sha256,
    )
    core = {
        "schema": PLAN_SCHEMA,
        "mission_id": mission,
        "capsule_head_sha256": head,
        "action_ref": action,
        "descriptor": descriptor,
    }
    return {**core, "plan_sha256": _sha(_canon(core))}


def _validate_plan(plan: Mapping[str, Any], payload: bytes) -> dict[str, Any]:
    if not isinstance(plan, Mapping) or set(plan) != {
        "schema", "mission_id", "capsule_head_sha256", "action_ref",
        "descriptor", "plan_sha256",
    }:
        raise ArtifactFinalizeDenied("PLAN_FIELDS_INVALID")
    if plan.get("schema") != PLAN_SCHEMA:
        raise ArtifactFinalizeDenied("PLAN_SCHEMA_INVALID")
    desc = plan.get("descriptor")
    if not isinstance(desc, Mapping) or set(desc) != {
        "schema", "destination_path", "artifact_sha256", "artifact_bytes",
        "expected_pre_sha256", "content_type", "producer_sha256", "toolchain_sha256",
    }:
        raise ArtifactFinalizeDenied("DESCRIPTOR_FIELDS_INVALID")
    rebuilt = build_plan(
        mission_id=plan.get("mission_id"),
        capsule_head_sha256=plan.get("capsule_head_sha256"),
        action_ref=plan.get("action_ref"),
        destination_path=desc.get("destination_path"),
        payload=payload,
        expected_pre_sha256=desc.get("expected_pre_sha256"),
        content_type=desc.get("content_type"),
        producer_sha256=desc.get("producer_sha256"),
        toolchain_sha256=desc.get("toolchain_sha256"),
    )
    if dict(plan) != rebuilt:
        raise ArtifactFinalizeDenied("PLAN_OR_PAYLOAD_MISMATCH")
    return rebuilt


def effect_request(plan: Mapping[str, Any], payload: bytes) -> dict[str, Any]:
    checked = _validate_plan(plan, payload)
    desc = checked["descriptor"]
    return make_request(
        mission_id=checked["mission_id"],
        capsule_head_sha256=checked["capsule_head_sha256"],
        action_ref=checked["action_ref"],
        effect_kind="FINAL_OUTPUT",
        resource="artifact:" + desc["destination_path"],
        operation="replace",
        payload=desc,
    )


def _target(repo_root: Path, destination_path: str) -> Path:
    root = repo_root.resolve(strict=True)
    allowed = root / ARTIFACT_ROOT
    if allowed.is_symlink():
        raise ArtifactFinalizeDenied("ARTIFACT_ROOT_SYMLINK_DENIED")
    allowed = allowed.resolve(strict=True)
    if not allowed.is_dir() or (allowed != root and root not in allowed.parents):
        raise ArtifactFinalizeDenied("ARTIFACT_ROOT_INVALID")
    target = root.joinpath(*Path(destination_path).parts)
    if target.parent != allowed:
        raise ArtifactFinalizeDenied("DESTINATION_PATH_NOT_ALLOWED")
    if target.is_symlink():
        raise ArtifactFinalizeDenied("TARGET_SYMLINK_DENIED")
    if target.exists() and not target.is_file():
        raise ArtifactFinalizeDenied("TARGET_NOT_REGULAR_FILE")
    return target


def _current(target: Path) -> tuple[str, bytes]:
    if not target.exists():
        return "ABSENT", b""
    data = target.read_bytes()
    if len(data) > MAX_ARTIFACT_BYTES:
        raise ArtifactFinalizeDenied("PRESTATE_TOO_LARGE")
    return _sha(data), data


def _atomic_replace(target: Path, payload: bytes) -> None:
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=target.parent,
            prefix="." + target.name + ".project-brain-artifact.",
            suffix=".tmp",
            delete=False,
        ) as fh:
            temp_name = fh.name
            fh.write(payload)
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
    grant: Mapping[str, Any],
) -> dict[str, Any]:
    checked = _validate_plan(plan, payload)
    desc = checked["descriptor"]
    target = _target(Path(repo_root), desc["destination_path"])
    lock = target.parent / ("." + target.name + ".project-brain-artifact.lock")
    fd = None
    try:
        try:
            fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            raise ArtifactFinalizeDenied("FINALIZE_LOCK_BUSY") from exc

        pre_sha, _ = _current(target)
        if pre_sha != desc["expected_pre_sha256"]:
            raise ArtifactFinalizeDenied("PRESTATE_MISMATCH")

        request = effect_request(checked, payload)
        verdict = authorize_effect(request, grant, repo_root=repo_root)
        if (
            not isinstance(verdict, Mapping)
            or verdict.get("allowed") is not True
            or verdict.get("status") != "ALLOW_FINAL_AUTHORIZATION"
            or verdict.get("request_sha256") != request["request_sha256"]
            or verdict.get("effect_kind") != "FINAL_OUTPUT"
            or verdict.get("resource") != request["resource"]
            or verdict.get("operation") != "replace"
            or verdict.get("payload_sha256") != request["payload_sha256"]
        ):
            raise ArtifactFinalizeDenied(
                "FINAL_AUTHORIZATION_DENIED:"
                + str(
                    verdict.get("failed_stage")
                    or verdict.get("reason")
                    or verdict.get("status")
                    if isinstance(verdict, Mapping)
                    else "INVALID_VERDICT"
                )
            )

        _atomic_replace(target, payload)
        observed = target.read_bytes()
        if observed != payload:
            raise ArtifactFinalizeDenied("POSTSTATE_BYTE_MISMATCH")
        return {
            "schema": RECEIPT_SCHEMA,
            "status": "COMMITTED",
            "plan_sha256": checked["plan_sha256"],
            "request_sha256": request["request_sha256"],
            "destination_path": desc["destination_path"],
            "pre_sha256": pre_sha,
            "post_sha256": _sha(observed),
            "post_bytes": len(observed),
            "producer_sha256": desc["producer_sha256"],
            "toolchain_sha256": desc["toolchain_sha256"],
            "atomic_replace": True,
            "exact_readback": True,
            "acceptance_credit_delta": 0,
        }
    finally:
        if fd is not None:
            os.close(fd)
        try:
            os.unlink(lock)
        except FileNotFoundError:
            pass
