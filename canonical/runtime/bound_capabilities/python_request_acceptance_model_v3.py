from __future__ import annotations

import ast
import hashlib
import json
import os
import pathlib
import subprocess
import sys
from typing import Any, Mapping

from canonical.runtime.bound_capabilities.python_request_acceptance_model_v1 import (
    RequestAcceptanceError,
    _safe_rel,
)
from canonical.runtime.bound_capabilities.python_request_acceptance_model_v2 import (
    PLAN_SCHEMA as V2_PLAN_SCHEMA,
    compile_plan,
)

SCHEMA = "PROJECT_BRAIN_PYTHON_REQUEST_ACCEPTANCE_MODEL_V3"
BASELINE_SCHEMA = "PROJECT_BRAIN_REPOSITORY_BASELINE_MANIFEST_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_PYTHON_REQUEST_ACCEPTANCE_RESULT_V3"

DEFAULT_MAX_FILES = 20_000
DEFAULT_MAX_TOTAL_BYTES = 512 * 1024 * 1024
DEFAULT_MAX_SINGLE_FILE_BYTES = 64 * 1024 * 1024


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value).encode("utf-8")).hexdigest()


def _path_entry(root: pathlib.Path, path: pathlib.Path) -> tuple[str, str, int]:
    rel = path.relative_to(root).as_posix()
    if path.is_symlink():
        target = os.readlink(path)
        digest = hashlib.sha256(("SYMLINK\0" + target).encode("utf-8", "surrogateescape")).hexdigest()
        return rel, "SYMLINK:" + digest, len(target.encode("utf-8", "surrogateescape"))
    data = path.read_bytes()
    return rel, hashlib.sha256(data).hexdigest(), len(data)


def _tree_manifest(
    root: pathlib.Path,
    *,
    max_files: int,
    max_total_bytes: int,
    max_single_file_bytes: int,
) -> dict[str, Any]:
    files: dict[str, str] = {}
    total = 0
    count = 0
    for path in sorted(root.rglob("*")):
        rel_parts = path.relative_to(root).parts
        if ".git" in rel_parts or "__pycache__" in rel_parts:
            continue
        if not (path.is_file() or path.is_symlink()):
            continue
        count += 1
        if count > max_files:
            raise RequestAcceptanceError("BASELINE_FILE_LIMIT_EXCEEDED")
        rel, digest, size = _path_entry(root, path)
        if size > max_single_file_bytes:
            raise RequestAcceptanceError("BASELINE_SINGLE_FILE_LIMIT_EXCEEDED:" + rel)
        total += size
        if total > max_total_bytes:
            raise RequestAcceptanceError("BASELINE_TOTAL_BYTE_LIMIT_EXCEEDED")
        files[rel] = digest
    return {"files": files, "file_count": count, "total_bytes": total}


def build_baseline_manifest(
    repo_root: str | os.PathLike[str],
    *,
    max_files: int = DEFAULT_MAX_FILES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    max_single_file_bytes: int = DEFAULT_MAX_SINGLE_FILE_BYTES,
) -> dict[str, Any]:
    root = pathlib.Path(repo_root).resolve()
    if not root.is_dir() or root.is_symlink():
        raise RequestAcceptanceError("REPOSITORY_INVALID")
    body = _tree_manifest(
        root,
        max_files=max_files,
        max_total_bytes=max_total_bytes,
        max_single_file_bytes=max_single_file_bytes,
    )
    payload = {
        "schema": BASELINE_SCHEMA,
        "files": body["files"],
        "file_count": body["file_count"],
        "total_bytes": body["total_bytes"],
    }
    return {
        **payload,
        "manifest_sha256": _sha(payload),
        "capture_authority": "BRAIN_LOCAL_CONTENT_HASH_CAPTURE_ONLY",
        "freshness_or_pre_repair_time_authority": False,
    }


def _validate_baseline(baseline: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(baseline, Mapping) or baseline.get("schema") != BASELINE_SCHEMA:
        raise RequestAcceptanceError("BASELINE_MANIFEST_REQUIRED")
    files = baseline.get("files")
    if not isinstance(files, Mapping):
        raise RequestAcceptanceError("BASELINE_FILES_INVALID")
    normalized: dict[str, str] = {}
    for raw_path, raw_digest in files.items():
        path = _safe_rel(raw_path)
        digest = str(raw_digest or "")
        if digest.startswith("SYMLINK:"):
            h = digest.split(":", 1)[1]
        else:
            h = digest
        if len(h) != 64 or any(ch not in "0123456789abcdef" for ch in h.lower()):
            raise RequestAcceptanceError("BASELINE_DIGEST_INVALID:" + path)
        normalized[path] = digest
    payload = {
        "schema": BASELINE_SCHEMA,
        "files": normalized,
        "file_count": int(baseline.get("file_count", len(normalized))),
        "total_bytes": int(baseline.get("total_bytes", 0)),
    }
    if baseline.get("manifest_sha256") != _sha(payload):
        raise RequestAcceptanceError("BASELINE_MANIFEST_HASH_MISMATCH")
    if payload["file_count"] != len(normalized):
        raise RequestAcceptanceError("BASELINE_FILE_COUNT_MISMATCH")
    return payload


def _changed_paths(root: pathlib.Path, baseline: Mapping[str, Any]) -> tuple[set[str], dict[str, Any]]:
    valid = _validate_baseline(baseline)
    current = _tree_manifest(
        root,
        max_files=DEFAULT_MAX_FILES,
        max_total_bytes=DEFAULT_MAX_TOTAL_BYTES,
        max_single_file_bytes=DEFAULT_MAX_SINGLE_FILE_BYTES,
    )
    before = dict(valid["files"])
    after = dict(current["files"])
    keys = set(before) | set(after)
    changed = {p for p in keys if before.get(p) != after.get(p)}
    return changed, {
        "baseline_manifest_sha256": baseline["manifest_sha256"],
        "changed_path_count": len(changed),
        "changed_paths": sorted(changed),
    }


def _safe_path(root: pathlib.Path, raw: Any) -> pathlib.Path:
    rel = _safe_rel(raw)
    raw_path = root / rel
    if raw_path.is_symlink():
        raise RequestAcceptanceError("SYMLINK_REJECTED:" + rel)
    p = raw_path.resolve()
    if p == root or root not in p.parents:
        raise RequestAcceptanceError("PATH_OUTSIDE_REPOSITORY")
    return p


def _run_verifier(
    verifier: Mapping[str, Any],
    *,
    root: pathlib.Path,
    baseline: Mapping[str, Any] | None,
    timeout_s: int,
) -> tuple[bool, str, dict[str, Any]]:
    kind = str(verifier.get("kind") or "")
    details: dict[str, Any] = {"kind": kind}

    if kind in {"CHANGED_PATHS_SUBSET", "PATH_UNCHANGED"}:
        try:
            changed, meta = _changed_paths(root, baseline or {})
        except RequestAcceptanceError as exc:
            return False, str(exc), details
        details.update(meta)
        if kind == "CHANGED_PATHS_SUBSET":
            allowed = {_safe_rel(x) for x in verifier.get("allowed_paths") or []}
            details["allowed_paths"] = sorted(allowed)
            ok = changed <= allowed
            return ok, "CHANGED_PATHS_WITHIN_SCOPE" if ok else "CHANGED_PATH_OUTSIDE_SCOPE", details
        path = _safe_rel(verifier.get("path"))
        ok = path not in changed
        details["path"] = path
        return ok, "PATH_UNCHANGED" if ok else "PATH_CHANGED", details

    path = _safe_rel(verifier.get("path"))
    try:
        p = _safe_path(root, path)
    except RequestAcceptanceError as exc:
        return False, str(exc), {"kind": kind, "path": path}
    details["path"] = path

    if kind == "FILE_EXISTS":
        ok = p.is_file()
        return ok, "FILE_EXISTS" if ok else "FILE_MISSING", details

    if kind == "FILE_ABSENT":
        ok = not (root / path).exists() and not (root / path).is_symlink()
        return ok, "FILE_ABSENT" if ok else "FILE_PRESENT", details

    if kind in {"FILE_CONTAINS", "FILE_NOT_CONTAINS"}:
        if not p.is_file():
            return False, "FILE_MISSING", details
        data = p.read_bytes()
        if len(data) > 4_000_000:
            return False, "FILE_TOO_LARGE", details
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return False, "FILE_NOT_UTF8", details
        literal = str(verifier.get("literal") or "")
        found = literal in text
        details["literal_sha256"] = hashlib.sha256(literal.encode("utf-8")).hexdigest()
        details["file_sha256"] = hashlib.sha256(data).hexdigest()
        ok = found if kind == "FILE_CONTAINS" else not found
        return ok, ("LITERAL_PRESENT" if found else "LITERAL_ABSENT"), details

    if kind == "PYTHON_AST_PARSE":
        if not p.is_file() or p.suffix != ".py":
            return False, "PYTHON_FILE_INVALID", details
        try:
            ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        except (SyntaxError, UnicodeDecodeError):
            return False, "PYTHON_PARSE_FAILED", details
        details["file_sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
        return True, "PYTHON_PARSE_PASS", details

    if kind == "PYTHON_TEST_FILE_PASS":
        try:
            valid = _validate_baseline(baseline)
        except RequestAcceptanceError as exc:
            return False, str(exc), details
        expected = valid["files"].get(path)
        if expected is None:
            return False, "TEST_VERIFIER_NOT_IN_BASELINE", details
        if expected.startswith("SYMLINK:"):
            return False, "TEST_VERIFIER_SYMLINK_BASELINE_REJECTED", details
        if not p.is_file() or p.suffix != ".py":
            return False, "TEST_FILE_INVALID", details
        current_sha = hashlib.sha256(p.read_bytes()).hexdigest()
        if current_sha != expected:
            return False, "TEST_VERIFIER_CHANGED_SINCE_BASELINE", details

        before = _tree_manifest(
            root,
            max_files=DEFAULT_MAX_FILES,
            max_total_bytes=DEFAULT_MAX_TOTAL_BYTES,
            max_single_file_bytes=DEFAULT_MAX_SINGLE_FILE_BYTES,
        )
        try:
            proc = subprocess.run(
                [sys.executable, str(p)],
                cwd=root,
                text=True,
                capture_output=True,
                timeout=timeout_s,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
        except subprocess.TimeoutExpired:
            return False, "TEST_TIMEOUT", details
        after = _tree_manifest(
            root,
            max_files=DEFAULT_MAX_FILES,
            max_total_bytes=DEFAULT_MAX_TOTAL_BYTES,
            max_single_file_bytes=DEFAULT_MAX_SINGLE_FILE_BYTES,
        )
        if before["files"] != after["files"]:
            before_files = before["files"]
            after_files = after["files"]
            keys = set(before_files) | set(after_files)
            side_effects = sorted(pth for pth in keys if before_files.get(pth) != after_files.get(pth))
            details["side_effect_paths"] = side_effects
            return False, "TEST_VERIFIER_SIDE_EFFECT", details

        details.update({
            "returncode": proc.returncode,
            "stdout_sha256": hashlib.sha256(proc.stdout.encode("utf-8", "replace")).hexdigest(),
            "stderr_sha256": hashlib.sha256(proc.stderr.encode("utf-8", "replace")).hexdigest(),
            "test_file_sha256": current_sha,
            "baseline_manifest_sha256": baseline["manifest_sha256"],
        })
        return proc.returncode == 0, "TEST_PASS" if proc.returncode == 0 else "TEST_FAIL", details

    return False, "UNKNOWN_VERIFIER_KIND", details


def evaluate_plan(
    plan: Mapping[str, Any],
    *,
    repo_root: str | os.PathLike[str],
    baseline_manifest: Mapping[str, Any] | None = None,
    existing_test_evidence: Mapping[str, Any] | None = None,
    timeout_s: int = 20,
) -> dict[str, Any]:
    if not isinstance(plan, Mapping) or plan.get("schema") != V2_PLAN_SCHEMA or plan.get("pass") is not True:
        raise RequestAcceptanceError("PLAN_INVALID")
    root = pathlib.Path(repo_root).resolve()
    if not root.is_dir() or root.is_symlink():
        raise RequestAcceptanceError("REPOSITORY_INVALID")
    timeout = max(1, min(int(timeout_s), 60))

    rows = []
    bound_raw_ids: set[str] = set()
    passed_raw_ids: set[str] = set()
    for pred in plan.get("acceptance_predicates") or []:
        obligation_ids = [str(x) for x in pred.get("obligation_ids") or []]
        if pred.get("semantic_binding") != "BOUND_EXECUTABLE" or not isinstance(pred.get("verifier"), Mapping):
            rows.append({
                "predicate_id": pred.get("predicate_id"),
                "obligation_ids": obligation_ids,
                "status": "UNBOUND",
                "pass": False,
                "reason": pred.get("unbound_reason") or "UNBOUND",
            })
            continue
        bound_raw_ids.update(obligation_ids)
        ok, reason, details = _run_verifier(
            pred["verifier"],
            root=root,
            baseline=baseline_manifest,
            timeout_s=timeout,
        )
        if ok:
            passed_raw_ids.update(obligation_ids)
        rows.append({
            "predicate_id": pred.get("predicate_id"),
            "obligation_ids": obligation_ids,
            "status": "VERIFIED_PASS" if ok else "VERIFIED_FAIL",
            "pass": ok,
            "reason": reason,
            "details": details,
        })

    required = {
        str(x)
        for x in plan["task_contract"]["acceptance_contract"]["required_obligation_ids"]
    }
    unbound = [r for r in rows if r["status"] == "UNBOUND"]
    failed = [r for r in rows if r["status"] == "VERIFIED_FAIL"]
    all_bound = bound_raw_ids == required
    all_pass = passed_raw_ids == required
    complete = bool(rows) and all_bound and all_pass and not unbound and not failed
    return {
        "schema": RESULT_SCHEMA,
        "status": "PASS__COMPLETE_BOUND_REQUEST_ACCEPTANCE" if complete else "OPEN__REQUEST_ACCEPTANCE_NOT_COMPLETE",
        "pass": complete,
        "acceptance_plan_sha256": plan.get("acceptance_plan_sha256"),
        "predicate_results": rows,
        "raw_obligation_count": len(required),
        "bound_raw_obligation_count": len(bound_raw_ids),
        "verified_pass_raw_obligation_count": len(passed_raw_ids),
        "unbound_predicate_count": len(unbound),
        "bound_verified_fail_count": len(failed),
        "all_raw_obligations_semantically_bound": all_bound,
        "all_raw_obligations_verified_pass": all_pass,
        "existing_test_evidence": dict(existing_test_evidence or {}),
        "existing_test_evidence_is_request_semantics_authority": False,
        "baseline_manifest_used": baseline_manifest is not None,
        "baseline_freshness_or_pre_repair_time_authority": False,
        "repair_stop_authorized_by_this_capability": complete,
        "model_dependency_count": 0,
        "external_capability_provider_count": 0,
        "incremental_spend_usd": 0,
        "hard_nonclaims": [
            "NO_ARBITRARY_NATURAL_LANGUAGE_SEMANTIC_COMPLETENESS",
            "NO_TEST_PASS_TO_UNBOUND_REQUEST_SEMANTICS_INFERENCE",
            "NO_REPAIR_STOP_WHILE_ANY_RAW_OBLIGATION_IS_UNBOUND_OR_FAILING",
            "NO_CALLER_SUPPLIED_CHANGED_PATHS_AS_SCOPE_AUTHORITY",
            "NO_BASELINE_FRESHNESS_AUTHORITY_FROM_CONTENT_HASH_CAPTURE_ALONE",
            "NO_GENERAL_MERGEABILITY_OR_FRONTIERCODE_SCORE_CLAIM",
        ],
    }


def run(args: Mapping[str, Any], root: str | os.PathLike[str]) -> dict[str, Any]:
    if not isinstance(args, Mapping):
        raise RequestAcceptanceError("ARGS_NOT_OBJECT")
    plan = compile_plan(
        str(args.get("request_text") or ""),
        source_id=str(args.get("source_id") or "software_request"),
        routing_target_effects=tuple(args.get("routing_target_effects") or ("software.patch.correct",)),
    )
    if plan.get("pass") is not True or args.get("compile_only") is True:
        return plan
    baseline = args.get("baseline_manifest") if isinstance(args.get("baseline_manifest"), Mapping) else None
    return evaluate_plan(
        plan,
        repo_root=root,
        baseline_manifest=baseline,
        existing_test_evidence=args.get("existing_test_evidence") if isinstance(args.get("existing_test_evidence"), Mapping) else None,
        timeout_s=int(args.get("timeout_s", 20)),
    )
