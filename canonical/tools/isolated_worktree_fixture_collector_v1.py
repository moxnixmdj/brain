"""Controlled namespace worktree experiment; not qualified for untrusted repair.

Creates its own temporary clone and mounts only that clone writable. It checks
HEAD before a trusted fixture runs, waits for the namespace init to exit, then
snapshots files twice and builds a limited text diff in the host. This is NOT a
security admission, independently verified receipt, general SWE-bench carrier,
or proof against an external host process modifying the temporary directory.
Only trusted test fixtures may use it. Nothing is adopted to the source repo.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
from typing import Any

from canonical.runtime import repair_candidate_broker_v1 as snapshot
from canonical.runtime import zero_ambient_namespace_launcher_v1 as ns
from canonical.tools import isolated_effect_receipt_verifier_v1 as verifier

SCHEMA = 'PROJECT_BRAIN_ISOLATED_WORKTREE_FIXTURE_V1'
_SAFE_PATH = re.compile(r'[A-Za-z0-9_.\-/]+\Z')


class FixtureRefused(ValueError):
    pass


def _git(args: list[str], *, cwd: Path, home: Path, allowed: tuple[int, ...] = (0,)) -> bytes:
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(home), 'LC_ALL': 'C',
           'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
           'GIT_TERMINAL_PROMPT': '0', 'GIT_OPTIONAL_LOCKS': '0'}
    try:
        p = subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false', *args],
                           cwd=str(cwd), env=env, stdin=subprocess.DEVNULL,
                           capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise FixtureRefused('GIT_UNAVAILABLE') from exc
    if p.returncode not in allowed:
        raise FixtureRefused('GIT_FAILED:' + str(p.returncode))
    return p.stdout


def _snapshot_worktree(worktree: Path, quarantine: Path, *, restore: bool) -> snapshot.ProjectSnapshot:
    """Snapshot real files after temporarily moving the scratch clone's .git.

    Assumes the private host temp directory has no external writers. The existing
    snapshotter rejects symlinks, hardlinks and specials and checks metadata for
    changes during reads. This cannot detect a privileged external writer.
    """
    gitdir = worktree / '.git'
    if not gitdir.is_dir() or gitdir.is_symlink() or quarantine.exists():
        raise FixtureRefused('SCRATCH_GIT_DIRECTORY_INVALID')
    os.rename(gitdir, quarantine)
    try:
        return snapshot.snapshot_project(worktree)
    except (snapshot.CandidateDenied, OSError) as exc:
        raise FixtureRefused('WORKTREE_SNAPSHOT_FAILED') from exc
    finally:
        if restore:
            os.rename(quarantine, gitdir)


def _modes(worktree: Path, captured: snapshot.ProjectSnapshot) -> dict[str, int]:
    try:
        return {path: (os.lstat(worktree / path).st_mode & 0o7777)
                for path in (*captured.directories, *(p for p, _ in captured.files))}
    except OSError as exc:
        raise FixtureRefused('WORKTREE_MODE_SNAPSHOT_FAILED') from exc


def _limited_text_diff(before: snapshot.ProjectSnapshot, after: snapshot.ProjectSnapshot) -> tuple[bytes, dict[str, bytes]]:
    old, new = dict(before.files), dict(after.files)
    if set(old) != set(new) or before.directories != after.directories:
        raise FixtureRefused('FILE_LAYOUT_CHANGED_UNSUPPORTED')
    changed = {p: new[p] for p in sorted(new) if new[p] != old[p]}
    chunks: list[str] = []
    for path, data in changed.items():
        if not _SAFE_PATH.fullmatch(path):
            raise FixtureRefused('DIFF_PATH_UNSUPPORTED')
        try:
            old_text, new_text = old[path].decode('utf-8'), data.decode('utf-8')
        except UnicodeError as exc:
            raise FixtureRefused('NON_TEXT_DIFF_UNSUPPORTED') from exc
        if '\x00' in old_text or '\x00' in new_text or (old_text and not old_text.endswith('\n')) or (new_text and not new_text.endswith('\n')):
            raise FixtureRefused('TEXT_DIFF_UNSUPPORTED')
        chunks.append('diff --git a/' + path + ' b/' + path + '\n')
        chunks.extend(difflib.unified_diff(old_text.splitlines(keepends=True), new_text.splitlines(keepends=True),
                                           fromfile='a/'+path, tofile='b/'+path))
    return ''.join(chunks).encode('utf-8'), changed


def _run_fixture(input_dir: Path, worktree: Path, script: str) -> tuple[int, str]:
    """Run fixed trusted fixture bytes using a private mount and PID-1 guard."""
    p = ns.canonical_policy({'argv': ['/usr/bin/python3', '-I', '/input/fixture.py'],
                             'input_dir': str(input_dir),
                             'limits': {'wallclock_s': 12, 'cpu_seconds': 8,
                                        'memory_mb': 128, 'pids': 16, 'scratch_mb': 16}})
    if not ns.syscall_filter_hex():
        raise FixtureRefused('SYSCALL_FILTER_UNAVAILABLE')
    names = ['unshare', 'mount', 'python3', 'setpriv', 'ip', 'bash', 'env']
    binaries = {n: ns.resolve_system_binary(n) for n in names}
    if any(not binaries[n] for n in names):
        raise FixtureRefused('HOST_PRIMITIVE_MISSING')
    original = 'mount -t tmpfs -o size="${SCRATCH_MB}m",nosuid,nodev tmpfs "$ROOT/work"'
    replacement = original + '\nmkdir -p "$ROOT/work/project"\nmount --bind "$FIXTURE_WORKTREE" "$ROOT/work/project"\nmount -o remount,bind,nosuid,nodev "$ROOT/work/project"'
    if ns._SETUP.count(original) != 1:
        raise FixtureRefused('SETUP_TEMPLATE_CHANGED')
    setup = ns._SETUP.replace(original, replacement)
    policy_basis = {'policy_sha256': ns.policy_sha256(p), 'setup_sha256': hashlib.sha256(setup.encode()).hexdigest(),
                    'pid1_sha256': hashlib.sha256(ns._PID1_GUARD.encode()).hexdigest(),
                    'syscall_filter_sha256': ns.syscall_filter_sha256(),
                    'fixture_script_sha256': hashlib.sha256(script.encode('utf-8')).hexdigest()}
    policy_sha = hashlib.sha256(json.dumps(policy_basis, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    (input_dir / 'fixture.py').write_text(script, encoding='utf-8')
    root = Path(tempfile.mkdtemp(prefix='fixture_ns_root_'))
    parent, child = socket.socketpair()
    pidfd = None; proc = None
    try:
        pidfd = os.pidfd_open(os.getpid(), 0)
        lim = p['limits']
        cmd = [binaries['unshare'], '--user', '--map-root-user', '--mount', '--net', '--pid', '--fork', '--ipc', '--uts',
               binaries['python3'], '-I', '-c', ns._PID1_GUARD, str(pidfd), str(child.fileno()),
               binaries['bash'], '-c', setup, '_', str(root), p['input_dir'], str(child.fileno()),
               str(lim['memory_mb'] * 1024), str(lim['cpu_seconds']), str(math.ceil(lim['max_file_mb'] * 1024)),
               str(lim['nofile']), str(lim['pids']), str(lim['scratch_mb']), '0', '0',
               binaries['setpriv'], '--no-new-privs', '--bounding-set=-all', '--inh-caps=-all', '--ambient-caps=-all',
               binaries['env'], '-i', 'PATH=/usr/bin:/bin', 'HOME=/tmp', 'PYTHONDONTWRITEBYTECODE=1',
               'PROJECT_BRAIN_BROKER_FD=' + str(child.fileno()), *p['argv']]
        env = {'FIXTURE_WORKTREE': str(worktree), 'PYTHONDONTWRITEBYTECODE': '1'}
        kw: dict[str, Any] = {'stdin': subprocess.DEVNULL, 'stdout': subprocess.DEVNULL, 'stderr': subprocess.DEVNULL,
                              'env': env, 'pass_fds': (pidfd, child.fileno()), 'start_new_session': True}
        if os.geteuid() == 0:
            kw.update(user=p['host_uid'], group=p['host_gid'], extra_groups=[])
        proc = subprocess.Popen(cmd, **kw)
        child.close()
        try:
            rc = proc.wait(timeout=lim['wallclock_s'])
        except subprocess.TimeoutExpired as exc:
            os.killpg(proc.pid, 9); proc.wait(timeout=5)
            raise FixtureRefused('FIXTURE_TIMEOUT') from exc
        if rc != 0:
            raise FixtureRefused('FIXTURE_FAILED:' + str(rc))
        # unshare --fork waited for namespace PID 1; its exit causes Linux to
        # kill and reap processes remaining in that PID namespace. The exact
        # behaviour/configuration still needs independent carrier review.
        return rc, policy_sha
    except (OSError, AttributeError) as exc:
        raise FixtureRefused('FIXTURE_LAUNCH_FAILED') from exc
    finally:
        if proc is not None and proc.poll() is None:
            try: os.killpg(proc.pid, 9)
            except ProcessLookupError: pass
            proc.wait(timeout=5)
        child.close(); parent.close()
        if pidfd is not None: os.close(pidfd)
        shutil.rmtree(root, ignore_errors=True)


def verify_fixture_worktree_receipt(receipt: dict[str, Any], effect_bytes: dict[str, bytes], *,
                                   expected_receipt_sha256: str, expected_base_commit: str,
                                   expected_policy_sha256: str, expected_effect_paths: tuple[str, ...]) -> bytes:
    """Check exact fixture output bytes against separately supplied expectations.

    The source of expected values determines trust. A producer-generated digest
    is not a signature, independent verification or an execution authorization.
    """
    if not isinstance(receipt, dict) or set(receipt) != {
        'schema', 'base_commit', 'policy_sha256', 'before_snapshot_sha256',
        'after_snapshot_sha256', 'fixture_returncode', 'effects',
    } or receipt.get('schema') != SCHEMA:
        raise FixtureRefused('RECEIPT_SHAPE_INVALID')
    try:
        actual_hash = hashlib.sha256(json.dumps(receipt, sort_keys=True, separators=(',', ':'),
                                                allow_nan=False).encode()).hexdigest()
    except (TypeError, ValueError, UnicodeError) as exc:
        raise FixtureRefused('RECEIPT_SHAPE_INVALID') from exc
    if not isinstance(expected_receipt_sha256, str) or not verifier._DIGEST.fullmatch(expected_receipt_sha256) or actual_hash != expected_receipt_sha256:
        raise FixtureRefused('RECEIPT_HASH_MISMATCH')
    for key in ('before_snapshot_sha256', 'after_snapshot_sha256'):
        if not isinstance(receipt[key], str) or not verifier._DIGEST.fullmatch(receipt[key]):
            raise FixtureRefused('SNAPSHOT_HASH_INVALID')
    if type(receipt['fixture_returncode']) is not int or receipt['fixture_returncode'] != 0:
        raise FixtureRefused('FIXTURE_RESULT_INVALID')
    inner = {'schema': verifier.SCHEMA, 'base_commit': receipt['base_commit'],
             'policy_sha256': receipt['policy_sha256'], 'effects': receipt['effects']}
    try:
        return verifier.verify_patch(inner, effect_bytes, expected_receipt_sha256=verifier.receipt_digest(inner),
                                     expected_base_commit=expected_base_commit,
                                     expected_policy_sha256=expected_policy_sha256,
                                     expected_effect_paths=expected_effect_paths, expected_patch_path='patch.diff')
    except verifier.ReceiptRefused as exc:
        raise FixtureRefused('EFFECT_VERIFICATION_FAILED:' + str(exc)) from exc


def collect_fixture_worktree(source_repo: str | Path, expected_base_commit: str, fixture_script: str) -> dict[str, Any]:
    """Return a producer-run fixture receipt only; not an admission or signature."""
    if not isinstance(expected_base_commit, str) or not verifier._COMMIT.fullmatch(expected_base_commit):
        raise FixtureRefused('BASE_COMMIT_INVALID')
    if not isinstance(fixture_script, str) or not fixture_script or len(fixture_script.encode()) > 32_768:
        raise FixtureRefused('FIXTURE_SCRIPT_INVALID')
    source = Path(source_repo).resolve(strict=True)
    if not source.is_dir():
        raise FixtureRefused('SOURCE_REPOSITORY_INVALID')
    with tempfile.TemporaryDirectory(prefix='brain_fixture_collector_') as temp:
        root = Path(temp); worktree = root / 'worktree'; inp = root / 'input'; inp.mkdir()
        _git(['clone', '--no-local', '--no-hardlinks', '--no-checkout', '--quiet', '--', str(source), str(worktree)], cwd=root, home=root)
        try:
            _git(['checkout', '--detach', '--force', expected_base_commit], cwd=worktree, home=root)
        except FixtureRefused as exc:
            raise FixtureRefused('BASE_COMMIT_UNAVAILABLE') from exc
        actual = _git(['rev-parse', '--verify', 'HEAD^{commit}'], cwd=worktree, home=root).decode('ascii').strip()
        if actual != expected_base_commit:
            raise FixtureRefused('BASE_COMMIT_MISMATCH')
        if _git(['status', '--porcelain', '--untracked-files=all'], cwd=worktree, home=root):
            raise FixtureRefused('BASE_WORKTREE_NOT_CLEAN')
        # The same clone is bind-mounted inside the namespace. HEAD is checked
        # by the parent before launch, never by the fixture itself.
        before = _snapshot_worktree(worktree, root / 'git_before', restore=True)
        modes_before = _modes(worktree, before)
        try:
            git_before = snapshot.snapshot_project(worktree / '.git')
        except snapshot.CandidateDenied as exc:
            raise FixtureRefused('GIT_METADATA_SNAPSHOT_FAILED') from exc
        rc, policy_sha = _run_fixture(inp, worktree, fixture_script)
        try:
            git_after = snapshot.snapshot_project(worktree / '.git')
        except snapshot.CandidateDenied as exc:
            raise FixtureRefused('GIT_METADATA_SNAPSHOT_FAILED') from exc
        if git_before.digest != git_after.digest or git_before.files != git_after.files:
            raise FixtureRefused('GIT_METADATA_CHANGED')
        after = _snapshot_worktree(worktree, root / 'git_after', restore=False)
        # Metadata/content checks during each read plus a second full snapshot
        # detect many races, but do not claim an adversarial-host guarantee.
        after_again = snapshot.snapshot_project(worktree)
        if after.digest != after_again.digest or after.files != after_again.files:
            raise FixtureRefused('WORKTREE_CHANGED_DURING_COLLECTION')
        if _modes(worktree, after) != modes_before:
            raise FixtureRefused('WORKTREE_MODE_CHANGED_UNSUPPORTED')
        patch, changed = _limited_text_diff(before, after)
        effects = {'patch.diff': patch, **{'files/' + k: v for k, v in changed.items()}}
        receipt = {'schema': SCHEMA, 'base_commit': actual, 'policy_sha256': policy_sha,
                   'before_snapshot_sha256': before.digest, 'after_snapshot_sha256': after.digest,
                   'fixture_returncode': rc,
                   'effects': {k: {'size': len(v), 'sha256': hashlib.sha256(v).hexdigest()}
                               for k, v in sorted(effects.items())}}
        receipt_sha = hashlib.sha256(json.dumps(receipt, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        if patch:
            verify_fixture_worktree_receipt(receipt, effects, expected_receipt_sha256=receipt_sha,
                                            expected_base_commit=expected_base_commit,
                                            expected_policy_sha256=policy_sha,
                                            expected_effect_paths=tuple(sorted(effects)))
        return {'receipt': receipt, 'receipt_sha256': receipt_sha, 'effect_bytes': effects,
                'patch_bytes': patch, 'carrier_qualified': False,
                'independent_verification': False, 'publication_authority': False}
