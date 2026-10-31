"""Run existing refactoring and measured repair in the existing namespace.

A local exercise, not capability admission or an independent semantic oracle.
Only current Brain runtime/governance data, explicit project input, and the
caller's Python dependencies enter the read-only input snapshot. No Git data,
host home, inherited environment, network or package installation is required.
The entire baseline/solve/replay runs on disposable private copies. This is an
explicit exercise entry; ordinary solve() is NOT automatically confined.
Rename/move uses normal entry; synthesized repair uses the measured API.

The broker is an untrusted workload output channel, not an attestation service.
This runner contains execution effects; it does not make malicious tests honest.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys
import sysconfig
import tempfile
import time

from canonical.runtime.canonical_tree_attestation_v1 import tree_manifest
from canonical.runtime.zero_ambient_namespace_launcher_v1 import run_confined

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_CONFINED_CROSSFILE_LOCAL_EXERCISE_V1"
_IGNORE = shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".pytest_cache",
                                 ".venv", "node_modules")

# This trusted bootstrap creates a real, offline venv. Its .pth projects the
# explicitly snapshotted dependencies into every genuine pytest subprocess.
# No interpreter shim, subprocess patch, historical source, or pip is involved.
_BOOTSTRAP = r'''
import os, pathlib, shutil, venv
shutil.copytree('/input/brain', '/work/brain')
venv.EnvBuilder(with_pip=False).create('/work/venv')
site = next(pathlib.Path('/work/venv/lib').glob('python*/site-packages'))
(site / 'declared_dependencies.pth').write_text('/input/dependencies\n')
os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
os.chdir('/work/brain')
os.execv('/work/venv/bin/python', ['/work/venv/bin/python', '-I', '-c', pathlib.Path('/input/driver.py').read_text()])
'''

_DRIVER = r'''
import contextlib, json, os, pathlib, sys, traceback
sys.path.insert(0, '/work/brain')
fd = int(os.environ['PROJECT_BRAIN_BROKER_FD'])
request = json.loads(pathlib.Path('/input/request.json').read_text())
result = {'pass': False}
with open('/work/driver.log', 'w+') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
    try:
        from canonical.runtime.canonical_tree_attestation_v1 import tree_manifest
        from canonical.runtime.bound_capabilities.software_repair_crossfile_choreograph_v1 import _regression
        from canonical.runtime.live_brain_route_admission_v1 import solve
        source = pathlib.Path('/work/brain/work/src')
        before = tree_manifest(source)
        baseline = _regression(source, pathlib.Path('/work/baseline.xml'), 60)
        if baseline.get('status') == 'REGRESSION_EVIDENCE_UNAVAILABLE':
            import subprocess
            diagnostic = subprocess.run([sys.executable, '-m', 'pytest', '--collect-only', '-q'],
                                        cwd=source, capture_output=True, text=True, timeout=15)
            baseline['diagnostic'] = {'returncode': diagnostic.returncode,
                                      'stdout_tail': diagnostic.stdout[-6000:],
                                      'stderr_tail': diagnostic.stderr[-6000:]}
        baseline_unchanged = tree_manifest(source)['tree_sha256'] == before['tree_sha256']
        solved = solve(request)
        artifact = pathlib.Path('/work/brain/work/out/report.json')
        report = json.loads(artifact.read_bytes()) if artifact.is_file() else None
        result = {'pass': (baseline['pass'] is True and baseline_unchanged
                           and solved.get('pass') is True
                           and solved.get('crossfile_acceptance_complete') is True
                           and solved.get('semantic_acceptance_complete') is True),
                  'source_tree_sha256': before['tree_sha256'],
                  'baseline': baseline, 'baseline_source_unchanged': baseline_unchanged,
                  'solve': solved, 'report': report}
    except (Exception, SystemExit) as exc:
        result = {'pass': False, 'error': type(exc).__name__ + ':' + str(exc)[:2000]}
        traceback.print_exc()
    log.flush()
    log.seek(0, 2)
    size = log.tell()
    log.seek(max(0, size - 12000))
    result['log_tail'] = log.read()
raw = json.dumps(result, sort_keys=True).encode()
while raw:
    n = os.write(fd, raw)
    raw = raw[n:]
'''


_REPAIR_DRIVER = r'''
import contextlib, hashlib, json, os, pathlib, sys, traceback
sys.path.insert(0, '/work/brain')
fd = int(os.environ['PROJECT_BRAIN_BROKER_FD'])
task = json.loads(pathlib.Path('/input/request.json').read_text())['repair_task']
result = {'pass': False}
with open('/work/driver.log', 'w+') as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
    try:
        from canonical.runtime.canonical_tree_attestation_v1 import tree_manifest
        from canonical.runtime.bound_capabilities.software_repair_crossfile_choreograph_v1 import _regression
        from canonical.runtime.bound_capabilities import python_repair_measured_acceptance_controller_v1 as controller
        root = pathlib.Path('/work/brain/work')
        source = root / 'src'
        before = tree_manifest(source)
        timeout = task.get('search_limits', {}).get('timeout_s', 60)
        baseline = _regression(source, pathlib.Path('/work/baseline.xml'), timeout)
        result = {'pass': False, 'source_tree_sha256': before['tree_sha256'], 'baseline': baseline}
        if (baseline.get('returncode') != 1 or baseline.get('completed', 0) == 0
                or baseline.get('failed', 0) == 0):
            result['reason'] = 'FAILING_EXECUTED_BASELINE_REQUIRED'
        elif tree_manifest(source)['tree_sha256'] != before['tree_sha256']:
            result['reason'] = 'BASELINE_CHANGED_SOURCE'
        else:
            args = {'source_root': 'src', 'test_paths': ['src/' + p for p in task['test_paths']],
                    'test_argv': [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', str(source)],
                    'task_text': task['task_text'], 'output_path': 'out/report.json',
                    'repair_strategy': task.get('repair_strategy', 'guided'),
                    **task.get('search_limits', {})}
            args.setdefault('timeout_s', timeout)
            returned = controller.run(args, root)
            raw = (root / 'out/report.json').read_bytes()
            if hashlib.sha256(raw).hexdigest() != returned.get('output_sha256'):
                raise ValueError('REPAIR_REPORT_HASH_MISMATCH')
            report = json.loads(raw)
            result['repair'] = report
            if report.get('pass') is True and report.get('acceptance_stop_authorized') is True:
                patches = report.get('patches') or []
                if not patches:
                    raise ValueError('REPAIR_PATCHES_MISSING')
                for patch in patches:
                    rel = pathlib.Path(patch['source_path'])
                    if ('tests' in rel.parts or rel.name == 'conftest.py'
                            or rel.name.startswith('test_') or rel.name.endswith('_test.py')
                            or patch['source_path'] in args['test_paths']):
                        raise ValueError('REPAIR_MAY_NOT_CHANGE_TESTS')
                candidate = pathlib.Path('/work/replay')
                realized = controller._realize_candidate(root, source, patches, candidate)
                candidate_before = tree_manifest(candidate)
                replay = _regression(candidate, pathlib.Path('/work/replay.xml'), timeout)
                result['replay'] = replay
                result['realized_patches'] = realized
                result['candidate_tree_sha256'] = candidate_before['tree_sha256']
                result['candidate_unchanged_during_replay'] = (
                    tree_manifest(candidate)['tree_sha256'] == candidate_before['tree_sha256'])
                result['pass'] = (report.get('source_restored') is True and replay['pass'] is True
                                  and candidate_before['pass'] is True
                                  and result['candidate_unchanged_during_replay']
                                  and report.get('measured_fields', {}).get('test_count') == replay['completed'])
            result['source_unchanged_after_repair'] = tree_manifest(source)['tree_sha256'] == before['tree_sha256']
            result['pass'] = result['pass'] and result['source_unchanged_after_repair']
    except (Exception, SystemExit) as exc:
        result['pass'] = False
        result['error'] = type(exc).__name__ + ':' + str(exc)[:2000]
        traceback.print_exc()
    log.flush()
    log.seek(0, 2)
    log.seek(max(0, log.tell() - 12000))
    result['log_tail'] = log.read()
raw = json.dumps(result, sort_keys=True).encode()
while raw:
    n = os.write(fd, raw)
    raw = raw[n:]
'''


def _snapshot(source: Path, destination: Path):
    """Copy actual bytes, never follow symlinks or import project code on host."""
    if any(p.is_symlink() for p in source.rglob("*")):
        raise ValueError("SNAPSHOT_SYMLINK_REJECTED")
    shutil.copytree(source, destination, symlinks=True, ignore=_IGNORE)


def _qualify(source_root, payload, *, input_kind="issue", brain_root=ROOT,
            wallclock_s=180, host_uid=None, host_gid=None):
    """Exercise one explicit rename/move task; return the real report and trace.

    Inputs must be authorized project data. Snapshot all installed dependencies
    from this interpreter's purelib (excluding packaging tools), so tests cannot
    discover the caller's home via a mounted venv. Missing/incompatible runtime
    dependencies, namespace failures, output overflow and timeouts fail closed;
    there is no unconfined fallback. Source promotion is never performed.
    """
    started = time.perf_counter_ns()
    source = Path(source_root).resolve()
    brain = Path(brain_root).resolve()
    if not source.is_dir():
        raise ValueError("SOURCE_ROOT_NOT_DIRECTORY")
    if input_kind not in ("issue", "task", "repair") or not isinstance(payload, dict):
        raise ValueError("EXPLICIT_ISSUE_OR_TASK_REQUIRED")
    if type(wallclock_s) is not int or not 1 <= wallclock_s <= 300:
        raise ValueError("WALLCLOCK_MUST_BE_BOUNDED_INTEGER")
    before = tree_manifest(source)
    if before["pass"] is not True:
        raise ValueError("SOURCE_TREE_INVALID")
    with tempfile.TemporaryDirectory(prefix="brain-crossfile-input-") as raw:
        intake = Path(raw)
        # This is an explicit runtime projection, NOT a full-Brain-suite claim.
        # Keep laws, receipts and governance bytes; never manufacture admission.
        shutil.copytree(brain / "canonical", intake / "brain/canonical", symlinks=True,
                        ignore=shutil.ignore_patterns("astra_runtime", "tests", ".git",
                                                     "__pycache__", "*.pyc", ".pytest_cache"))
        work = intake / "brain/work"
        work.mkdir()
        _snapshot(source, work / "src")
        (work / (input_kind + ".json")).write_text(json.dumps(payload), encoding="utf-8")
        request = {"task_id": "CONFINED_CROSSFILE_EXERCISE", "goal":
                   "Write a cross-file repair report to work/out/report.json "
                   f"for the source root work/src using the {input_kind} path work/{input_kind}.json"}
        if input_kind == "repair":
            request = {"repair_task": payload}
        (intake / "request.json").write_text(json.dumps(request), encoding="utf-8")
        (intake / "driver.py").write_text(_REPAIR_DRIVER if input_kind == "repair" else _DRIVER, encoding="utf-8")
        dependencies = Path(sysconfig.get_path("purelib"))
        if sys.prefix == sys.base_prefix:
            raise ValueError("EXPLICIT_VENV_DEPENDENCIES_REQUIRED")
        shutil.copytree(dependencies, intake / "dependencies", symlinks=True, ignore=shutil.ignore_patterns(
            "__pycache__", "*.pyc", "pip", "pip-*.dist-info", "setuptools",
            "setuptools-*.dist-info", "pkg_resources", "_distutils_hack", "*.pth"))
        frozen = tree_manifest(intake)
        if frozen["pass"] is not True:
            raise ValueError("RUNTIME_SNAPSHOT_INVALID")
        # Confirm the copied input represents precisely the authorized source.
        if tree_manifest(work / "src")["tree_sha256"] != before["tree_sha256"]:
            raise ValueError("SOURCE_CHANGED_DURING_SNAPSHOT")
        policy = {"input_dir": str(intake), "expose_null_device": True, "argv": ["/usr/bin/python3", "-I", "-c", _BOOTSTRAP],
                  "limits": {"wallclock_s": wallclock_s, "cpu_seconds": min(wallclock_s, 300),
                             "memory_mb": 2048, "scratch_mb": 512, "max_file_mb": 32,
                             "nofile": 128, "pids": 64, "broker_max_bytes": 4_000_000}}
        if host_uid is not None:
            policy["host_uid"] = host_uid
        if host_gid is not None:
            policy["host_gid"] = host_gid
        if os.geteuid() == 0:
            # Only an explicit nonroot identity is accepted by the launcher.
            # The root carrier must make the declared input traversable.
            if host_uid is not None and host_gid is not None:
                os.chown(intake, host_uid, host_gid)
                os.chmod(intake, 0o755)
        execution = run_confined(policy)
        try:
            observed = json.loads(execution["broker_payload"])
            if not isinstance(observed, dict):
                raise ValueError("BROKER_RESULT_NOT_OBJECT")
        except (ValueError, UnicodeDecodeError):
            observed = {"pass": False, "error": "BROKER_RESULT_UNAVAILABLE"}
        intake_unchanged = tree_manifest(intake)["tree_sha256"] == frozen["tree_sha256"]
    source_unchanged = tree_manifest(source)["tree_sha256"] == before["tree_sha256"]
    accepted = (execution["status"] == "CHILD_EXITED" and execution["returncode"] == 0
                and observed.get("pass") is True and intake_unchanged and source_unchanged
                and observed.get("source_tree_sha256") == before["tree_sha256"])
    return {"schema": ("PROJECT_BRAIN_CONFINED_REPAIR_LOCAL_EXERCISE_V1" if input_kind == "repair" else SCHEMA), "pass": accepted,
            "source_tree_sha256": before["tree_sha256"], "source_unchanged": source_unchanged,
            "input_snapshot_sha256": frozen["tree_sha256"], "input_snapshot_unchanged": intake_unchanged,
            "execution": {k: v for k, v in execution.items() if k != "broker_payload"},
            "observed": observed, "elapsed_ms": round((time.perf_counter_ns() - started) / 1e6, 3),
            "source_promotion_performed": False, "independent_semantic_oracle_credit": False,
            "terminal_credit_delta": 0}


def qualify(source_root, payload, *, input_kind="issue", brain_root=ROOT,
            wallclock_s=180, host_uid=None, host_gid=None):
    """Explicit confined normal-entry rename/move exercise (existing interface)."""
    if input_kind not in ("issue", "task"):
        raise ValueError("EXPLICIT_ISSUE_OR_TASK_REQUIRED")
    return _qualify(source_root, payload, input_kind=input_kind, brain_root=brain_root,
                    wallclock_s=wallclock_s, host_uid=host_uid, host_gid=host_gid)


def qualify_repair(source_root, payload, *, brain_root=ROOT, wallclock_s=180,
                   host_uid=None, host_gid=None):
    """Reuse guided repair + measured acceptance + full patch replay, confined.

    Unlike rename/move this exercises the existing measured-controller API,
    not the natural-language front door. Whole-project pytest is mandatory.
    Trace suites guide search but never substitute for that regression oracle.
    """
    if (not isinstance(payload, dict) or set(payload) - {"task_text", "test_paths", "search_limits", "repair_strategy"}
            or not isinstance(payload.get("task_text"), str) or not payload["task_text"].strip()
            or len(payload["task_text"]) > 10000):
        raise ValueError("REPAIR_TASK_SCHEMA_INVALID")
    if payload.get("repair_strategy", "guided") not in ("guided", "iterative_then_guided"):
        raise ValueError("REPAIR_STRATEGY_UNSUPPORTED")
    paths = payload.get("test_paths")
    if not isinstance(paths, list) or not 1 <= len(paths) <= 32:
        raise ValueError("REPAIR_TRACE_PATHS_REQUIRED")
    for path in paths:
        if (not isinstance(path, str) or not path.endswith(".py") or "\\" in path
                or Path(path).is_absolute() or ".." in Path(path).parts):
            raise ValueError("REPAIR_TRACE_PATH_INVALID")
    source = Path(source_root).resolve()
    for path in paths:
        target = (source / path).resolve()
        if source not in target.parents or not target.is_file():
            raise ValueError("REPAIR_TRACE_FILE_REQUIRED")
    if len(set(paths)) != len(paths):
        raise ValueError("REPAIR_TRACE_PATH_DUPLICATED")
    limits = payload.get("search_limits", {})
    bounds = {"timeout_s": 120, "max_guided_files": 16, "max_guided_symbols_per_file": 32,
              "mutations_per_file": 128, "max_pair_candidates": 20000,
              "max_control_files": 32, "max_control_symbols_per_file": 64,
              "iterative_max_rounds": 20, "iterative_candidates_per_file": 5000,
              "iterative_max_candidates": 50000}
    if not isinstance(limits, dict) or set(limits) - set(bounds):
        raise ValueError("REPAIR_SEARCH_LIMITS_INVALID")
    if any(type(value) is not int or not 1 <= value <= bounds[key] for key, value in limits.items()):
        raise ValueError("REPAIR_SEARCH_LIMITS_INVALID")
    return _qualify(source_root, payload, input_kind="repair", brain_root=brain_root,
                    wallclock_s=wallclock_s, host_uid=host_uid, host_gid=host_gid)


def main(argv=None):
    """Explicit opt-in command; writes a fresh local exercise artifact only."""
    import argparse
    from canonical.runtime.swe_task_artifacts_v1 import fresh_output, publish_report

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--issue-path")
    inputs.add_argument("--task-path")
    inputs.add_argument("--repair-task-path")
    parser.add_argument("--output-path", required=True, help="Fresh path relative to the Brain checkout")
    parser.add_argument("--wallclock-s", type=int, default=180)
    parser.add_argument("--host-uid", type=int)
    parser.add_argument("--host-gid", type=int)
    args = parser.parse_args(argv)
    output = fresh_output(ROOT, args.output_path, "unused.json")
    kind = "issue" if args.issue_path else "task"
    payload = json.loads(Path(args.issue_path or args.task_path or args.repair_task_path).read_bytes())
    options = {"wallclock_s": args.wallclock_s, "host_uid": args.host_uid, "host_gid": args.host_gid}
    result = (qualify_repair(args.source_root, payload, **options) if args.repair_task_path else
              qualify(args.source_root, payload, input_kind=kind, **options))
    publish_report(ROOT, output, result)
    print(json.dumps({"pass": result["pass"], "output_path": str(output),
                      "elapsed_ms": result["elapsed_ms"], "execution_status": result["execution"]["status"]}))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
