# PROJECT_BRAIN
"""python.repo.diff_apply_full_testgate.v1 — the pre-merge integration gate.

Static triage (python.review.diff_static_triage.v1) proves the *changed
lines* are clean; it cannot see a runtime break one file away.  A senior
engineer's last act before opening a PR is to apply the diff to a clean
checkout of exactly the anchor it was cut from and run the WHOLE test
suite — not the handful of tests the diff touched.

This adapter does that, zero-trust:

* materializes a scratch copy of the anchor tree (the anchor is never
  mutated — pin-proven),
* applies the unified diff with ``git apply`` (probe first;
  REFUSE-LOUD if git is absent, CHECK then APPLY so a bogus diff is a
  named refusal, not a half-written tree),
* discovers tests by filename convention over the whole scratch tree —
  an empty suite is a loud REFUSAL, never a vacuous PASS,
* runs the full suite with ``python -m pytest`` (byte-code and cache
  writes suppressed: the artifact must be byte-identical on rerun),
* gate PASS only with the suite green; failing tests are listed by
  name in the artifact as evidence.

Laws:
* fail closed: every environmental or packaging break is a named
  refusal (PATH_ESCAPE, DIFF_EMPTY, ANCHOR_NOT_DIRECTORY,
  GIT_UNAVAILABLE, NO_TESTS_DISCOVERED, DIFF_DOES_NOT_APPLY, TIMEOUT);
  ``verified`` is true only on gate PASS.
* determinism: artifact carries no wall-clock fields; failing-test list
  is pytest emission order; byte-identical artifacts on rerun
  (pin-proven).
* zero anchor mutation: the fixture tree manifest is hashed before and
  after by the pins.

Inputs (kwargs, repo-confined):
  anchor_path        clean tree the diff was cut against (read-only)
  diff_path          unified diff artifact under test
  output_path        summary artifact (registry result_fields mirror)
  python_executable  interpreter used for pytest (default: this one)
  timeout_s          wall-clock cap for the pytest call (default 300)

result_fields: adapter, anchor_path, diff_sha256, tests_discovered,
tests_failed, gate, complete, output_path, output_sha256,
output_verified, verified.
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

SCHEMA = "PROJECT_BRAIN_REPO_DIFF_APPLY_FULL_TESTGATE_V1"
_TESTNAME = lambda p: p.name.startswith("test_") and p.suffix == ".py" \
    or p.name.endswith("_test.py")


def _fail(reason: str) -> None:
    raise SystemExit(json.dumps({"error": True,
                                 "capability": "python.repo.diff_apply_full_testgate.v1",
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
    out_rel = str(args.get("output_path") or "")
    out_abs = _safe_path(repo, out_rel)
    timeout_s = int(args.get("timeout_s") or 300)
    python_exe = str(args.get("python_executable") or sys.executable)

    probe = subprocess.run(["git", "--version"], capture_output=True, text=True,
                           timeout=min(timeout_s, 30))
    if probe.returncode != 0 or not probe.stdout.strip().startswith("git version"):
        _fail("GIT_UNAVAILABLE")

    anchor_abs = _gate_anchor.resolve_anchor(repo, anchor_abs, diff_abs, timeout_s)
    scratch = _gate_anchor.scratch_base(anchor_abs, out_abs.parent) / (
        "_gate_tree_" + _sha256(diff_text.encode("utf-8"))[:16])
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
                       for p in scratch.rglob("*.py") if _TESTNAME(p))
        if not tests:
            _fail("NO_TESTS_DISCOVERED")

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        try:
            proc = subprocess.run([python_exe, "-m", "pytest", "-q",
                                   "-p", "no:cacheprovider"],
                                  cwd=scratch, capture_output=True, text=True,
                                  timeout=timeout_s, env=env)
        except subprocess.TimeoutExpired:
            _fail("TIMEOUT")

        failing = [line.split(" ", 1)[1].strip().split(" - ")[0]
                   for line in proc.stdout.splitlines()
                   if line.startswith(("FAILED ", "ERROR "))
                   and line.split(" ", 1)[1].strip()]
        gate = "PASS" if proc.returncode == 0 and not failing else "FAIL"
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
        "failing_tests": failing,
        "gate": gate,
        "gate_law": ("PASS requires the diff to apply cleanly onto the anchor AND "
                     "the entire discovered test suite green under pytest; an empty "
                     "suite is a refusal, never a pass; the anchor tree is never "
                     "mutated"),
        "complete": complete,
    }
    out_abs.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(artifact, indent=2, ensure_ascii=False) + "\n"
    out_abs.write_text(text, encoding="utf-8")
    out_verified = json.loads(out_abs.read_text(encoding="utf-8")) == artifact

    return {
        "adapter": "python_repo_diff_apply_full_testgate",
        "anchor_path": anchor_rel,
        "diff_sha256": artifact["diff_sha256"],
        "tests_discovered": len(tests),
        "tests_failed": len(failing),
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
    ns = p.parse_args()
    print(json.dumps(run(vars(ns), Path.cwd()), indent=2, sort_keys=True))
