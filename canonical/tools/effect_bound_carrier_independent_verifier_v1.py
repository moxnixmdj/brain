"""Independent effect-bound carrier byte verifier; no producer-module imports.

This script runs as a separate ``python3 -I`` process. It receives one canonical
packet of immutable bytes from the trusted parent, recomputes the receipt and all
effect digests, checks its own script digest, validates patch paths, builds a
fresh Git tree from the supplied baseline bytes, checks patch applicability,
applies the exact patch, and compares the replayed tree with the declared effect
bytes. It supplies its own run reference.

A pass here is byte/replay verification by a different process. It is not an
authenticated attestation, a qualified isolation carrier, a benchmark score, a
test success oracle, authority to publish, or permission to execute untrusted
code.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import stat
import subprocess
import sys
import tempfile
from typing import Any

VERIFIER_ID = "BRAIN_EFFECT_BOUND_CARRIER_INDEPENDENT_VERIFIER_V1"
VERIFIER_VERSION = "1"
VERIFIER_RELPATH = "canonical/tools/effect_bound_carrier_independent_verifier_v1.py"
PACKET_SCHEMA = "BRAIN_EFFECT_BOUND_CARRIER_VERIFIER_PACKET_V1"
RECEIPT_SCHEMA = "BRAIN_EFFECT_BOUND_CARRIER_RECEIPT_V1"
MAX_PACKET_BYTES = 24_000_000
MAX_EFFECT_TOTAL_BYTES = 8_000_000
MAX_EFFECT_BYTES = 4_000_000
MAX_BASELINE_TOTAL_BYTES = 8_000_000
_HEX16 = re.compile(r"[0-9a-f]{16}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_COMMIT = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_SAFE_PART = re.compile(r"[A-Za-z0-9_.-]+\Z")
RECEIPT_KEYS = {
    "schema",
    "run_id",
    "fixture_id",
    "base_commit_claim",
    "dirty_tree_sha256",
    "input_snapshot_sha256",
    "runtime_policy_sha256",
    "runtime",
    "isolation_policy",
    "resource_policy",
    "collector",
    "producer",
    "verifier",
    "worker",
    "declared_effect_paths",
    "effects",
    "exact_patch_path",
    "canonicalization",
    "authority",
    "truth",
}
PACKET_KEYS = {
    "schema",
    "receipt_bytes_b64",
    "expected_receipt_sha256",
    "expected_run_id",
    "expected_base_commit",
    "expected_runtime_policy_sha256",
    "expected_input_snapshot_sha256",
    "expected_effect_paths",
    "expected_effect_sha256s",
    "expected_patch_path",
    "expected_patch_sha256",
    "expected_verifier_script_sha256",
    "effects",
    "baseline",
    "run_refs",
}


class Refused(ValueError):
    """Structured refusal, never converted into a pass."""


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


def safe_path(value: Any) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise Refused("PATH_INVALID")
    parts = value.split("/")
    if (
        value.startswith("/")
        or len(parts) > 32
        or any(not part or part in (".", "..", ".git") or not _SAFE_PART.fullmatch(part) for part in parts)
    ):
        raise Refused("PATH_INVALID")
    return value


def _identity(st: os.stat_result) -> tuple[Any, ...]:
    return (st.st_dev, st.st_ino, st.st_mode, st.st_size, st.st_mtime_ns, st.st_ctime_ns, st.st_nlink)


def _decode_bytes_map(value: Any, *, label: str) -> dict[str, bytes]:
    if not isinstance(value, dict):
        raise Refused(label + "_SHAPE_INVALID")
    result: dict[str, bytes] = {}
    for raw_path, encoded in value.items():
        path = safe_path(raw_path)
        if path in result:
            raise Refused(label + "_DUPLICATE_PATH")
        if not isinstance(encoded, str):
            raise Refused(label + "_ENCODING_INVALID")
        try:
            data = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise Refused(label + "_ENCODING_INVALID") from exc
        result[path] = data
    return result


def _expected_directories(paths: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    dirs: set[str] = set()
    for path in paths:
        parts = PurePosixPath(path).parts[:-1]
        for index in range(1, len(parts) + 1):
            dirs.add("/".join(parts[:index]))
    return tuple(sorted(dirs))


def _digest_tree(directories: tuple[str, ...], files: dict[str, bytes]) -> str:
    content = {
        "directories": list(directories),
        "files": [[path, len(data), sha256_hex(data)] for path, data in sorted(files.items())],
    }
    return sha256_hex(canonical_bytes(content))


def parse_patch_paths(patch: bytes) -> tuple[str, ...]:
    """Return patch paths after refusing traversal, binary, rename and mode syntax."""
    if not isinstance(patch, bytes) or not patch or b"\x00" in patch:
        raise Refused("PATCH_BYTES_INVALID")
    try:
        text = patch.decode("utf-8")
    except UnicodeError as exc:
        raise Refused("PATCH_NOT_UTF8") from exc
    if "\r" in text or not text.endswith("\n"):
        raise Refused("PATCH_LINE_ENDINGS_UNSUPPORTED")
    if "GIT binary patch" in text or "Binary files " in text:
        raise Refused("BINARY_PATCH_UNSUPPORTED")
    paths: list[str] = []
    current_paths: set[str] = set()
    saw_hunk = False
    saw_from = False
    saw_to = False
    saw_current_hunk = False
    saw_diff = False

    def close_current() -> None:
        nonlocal saw_current_hunk
        if saw_diff and not (saw_from and saw_to and saw_current_hunk):
            raise Refused("PATCH_STRUCTURE_INCOMPLETE")
        saw_current_hunk = False

    for line in text.splitlines():
        if line.startswith("diff --git "):
            close_current()
            parts = line.split()
            if len(parts) != 4 or parts[0] != "diff" or parts[1] != "--git":
                raise Refused("PATCH_DIFF_LINE_INVALID")
            a_path, b_path = parts[2], parts[3]
            if not a_path.startswith("a/") or not b_path.startswith("b/"):
                raise Refused("PATCH_DIFF_PREFIX_INVALID")
            path_a, path_b = safe_path(a_path[2:]), safe_path(b_path[2:])
            if path_a != path_b:
                raise Refused("PATCH_PATH_PAIR_MISMATCH")
            if path_a in current_paths:
                raise Refused("PATCH_DUPLICATE_PATH")
            paths.append(path_a)
            current_paths.add(path_a)
            saw_diff = True
            saw_from = False
            saw_to = False
        elif line in ("new file mode 100644", "deleted file mode 100644"):
            continue
        elif line.startswith("--- "):
            token = line[4:]
            if token == "/dev/null":
                pass
            elif token.startswith("a/"):
                path = safe_path(token[2:])
                if path not in current_paths:
                    raise Refused("PATCH_FROM_PATH_UNDECLARED")
            else:
                raise Refused("PATCH_FROM_LINE_UNSUPPORTED")
            saw_from = True
        elif line.startswith("+++ "):
            token = line[4:]
            if token == "/dev/null":
                pass
            elif token.startswith("b/"):
                path = safe_path(token[2:])
                if path not in current_paths:
                    raise Refused("PATCH_TO_PATH_UNDECLARED")
            else:
                raise Refused("PATCH_TO_LINE_UNSUPPORTED")
            saw_to = True
        elif line.startswith("@@ "):
            saw_hunk = True
            saw_current_hunk = True
        elif line.startswith("index ") or line == "\\ No newline at end of file":
            continue
        elif line.startswith(("old mode ", "new mode ", "rename from ", "rename to ", "similarity index ", "dissimilarity index ")):
            raise Refused("PATCH_METADATA_UNSUPPORTED")
        elif line.startswith(("+", "-", " ")):
            continue
        else:
            raise Refused("PATCH_LINE_UNSUPPORTED")
    close_current()
    if not paths or not saw_hunk or len(set(paths)) != len(paths):
        raise Refused("PATCH_STRUCTURE_INCOMPLETE")
    return tuple(paths)


def _validate_receipt(
    receipt: dict[str, Any],
    *,
    raw_receipt_bytes: bytes,
    expected: dict[str, Any],
    baseline_digest: str,
    effect_bytes: dict[str, bytes],
    actual_script_sha: str,
) -> tuple[str, ...]:
    if not isinstance(receipt, dict) or set(receipt) != RECEIPT_KEYS:
        raise Refused("RECEIPT_SHAPE_INVALID")
    if canonical_bytes(receipt) != raw_receipt_bytes:
        raise Refused("RECEIPT_NOT_CANONICAL")
    if receipt["schema"] != RECEIPT_SCHEMA:
        raise Refused("RECEIPT_SCHEMA_INVALID")
    digest = sha256_hex(raw_receipt_bytes)
    if digest != expected["receipt_sha256"]:
        raise Refused("RECEIPT_DIGEST_MISMATCH")
    if receipt["run_id"] != expected["run_id"]:
        raise Refused("RUN_ID_MISMATCH")
    if not isinstance(receipt["fixture_id"], str) or not receipt["fixture_id"]:
        raise Refused("FIXTURE_ID_INVALID")
    if not isinstance(receipt["base_commit_claim"], str) or not _COMMIT.fullmatch(receipt["base_commit_claim"]):
        raise Refused("BASE_COMMIT_INVALID")
    if receipt["base_commit_claim"] != expected["base_commit"]:
        raise Refused("BASE_COMMIT_MISMATCH")
    if not isinstance(receipt["dirty_tree_sha256"], str) or not _HEX64.fullmatch(receipt["dirty_tree_sha256"]):
        raise Refused("DIRTY_TREE_DIGEST_INVALID")
    if not isinstance(receipt["input_snapshot_sha256"], str) or not _HEX64.fullmatch(receipt["input_snapshot_sha256"]):
        raise Refused("INPUT_SNAPSHOT_DIGEST_INVALID")
    if receipt["input_snapshot_sha256"] != baseline_digest or receipt["input_snapshot_sha256"] != expected["input_snapshot_sha256"]:
        raise Refused("INPUT_SNAPSHOT_MISMATCH")
    if not isinstance(receipt["runtime_policy_sha256"], str) or not _HEX64.fullmatch(receipt["runtime_policy_sha256"]):
        raise Refused("RUNTIME_POLICY_DIGEST_INVALID")
    if receipt["runtime_policy_sha256"] != expected["runtime_policy_sha256"]:
        raise Refused("RUNTIME_POLICY_MISMATCH")
    runtime = receipt["runtime"]
    if not isinstance(runtime, dict) or set(runtime) != {
        "python_version",
        "collector_source_sha256",
        "runner_source_sha256",
        "verifier_script_sha256",
    }:
        raise Refused("RUNTIME_SHAPE_INVALID")
    if not isinstance(runtime["python_version"], str) or not runtime["python_version"]:
        raise Refused("RUNTIME_PYTHON_VERSION_INVALID")
    for key in ("collector_source_sha256", "runner_source_sha256", "verifier_script_sha256"):
        if not isinstance(runtime[key], str) or not _HEX64.fullmatch(runtime[key]):
            raise Refused("RUNTIME_DIGEST_INVALID")
    if runtime["verifier_script_sha256"] != actual_script_sha:
        raise Refused("RUNTIME_VERIFIER_DIGEST_MISMATCH")
    isolation = receipt["isolation_policy"]
    if not isinstance(isolation, dict) or set(isolation) != {
        "id",
        "nested_namespaces_used",
        "reviewed_carrier",
        "egress_boundary",
    }:
        raise Refused("ISOLATION_POLICY_SHAPE_INVALID")
    if isolation["id"] != "NO_QUALIFIED_ISOLATION_CARRIER_V1" or isolation["egress_boundary"] != "NOT_QUALIFIED":
        raise Refused("ISOLATION_POLICY_ID_MISMATCH")
    if isolation["nested_namespaces_used"] is not False or isolation["reviewed_carrier"] is not False:
        raise Refused("ISOLATION_POLICY_NOT_UNQUALIFIED")
    resources = receipt["resource_policy"]
    if not isinstance(resources, dict) or set(resources) != {"worker_kind", "descendants_started", "quiescence"}:
        raise Refused("RESOURCE_POLICY_SHAPE_INVALID")
    if resources["worker_kind"] != "IN_PROCESS_TRUSTED_FIXTURE_ONLY":
        raise Refused("RESOURCE_POLICY_WORKER_KIND_MISMATCH")
    if resources["quiescence"] != "NO_CHILD_PROCESS_STARTED_BY_THIS_GATE":
        raise Refused("RESOURCE_POLICY_QUIESCENCE_MISMATCH")
    if type(resources["descendants_started"]) is not int or resources["descendants_started"] != 0:
        raise Refused("RESOURCE_POLICY_DESCENDANTS_INVALID")
    collector = receipt["collector"]
    if not isinstance(collector, dict) or set(collector) != {"id", "version", "run_ref"}:
        raise Refused("COLLECTOR_SHAPE_INVALID")
    if collector["id"] != "BRAIN_EFFECT_BOUND_CARRIER_TRUSTED_PARENT_V1" or collector["version"] != "1":
        raise Refused("COLLECTOR_IDENTITY_MISMATCH")
    if collector["run_ref"] != expected["run_refs"]["collector"]:
        raise Refused("COLLECTOR_RUN_REF_MISMATCH")
    producer = receipt["producer"]
    if not isinstance(producer, dict) or set(producer) != {
        "kind",
        "run_ref",
        "open_model_solve_invoked",
        "runtime_model_calls",
        "runtime_network_calls",
    }:
        raise Refused("PRODUCER_SHAPE_INVALID")
    if producer["kind"] != "IN_PROCESS_TRUSTED_FIXTURE":
        raise Refused("PRODUCER_KIND_MISMATCH")
    if producer["run_ref"] != expected["run_refs"]["producer"]:
        raise Refused("PRODUCER_RUN_REF_MISMATCH")
    if (
        producer["open_model_solve_invoked"] is not False
        or type(producer["runtime_model_calls"]) is not int
        or producer["runtime_model_calls"] != 0
        or type(producer["runtime_network_calls"]) is not int
        or producer["runtime_network_calls"] != 0
    ):
        raise Refused("PRODUCER_MODEL_OR_NETWORK_NOT_ZERO")
    verifier = receipt["verifier"]
    if not isinstance(verifier, dict) or set(verifier) != {
        "id",
        "version",
        "script_relpath",
        "script_sha256",
        "ticket_run_ref",
        "run_ref_policy",
    }:
        raise Refused("VERIFIER_SHAPE_INVALID")
    if verifier["id"] != VERIFIER_ID or verifier["version"] != VERIFIER_VERSION:
        raise Refused("VERIFIER_IDENTITY_MISMATCH")
    if verifier["script_relpath"] != VERIFIER_RELPATH:
        raise Refused("VERIFIER_RELPATH_MISMATCH")
    if verifier["script_sha256"] != actual_script_sha or verifier["script_sha256"] != expected["verifier_script_sha256"]:
        raise Refused("VERIFIER_SCRIPT_DIGEST_MISMATCH")
    if verifier["ticket_run_ref"] != expected["run_refs"]["verifier_ticket"]:
        raise Refused("VERIFIER_TICKET_RUN_REF_MISMATCH")
    if verifier["run_ref_policy"] != "SEPARATE_PROCESS_SUPPLIED":
        raise Refused("VERIFIER_RUN_REF_POLICY_INVALID")
    worker = receipt["worker"]
    if not isinstance(worker, dict) or set(worker) != {
        "exit_status",
        "wall_s",
        "descendants_started",
        "quiescence_observed",
        "cleanup_outcome",
    }:
        raise Refused("WORKER_SHAPE_INVALID")
    if worker["exit_status"] != "RETURNED" or worker["cleanup_outcome"] != "TEMP_TREE_REMOVED":
        raise Refused("WORKER_CLEANUP_NOT_VERIFIED")
    if type(worker["descendants_started"]) is not int or worker["descendants_started"] != 0:
        raise Refused("WORKER_DESCENDANTS_INVALID")
    if worker["quiescence_observed"] is not True:
        raise Refused("WORKER_QUIESCENCE_NOT_OBSERVED")
    if not isinstance(worker["wall_s"], (int, float)) or isinstance(worker["wall_s"], bool) or worker["wall_s"] < 0:
        raise Refused("WORKER_WALL_TIME_INVALID")
    declared = receipt["declared_effect_paths"]
    if not isinstance(declared, list) or declared != sorted(declared) or len(set(declared)) != len(declared):
        raise Refused("DECLARED_EFFECT_SET_INVALID")
    declared_tuple = tuple(safe_path(path) for path in declared)
    if declared_tuple != tuple(sorted(effect_bytes)) or declared_tuple != tuple(expected["effect_paths"]):
        raise Refused("EFFECT_SET_MISMATCH")
    effects = receipt["effects"]
    if not isinstance(effects, dict) or set(effects) != set(declared_tuple):
        raise Refused("EFFECT_MANIFEST_SHAPE_INVALID")
    total = 0
    for path in declared_tuple:
        meta = effects[path]
        data = effect_bytes[path]
        if not isinstance(meta, dict) or set(meta) != {"size", "sha256"}:
            raise Refused("EFFECT_METADATA_INVALID")
        if not isinstance(data, bytes) or len(data) > MAX_EFFECT_BYTES or b"\x00" in data:
            raise Refused("EFFECT_BYTES_INVALID")
        total += len(data)
        if total > MAX_EFFECT_TOTAL_BYTES:
            raise Refused("EFFECT_BYTES_TOO_LARGE")
        if type(meta["size"]) is not int or meta["size"] != len(data):
            raise Refused("EFFECT_SIZE_MISMATCH")
        actual_hash = sha256_hex(data)
        if meta["sha256"] != actual_hash or expected["effect_sha256s"][path] != actual_hash:
            raise Refused("EFFECT_DIGEST_MISMATCH")
    if receipt["exact_patch_path"] != expected["patch_path"]:
        raise Refused("PATCH_PATH_MISMATCH")
    patch = effect_bytes[expected["patch_path"]]
    if sha256_hex(patch) != expected["patch_sha256"]:
        raise Refused("PATCH_DIGEST_MISMATCH")
    if receipt["canonicalization"] != {
        "algorithm": "JSON_SORT_KEYS_COMPACT_UTF8",
        "digest": "SHA256_OVER_CANONICAL_RECEIPT_BYTES",
    }:
        raise Refused("CANONICALIZATION_MISMATCH")
    authority = receipt["authority"]
    if not isinstance(authority, dict) or set(authority) != {
        "carrier_qualified",
        "execution_authorized",
        "patch_published",
        "independent_verification",
        "publication_authority",
    }:
        raise Refused("AUTHORITY_SHAPE_INVALID")
    if any(authority[key] is not False for key in ("carrier_qualified", "execution_authorized", "patch_published", "publication_authority")):
        raise Refused("AUTHORITY_FIELD_NOT_FALSE")
    if authority["independent_verification"] != "SEPARATE_PROCESS_REQUIRED":
        raise Refused("AUTHORITY_INDEPENDENCE_FIELD_INVALID")
    truth = receipt["truth"]
    if not isinstance(truth, dict) or set(truth) != {
        "acceptance_credit_delta",
        "section_6",
        "completion_claim",
        "truth_achieved",
        "own_weights",
        "written_to_weights",
    }:
        raise Refused("TRUTH_SHAPE_INVALID")
    if type(truth["acceptance_credit_delta"]) is not int or truth["acceptance_credit_delta"] != 0:
        raise Refused("TRUTH_FIELD_INVALID")
    if truth["section_6"] != "NOT_DONE":
        raise Refused("TRUTH_FIELD_INVALID")
    if any(truth[key] is not False for key in ("completion_claim", "truth_achieved", "own_weights", "written_to_weights")):
        raise Refused("TRUTH_FIELD_NOT_FALSE")
    return declared_tuple


def _validate_baseline(baseline: dict[str, Any], expected_digest: str) -> tuple[dict[str, bytes], tuple[str, ...]]:
    if not isinstance(baseline, dict) or set(baseline) != {"directories", "files", "sha256"}:
        raise Refused("BASELINE_SHAPE_INVALID")
    directories = baseline["directories"]
    if not isinstance(directories, list) or any(not isinstance(path, str) for path in directories):
        raise Refused("BASELINE_DIRECTORIES_INVALID")
    directories = tuple(safe_path(path) for path in directories)
    files = _decode_bytes_map(baseline["files"], label="BASELINE")
    total = 0
    for path, data in files.items():
        if len(data) > MAX_EFFECT_BYTES or b"\x00" in data:
            raise Refused("BASELINE_BYTES_INVALID")
        total += len(data)
        if total > MAX_BASELINE_TOTAL_BYTES:
            raise Refused("BASELINE_BYTES_TOO_LARGE")
    expected_dirs = _expected_directories(tuple(files))
    if directories != expected_dirs:
        raise Refused("BASELINE_DIRECTORY_SET_MISMATCH")
    digest = _digest_tree(expected_dirs, files)
    if baseline["sha256"] != digest or digest != expected_digest:
        raise Refused("BASELINE_DIGEST_MISMATCH")
    return files, expected_dirs


def _write_tree(root: Path, directories: tuple[str, ...], files: dict[str, bytes]) -> None:
    for directory in sorted(directories, key=lambda path: (path.count("/"), path)):
        (root / directory).mkdir(parents=True, exist_ok=True)
    for path, data in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def _snapshot_regular_tree(root: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}

    def walk(directory: Path, prefix: str) -> None:
        with os.scandir(directory) as stream:
            entries = sorted(stream, key=lambda entry: entry.name)
        for entry in entries:
            if not prefix and entry.name == ".git":
                continue
            rel = prefix + "/" + entry.name if prefix else entry.name
            safe_path(rel)
            before = entry.stat(follow_symlinks=False)
            if stat.S_ISDIR(before.st_mode):
                walk(Path(entry.path), rel)
            elif stat.S_ISREG(before.st_mode):
                if before.st_nlink != 1:
                    raise Refused("HARDLINK_OR_SPECIAL_IN_REPLAY")
                data = Path(entry.path).read_bytes()
                after = entry.stat(follow_symlinks=False)
                if _identity(before) != _identity(after) or len(data) != after.st_size:
                    raise Refused("REPLAY_TREE_CHANGED_DURING_READ")
                files[rel] = data
            else:
                raise Refused("SYMLINK_OR_SPECIAL_IN_REPLAY")

    walk(root, "")
    return files


def _git(args: list[str], *, cwd: Path, home: Path, input_bytes: bytes | None = None) -> bytes:
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
        "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
    }
    cmd = ["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false", *args]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Refused("GIT_UNAVAILABLE") from exc
    if proc.returncode != 0:
        raise Refused("GIT_FAILED:" + proc.stderr.decode("utf-8", "replace")[:200])
    return proc.stdout


def _replay_patch(
    patch: bytes,
    baseline_files: dict[str, bytes],
    baseline_directories: tuple[str, ...],
    expected_post: dict[str, bytes],
) -> None:
    with tempfile.TemporaryDirectory(prefix="effect_bound_independent_replay_") as temp:
        root = Path(temp)
        _write_tree(root, baseline_directories, baseline_files)
        _git(["init", "-q"], cwd=root, home=root)
        _git(["add", "-A"], cwd=root, home=root)
        _git(
            [
                "-c",
                "user.name=Effect Bound Verifier",
                "-c",
                "user.email=verifier@example.invalid",
                "commit",
                "-qm",
                "immutable baseline",
            ],
            cwd=root,
            home=root,
        )
        _git(["apply", "--check", "-p1", "-"], cwd=root, home=root, input_bytes=patch)
        _git(["apply", "-p1", "-"], cwd=root, home=root, input_bytes=patch)
        replayed = _snapshot_regular_tree(root)
        if replayed != expected_post:
            raise Refused("PATCH_DOES_NOT_REPRODUCE_DECLARED_EFFECTS")


def verify(raw_packet: bytes) -> dict[str, Any]:
    if not raw_packet or len(raw_packet) > MAX_PACKET_BYTES:
        raise Refused("VERIFIER_PACKET_BYTES_INVALID")
    try:
        packet = json.loads(raw_packet.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise Refused("VERIFIER_PACKET_JSON_INVALID") from exc
    if not isinstance(packet, dict) or set(packet) != PACKET_KEYS or packet["schema"] != PACKET_SCHEMA:
        raise Refused("VERIFIER_PACKET_SHAPE_INVALID")
    if canonical_bytes(packet) != raw_packet:
        raise Refused("VERIFIER_PACKET_NOT_CANONICAL")
    try:
        receipt_bytes = base64.b64decode(packet["receipt_bytes_b64"], validate=True)
        receipt = json.loads(receipt_bytes.decode("utf-8"))
    except (binascii.Error, ValueError, UnicodeError) as exc:
        raise Refused("RECEIPT_BYTES_INVALID") from exc
    if not isinstance(receipt, dict):
        raise Refused("RECEIPT_NOT_OBJECT")
    for key in (
        "expected_receipt_sha256",
        "expected_runtime_policy_sha256",
        "expected_input_snapshot_sha256",
        "expected_patch_sha256",
        "expected_verifier_script_sha256",
    ):
        if not isinstance(packet[key], str) or not _HEX64.fullmatch(packet[key]):
            raise Refused("EXPECTED_DIGEST_INVALID")
    expected_effect_paths = packet["expected_effect_paths"]
    if not isinstance(expected_effect_paths, list) or expected_effect_paths != sorted(expected_effect_paths):
        raise Refused("EXPECTED_EFFECT_SET_INVALID")
    expected_effect_paths = tuple(safe_path(path) for path in expected_effect_paths)
    if len(set(expected_effect_paths)) != len(expected_effect_paths):
        raise Refused("EXPECTED_EFFECT_SET_DUPLICATE")
    expected_effect_sha256s = packet["expected_effect_sha256s"]
    if not isinstance(expected_effect_sha256s, dict) or set(expected_effect_sha256s) != set(expected_effect_paths):
        raise Refused("EXPECTED_EFFECT_HASH_SET_INVALID")
    if any(not isinstance(value, str) or not _HEX64.fullmatch(value) for value in expected_effect_sha256s.values()):
        raise Refused("EXPECTED_EFFECT_HASH_INVALID")
    run_refs = packet["run_refs"]
    if not isinstance(run_refs, dict) or set(run_refs) != {"producer", "collector", "verifier_ticket"}:
        raise Refused("RUN_REFS_SHAPE_INVALID")
    if any(not isinstance(value, str) or not _HEX16.fullmatch(value) for value in run_refs.values()):
        raise Refused("RUN_REF_INVALID")
    if len(set(run_refs.values())) != 3:
        raise Refused("RUN_REFERENCE_COLLISION")
    if packet["expected_patch_path"] != "model.patch":
        raise Refused("EXPECTED_PATCH_PATH_INVALID")
    if not isinstance(packet["expected_run_id"], str) or not packet["expected_run_id"]:
        raise Refused("EXPECTED_RUN_ID_INVALID")
    if not isinstance(packet["expected_base_commit"], str) or not _COMMIT.fullmatch(packet["expected_base_commit"]):
        raise Refused("EXPECTED_BASE_COMMIT_INVALID")
    script_path = Path(__file__).resolve(strict=True)
    actual_script_sha = sha256_hex(script_path.read_bytes())
    if actual_script_sha != packet["expected_verifier_script_sha256"]:
        raise Refused("VERIFIER_SCRIPT_DIGEST_MISMATCH")
    effect_bytes = _decode_bytes_map(packet["effects"], label="EFFECT")
    if set(effect_bytes) != set(expected_effect_paths):
        raise Refused("EFFECT_SET_MISMATCH")
    baseline_files, baseline_directories = _validate_baseline(packet["baseline"], packet["expected_input_snapshot_sha256"])
    expected = {
        "receipt_sha256": packet["expected_receipt_sha256"],
        "run_id": packet["expected_run_id"],
        "base_commit": packet["expected_base_commit"],
        "runtime_policy_sha256": packet["expected_runtime_policy_sha256"],
        "input_snapshot_sha256": packet["expected_input_snapshot_sha256"],
        "effect_paths": expected_effect_paths,
        "effect_sha256s": dict(sorted(expected_effect_sha256s.items())),
        "patch_path": packet["expected_patch_path"],
        "patch_sha256": packet["expected_patch_sha256"],
        "verifier_script_sha256": packet["expected_verifier_script_sha256"],
        "run_refs": run_refs,
    }
    _validate_receipt(
        receipt,
        raw_receipt_bytes=receipt_bytes,
        expected=expected,
        baseline_digest=packet["expected_input_snapshot_sha256"],
        effect_bytes=effect_bytes,
        actual_script_sha=actual_script_sha,
    )
    patch = effect_bytes[expected["patch_path"]]
    patch_paths = parse_patch_paths(patch)
    changed: dict[str, bytes] = {}
    deleted: dict[str, bytes] = {}
    for effect_path, data in effect_bytes.items():
        if effect_path == expected["patch_path"]:
            continue
        if effect_path.startswith("files/"):
            suffix = safe_path(effect_path[len("files/") :])
            if suffix in deleted:
                raise Refused("EFFECT_PATH_CLASS_CONFLICT")
            changed[suffix] = data
        elif effect_path.startswith("deleted/"):
            suffix = safe_path(effect_path[len("deleted/") :])
            if suffix in changed:
                raise Refused("EFFECT_PATH_CLASS_CONFLICT")
            deleted[suffix] = data
        else:
            raise Refused("EFFECT_PATH_CLASS_UNSUPPORTED")
    if set(patch_paths) != set(changed) | set(deleted):
        raise Refused("PATCH_EFFECT_PATH_SET_MISMATCH")
    expected_post = dict(baseline_files)
    for path, data in deleted.items():
        if path not in expected_post or expected_post[path] != data:
            raise Refused("DELETED_BASE_BYTES_MISMATCH")
        del expected_post[path]
    for path, data in changed.items():
        expected_post[path] = data
    _replay_patch(patch, baseline_files, baseline_directories, expected_post)
    verifier_run_ref = secrets.token_hex(8)
    if verifier_run_ref in set(run_refs.values()):
        raise Refused("VERIFIER_RUN_REFERENCE_COLLISION")
    return {
        "status": "INDEPENDENT_EFFECT_BYTES_VERIFIED",
        "verifier_id": VERIFIER_ID,
        "verifier_version": VERIFIER_VERSION,
        "verifier_run_ref": verifier_run_ref,
        "verifier_pid": os.getpid(),
        "packet_sha256": sha256_hex(raw_packet),
        "receipt_sha256": sha256_hex(receipt_bytes),
        "effect_sha256s": {path: sha256_hex(data) for path, data in sorted(effect_bytes.items())},
        "patch_sha256": sha256_hex(patch),
        "baseline_sha256": packet["expected_input_snapshot_sha256"],
        "patch_paths": list(patch_paths),
        "git_apply_check_passed": True,
        "patch_replay_ok": True,
        "verifier_script_sha256": actual_script_sha,
        "receipt_verified": True,
        "independent_process_verification": True,
        "independent_attestation": False,
        "carrier_qualified": False,
        "execution_authorized": False,
        "patch_published": False,
        "publication_authority": False,
        "acceptance_credit_delta": 0,
        "section_6": "NOT_DONE",
        "completion_claim": False,
        "truth_achieved": False,
    }


def main() -> int:
    try:
        raw = sys.stdin.buffer.read(MAX_PACKET_BYTES + 1)
        result = verify(raw)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Refused as exc:
        print(
            json.dumps(
                {
                    "status": "REFUSED",
                    "reason": str(exc),
                    "verifier_id": VERIFIER_ID,
                    "execution_authorized": False,
                    "carrier_qualified": False,
                },
                sort_keys=True,
            )
        )
        return 0
    except Exception as exc:  # fail closed without leaking a traceback as a pass
        print(
            json.dumps(
                {
                    "status": "CRASH",
                    "reason": type(exc).__name__ + ":" + str(exc)[:200],
                    "execution_authorized": False,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
