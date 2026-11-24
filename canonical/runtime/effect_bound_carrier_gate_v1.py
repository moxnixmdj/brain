"""Effect-bound carrier gate; byte verification only, no execution authority.

This module is the trusted parent for a controlled in-process fixture. It uses
an existing bounded no-follow snapshotter to turn a quiescent tree into immutable
bytes, then sends those exact bytes to a different Python verifier process. The
verifier recomputes the canonical receipt digest, every effect digest, patch path
safety, fresh-tree patch applicability, and patch replay. The result is a receipt
with a distinct verifier run reference, not a qualified isolation carrier.

It does not launch untrusted code, call ``open_model().solve()``, use nested Linux
namespaces, accept caller authority flags, publish a patch, adopt a worktree, or
create a benchmark score. Existing producer-built collectors and recomputers are
not treated as independent verifiers or authority.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from canonical.runtime import repair_candidate_broker_v1 as snapshots

SCHEMA = "BRAIN_EFFECT_BOUND_CARRIER_GATE_V1"
RECEIPT_SCHEMA = "BRAIN_EFFECT_BOUND_CARRIER_RECEIPT_V1"
PACKET_SCHEMA = "BRAIN_EFFECT_BOUND_CARRIER_VERIFIER_PACKET_V1"
STORE_SCHEMA = "BRAIN_EFFECT_BOUND_CARRIER_EXTERNAL_STORE_V1"
VERIFIER_RELPATH = "canonical/tools/effect_bound_carrier_independent_verifier_v1.py"
VERIFIER_ID = "BRAIN_EFFECT_BOUND_CARRIER_INDEPENDENT_VERIFIER_V1"
VERIFIER_VERSION = "1"
COLLECTOR_ID = "BRAIN_EFFECT_BOUND_CARRIER_TRUSTED_PARENT_V1"
COLLECTOR_VERSION = "1"
PATCH_EFFECT = "model.patch"
LIMITS = snapshots.SnapshotLimits(
    max_files=256, max_dirs=128, max_file_bytes=4_000_000, max_total_bytes=8_000_000
)
MAX_PACKET_BYTES = 24_000_000
_FORBIDDEN_AUTHORITY_FIELDS = frozenset(
    {
        "confinement_admitted",
        "carrier_qualified",
        "execution_authorized",
        "allow_isolated_vm_eval",
        "receipt_sha256",
        "patch_published",
        "independent_verification",
        "owner_approved",
        "verified",
        "publication_authority",
        "truth_achieved",
    }
)
_HEX16 = re.compile(r"[0-9a-f]{16}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class GateRefused(ValueError):
    """Raised when any byte, path, authority, run-ref or cleanup precondition fails."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_relative_path(value: Any) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise GateRefused("EFFECT_PATH_INVALID")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or str(path) != value
        or any(part in ("", ".", "..", ".git") for part in value.split("/"))
        or len(path.parts) > 32
    ):
        raise GateRefused("EFFECT_PATH_INVALID")
    try:
        if len(value.encode("utf-8")) > 1024:
            raise GateRefused("EFFECT_PATH_TOO_LONG")
    except UnicodeError as exc:
        raise GateRefused("EFFECT_PATH_INVALID") from exc
    return value


def deny_caller_authority(request: Mapping[str, Any]) -> None:
    if not isinstance(request, Mapping):
        raise GateRefused("CALLER_REQUEST_INVALID")
    found = sorted(set(request) & _FORBIDDEN_AUTHORITY_FIELDS)
    if found:
        raise GateRefused("CALLER_AUTHORITY_FIELD_REFUSED:" + ",".join(found))


def _check_distinct_run_refs(values: tuple[str, ...]) -> None:
    for value in values:
        if not isinstance(value, str) or not _HEX16.fullmatch(value):
            raise GateRefused("RUN_REFERENCE_INVALID")
    if len(set(values)) != len(values):
        raise GateRefused("RUN_REFERENCE_COLLISION")


def _expected_directories(paths: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    directories: set[str] = set()
    for path in paths:
        parts = PurePosixPath(path).parts[:-1]
        for index in range(1, len(parts) + 1):
            directories.add("/".join(parts[:index]))
    return tuple(sorted(directories))


def collect_snapshot(root: str | Path) -> dict[str, Any]:
    """Return immutable bytes from one bounded, no-follow snapshot."""
    try:
        snap = snapshots.snapshot_project(root, limits=LIMITS)
    except snapshots.CandidateDenied as exc:
        raise GateRefused("SNAPSHOT_REFUSED:" + str(exc)) from exc
    files: dict[str, bytes] = {}
    total = 0
    for path, data in snap.files:
        safe_relative_path(path)
        if path in files:
            raise GateRefused("DUPLICATE_SNAPSHOT_PATH")
        if not isinstance(data, bytes) or len(data) > LIMITS.max_file_bytes:
            raise GateRefused("EFFECT_BYTES_INVALID")
        total += len(data)
        if total > LIMITS.max_total_bytes:
            raise GateRefused("EFFECT_BYTES_TOO_LARGE")
        files[path] = data
    expected_dirs = _expected_directories(tuple(files))
    if tuple(snap.directories) != expected_dirs:
        raise GateRefused("UNDECLARED_DIRECTORY_OR_EMPTY_DIRECTORY")
    manifest = {
        "directories": list(expected_dirs),
        "files": [[path, len(data), sha256_hex(data)] for path, data in sorted(files.items())],
    }
    digest = sha256_hex(canonical_bytes(manifest))
    if digest != snap.digest:
        raise GateRefused("SNAPSHOT_DIGEST_MISMATCH")
    return {
        "files": files,
        "directories": expected_dirs,
        "digest": digest,
        "total_bytes": total,
        "origin": snap.origin,
    }


def validate_effects(
    collection: Mapping[str, Any],
    declared_paths: tuple[str, ...] | list[str],
    *,
    patch_path: str = PATCH_EFFECT,
) -> dict[str, bytes]:
    if not isinstance(collection, Mapping) or not isinstance(collection.get("files"), Mapping):
        raise GateRefused("EFFECT_COLLECTION_INVALID")
    files = collection["files"]
    for path, data in files.items():
        safe_relative_path(path)
        if not isinstance(data, bytes):
            raise GateRefused("EFFECT_BYTES_INVALID")
    declared = tuple(declared_paths)
    if not declared:
        raise GateRefused("DECLARED_EFFECT_SET_EMPTY")
    if len(set(declared)) != len(declared):
        raise GateRefused("DUPLICATE_DECLARED_EFFECT_PATH")
    for path in declared:
        safe_relative_path(path)
    if set(files) != set(declared):
        raise GateRefused("EFFECT_SET_MISMATCH")
    if patch_path not in files or not isinstance(files[patch_path], bytes) or not files[patch_path]:
        raise GateRefused("PATCH_EFFECT_MISSING_OR_EMPTY")
    total = 0
    for path in declared:
        data = files[path]
        if len(data) > LIMITS.max_file_bytes:
            raise GateRefused("EFFECT_BYTES_TOO_LARGE")
        total += len(data)
        if path == patch_path:
            continue
        if path.startswith("files/"):
            suffix = path[len("files/") :]
        elif path.startswith("deleted/"):
            suffix = path[len("deleted/") :]
        else:
            raise GateRefused("EFFECT_PATH_CLASS_UNSUPPORTED")
        safe_relative_path(suffix)
    if total > LIMITS.max_total_bytes:
        raise GateRefused("EFFECT_BYTES_TOO_LARGE")
    if collection.get("digest") != sha256_hex(
        canonical_bytes(
            {
                "directories": list(_expected_directories(declared)),
                "files": [[path, len(files[path]), sha256_hex(files[path])] for path in sorted(declared)],
            }
        )
    ):
        raise GateRefused("EFFECT_MANIFEST_DIGEST_MISMATCH")
    return {path: files[path] for path in sorted(declared)}


def _script_path(code_root: str | Path | None = None) -> tuple[Path, Path, str]:
    root = Path(code_root).resolve(strict=True) if code_root else Path(__file__).resolve().parents[2]
    script = (root / VERIFIER_RELPATH).resolve(strict=True)
    data = script.read_bytes()
    return root, script, sha256_hex(data)


def _policy_document(python_version: str) -> dict[str, Any]:
    return {
        "python_version": python_version,
        "worker_kind": "IN_PROCESS_TRUSTED_FIXTURE_ONLY",
        "nested_namespaces_used": False,
        "runtime_model_calls": 0,
        "runtime_network_calls": 0,
        "git_apply": ["git", "apply", "--check", "-p1", "-"],
        "limits": {
            "max_files": LIMITS.max_files,
            "max_dirs": LIMITS.max_dirs,
            "max_file_bytes": LIMITS.max_file_bytes,
            "max_total_bytes": LIMITS.max_total_bytes,
        },
        "canonicalization": "JSON_SORT_KEYS_COMPACT_UTF8_SHA256",
    }


def build_receipt(
    *,
    run_id: str,
    base_commit: str,
    baseline: Mapping[str, Any],
    effects: Mapping[str, bytes],
    python_version: str,
    runner_source_sha256: str,
    collector_source_sha256: str,
    verifier_script_sha256: str,
    producer_run_ref: str,
    collector_run_ref: str,
    verifier_ticket_run_ref: str,
    worker_wall_s: float,
    cleanup_outcome: str,
    dirty_tree_sha256: str,
    fixture_id: str,
) -> tuple[dict[str, Any], bytes, str]:
    if cleanup_outcome != "TEMP_TREE_REMOVED":
        raise GateRefused("CLEANUP_NOT_VERIFIED")
    if not isinstance(base_commit, str) or not re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z").fullmatch(base_commit):
        raise GateRefused("BASE_COMMIT_CLAIM_INVALID")
    if not isinstance(baseline.get("digest"), str) or not _HEX64.fullmatch(baseline["digest"]):
        raise GateRefused("INPUT_SNAPSHOT_DIGEST_INVALID")
    if not isinstance(dirty_tree_sha256, str) or not _HEX64.fullmatch(dirty_tree_sha256):
        raise GateRefused("DIRTY_TREE_DIGEST_INVALID")
    _check_distinct_run_refs((producer_run_ref, collector_run_ref, verifier_ticket_run_ref))
    policy = _policy_document(python_version)
    runtime_policy_sha256 = sha256_hex(canonical_bytes(policy))
    declared = tuple(sorted(effects))
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "run_id": run_id,
        "fixture_id": fixture_id,
        "base_commit_claim": base_commit,
        "dirty_tree_sha256": dirty_tree_sha256,
        "input_snapshot_sha256": baseline["digest"],
        "runtime_policy_sha256": runtime_policy_sha256,
        "runtime": {
            "python_version": python_version,
            "collector_source_sha256": collector_source_sha256,
            "runner_source_sha256": runner_source_sha256,
            "verifier_script_sha256": verifier_script_sha256,
        },
        "isolation_policy": {
            "id": "NO_QUALIFIED_ISOLATION_CARRIER_V1",
            "nested_namespaces_used": False,
            "reviewed_carrier": False,
            "egress_boundary": "NOT_QUALIFIED",
        },
        "resource_policy": {
            "worker_kind": "IN_PROCESS_TRUSTED_FIXTURE_ONLY",
            "descendants_started": 0,
            "quiescence": "NO_CHILD_PROCESS_STARTED_BY_THIS_GATE",
        },
        "collector": {
            "id": COLLECTOR_ID,
            "version": COLLECTOR_VERSION,
            "run_ref": collector_run_ref,
        },
        "producer": {
            "kind": "IN_PROCESS_TRUSTED_FIXTURE",
            "run_ref": producer_run_ref,
            "open_model_solve_invoked": False,
            "runtime_model_calls": 0,
            "runtime_network_calls": 0,
        },
        "verifier": {
            "id": VERIFIER_ID,
            "version": VERIFIER_VERSION,
            "script_relpath": VERIFIER_RELPATH,
            "script_sha256": verifier_script_sha256,
            "ticket_run_ref": verifier_ticket_run_ref,
            "run_ref_policy": "SEPARATE_PROCESS_SUPPLIED",
        },
        "worker": {
            "exit_status": "RETURNED",
            "wall_s": round(float(worker_wall_s), 6),
            "descendants_started": 0,
            "quiescence_observed": True,
            "cleanup_outcome": cleanup_outcome,
        },
        "declared_effect_paths": list(declared),
        "effects": {
            path: {"size": len(data), "sha256": sha256_hex(data)}
            for path, data in sorted(effects.items())
        },
        "exact_patch_path": PATCH_EFFECT,
        "canonicalization": {
            "algorithm": "JSON_SORT_KEYS_COMPACT_UTF8",
            "digest": "SHA256_OVER_CANONICAL_RECEIPT_BYTES",
        },
        "authority": {
            "carrier_qualified": False,
            "execution_authorized": False,
            "patch_published": False,
            "independent_verification": "SEPARATE_PROCESS_REQUIRED",
            "publication_authority": False,
        },
        "truth": {
            "acceptance_credit_delta": 0,
            "section_6": "NOT_DONE",
            "completion_claim": False,
            "truth_achieved": False,
            "own_weights": False,
            "written_to_weights": False,
        },
    }
    raw = canonical_bytes(receipt)
    return receipt, raw, runtime_policy_sha256


def run_independent_verifier(
    *,
    receipt_bytes: bytes,
    expected_receipt_sha256: str,
    effect_bytes: Mapping[str, bytes],
    baseline: Mapping[str, Any],
    expected_effect_paths: tuple[str, ...] | list[str],
    expected_effect_sha256s: Mapping[str, str],
    expected_patch_sha256: str,
    expected_run_id: str,
    expected_base_commit: str,
    expected_runtime_policy_sha256: str,
    producer_run_ref: str,
    collector_run_ref: str,
    verifier_ticket_run_ref: str,
    code_root: str | Path | None = None,
    timeout_s: int = 90,
) -> dict[str, Any]:
    _check_distinct_run_refs((producer_run_ref, collector_run_ref, verifier_ticket_run_ref))
    root, script, script_sha = _script_path(code_root)
    if not isinstance(receipt_bytes, bytes) or not receipt_bytes:
        raise GateRefused("RECEIPT_BYTES_INVALID")
    if sha256_hex(receipt_bytes) != expected_receipt_sha256:
        raise GateRefused("EXPECTED_RECEIPT_DIGEST_MISMATCH")
    if not isinstance(baseline.get("digest"), str):
        raise GateRefused("BASELINE_INVALID")
    baseline_files = baseline.get("files")
    if not isinstance(baseline_files, Mapping):
        raise GateRefused("BASELINE_INVALID")
    packet = {
        "schema": PACKET_SCHEMA,
        "receipt_bytes_b64": base64.b64encode(receipt_bytes).decode("ascii"),
        "expected_receipt_sha256": expected_receipt_sha256,
        "expected_run_id": expected_run_id,
        "expected_base_commit": expected_base_commit,
        "expected_runtime_policy_sha256": expected_runtime_policy_sha256,
        "expected_input_snapshot_sha256": baseline["digest"],
        "expected_effect_paths": list(sorted(expected_effect_paths)),
        "expected_effect_sha256s": dict(sorted(expected_effect_sha256s.items())),
        "expected_patch_path": PATCH_EFFECT,
        "expected_patch_sha256": expected_patch_sha256,
        "expected_verifier_script_sha256": script_sha,
        "effects": {
            path: base64.b64encode(data).decode("ascii")
            for path, data in sorted(effect_bytes.items())
        },
        "baseline": {
            "directories": list(baseline.get("directories", ())),
            "files": {
                path: base64.b64encode(data).decode("ascii")
                for path, data in sorted(baseline_files.items())
            },
            "sha256": baseline["digest"],
        },
        "run_refs": {
            "producer": producer_run_ref,
            "collector": collector_run_ref,
            "verifier_ticket": verifier_ticket_run_ref,
        },
    }
    raw = canonical_bytes(packet)
    if len(raw) > MAX_PACKET_BYTES:
        raise GateRefused("VERIFIER_PACKET_TOO_LARGE")
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(root),
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
    }
    try:
        proc = subprocess.run(
            [sys.executable, "-I", str(script)],
            cwd=str(root),
            env=env,
            input=raw,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_s,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GateRefused("INDEPENDENT_VERIFIER_UNAVAILABLE:" + type(exc).__name__) from exc
    if proc.returncode != 0:
        raise GateRefused(
            "INDEPENDENT_VERIFIER_FAILED:" + proc.stderr.decode("utf-8", "replace")[:300]
        )
    try:
        result = json.loads(proc.stdout.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise GateRefused("INDEPENDENT_VERIFIER_OUTPUT_INVALID") from exc
    if not isinstance(result, dict) or result.get("status") != "INDEPENDENT_EFFECT_BYTES_VERIFIED":
        raise GateRefused("INDEPENDENT_VERIFIER_REFUSED:" + str(result.get("reason", "UNKNOWN"))[:200])
    if result.get("packet_sha256") != sha256_hex(raw):
        raise GateRefused("VERIFIER_PACKET_DIGEST_MISMATCH")
    if result.get("receipt_sha256") != expected_receipt_sha256:
        raise GateRefused("VERIFIER_RECEIPT_DIGEST_MISMATCH")
    if result.get("effect_sha256s") != dict(sorted(expected_effect_sha256s.items())):
        raise GateRefused("VERIFIER_EFFECT_DIGEST_MISMATCH")
    if result.get("patch_sha256") != expected_patch_sha256:
        raise GateRefused("VERIFIER_PATCH_DIGEST_MISMATCH")
    if result.get("verifier_script_sha256") != script_sha:
        raise GateRefused("VERIFIER_SCRIPT_DIGEST_MISMATCH")
    if result.get("git_apply_check_passed") is not True or result.get("patch_replay_ok") is not True:
        raise GateRefused("VERIFIER_PATCH_REPLAY_NOT_PROVEN")
    if result.get("execution_authorized") is not False or result.get("carrier_qualified") is not False:
        raise GateRefused("VERIFIER_AUTHORITY_FIELD_NOT_FALSE")
    verifier_run_ref = result.get("verifier_run_ref")
    if not isinstance(verifier_run_ref, str):
        raise GateRefused("VERIFIER_RUN_REFERENCE_INVALID")
    _check_distinct_run_refs(
        (producer_run_ref, collector_run_ref, verifier_ticket_run_ref, verifier_run_ref)
    )
    if result.get("verifier_pid") == os.getpid():
        raise GateRefused("VERIFIER_PROCESS_NOT_DISTINCT")
    return result


def gate_from_collection(
    *,
    request: Mapping[str, Any],
    baseline: Mapping[str, Any],
    effect_collection: Mapping[str, Any],
    declared_effect_paths: tuple[str, ...] | list[str],
    fixture_id: str,
    run_id: str,
    base_commit: str,
    dirty_tree_sha256: str,
    python_version: str,
    runner_source_sha256: str,
    producer_run_ref: str,
    collector_run_ref: str,
    verifier_ticket_run_ref: str,
    worker_wall_s: float,
    cleanup_outcome: str,
    code_root: str | Path | None = None,
) -> dict[str, Any]:
    deny_caller_authority(request)
    _check_distinct_run_refs((producer_run_ref, collector_run_ref, verifier_ticket_run_ref))
    effects = validate_effects(effect_collection, declared_effect_paths)
    _, script, script_sha = _script_path(code_root)
    collector_source_sha = sha256_hex(Path(__file__).resolve(strict=True).read_bytes())
    receipt, receipt_bytes, runtime_policy_sha = build_receipt(
        run_id=run_id,
        base_commit=base_commit,
        baseline=baseline,
        effects=effects,
        python_version=python_version,
        runner_source_sha256=runner_source_sha256,
        collector_source_sha256=collector_source_sha,
        verifier_script_sha256=script_sha,
        producer_run_ref=producer_run_ref,
        collector_run_ref=collector_run_ref,
        verifier_ticket_run_ref=verifier_ticket_run_ref,
        worker_wall_s=worker_wall_s,
        cleanup_outcome=cleanup_outcome,
        dirty_tree_sha256=dirty_tree_sha256,
        fixture_id=fixture_id,
    )
    expected_effect_sha256s = {path: sha256_hex(data) for path, data in effects.items()}
    expected_patch_sha256 = expected_effect_sha256s[PATCH_EFFECT]
    verifier_result = run_independent_verifier(
        receipt_bytes=receipt_bytes,
        expected_receipt_sha256=sha256_hex(receipt_bytes),
        effect_bytes=effects,
        baseline=baseline,
        expected_effect_paths=tuple(sorted(effects)),
        expected_effect_sha256s=expected_effect_sha256s,
        expected_patch_sha256=expected_patch_sha256,
        expected_run_id=run_id,
        expected_base_commit=base_commit,
        expected_runtime_policy_sha256=runtime_policy_sha,
        producer_run_ref=producer_run_ref,
        collector_run_ref=collector_run_ref,
        verifier_ticket_run_ref=verifier_ticket_run_ref,
        code_root=code_root,
    )
    return {
        "schema": SCHEMA,
        "status": "EFFECT_BOUND_RECEIPT_VERIFIED__CARRIER_NOT_QUALIFIED",
        "fixture_id": fixture_id,
        "receipt": receipt,
        "receipt_sha256": sha256_hex(receipt_bytes),
        "effect_sha256s": expected_effect_sha256s,
        "patch_sha256": expected_patch_sha256,
        "verifier": verifier_result,
        "verifier_script_relpath": VERIFIER_RELPATH,
        "verifier_script_sha256": script_sha,
        "run_references": {
            "producer": producer_run_ref,
            "collector": collector_run_ref,
            "verifier_ticket": verifier_ticket_run_ref,
            "verifier": verifier_result["verifier_run_ref"],
        },
        "receipt_verified": True,
        "independent_process_verification": True,
        "independent_attestation": False,
        "carrier_qualified": False,
        "execution_authorized": False,
        "patch_published": False,
        "no_automatic_adoption": True,
        "acceptance_credit_delta": 0,
        "section_6": "NOT_DONE",
        "completion_claim": False,
        "truth_achieved": False,
        "own_weights": False,
        "written_to_weights": False,
        "runtime_model_calls": 0,
        "runtime_network_calls": 0,
    }


def store_document(
    *,
    module_sha256: str,
    verifier_script_sha256: str,
    receipt_relpath: str,
) -> dict[str, Any]:
    return {
        "schema": STORE_SCHEMA,
        "procedure": {
            "id": "EFFECT_BOUND_CARRIER_GATE_V1",
            "source_sha256": module_sha256,
            "verifier_script_sha256": verifier_script_sha256,
            "receipt_ref": receipt_relpath,
        },
        "boundary": {
            "caller_authority_fields_refused": True,
            "independent_process_required": True,
            "distinct_run_refs_required": True,
            "carrier_qualified": False,
            "execution_authorized": False,
            "patch_published": False,
            "own_weights": False,
            "section_6": "NOT_DONE",
            "completion_claim": False,
        },
    }


def verify_store(
    store_path: str | Path,
    *,
    module_sha256: str,
    verifier_script_sha256: str,
) -> dict[str, Any]:
    path = Path(store_path)
    if not path.is_file():
        raise GateRefused("STORE_MISSING__REFUSE")
    data = path.read_bytes()
    if len(data) > 1_000_000:
        raise GateRefused("STORE_TOO_LARGE")
    try:
        document = json.loads(data.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise GateRefused("STORE_JSON_INVALID") from exc
    if not isinstance(document, dict) or data != canonical_bytes(document):
        raise GateRefused("STORE_NOT_CANONICAL")
    boundary = document.get("boundary")
    procedure = document.get("procedure")
    if not isinstance(boundary, Mapping) or not isinstance(procedure, Mapping):
        raise GateRefused("STORE_SHAPE_INVALID")
    if document.get("schema") != STORE_SCHEMA:
        raise GateRefused("STORE_SCHEMA_INVALID")
    if procedure.get("source_sha256") != module_sha256:
        raise GateRefused("STORE_PROCEDURE_DIGEST_MISMATCH")
    if procedure.get("verifier_script_sha256") != verifier_script_sha256:
        raise GateRefused("STORE_VERIFIER_DIGEST_MISMATCH")
    expected_false = (
        "carrier_qualified",
        "execution_authorized",
        "patch_published",
        "own_weights",
        "completion_claim",
    )
    if any(boundary.get(key) is not False for key in expected_false):
        raise GateRefused("STORE_AUTHORITY_FIELD_NOT_FALSE")
    expected_true = (
        "caller_authority_fields_refused",
        "independent_process_required",
        "distinct_run_refs_required",
    )
    if any(boundary.get(key) is not True for key in expected_true):
        raise GateRefused("STORE_POLICY_FIELD_NOT_TRUE")
    if boundary.get("section_6") != "NOT_DONE":
        raise GateRefused("STORE_SECTION_6_FIELD_INVALID")
    if set(document) != {"schema", "procedure", "boundary"} or set(procedure) != {
        "id",
        "source_sha256",
        "verifier_script_sha256",
        "receipt_ref",
    }:
        raise GateRefused("STORE_SHAPE_INVALID")
    return {
        "status": "EXTERNAL_STORE_PRESENT_AND_INSPECTABLE",
        "store_sha256": sha256_hex(data),
        "canonical_sha256": sha256_hex(canonical_bytes(document)),
        "document": document,
    }


def restart_store_digest(store_bytes: bytes, *, code_root: str | Path) -> dict[str, Any]:
    """Recompute store digests in a separate Python process with its own run ref."""
    code = (
        "import hashlib,json,secrets,sys\n"
        "raw=sys.stdin.buffer.read()\n"
        "doc=json.loads(raw.decode('utf-8'))\n"
        "can=json.dumps(doc,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')\n"
        "print(json.dumps({'status':'STORE_DIGEST_RECOMPUTED',"
        "'store_sha256':hashlib.sha256(raw).hexdigest(),"
        "'canonical_sha256':hashlib.sha256(can).hexdigest(),"
        "'restart_run_ref':secrets.token_hex(8)},sort_keys=True))\n"
    )
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(Path(code_root).resolve(strict=True)),
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    try:
        proc = subprocess.run(
            [sys.executable, "-I", "-c", code],
            cwd=str(Path(code_root).resolve(strict=True)),
            env=env,
            input=store_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GateRefused("STORE_RESTART_UNAVAILABLE:" + type(exc).__name__) from exc
    if proc.returncode != 0:
        raise GateRefused("STORE_RESTART_FAILED:" + proc.stderr.decode("utf-8", "replace")[:200])
    try:
        result = json.loads(proc.stdout.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise GateRefused("STORE_RESTART_OUTPUT_INVALID") from exc
    if result.get("status") != "STORE_DIGEST_RECOMPUTED":
        raise GateRefused("STORE_RESTART_REFUSED")
    return result
