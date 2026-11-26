"""Host-side paired route diagnostic, NOT a Harbor runner or a benchmark grade.

Use a clean shallow clone of the *base* revision, public instruction and prebuilt
Python venv. Each treatment gets a fresh namespace and private working copy.
The Brain mount is relocated (/input/producer in this launcher); no evaluator,
other treatment, task ID, network fetch or teacher memory goes into the room.
See ONE_EXPERIENCE_AND_ITS_LIMITS_20261126.md for protocol and reproduce commands.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time


def run(argv: list[str], *, seconds: int, cwd: Path) -> subprocess.CompletedProcess:
    # Child inherits no broker FD or host environment; no shell interpretation.
    return subprocess.run(argv, cwd=cwd, env={'PATH': '/usr/bin:/bin', 'HOME': '/tmp', 'LC_ALL': 'C.UTF-8',
                          'GIT_CONFIG_NOSYSTEM': '1', 'PYTHONDONTWRITEBYTECODE': '1'},
                          stdin=subprocess.DEVNULL, capture_output=True, timeout=seconds, check=False)


def inside() -> dict:
    root, repo = Path('/input/producer'), Path('/work/repo')
    shutil.copytree('/input/base', repo, symlinks=True)
    # Only base-native dependencies. Do not commit the environment symlink in a patch.
    (repo / '.venv').symlink_to('/input/venv', target_is_directory=True)
    info = repo / '.git/info'
    info.mkdir(exist_ok=True)
    with (info / 'exclude').open('a') as f:
        f.write('\n/.venv\n')
    base = run(['git', 'rev-parse', '--verify', 'HEAD'], seconds=10, cwd=repo).stdout.decode().strip()
    task = Path('/input/instruction.txt').read_text().strip()
    worker = root / 'canonical/runtime/harbor_container_solver_worker_v1.py'
    runner = 'canonical/swe_kernel/harbor_in_container_runner_v1.py'
    capture = root / 'canonical/runtime/harbor_pro_git_capture_v1.py'
    obs, trace = [], []
    for cycle in range(1, 9):
        # Same public text in both arms; no Harbor host prompt decoration in this control.
        request = {'goal': task, 'mode': 'EPISTEMIC', 'inputs': {'harbor_task': task, 'observations': obs, 'cycle': cycle}}
        arg = base64.b64encode(json.dumps(request).encode()).decode()
        t0 = time.monotonic()
        p = run(['/usr/bin/python3', '-I', '-B', str(worker), arg], seconds=60, cwd=repo)
        step = {'cycle': cycle, 'worker_exit': p.returncode, 'worker_s': round(time.monotonic() - t0, 3)}
        trace.append(step)
        marker = b'BRAIN_CONTAINER_SOLVE_V1:'
        if p.returncode or marker not in p.stdout:
            step['error'] = p.stderr.decode(errors='replace')[-400:]
            break
        response = json.loads(p.stdout.split(marker)[-1])
        actions = response.get('actions', [])
        step.update(status=response.get('status'), reason=response.get('reason'), actions=[a['type'] for a in actions])
        if response.get('pass') is not True or len(actions) != 1 or actions[0]['type'] == 'finish':
            break
        if actions[0]['type'] != 'terminal_exec':
            raise ValueError('not a reviewed in-room action')
        args = actions[0]['args']
        parts = shlex.split(args['command'])
        slot = parts.index('/opt/brain-ro/' + runner)
        # This diagnostic runs only the reviewed phase runner, no general terminal commands.
        if parts[:2] != ['env', '-i'] or not parts[2].startswith('PATH=') or parts[3:6] != ['HOME=/tmp', 'python3', '-I']:
            raise ValueError('unexpected runner argv')
        if parts[6:slot] not in (['-B'], ['-B', '-W', 'ignore']):
            raise ValueError('unexpected interpreter options')
        parts[slot] = str(root / runner)
        t0 = time.monotonic()
        cmd = run(parts, seconds=min(180, int(args['timeout_sec'])), cwd=repo)
        stdout, stderr = (v.decode(errors='replace')[-16000:] for v in (cmd.stdout, cmd.stderr))
        step.update(phase=parts[slot+2], command_exit=cmd.returncode, command_s=round(time.monotonic() - t0, 3))
        try:
            step['observed'] = json.loads(stdout.splitlines()[-1])
        except (ValueError, IndexError):
            step.update(stdout_tail=stdout[-400:], stderr_tail=stderr[-400:])
        obs.append({'type': 'terminal_exec', 'stdout': stdout, 'stderr': stderr, 'returncode': cmd.returncode})
    captured = run(['/usr/bin/python3', '-I', '-B', str(capture), str(repo), base], seconds=45, cwd=repo)
    row = {'public_instruction_chars': len(task), 'base': base, 'trace': trace, 'capture_exit': captured.returncode,
           'patch_bytes': None, 'official_reward': None}
    if captured.returncode == 0:
        payload = json.loads(captured.stdout.split(b'BRAIN_PRO_PATCH_CANDIDATE_V1:')[-1])
        data = base64.b64decode(payload['patch_base64'], validate=True)
        if payload['reported_base'] != base or hashlib.sha256(data).hexdigest() != payload['sha256']:
            raise ValueError('invalid capture')
        row.update(patch_bytes=len(data), patch_sha256=payload['sha256'], source_replay='EMPTY_CAPTURE')
        if data:
            fresh = Path('/work/replay')
            shutil.copytree('/input/base', fresh, symlinks=True)
            patch = Path('/tmp/candidate.patch')
            patch.write_bytes(data)
            applied = run(['git', 'apply', '--', str(patch)], seconds=30, cwd=fresh)
            row.update(source_replay='APPLIED' if applied.returncode == 0 else 'APPLY_FAILED',
                       patch_base64=payload['patch_base64'])
    else:
        row['capture_error'] = captured.stderr.decode(errors='replace')[-400:]
    return row


def paired(base: Path, instruction: Path, venv: Path, revisions: list[str]) -> dict:
    # Imported only by the host. The child doesn't receive the main checkout.
    from canonical.runtime.zero_ambient_namespace_launcher_v1 import run_confined
    from canonical.tools.stage_harbor_runtime_v1 import SOURCES, stage
    if (base / '.git').is_symlink() or not (base / '.git/shallow').is_file():
        raise ValueError('expected an actual single-commit shallow base')
    def git_base(*args):
        return subprocess.check_output(['git', '-C', str(base), *args], text=True).strip()
    if git_base('rev-list', '--all', 'HEAD', '--count') != '1' or git_base('status', '--porcelain', '-uall'):
        raise ValueError('base must be clean and contain no other reachable revision')
    if not (venv / 'pyvenv.cfg').is_file():
        raise ValueError('supply a prebuilt target-interpreter environment')
    results = []
    for rev in revisions:
        rev = subprocess.check_output(['git', 'rev-parse', '--verify', rev + '^{commit}'], text=True).strip()
        with tempfile.TemporaryDirectory() as tmp:
            mount = Path(tmp) / 'input'
            mount.mkdir()
            shutil.copytree(base, mount / 'base', symlinks=True)
            shutil.copytree(venv, mount / 'venv', symlinks=True)
            shutil.copyfile(instruction, mount / 'instruction.txt')
            shutil.copyfile(__file__, mount / 'driver.py')
            src = Path(tmp) / 'src'
            for rel in SOURCES:
                p = src / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(subprocess.check_output(['git', 'cat-file', 'blob', rev + ':' + rel]))
            manifest = stage(mount / 'producer', source_root=src)
            result = run_confined({'input_dir': str(mount), 'argv': ['/usr/bin/python3', '-I', '-B', '/input/driver.py', '--inside'],
                                   'expose_runtime_devices': True,
                                   'limits': {'memory_mb': 2048, 'cpu_seconds': 120, 'wallclock_s': 240, 'scratch_mb': 256,
                                              'max_file_mb': 64, 'nofile': 128, 'pids': 128}})
            raw = result.pop('broker_payload')
            results.append({'producer_revision': rev, 'cold_manifest': manifest, 'launcher': result,
                            'measurement': json.loads(raw) if raw else None})
    return {'kind': 'source-only paired route control; no official image, Harbor, verifier or grade',
            'input_instruction_sha256': hashlib.sha256(instruction.read_bytes()).hexdigest(), 'rows': results}


if __name__ == '__main__':
    if sys.argv[1:] == ['--inside']:
        try:
            result = inside()
        except Exception as exc:
            result = {'incomplete': f'{type(exc).__name__}: {exc}', 'official_reward': None}
        with os.fdopen(int(os.environ['PROJECT_BRAIN_BROKER_FD']), 'wb') as out:
            out.write(json.dumps(result).encode())
        sys.exit(2 if 'incomplete' in result else 0)
    p = argparse.ArgumentParser(description=__doc__)
    for flag in ('base', 'instruction', 'venv'):
        p.add_argument('--' + flag, type=Path, required=True)
    p.add_argument('--revision', action='append', required=True)
    a = p.parse_args()
    print(json.dumps(paired(a.base, a.instruction, a.venv, a.revision), indent=2))
