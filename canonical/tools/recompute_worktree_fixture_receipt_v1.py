"""Recompute a controlled fixture receipt from disk in a separate process.

This is producer-built diagnostic code, not an independent human verifier,
signature, attestation, carrier admission or permission to run hostile code.
The source repo, worktree and input must be controlled fixtures. Expected base,
policy and receipt digest need an independent trust source to mean anything.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any

from canonical.runtime import repair_candidate_broker_v1 as snapshots
from canonical.runtime import zero_ambient_namespace_launcher_v1 as ns

SCHEMA = 'PROJECT_BRAIN_ISOLATED_WORKTREE_FIXTURE_V1'
_HEX64 = re.compile(r'[0-9a-f]{64}\Z')
_COMMIT = re.compile(r'(?:[0-9a-f]{40}|[0-9a-f]{64})\Z')
MAX_PAYLOAD = 12_000_000


class RecomputeRefused(ValueError):
    pass


def _git(args: list[str], *, cwd: Path, home: Path, input_bytes: bytes | None = None) -> bytes:
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(home), 'LC_ALL': 'C',
           'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
           'GIT_TERMINAL_PROMPT': '0', 'GIT_OPTIONAL_LOCKS': '0'}
    try:
        p = subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false', *args],
                           cwd=str(cwd), env=env, input=input_bytes, capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RecomputeRefused('GIT_UNAVAILABLE') from exc
    if p.returncode:
        raise RecomputeRefused('GIT_FAILED:' + str(p.returncode))
    return p.stdout


def _measure_policy(input_dir: Path) -> str:
    policy = ns.canonical_policy({'argv': ['/usr/bin/python3', '-I', '/input/fixture.py'],
                                  'input_dir': str(input_dir),
                                  'limits': {'wallclock_s': 12, 'cpu_seconds': 8,
                                             'memory_mb': 128, 'pids': 16, 'scratch_mb': 16}})
    marker = 'mount -t tmpfs -o size="${SCRATCH_MB}m",nosuid,nodev tmpfs "$ROOT/work"'
    if ns._SETUP.count(marker) != 1 or not ns.syscall_filter_hex():
        raise RecomputeRefused('CARRIER_POLICY_UNAVAILABLE')
    setup = ns._SETUP.replace(marker, marker + '\nmkdir -p "$ROOT/work/project"\nmount --bind "$FIXTURE_WORKTREE" "$ROOT/work/project"\nmount -o remount,bind,nosuid,nodev "$ROOT/work/project"')
    script = (input_dir / 'fixture.py').read_bytes()
    if not script or len(script) > 32768:
        raise RecomputeRefused('FIXTURE_SCRIPT_INVALID')
    basis = {'policy_sha256': ns.policy_sha256(policy), 'setup_sha256': hashlib.sha256(setup.encode()).hexdigest(),
             'pid1_sha256': hashlib.sha256(ns._PID1_GUARD.encode()).hexdigest(),
             'syscall_filter_sha256': ns.syscall_filter_sha256(),
             'git_visibility': 'QUARANTINED_BEFORE_WORKER',
             'snapshot_limits': vars(snapshots.FIXTURE_WORKTREE_LIMITS),
             'fixture_script_sha256': hashlib.sha256(script).hexdigest()}
    return hashlib.sha256(json.dumps(basis, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _modes(path: Path, snap: snapshots.ProjectSnapshot) -> dict[str, int]:
    return {p: os.lstat(path / p).st_mode & 0o7777 for p in (*snap.directories, *(name for name, _ in snap.files))}


def recompute(*, source: Path, worktree: Path, input_dir: Path, receipt: dict[str, Any],
              effects: dict[str, bytes], expected_base: str, expected_policy: str,
              expected_receipt_sha256: str) -> dict[str, Any]:
    if not isinstance(expected_base, str) or not _COMMIT.fullmatch(expected_base):
        raise RecomputeRefused('EXPECTED_BASE_INVALID')
    if not isinstance(expected_policy, str) or not _HEX64.fullmatch(expected_policy):
        raise RecomputeRefused('EXPECTED_POLICY_INVALID')
    if not isinstance(expected_receipt_sha256, str) or not _HEX64.fullmatch(expected_receipt_sha256):
        raise RecomputeRefused('EXPECTED_RECEIPT_INVALID')
    if not isinstance(receipt, dict) or set(receipt) != {
        'schema', 'base_commit', 'policy_sha256', 'before_snapshot_sha256', 'after_snapshot_sha256',
        'fixture_returncode', 'effects',
    } or receipt.get('schema') != SCHEMA:
        raise RecomputeRefused('RECEIPT_SHAPE_INVALID')
    actual_digest = hashlib.sha256(json.dumps(receipt, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    if actual_digest != expected_receipt_sha256:
        raise RecomputeRefused('RECEIPT_DIGEST_MISMATCH')
    if receipt['base_commit'] != expected_base:
        raise RecomputeRefused('BASE_MISMATCH')
    if type(receipt['fixture_returncode']) is not int or receipt['fixture_returncode'] != 0:
        raise RecomputeRefused('WORKER_RESULT_INVALID')
    policy = _measure_policy(input_dir)
    if policy != expected_policy or receipt['policy_sha256'] != expected_policy:
        raise RecomputeRefused('POLICY_MISMATCH')
    if not isinstance(effects, dict) or not isinstance(receipt['effects'], dict) or set(effects) != set(receipt['effects']):
        raise RecomputeRefused('EFFECT_SET_MISMATCH')
    total = 0
    for name, data in effects.items():
        meta = receipt['effects'][name]
        if not isinstance(name, str) or not isinstance(data, bytes) or not isinstance(meta, dict) or set(meta) != {'sha256', 'size'}:
            raise RecomputeRefused('EFFECT_SHAPE_INVALID')
        total += len(data)
        if (total > 8_000_000 or type(meta['size']) is not int or meta['size'] != len(data)
                or meta['sha256'] != hashlib.sha256(data).hexdigest()):
            raise RecomputeRefused('EFFECT_BYTES_MISMATCH')
    patch = effects.get('patch.diff')
    if not isinstance(patch, bytes) or not patch:
        raise RecomputeRefused('PATCH_MISSING')
    with tempfile.TemporaryDirectory(prefix='fixture_receipt_recompute_') as tmp:
        root = Path(tmp); baseline = root / 'baseline'
        _git(['clone', '--no-local', '--no-hardlinks', '--no-checkout', '--quiet', '--', str(source.resolve(strict=True)), str(baseline)], cwd=root, home=root)
        _git(['checkout', '--detach', '--force', expected_base], cwd=baseline, home=root)
        head = _git(['rev-parse', '--verify', 'HEAD^{commit}'], cwd=baseline, home=root).decode('ascii').strip()
        if head != expected_base:
            raise RecomputeRefused('CHECKED_OUT_BASE_MISMATCH')
        os.rename(baseline / '.git', root / 'git_baseline')
        before = snapshots.snapshot_project(baseline, limits=snapshots.FIXTURE_WORKTREE_LIMITS)
        after = snapshots.snapshot_project(worktree, limits=snapshots.FIXTURE_WORKTREE_LIMITS)
        after2 = snapshots.snapshot_project(worktree, limits=snapshots.FIXTURE_WORKTREE_LIMITS)
        if after.digest != after2.digest or after.files != after2.files:
            raise RecomputeRefused('WORKTREE_CHANGED_DURING_RECOMPUTE')
        if before.digest != receipt['before_snapshot_sha256'] or after.digest != receipt['after_snapshot_sha256']:
            raise RecomputeRefused('SNAPSHOT_MISMATCH')
        if _modes(baseline, before) != _modes(worktree, after):
            raise RecomputeRefused('MODE_MISMATCH')
        old, new = dict(before.files), dict(after.files)
        if set(old) != set(new) or before.directories != after.directories:
            raise RecomputeRefused('LAYOUT_MISMATCH')
        changed = {name: data for name, data in new.items() if old[name] != data}
        if set(effects) != {'patch.diff', *('files/' + name for name in changed)}:
            raise RecomputeRefused('CHANGED_FILE_SET_MISMATCH')
        for name, data in changed.items():
            if effects['files/' + name] != data:
                raise RecomputeRefused('CHANGED_FILE_BYTES_MISMATCH')
        _git(['apply', '--check', '-'], cwd=baseline, home=root, input_bytes=patch)
        _git(['apply', '-'], cwd=baseline, home=root, input_bytes=patch)
        applied = snapshots.snapshot_project(baseline, limits=snapshots.FIXTURE_WORKTREE_LIMITS)
        if applied.digest != after.digest or applied.files != after.files:
            raise RecomputeRefused('PATCH_DOES_NOT_REPRODUCE_WORKTREE')
    return {'status': 'FIXTURE_BYTES_RECOMPUTED', 'producer_built': True,
            'independent_attestation': False, 'carrier_qualified': False,
            'execution_authority': False, 'publication_authority': False,
            'receipt_sha256': actual_digest, 'patch_sha256': hashlib.sha256(patch).hexdigest()}


def main() -> int:
    try:
        raw = sys.stdin.buffer.read(MAX_PAYLOAD + 1)
        if not raw or len(raw) > MAX_PAYLOAD:
            raise RecomputeRefused('INPUT_BYTES_INVALID')
        payload = json.loads(raw)
        effects = {k: base64.b64decode(v, validate=True) for k, v in payload['effects'].items()}
        result = recompute(source=Path(payload['source']), worktree=Path(payload['worktree']),
                           input_dir=Path(payload['input_dir']), receipt=payload['receipt'], effects=effects,
                           expected_base=payload['expected_base'], expected_policy=payload['expected_policy'],
                           expected_receipt_sha256=payload['expected_receipt_sha256'])
        print(json.dumps(result, sort_keys=True))
        return 0
    except (RecomputeRefused, snapshots.CandidateDenied, OSError, ValueError, TypeError,
            KeyError, binascii.Error) as exc:
        print(json.dumps({'status': 'FAIL_CLOSED', 'reason': str(exc),
                          'independent_attestation': False, 'execution_authority': False}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
