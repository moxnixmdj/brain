#!/usr/bin/env python3
"""Unqualified Git patch capture for a trusted fixture or confined task container.

Checks HEAD before and after capture and preserves the normal index using a
separate temporary index. This does NOT establish worker quiescence, authenticate
Git metadata, guarantee a complete worktree snapshot, or run a verifier. Never
run this against an untrusted repository on the host: Git add may run configured
clean filters. The experimental opt-in Harbor path may dispatch this tool.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any

MARKER = "BRAIN_PRO_PATCH_CANDIDATE_V1:"
MAX_PATCH_BYTES = 20_000_000
_COMMIT = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")


class CaptureError(ValueError):
    pass


def capture_candidate(repo: Path, expected_base: str) -> dict[str, Any]:
    """Capture final nonignored worktree changes relative to HEAD, not staged-only.

    Caller must already have confined the task and stopped all mutators. A
    temporary index avoids modifying the task's staging area. Ignored untracked
    files, submodule contents and external effects are not represented by a Git
    patch. Two matching HEAD reads do not guarantee quiescence or provenance.
    """
    if not isinstance(expected_base, str) or not _COMMIT.fullmatch(expected_base):
        raise CaptureError("EXPECTED_BASE_INVALID")
    try:
        root = Path(repo).resolve(strict=True)
    except (OSError, TypeError, ValueError, RuntimeError) as exc:
        raise CaptureError("REPOSITORY_INVALID") from exc
    if not root.is_dir():
        raise CaptureError("REPOSITORY_INVALID")
    brain = Path('/opt/brain-ro').resolve()
    if root == brain or root in brain.parents:
        raise CaptureError("BRAIN_ROOT_INSIDE_REPOSITORY")

    with tempfile.TemporaryDirectory(prefix='brain-pro-index-') as temp:
        env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': temp, 'LC_ALL': 'C',
               'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
               'GIT_TERMINAL_PROMPT': '0', 'GIT_OPTIONAL_LOCKS': '0',
               'GIT_INDEX_FILE': str(Path(temp) / 'index')}

        def git(*args: str) -> bytes:
            try:
                result = subprocess.run(
                    ['git', '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
                     '-c', 'core.excludesfile=/dev/null', '-c', 'core.attributesfile=/dev/null', *args],
                    cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    timeout=120, check=False)
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise CaptureError('GIT_EXECUTION_FAILED') from exc
            if result.returncode != 0:
                raise CaptureError('GIT_COMMAND_FAILED')
            return result.stdout

        # Prevent a subdirectory from silently changing the patch root.
        top = git('rev-parse', '--show-toplevel').decode('utf-8', 'strict').strip()
        if Path(top).resolve() != root:
            raise CaptureError('REPOSITORY_NOT_TOP_LEVEL')

        def head() -> str:
            return git('rev-parse', '--verify', 'HEAD^{commit}').decode('ascii', 'strict').strip()

        if head() != expected_base:
            raise CaptureError('BASE_MISMATCH_BEFORE_CAPTURE')
        git('read-tree', 'HEAD')
        git('add', '-A', '--', '.')
        patch = git('diff', '--cached', '--binary', '--full-index', '--no-ext-diff', '--no-textconv', '--')
        if len(patch) > MAX_PATCH_BYTES:
            raise CaptureError('PATCH_TOO_LARGE')
        if head() != expected_base:
            raise CaptureError('BASE_MISMATCH_AFTER_CAPTURE')
    return {'reported_base': expected_base, 'sha256': hashlib.sha256(patch).hexdigest(),
            'patch_base64': base64.b64encode(patch).decode('ascii'),
            'worker_quiescence_verified': False, 'patch_completeness_verified': False,
            'external_verifier_invoked': False}


def main() -> int:
    try:
        if len(sys.argv) != 3:
            raise CaptureError('REPOSITORY_AND_BASE_REQUIRED')
        result = capture_candidate(Path(sys.argv[1]), sys.argv[2])
        print(MARKER + json.dumps(result, sort_keys=True), flush=True)
        return 0
    except (CaptureError, UnicodeError, OSError) as exc:
        print('BRAIN_PRO_PATCH_CAPTURE_REFUSED:' + str(exc)[:200], file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
