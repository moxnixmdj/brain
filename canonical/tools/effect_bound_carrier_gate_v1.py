"""Formal runner for the effect-bound carrier gate; progress evidence only.

This tool creates five synthetic fixtures from real repository source files,
runs a deterministic in-process producer, collects immutable effect bytes, and
asks a separate Python verifier to recompute the receipt, patch applicability,
and patch replay from those bytes. It also exercises preregistered refusals and
external-store editability. It writes one canonical receipt and one external
store pointer. It publishes no patch, calls no model, uses no nested namespace,
claims no benchmark score, and keeps the front door closed.
"""
from __future__ import annotations

import argparse
import copy
import difflib
import hashlib
import json
import os
from pathlib import Path
import platform
import secrets
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable

from canonical.runtime import effect_bound_carrier_gate_v1 as gate
from canonical.tools import effect_bound_carrier_independent_verifier_v1 as independent

RECEIPT_SCHEMA = "BRAIN_EFFECT_BOUND_CARRIER_GATE_FORMAL_RECEIPT_V1"
DEFAULT_RECEIPT_RELPATH = "canonical/verification/EFFECT_BOUND_CARRIER_GATE_20261124_V1.json"
DEFAULT_STORE_RELPATH = "canonical/astra_runtime/state/EFFECT_BOUND_CARRIER_GATE_V1.json"
PREREG_RELPATH = "EFFECT_BOUND_CARRIER_PREREG_20261124_V1.md"
SYSTEM_DATE_UTC = "2026-11-24"
MARKER = b"# synthetic effect-bound carrier fixture marker\n"
ADDED_TEXT = b"# synthetic added effect file\n"
EXTRA_TEXT = b"# synthetic mixed fixture addition\n"

FIXTURES: tuple[dict[str, Any], ...] = (
    {
        "id": "F1_MODIFY",
        "sources": ("canonical/runtime/active_question_v1.py",),
        "mutations": ({"op": "modify", "path": "canonical/runtime/active_question_v1.py"},),
    },
    {
        "id": "F2_ADD",
        "sources": ("canonical/runtime/settlement_v1.py",),
        "mutations": ({"op": "add", "path": "carrier_fixture_notes.txt", "data": ADDED_TEXT},),
    },
    {
        "id": "F3_DELETE",
        "sources": ("canonical/runtime/guide_precondition_v1.py",),
        "mutations": ({"op": "delete", "path": "canonical/runtime/guide_precondition_v1.py"},),
    },
    {
        "id": "F4_MULTI_MODIFY",
        "sources": (
            "canonical/swe_kernel/perfect_algorithm_v1.py",
            "canonical/runtime/environment_learning_v1.py",
        ),
        "mutations": (
            {"op": "modify", "path": "canonical/swe_kernel/perfect_algorithm_v1.py"},
            {"op": "modify", "path": "canonical/runtime/environment_learning_v1.py"},
        ),
    },
    {
        "id": "F5_MIXED",
        "sources": (
            "canonical/tools/one_experience_cross_family_transfer_v1.py",
            "canonical/runtime/contrast_selection_v1.py",
        ),
        "mutations": (
            {"op": "modify", "path": "canonical/tools/one_experience_cross_family_transfer_v1.py"},
            {"op": "add", "path": "carrier_fixture_extra.txt", "data": EXTRA_TEXT},
            {"op": "delete", "path": "canonical/runtime/contrast_selection_v1.py"},
        ),
    },
)


class ToolRefused(ValueError):
    pass


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_source_bytes(data: bytes) -> bytes:
    if b"\x00" in data:
        raise ToolRefused("SOURCE_CONTAINS_NUL")
    try:
        text = data.decode("utf-8")
    except UnicodeError as exc:
        raise ToolRefused("SOURCE_NOT_UTF8") from exc
    if "\r" in text:
        raise ToolRefused("SOURCE_CR_UNSUPPORTED")
    if text and not text.endswith("\n"):
        text += "\n"
    return text.encode("utf-8")


def modified_bytes(data: bytes) -> bytes:
    if not data.endswith(b"\n"):
        data += b"\n"
    return data + MARKER


def write_tree(root: Path, files: dict[str, bytes]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for path, data in files.items():
        gate.safe_relative_path(path)
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def prune_empty_dirs(root: Path) -> None:
    for directory, _, _ in os.walk(root, topdown=False):
        path = Path(directory)
        if path != root and not any(path.iterdir()):
            path.rmdir()


def make_patch(before: dict[str, bytes], after: dict[str, bytes]) -> bytes:
    chunks: list[str] = []
    for path in sorted(set(before) | set(after)):
        gate.safe_relative_path(path)
        old = before.get(path, b"")
        new = after.get(path, b"")
        if old == new:
            continue
        if b"\x00" in old or b"\x00" in new:
            raise ToolRefused("PATCH_SOURCE_CONTAINS_NUL")
        try:
            old_text = old.decode("utf-8")
            new_text = new.decode("utf-8")
        except UnicodeError as exc:
            raise ToolRefused("PATCH_SOURCE_NOT_UTF8") from exc
        if (old_text and not old_text.endswith("\n")) or (new_text and not new_text.endswith("\n")):
            raise ToolRefused("PATCH_SOURCE_NOT_NEWLINE_TERMINATED")
        if "\r" in old_text or "\r" in new_text:
            raise ToolRefused("PATCH_SOURCE_CR_UNSUPPORTED")
        chunks.append("diff --git a/" + path + " b/" + path + "\n")
        if path not in before:
            chunks.append("new file mode 100644\n")
        elif path not in after:
            chunks.append("deleted file mode 100644\n")
        chunks.extend(
            difflib.unified_diff(
                old_text.splitlines(keepends=True),
                new_text.splitlines(keepends=True),
                fromfile="/dev/null" if path not in before else "a/" + path,
                tofile="/dev/null" if path not in after else "b/" + path,
                n=3,
            )
        )
    return "".join(chunks).encode("utf-8")


def materialize_fixture(fixture: dict[str, Any], root: Path, repo_root: Path) -> dict[str, Any]:
    before: dict[str, bytes] = {}
    source_meta: list[dict[str, Any]] = []
    for rel in fixture["sources"]:
        original = (repo_root / rel).read_bytes()
        normalized = normalize_source_bytes(original)
        before[rel] = normalized
        source_meta.append(
            {
                "path": rel,
                "source_sha256": sha256_hex(original),
                "baseline_sha256": sha256_hex(normalized),
                "normalized_newline_appended": original != normalized,
            }
        )
    input_root = root / "input"
    worktree = root / "worktree"
    effects_root = root / "effects"
    write_tree(input_root, before)
    write_tree(worktree, before)
    started = time.perf_counter()
    after = dict(before)
    for mutation in fixture["mutations"]:
        op = mutation["op"]
        path = mutation["path"]
        gate.safe_relative_path(path)
        if op == "modify":
            if path not in after:
                raise ToolRefused("MODIFY_PATH_MISSING")
            after[path] = modified_bytes(after[path])
            (worktree / path).write_bytes(after[path])
        elif op == "add":
            if path in after:
                raise ToolRefused("ADD_PATH_ALREADY_EXISTS")
            data = mutation["data"]
            if not isinstance(data, bytes) or not data or b"\x00" in data or not data.endswith(b"\n") or b"\r" in data:
                raise ToolRefused("ADDED_BYTES_INVALID")
            after[path] = data
            (worktree / path).parent.mkdir(parents=True, exist_ok=True)
            (worktree / path).write_bytes(data)
        elif op == "delete":
            if path not in after:
                raise ToolRefused("DELETE_PATH_MISSING")
            del after[path]
            (worktree / path).unlink()
        else:
            raise ToolRefused("MUTATION_OP_UNSUPPORTED")
    prune_empty_dirs(worktree)
    after_files = gate.collect_snapshot(worktree)["files"]
    worker_wall_s = time.perf_counter() - started
    patch = make_patch(before, after_files)
    if not patch:
        raise ToolRefused("EMPTY_PATCH")
    effect_files: dict[str, bytes] = {gate.PATCH_EFFECT: patch}
    for path in sorted(set(before) | set(after_files)):
        if path not in before or before[path] != after_files.get(path, b""):
            if path in after_files:
                effect_files["files/" + path] = after_files[path]
        if path in before and path not in after_files:
            effect_files["deleted/" + path] = before[path]
    write_tree(effects_root, effect_files)
    baseline = gate.collect_snapshot(input_root)
    effect_collection = gate.collect_snapshot(effects_root)
    declared = tuple(sorted(effect_collection["files"]))
    gate.validate_effects(effect_collection, declared)
    return {
        "baseline": baseline,
        "effect_collection": effect_collection,
        "effect_bytes": dict(effect_collection["files"]),
        "declared_effect_paths": declared,
        "patch_bytes": patch,
        "patch_nonempty": bool(patch),
        "patch_byte_length": len(patch),
        "source_meta": source_meta,
        "mutation_kinds": [mutation["op"] for mutation in fixture["mutations"]],
        "worker_wall_s": worker_wall_s,
    }


def measure_git_state(repo_root: Path) -> dict[str, Any]:
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(repo_root),
        "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
    }
    base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(repo_root), env=env, text=True).strip()
    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=str(repo_root), env=env, text=True
    ).strip()
    status = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all"], cwd=str(repo_root), env=env
    )
    return {
        "base_commit": base,
        "branch": branch,
        "dirty_tree_sha256": sha256_hex(status),
        "dirty_tree_line_count": len(status.splitlines()),
    }


def new_run_refs() -> tuple[str, str, str]:
    while True:
        refs = (secrets.token_hex(8), secrets.token_hex(8), secrets.token_hex(8))
        if len(set(refs)) == 3:
            return refs


def run_fixture(
    fixture: dict[str, Any],
    *,
    repo_root: Path,
    code_root: Path | None,
    git_state: dict[str, Any],
    python_version: str,
    runner_source_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    holder = tempfile.TemporaryDirectory(prefix="brain_effect_bound_gate_")
    root = Path(holder.name)
    verifier_code_root = Path(code_root or repo_root)
    try:
        material = materialize_fixture(fixture, root, repo_root)
    finally:
        holder.cleanup()
    cleanup_outcome = "TEMP_TREE_REMOVED" if not root.exists() else "CLEANUP_UNVERIFIED"
    producer_ref, collector_ref, ticket_ref = new_run_refs()
    run_id = "EBCG-" + secrets.token_hex(8)
    request = {
        "fixture_id": fixture["id"],
        "source_paths": list(fixture["sources"]),
        "mutation_kinds": list(material["mutation_kinds"]),
    }
    gate_result = gate.gate_from_collection(
        request=request,
        baseline=material["baseline"],
        effect_collection=material["effect_collection"],
        declared_effect_paths=material["declared_effect_paths"],
        fixture_id=fixture["id"],
        run_id=run_id,
        base_commit=git_state["base_commit"],
        dirty_tree_sha256=git_state["dirty_tree_sha256"],
        python_version=python_version,
        runner_source_sha256=runner_source_sha256,
        producer_run_ref=producer_ref,
        collector_run_ref=collector_ref,
        verifier_ticket_run_ref=ticket_ref,
        worker_wall_s=material["worker_wall_s"],
        cleanup_outcome=cleanup_outcome,
        code_root=verifier_code_root,
    )
    return material, gate_result


def prepare_store(
    store_path: Path,
    *,
    repo_root: Path,
    receipt_relpath: str,
) -> dict[str, Any]:
    module_sha = sha256_hex(Path(gate.__file__).resolve(strict=True).read_bytes())
    _, script, script_sha = gate._script_path(repo_root)
    document = gate.store_document(
        module_sha256=module_sha,
        verifier_script_sha256=script_sha,
        receipt_relpath=receipt_relpath,
    )
    canonical = gate.canonical_bytes(document)
    created = False
    if not store_path.is_file():
        store_path.parent.mkdir(parents=True, exist_ok=True)
        store_path.write_bytes(canonical)
        created = True
    verified = gate.verify_store(
        store_path,
        module_sha256=module_sha,
        verifier_script_sha256=script_sha,
    )
    store_bytes = store_path.read_bytes()
    restart = gate.restart_store_digest(store_bytes, code_root=repo_root)
    restart_digest_match = (
        restart["store_sha256"] == verified["store_sha256"]
        and restart["canonical_sha256"] == verified["canonical_sha256"]
    )
    store_path.unlink()
    removal_refused = False
    removal_reason = "NO_REFUSAL"
    try:
        gate.verify_store(
            store_path,
            module_sha256=module_sha,
            verifier_script_sha256=script_sha,
        )
    except gate.GateRefused as exc:
        removal_refused = True
        removal_reason = str(exc)
    store_path.write_bytes(store_bytes)
    restored = gate.verify_store(
        store_path,
        module_sha256=module_sha,
        verifier_script_sha256=script_sha,
    )
    restore_ok = restored["store_sha256"] == verified["store_sha256"]
    return {
        "created": created,
        "status": verified["status"],
        "store_sha256": verified["store_sha256"],
        "canonical_sha256": verified["canonical_sha256"],
        "document": verified["document"],
        "module_sha256": module_sha,
        "verifier_script_sha256": script_sha,
        "restart": restart,
        "restart_digest_match": restart_digest_match,
        "store_removal_refused": removal_refused,
        "store_removal_refusal_reason": removal_reason,
        "restore_ok": restore_ok,
        "external_store_editability_ok": removal_refused and restore_ok and restart_digest_match,
    }


def _record_refusal(name: str, fn: Callable[[], Any]) -> dict[str, Any]:
    try:
        fn()
    except (gate.GateRefused, independent.Refused) as exc:
        return {"name": name, "refused": True, "reason": str(exc)[:240], "kind": type(exc).__name__}
    except Exception as exc:
        return {
            "name": name,
            "refused": False,
            "reason": "UNEXPECTED_" + type(exc).__name__ + ":" + str(exc)[:200],
            "kind": type(exc).__name__,
        }
    return {"name": name, "refused": False, "reason": "NO_REFUSAL", "kind": "NONE"}


def run_negative_cases(
    material: dict[str, Any],
    gate_result: dict[str, Any],
    *,
    repo_root: Path,
    base_commit: str,
) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    baseline = material["baseline"]
    effect_collection = material["effect_collection"]
    declared = material["declared_effect_paths"]
    base_effects = material["effect_bytes"]
    base_receipt = gate_result["receipt"]
    base_receipt_sha = gate_result["receipt_sha256"]
    base_effect_hashes = gate_result["effect_sha256s"]
    base_patch_sha = gate_result["patch_sha256"]
    run_refs = gate_result["run_references"]
    expected_args = {
        "expected_effect_paths": declared,
        "expected_effect_sha256s": base_effect_hashes,
        "expected_patch_sha256": base_patch_sha,
        "expected_run_id": base_receipt["run_id"],
        "expected_base_commit": base_commit,
        "expected_runtime_policy_sha256": base_receipt["runtime_policy_sha256"],
        "producer_run_ref": run_refs["producer"],
        "collector_run_ref": run_refs["collector"],
        "verifier_ticket_run_ref": run_refs["verifier_ticket"],
        "code_root": repo_root,
    }

    def call_verifier(
        *,
        receipt_mutator: Callable[[dict[str, Any]], None] | None = None,
        effect_mutator: Callable[[dict[str, bytes]], None] | None = None,
        rehash_receipt: bool = True,
        expected_receipt_sha256: str | None = None,
        expected_effect_sha256s: dict[str, str] | None = None,
        expected_patch_sha256: str | None = None,
        run_ref_override: tuple[str, str, str] | None = None,
    ) -> dict[str, Any]:
        receipt = copy.deepcopy(base_receipt)
        if receipt_mutator is not None:
            receipt_mutator(receipt)
        receipt_bytes = gate.canonical_bytes(receipt)
        receipt_sha = gate.sha256_hex(receipt_bytes) if rehash_receipt else base_receipt_sha
        effects = dict(base_effects)
        if effect_mutator is not None:
            effect_mutator(effects)
        refs = run_ref_override or (
            run_refs["producer"],
            run_refs["collector"],
            run_refs["verifier_ticket"],
        )
        return gate.run_independent_verifier(
            receipt_bytes=receipt_bytes,
            expected_receipt_sha256=expected_receipt_sha256 or receipt_sha,
            effect_bytes=effects,
            baseline=baseline,
            expected_effect_paths=declared,
            expected_effect_sha256s=expected_effect_sha256s or base_effect_hashes,
            expected_patch_sha256=expected_patch_sha256 or base_patch_sha,
            expected_run_id=base_receipt["run_id"],
            expected_base_commit=base_commit,
            expected_runtime_policy_sha256=base_receipt["runtime_policy_sha256"],
            producer_run_ref=refs[0],
            collector_run_ref=refs[1],
            verifier_ticket_run_ref=refs[2],
            code_root=repo_root,
        )

    def verify_with(**kwargs: Any) -> None:
        call_verifier(**kwargs)

    cases.append(
        _record_refusal(
            "caller_authority_field",
            lambda: gate.deny_caller_authority({"carrier_qualified": True, "fixture": "negative"}),
        )
    )
    cases.append(
        _record_refusal(
            "shared_run_references",
            lambda: verify_with(run_ref_override=(run_refs["producer"], run_refs["producer"], run_refs["verifier_ticket"])),
        )
    )
    cases.append(
        _record_refusal("missing_effect", lambda: gate.validate_effects(effect_collection, tuple(p for p in declared if p != gate.PATCH_EFFECT)))
    )
    cases.append(
        _record_refusal("undeclared_effect", lambda: gate.validate_effects(effect_collection, declared + ("undeclared.txt",)))
    )
    cases.append(
        _record_refusal("duplicated_effect_path", lambda: gate.validate_effects(effect_collection, declared + (declared[0],)))
    )
    cases.append(
        _record_refusal("escaping_effect_path", lambda: gate.validate_effects(effect_collection, ("../escape",)))
    )

    def filesystem_case(name: str, setup: Callable[[Path, Path], None]) -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="brain_effect_bound_negative_") as temp:
            root = Path(temp)
            effects = root / "effects"
            effects.mkdir()
            (effects / gate.PATCH_EFFECT).write_bytes(b"synthetic patch bytes\n")
            setup(effects, root)
            return _record_refusal(name, lambda: gate.collect_snapshot(effects))

    def symlink_setup(effects: Path, root: Path) -> None:
        (root / "outside").write_bytes(b"outside\n")
        (effects / "escape").symlink_to(root / "outside")

    def hardlink_setup(effects: Path, root: Path) -> None:
        first = effects / "a.txt"
        first.write_bytes(b"hardlink\n")
        os.link(first, effects / "b.txt")

    def special_setup(effects: Path, root: Path) -> None:
        os.mkfifo(effects / "pipe")

    def oversized_setup(effects: Path, root: Path) -> None:
        (effects / "big.bin").write_bytes(b"x" * (gate.LIMITS.max_file_bytes + 1))

    cases.append(filesystem_case("symlink_effect", symlink_setup))
    cases.append(filesystem_case("hardlink_effect", hardlink_setup))
    cases.append(filesystem_case("special_effect", special_setup))
    cases.append(filesystem_case("oversized_effect", oversized_setup))

    def sentinel_case() -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="brain_effect_bound_sentinel_") as temp:
            root = Path(temp)
            effects = root / "effects"
            effects.mkdir()
            (effects / gate.PATCH_EFFECT).write_bytes(b"synthetic patch bytes\n")
            sentinel = root / "outside-allocated-workspace"
            sentinel.write_bytes(b"UNCHANGED")
            collection = gate.collect_snapshot(effects)
            outside_absent = sentinel.name not in collection["files"] and sentinel.read_bytes() == b"UNCHANGED"
            return {
                "name": "sentinel_outside_allocated_workspace",
                "refused": outside_absent,
                "reason": "UNQUALIFIED_NO_AUTOMATIC_ADOPTION" if outside_absent else "SENTINEL_OBSERVED",
                "kind": "UNQUALIFIED" if outside_absent else "FAILURE",
                "unqualified": outside_absent,
            }

    cases.append(sentinel_case())
    cases.append(
        _record_refusal(
            "patch_path_traversal",
            lambda: independent.parse_patch_paths(
                b"diff --git a/../escape b/../escape\n--- /dev/null\n+++ b/../escape\n@@ -0,0 +1 @@\n+escape\n"
            ),
        )
    )

    def mutate_receipt_digest(receipt: dict[str, Any]) -> None:
        receipt["fixture_id"] = "MUTATED_RECEIPT_DIGEST"

    cases.append(
        _record_refusal(
            "mutated_receipt_digest",
            lambda: verify_with(receipt_mutator=mutate_receipt_digest, rehash_receipt=False, expected_receipt_sha256=base_receipt_sha),
        )
    )

    def mutate_patch_effect(effects: dict[str, bytes]) -> None:
        effects[gate.PATCH_EFFECT] = b"forged patch bytes\n"

    cases.append(_record_refusal("forged_patch_bytes", lambda: verify_with(effect_mutator=mutate_patch_effect)))

    def mutate_changed_effect(effects: dict[str, bytes]) -> None:
        changed = sorted(path for path in effects if path.startswith("files/"))
        if not changed:
            raise ToolRefused("NEGATIVE_FIXTURE_HAS_NO_CHANGED_EFFECT")
        effects[changed[0]] = b"forged changed bytes\n"

    cases.append(_record_refusal("forged_changed_effect_bytes", lambda: verify_with(effect_mutator=mutate_changed_effect)))

    def mutate_patch_manifest(receipt: dict[str, Any]) -> None:
        receipt["effects"][gate.PATCH_EFFECT]["sha256"] = "0" * 64

    def mutate_effect_manifest(receipt: dict[str, Any]) -> None:
        receipt["declared_effect_paths"] = [p for p in receipt["declared_effect_paths"] if p != gate.PATCH_EFFECT]

    def mutate_run_id(receipt: dict[str, Any]) -> None:
        receipt["run_id"] = "MUTATED_RUN_ID"

    def mutate_base(receipt: dict[str, Any]) -> None:
        receipt["base_commit_claim"] = "1" * 40

    def mutate_policy(receipt: dict[str, Any]) -> None:
        receipt["runtime_policy_sha256"] = "1" * 64

    def mutate_script_digest(receipt: dict[str, Any]) -> None:
        receipt["verifier"]["script_sha256"] = "2" * 64
        receipt["runtime"]["verifier_script_sha256"] = "2" * 64

    cases.append(_record_refusal("mutated_patch_manifest", lambda: verify_with(receipt_mutator=mutate_patch_manifest)))
    cases.append(_record_refusal("mutated_effect_manifest", lambda: verify_with(receipt_mutator=mutate_effect_manifest)))
    cases.append(_record_refusal("mutated_run_id", lambda: verify_with(receipt_mutator=mutate_run_id)))
    cases.append(_record_refusal("mutated_base", lambda: verify_with(receipt_mutator=mutate_base)))
    cases.append(_record_refusal("mutated_policy", lambda: verify_with(receipt_mutator=mutate_policy)))
    cases.append(_record_refusal("verifier_script_digest_mismatch", lambda: verify_with(receipt_mutator=mutate_script_digest)))
    return cases


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", default=DEFAULT_RECEIPT_RELPATH)
    parser.add_argument("--store", default=DEFAULT_STORE_RELPATH)
    return parser.parse_args(argv)


def resolve_path(repo_root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else repo_root / path


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path(__file__).resolve().parents[2]
    receipt_path = resolve_path(repo_root, args.receipt)
    store_path = resolve_path(repo_root, args.store)
    prereg_path = repo_root / PREREG_RELPATH
    errors: list[str] = []
    prereg_sha = sha256_hex(prereg_path.read_bytes())
    python_version = platform.python_version()
    runner_source_sha = sha256_hex(Path(__file__).resolve(strict=True).read_bytes())

    store_info: dict[str, Any] = {}
    try:
        store_info = prepare_store(
            store_path,
            repo_root=repo_root,
            receipt_relpath=DEFAULT_RECEIPT_RELPATH,
        )
    except Exception as exc:
        errors.append("STORE_PREPARATION_FAILED:" + type(exc).__name__ + ":" + str(exc)[:200])
        store_info = {"external_store_editability_ok": False, "status": "REFUSED"}

    git_state = measure_git_state(repo_root)
    fixture_results: list[dict[str, Any]] = []
    materials: dict[str, dict[str, Any]] = {}
    gate_results: dict[str, dict[str, Any]] = {}
    for fixture in FIXTURES:
        try:
            material, result = run_fixture(
                fixture,
                repo_root=repo_root,
                code_root=repo_root,
                git_state=git_state,
                python_version=python_version,
                runner_source_sha256=runner_source_sha,
            )
            materials[fixture["id"]] = material
            gate_results[fixture["id"]] = result
            fixture_results.append(
                {
                    "fixture_id": fixture["id"],
                    "status": result["status"],
                    "source_meta": material["source_meta"],
                    "mutation_kinds": material["mutation_kinds"],
                    "declared_effect_paths": list(material["declared_effect_paths"]),
                    "effect_count": len(material["declared_effect_paths"]),
                    "patch_nonempty": material["patch_nonempty"],
                    "patch_byte_length": material["patch_byte_length"],
                    "patch_sha256": result["patch_sha256"],
                    "receipt_sha256": result["receipt_sha256"],
                    "input_snapshot_sha256": material["baseline"]["digest"],
                    "run_references": result["run_references"],
                    "verifier": {
                        "status": result["verifier"]["status"],
                        "verifier_run_ref": result["verifier"]["verifier_run_ref"],
                        "verifier_pid": result["verifier"]["verifier_pid"],
                        "git_apply_check_passed": result["verifier"]["git_apply_check_passed"],
                        "patch_replay_ok": result["verifier"]["patch_replay_ok"],
                        "independent_attestation": result["verifier"]["independent_attestation"],
                    },
                    "receipt_verified": result["receipt_verified"],
                    "carrier_qualified": result["carrier_qualified"],
                    "execution_authorized": result["execution_authorized"],
                    "patch_published": result["patch_published"],
                }
            )
        except Exception as exc:
            errors.append("FIXTURE_FAILED:" + fixture["id"] + ":" + type(exc).__name__ + ":" + str(exc)[:200])
            fixture_results.append(
                {
                    "fixture_id": fixture["id"],
                    "status": "REFUSED",
                    "reason": type(exc).__name__ + ":" + str(exc)[:200],
                    "receipt_verified": False,
                    "patch_nonempty": False,
                    "run_references": {},
                }
            )

    negative_cases: list[dict[str, Any]] = []
    if FIXTURES[0]["id"] in materials and FIXTURES[0]["id"] in gate_results:
        try:
            negative_cases = run_negative_cases(
                materials[FIXTURES[0]["id"]],
                gate_results[FIXTURES[0]["id"]],
                repo_root=repo_root,
                base_commit=git_state["base_commit"],
            )
        except Exception as exc:
            errors.append("NEGATIVE_CASES_FAILED:" + type(exc).__name__ + ":" + str(exc)[:200])
            negative_cases = [{"name": "NEGATIVE_CASE_HARNESS", "refused": False, "reason": str(exc)[:200]}]
    else:
        negative_cases = [{"name": "NO_SUCCESSFUL_FIRST_FIXTURE", "refused": False, "reason": "NEGATIVE_CASES_SKIPPED"}]

    all_refs = {
        ref
        for row in fixture_results
        for ref in row.get("run_references", {}).values()
    }
    restart_ref = store_info.get("restart", {}).get("restart_run_ref")
    restart_ref_distinct = isinstance(restart_ref, str) and restart_ref not in all_refs
    fixture_verifier_refs = [
        row.get("verifier", {}).get("verifier_run_ref") for row in fixture_results if row.get("receipt_verified")
    ]
    distinct_verifier_refs = len(fixture_verifier_refs) == len(FIXTURES) and len(set(fixture_verifier_refs)) == len(FIXTURES)
    negative_cases_all_refused = bool(negative_cases) and all(case["refused"] for case in negative_cases)
    all_fixture_receipts_verified = all(row.get("receipt_verified") is True for row in fixture_results)
    non_empty_patch_count = sum(1 for row in fixture_results if row.get("patch_nonempty") is True)
    external_store_ok = store_info.get("external_store_editability_ok") is True
    restart_digest_match = store_info.get("restart_digest_match") is True
    gate_pass = (
        not errors
        and len(fixture_results) == len(FIXTURES)
        and all_fixture_receipts_verified
        and non_empty_patch_count >= 1
        and distinct_verifier_refs
        and negative_cases_all_refused
        and external_store_ok
        and restart_digest_match
        and restart_ref_distinct
    )
    verdict = {
        "gate_pass": gate_pass,
        "fixture_count": len(fixture_results),
        "all_fixture_receipts_verified": all_fixture_receipts_verified,
        "non_empty_patch_count": non_empty_patch_count,
        "independent_verifier_process_count": len(fixture_verifier_refs),
        "distinct_verifier_run_refs": distinct_verifier_refs,
        "negative_case_count": len(negative_cases),
        "negative_cases_all_refused": negative_cases_all_refused,
        "external_store_editability_ok": external_store_ok,
        "restart_digest_match": restart_digest_match,
        "restart_run_ref_distinct": restart_ref_distinct,
        "carrier_qualified": False,
        "execution_authorized": False,
        "patch_published": False,
        "no_automatic_adoption": True,
        "independent_attestation": False,
        "independent_cloud_verifier": False,
        "gui_dom_oracle": False,
        "hardest_open_nov_2026_score": "NO_SCORE",
        "acceptance_credit_delta": 0,
        "section_6": "NOT_DONE",
        "completion_claim": False,
        "truth_achieved": False,
        "own_weights": False,
        "written_to_weights": False,
        "runtime_model_calls": 0,
        "runtime_network_calls": 0,
    }
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "date_utc": SYSTEM_DATE_UTC,
        "branch": git_state["branch"],
        "base_commit": git_state["base_commit"],
        "dirty_tree_sha256": git_state["dirty_tree_sha256"],
        "dirty_tree_line_count": git_state["dirty_tree_line_count"],
        "prereg_path": PREREG_RELPATH,
        "prereg_sha256": prereg_sha,
        "prereg_amended_before_formal_run": True,
        "python_version": python_version,
        "runner_source_sha256": runner_source_sha,
        "receipt_path": str(receipt_path.relative_to(repo_root)) if receipt_path.is_relative_to(repo_root) else str(receipt_path),
        "external_store": store_info,
        "fixtures": fixture_results,
        "negative_cases": negative_cases,
        "errors": errors,
        "verdict": verdict,
        "physical_cost_blocker_logged_once": "DOCKER_PODMAN_HARBOR_PY312_DISPOSABLE_VM_GPU_UNAVAILABLE",
        "next_bottleneck": "REVIEWED_CONTAINER_LOCAL_OPEN_MODEL_SOLVE_CARRIER_WITH_REAL_ISOLATION_QUIESCENCE_CLEANUP_AND_INDEPENDENT_CLOUD_VERIFIER",
        "research_inputs_are_not_runtime_dependencies": True,
        "build_time_web_research_only": True,
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_bytes(gate.canonical_bytes(receipt))
    summary = {
        "status": "EFFECT_BOUND_GATE_PASS__PROGRESS_ONLY" if gate_pass else "EFFECT_BOUND_GATE_REFUSED",
        "receipt": str(receipt_path),
        "fixture_count": len(fixture_results),
        "non_empty_patch_count": non_empty_patch_count,
        "negative_cases": len(negative_cases),
        "negative_cases_all_refused": negative_cases_all_refused,
        "carrier_qualified": False,
        "execution_authorized": False,
        "section_6": "NOT_DONE",
        "errors": errors,
    }
    print(json.dumps(summary, sort_keys=True))
    return 0 if gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
