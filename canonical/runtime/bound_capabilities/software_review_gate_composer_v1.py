#!/usr/bin/env python3
"""Execute six existing diff gates; report creation is not review acceptance.

Copies are disposable workspaces, not an OS sandbox. Benchmarks and tests run
code and must be trusted or confined by the caller's execution environment.
"""
from __future__ import annotations
import hashlib
import json
import pathlib
import shutil
import subprocess
import tempfile
from typing import Any

SCHEMA = "PROJECT_BRAIN_SOFTWARE_REVIEW_GATE_COMPOSER_V1"
CAPABILITY_ID = "software.review.gate.composer.v1"
PROVIDES = ["software.review.all_gates.verified", "software.review.composition.typed"]
REQUIRES = ["software.repair.choreography.verified"]
GATES = ("static", "type", "coverage", "performance", "security", "mutation")


def _gate_functions():
    from canonical.runtime.bound_capabilities import (
        python_review_diff_static_triage as static,
        python_review_diff_type_gate as types,
        python_review_diff_coverage_gate as coverage,
        python_review_diff_perf_gate as performance,
        python_review_diff_security_gate as security,
        python_review_diff_mutation_gate as mutation,
    )
    return dict(zip(GATES, (m.run for m in (static, types, coverage, performance, security, mutation))))


def _path(repo, raw):
    if not isinstance(raw, str) or not raw.strip():
        raise RuntimeError("REVIEW_INPUT_REQUIRED")
    path = (repo / raw).resolve()
    if path == repo or repo not in path.parents:
        raise RuntimeError("REVIEW_PATH_OUTSIDE_REPOSITORY")
    return path


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _manifest(root):
    rows = []
    for path in sorted(root.rglob('*')):
        if any(p in {'.git', '__pycache__', '.pytest_cache'} for p in path.relative_to(root).parts):
            continue
        if path.is_symlink():
            raise RuntimeError("REVIEW_SYMLINK_REFUSED")
        if path.is_file():
            rows.append((path.relative_to(root).as_posix(), _sha(path.read_bytes())))
    return _sha(json.dumps(rows, separators=(',', ':')).encode())


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    anchor = _path(repo, args.get('anchor_path'))
    diff = _path(repo, args.get('diff_path'))
    output = _path(repo, args.get('output_path'))
    if not anchor.is_dir() or not diff.is_file():
        raise RuntimeError("REVIEW_INPUT_MISSING")
    if anchor in output.parents:
        raise RuntimeError("REVIEW_OUTPUT_OVERLAPS_ANCHOR")
    from canonical.runtime.write_authority_v1 import check_report
    check_report(repo, output, [diff, *(p for p in anchor.rglob("*") if p.is_file())])
    bench = args.get('bench_path')
    if not isinstance(bench, str) or not bench or pathlib.Path(bench).is_absolute() or '..' in pathlib.Path(bench).parts:
        raise RuntimeError("REVIEW_BENCH_REQUIRED_OR_INVALID")
    benchmark = (anchor / bench).resolve()
    if anchor not in benchmark.parents or not benchmark.is_file():
        raise RuntimeError("REVIEW_BENCH_MISSING")
    timeout = int(args.get('timeout_s', 120))
    if timeout < 1 or timeout > 300:
        raise RuntimeError("REVIEW_TIMEOUT_INVALID")
    text = diff.read_text(encoding='utf-8')
    from canonical.runtime.bound_capabilities.python_review_diff_static_triage import _parse_diff_ranges
    changed, _ = _parse_diff_ranges(text)
    if not changed or not any(name.endswith('.py') for name in changed):
        raise RuntimeError("REVIEW_PYTHON_DIFF_REQUIRED")
    for name in changed:
        target = pathlib.PurePosixPath(name)
        if target.is_absolute() or '..' in target.parts:
            raise RuntimeError("REVIEW_DIFF_PATH_ESCAPE")
    before = _manifest(anchor)
    digest = _sha(text.encode('utf-8'))
    output.parent.mkdir(parents=True, exist_ok=True)
    # Delegate scratch names are fixed relative to their output. Giving every
    # invocation a freshly owned parent prevents deleting another task's tree.
    # Keep it outside the checkout so git apply does not inherit its subdirectory
    # filtering rules. Delegate paths use this root; this is not OS confinement.
    with tempfile.TemporaryDirectory(prefix='brain_review_') as tmp:
        work = pathlib.Path(tmp)
        if anchor == work or anchor in work.parents:
            raise RuntimeError("REVIEW_WORKSPACE_OVERLAP")
        original = work / 'anchor'
        patched = work / 'patched'
        shutil.copytree(anchor, original, ignore=shutil.ignore_patterns('.git', '__pycache__', '.pytest_cache'))
        if _manifest(original) != before:
            raise RuntimeError("REVIEW_ANCHOR_CHANGED_DURING_COPY")
        shutil.copytree(original, patched)
        local_diff = work / 'change.diff'
        local_diff.write_text(text, encoding='utf-8')
        applied = subprocess.run(['git', 'apply', str(local_diff)], cwd=patched,
                                 capture_output=True, text=True, timeout=timeout)
        if applied.returncode != 0:
            raise RuntimeError("REVIEW_DIFF_DOES_NOT_APPLY:" + applied.stderr[:300])
        _manifest(patched)  # refuse symlinks introduced by the diff before running code
        executions = []
        functions = _gate_functions()
        for name in GATES:
            gate_output = work / (name + '.json')
            gate_args = dict(anchor_path=str(original.relative_to(work)),
                             worktree_path=str(patched.relative_to(work)),
                             diff_path=str(local_diff.relative_to(work)),
                             output_path=str(gate_output.relative_to(work)),
                             bench_path=bench, timeout_s=timeout)
            for key in ('python_executable',):
                if key in args:
                    gate_args[key] = args[key]
            row = {'gate': name, 'accepted': False}
            try:
                result = functions[name](gate_args, work)
                raw = gate_output.read_bytes()
                report = json.loads(raw)
                # Some delegates set verified=True even for a measured FAIL.
                # Others set output_verified=True for an honest partial report.
                # Neither alone is acceptance; enforce all verdict dimensions.
                accepted = (result.get('gate') == report.get('gate') == 'PASS'
                            and result.get('complete') is True and report.get('complete') is True
                            and result.get('verified') is True and report.get('verified', True) is True
                            and result.get('output_verified') is True
                            and result.get('diff_sha256') == report.get('diff_sha256') == digest
                            and result.get('output_sha256') == _sha(raw))
                row.update(accepted=accepted, result=result, report=report, report_sha256=_sha(raw))
            except (Exception, SystemExit) as exc:
                row['error'] = type(exc).__name__ + ':' + str(exc)[:1000]
            executions.append(row)
        stable = (_manifest(anchor) == before and _manifest(original) == before
                  and _sha(local_diff.read_bytes()) == digest
                  and _sha(diff.read_text(encoding='utf-8').encode('utf-8')) == digest)
        verified = stable and all(row['accepted'] for row in executions)
        artifact = dict(schema=SCHEMA, capability_id=CAPABILITY_ID, diff_sha256=digest,
                        anchor_sha256=before, anchor_unchanged=stable, executions=executions,
                        verified=verified, gates_verified=verified,
                        status='PASS__EXECUTED_REVIEW_GATES' if verified else 'FAIL__REVIEW_GATES_NOT_PASSED',
                        model_dependency_count=0, incremental_spend_usd=0)
        raw = (json.dumps(artifact, sort_keys=True, indent=2) + '\n').encode()
        output.write_bytes(raw)
    return dict(adapter='software_review_gate_composer_v1', output_path=str(output.relative_to(repo)),
                output_sha256=_sha(raw), output_verified=output.read_bytes() == raw,
                verified=verified, gates_verified=verified, status=artifact['status'],
                model_dependency_count=0, incremental_spend_usd=0)
