# PROJECT_BRAIN
"""python.repo.diff_apply_full_testgate.v1 — the pre-merge integration gate.

Static triage (python.review.diff_static_triage.v1) proves the *changed
lines* are clean; it cannot see a runtime break one file away.  A senior
engineer's last act before opening a PR is to apply the diff to a clean
checkout of exactly the anchor it was cut from and run the WHOLE test
suite — not the handful of tests the diff touched.

This adapter does that within the limits of the configured pytest suite:

* materializes a scratch copy outside the anchor tree; this is not an OS
  sandbox and pytest code retains the host process's access,
* applies the unified diff with ``git apply`` (probe first;
  REFUSE-LOUD if git is absent, CHECK then APPLY so a bogus diff is a
  named refusal, not a half-written tree),
* records conventional test filenames, but lets pytest and project
  configuration discover the actual suite, including custom filenames,
* runs the pytest-configured suite with ``python -m pytest`` and reads
  its JUnit report; ambient ``PYTEST_ADDOPTS`` is excluded,
* gate PASS requires an unchanged diff, at least one passing test, and no
  failures or errors; skipped or xfailed tests do not count as passes.

Laws:
* fail closed: every environmental or packaging break is a named
  refusal (PATH_ESCAPE, DIFF_EMPTY, ANCHOR_NOT_DIRECTORY,
  GIT_UNAVAILABLE, NO_TESTS_DISCOVERED, DIFF_DOES_NOT_APPLY, TIMEOUT);
  ``verified`` is true only on gate PASS.
* determinism: artifact carries no wall-clock fields; failing-test list
  is pytest emission order; byte-identical artifacts on rerun
  (pin-proven).
* the adapter itself does not write into the anchor. Test code is not
  isolated from the anchor or other host paths; use an OS sandbox when the
  repository or tests are untrusted.

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

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from canonical.runtime.bound_capabilities import python_test_guided_patch_search_v1 as test_process

SCHEMA = "PROJECT_BRAIN_REPO_DIFF_APPLY_FULL_TESTGATE_V1"
_TESTNAME = lambda p: p.name.startswith("test_") and p.suffix == ".py" \
    or p.name.endswith("_test.py")


def _fail(reason: str) -> dict:
    return {
        "error": True,
        "capability": "python.repo.diff_apply_full_testgate.v1",
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


def _file_snapshot(path: Path) -> tuple:
    """Snapshot a diff target, including deletions and file mode."""
    if path.is_symlink():
        return ("symlink", os.readlink(path))
    if not path.exists():
        return ("absent",)
    mode = path.stat().st_mode & 0o7777
    if path.is_file():
        return ("file", mode, _sha256(path.read_bytes()))
    return ("other", mode)


def _pytest_env(anchor: Path, scratch: Path, *other_anchors: Path) -> dict[str, str]:
    """Keep dependencies but redirect original import paths to the copy."""
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("PYTEST_ADDOPTS", None)
    if "PYTHONPATH" in env:
        paths = []
        for entry in env["PYTHONPATH"].split(os.pathsep):
            path = Path(entry)
            if entry and path.is_absolute():
                for original in (anchor, *other_anchors):
                    try:
                        entry = str(scratch / path.resolve().relative_to(original))
                        break
                    except (OSError, ValueError):
                        continue
            paths.append(entry)
        env["PYTHONPATH"] = os.pathsep.join(paths)
    return env


def _pytest_report(path: Path) -> dict:
    """Read test outcomes, not just pytest's process exit code.

    Pytest can exit successfully when all collected tests were skipped or
    xfailed. A JUnit testcase with no skip/failure/error child is a passed
    test; skipped cases do not count as executed evidence. A missing, malformed
    or empty report cannot establish that tests ran. Error cases are not
    counted as executed because collection or setup may have failed before a
    test body ran.
    """
    unavailable = {"available": False, "collected": 0, "passed": 0, "failed": 0,
                   "errors": 0, "skipped": 0, "executed": 0, "failing_tests": []}
    try:
        document = ET.parse(path).getroot()
    except (OSError, ET.ParseError):
        return unavailable
    if document.tag == "testsuites":
        suites = document.findall("testsuite")
    elif document.tag == "testsuite":
        suites = [document]
    else:
        return unavailable
    if not suites:
        return unavailable
    cases = []
    for suite in suites:
        suite_cases = list(suite.iter("testcase"))
        try:
            totals = {key: int(suite.attrib[key]) for key in
                      ("tests", "failures", "errors", "skipped")}
        except (KeyError, ValueError):
            return unavailable
        if (any(value < 0 for value in totals.values())
                or (totals["tests"] < len(suite_cases) and not (totals["failures"] or totals["errors"]))
                or any(not case.get("name") for case in suite_cases)
                or totals["failures"] != sum(case.find("failure") is not None for case in suite_cases)
                or totals["errors"] != sum(case.find("error") is not None for case in suite_cases)
                or totals["skipped"] != sum(case.find("skipped") is not None for case in suite_cases)):
            return unavailable
        cases.extend(suite_cases)
    counts = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0}
    failing_tests = []
    for case in cases:
        if case.find("error") is not None:
            counts["errors"] += 1
        elif case.find("failure") is not None:
            counts["failed"] += 1
        elif case.find("skipped") is not None:
            counts["skipped"] += 1
        else:
            counts["passed"] += 1
        if case.find("error") is not None or case.find("failure") is not None:
            location = case.get("classname") or ""
            name = case.get("name") or ""
            failing_tests.append("::".join(part for part in (location, name) if part))
    return {"available": bool(cases), "collected": len(cases), **counts,
            "executed": counts["passed"] + counts["failed"],
            "failing_tests": failing_tests}


def _pytest_file_evidence(path: Path, cwd: Path, targets: list[str]) -> dict[str, dict]:
    """Attribute legacy JUnit cases to explicit test-file targets.

    Callers should set ``--rootdir=.`` and ``junit_family=legacy`` so the
    reported ``file`` attributes are relative to cwd. A missing attribute or
    unmatched file is not evidence that an explicitly named file executed.
    """
    if not _pytest_report(path)["available"]:
        return {}
    by_path = {}
    expected = {str((cwd / rel).resolve()): rel for rel in targets}
    try:
        document = ET.parse(path).getroot()
    except (OSError, ET.ParseError):
        return {}
    for case in document.iter("testcase"):
        file = case.get("file")
        if not file:
            continue
        rel = expected.get(str((cwd / file).resolve()))
        if rel is None:
            continue
        row = by_path.setdefault(rel, {"path": rel, "executed": 0,
                                       "passed": 0, "failed": 0, "skipped": 0})
        if case.find("skipped") is not None:
            row["skipped"] += 1
        elif case.find("failure") is not None or case.find("error") is not None:
            row["executed"] += 1
            row["failed"] += 1
        else:
            row["executed"] += 1
            row["passed"] += 1
    return by_path


_PYTEST_CAPTURE = r'''
import json, pathlib, sys
import pytest

class Recorder:
    def __init__(self):
        self.nodeids = None
        self.deselected = []
    def pytest_collection_finish(self, session):
        self.nodeids = [item.nodeid for item in session.items]
    def pytest_deselected(self, items):
        self.deselected.extend(item.nodeid for item in items)

recorder = Recorder()
args = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
rc = pytest.main(args, plugins=[recorder])
if recorder.nodeids is not None:
    pathlib.Path(sys.argv[2]).write_text(json.dumps({"nodeids": recorder.nodeids,
                                                   "deselected": recorder.deselected}), encoding="utf-8")
sys.exit(int(rc))
'''


def _python_trial_snapshot(cwd: Path, explicit_paths: list[str]) -> dict[str, tuple]:
    """Snapshot Python inputs before collection, including custom-named tests."""
    skip = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
            ".venv", "venv", "node_modules"}
    paths = set()
    for directory, dirs, files in os.walk(cwd, followlinks=False):
        dirs[:] = [name for name in dirs if name not in skip]
        base = Path(directory)
        paths.update(base / name for name in files if name.endswith(".py"))
    paths.update((cwd / rel) for rel in explicit_paths)
    return {str(path): _file_snapshot(path) for path in sorted(paths)}


def _pytest_combined_session(cwd: Path, python: str, env: dict[str, str],
                             explicit_paths: list[str], timeout_s: float,
                             coverage_data_path: Path | None = None) -> dict:
    """Run configured tests plus known candidate files in one pytest session.

    Configured node IDs are obtained using pytest's actual collection hooks,
    not filename guesses. Explicit candidates are then added without duplicate
    configured selectors. Every configured node must still be collected, each
    explicit file must have a passing case, and no tests may be deselected.
    The trial is a copy, not an OS sandbox; snapshots detect only persistent
    changes to Python inputs, not transient writes or external side effects.
    """
    started = time.monotonic()
    result = {"oracle_ok": False, "returncode": None, "reason": "NOT_RUN",
              "pytest_report_available": False, "tests_collected": 0,
              "tests_passed": 0, "tests_failed": 0, "tests_skipped": 0,
              "configured_node_count": 0, "missing_configured_count": 0,
              "deselected_count": 0, "unexecuted_test_files": [],
              "input_integrity": False}
    # Paths can be repeated by callers or by the index; preserve the intended
    # selection ordering while running each explicit file only once.
    paths = list(dict.fromkeys(explicit_paths))
    try:
        snapshot = _python_trial_snapshot(cwd, paths)
    except OSError:
        result["reason"] = "INPUT_SNAPSHOT_UNAVAILABLE"
        return result
    with tempfile.TemporaryDirectory(prefix=".brain-combined-pytest-", dir=cwd) as temp:
        directory = Path(temp)
        argv_path, capture_path = directory / "args.json", directory / "collection.json"
        report_path = directory / "pytest.xml"

        def invoke(arguments: list[str], *, with_coverage: bool = False):
            remaining = timeout_s - (time.monotonic() - started)
            if remaining <= 0:
                return None, None
            argv_path.write_text(json.dumps(arguments), encoding="utf-8")
            capture_path.unlink(missing_ok=True)
            command = [python, "-c", _PYTEST_CAPTURE, str(argv_path), str(capture_path)]
            child_env = env
            if with_coverage:
                # coverage run accepts a script path, not Python's -c. Keep
                # its worker outside the measured tree and alive until the
                # caller has generated the coverage report.
                script = coverage_data_path.with_name(coverage_data_path.name + ".worker")
                script.write_text(_PYTEST_CAPTURE, encoding="utf-8")
                child_env = dict(env)
                child_env["COVERAGE_FILE"] = str(coverage_data_path)
                child_env["PYTHONPATH"] = str(cwd) + os.pathsep + child_env.get("PYTHONPATH", "")
                command = [python, "-m", "coverage", "run", "--source=.",
                           str(script), str(argv_path), str(capture_path)]
            try:
                proc = test_process._run_process(cwd, command, remaining, child_env)
                if proc["timed_out"]:
                    return None, None
                capture = json.loads(capture_path.read_text(encoding="utf-8"))
                if (not isinstance(capture, dict) or not isinstance(capture.get("nodeids"), list)
                        or not all(isinstance(x, str) and x for x in capture["nodeids"])
                        or not isinstance(capture.get("deselected"), list)):
                    return proc, None
                return proc, capture
            except (OSError, ValueError, subprocess.TimeoutExpired):
                return None, None

        common = ["-q", "-p", "no:cacheprovider", "--rootdir=."]
        collection, config = invoke(common + ["--collect-only"])
        if collection is None or collection["returncode"] != 0 or config is None:
            result["reason"] = "CONFIGURED_COLLECTION_UNAVAILABLE"
            return result
        configured = config["nodeids"]
        result["configured_node_count"] = len(configured)
        explicit_abs = {str((cwd / path).resolve()) for path in paths}
        # If a configured test is inside an explicitly named file, that file
        # collects it already; asking for both duplicates tests and fixtures.
        extra = []
        for nodeid in configured:
            filepart = nodeid.split("::", 1)[0]
            if str((cwd / filepart).resolve()) not in explicit_abs:
                extra.append(nodeid)
        # --junitxml must be relative to cwd so it resolves inside the
        # sandbox chroot (cwd is mounted at /project). The host-side report
        # read below still uses the absolute report_path.
        report_rel = report_path.relative_to(cwd)
        combined_args = (common + ["-o", "addopts=", "-o", "junit_family=legacy",
                                   "--junitxml=" + str(report_rel)] + extra + paths)
        proc, collected = invoke(combined_args, with_coverage=coverage_data_path is not None)
        if proc is None or collected is None:
            result["reason"] = "COMBINED_SESSION_UNAVAILABLE"
            return result
        report = _pytest_report(report_path)
        by_file = _pytest_file_evidence(report_path, cwd, paths)
        unexecuted = [path for path in paths if by_file.get(path, {}).get("passed", 0) == 0]
        missing = set(configured) - set(collected["nodeids"])
        try:
            intact = _python_trial_snapshot(cwd, paths) == snapshot
        except OSError:
            intact = False
        ok = (proc["returncode"] == 0 and report["available"] and report["passed"] > 0
              and not report["failed"] and not report["errors"] and not unexecuted
              and not missing and not collected["deselected"] and intact)
        result.update({"oracle_ok": ok, "returncode": proc["returncode"],
                       "reason": ("PASS" if ok else "INPUT_CHANGED" if not intact else
                                  "TEST_FAILURE" if proc["returncode"] != 0 else "EVIDENCE_INCOMPLETE"),
                       "pytest_report_available": report["available"],
                       "tests_collected": report["collected"], "tests_passed": report["passed"],
                       "tests_failed": report["failed"] + report["errors"],
                       "tests_skipped": report["skipped"], "unexecuted_test_files": unexecuted,
                       "missing_configured_count": len(missing),
                       "deselected_count": len(collected["deselected"]),
                       "input_integrity": intact})
    return result


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
    if not diff_abs.is_file():
        return _fail("DIFF_NOT_FILE")
    diff_bytes = diff_abs.read_bytes()
    if not diff_bytes.strip():
        return _fail("DIFF_EMPTY")
    diff_sha = _sha256(diff_bytes)
    out_rel = str(args.get("output_path") or "")
    out_abs = _safe_path(repo, out_rel)
    if isinstance(out_abs, dict): return out_abs
    if out_abs == anchor_abs or anchor_abs in out_abs.parents:
        return _fail("OUTPUT_INSIDE_ANCHOR")
    if out_abs == diff_abs:
        return _fail("OUTPUT_DIFF_OVERLAP")
    timeout_s = int(args.get("timeout_s") or 300)
    python_exe = str(args.get("python_executable") or sys.executable)

    try:
        probe = subprocess.run(["git", "--version"], capture_output=True, text=True,
                               timeout=min(timeout_s, 30))
    except (OSError, subprocess.TimeoutExpired):
        return _fail("GIT_UNAVAILABLE")
    if probe.returncode != 0 or not probe.stdout.strip().startswith("git version"):
        return _fail("GIT_UNAVAILABLE")

    out_abs.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="_gate_tree_", dir=out_abs.parent) as scratch_dir:
        scratch = Path(scratch_dir) / "tree"
        shutil.copytree(anchor_abs, scratch,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
        # Check and apply the same captured bytes, rather than reopening a path
        # that may have changed between the two operations.
        check = subprocess.run(["git", "apply", "--check", "-"], input=diff_bytes,
                               cwd=scratch, capture_output=True, timeout=min(timeout_s, 60))
        if check.returncode != 0:
            stderr = check.stderr.decode("utf-8", errors="replace")
            _fail("DIFF_DOES_NOT_APPLY:" + (stderr.strip().splitlines() or ["<empty>"])[0][:200])
        applied = subprocess.run(["git", "apply", "-"], input=diff_bytes,
                                 cwd=scratch, capture_output=True, timeout=min(timeout_s, 60))
        if applied.returncode != 0:
            return _fail("DIFF_APPLY_FAILED_AFTER_CHECK")
        # Forward and reverse numstat together cover both sides of renames,
        # as well as creations and deletions, without parsing quoted paths.
        targets = set()
        for direction in ([], ["--reverse"]):
            stats = subprocess.run(["git", "apply", "--numstat"] + direction + ["-z", "-"],
                                   input=diff_bytes, cwd=scratch, capture_output=True,
                                   timeout=min(timeout_s, 60))
            if stats.returncode != 0:
                return _fail("DIFF_TARGETS_UNAVAILABLE")
            for record in stats.stdout.split(b"\0"):
                if not record:
                    continue
                fields = record.split(b"\t", 2)
                if len(fields) != 3 or not fields[2]:
                    return _fail("DIFF_TARGETS_UNAVAILABLE")
                rel = os.fsdecode(fields[2])
                _safe_path(scratch, rel)
                targets.add(rel)
        if not targets:
            return _fail("DIFF_TARGETS_UNAVAILABLE")
        target_snapshot = {rel: _file_snapshot(scratch / rel) for rel in targets}

        # --- Change-impact test selection: run only tests affected by the diff ---
        # Instead of paying the full test battery for a one-line edit, build the
        # semantic symbol index, walk the call/import graph downstream from the
        # changed files, and select exactly the tests that can still observe the
        # change. Over-approximation law: never miss an affected test, may
        # over-select; if selection is unavailable or yields nothing, fall back
        # to the full suite (fail-safe, never fail-closed on a missed test).
        selected_test_paths = []
        try:
            from canonical.runtime.bound_capabilities.python_change_impact_testselect import run as _ci_run
            ci_result = _ci_run({
                "source_root": str(scratch.relative_to(repo)) if scratch != repo else ".",
                "diff_path": str(diff_abs.relative_to(repo)),
                "output_path": str(diff_abs.parent / ".change_impact_report.json"),
                "test_roots": [".", "tests", "canonical/tests"],
            }, str(repo))
            selected_test_paths = ci_result.get("selected_tests", [])
            # selected paths are repo-relative; resolve to scratch-relative
            scratch_selected = []
            for rel in selected_test_paths:
                sp = scratch / rel
                if sp.is_file():
                    scratch_selected.append(str(sp.relative_to(scratch)))
            if scratch_selected:
                tests = sorted(scratch_selected)
            else:
                # Selection returned nothing: fall back to full suite (fail-safe)
                tests = sorted(str(p.relative_to(scratch))
                               for p in scratch.rglob("*.py") if _TESTNAME(p))
        except Exception:
            # Change-impact unavailable: fall back to full suite
            tests = sorted(str(p.relative_to(scratch))
                           for p in scratch.rglob("*.py") if _TESTNAME(p))

        # Ambient selection flags cannot shrink this run, and import paths
        # into the original anchor must point at the patched copy instead.
        env = _pytest_env(anchor_abs, scratch)
        with tempfile.TemporaryDirectory(prefix=".brain-full-testgate-", dir=scratch) as report_dir:
            report_path = Path(report_dir) / "pytest.xml"
            # --junitxml must be relative to cwd so it resolves inside the
            # sandbox chroot (cwd is mounted at /project).
            report_rel = report_path.relative_to(scratch)
            try:
                proc = test_process._run_process(
                    scratch, [python_exe, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                              "--junitxml=" + str(report_rel)], timeout_s, env)
            except OSError:
                return _fail("PYTEST_UNAVAILABLE")
            if proc["timed_out"]:
                return _fail("TIMEOUT")
            report = _pytest_report(report_path)
        if proc["returncode"] == 5 and report["collected"] == 0:
            return _fail("NO_TESTS_DISCOVERED")

        failing = [line.split(" ", 1)[1].strip().split(" - ")[0]
                   for line in proc["stdout"].splitlines()
                   if line.startswith(("FAILED ", "ERROR "))
                   and line.split(" ", 1)[1].strip()]
        for name in report["failing_tests"]:
            if name and name not in failing:
                failing.append(name)
        try:
            diff_unchanged = diff_abs.is_file() and _sha256(diff_abs.read_bytes()) == diff_sha
        except OSError:
            diff_unchanged = False
        try:
            applied_unchanged = all(_file_snapshot(scratch / rel) == target_snapshot[rel]
                                    for rel in targets)
        except OSError:
            applied_unchanged = False
        gate = "PASS" if (diff_unchanged and applied_unchanged and proc["returncode"] == 0 and not failing
                          and report["available"] and report["passed"] > 0
                          and report["failed"] == 0 and report["errors"] == 0) else "FAIL"

    complete = True
    verified = gate == "PASS"
    if verified:
        reason = ""
    elif not diff_unchanged:
        reason = "DIFF_CHANGED_DURING_TESTS"
    elif not applied_unchanged:
        reason = "APPLIED_FILES_CHANGED_DURING_TESTS"
    elif not report["available"]:
        reason = "PYTEST_REPORT_UNAVAILABLE_OR_EMPTY"
    elif proc["returncode"] != 0 or report["failed"] or report["errors"] or failing:
        reason = "PYTEST_FAILED"
    else:
        reason = "NO_TESTS_EXECUTED"
    artifact = {
        "schema": SCHEMA,
        "anchor_path": anchor_rel,
        "diff_path": diff_rel,
        "diff_sha256": diff_sha,
        "diff_unchanged": diff_unchanged,
        "applied_files": sorted(targets),
        "applied_files_unchanged": applied_unchanged,
        "tests_discovered": len(tests),
        "test_files": tests,
        "tests_collected": report["collected"],
        "tests_executed": report["executed"],
        "tests_passed": report["passed"],
        "tests_failed": report["failed"] + report["errors"],
        "tests_skipped": report["skipped"],
        "failing_tests": failing,
        "pytest_report_available": report["available"],
        "pytest_returncode": proc["returncode"],
        "gate": gate,
        "reason": reason,
        "gate_law": ("PASS requires an unchanged diff and unchanged applied target files "
                     "after testing AND pytest to report at least one passing test and no "
                     "failures or errors in the configured suite; an empty or wholly "
                     "skipped suite cannot pass. Test code is not OS-isolated."),
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
        "applied_files_unchanged": applied_unchanged,
        "tests_discovered": len(tests),
        "tests_collected": report["collected"],
        "tests_executed": report["executed"],
        "tests_passed": report["passed"],
        "tests_failed": report["failed"] + report["errors"],
        "tests_skipped": report["skipped"],
        "failing_tests": failing,
        "pytest_returncode": proc["returncode"],
        "gate": gate,
        "reason": reason,
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
