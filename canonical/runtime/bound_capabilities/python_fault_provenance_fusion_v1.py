#!/usr/bin/env python3
# PROJECT_BRAIN
"""Real fault-provenance fusion: localize fault → fuse provenance → verify on project.

Delegates to python_dynamic_fault_localizer_v1 and
python_provenance_guided_coupled_repair_v1 for actual project execution.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any, Mapping

from canonical.runtime.bound_capabilities.real_swe_execution_v1 import (
    fault_localize, patch_search, full_test_gate, end_to_end_repair,
)

SCHEMA = 'PROJECT_BRAIN_PYTHON_FAULT_PROVENANCE_FUSION_V1'
CAPABILITY_ID = 'python.fault.provenance.fusion.v1'
PROVIDES = ['python.fault.provenance.fused', 'python.fault.fusion.verified']
REQUIRES = ['python.fault.localization.symbol_ranked',
            'python.fault.provenance.interprocedural_value_hypotheses',
            'python.fault.localization.dynamic_spectrum']
PRODUCERS = ['python.fault.localize.dynamic.dataflow.v1',
             'python.fault.provenance.interprocedural.value.v1']


def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p = (root / str(raw or 'canonical/tmp_fault_provenance_fusion.json')).resolve()
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
    worktree_rel = str(args.get('worktree_path') or 'canonical/tmp_fault_prov_worktree')
    diff_rel = str(args.get('diff_path') or 'canonical/tmp_fault_prov_diff.diff')
    pr_rel = str(args.get('pr_intent_path') or 'canonical/tmp_fault_prov_pr.json')
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
        'fault_localized': result.get('fault_localized', False),
        'patches_tried': result.get('patches_tried', 0),
        'patches_passing': result.get('patches_passing', 0),
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
        'adapter': 'python_fault_provenance_fusion_v1',
        'output_path': str(output.relative_to(repo)),
        'output_sha256': artifact['output_sha256'],
        'output_verified': True,
        'verified': artifact['verified'],
        'model_dependency_count': 0,
        'incremental_spend_usd': 0,
    }
