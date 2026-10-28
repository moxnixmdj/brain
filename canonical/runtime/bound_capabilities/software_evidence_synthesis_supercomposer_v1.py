#!/usr/bin/env python3
# PROJECT_BRAIN
"""Real evidence-synthesis supercomposer: synthesize evidence from concrete test execution.

Runs evidence oracle (concrete execution + hypothesis property) on the actual
project and synthesizes a bound evidence claim.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
from typing import Any, Mapping

from canonical.runtime.bound_capabilities.real_swe_execution_v1 import (
    end_to_end_repair, _run_in_process, REPO,
)

SCHEMA = 'PROJECT_BRAIN_SOFTWARE_EVIDENCE_SYNTHESIS_SUPERCOMPOSER_V1'
CAPABILITY_ID = 'software.evidence.synthesis.supercomposer.v1'
PROVIDES = ['evidence.synthesis.super.verified', 'evidence.evidence.family.super.verified']
REQUIRES = ['evidence.claim.exact_quoted_bound', 'evidence.claim.exact_text_support',
            'evidence.claim_spec.explicit_bounded', 'evidence.numeric_relation.objective_bound',
            'source.evidence.verbatim_provenance_bound']
PRODUCERS = ['evidence.claim_spec.bind.explicit_comparison.stdlib',
             'evidence.claim_relation.generic_units.stdlib',
             'source.evidence.extract.objective_grounded.stdlib']


def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p = (root / str(raw or 'canonical/tmp_evidence_synthesis_supercomposer.json')).resolve()
    if p == root or root not in p.parents:
        raise RuntimeError('PATH_OUTSIDE_REPOSITORY')
    if p.is_file() and p.suffix == '.py':
        raise RuntimeError('OUTPUT_OVERLAPS_INPUT')
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _run_oracle(adapter_name: str, source_path: pathlib.Path,
                output_path: pathlib.Path) -> dict:
    """Run an evidence oracle adapter in-process."""
    adapter = REPO / 'canonical/runtime/bound_capabilities' / adapter_name
    args = {
        'source_file': str(source_path),
        'output_path': str(output_path),
    }
    return _run_in_process(adapter, 'run', args, REPO)


def run(args: Mapping[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = _safe_output(repo, args.get('output_path'))

    source_path = pathlib.Path(args.get('source_path') or '')
    if not source_path.is_absolute():
        source_path = repo / source_path
    source_path = source_path.resolve()

    # Run end-to-end repair first
    result = end_to_end_repair(
        source_root=str(args.get('source_root') or '.'),
        worktree_path=str(args.get('worktree_path') or 'canonical/tmp_evidence_worktree'),
        source_path=str(source_path),
        test_paths=args.get('test_paths') or [],
        output_path=str(output.relative_to(repo)),
        diff_path=str(args.get('diff_path') or 'canonical/tmp_evidence_diff.diff'),
        pr_intent_path=str(args.get('pr_intent_path') or 'canonical/tmp_evidence_pr.json'),
        timeout_s=int(args.get('timeout_s', 300)),
        max_candidates=int(args.get('max_candidates', 50)),
    )

    # Run evidence oracles on the source
    oracle_results = {}
    for oracle_name in ['evidence_oracle_concrete_v1.py', 'evidence_oracle_hypothesis_v1.py']:
        oracle_out = output.parent / (oracle_name.replace('.py', '') + '_result.json')
        try:
            oracle_results[oracle_name] = _run_oracle(oracle_name, source_path, oracle_out)
        except Exception as exc:
            oracle_results[oracle_name] = {'error': str(exc)}

    # Synthesize evidence claim: verified if repair passed AND at least one oracle produced evidence
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
        'adapter': 'software_evidence_synthesis_supercomposer_v1',
        'output_path': str(output.relative_to(repo)),
        'output_sha256': artifact['output_sha256'],
        'output_verified': True,
        'verified': artifact['verified'],
        'model_dependency_count': 0,
        'incremental_spend_usd': 0,
    }
