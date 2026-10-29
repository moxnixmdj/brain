# PROJECT_BRAIN
"""Diff-local Python statement coverage with fail-closed evidence checks.

A unique scratch copy receives the diff. Configured pytest nodes and known
candidate files run together under coverage; a passing JUnit case in each
candidate file and intact Python inputs are required. Missing source rows or
zero executable changed lines are not a coverage pass. With no coverage.py,
PASS_BLIND is only diagnostic and never verified.

Coverage is not behavioral proof. Tests, plugins, the coverage process and
their output run without an OS sandbox and are not independent attestations;
they may affect host paths, spoof data or escape process groups. Discovery of
extra files is convention-based and custom configurations can require more.
The per-subprocess timeouts do not bound filesystem copies or all descendants.
"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from canonical.runtime.bound_capabilities import python_repo_diff_apply_full_testgate as full_testgate
from canonical.runtime.bound_capabilities.python_review_diff_static_triage import (
    _parse_diff_ranges,
)
from canonical.runtime.bound_capabilities.review_gate_input_safety_v1 import guard_inputs

SCHEMA = "PROJECT_BRAIN_DIFF_COVERAGE_GATE_V1"


def _fail(reason: str) -> dict:
    return {
        "error": True,
        "capability": "python.review.diff_coverage_gate.v1",
        "reason": reason,
    }


def _safe_path(repo: Path, rel: str, must_exist: bool = False) -> Path | dict:
    if not rel or not isinstance(rel, str):
        return _fail("MISSING_OR_INVALID_PATH_ARGUMENT")
    p = (repo / rel).resolve()
    if p != repo and repo not in p.parents:
        return _fail("PATH_ESCAPE:" + rel)
    if must_exist and not p.exists():
        return _fail("PATH_MISSING:" + rel)
    return p


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _in_ranges(ranges, lineno: int) -> bool:
    return any(start <= lineno <= end for start, end in ranges)


def run(args, root):
    repo = Path(root).resolve()
    args = dict(args or {})
    anchor_rel = str(args.get("anchor_path") or "")
    anchor_abs = _safe_path(repo, anchor_rel, must_exist=True)
    if isinstance(anchor_abs, dict): return anchor_abs
    if not anchor_abs.is_dir():
        return _fail("ANCHOR_NOT_DIRECTORY")
    diff_rel = str(args.get("diff_path") or "")
    diff_abs = _safe_path(repo, diff_rel, must_exist=True)
    if isinstance(diff_abs, dict): return diff_abs
    diff_text = diff_abs.read_text(encoding="utf-8", errors="strict")
    if not diff_text.strip():
        return _fail("DIFF_EMPTY")
    changed, _created = _parse_diff_ranges(diff_text)
    py_changed = {p: r for p, r in changed.items() if p.endswith(".py")}
    out_rel = str(args.get("output_path") or "")
    out_abs = _safe_path(repo, out_rel)
    if isinstance(out_abs, dict): return out_abs
    if out_abs == anchor_abs or anchor_abs in out_abs.parents:
        return _fail("OUTPUT_INSIDE_ANCHOR")
    if (out_abs == diff_abs or (out_abs.exists() and out_abs.samefile(diff_abs))
            or (out_abs.is_file() and (out_abs.suffix == ".py" or out_abs.stat().st_nlink > 1))):
        return _fail("OUTPUT_OVERLAPS_INPUT")
    timeout_s = int(args.get("timeout_s") if args.get("timeout_s") is not None else 300)
    python_exe = str(args.get("python_executable") or sys.executable)
    min_ratio = float(args.get("min_coverage_ratio") if args.get("min_coverage_ratio") is not None else 1.0)
    if timeout_s <= 0 or not math.isfinite(min_ratio) or not 0 <= min_ratio <= 1:
        return _fail("INVALID_BUDGET_OR_COVERAGE_THRESHOLD")

    git_probe = subprocess.run(["git", "--version"], capture_output=True, text=True,
                               timeout=min(timeout_s, 30))
    if git_probe.returncode != 0:
        return _fail("GIT_UNAVAILABLE")
    cov_probe = subprocess.run([python_exe, "-m", "coverage", "--version"],
                               capture_output=True, text=True, timeout=min(timeout_s, 30))
    coverage_on = cov_probe.returncode == 0 and "overage" in cov_probe.stdout
    guard_result = guard_inputs(anchor_abs, diff_abs, out_abs, py_changed.keys(), _fail)
    if isinstance(guard_result, dict):
        return guard_result
    out_abs.parent.mkdir(parents=True, exist_ok=True)
    unobserved = []
    with tempfile.TemporaryDirectory(prefix=".brain-coverage-", dir=out_abs.parent) as temporary:
        temp = Path(temporary)
        scratch = temp / "tree"
        shutil.copytree(anchor_abs, scratch,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
        check = subprocess.run(["patch", "--dry-run", "-p1", "-i", str(diff_abs)],
                               cwd=scratch, capture_output=True, text=True,
                               timeout=min(timeout_s, 60))
        if check.returncode != 0:
            return _fail("DIFF_DOES_NOT_APPLY:" + (check.stderr.strip().splitlines() or ["<empty>"])[0][:200])
        applied = subprocess.run(["patch", "-p1", "-i", str(diff_abs)],
                                 cwd=scratch, capture_output=True, text=True,
                                 timeout=min(timeout_s, 60))
        if applied.returncode != 0:
            return _fail("DIFF_APPLY_FAILED_AFTER_CHECK")

        tests = {str(p.relative_to(scratch)) for p in scratch.rglob("*.py")
                 if p.name.startswith("test_") or p.name.endswith("_test.py")}
        extra_tests = args.get("run_tests") or []
        if not isinstance(extra_tests, list) or any(not isinstance(x, str) or not x or x.startswith("-")
                                                    for x in extra_tests):
            return _fail("INVALID_TEST_PATHS")
        for name in extra_tests:
            target = (scratch / name).resolve()
            if scratch not in target.parents or not target.is_file() or target.suffix != ".py":
                return _fail("INVALID_TEST_PATH:" + name)
            tests.add(str(target.relative_to(scratch)))
        tests = sorted(tests)
        if not tests:
            return _fail("NO_TESTS_DISCOVERED")
        env = full_testgate._pytest_env(anchor_abs, scratch)
        # Coverage data file must live inside scratch (the sandbox root) so its
        # path resolves inside the chroot. Placing it at temp/coverage.data
        # (a sibling of scratch) leaves it outside /project inside the sandbox.
        data_path = scratch / "coverage.data"
        evidence = full_testgate._pytest_combined_session(
            scratch, python_exe, env, tests, timeout_s,
            coverage_data_path=data_path if coverage_on else None)
        miss_rows = []
        executable_changed = 0
        ratio = None
        if not coverage_on:
            # No statement-coverage claim is possible without the tool.
            gate = "PASS_BLIND" if evidence["oracle_ok"] else "FAIL"
        else:
            if not evidence["oracle_ok"]:
                if evidence["reason"] == "TEST_FAILURE":
                    return _fail("SUITE_RED:coverage under a failing suite is untrustworthy evidence")
                return _fail("SUITE_EVIDENCE_UNAVAILABLE:" + str(evidence["reason"]))
            # Run coverage json inside the sandbox so /project/ source paths
            # (recorded by coverage run under --source=.) resolve correctly.
            # JSON output goes inside scratch; file names carry the /project/
            # prefix and are mapped back to host scratch paths below.
            jf = scratch / "coverage.json"
            cov_env = dict(env, COVERAGE_FILE="coverage.data")
            rep = full_testgate.test_process._run_process(
                scratch, [python_exe, "-m", "coverage", "json", "-o",
                          str(jf.relative_to(scratch)), "--quiet"],
                min(timeout_s, 120), cov_env)
            if rep["timed_out"]:
                return _fail("COVERAGE_JSON_TIMEOUT")
            if rep["returncode"] != 0 or not jf.is_file():
                err_text = (rep.get("stderr", "") or rep.get("stdout", "") or "<error>")
                return _fail("COVERAGE_JSON_FAILED:" + str(err_text).strip().splitlines()[-1][:200])
            try:
                doc = json.loads(jf.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return _fail("COVERAGE_JSON_NOT_JSON")
            files = doc.get("files")
            if not isinstance(files, dict):
                return _fail("COVERAGE_JSON_INVALID")
            # Map /project/... names (recorded inside the sandbox chroot) back
            # to host scratch paths. Only a matching local source file is
            # evidence; an unrelated same-suffix filename elsewhere must not
            # stand in for it.
            scratch_str = str(scratch.resolve())
            measured = {}
            for name, value in files.items():
                if not isinstance(name, str) or not isinstance(value, dict):
                    continue
                if name.startswith("/project/"):
                    host_name = scratch_str + name[len("/project"):]
                else:
                    host_name = str((scratch / name).resolve())
                measured[host_name] = value
            for rel in sorted(py_changed):
                target = str((scratch / rel).resolve())
                row = measured.get(target)
                if row is None:
                    unobserved.append(rel)
                    continue
                executed = set(row.get("executed_lines") or [])
                missing = set(row.get("missing_lines") or [])
                executable = executed | missing
                for start, end in py_changed[rel]:
                    for ln in range(start, (end if end < 10 ** 9 else max(executable or {0})) + 1):
                        if ln in executable:
                            executable_changed += 1
                            if ln in missing:
                                miss_rows.append({"file": rel, "line": ln})
            ratio = ((executable_changed - len(miss_rows)) / executable_changed
                     if executable_changed else None)
            gate = ("UNOBSERVED_FILES" if unobserved else "NO_EXECUTABLE_LINES" if ratio is None
                    else "PASS" if ratio >= min_ratio else "FAIL")

    verified = gate == "PASS"
    artifact = {
        "schema": SCHEMA, "anchor_path": anchor_rel, "diff_path": diff_rel,
        "diff_sha256": _sha256(diff_text.encode("utf-8")),
        "tests_discovered": len(tests), "test_files": tests,
        "test_evidence": evidence,
        "coverage_tool": "UNAVAILABLE" if not coverage_on else "present",
        "diff_executable_lines": executable_changed if coverage_on else None,
        "diff_covered_ratio": ratio, "diff_miss_lines": miss_rows,
        "unobserved_changed_files": unobserved, "min_coverage_ratio": min_ratio,
        "gate": gate,
        "gate_law": ("PASS requires passing configured and candidate tests together, "
                     "observed changed files and executable lines, and the configured "
                     "coverage threshold. Statement coverage is not behavioral proof; "
                     "tests and coverage data are not isolated from hostile code."),
        "complete": True,
    }
    text = json.dumps(artifact, indent=2, ensure_ascii=False) + "\n"
    out_abs.write_text(text, encoding="utf-8")
    out_verified = json.loads(out_abs.read_text(encoding="utf-8")) == artifact
    return {"adapter": "python_review_diff_coverage_gate", "anchor_path": anchor_rel,
            "diff_sha256": artifact["diff_sha256"], "tests_discovered": len(tests),
            "diff_executable_lines": executable_changed if coverage_on else None,
            "diff_covered_ratio": ratio, "diff_miss_lines": len(miss_rows),
            "unobserved_changed_files": unobserved,
            "gate": gate, "complete": True, "output_path": out_rel,
            "output_sha256": _sha256(text.encode("utf-8")),
            "output_verified": out_verified, "verified": bool(verified)}


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--anchor_path", required=True)
    p.add_argument("--diff_path", required=True)
    p.add_argument("--output_path", required=True)
    p.add_argument("--python_executable", default=None)
    p.add_argument("--timeout_s", type=int, default=300)
    p.add_argument("--min_coverage_ratio", type=float, default=None)
    ns = p.parse_args()
    print(json.dumps(run(vars(ns), Path.cwd()), indent=2, sort_keys=True))
