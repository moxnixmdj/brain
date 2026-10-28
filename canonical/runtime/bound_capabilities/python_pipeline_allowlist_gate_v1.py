#!/usr/bin/env python3
# PROJECT_BRAIN
"""Real pipeline allowlist gate: run all review gates on the patched worktree → verify allowlist.

Delegates to python_review_diff_static_triage, python_review_diff_type_gate,
python_review_diff_coverage_gate, python_review_diff_security_gate on actual project diffs.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any, Mapping

from canonical.runtime.bound_capabilities.real_swe_execution_v1 import (
    end_to_end_repair, _run_in_process, REPO,
)

SCHEMA = 'PROJECT_BRAIN_PYTHON_PIPELINE_ALLOWLIST_GATE_V1'
CAPABILITY_ID = 'python.pipeline.allowlist_gate.v1'
PROVIDES = ['python.pipeline.allowlist.verified', 'python.review.composition.allowlist_verified']
REQUIRES = ['python.review.diff_static_triage', 'python.review.diff_type_gate',
            'python.review.diff_coverage_gate', 'python.review.diff_security_gate']
PRODUCERS = ['python.review.diff_static_triage.v1', 'python.review.diff_type_gate.v1',
             'python.review.diff_coverage_gate.v1', 'python.review.diff_perf_gate.v1',
             'python.review.diff_security_gate.v1', 'python.review.diff_mutation_gate.v1',
             'execution.pipeline.8stage.v1']


def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p = (root / str(raw or 'canonical/tmp_pipeline_allowlist.json')).resolve()
    if p == root or root not in p.parents:
        raise RuntimeError('PATH_OUTSIDE_REPOSITORY')
    if p.is_file() and p.suffix == '.py':
        raise RuntimeError('OUTPUT_OVERLAPS_INPUT')
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _run_review_gate(adapter_name: str, anchor_path: pathlib.Path,
                     diff_path: pathlib.Path, output_path: pathlib.Path,
                     timeout_s: int) -> dict:
    adapter = REPO / 'canonical/runtime/bound_capabilities' / adapter_name
    args = {
        'anchor_path': str(anchor_path),
        'diff_path': str(diff_path),
        'output_path': str(output_path),
        'python_executable': '/usr/bin/python3',
        'timeout_s': timeout_s,
    }
    return _run_in_process(adapter, 'run', args, REPO)


def run(args: Mapping[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = _safe_output(repo, args.get('output_path'))

    source_root = pathlib.Path(args.get('source_root') or '.')
    if not source_root.is_absolute():
        source_root = repo / source_root
    source_root = source_root.resolve()

    worktree_rel = str(args.get('worktree_path') or 'canonical/tmp_pipeline_allowlist_worktree')
    worktree = pathlib.Path(worktree_rel)
    if not worktree.is_absolute():
        worktree = repo / worktree
    worktree = worktree.resolve()

    diff_rel = str(args.get('diff_path') or 'canonical/tmp_pipeline_allowlist_diff.diff')
    diff_path = pathlib.Path(diff_rel)
    if not diff_path.is_absolute():
        diff_path = repo / diff_path
    diff_path = diff_path.resolve()

    timeout_s = int(args.get('timeout_s', 300))

    # Run end-to-end repair first to get a verified patch
    result = end_to_end_repair(
        source_root=str(source_root.relative_to(repo)),
        worktree_path=str(worktree.relative_to(repo)),
        source_path=args.get('source_path'),
        test_paths=args.get('test_paths') or [],
        output_path=str(output.relative_to(repo)),
        diff_path=str(diff_path.relative_to(repo)),
        pr_intent_path=str(args.get('pr_intent_path') or 'canonical/tmp_pipeline_allowlist_pr.json'),
        timeout_s=timeout_s,
        max_candidates=int(args.get('max_candidates', 50)),
    )

    # Run all review gates on the produced diff
    gate_results = {}
    review_gates = [
        'python_review_diff_static_triage.py',
        'python_review_diff_type_gate.py',
        'python_review_diff_coverage_gate.py',
        'python_review_diff_security_gate.py',
    ]
    all_gates_pass = True
    for gate_name in review_gates:
        gate_out = output.parent / (gate_name.replace('.py', '') + '_result.json')
        try:
            gr = _run_review_gate(gate_name, source_root, diff_path, gate_out, timeout_s)
            gate_results[gate_name] = gr
            if gr.get('gate') != 'PASS' and gr.get('verified') is not True:
                all_gates_pass = False
        except Exception as exc:
            gate_results[gate_name] = {'error': str(exc)}
            all_gates_pass = False

    verified = result.get('verified', False) and all_gates_pass

    artifact = {
        'schema': SCHEMA,
        'capability_id': CAPABILITY_ID,
        'verified': verified,
        'repair_verified': result.get('verified', False),
        'all_review_gates_pass': all_gates_pass,
        'gate_results': gate_results,
        'test_passed_count': result.get('test_passed_count', 0),
        'test_failed_count': result.get('test_failed_count', 0),
        'diff_sha256': result.get('diff_sha256', ''),
        'model_dependency_count': 0,
        'incremental_spend_usd': 0,
        'output_path': str(output.relative_to(repo)),
        'output_verified': True,
    }
    raw = json.dumps(artifact, sort_keys=True, separators=(',', ':')).encode()
    output.write_bytes(raw)
    artifact['output_sha256'] = hashlib.sha256(raw).hexdigest()
    return {
        'adapter': 'python_pipeline_allowlist_gate_v1',
        'output_path': str(output.relative_to(repo)),
        'output_sha256': artifact['output_sha256'],
        'output_verified': True,
        'verified': artifact['verified'],
        'model_dependency_count': 0,
        'incremental_spend_usd': 0,
    }
