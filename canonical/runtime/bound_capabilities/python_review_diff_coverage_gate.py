# PROJECT_BRAIN
"""python.review.diff_coverage_gate.v1 — every changed line must be
executed by the suite, measured, not asserted.

The review trio's senior gate: lint triage (#82) proves changed lines are
name/syntax-clean, the type gate (#84) proves they are type-sound — and
NEITHER can see a changed line nothing ever executes.  Coverage is the
class a senior blocks on: "your new branch has no test."

* materializes a scratch copy of the anchor tree (never mutated),
* ``git apply --check`` then ``git apply`` the diff (named refusals,
  same contract as python.repo.diff_apply_full_testgate.v1),
* discovers the whole pytest suite (empty -> loud refusal),
* runs ``coverage run -m pytest -q`` then ``coverage json`` and
  intersects missing executable lines with the diff's new-side changed
  ranges: ``diff_miss_lines`` are the evidence rows.
* gate PASS only when the suite is green AND diff coverage on the
  diff's own .py files is exactly 100% (threshold is a parameter).

Laws:
* fail closed: PATH_*, DIFF_EMPTY, ANCHOR_NOT_DIRECTORY, GIT_UNAVAILABLE,
  COVERAGE_UNAVAILABLE, NO_TESTS_DISCOVERED, DIFF_DOES_NOT_APPLY,
  TIMEOUT, SUITE_RED (a failing suite makes coverage untrustworthy).
* degrade loudly: coverage absent -> gate PASS_BLIND (recorded, verified
  stays False) — never a silent pretending pass.
* determinism: artifact carries no wall-clock fields; byte-identical on
  rerun (pin-proven).  Scratch tree and .coverage data deleted after.
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
diff_executable_lines, diff_covered_ratio, gate, complete, output_path,
output_sha256, output_verified, verified.
"""

from __future__ import annotations

try:  # the module is importable both as a package member and as a script
    from canonical.runtime.bound_capabilities import _diff_gate_anchor_v1 as _gate_anchor
except ImportError:  # pragma: no cover - direct script execution
    import _diff_gate_anchor_v1 as _gate_anchor  # type: ignore

import hashlib
import json
import os
import shutil
import subprocess
import sys
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
    scratch = _gate_anchor.scratch_base(anchor_abs, out_abs.parent) / (
        "_cov_tree_" + _sha256(diff_text.encode("utf-8"))[:16])
    if scratch.exists():
        shutil.rmtree(scratch)
    shutil.copytree(anchor_abs, scratch,
                    ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
    try:
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
        if not coverage_on:
            # still prove the suite green so the partial gate is honest
            only = subprocess.run([python_exe, "-m", "pytest", "-q",
                                   "-p", "no:cacheprovider"], cwd=scratch,
                                  capture_output=True, text=True,
                                  timeout=timeout_s, env=env)
            suite_green = only.returncode == 0
            miss_rows = []
            ratio = None
            executable_changed = 0
            gate = "FAIL" if not suite_green else "PASS_BLIND"
        else:
            try:
                suite = subprocess.run([python_exe, "-m", "coverage", "run",
                                        "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                                       cwd=scratch, capture_output=True, text=True,
                                       timeout=timeout_s, env=env)
            except subprocess.TimeoutExpired:
                _fail("TIMEOUT")
            suite_green = suite.returncode == 0
            if not suite_green:
                _fail("SUITE_RED:coverage under a failing suite is untrustworthy evidence")
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
            miss_rows = []
            executable_changed = 0
            files = doc.get("files") or {}
            norm = {k.replace("\\", "/"): v for k, v in files.items()}
            for rel in sorted(py_changed):
                row = None
                for fname, v in norm.items():
                    if fname == rel or fname.endswith("/" + rel):
                        row = v
                        break
                if row is None:
                    continue
                executable = set(row.get("executed_lines") or []) | set(row.get("missing_lines") or [])
                for start, end in py_changed[rel]:
                    for ln in range(start, (end if end < 10 ** 9 else max(executable or {0})) + 1):
                        if ln in executable:
                            executable_changed += 1
                            if ln in set(row.get("missing_lines") or []):
                                miss_rows.append({"file": rel, "line": ln})
            ratio = 1.0 if executable_changed == 0 else (
                (executable_changed - len(miss_rows)) / executable_changed)
            gate = "PASS" if ratio >= min_ratio else "FAIL"
    finally:
        if scratch.exists():
            shutil.rmtree(scratch, ignore_errors=True)

    complete = True
    verified = gate == "PASS"
    artifact = {
        "schema": SCHEMA,
        "anchor_path": anchor_rel,
        "diff_path": diff_rel,
        "diff_sha256": _sha256(diff_text.encode("utf-8")),
        "tests_discovered": len(tests),
        "test_files": tests,
        "coverage_tool": "UNAVAILABLE" if not coverage_on else "present",
        "diff_executable_lines": (executable_changed if coverage_on else None),
        "diff_covered_ratio": ratio,
        "diff_miss_lines": miss_rows,
        "min_coverage_ratio": min_ratio,
        "gate": gate,
        "gate_law": ("PASS requires the diff to apply, the whole discovered suite "
                     "green under coverage, and >=100% (default) of the diff's "
                     "executable .py lines executed; statement coverage is a floor "
                     "not a behavior proof; tool-absent degrades to PASS_BLIND "
                     "recorded loudly; a failing suite is SUITE_RED, never data"),
        "complete": complete,
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
        "diff_executable_lines": executable_changed if coverage_on else None,
        "diff_covered_ratio": ratio,
        "diff_miss_lines": len(miss_rows),
        "gate": gate,
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
