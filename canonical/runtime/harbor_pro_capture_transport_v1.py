"""Unqualified Pro candidate capture over Harbor exec, not solver admission.

The worker response is untrusted and may be forged; a checksum verifies only
byte agreement. This helper does not prove quiescence, container identity,
isolation or benchmark validity. The explicit VM opt-in may call it.
"""
from __future__ import annotations

import base64
import binascii
import json
from pathlib import Path
import re
import shlex
from typing import Any

from canonical.runtime.harbor_environment_transport_v2 import HarborEnvironmentTransport
from canonical.runtime.harbor_pro_patch_handoff_v1 import MAX_PATCH_BYTES, store_candidate_patch

MARKER = 'BRAIN_PRO_PATCH_CANDIDATE_V1:'
_COMMIT = re.compile(r'(?:[0-9a-f]{40}|[0-9a-f]{64})\Z')


class CaptureTransportError(ValueError):
    pass


async def capture_unqualified_candidate(environment: Any, *, repo: str, expected_base: str,
                                        agent_log_dir: Path) -> dict[str, Any]:
    """Execute the capture worker in the given environment, then store bytes once.

    Caller must ensure the environment is properly confined and quiescent and
    the log directory is trusted. This function does not establish either.
    A failed or uncertain exec is never retried; it does not invoke a verifier.
    """
    if not isinstance(repo, str) or not repo.startswith('/') or '\x00' in repo or len(repo) > 4096:
        raise CaptureTransportError('REPOSITORY_PATH_INVALID')
    if not isinstance(expected_base, str) or not _COMMIT.fullmatch(expected_base):
        raise CaptureTransportError('EXPECTED_BASE_INVALID')
    command = ('env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/tmp '
               'python3 -I -B /opt/brain-ro/canonical/runtime/harbor_pro_git_capture_v1.py '
               + shlex.quote(repo) + ' ' + shlex.quote(expected_base))
    receipt = await HarborEnvironmentTransport(environment).exec(command, timeout_sec=300)
    if receipt.returncode != 0:
        raise CaptureTransportError('CONTAINER_CAPTURE_FAILED')
    # Reject duplicate markers and bound the untrusted response before parsing.
    lines = [line[len(MARKER):] for line in receipt.stdout.splitlines() if line.startswith(MARKER)]
    if len(lines) != 1 or len(lines[0]) > 4 * ((MAX_PATCH_BYTES + 2) // 3) + 2000:
        raise CaptureTransportError('CAPTURE_RESPONSE_INVALID')
    try:
        data = json.loads(lines[0])
        if not isinstance(data, dict) or set(data) != {
            'reported_base', 'sha256', 'patch_base64', 'worker_quiescence_verified',
            'patch_completeness_verified', 'external_verifier_invoked'
        }:
            raise ValueError('shape')
        if any(data[x] is not False for x in ('worker_quiescence_verified',
                                               'patch_completeness_verified', 'external_verifier_invoked')):
            raise ValueError('invalid assertion')
        if not isinstance(data['patch_base64'], str):
            raise ValueError('invalid bytes')
        patch = base64.b64decode(data['patch_base64'], validate=True)
    except (ValueError, TypeError, binascii.Error) as exc:
        raise CaptureTransportError('CAPTURE_RESPONSE_INVALID') from exc
    result = store_candidate_patch(agent_log_dir=agent_log_dir, patch=patch,
                                   expected_base=expected_base, reported_base=data['reported_base'],
                                   expected_sha256=data['sha256'])
    result['source'] = 'UNTRUSTED_CONTAINER_EXEC_RESPONSE'
    result['container_boundary_verified'] = False
    return result
