"""Shared reporting boundary for metadata-only composition inventories.

A report written successfully is not evidence that its advertised work ran.
This helper never dispatches stages or accepts caller-supplied execution receipts.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from canonical.runtime.write_authority_v1 import SOURCE_SUFFIXES, check_report


def write_inventory_report(
    repo: Path, output: Path, artifact: dict[str, Any], adapter: str,
) -> dict[str, Any]:
    """Write diagnostics, but never grant an execution-verified effect."""
    check_report(repo, output, [repo / 'canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json'])
    if output.suffix.lower() in SOURCE_SUFFIXES:
        raise RuntimeError('REPORT_DESTINATION_IS_SOURCE')
    artifact.update(
        verified=False, **{'pass': False}, execution_performed=False,
        status='OPEN__EXECUTION_EVIDENCE_REQUIRED',
        evidence_scope='registry_inventory_only',
    )
    raw = json.dumps(artifact, sort_keys=True, separators=(',', ':')).encode()
    output.write_bytes(raw)
    return {
        'adapter': adapter,
        'output_path': str(output.relative_to(repo)),
        'output_sha256': hashlib.sha256(raw).hexdigest(),
        'output_verified': output.read_bytes() == raw,
        'verified': False,
        'pass': False,
        'execution_performed': False,
        'status': artifact['status'],
        'evidence_scope': artifact['evidence_scope'],
        'inventory_ready': artifact['inventory_ready'],
        'found': artifact['found'],
        'model_dependency_count': 0,
        'incremental_spend_usd': 0,
    }
