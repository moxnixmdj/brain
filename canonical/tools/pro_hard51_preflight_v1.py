"""Read-only SWE-bench Pro V2 HARD-51 metadata preflight; NEVER runs tasks.

This utility hashes selected public instructions and task.toml files against a
pinned upstream checksum manifest. It creates no predictions or receipts and
is not an execution authorization, isolation check, or signature verifier.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tomllib
from typing import Any

DATASET_COMMIT = '66f92766bba642462d4bbe5479e83f91f9211862'
MANIFEST_SHA256 = '9d84f8507c89241d42d8b3ef911600a1ec75dbbb32687ce9b45b93318502c0bd'
IDS_SHA256 = '6e35e84708a26443e1746ae928940555a3188654c90f3a2eb691f4f699482bd1'
DISCLOSED_ID = 'instance_NodeBB__NodeBB-8168c6c40707478f71b8af60300830fe554c778c-vf2cf3cbd463b7ad942381f1c6d077626485a1e9e'
DISCLOSURE = ('Public tests/config.json fail-to-pass and pass-to-pass test names were '
              'displayed to the coding agent during preparation; no gold patch was accessed.')
_ID = re.compile(r'instance_[A-Za-z0-9_.-]+__[A-Za-z0-9_.-]+-[0-9a-f]{40}(?:-v(?:[0-9a-f]{40}|nan))?\Z')
_LINE = re.compile(r'([0-9a-f]{64})  ([^\r\n]+)\Z')


class PreflightRefused(ValueError):
    pass


def _read(path: Path, maximum: int) -> bytes:
    try:
        with path.open('rb') as stream:
            data = stream.read(maximum + 1)
    except OSError as exc:
        raise PreflightRefused('PUBLIC_METADATA_UNREADABLE:' + str(path)) from exc
    if len(data) > maximum:
        raise PreflightRefused('PUBLIC_METADATA_TOO_LARGE:' + str(path))
    return data


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_plan(v2: Path, *, selection: str, requested_isolated_vm_eval: bool = False) -> dict[str, Any]:
    """Check pinned metadata and describe a blocked run without loading tests.

    Fixed hashes identify public upstream bytes, not an authenticated reviewer or
    proof that the runtime, container, or checkout provides isolation.
    """
    if selection not in ('smoke5', 'hard51'):
        raise PreflightRefused('SELECTION_INVALID')
    manifest = _read(v2 / 'SHA256SUMS', 2_000_000)
    if _sha(manifest) != MANIFEST_SHA256:
        raise PreflightRefused('MANIFEST_PIN_MISMATCH')
    try:
        lines = manifest.decode('utf-8').splitlines()
    except UnicodeDecodeError as exc:
        raise PreflightRefused('MANIFEST_INVALID') from exc
    checksums: dict[str, str] = {}
    for line in lines:
        match = _LINE.fullmatch(line)
        if match is None or match.group(2) in checksums:
            raise PreflightRefused('MANIFEST_INVALID')
        checksums[match.group(2)] = match.group(1)
    ids_raw = _read(v2 / 'hard51_ids.txt', 20_000)
    if _sha(ids_raw) != IDS_SHA256 or checksums.get('hard51_ids.txt') != IDS_SHA256:
        raise PreflightRefused('HARD51_PIN_MISMATCH')
    try:
        ids = ids_raw.decode('ascii').splitlines()
    except UnicodeDecodeError as exc:
        raise PreflightRefused('HARD51_INVALID') from exc
    if len(ids) != 51 or len(set(ids)) != 51 or any(not _ID.fullmatch(i) for i in ids):
        raise PreflightRefused('HARD51_INVALID')
    selected = ids[:5] if selection == 'smoke5' else ids
    tasks = []
    for iid in selected:
        metadata: dict[str, bytes] = {}
        for name, maximum in (('instruction.md', 2_000_000), ('task.toml', 256_000)):
            rel = f'tasks/{iid}/{name}'
            data = _read(v2 / rel, maximum)
            if _sha(data) != checksums.get(rel):
                raise PreflightRefused('TASK_METADATA_HASH_MISMATCH:' + rel)
            metadata[name] = data
        try:
            task = tomllib.loads(metadata['task.toml'].decode('utf-8'))
            if task['task']['name'] != 'swebench-pro/' + iid:
                raise PreflightRefused('TASK_NAME_MISMATCH:' + iid)
            if task['agent']['network_mode'] != 'no-network':
                raise PreflightRefused('TASK_NETWORK_POLICY_MISMATCH:' + iid)
            image = task['environment']['docker_image']
            if image != 'ghcr.io/scaleapi/swe-bench_pro-v2:' + iid:
                raise PreflightRefused('TASK_IMAGE_MISMATCH:' + iid)
        except (UnicodeDecodeError, tomllib.TOMLDecodeError, KeyError, TypeError) as exc:
            raise PreflightRefused('TASK_TOML_INVALID:' + iid) from exc
        tasks.append({'instance_id': iid, 'instruction_sha256': _sha(metadata['instruction.md']),
                      'task_toml_sha256': _sha(metadata['task.toml']), 'image': image,
                      'disclosure': DISCLOSURE if iid == DISCLOSED_ID else None,
                      'status': 'NOT_RUN_ONESHOT_CARRIER_UNQUALIFIED'})
    return {'schema': 'PROJECT_BRAIN_PRO_HARD51_PREFLIGHT_V1', 'dataset_commit': DATASET_COMMIT,
            'manifest_sha256': MANIFEST_SHA256, 'selection': selection, 'tasks': tasks,
            'docker_cli_found': shutil.which('docker') is not None,
            'harbor_cli_found': shutil.which('harbor') is not None,
            'isolation_verified': False, 'requested_isolated_vm_eval': requested_isolated_vm_eval,
            'execution_authorized': False, 'instances_executed': 0, 'patches_verified': 0,
            'status': 'PREFLIGHT_ONLY_EXECUTION_BLOCKED',
            'note': 'Pinned metadata integrity only; not an authenticated attestation or evaluation.'}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--v2-root', type=Path, required=True, help='local pinned SWE-bench Pro v2 directory')
    parser.add_argument('--selection', choices=('smoke5', 'hard51'), default='smoke5')
    parser.add_argument('--allow-isolated-vm-eval', action='store_true',
                        help='record request only; never enables execution or proves isolation')
    args = parser.parse_args(argv)
    try:
        plan = build_plan(args.v2_root, selection=args.selection,
                          requested_isolated_vm_eval=args.allow_isolated_vm_eval)
    except PreflightRefused as exc:
        print(json.dumps({'status': 'PREFLIGHT_FAILED', 'reason': str(exc),
                          'execution_authorized': False}), file=sys.stderr)
        return 2
    print(json.dumps(plan, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
