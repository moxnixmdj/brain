"""A real passing suite must not certify source it changed after publication."""
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime.bound_capabilities import python_repair_apply_verified_v1 as apply

BROKEN = 'def f(x):\n    return x < 3\n'
FIXED = 'def f(x):\n    return x <= 3\n'


@unittest.skipUnless(os.name == 'posix', 'POSIX inode/mode publication observation')
class DeliveryPostVerificationReadbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix='brain_delivery_readback_')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'm.py'
        self.source.write_text(BROKEN)
        self.source.chmod(0o751)
        (self.root / 'initial_inode.txt').write_text(str(self.source.stat().st_ino))
        self.victim = self.root / 'user_data.txt'
        self.victim.write_bytes(b'user data must survive')
        self.suite = self.root / 'test_m.py'

    def invoke(self, mutation):
        # Actual test side effect, triggered by the real publication's inode
        # change. Search trials keep the original inode. No runner is mocked.
        self.suite.write_text('from pathlib import Path\nimport os,unittest\nfrom m import f\n'
                              'class T(unittest.TestCase):\n def test_fix(self):\n'
                              '  assert f(3)\n  assert f(2)\n  assert not f(4)\n'
                              "  p=Path('m.py')\n"
                              "  if p.stat().st_ino!=int(Path('initial_inode.txt').read_text()):\n"
                              + ''.join('   '+line+'\n' for line in mutation.splitlines()))
        before = self.suite.read_bytes()
        result = apply.run({'source_root': '.', 'output_path': 'report.json',
                            'timeout_s': 3, 'mutations_per_file': 12,
                            'max_pair_candidates': 100}, self.root)
        self.assertEqual(self.suite.read_bytes(), before)
        self.assertEqual(self.victim.read_bytes(), b'user data must survive')
        self.assertEqual(list(self.root.glob('*.brain_apply_tmp.*')), [])
        return result

    def assert_refused_and_restored(self, mutation):
        result = self.invoke(mutation)
        self.assertFalse(result['pass'], 'exit0 must not certify altered delivery')
        self.assertFalse(result['applied'])
        self.assertFalse(result['output_verified'])
        self.assertTrue(result['source_restored'])
        self.assertEqual(result['status'], 'FAIL_CLOSED__APPLIED_SOURCE_CHANGED_DURING_VERIFICATION')
        self.assertEqual(result['post_apply_test_returncode'], 0)
        self.assertEqual(result['files_written'], [])
        self.assertEqual(result['changed_source_paths'], ['m.py'])
        self.assertFalse(self.source.is_symlink())
        self.assertEqual(self.source.read_text(), BROKEN)
        self.assertEqual(stat.S_IMODE(self.source.stat().st_mode), 0o751)
        self.assertFalse(self.source.samefile(self.victim))
        report = json.loads((self.root / 'report.json').read_bytes())
        self.assertEqual(report['status'], result['status'])
        fresh = subprocess.run([sys.executable, '-B', '-m', 'unittest', 'test_m'], cwd=self.root,
                               capture_output=True, timeout=5)
        self.assertNotEqual(fresh.returncode, 0, 'original broken source was really restored')

    def test_exit0_cannot_certify_source_rewritten_after_its_assertions(self):
        self.assert_refused_and_restored("p.write_text('def f(x): return False\\n')")

    def test_deleted_source_is_restored_with_original_permissions(self):
        self.assert_refused_and_restored('p.unlink()')

    def test_source_symlink_replacement_does_not_redirect_rollback(self):
        self.assert_refused_and_restored("p.unlink()\np.symlink_to('user_data.txt')")

    def test_source_hardlink_replacement_does_not_clobber_unrelated_data(self):
        self.assert_refused_and_restored("p.unlink()\nos.link('user_data.txt',p)")

    def test_fifo_source_replacement_is_refused_without_blocking_readback(self):
        self.assert_refused_and_restored('p.unlink()\nos.mkfifo(p)')

    def test_oversized_source_replacement_is_refused_before_content_read(self):
        self.assert_refused_and_restored("p.write_bytes(b'x'*2000000)")

    def test_permission_mutation_is_not_silently_certified(self):
        self.assert_refused_and_restored('p.chmod(0o600)')

    def test_unrelated_generated_artifact_does_not_invalidate_real_delivery(self):
        result = self.invoke("Path('generated.txt').write_text('ordinary test artifact')")
        self.assertTrue(result['pass'], result)
        self.assertTrue(result['applied'])
        self.assertEqual(self.source.read_text(), FIXED)
        self.assertEqual(stat.S_IMODE(self.source.stat().st_mode), 0o751)
        self.assertEqual((self.root / 'generated.txt').read_text(), 'ordinary test artifact')


if __name__ == '__main__':
    unittest.main()
