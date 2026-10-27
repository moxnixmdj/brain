#!/usr/bin/env python3
"""Exact tree-node patch trial with fresh index/impact artifacts and test oracle."""
from __future__ import annotations

import difflib
import json
import os
import pathlib
import subprocess
import sys
from typing import Any

from canonical.runtime import tree_sitter_swe_kernel_v1 as kernel
from canonical.runtime.bound_capabilities.python_test_guided_patch_search_v1 import suite_argv

SCHEMA = kernel.PATCH_SCHEMA
CAPABILITY_ID = "code.patch.tree_sitter.verify.v1"
PROVIDES = ["code.patch.tree_sitter.verified", "code.patch.multilanguage.test_verified"]
REQUIRES = ["code.symbols.tree_sitter.indexed", "code.impact.test_selection.verified"]


def _selection(repo: pathlib.Path, args: dict[str, Any], index_path: pathlib.Path) -> dict[str, Any]:
    selection_path = kernel.safe_path(repo, args.get("selection_path"), must_exist=True)
    try:
        selection = json.loads(selection_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise kernel.TreeSitterSWEError("SELECTION_UNREADABLE") from exc
    if selection.get("schema") != kernel.IMPACT_SCHEMA or selection.get("verified") is not True:
        raise kernel.TreeSitterSWEError("SELECTION_NOT_VERIFIED")
    if selection.get("index_sha256") != kernel.bytes_sha256(index_path.read_bytes()):
        raise kernel.TreeSitterSWEError("SELECTION_INDEX_MISMATCH")
    if not isinstance(selection.get("selected_tests"), list):
        raise kernel.TreeSitterSWEError("SELECTION_TESTS_INVALID")
    return selection


def _edits(repo: pathlib.Path, raw_edits: Any) -> tuple[dict[str, bytes], dict[str, bytes], dict[str, list[dict[str, Any]]]]:
    if not isinstance(raw_edits, list) or not raw_edits:
        raise kernel.TreeSitterSWEError("EDITS_REQUIRED")
    originals: dict[str, bytes] = {}
    candidates: dict[str, bytes] = {}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for raw in raw_edits:
        if not isinstance(raw, dict):
            raise kernel.TreeSitterSWEError("EDIT_INVALID")
        path = kernel.safe_path(repo, raw.get("path"), must_exist=True)
        if not path.is_file():
            raise kernel.TreeSitterSWEError("EDIT_SOURCE_NOT_FILE")
        language = kernel.detect_language(path)
        if not language:
            raise kernel.TreeSitterSWEError("LANGUAGE_UNSUPPORTED:" + str(raw.get("path")))
        rel = kernel.relative_path(repo, path)
        source = path.read_bytes()
        originals.setdefault(rel, source)
        start, end = raw.get("start_byte"), raw.get("end_byte")
        if isinstance(start, bool) or isinstance(end, bool) or not isinstance(start, int) or not isinstance(end, int):
            raise kernel.TreeSitterSWEError("EDIT_SPAN_INVALID")
        if not (0 <= start < end <= len(source)):
            raise kernel.TreeSitterSWEError("EDIT_SPAN_OUT_OF_RANGE")
        expected, replacement = raw.get("expected"), raw.get("replacement")
        if not isinstance(expected, str) or not isinstance(replacement, str):
            raise kernel.TreeSitterSWEError("EDIT_TEXT_INVALID")
        if source[start:end] != expected.encode("utf-8"):
            raise kernel.TreeSitterSWEError("EDIT_EXPECTED_BYTES_MISMATCH:" + rel)
        tree = kernel.parse_bytes(language, source)
        if not kernel.node_span_exists(tree, start, end):
            raise kernel.TreeSitterSWEError("EDIT_NOT_NODE_ALIGNED:" + rel)
        grouped.setdefault(rel, []).append({
            "path": rel, "start_byte": start, "end_byte": end,
            "expected": expected, "replacement": replacement,
        })
    for rel, edits in grouped.items():
        ordered = sorted(edits, key=lambda edit: (edit["start_byte"], edit["end_byte"]))
        for left, right in zip(ordered, ordered[1:]):
            if right["start_byte"] < left["end_byte"]:
                raise kernel.TreeSitterSWEError("EDITS_OVERLAP:" + rel)
        updated = originals[rel]
        for edit in reversed(ordered):
            updated = updated[:edit["start_byte"]] + edit["replacement"].encode("utf-8") + updated[edit["end_byte"]:]
        candidates[rel] = updated
    return originals, candidates, grouped


def _test_command(repo: pathlib.Path, args: dict[str, Any], selection: dict[str, Any]) -> list[str]:
    explicit = args.get("test_argv")
    if explicit is not None:
        if not isinstance(explicit, list) or not explicit or any(not isinstance(item, str) or not item for item in explicit):
            raise kernel.TreeSitterSWEError("TEST_ARGV_INVALID")
        return list(explicit)
    selected = selection.get("selected_tests") or []
    if not selected:
        raise kernel.TreeSitterSWEError("NO_SELECTED_TESTS")
    paths = [kernel.safe_path(repo, path, must_exist=True) for path in selected]
    if any(path.suffix != ".py" for path in paths):
        raise kernel.TreeSitterSWEError("TEST_ARGV_REQUIRED_FOR_NON_PYTHON_SELECTION")
    return suite_argv(sys.executable, *paths)


def _run_tests(argv: list[str], cwd: pathlib.Path, timeout_s: float, env: dict[str, str]) -> dict[str, Any]:
    try:
        proc = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout_s)
        return {
            "returncode": proc.returncode,
            "timed_out": False,
            "stdout_tail": (proc.stdout or "")[-1000:],
            "stderr_tail": (proc.stderr or "")[-1000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "returncode": None,
            "timed_out": True,
            "stdout_tail": str(exc.stdout or "")[-1000:],
            "stderr_tail": str(exc.stderr or "")[-1000:],
        }
    except OSError as exc:
        return {"returncode": None, "timed_out": False, "error": type(exc).__name__, "stdout_tail": "", "stderr_tail": str(exc)[-1000:]}


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = kernel.safe_output(repo, args.get("output_path"))
    index_path = kernel.safe_path(repo, args.get("index_path"), must_exist=True)
    kernel.read_index(repo, index_path)
    selection = _selection(repo, args, index_path)
    originals, candidates, edits = _edits(repo, args.get("edits"))
    if set(originals) != set(selection.get("changed_files") or []):
        raise kernel.TreeSitterSWEError("SELECTION_CHANGE_MISMATCH")
    argv = _test_command(repo, args, selection)
    test_cwd = kernel.safe_path(repo, args.get("test_cwd") or ".", must_exist=True, allow_root=True)
    if not test_cwd.is_dir():
        raise kernel.TreeSitterSWEError("TEST_CWD_NOT_DIRECTORY")
    timeout_s = float(args.get("timeout_s", 30))
    replay_count = int(args.get("replay_count", 2))
    if not (0 < timeout_s <= 300 and 1 <= replay_count <= 3):
        raise kernel.TreeSitterSWEError("TEST_BOUND_INVALID")

    parse_results: dict[str, dict[str, Any]] = {}
    for rel, updated in candidates.items():
        language = kernel.detect_language(pathlib.Path(rel))
        tree = kernel.parse_bytes(str(language), updated)
        parse_results[rel] = {
            "language": language,
            "has_syntax_error": bool(tree.root_node.has_error),
            "candidate_sha256": kernel.bytes_sha256(updated),
            "root_node_type": tree.root_node.type,
        }
    parse_ok = all(not row["has_syntax_error"] for row in parse_results.values())
    test_runs: list[dict[str, Any]] = []
    restored = False
    try:
        if parse_ok:
            for rel, updated in candidates.items():
                kernel.safe_path(repo, rel, must_exist=True).write_bytes(updated)
            env = dict(os.environ)
            python_paths = [str((repo / rel).resolve().parent) for rel in originals]
            if env.get("PYTHONPATH"):
                python_paths.append(env["PYTHONPATH"])
            env.update({
                "PYTHONPATH": os.pathsep.join(dict.fromkeys(python_paths)),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PIP_NO_INDEX": "1",
                "CARGO_NET_OFFLINE": "true",
                "npm_config_offline": "true",
            })
            for replay in range(replay_count):
                result = _run_tests(argv, test_cwd, timeout_s, env)
                result["replay"] = replay + 1
                test_runs.append(result)
                if result.get("returncode") != 0:
                    break
    finally:
        for rel, source in originals.items():
            kernel.safe_path(repo, rel, must_exist=True).write_bytes(source)
        restored = all(
            kernel.bytes_sha256(kernel.safe_path(repo, rel, must_exist=True).read_bytes()) == kernel.bytes_sha256(source)
            for rel, source in originals.items()
        )

    tests_ok = len(test_runs) == replay_count and all(run.get("returncode") == 0 for run in test_runs)
    verified = parse_ok and tests_ok and restored
    diffs = []
    for rel in sorted(originals):
        before = originals[rel].decode("utf-8", "replace").splitlines(keepends=True)
        after = candidates[rel].decode("utf-8", "replace").splitlines(keepends=True)
        diffs.append("".join(difflib.unified_diff(before, after, fromfile="a/" + rel, tofile="b/" + rel)))
    artifact = {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "selection_path": args.get("selection_path"),
        "index_path": args.get("index_path"),
        "edits": [edit for rel in sorted(edits) for edit in edits[rel]],
        "parse_results": parse_results,
        "test_argv": argv,
        "test_runs": test_runs,
        "source_restored": restored,
        "unified_diff": "".join(diffs),
        "status": "PATCH_VERIFIED" if verified else "PATCH_REJECTED",
        "verified": verified,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
    digest = kernel.write_artifact(output, artifact)
    return {
        "adapter": "code_tree_sitter_patch_verify_v1",
        "output_path": kernel.relative_path(repo, output),
        "output_sha256": digest,
        "output_verified": verified,
        "verified": verified,
        "status": artifact["status"],
        "source_restored": restored,
        "test_pass_count": sum(run.get("returncode") == 0 for run in test_runs),
        "unified_diff": artifact["unified_diff"],
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
