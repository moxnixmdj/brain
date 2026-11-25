"""Producer-run namespace broker byte collection experiment; no admission authority.

The namespace worker emits a bounded JSON/base64 envelope as raw material. The
host copies and hashes the exact returned bytes, then uses the experimental byte
verifier. Worker-provided hashes are not accepted. This is not a filesystem
snapshot, proof that a patch represents a worktree diff, authenticated provenance,
independent verification, or permission to run untrusted repair. The existing
carrier remains unqualified; use only controlled trusted fixtures for this tool.
"""
from __future__ import annotations

import base64
import binascii
import json
from collections.abc import Mapping
from typing import Any

from canonical.runtime import zero_ambient_namespace_launcher_v1 as launcher
from canonical.tools import isolated_effect_receipt_verifier_v1 as verifier

PAYLOAD_SCHEMA = 'PROJECT_BRAIN_EXPERIMENTAL_BROKER_EFFECT_BYTES_V1'


class CollectionRefused(ValueError):
    pass


def _unique(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise CollectionRefused('BROKER_DUPLICATE_KEY')
        obj[key] = value
    return obj


def collect_fixture_effects(policy: Mapping[str, Any], *, base_commit: str,
                            expected_policy_sha256: str,
                            expected_effect_paths: tuple[str, ...],
                            expected_patch_path: str) -> dict[str, Any]:
    """Run a controlled fixture and return host-hashed bytes, without adoption.

    All expected values are caller-supplied and not authorization. Exactly the
    broker bytes received from the launched fixture are collected. The producer
    computes both receipt and digest, so this is not independent verification.
    """
    if not isinstance(base_commit, str) or not verifier._COMMIT.fullmatch(base_commit):
        raise CollectionRefused('BASE_COMMIT_INVALID')
    if not isinstance(expected_effect_paths, tuple) or not expected_effect_paths:
        raise CollectionRefused('EFFECT_PATH_SET_INVALID')
    try:
        paths = tuple(verifier._path(path) for path in expected_effect_paths)
        patch_path = verifier._path(expected_patch_path)
    except verifier.ReceiptRefused as exc:
        raise CollectionRefused('EFFECT_PATH_INVALID') from exc
    if len(set(paths)) != len(paths) or patch_path not in paths:
        raise CollectionRefused('EFFECT_PATH_SET_INVALID')
    normalized_policy = launcher.canonical_policy(policy)
    if launcher.policy_sha256(normalized_policy) != expected_policy_sha256:
        raise CollectionRefused('POLICY_MISMATCH_BEFORE_EXECUTION')
    result = launcher.run_confined(normalized_policy)
    if (result.get('status') != 'CHILD_EXITED' or result.get('returncode') != 0
            or result.get('policy_sha256') != expected_policy_sha256):
        raise CollectionRefused('CARRIER_DID_NOT_COMPLETE')
    raw = result.get('broker_payload')
    if not isinstance(raw, bytes) or not raw or len(raw) > verifier.MAX_EFFECT_BYTES:
        raise CollectionRefused('BROKER_BYTES_INVALID')
    try:
        payload = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique)
        if (not isinstance(payload, dict) or set(payload) != {'schema', 'effects'}
                or payload['schema'] != PAYLOAD_SCHEMA or not isinstance(payload['effects'], dict)):
            raise CollectionRefused('BROKER_SHAPE_INVALID')
        if not isinstance(expected_effect_paths, tuple) or set(payload['effects']) != set(expected_effect_paths):
            raise CollectionRefused('BROKER_EFFECT_SET_MISMATCH')
        effects = {}
        for name, encoded in payload['effects'].items():
            if not isinstance(encoded, str):
                raise CollectionRefused('BROKER_ENCODING_INVALID')
            effects[name] = base64.b64decode(encoded, validate=True)
    except CollectionRefused:
        raise
    except (ValueError, TypeError, UnicodeError, binascii.Error) as exc:
        raise CollectionRefused('BROKER_PAYLOAD_INVALID') from exc
    receipt = {
        'schema': verifier.SCHEMA,
        'base_commit': base_commit,
        'policy_sha256': expected_policy_sha256,
        'effects': {p: {'size': len(data), 'sha256': verifier.digest_bytes(data)}
                    for p, data in effects.items()},
    }
    digest = verifier.receipt_digest(receipt)
    try:
        patch = verifier.verify_patch(receipt, effects, expected_receipt_sha256=digest,
                                      expected_base_commit=base_commit,
                                      expected_policy_sha256=expected_policy_sha256,
                                      expected_patch_path=expected_patch_path,
                                      expected_effect_paths=expected_effect_paths)
    except verifier.ReceiptRefused as exc:
        raise CollectionRefused('EFFECT_VERIFICATION_FAILED:' + str(exc)) from exc
    return {'receipt': receipt, 'receipt_sha256': digest, 'effect_bytes': effects,
            'patch_bytes': patch, 'carrier_qualified': False,
            'independent_verification': False, 'publication_authority': False}
