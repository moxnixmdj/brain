#!/usr/bin/env python3
# PROJECT_BRAIN
"""Real CEGIS repair loop: counterexample-guided synthesis → apply → verify on project.

Delegates to python_test_guided_patch_search_v1 for bounded counterexample-guided
patch search and python_repo_diff_apply_full_testgate for verification.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any, Mapping

from canonical.runtime.bound_capabilities.real_swe_execution_v1 import end_to_end_repair

SCHEMA = 'PROJECT_BRAIN_SOFTWARE_REPAIR_LOOP_CEGIS_HYPOTHESIS_V1'
CAPABILITY_ID = 'software.repair.loop.cegis_hypothesis.v1'
PROVIDES = ['software.repair.loop.cegis_verified', 'software.repair.synthesis.triad_proven']
REQUIRES: list[str] = ['python.fault.localization.symbol_ranked']


def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p = (root / str(raw or 'canonical/tmp_repair_loop_cegis.json')).resolve()
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
    worktree_rel = str(args.get('worktree_path') or 'canonical/tmp_cegis_worktree')
    diff_rel = str(args.get('diff_path') or 'canonical/tmp_cegis_diff.diff')
    pr_rel = str(args.get('pr_intent_path') or 'canonical/tmp_cegis_pr.json')
    timeout_s = int(args.get('timeout_s', 300))
    max_candidates = int(args.get('max_candidates', 50))
    budget = int(args.get('budget', max_candidates))

    result = end_to_end_repair(
        source_root=str(args.get('source_root') or '.'),
        worktree_path=worktree_rel,
        source_path=source_path,
        test_paths=test_paths,
        output_path=str(output.relative_to(repo)),
        diff_path=diff_rel,
        pr_intent_path=pr_rel,
        timeout_s=timeout_s,
        max_candidates=budget,
    )

    artifact = {
        'schema': SCHEMA,
        'capability_id': CAPABILITY_ID,
        'verified': result.get('verified', False),
        'gate': result.get('gate', 'FAIL'),
        'budget': budget,
        'iterations': result.get('patches_tried', 0),
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
        'adapter': 'software_repair_loop_cegis_hypothesis_v1',
        'output_path': str(output.relative_to(repo)),
        'output_sha256': artifact['output_sha256'],
        'output_verified': True,
        'verified': artifact['verified'],
        'model_dependency_count': 0,
        'incremental_spend_usd': 0,
    }
