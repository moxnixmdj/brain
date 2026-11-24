"""Controlled fixture checks only; these do not qualify the carrier."""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

from canonical.runtime import brokered_workspace_execution_v1 as broker
from canonical.runtime import repair_candidate_broker_v1 as snapshot
from canonical.tools import isolated_worktree_fixture_collector_v1 as collector
from canonical.tests.test_namespace_carrier_host_observed_v1 import children, proc_identity, still_alive


class WorktreeFixtureCollectorTests(unittest.TestCase):
    def setUp(self):
        if not broker.namespace_broker_available():
            self.skipTest('namespace carrier unavailable; not qualified')
        self.temp = tempfile.TemporaryDirectory(prefix='worktree_fixture_test_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'; self.repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        (self.repo / 'mod.py').write_text('value = 1\n', encoding='utf-8')
        subprocess.run(['git', '-C', str(self.repo), 'add', 'mod.py'], check=True)
        self.commit('initial')
        self.base = subprocess.check_output(['git', '-C', str(self.repo), 'rev-parse', 'HEAD'], text=True).strip()

    def commit(self, message):
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=Fixture', '-c',
                        'user.email=fixture@example.invalid', 'commit', '-qm', message], check=True)

    def test_historical_base_is_checked_and_source_is_unchanged(self):
        (self.repo / 'mod.py').write_text('value = 9\n', encoding='utf-8')
        subprocess.run(['git', '-C', str(self.repo), 'add', 'mod.py'], check=True)
        self.commit('later')
        fixture = "from pathlib import Path\nPath('/work/project/mod.py').write_text('value = 2\\n')\n"
        result = collector.collect_fixture_worktree(self.repo, self.base, fixture)
        self.assertEqual(result['receipt']['base_commit'], self.base)
        self.assertEqual(result['effect_bytes']['files/mod.py'], b'value = 2\n')
        self.assertIn(b'-value = 1\n+value = 2\n', result['patch_bytes'])
        self.assertEqual((self.repo / 'mod.py').read_bytes(), b'value = 9\n')
        self.assertFalse(result['carrier_qualified'])
        self.assertFalse(result['independent_verification'])
        self.assertEqual(result['separate_recomputation']['status'], 'FIXTURE_BYTES_RECOMPUTED')
        self.assertFalse(result['separate_recomputation']['independent_attestation'])
        self.assertFalse(result['publication_authority'])
        for name, data in result['effect_bytes'].items():
            self.assertEqual(result['receipt']['effects'][name]['sha256'], hashlib.sha256(data).hexdigest())

    def test_larger_multi_file_fixture_and_host_sentinel(self):
        directory = self.repo / 'pkg'; directory.mkdir()
        (directory / 'core.py').write_text('answer = 1\n', encoding='utf-8')
        for index in range(520):
            (directory / f'file_{index:03}.py').write_text('pass\n', encoding='utf-8')
        subprocess.run(['git', '-C', str(self.repo), 'add', 'pkg'], check=True)
        self.commit('large fixture')
        base = subprocess.check_output(['git', '-C', str(self.repo), 'rev-parse', 'HEAD'], text=True).strip()
        sentinel = self.root / 'host-sentinel'; sentinel.write_bytes(b'HOST_UNCHANGED')
        fixture = f'''from pathlib import Path
try:
    Path({str(sentinel)!r}).write_bytes(b'ESCAPE')
except OSError:
    pass
else:
    raise RuntimeError('host sentinel was reachable')
Path('/work/project/mod.py').write_text('value = 2\\n')
Path('/work/project/pkg/core.py').write_text('answer = 2\\n')
'''
        result = collector.collect_fixture_worktree(self.repo, base, fixture)
        self.assertEqual(result['receipt']['base_commit'], base)
        self.assertEqual(set(result['effect_bytes']), {'patch.diff', 'files/mod.py', 'files/pkg/core.py'})
        self.assertEqual(result['effect_bytes']['files/mod.py'], b'value = 2\n')
        self.assertEqual(result['effect_bytes']['files/pkg/core.py'], b'answer = 2\n')
        for path, data in result['effect_bytes'].items():
            self.assertEqual(result['receipt']['effects'][path]['sha256'], hashlib.sha256(data).hexdigest())
        self.assertIn(b'diff --git a/mod.py b/mod.py', result['patch_bytes'])
        self.assertIn(b'diff --git a/pkg/core.py b/pkg/core.py', result['patch_bytes'])
        check = subprocess.run(['git', '-C', str(self.repo), 'apply', '--check', '-'],
                               input=result['patch_bytes'], capture_output=True)
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertEqual(sentinel.read_bytes(), b'HOST_UNCHANGED')
        self.assertEqual((self.repo / 'mod.py').read_bytes(), b'value = 1\n')
        self.assertEqual((directory / 'core.py').read_bytes(), b'answer = 1\n')
        self.assertFalse(result['carrier_qualified'])
        self.assertFalse(result['independent_verification'])
        self.assertFalse(result['publication_authority'])

    def test_host_receipt_refuses_tampered_base_and_file_bytes(self):
        fixture = "from pathlib import Path\nPath('/work/project/mod.py').write_text('value = 2\\n')\n"
        result = collector.collect_fixture_worktree(self.repo, self.base, fixture)
        args = {'expected_receipt_sha256': result['receipt_sha256'], 'expected_base_commit': self.base,
                'expected_policy_sha256': result['receipt']['policy_sha256'],
                'expected_effect_paths': tuple(sorted(result['effect_bytes']))}
        self.assertEqual(collector.verify_fixture_worktree_receipt(result['receipt'], result['effect_bytes'], **args),
                         result['patch_bytes'])
        altered = dict(result['effect_bytes'], **{'files/mod.py': b'value = 3\n'})
        with self.assertRaisesRegex(collector.FixtureRefused, 'EFFECT_DIGEST_MISMATCH'):
            collector.verify_fixture_worktree_receipt(result['receipt'], altered, **args)
        fake = copy.deepcopy(result['receipt']); fake['base_commit'] = 'b' * len(self.base)
        fake_digest = hashlib.sha256(json.dumps(fake, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        with self.assertRaisesRegex(collector.FixtureRefused, 'BASE_COMMIT_MISMATCH'):
            collector.verify_fixture_worktree_receipt(fake, result['effect_bytes'],
                                                       **{**args, 'expected_receipt_sha256': fake_digest})

    def test_separate_recomputation_rejects_real_file_change_after_collection(self):
        original = collector._recompute_in_separate_process
        def mutate_then_recompute(**kwargs):
            (kwargs['worktree'] / 'mod.py').write_text('value = 8\n', encoding='utf-8')
            return original(**kwargs)
        fixture = "from pathlib import Path\nPath('/work/project/mod.py').write_text('value = 2\\n')\n"
        with mock.patch.object(collector, '_recompute_in_separate_process', side_effect=mutate_then_recompute):
            with self.assertRaisesRegex(collector.FixtureRefused, 'SNAPSHOT_MISMATCH'):
                collector.collect_fixture_worktree(self.repo, self.base, fixture)

    def test_separate_recomputation_rejects_rehashed_wrong_base(self):
        original = collector._recompute_in_separate_process
        def forge_then_recompute(**kwargs):
            receipt = copy.deepcopy(kwargs['receipt'])
            receipt['base_commit'] = 'b' * len(self.base)
            digest = hashlib.sha256(json.dumps(receipt, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            return original(**{**kwargs, 'receipt': receipt, 'receipt_sha': digest})
        fixture = "from pathlib import Path\nPath('/work/project/mod.py').write_text('value = 2\\n')\n"
        with mock.patch.object(collector, '_recompute_in_separate_process', side_effect=forge_then_recompute):
            with self.assertRaisesRegex(collector.FixtureRefused, 'BASE_MISMATCH'):
                collector.collect_fixture_worktree(self.repo, self.base, fixture)

    def test_separate_recomputation_rejects_changed_fixture_policy(self):
        original = collector._recompute_in_separate_process
        def mutate_then_recompute(**kwargs):
            (kwargs['input_dir'] / 'fixture.py').write_text('pass\n', encoding='utf-8')
            return original(**kwargs)
        fixture = "from pathlib import Path\nPath('/work/project/mod.py').write_text('value = 2\\n')\n"
        with mock.patch.object(collector, '_recompute_in_separate_process', side_effect=mutate_then_recompute):
            with self.assertRaisesRegex(collector.FixtureRefused, 'POLICY_MISMATCH'):
                collector.collect_fixture_worktree(self.repo, self.base, fixture)

    def test_separate_recomputation_rejects_rehashed_patch_that_changes_different_bytes(self):
        original = collector._recompute_in_separate_process
        def forge_then_recompute(**kwargs):
            effects = dict(kwargs['effects'])
            effects['patch.diff'] = effects['patch.diff'].replace(b'+value = 2', b'+value = 3')
            receipt = copy.deepcopy(kwargs['receipt'])
            receipt['effects']['patch.diff']['sha256'] = hashlib.sha256(effects['patch.diff']).hexdigest()
            receipt['effects']['patch.diff']['size'] = len(effects['patch.diff'])
            digest = hashlib.sha256(json.dumps(receipt, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            return original(**{**kwargs, 'effects': effects, 'receipt': receipt, 'receipt_sha': digest})
        fixture = "from pathlib import Path\nPath('/work/project/mod.py').write_text('value = 2\\n')\n"
        with mock.patch.object(collector, '_recompute_in_separate_process', side_effect=forge_then_recompute):
            with self.assertRaisesRegex(collector.FixtureRefused, 'PATCH_DOES_NOT_REPRODUCE_WORKTREE'):
                collector.collect_fixture_worktree(self.repo, self.base, fixture)

    def test_unknown_base_refuses_before_fixture_runs(self):
        fixture = "raise RuntimeError('fixture should not run')\n"
        with self.assertRaisesRegex(collector.FixtureRefused, 'BASE_COMMIT_UNAVAILABLE'):
            collector.collect_fixture_worktree(self.repo, 'f' * len(self.base), fixture)
        self.assertEqual((self.repo / 'mod.py').read_bytes(), b'value = 1\n')

    def test_actual_changes_during_host_collection_are_refused(self):
        original = snapshot.snapshot_project
        calls = 0
        def inject_real_write(path, **kwargs):
            nonlocal calls
            result = original(path, **kwargs)
            if Path(path).name == 'worktree':
                calls += 1
            if Path(path).name == 'worktree' and calls == 2:  # real host write after first post-exit snapshot
                (Path(path) / 'mod.py').write_text('value = 7\n', encoding='utf-8')
            return result
        fixture = "from pathlib import Path\nPath('/work/project/mod.py').write_text('value = 2\\n')\n"
        with mock.patch.object(snapshot, 'snapshot_project', side_effect=inject_real_write):
            with self.assertRaisesRegex(collector.FixtureRefused, 'WORKTREE_CHANGED_DURING_COLLECTION'):
                collector.collect_fixture_worktree(self.repo, self.base, fixture)

    def test_actual_git_metadata_is_not_mounted_into_fixture(self):
        fixture = '''from pathlib import Path
head = Path('/work/project/.git/HEAD')
try:
    head.write_text('0'*40 + '\\n')
except FileNotFoundError:
    pass
else:
    raise RuntimeError('git metadata was reachable')
Path('/work/project/mod.py').write_text('value = 2\\n')
'''
        result = collector.collect_fixture_worktree(self.repo, self.base, fixture)
        self.assertEqual(result['effect_bytes']['files/mod.py'], b'value = 2\n')
        self.assertEqual((self.repo / 'mod.py').read_bytes(), b'value = 1\n')
        self.assertEqual(subprocess.check_output(['git', '-C', str(self.repo), 'rev-parse', 'HEAD'], text=True).strip(), self.base)

    def test_worker_created_git_metadata_is_refused(self):
        fixture = "from pathlib import Path\nPath('/work/project/.git').mkdir()\n"
        with self.assertRaisesRegex(collector.FixtureRefused, 'WORKER_CREATED_GIT_METADATA'):
            collector.collect_fixture_worktree(self.repo, self.base, fixture)
        self.assertEqual((self.repo / 'mod.py').read_bytes(), b'value = 1\n')

    def test_file_mode_changes_are_not_silently_dropped(self):
        fixture = "import os\nos.chmod('/work/project/mod.py',0o755)\n"
        with self.assertRaisesRegex(collector.FixtureRefused, 'WORKTREE_MODE_CHANGED_UNSUPPORTED'):
            collector.collect_fixture_worktree(self.repo, self.base, fixture)

    def test_symlink_effect_is_refused(self):
        fixture = "import os\nos.unlink('/work/project/mod.py')\nos.symlink('/etc/passwd','/work/project/mod.py')\n"
        with self.assertRaisesRegex(collector.FixtureRefused, 'WORKTREE_SNAPSHOT_FAILED'):
            collector.collect_fixture_worktree(self.repo, self.base, fixture)

    def test_host_observes_worker_death_before_file_bytes_are_returned(self):
        fixture = '''import os,time
from pathlib import Path
p=Path('/work/project/mod.py')
p.write_text('value = 2\\n')
if os.fork()==0:
    os.setsid()
    time.sleep(3)
    p.write_text('value = 99\\n')
    os._exit(0)
time.sleep(.8)
'''
        helper = '''import base64,json,sys
from canonical.tools.isolated_worktree_fixture_collector_v1 import collect_fixture_worktree
r=collect_fixture_worktree(sys.argv[1],sys.argv[2],sys.argv[3])
print(json.dumps({'receipt':r['receipt'],'patch':base64.b64encode(r['patch_bytes']).decode(),
                  'file':base64.b64encode(r['effect_bytes']['files/mod.py']).decode()}))
'''
        proc = subprocess.Popen([sys.executable, '-c', helper, str(self.repo), self.base, fixture],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        seen = []
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                workers = []
                for pid in children(proc.pid):
                    try: parts = Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
                    except (FileNotFoundError, ProcessLookupError): continue
                    if len(parts)>2 and parts[1:3]==[b'-I',b'/input/fixture.py']:
                        ident = proc_identity(pid)
                        if ident: workers.append(ident)
                if len(workers) >= 2:
                    seen = workers
                    break
                if proc.poll() is not None: break
                time.sleep(.02)
            self.assertGreaterEqual(len(seen), 2, 'host did not observe both fixture processes')
            out, err = proc.communicate(timeout=15)
            self.assertEqual(proc.returncode, 0, err.decode(errors='replace'))
            self.assertFalse([pid for pid in seen if still_alive(pid)], 'worker survived collector return')
            result = json.loads(out)
            data, patch = base64.b64decode(result['file']), base64.b64decode(result['patch'])
            self.assertEqual(data, b'value = 2\n')
            self.assertEqual(result['receipt']['effects']['files/mod.py']['sha256'], hashlib.sha256(data).hexdigest())
            self.assertEqual(result['receipt']['effects']['patch.diff']['sha256'], hashlib.sha256(patch).hexdigest())
            self.assertIn(b'-value = 1\n+value = 2\n', patch)
            check = subprocess.run(['git', '-C', str(self.repo), 'apply', '--check', '-'], input=patch,
                                   capture_output=True)
            self.assertEqual(check.returncode, 0, check.stderr)
        finally:
            for pid, start in seen:
                if still_alive((pid, start)):
                    try: os.kill(pid, 9)
                    except ProcessLookupError: pass
            if proc.poll() is None: proc.kill()
            proc.communicate(timeout=5)


if __name__ == '__main__':
    unittest.main()
