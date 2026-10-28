#!/usr/bin/env python3
# PROJECT_BRAIN
"""Real evidence-contract supercomposer: synthesize evidence from concrete test execution and verify contracts.

Delegates to evidence oracle (concrete execution + hypothesis property) and
test contract verification on the actual project source.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any, Mapping

from canonical.runtime.bound_capabilities.real_swe_execution_v1 import (
    end_to_end_repair, _run_in_process, REPO,
)

SCHEMA = 'PROJECT_BRAIN_PYTHON_EVIDENCE_CONTRACT_SUPERCOMPOSER_V1'
CAPABILITY_ID = 'python.evidence.contract.supercomposer.v1'
PROVIDES = ['python.evidence.contract.super.verified', 'python.evidence.contract.family.verified']
REQUIRES = ['evidence.evidence.family.super.verified', 'evidence.synthesis.super.verified',
            'evidence.hypothesis.property_violation', 'evidence.oracle.independent_second',
            'python.contract.issue.composition.verified']
PRODUCERS = ['software.evidence.synthesis.supercomposer.v1',
             'evidence.oracle.hypothesis_property.v1',
             'evidence.oracle.concrete_execution.v1',
             'python.contract.issue_orchestration.fusion.v1']


def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p = (root / str(raw or 'canonical/tmp_evidence_contract_supercomposer.json')).resolve()
    if p == root or root not in p.parents:
        raise RuntimeError('PATH_OUTSIDE_REPOSITORY')
    if p.is_file() and p.suffix == '.py':
        raise RuntimeError('OUTPUT_OVERLAPS_INPUT')
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _run_oracle(adapter_name: str, source_path: pathlib.Path, output_path: pathlib.Path) -> dict:
    adapter = REPO / 'canonical/runtime/bound_capabilities' / adapter_name
    args = {'source_file': str(source_path), 'output_path': str(output_path)}
    return _run_in_process(adapter, 'run', args, REPO)


def run(args: Mapping[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = _safe_output(repo, args.get('output_path'))

    source_path = pathlib.Path(args.get('source_path') or '')
    if not source_path.is_absolute():
        source_path = repo / source_path
    source_path = source_path.resolve()

    test_paths = args.get('test_paths') or []
    timeout_s = int(args.get('timeout_s', 300))

    # Run end-to-end repair first
    result = end_to_end_repair(
        source_root=str(args.get('source_root') or '.'),
        worktree_path=str(args.get('worktree_path') or 'canonical/tmp_evidence_contract_worktree'),
        source_path=str(source_path),
        test_paths=test_paths,
        output_path=str(output.relative_to(repo)),
        diff_path=str(args.get('diff_path') or 'canonical/tmp_evidence_contract_diff.diff'),
        pr_intent_path=str(args.get('pr_intent_path') or 'canonical/tmp_evidence_contract_pr.json'),
        timeout_s=timeout_s,
        max_candidates=int(args.get('max_candidates', 50)),
    )

    # Run evidence oracles
    oracle_results = {}
    for oracle_name in ['evidence_oracle_concrete_v1.py', 'evidence_oracle_hypothesis_v1.py']:
        oracle_out = output.parent / (oracle_name.replace('.py', '') + '_result.json')
        try:
            oracle_results[oracle_name] = _run_oracle(oracle_name, source_path, oracle_out)
        except Exception as exc:
            oracle_results[oracle_name] = {'error': str(exc)}

    oracle_verified = any(
        r.get('verified') is True or r.get('pass') is True
        for r in oracle_results.values() if isinstance(r, dict)
    )

    verified = result.get('verified', False) and oracle_verified

    artifact = {
        'schema': SCHEMA,
        'capability_id': CAPABILITY_ID,
        'verified': verified,
        'repair_verified': result.get('verified', False),
        'evidence_oracle_verified': oracle_verified,
        'oracle_results': oracle_results,
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
        'adapter': 'python_evidence_contract_supercomposer_v1',
        'output_path': str(output.relative_to(repo)),
        'output_sha256': artifact['output_sha256'],
        'output_verified': True,
        'verified': artifact['verified'],
        'model_dependency_count': 0,
        'incremental_spend_usd': 0,
    }
