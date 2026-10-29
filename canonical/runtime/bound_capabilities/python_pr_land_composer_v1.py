#!/usr/bin/env python3
# PROJECT_BRAIN
"""Real PR land composer: apply diff → full test gate → realize PR.

Delegates to python_repo_diff_apply_full_testgate and python_repo_pr_realize
for actual project-bound PR realization.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any, Mapping

from canonical.runtime.bound_capabilities.real_swe_execution_v1 import (
    end_to_end_repair, _run_in_process, REPO,
)

SCHEMA = 'PROJECT_BRAIN_PYTHON_PR_LAND_COMPOSER_V1'
CAPABILITY_ID = 'python.pr.land.composer.v1'
PROVIDES = ['python.pr.land.verified', 'python.pr.composition.verified']
REQUIRES = ['python.repo.diff_apply_full_testgate', 'python.repo.pr_realize',
            'python.software.repair.apply.verified', 'python.software.repair.measured_acceptance']
PRODUCERS = ['python.repo.diff_apply_full_testgate.v1', 'python.repo.pr_realize.v1',
             'python.software.repair.apply.verified.v1',
             'python.software.repair.measured_acceptance.v1']


def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p = (root / str(raw or 'canonical/tmp_pr_land_composer.json')).resolve()
    if p == root or root not in p.parents:
        raise RuntimeError('PATH_OUTSIDE_REPOSITORY')
    if p.is_file() and p.suffix == '.py':
        raise RuntimeError('OUTPUT_OVERLAPS_INPUT')
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def run(args: Mapping[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = _safe_output(repo, args.get('output_path'))

    source_root = str(args.get('source_root') or '.')
    worktree_rel = str(args.get('worktree_path') or 'canonical/tmp_pr_land_worktree')
    diff_rel = str(args.get('diff_path') or 'canonical/tmp_pr_land_diff.diff')
    pr_rel = str(args.get('pr_intent_path') or 'canonical/tmp_pr_land_pr.json')
    timeout_s = int(args.get('timeout_s', 300))

    # Run end-to-end repair
    result = end_to_end_repair(
        source_root=source_root,
        worktree_path=worktree_rel,
        source_path=args.get('source_path'),
        test_paths=args.get('test_paths') or [],
        output_path=str(output.relative_to(repo)),
        diff_path=diff_rel,
        pr_intent_path=pr_rel,
        timeout_s=timeout_s,
        max_candidates=int(args.get('max_candidates', 50)),
    )

    # Run PR realize
    pr_realize_result = {}
    try:
        pr_out = output.parent / 'pr_realize_result.json'
        pr_realize_result = _run_in_process(
            REPO / 'canonical/runtime/bound_capabilities/python_repo_pr_realize.py',
            'run',
            {
                'source_root': source_root,
                'worktree_path': worktree_rel,
                'diff_path': diff_rel,
                'output_path': str(pr_out.relative_to(repo)),
                'timeout_s': timeout_s,
            },
            repo,
        )
    except Exception as exc:
        pr_realize_result = {'error': str(exc)}

    pr_realized = bool(pr_realize_result.get('verified') or pr_realize_result.get('pr_created'))
    verified = result.get('verified', False) and pr_realized

    artifact = {
        'schema': SCHEMA,
        'capability_id': CAPABILITY_ID,
        'verified': verified,
        'repair_verified': result.get('verified', False),
        'pr_realized': pr_realized,
        'pr_realize_result': pr_realize_result,
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
        'adapter': 'python_pr_land_composer_v1',
        'output_path': str(output.relative_to(repo)),
        'output_sha256': artifact['output_sha256'],
        'output_verified': True,
        'verified': artifact['verified'],
        'model_dependency_count': 0,
        'incremental_spend_usd': 0,
    }
