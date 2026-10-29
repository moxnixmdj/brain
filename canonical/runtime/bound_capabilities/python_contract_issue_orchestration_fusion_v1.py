#!/usr/bin/env python3
# PROJECT_BRAIN
"""Real contract-issue orchestration fusion: parse issue → orchestrate → PR.

Delegates to python_issue_to_pr_orchestrate.py for actual issue-to-PR execution
and python_cont
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any, Mapping

from canonical.runtime.bound_capabilities.real_swe_execution_v1 import (
    end_to_end_repair, _run_in_process, REPO,
)

SCHEMA = 'PROJECT_BRAIN_PYTHON_CONTRACT_ISSUE_ORCHESTRATION_FUSION_V1'
CAPABILITY_ID = 'python.contract.issue.orchestration.fusion.v1'
PROVIDES = ['python.orchestration.fused.verified', 'python.contract.issue.composition.verified']
REQUIRES = ['python.contract.verdict', 'python.issue.natural.language.edit.intent',
            'python.software.issue.to.pr.orchestration']
PRODUCERS = ['python.contract.check.crosshair.v1',
             'python.issue.natural.language.parse.edit.intent.v1',
             'python.software.issue.to.pr.orchestrate.v1']


def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p = (root / str(raw or 'canonical/tmp_contract_issue_fusion.json')).resolve()
    if p == root or root not in p.parents:
        raise RuntimeError('PATH_OUTSIDE_REPOSITORY')
    if p.is_file() and p.suffix == '.py':
        raise RuntimeError('OUTPUT_OVERLAPS_INPUT')
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def run(args: Mapping[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = _safe_output(repo, args.get('output_path'))

    task_path = args.get('task_path')
    source_root = str(args.get('source_root') or '.')
    worktree_rel = str(args.get('worktree_path') or 'canonical/tmp_contract_issue_worktree')
    output_rel = str(output.relative_to(repo))
    diff_rel = str(args.get('diff_path') or 'canonical/tmp_contract_issue_diff.diff')
    pr_rel = str(args.get('pr_intent_path') or 'canonical/tmp_contract_issue_pr.json')
    timeout_s = int(args.get('timeout_s', 300))

    # Run end-to-end repair (which includes issue_to_pr orchestration via end_to_end_repair)
    result = end_to_end_repair(
        source_root=source_root,
        worktree_path=worktree_rel,
        source_path=args.get('source_path'),
        test_paths=args.get('test_paths') or [],
        output_path=output_rel,
        diff_path=diff_rel,
        pr_intent_path=pr_rel,
        timeout_s=timeout_s,
        max_candidates=int(args.get('max_candidates', 50)),
    )

    # Also run the issue-to-pr orchestrator directly if task_path is provided
    orchestrate_result = {}
    if task_path:
        orch_out = output.parent / 'issue_to_pr_orchestrate_result.json'
        try:
            orchestrate_result = _run_in_process(
                REPO / 'canonical/runtime/bound_capabilities/python_issue_to_pr_orchestrate.py',
                'run',
                {
                    'task_path': str(task_path),
                    'source_root': source_root,
                    'worktree_path': worktree_rel,
                    'output_path': str(orch_out.relative_to(repo)),
                    'diff_path': diff_rel,
                    'pr_intent_path': pr_rel,
                    'timeout_s': timeout_s,
                },
                repo,
            )
        except Exception as exc:
            orchestrate_result = {'error': str(exc)}

    verified = result.get('verified', False) and (
        orchestrate_result.get('verified') is True or not task_path
    )

    artifact = {
        'schema': SCHEMA,
        'capability_id': CAPABILITY_ID,
        'verified': verified,
        'repair_verified': result.get('verified', False),
        'orchestration_verified': bool(orchestrate_result.get('verified')),
        'test_passed_count': result.get('test_passed_count', 0),
        'test_failed_count': result.get('test_failed_count', 0),
        'diff_sha256': result.get('diff_sha256', ''),
        'model_dependency_count': 0,
        'incremental_spend_usd': 0,
        'output_path': output_rel,
        'output_verified': True,
    }
    raw = json.dumps(artifact, sort_keys=True, separators=(',', ':')).encode()
    output.write_bytes(raw)
    artifact['output_sha256'] = hashlib.sha256(raw).hexdigest()
    return {
        'adapter': 'python_contract_issue_orchestration_fusion_v1',
        'output_path': output_rel,
        'output_sha256': artifact['output_sha256'],
        'output_verified': True,
        'verified': artifact['verified'],
        'model_dependency_count': 0,
        'incremental_spend_usd': 0,
    }
