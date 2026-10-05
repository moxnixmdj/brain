"""Fail-closed typed parent finalizer for declared PDF artifacts."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

PLAN_SCHEMA = "PROJECT_BRAIN_TYPED_PDF_ARTIFACT_FINALIZER_PLAN_V1"
RECEIPT_SCHEMA = "PROJECT_BRAIN_TYPED_PDF_ARTIFACT_FINALIZER_RECEIPT_V1"
ARTIFACT_CLASS = "DECLARED_PDF_ARTIFACT"
PRODUCER_ID = "document.convert.markdown_pdf.pandoc_weasyprint"
MAX_ARTIFACT_BYTES = 128_000_000
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9._ -]{1,240}$")
PROTECTED_PREFIXES = (
    PurePosixPath(".git"),
    PurePosixPath(".github"),
    PurePosixPath("canonical/runtime"),
    PurePosixPath("canonical/governance"),
    PurePosixPath("canonical/tests"),
    PurePosixPath("canonical/astra_runtime/state"),
    PurePosixPath("canonical/astra_runtime/evidence"),
    PurePosixPath("canonical/astra_runtime/missions"),
)


class ArtifactFinalizeDenied(RuntimeError):
    pass


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canon(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _sha_field(value: Any, label: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise ArtifactFinalizeDenied(label + "_INVALID")
    return value


def _relative_pdf_path(value: Any) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise ArtifactFinalizeDenied("OUTPUT_PATH_INVALID")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.as_posix() != value
        or path.suffix.lower() != ".pdf"
        or any(SAFE_NAME_RE.fullmatch(part) is None for part in path.parts)
    ):
        raise ArtifactFinalizeDenied("OUTPUT_PATH_INVALID")
    for prefix in PROTECTED_PREFIXES:
        if path == prefix or prefix in path.parents:
            raise ArtifactFinalizeDenied("OUTPUT_PATH_PROTECTED")
    return value


def _expected_pre(value: Any) -> str:
    if value == "ABSENT":
        return value
    return _sha_field(value, "EXPECTED_PRESTATE_SHA256")


def _check_pdf(payload: bytes) -> None:
    if (
        not isinstance(payload, bytes)
        or not payload
        or len(payload) > MAX_ARTIFACT_BYTES
    ):
        raise ArtifactFinalizeDenied("PDF_PAYLOAD_INVALID")
    if not payload.startswith(b"%PDF-"):
        raise ArtifactFinalizeDenied("PDF_MAGIC_MISMATCH")
    if b"%%EOF" not in payload[-8192:]:
        raise ArtifactFinalizeDenied("PDF_EOF_MISSING")


def build_plan(
    *,
    output_path: str,
    payload: bytes,
    expected_pre_sha256: str,
    input_sha256: str,
    toolchain_binding_sha256: str,
) -> dict[str, Any]:
    _check_pdf(payload)
    core = {
        "schema": PLAN_SCHEMA,
        "artifact_class": ARTIFACT_CLASS,
        "producer_id": PRODUCER_ID,
        "output_path": _relative_pdf_path(output_path),
        "payload_sha256": _sha(payload),
        "payload_bytes": len(payload),
        "expected_pre_sha256": _expected_pre(expected_pre_sha256),
        "input_sha256": _sha_field(input_sha256, "INPUT_SHA256"),
        "toolchain_binding_sha256": _sha_field(
            toolchain_binding_sha256, "TOOLCHAIN_BINDING_SHA256"
        ),
    }
    return {**core, "plan_sha256": _sha(_canon(core))}


def _validate_plan(plan: Mapping[str, Any], payload: bytes) -> dict[str, Any]:
    keys = {
        "schema",
        "artifact_class",
        "producer_id",
        "output_path",
        "payload_sha256",
        "payload_bytes",
        "expected_pre_sha256",
        "input_sha256",
        "toolchain_binding_sha256",
        "plan_sha256",
    }
    if not isinstance(plan, Mapping) or set(plan) != keys:
        raise ArtifactFinalizeDenied("PLAN_FIELDS_INVALID")
    if plan.get("schema") != PLAN_SCHEMA:
        raise ArtifactFinalizeDenied("PLAN_SCHEMA_INVALID")
    if plan.get("artifact_class") != ARTIFACT_CLASS:
        raise ArtifactFinalizeDenied("ARTIFACT_CLASS_INVALID")
    if plan.get("producer_id") != PRODUCER_ID:
        raise ArtifactFinalizeDenied("PRODUCER_ID_INVALID")
    _check_pdf(payload)
    core = {
        "schema": PLAN_SCHEMA,
        "artifact_class": ARTIFACT_CLASS,
        "producer_id": PRODUCER_ID,
        "output_path": _relative_pdf_path(plan.get("output_path")),
        "payload_sha256": _sha(payload),
        "payload_bytes": len(payload),
        "expected_pre_sha256": _expected_pre(plan.get("expected_pre_sha256")),
        "input_sha256": _sha_field(plan.get("input_sha256"), "INPUT_SHA256"),
        "toolchain_binding_sha256": _sha_field(
            plan.get("toolchain_binding_sha256"), "TOOLCHAIN_BINDING_SHA256"
        ),
    }
    if plan.get("payload_sha256") != core["payload_sha256"]:
        raise ArtifactFinalizeDenied("PAYLOAD_HASH_MISMATCH")
    if plan.get("payload_bytes") != core["payload_bytes"]:
        raise ArtifactFinalizeDenied("PAYLOAD_LENGTH_MISMATCH")
    if plan.get("plan_sha256") != _sha(_canon(core)):
        raise ArtifactFinalizeDenied("PLAN_HASH_MISMATCH")
    return core


def _dir_flags() -> int:
    return os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)


def _open_parent(
    repo_root: Path,
    relative: str,
    *,
    create_missing: bool,
) -> tuple[int | None, str]:
    root = repo_root.resolve(strict=True)
    parts = PurePosixPath(relative).parts
    target_name = parts[-1]
    fd = os.open(root, _dir_flags())
    try:
        for part in parts[:-1]:
            try:
                next_fd = os.open(part, _dir_flags(), dir_fd=fd)
            except FileNotFoundError:
                if not create_missing:
                    os.close(fd)
                    return None, target_name
                os.mkdir(part, mode=0o755, dir_fd=fd)
                next_fd = os.open(part, _dir_flags(), dir_fd=fd)
            except OSError as exc:
                raise ArtifactFinalizeDenied("PARENT_COMPONENT_DENIED") from exc
            os.close(fd)
            fd = next_fd
        return fd, target_name
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        raise


def _read_current(parent_fd: int, target_name: str) -> tuple[str, bytes]:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(target_name, flags, dir_fd=parent_fd)
    except FileNotFoundError:
        return "ABSENT", b""
    except OSError as exc:
        raise ArtifactFinalizeDenied("TARGET_OPEN_DENIED") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ArtifactFinalizeDenied("TARGET_NOT_REGULAR_FILE")
        if info.st_size > MAX_ARTIFACT_BYTES:
            raise ArtifactFinalizeDenied("PRESTATE_TOO_LARGE")
        chunks: list[bytes] = []
        remaining = MAX_ARTIFACT_BYTES + 1
        while remaining > 0:
            chunk = os.read(fd, min(1_048_576, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > MAX_ARTIFACT_BYTES:
            raise ArtifactFinalizeDenied("PRESTATE_TOO_LARGE")
        return _sha(data), data
    finally:
        os.close(fd)


def observe_prestate(
    repo_root: str | os.PathLike[str],
    output_path: str,
) -> str:
    relative = _relative_pdf_path(output_path)
    parent_fd, target_name = _open_parent(
        Path(repo_root), relative, create_missing=False
    )
    if parent_fd is None:
        return "ABSENT"
    try:
        digest, _ = _read_current(parent_fd, target_name)
        return digest
    finally:
        os.close(parent_fd)


def _atomic_write(
    parent_fd: int,
    target_name: str,
    payload: bytes,
    plan_sha256: str,
) -> None:
    temp_name = "." + target_name + ".project-brain." + plan_sha256[:16] + ".tmp"
    lock_name = "." + target_name + ".project-brain.lock"
    lock_fd = None
    temp_fd = None
    try:
        exclusive = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_NOFOLLOW", 0)
        )
        try:
            lock_fd = os.open(lock_name, exclusive, 0o600, dir_fd=parent_fd)
        except FileExistsError as exc:
            raise ArtifactFinalizeDenied("FINALIZE_LOCK_BUSY") from exc

        try:
            temp_fd = os.open(temp_name, exclusive, 0o600, dir_fd=parent_fd)
        except FileExistsError as exc:
            raise ArtifactFinalizeDenied("STALE_TEMP_FILE_PRESENT") from exc
        view = memoryview(payload)
        written = 0
        while written < len(view):
            count = os.write(temp_fd, view[written:])
            if count <= 0:
                raise ArtifactFinalizeDenied("TEMP_WRITE_FAILED")
            written += count
        os.fsync(temp_fd)
        os.close(temp_fd)
        temp_fd = None
        os.replace(
            temp_name,
            target_name,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
        )
        os.fsync(parent_fd)
    finally:
        if temp_fd is not None:
            os.close(temp_fd)
        try:
            os.unlink(temp_name, dir_fd=parent_fd)
        except FileNotFoundError:
            pass
        if lock_fd is not None:
            os.close(lock_fd)
        try:
            os.unlink(lock_name, dir_fd=parent_fd)
        except FileNotFoundError:
            pass


def commit(
    repo_root: str | os.PathLike[str],
    plan: Mapping[str, Any],
    payload: bytes,
) -> dict[str, Any]:
    core = _validate_plan(plan, payload)
    parent_fd, target_name = _open_parent(
        Path(repo_root), core["output_path"], create_missing=True
    )
    if parent_fd is None:
        raise ArtifactFinalizeDenied("PARENT_CREATION_FAILED")
    try:
        pre_sha256, _ = _read_current(parent_fd, target_name)
        if pre_sha256 != core["expected_pre_sha256"]:
            raise ArtifactFinalizeDenied("PRESTATE_MISMATCH")
        _atomic_write(parent_fd, target_name, payload, plan["plan_sha256"])
        post_sha256, observed = _read_current(parent_fd, target_name)
        if observed != payload or post_sha256 != core["payload_sha256"]:
            raise ArtifactFinalizeDenied("POSTSTATE_MISMATCH")
        return {
            "schema": RECEIPT_SCHEMA,
            "status": "COMMITTED",
            "artifact_class": ARTIFACT_CLASS,
            "producer_id": PRODUCER_ID,
            "output_path": core["output_path"],
            "plan_sha256": plan["plan_sha256"],
            "input_sha256": core["input_sha256"],
            "toolchain_binding_sha256": core["toolchain_binding_sha256"],
            "pre_sha256": pre_sha256,
            "payload_sha256": core["payload_sha256"],
            "post_sha256": post_sha256,
            "output_bytes": len(observed),
            "atomic_replace": True,
            "acceptance_credit_delta": 0,
        }
    finally:
        os.close(parent_fd)
