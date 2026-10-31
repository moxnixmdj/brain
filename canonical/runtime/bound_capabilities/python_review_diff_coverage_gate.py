# PROJECT_BRAIN
"""python.review.diff_coverage_gate.v1 — bounded coverage of diff hunks.

The review trio's senior gate: lint triage (#82) proves changed lines are
name/syntax-clean, the type gate (#84) proves they are type-sound — and
NEITHER can see a changed line nothing ever executes.  Coverage is the
class a senior blocks on: "your new branch has no test."

* materializes a scratch copy rather than intentionally patching the anchor,
* ``git apply --check`` then ``git apply`` the diff (named refusals,
  same contract as python.repo.diff_apply_full_testgate.v1),
* discovers the whole pytest suite (empty -> loud refusal),
* runs ``coverage run -m pytest -q`` then ``coverage json`` and
  intersects missing executable lines with the diff's new-side changed
  ranges: ``diff_miss_lines`` are the evidence rows.
* local_gate PASS only when pytest reports at least one pass and no failures,
  every changed Python file appears in the coverage report, no diff-hunk
  lines are excluded, and a nonempty measured executable hunk meets the
  threshold. Hunk ranges include unchanged context lines. A local PASS
  remains UNRESOLVED because reports are unauthenticated.

Configured pytest/coverage discovery can omit relevant behavior. The scratch
copy is not an OS sandbox, and reports are not authenticated against hostile
project code or plugins.

Laws:
* fail closed: PATH_*, DIFF_EMPTY, ANCHOR_NOT_DIRECTORY, GIT_UNAVAILABLE,
  COVERAGE_UNAVAILABLE, NO_TESTS_DISCOVERED, DIFF_DOES_NOT_APPLY,
  TIMEOUT, SUITE_RED (a failing suite makes coverage untrustworthy).
* degrade loudly: coverage absent -> gate PASS_BLIND (recorded, verified
  stays False) — never a silent pretending pass.
* artifact carries no wall-clock fields; deterministic fixture reruns are
  byte-identical. The scratch tree and its .coverage data are deleted after.
* semantic honesty: statement coverage counts a ``def`` line executing
  at import — "line executed" is a floor, not proof of behavior; the
  gate_law row documents this and deep behavioral adequacy belongs to
  test-quality capabilities.

Inputs (kwargs, repo-confined):
  anchor_path        clean tree the diff was cut against (read-only)
  diff_path          unified diff artifact under test
  output_path        summary artifact (registry result_fields mirror)
  python_executable  interpreter used for coverage/pytest (default: this one)
  timeout_s          wall-clock cap for the suite call (default 300)
  min_coverage_ratio float threshold (default 1.0 — every changed line)

result_fields: adapter, anchor_path, diff_sha256, tests_discovered,
tests_passed, tests_failed, tests_skipped, pytest_returncode, test_report_status,
coverage_scope, unmeasured_files, unmeasured_lines, diff_executable_lines,
diff_covered_ratio, diff_miss_lines, gate, local_gate,
test_evidence_authentication, complete, output_path, output_sha256,
output_verified, verified.
"""

from __future__ import annotations

try:  # the module is importable both as a package member and as a script
    from canonical.runtime.bound_capabilities import _diff_gate_anchor_v1 as _gate_anchor
    from canonical.runtime.bound_capabilities import quality_flake_detect_v1 as _junit_report
except ImportError:  # pragma: no cover - direct script execution
    import _diff_gate_anchor_v1 as _gate_anchor  # type: ignore
    import quality_flake_detect_v1 as _junit_report  # type: ignore

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from canonical.runtime.bound_capabilities.python_review_diff_static_triage import (
    _parse_diff_ranges,
)

SCHEMA = "PROJECT_BRAIN_DIFF_COVERAGE_GATE_V1"


def _fail(reason: str) -> None:
    raise SystemExit(json.dumps({"error": True,
                                 "capability": "python.review.diff_coverage_gate.v1",
                                 "reason": reason}, indent=2, sort_keys=True))


def _safe_path(repo: Path, rel: str, must_exist: bool = False) -> Path:
    if not rel or not isinstance(rel, str):
        _fail("MISSING_OR_INVALID_PATH_ARGUMENT")
    p = (repo / rel).resolve()
    if p != repo and repo not in p.parents:
        _fail("PATH_ESCAPE:" + rel)
    if must_exist and not p.exists():
        _fail("PATH_MISSING:" + rel)
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
    if not anchor_abs.is_dir():
        _fail("ANCHOR_NOT_DIRECTORY")
    diff_rel = str(args.get("diff_path") or "")
    diff_abs = _safe_path(repo, diff_rel, must_exist=True)
    diff_text = diff_abs.read_text(encoding="utf-8", errors="replace")
    if not diff_text.strip():
        _fail("DIFF_EMPTY")
    changed, _created = _parse_diff_ranges(diff_text)
    py_changed = {p: r for p, r in changed.items() if p.endswith(".py")}
    out_rel = str(args.get("output_path") or "")
    out_abs = _safe_path(repo, out_rel)
    timeout_s = int(args.get("timeout_s") or 300)
    python_exe = str(args.get("python_executable") or sys.executable)
    min_ratio = float(args.get("min_coverage_ratio") if args.get("min_coverage_ratio") is not None else 1.0)

    git_probe = subprocess.run(["git", "--version"], capture_output=True, text=True,
                               timeout=min(timeout_s, 30))
    if git_probe.returncode != 0:
        _fail("GIT_UNAVAILABLE")
    cov_probe = subprocess.run([python_exe, "-m", "coverage", "--version"],
                               capture_output=True, text=True, timeout=min(timeout_s, 30))
    coverage_on = cov_probe.returncode == 0 and "overage" in cov_probe.stdout

    anchor_abs = _gate_anchor.resolve_anchor(repo, anchor_abs, diff_abs, timeout_s)
    scratch_base = _gate_anchor.scratch_base(anchor_abs, out_abs.parent)
    scratch = Path(tempfile.mkdtemp(prefix="_cov_tree_", dir=scratch_base))
    try:
        shutil.copytree(anchor_abs, scratch, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
        check = subprocess.run(["git", "apply", "--check", str(diff_abs)],
                               cwd=scratch, capture_output=True, text=True,
                               timeout=min(timeout_s, 60))
        if check.returncode != 0:
            _fail("DIFF_DOES_NOT_APPLY:" + (check.stderr.strip().splitlines() or ["<empty>"])[0][:200])
        applied = subprocess.run(["git", "apply", str(diff_abs)],
                                 cwd=scratch, capture_output=True, text=True,
                                 timeout=min(timeout_s, 60))
        if applied.returncode != 0:
            _fail("DIFF_APPLY_FAILED_AFTER_CHECK")

        tests = sorted(str(p.relative_to(scratch))
                       for p in scratch.rglob("*.py")
                       if p.name.startswith("test_") or p.name.endswith("_test.py"))
        if not tests:
            _fail("NO_TESTS_DISCOVERED")

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        # Do not let an inherited COVERAGE_FILE reuse data from another run.
        env["COVERAGE_FILE"] = str(scratch / ".coverage")
        (scratch / ".coverage").unlink(missing_ok=True)
        with tempfile.TemporaryDirectory(prefix="brain-coverage-report-") as report_dir:
            report_path = Path(report_dir) / "results.xml"
            command = ([python_exe, "-m", "coverage", "run", "-m", "pytest"]
                       if coverage_on else [python_exe, "-m", "pytest"])
            command += ["-q", "-p", "no:cacheprovider", f"--junitxml={report_path}"]
            try:
                suite = subprocess.run(command, cwd=scratch, capture_output=True, text=True,
                                       timeout=timeout_s, env=env)
            except subprocess.TimeoutExpired:
                _fail("TIMEOUT")
            try:
                cases = _junit_report._junit_cases(report_path)
                report_status = "READABLE"
            except (OSError, ET.ParseError, ValueError):
                cases = []
                report_status = "UNAVAILABLE_OR_INVALID"
        passed = sum(outcome == "passed" for _, outcome in cases)
        failed = sum(outcome == "failed" for _, outcome in cases)
        skipped = sum(outcome == "skipped" for _, outcome in cases)
        suite_green = (suite.returncode == 0 and report_status == "READABLE"
                       and passed > 0 and failed == 0)
        miss_rows = []
        unmeasured_files = sorted(py_changed)
        unmeasured_lines = []
        ratio = None
        executable_changed = 0
        scope = "COVERAGE_TOOL_UNAVAILABLE"
        if not coverage_on:
            gate = "PASS_BLIND" if suite_green else "FAIL"
        else:
            if not suite_green:
                _fail("SUITE_RED:pytest needs a passing case, no failures/errors, "
                      "zero exit, and a readable JUnit report")
            jf = scratch / "_cov.json"
            rep = subprocess.run([python_exe, "-m", "coverage", "json",
                                  "-o", str(jf), "--quiet"],
                                 cwd=scratch, capture_output=True, text=True,
                                 timeout=min(timeout_s, 120), env=env)
            if rep.returncode != 0 or not jf.is_file():
                _fail("COVERAGE_JSON_FAILED")
            try:
                doc = json.loads(jf.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                _fail("COVERAGE_JSON_NOT_JSON")
            if not isinstance(doc, dict) or not isinstance(doc.get("files"), dict):
                _fail("COVERAGE_JSON_INVALID")
            # Coverage keys may be absolute or relative. Only an exact path in
            # this scratch tree can cover the changed file; suffix matches can
            # accidentally credit an unrelated file with the same name.
            norm = {}
            for filename, row in doc["files"].items():
                if not isinstance(filename, str) or not isinstance(row, dict):
                    continue
                try:
                    rel = (scratch / filename).resolve().relative_to(scratch.resolve()).as_posix()
                except (OSError, ValueError):
                    continue
                executed = row.get("executed_lines")
                missing = row.get("missing_lines")
                excluded = row.get("excluded_lines")
                if (not isinstance(executed, list) or not isinstance(missing, list)
                        or not isinstance(excluded, list)
                        or any(type(n) is not int or n < 1 for n in executed + missing + excluded)
                        or set(executed) & set(missing)):
                    continue
                norm[rel] = (set(executed), set(missing), set(excluded))
            unmeasured_files = [rel for rel in sorted(py_changed) if rel not in norm]
            for rel in sorted(py_changed):
                if rel not in norm:
                    continue
                executed, missing, excluded = norm[rel]
                executable = executed | missing
                # Use set intersection instead of walking a potentially huge
                # new-file range, and count each line only once across hunks.
                in_diff = {ln for ln in executable if _in_ranges(py_changed[rel], ln)}
                executable_changed += len(in_diff)
                miss_rows.extend({"file": rel, "line": ln} for ln in sorted(in_diff & missing))
                unmeasured_lines.extend({"file": rel, "line": ln} for ln in sorted(excluded)
                                        if _in_ranges(py_changed[rel], ln))
            if not py_changed:
                scope = "NO_PYTHON_CHANGES"
            elif unmeasured_files:
                scope = "UNMEASURED_CHANGED_FILES"
            elif unmeasured_lines:
                scope = "EXCLUDED_DIFF_LINES"
            elif not executable_changed:
                scope = "NO_EXECUTABLE_LINES_IN_DIFF_HUNKS"
            else:
                scope = "MEASURED"
                ratio = (executable_changed - len(miss_rows)) / executable_changed
            gate = "PASS" if ratio is not None and ratio >= min_ratio else "FAIL"
    finally:
        if scratch.exists():
            shutil.rmtree(scratch, ignore_errors=True)

    complete = scope == "MEASURED"
    local_gate = gate
    if gate == "PASS":
        gate = "UNRESOLVED__UNAUTHENTICATED_EVIDENCE"
    verified = False
    artifact = {
        "schema": SCHEMA,
        "anchor_path": anchor_rel,
        "diff_path": diff_rel,
        "diff_sha256": _sha256(diff_text.encode("utf-8")),
        "tests_discovered": len(tests),  # filename-shaped files, not executed cases
        "test_files": tests,
        "tests_passed": passed,
        "tests_failed": failed,
        "tests_skipped": skipped,
        "pytest_returncode": suite.returncode,
        "test_report_status": report_status,
        "coverage_tool": "UNAVAILABLE" if not coverage_on else "present",
        "coverage_scope": scope,
        "unmeasured_files": unmeasured_files,
        "unmeasured_lines": unmeasured_lines,
        "diff_executable_lines": (executable_changed if coverage_on else None),
        "diff_covered_ratio": ratio,
        "diff_miss_lines": miss_rows,
        "min_coverage_ratio": min_ratio,
        "gate": gate,
        "local_gate": local_gate,
        "test_evidence_authentication": "UNAUTHENTICATED",
        "gate_law": ("local PASS requires a successful pytest exit, a reported pass, no "
                     "reported failures/errors, every changed Python file measured, "
                     "no excluded lines in the diff hunks, and a nonempty measured "
                     "executable hunk meeting the threshold; reports are not authenticated, "
                     "hunk ranges include context, statement coverage is not behavior "
                     "proof, and this is not a hostile-code sandbox"),
        "complete": complete,
        "verified": verified,
    }
    out_abs.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(artifact, indent=2, ensure_ascii=False) + "\n"
    out_abs.write_text(text, encoding="utf-8")
    out_verified = json.loads(out_abs.read_text(encoding="utf-8")) == artifact

    return {
        "adapter": "python_review_diff_coverage_gate",
        "anchor_path": anchor_rel,
        "diff_sha256": artifact["diff_sha256"],
        "tests_discovered": len(tests),
        "tests_passed": passed,
        "tests_failed": failed,
        "tests_skipped": skipped,
        "pytest_returncode": suite.returncode,
        "test_report_status": report_status,
        "coverage_scope": scope,
        "unmeasured_files": unmeasured_files,
        "unmeasured_lines": unmeasured_lines,
        "diff_executable_lines": executable_changed if coverage_on else None,
        "diff_covered_ratio": ratio,
        "diff_miss_lines": len(miss_rows),
        "gate": gate,
        "local_gate": local_gate,
        "test_evidence_authentication": "UNAUTHENTICATED",
        "complete": complete,
        "output_path": out_rel,
        "output_sha256": _sha256(text.encode("utf-8")),
        "output_verified": out_verified,
        "verified": bool(verified),
    }


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
