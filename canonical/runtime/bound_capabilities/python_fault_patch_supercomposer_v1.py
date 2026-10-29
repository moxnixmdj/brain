#!/usr/bin/env python3
# PROJECT_BRAIN
"""Real fault-patch supercomposer: localize fault → search patch → apply → verify.

Delegates to python_dynamic_fault_localizer_v1, python_test_guided_patch_search_v1,
and python_repo_diff_apply_full_testgate for actual project-bound execution.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any, Mapping

from canonical.runtime.bound_capabilities.real_swe_execution_v1 import (
    end_to_end_repair, fault_localize, patch_search,
)

SCHEMA = 'PROJECT_BRAIN_PYTHON_FAULT_PATCH_SUPERCOMPOSER_V1'
CAPABILITY_ID = 'python.fault.patch.supercomposer.v1'
PROVIDES = ['python.fault.patch.super.verified', 'python.fault.patch.family.verified']
REQUIRES = ['python.fault.localization.backward_def_use', 'python.fault.provenance.dynamic_call_edges',
            'python.patch.candidate.test_verified', 'python.patch.candidate.multi_edit.test_verified',
            'python.software.repair.semantic_acceptance']
PRODUCERS = ['python.fault.localize.dynamic.dataflow.v1', 'python.fault.provenance.interprocedural.value.v1',
             'python.patch.search.test_guided.ast.v1', 'python.software.repair.loop.test_guided.ast.v1',
             'python.software.repair.semantic_acceptance.v1']


def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p = (root / str(raw or 'canonical/tmp_fault_patch_supercomposer.json')).resolve()
    if p == root or root not in p.parents:
        raise RuntimeError('PATH_OUTSIDE_REPOSITORY')
    if p.is_file() and p.suffix == '.py':
        raise RuntimeError('OUTPUT_OVERLAPS_INPUT')
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def run(args: Mapping[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = _safe_output(repo, args.get('output_path'))

    source_path = args.get('source_path')
    test_paths = args.get('test_paths') or []
    worktree_rel = str(args.get('worktree_path') or 'canonical/tmp_fault_patch_worktree')
    diff_rel = str(args.get('diff_path') or 'canonical/tmp_fault_patch_diff.diff')
    pr_rel = str(args.get('pr_intent_path') or 'canonical/tmp_fault_patch_pr.json')
    timeout_s = int(args.get('timeout_s', 300))
    max_candidates = int(args.get('max_candidates', 50))

    result = end_to_end_repair(
        source_root=str(args.get('source_root') or '.'),
        worktree_path=worktree_rel,
        source_path=source_path,
        test_paths=test_paths,
        output_path=str(output.relative_to(repo)),
        diff_path=diff_rel,
        pr_intent_path=pr_rel,
        timeout_s=timeout_s,
        max_candidates=max_candidates,
    )

    artifact = {
        'schema': SCHEMA,
        'capability_id': CAPABILITY_ID,
        'verified': result.get('verified', False),
        'gate': result.get('gate', 'FAIL'),
        'patches_tried': result.get('patches_tried', 0),
        'patches_passing': result.get('patches_passing', 0),
        'applied_op_count': result.get('applied_op_count', 0),
        'test_passed_count': result.get('test_passed_count', 0),
        'test_failed_count': result.get('test_failed_count', 0),
        'diff_sha256': result.get('diff_sha256', ''),
        'pr_intent_verified': result.get('pr_intent_verified', False),
        'model_dependency_count': 0,
        'incremental_spend_usd': 0,
        'output_path': str(output.relative_to(repo)),
        'output_verified': True,
        'reason': result.get('reason'),
    }
    raw = json.dumps(artifact, sort_keys=True, separators=(',', ':')).encode()
    output.write_bytes(raw)
    artifact['output_sha256'] = hashlib.sha256(raw).hexdigest()
    return {
        'adapter': 'python_fault_patch_supercomposer_v1',
        'output_path': str(output.relative_to(repo)),
        'output_sha256': artifact['output_sha256'],
        'output_verified': True,
        'verified': artifact['verified'],
        'gate': artifact['gate'],
        'model_dependency_count': 0,
        'incremental_spend_usd': 0,
    }
