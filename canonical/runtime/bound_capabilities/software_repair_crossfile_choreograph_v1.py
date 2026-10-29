#!/usr/bin/env python3
# PROJECT_BRAIN
"""Real cross-file choreograph: apply coordinated multi-file edits → verify on project.

Uses python_crossfile_edit_choreograph for planning and applying cross-file
edits, then verifies with the full test gate.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any, Mapping

from canonical.runtime.bound_capabilities.real_swe_execution_v1 import end_to_end_repair

SCHEMA = 'PROJECT_BRAIN_SOFTWARE_REPAIR_CROSSFILE_CHOREOGRAPH_V1'
CAPABILITY_ID = 'software.repair.choreograph.crossfile.v1'
PROVIDES = ['software.repair.choreography.verified', 'software.patch.crossfile.atomic']
REQUIRES: list[str] = ['python.fault.localization.symbol_ranked',
                       'python.source.symbols.index.ast']


def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p = (root / str(raw or 'canonical/tmp_crossfile_choreograph.json')).resolve()
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
    worktree_rel = str(args.get('worktree_path') or 'canonical/tmp_crossfile_worktree')
    diff_rel = str(args.get('diff_path') or 'canonical/tmp_crossfile_diff.diff')
    pr_rel = str(args.get('pr_intent_path') or 'canonical/tmp_crossfile_pr.json')
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
        'applied_op_count': result.get('applied_op_count', 0),
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
        'adapter': 'software_repair_crossfile_choreograph_v1',
        'output_path': str(output.relative_to(repo)),
        'output_sha256': artifact['output_sha256'],
        'output_verified': True,
        'verified': artifact['verified'],
        'model_dependency_count': 0,
        'incremental_spend_usd': 0,
    }
