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
        self.assertFalse(result['publication_authority'])
        for name, data in result['effect_bytes'].items():
            self.assertEqual(result['receipt']['effects'][name]['sha256'], hashlib.sha256(data).hexdigest())

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

    def test_unknown_base_refuses_before_fixture_runs(self):
        fixture = "raise RuntimeError('fixture should not run')\n"
        with self.assertRaisesRegex(collector.FixtureRefused, 'BASE_COMMIT_UNAVAILABLE'):
            collector.collect_fixture_worktree(self.repo, 'f' * len(self.base), fixture)
        self.assertEqual((self.repo / 'mod.py').read_bytes(), b'value = 1\n')

    def test_actual_changes_during_host_collection_are_refused(self):
        original = snapshot.snapshot_project
        calls = 0
        def inject_real_write(path):
            nonlocal calls
            result = original(path)
            if Path(path).name == 'worktree':
                calls += 1
            if Path(path).name == 'worktree' and calls == 2:  # real host write after first post-exit snapshot
                (Path(path) / 'mod.py').write_text('value = 7\n', encoding='utf-8')
            return result
        fixture = "from pathlib import Path\nPath('/work/project/mod.py').write_text('value = 2\\n')\n"
        with mock.patch.object(snapshot, 'snapshot_project', side_effect=inject_real_write):
            with self.assertRaisesRegex(collector.FixtureRefused, 'WORKTREE_CHANGED_DURING_COLLECTION'):
                collector.collect_fixture_worktree(self.repo, self.base, fixture)

    def test_worker_cannot_change_git_metadata_and_keep_a_receipt(self):
        fixture = "from pathlib import Path\nPath('/work/project/.git/HEAD').write_text('0'*40 + '\\n')\n"
        with self.assertRaisesRegex(collector.FixtureRefused, 'GIT_METADATA_CHANGED'):
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
