#!/usr/bin/env python3
"""Exact tree-node patch trials with a non-vacuous Python test oracle.

Trials run in a copy of the repository, not an OS sandbox. Only Python edits
can currently be verified: pytest must execute the configured suite on every
replay and the selected plus remaining known indexed test files explicitly.
Each nonempty run requires passing, non-vacuous evidence. Other languages may
run an explicit command, but its exit status alone cannot verify a test suite.
Files outside the indexed root, nonstandard test names outside configured
discovery, and untested behavior remain outside this oracle's scope.
"""
from __future__ import annotations

import difflib
import json
import os
import pathlib
import shutil
import sys
import tempfile
from typing import Any

from canonical.runtime import tree_sitter_swe_kernel_v1 as kernel
from canonical.runtime.bound_capabilities import python_repo_diff_apply_full_testgate as full_testgate

SCHEMA = kernel.PATCH_SCHEMA
CAPABILITY_ID = "code.patch.tree_sitter.verify.v1"
PROVIDES = ["code.patch.tree_sitter.verified", "code.patch.python.pytest_verified"]
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
    paths = [kernel.safe_path(repo, path, must_exist=True) for path in selected]
    if any(path.suffix != ".py" for path in paths):
        raise kernel.TreeSitterSWEError("TEST_ARGV_REQUIRED_FOR_NON_PYTHON_SELECTION")
    # The selected set is a hint, not an oracle: dynamic dependencies and
    # pytest fixtures are not faithfully handled by the old sliced runner.
    return [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]


def _run_tests(argv: list[str], cwd: pathlib.Path, timeout_s: float, env: dict[str, str]) -> dict[str, Any]:
    try:
        proc = full_testgate.test_process._run_process(cwd, argv, timeout_s, env)
        return {
            "returncode": proc["returncode"],
            "timed_out": proc["timed_out"],
            "stdout_tail": proc["stdout"][-1000:],
            "stderr_tail": proc["stderr"][-1000:],
        }
    except OSError as exc:
        return {"returncode": None, "timed_out": False, "error": type(exc).__name__, "stdout_tail": "", "stderr_tail": str(exc)[-1000:]}


def _outside_temporary_directory(repo: pathlib.Path) -> tempfile.TemporaryDirectory:
    """Never create a copy inside the tree being copied."""
    for base in (pathlib.Path(tempfile.gettempdir()), pathlib.Path.home(), repo.parent):
        base = base.resolve()
        if base == repo or repo in base.parents:
            continue
        try:
            return tempfile.TemporaryDirectory(prefix="brain-ts-patch-", dir=base)
        except OSError:
            continue
    raise kernel.TreeSitterSWEError("EXTERNAL_SCRATCH_UNAVAILABLE")


def _relocate_argv(argv: list[str], repo: pathlib.Path, scratch: pathlib.Path) -> list[str]:
    """Redirect explicit absolute repository paths into the trial copy."""
    relocated = []
    for item in argv:
        path = pathlib.Path(item)
        if path.is_absolute():
            try:
                item = str(scratch / path.resolve().relative_to(repo))
            except (OSError, ValueError):
                pass
        relocated.append(item)
    return relocated


def _indexed_python_test_file(repo: pathlib.Path, row: dict[str, Any], source_root: str) -> bool:
    """Use indexed test candidates without treating fixtures/helpers as suites."""
    if row.get("language") != "python" or not kernel.is_test_file(repo, row, source_root):
        return False
    name = pathlib.PurePosixPath(row["path"]).name
    if name in {"conftest.py", "__init__.py"}:
        return False
    if name.startswith("test_") or name.endswith("_test.py"):
        return True
    # The indexer also marks every Python file inside tests/ as a candidate.
    # Keep nonstandard named files with indexed test definitions or syntax
    # errors, but do not require empty helper modules to collect pytest cases.
    return bool(row.get("has_syntax_error") or any(
        definition.get("kind") == "function" and str(definition.get("name") or "").startswith("test_")
        for definition in row.get("definitions") or []
    ))


def _run_pytest(cwd: pathlib.Path, timeout_s: float, env: dict[str, str],
                paths: list[str] | None = None) -> dict[str, Any]:
    """Require non-vacuous pytest evidence for a configured or explicit run."""
    argv = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    if paths:
        argv += ["--rootdir=.", "-o", "addopts=", "-o", "junit_family=legacy"]
    with tempfile.TemporaryDirectory(prefix=".brain-ts-pytest-", dir=cwd) as report_dir:
        report_path = pathlib.Path(report_dir) / "pytest.xml"
        # --junitxml must be relative to cwd so it resolves inside the
        # sandbox chroot (cwd is mounted at /project).
        report_rel = report_path.relative_to(cwd)
        result = _run_tests(argv + ["--junitxml=" + str(report_rel)] + (paths or []),
                            cwd, timeout_s, env)
        report = full_testgate._pytest_report(report_path)
        by_file = full_testgate._pytest_file_evidence(report_path, cwd, paths) if paths else {}
        unexecuted = [path for path in (paths or []) if by_file.get(path, {}).get("passed", 0) == 0]
        for key in ("stdout_tail", "stderr_tail"):
            result[key] = result[key].replace(str(report_path), "<pytest-report>")
    result.update({
        "pytest_report_available": report["available"],
        "tests_collected": report["collected"],
        "tests_executed": report["executed"],
        "tests_passed": report["passed"],
        "tests_failed": report["failed"] + report["errors"],
        "tests_skipped": report["skipped"],
        "unexecuted_test_files": unexecuted,
        "oracle_ok": (result["returncode"] == 0 and report["available"] and not unexecuted
                      and report["passed"] > 0 and report["failed"] == 0
                      and report["errors"] == 0),
    })
    return result


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = kernel.safe_output(repo, args.get("output_path"))
    index_path = kernel.safe_path(repo, args.get("index_path"), must_exist=True)
    selection_path = kernel.safe_path(repo, args.get("selection_path"), must_exist=True)
    index = kernel.read_index(repo, index_path)
    if output in (index_path, selection_path):
        raise kernel.TreeSitterSWEError("OUTPUT_OVERLAPS_INPUT_ARTIFACT")
    indexed_paths = {str(row.get("path")) for row in index.get("files", [])}
    if kernel.relative_path(repo, output) in indexed_paths:
        raise kernel.TreeSitterSWEError("OUTPUT_OVERLAPS_INDEXED_SOURCE")
    # Row hashes alone cannot detect a newly added/omitted test file. Refuse a
    # stale or incomplete file set before treating this index as a test scope.
    index_root = kernel.safe_path(repo, index.get("source_root"), must_exist=True, allow_root=True)
    current_paths = {kernel.relative_path(repo, path) for path in kernel.source_files(index_root)}
    if current_paths != indexed_paths or len(index.get("files", [])) != len(indexed_paths):
        raise kernel.TreeSitterSWEError("INDEX_FILE_SET_STALE")
    selection = _selection(repo, args, index_path)
    originals, candidates, edits = _edits(repo, args.get("edits"))
    if set(originals) != set(selection.get("changed_files") or []):
        raise kernel.TreeSitterSWEError("SELECTION_CHANGE_MISMATCH")
    argv = _test_command(repo, args, selection)
    explicit_command = args.get("test_argv") is not None
    python_only = all(kernel.detect_language(pathlib.Path(rel)) == "python" for rel in originals)
    selected_paths = [kernel.safe_path(repo, path, must_exist=True)
                      for path in (selection.get("selected_tests") or [])]
    python_selection = all(path.suffix == ".py" for path in selected_paths)
    # Derive candidates from the validated index, not from the selection's
    # potentially incomplete candidate/omitted metadata or static reachability.
    indexed_test_names = sorted(
        row["path"] for row in index["files"]
        if _indexed_python_test_file(repo, row, str(index.get("source_root") or "."))
    )
    selected_names = {kernel.relative_path(repo, path) for path in selected_paths}
    indexed_omitted = sorted(set(indexed_test_names) - selected_names)
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
    selected_runs: list[dict[str, Any]] = []
    indexed_test_runs: list[dict[str, Any]] = []
    combined_test_runs: list[dict[str, Any]] = []
    command_runs: list[dict[str, Any]] = []
    restored = False
    candidate_intact = True

    def bytes_match(root: pathlib.Path, expected: dict[str, bytes]) -> bool:
        try:
            return all(kernel.safe_path(root, rel, must_exist=True).read_bytes() == data
                       for rel, data in expected.items())
        except (OSError, kernel.TreeSitterSWEError):
            return False

    try:
        if parse_ok:
            # Test in a separate copy, rather than temporarily overwriting the
            # caller's checkout (which can race with other readers and edits).
            # Relative file side effects stay in the copy; it is not a sandbox.
            with _outside_temporary_directory(repo) as temp_dir:
                scratch = pathlib.Path(temp_dir) / "repo"
                shutil.copytree(repo, scratch, symlinks=True,
                                ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache",
                                                              ".mypy_cache", ".ruff_cache"))
                if not bytes_match(scratch, originals):
                    raise kernel.TreeSitterSWEError("TRIAL_SNAPSHOT_MISMATCH")
                for rel, updated in candidates.items():
                    kernel.safe_path(scratch, rel, must_exist=True).write_bytes(updated)
                # Snapshot the Python tree before any command or slice can
                # rewrite tests or other source and contaminate later runs.
                trial_python_snapshot = full_testgate._python_trial_snapshot(scratch, [])

                def trial_intact():
                    try:
                        return (bytes_match(scratch, candidates) and
                                full_testgate._python_trial_snapshot(scratch, []) == trial_python_snapshot)
                    except OSError:
                        return False

                scratch_cwd = scratch / test_cwd.relative_to(repo)
                env = full_testgate._pytest_env(repo, scratch)
                python_paths = [str((scratch / rel).parent) for rel in originals]
                if env.get("PYTHONPATH"):
                    python_paths.append(env["PYTHONPATH"])
                env.update({
                    "PYTHONPATH": os.pathsep.join(dict.fromkeys(python_paths)),
                    "PIP_NO_INDEX": "1",
                    "CARGO_NET_OFFLINE": "true",
                    "npm_config_offline": "true",
                })
                if explicit_command:
                    command_runs.append(_run_tests(_relocate_argv(argv, repo, scratch),
                                                   scratch_cwd, timeout_s, env))
                    candidate_intact = trial_intact()
                command_ok = not explicit_command or command_runs[-1].get("returncode") == 0
                if python_only and python_selection and command_ok and candidate_intact:
                    for replay in range(replay_count):
                        result = _run_pytest(scratch_cwd, timeout_s, env)
                        result["replay"] = replay + 1
                        test_runs.append(result)
                        candidate_intact = trial_intact()
                        if not result["oracle_ok"] or not candidate_intact:
                            break
                        if replay == 0 and selected_paths:
                            paths = [os.path.relpath(scratch / path.relative_to(repo), scratch_cwd)
                                     for path in selected_paths]
                            selected_result = _run_pytest(scratch_cwd, timeout_s, env, paths)
                            selected_runs.append(selected_result)
                            candidate_intact = trial_intact()
                            if not selected_result["oracle_ok"] or not candidate_intact:
                                break
                        if replay == 0 and indexed_omitted:
                            paths = [os.path.relpath(scratch / rel, scratch_cwd) for rel in indexed_omitted]
                            indexed_result = _run_pytest(scratch_cwd, timeout_s, env, paths)
                            indexed_test_runs.append(indexed_result)
                            candidate_intact = trial_intact()
                            if not indexed_result["oracle_ok"] or not candidate_intact:
                                break
                        if replay == 0:
                            selected_rel = [os.path.relpath(scratch / path.relative_to(repo), scratch_cwd)
                                            for path in selected_paths]
                            omitted_rel = [os.path.relpath(scratch / rel, scratch_cwd) for rel in indexed_omitted]
                            combined_result = full_testgate._pytest_combined_session(
                                scratch_cwd, sys.executable, env, selected_rel + omitted_rel, timeout_s)
                            combined_test_runs.append(combined_result)
                            candidate_intact = trial_intact()
                            if not combined_result["oracle_ok"] or not candidate_intact:
                                break
                for result in command_runs + selected_runs + indexed_test_runs + test_runs:
                    for key in ("stdout_tail", "stderr_tail"):
                        result[key] = result[key].replace(str(scratch), "<trial-repo>")
    finally:
        # Do not restore by writing: another process may have changed the
        # original checkout legitimately while this trial was running.
        restored = bytes_match(repo, originals)

    command_ok = not explicit_command or (bool(command_runs) and command_runs[0].get("returncode") == 0)
    selected_ok = not selected_paths or (bool(selected_runs) and selected_runs[0].get("oracle_ok") is True)
    indexed_ok = not indexed_omitted or (bool(indexed_test_runs) and indexed_test_runs[0].get("oracle_ok") is True)
    tests_ok = len(test_runs) == replay_count and all(run.get("oracle_ok") is True for run in test_runs)
    combined_ok = bool(combined_test_runs) and combined_test_runs[0].get("oracle_ok") is True
    verified = (parse_ok and python_only and python_selection and command_ok and selected_ok and indexed_ok
                and combined_ok and tests_ok and restored and candidate_intact)
    reported_test_failure = any(run.get("pytest_report_available") and
                                (run.get("returncode") != 0 or run.get("tests_failed", 0) > 0)
                                for run in test_runs + selected_runs + indexed_test_runs + combined_test_runs)
    if verified:
        status = "PATCH_VERIFIED"
    elif not parse_ok or not restored or not candidate_intact or not command_ok or reported_test_failure:
        status = "PATCH_REJECTED"
    else:
        status = "PATCH_ORACLE_UNVERIFIED"
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
        "command_runs": command_runs,
        "selected_test_runs": selected_runs,
        "indexed_test_candidates": indexed_test_names,
        "indexed_test_omitted": indexed_omitted,
        "indexed_test_runs": indexed_test_runs,
        "combined_test_runs": combined_test_runs,
        "test_runs": test_runs,
        "oracle_scope": ("PYTEST_CONFIGURED_SUITE_AND_INDEXED_TEST_FILES"
                         if python_only and python_selection else "EXTERNAL_COMMAND_UNATTESTED"),
        "candidate_intact_after_runs": candidate_intact if (command_runs or selected_runs or indexed_test_runs or test_runs) else None,
        "trial_workspace": "SCRATCH_COPY_NOT_OS_SANDBOX" if parse_ok else "NOT_CREATED",
        "source_restored": restored,
        "unified_diff": "".join(diffs),
        "status": status,
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
        "oracle_scope": artifact["oracle_scope"],
        "candidate_intact_after_runs": artifact["candidate_intact_after_runs"],
        "source_restored": restored,
        "test_pass_count": sum(run.get("oracle_ok") is True for run in test_runs),
        "unified_diff": artifact["unified_diff"],
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
