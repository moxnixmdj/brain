"""Sealed field-projection consumer for zero-credit currentness reuse.

This module closes the undeclared-read hole in field-scoped currentness:
1. project only declared RFC-6901 fields from authority documents;
2. materialize that projection plus the verifier/helper bytes into one input tree;
3. verify the exact closed-world input manifest;
4. run the verifier inside the independently verified zero-ambient namespace,
   where the host repository is not mounted.

The result is evidence that unrelated authority fields were unavailable to the
consumer. It grants no execution, promotion, acceptance, ownership, capability,
fresh-reality, or terminal authority.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import pwd
import tempfile
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime.field_scoped_authority_projection_gate_v1 import (
    freeze_manifest,
    sealed_projection,
)
from canonical.runtime.honesty_closed_world_input_manifest_v1 import (
    SCHEMA as CLOSED_WORLD_MANIFEST_SCHEMA,
    scan_input_dir,
    verify_declared_manifest,
)
from canonical.runtime.zero_ambient_namespace_launcher_v1 import run_confined

SCHEMA = "PROJECT_BRAIN_SEALED_FIELD_PROJECTION_CONSUMER_V1"
RUNNER_SCHEMA = "PROJECT_BRAIN_SEALED_FIELD_PROJECTION_CHILD_RESULT_V1"
PROJECTION_FILE = "_field_projection.json"
RUNNER_FILE = "_sealed_runner.py"
HEX = set("0123456789abcdef")


class SealedFieldProjectionError(RuntimeError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _safe_relpath(value: str) -> str:
    raw = str(value or "").replace("\\", "/").strip()
    p = pathlib.PurePosixPath(raw)
    if (
        not raw
        or raw.startswith("/")
        or raw in {".", ".."}
        or ".." in p.parts
        or any(part in {"", "."} for part in p.parts)
    ):
        raise SealedFieldProjectionError("UNSAFE_INPUT_PATH:" + raw)
    return p.as_posix()


def prepare_projection_bundle(
    *,
    source_documents: Mapping[str, Mapping[str, Any]],
    field_dependencies: Mapping[str, Sequence[str]],
) -> dict[str, Any]:
    if not isinstance(source_documents, Mapping) or not source_documents:
        raise SealedFieldProjectionError("SOURCE_DOCUMENTS_REQUIRED")
    if not isinstance(field_dependencies, Mapping) or not field_dependencies:
        raise SealedFieldProjectionError("FIELD_DEPENDENCIES_REQUIRED")

    source_keys = {str(x) for x in source_documents}
    dependency_keys = {str(x) for x in field_dependencies}
    if source_keys != dependency_keys:
        raise SealedFieldProjectionError("SOURCE_DEPENDENCY_PATH_SET_MISMATCH")

    sources = []
    for raw_path in sorted(source_keys):
        path = _safe_relpath(raw_path)
        document = source_documents[raw_path]
        pointers = field_dependencies[raw_path]
        if not isinstance(document, Mapping):
            raise SealedFieldProjectionError("SOURCE_DOCUMENT_NOT_MAPPING:" + path)
        if not isinstance(pointers, Sequence) or isinstance(pointers, (str, bytes)):
            raise SealedFieldProjectionError("FIELD_POINTERS_NOT_SEQUENCE:" + path)
        pointers = [str(x) for x in pointers]
        manifest = freeze_manifest(
            document,
            pointers,
            source_path=path,
        )
        projection = sealed_projection(document, pointers)
        sources.append(
            {
                "source_path": path,
                "dependency_manifest": manifest,
                "projection": projection,
            }
        )

    core = {
        "schema": SCHEMA,
        "sources": sources,
        "source_count": len(sources),
        "authority": {
            "execution": False,
            "promotion": False,
            "acceptance": False,
            "ownership": False,
            "capability": False,
            "fresh_reality": False,
            "terminal": False,
        },
    }
    return {
        **core,
        "projection_bundle_sha256": _sha256(_canon(core)),
    }


def _runner_source(
    *,
    consumer_module: str,
    consumer_entrypoint: str,
    projection_sha256: str,
) -> str:
    module_json = json.dumps(consumer_module)
    entry_json = json.dumps(consumer_entrypoint)
    digest_json = json.dumps(projection_sha256)
    schema_json = json.dumps(RUNNER_SCHEMA)
    return f'''from __future__ import annotations
import hashlib, importlib.util, json, os, pathlib, sys

MODULE={module_json}
ENTRYPOINT={entry_json}
EXPECTED_PROJECTION_SHA256={digest_json}
RESULT_SCHEMA={schema_json}

def emit(value):
    raw=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    fd=int(os.environ["PROJECT_BRAIN_BROKER_FD"])
    offset=0
    while offset < len(raw):
        offset += os.write(fd,raw[offset:])

projection_path=pathlib.Path("/input/{PROJECTION_FILE}")
raw=projection_path.read_bytes()
if hashlib.sha256(raw).hexdigest()!=EXPECTED_PROJECTION_SHA256:
    raise SystemExit(41)
projection=json.loads(raw.decode("utf-8"))
sys.path.insert(0,"/input")
module_path=pathlib.Path("/input")/MODULE
spec=importlib.util.spec_from_file_location("_sealed_consumer",module_path)
if spec is None or spec.loader is None:
    raise SystemExit(42)
consumer=importlib.util.module_from_spec(spec)
spec.loader.exec_module(consumer)
fn=getattr(consumer,ENTRYPOINT,None)
if not callable(fn):
    raise SystemExit(43)
result=fn(projection)
if not isinstance(result,dict):
    raise SystemExit(44)
emit({{
    "schema":RESULT_SCHEMA,
    "projection_bundle_sha256":projection["projection_bundle_sha256"],
    "consumer_result":result,
}})
'''


def _select_identity() -> tuple[int, int]:
    if os.geteuid() != 0:
        return os.geteuid(), os.getegid()
    try:
        account = pwd.getpwnam("nobody")
        uid, gid = int(account.pw_uid), int(account.pw_gid)
    except KeyError:
        uid = gid = 65534
    if uid <= 0 or gid <= 0:
        raise SealedFieldProjectionError("NONROOT_CONFINED_IDENTITY_UNAVAILABLE")
    return uid, gid


def _chown_tree(root: pathlib.Path, uid: int, gid: int) -> None:
    if os.geteuid() != 0:
        return
    for path in [root, *sorted(root.rglob("*"))]:
        os.chown(path, uid, gid)


def _closed_world_manifest(input_dir: pathlib.Path) -> dict[str, Any]:
    scan = scan_input_dir(input_dir)
    declared = {
        "schema": CLOSED_WORLD_MANIFEST_SCHEMA,
        "entries": scan["entries"],
        "manifest_sha256": scan["manifest_sha256"],
    }
    verified = verify_declared_manifest(
        input_dir=input_dir,
        declared_manifest=declared,
    )
    if verified.get("status") != "PASS__EXACT_CLOSED_WORLD_INPUT_TREE_BOUND":
        raise SealedFieldProjectionError("CLOSED_WORLD_INPUT_VERIFICATION_FAILED")
    return verified


def _normalize_consumer_files(
    consumer_files: Mapping[str, str | bytes],
) -> dict[str, bytes]:
    if not isinstance(consumer_files, Mapping) or not consumer_files:
        raise SealedFieldProjectionError("CONSUMER_FILES_REQUIRED")
    out: dict[str, bytes] = {}
    for raw_path, raw_content in consumer_files.items():
        path = _safe_relpath(str(raw_path))
        if path in {PROJECTION_FILE, RUNNER_FILE}:
            raise SealedFieldProjectionError("RESERVED_INPUT_PATH:" + path)
        if path in out:
            raise SealedFieldProjectionError("DUPLICATE_INPUT_PATH:" + path)
        if isinstance(raw_content, str):
            content = raw_content.encode("utf-8")
        elif isinstance(raw_content, bytes):
            content = raw_content
        else:
            raise SealedFieldProjectionError("CONSUMER_FILE_CONTENT_INVALID:" + path)
        out[path] = content
    return out


def run_sealed_consumer(
    *,
    source_documents: Mapping[str, Mapping[str, Any]],
    field_dependencies: Mapping[str, Sequence[str]],
    consumer_files: Mapping[str, str | bytes],
    consumer_module: str,
    consumer_entrypoint: str = "evaluate",
    launcher: Callable[[Mapping[str, Any]], Mapping[str, Any]] = run_confined,
    limits: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    try:
        module = _safe_relpath(consumer_module)
        files = _normalize_consumer_files(consumer_files)
        if module not in files:
            raise SealedFieldProjectionError("CONSUMER_MODULE_NOT_DECLARED")

        bundle = prepare_projection_bundle(
            source_documents=source_documents,
            field_dependencies=field_dependencies,
        )
        projection_bytes = _canon(bundle)
        projection_sha = _sha256(projection_bytes)
        runner_bytes = _runner_source(
            consumer_module=module,
            consumer_entrypoint=str(consumer_entrypoint or ""),
            projection_sha256=projection_sha,
        ).encode("utf-8")

        with tempfile.TemporaryDirectory(prefix="brain-sealed-field-input-") as td:
            root = pathlib.Path(td)
            (root / PROJECTION_FILE).write_bytes(projection_bytes)
            (root / RUNNER_FILE).write_bytes(runner_bytes)
            for rel, content in files.items():
                target = root / pathlib.PurePosixPath(rel)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)

            uid, gid = _select_identity()
            _chown_tree(root, uid, gid)
            manifest = _closed_world_manifest(root)

            effective_limits = {
                "pids": 16,
                "memory_mb": 256,
                "cpu_seconds": 5,
                "wallclock_s": 15,
                "scratch_mb": 16,
                "max_file_mb": 8,
                "nofile": 32,
                "broker_max_bytes": 1_000_000,
            }
            if limits is not None:
                if not isinstance(limits, Mapping):
                    raise SealedFieldProjectionError("LIMITS_NOT_MAPPING")
                effective_limits.update({str(k): int(v) for k, v in limits.items()})

            policy = {
                "argv": [
                    "/usr/bin/python3",
                    "-I",
                    "-S",
                    "/input/" + RUNNER_FILE,
                ],
                "input_dir": str(root),
                "env": {
                    "PYTHONHASHSEED": "0",
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "TZ": "UTC",
                },
                "host_uid": uid,
                "host_gid": gid,
                "limits": effective_limits,
            }
            launched = launcher(policy)
            if not isinstance(launched, Mapping):
                raise SealedFieldProjectionError("LAUNCHER_RESULT_NOT_MAPPING")
            if launched.get("status") != "CHILD_EXITED" or launched.get("returncode") != 0:
                raise SealedFieldProjectionError(
                    "SEALED_CONSUMER_LAUNCH_FAILED:"
                    + str(launched.get("status"))
                    + ":"
                    + str(launched.get("returncode"))
                )
            raw = launched.get("broker_payload")
            if not isinstance(raw, (bytes, bytearray)):
                raise SealedFieldProjectionError("BROKER_PAYLOAD_NOT_BYTES")
            try:
                child = json.loads(bytes(raw).decode("utf-8"))
            except Exception as exc:
                raise SealedFieldProjectionError(
                    "BROKER_PAYLOAD_JSON_INVALID:" + type(exc).__name__
                ) from exc
            if not isinstance(child, Mapping):
                raise SealedFieldProjectionError("CHILD_RESULT_NOT_MAPPING")
            if child.get("schema") != RUNNER_SCHEMA:
                raise SealedFieldProjectionError("CHILD_RESULT_SCHEMA_INVALID")
            if child.get("projection_bundle_sha256") != bundle["projection_bundle_sha256"]:
                raise SealedFieldProjectionError("CHILD_PROJECTION_BINDING_MISMATCH")
            result = child.get("consumer_result")
            if not isinstance(result, Mapping):
                raise SealedFieldProjectionError("CONSUMER_RESULT_NOT_MAPPING")

            return {
                "schema": SCHEMA,
                "pass": True,
                "status": "PASS__SEALED_FIELD_PROJECTION_CONSUMER",
                "projection_bundle_sha256": bundle["projection_bundle_sha256"],
                "projection_source_count": bundle["source_count"],
                "closed_world_input_manifest_sha256": manifest["manifest_sha256"],
                "closed_world_input_entry_count": manifest["entry_count"],
                "launcher_policy_sha256": launched.get("policy_sha256"),
                "consumer_result": dict(result),
                "undeclared_host_repository_reads_available": False,
                "network_authority": False,
                "execution_authority": False,
                "promotion_authority": False,
                "acceptance_credit_delta": 0,
                "capability_credit_delta": 0,
                "ownership_credit_delta": 0,
                "terminal_credit_delta": 0,
                "rule": (
                    "FIELD_SCOPED_REUSE_REQUIRES_CONSUMER_TO_EXECUTE_ONLY_INSIDE_"
                    "THE_EXACT_MANIFESTED_ZERO_AMBIENT_INPUT_TREE"
                ),
            }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "error": type(exc).__name__ + ":" + str(exc),
            "undeclared_host_repository_reads_available": None,
            "execution_authority": False,
            "promotion_authority": False,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "terminal_credit_delta": 0,
        }
