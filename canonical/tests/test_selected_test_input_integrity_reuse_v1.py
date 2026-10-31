"""Actual execution must not certify repair against changed selected tests."""
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
REPLACEMENT = 'import unittest\nclass T(unittest.TestCase):\n def test_fake(self): self.assertTrue(True)\n'


@unittest.skipUnless(os.name == 'posix', 'POSIX inode/mode publication observation')
class SelectedTestInputIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix='brain_test_input_')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'm.py'
        self.source.write_text(BROKEN)
        self.source.chmod(0o751)
        (self.root / 'original_inode.txt').write_text(str(self.source.stat().st_ino))
        self.suite = self.root / 'test_m.py'
        self.victim = self.root / 'user_data.txt'
        self.victim.write_bytes(b'user data, not a test')
        self.report = self.root / 'report.json'
        self.report.write_bytes(b'prior report must survive')

    def prepare(self, mutation, phase='final', fixed=False):
        if fixed:
            self.source.write_text(FIXED)
        if phase == 'baseline_failure':
            body = mutation + "\nraise RuntimeError('real baseline failure')"
        else:
            body = 'assert f(3)\nassert f(2)\nassert not f(4)\n'
            condition = ('p.stat().st_ino!=old' if phase == 'final' else
                         'p.stat().st_ino==old' if phase == 'search' else 'True')
            body += 'if ' + condition + ':\n' + ''.join(' '+x+'\n' for x in mutation.splitlines())
        self.suite.write_text('from pathlib import Path\nimport os,unittest\nfrom m import f\n'
                              'class T(unittest.TestCase):\n def test_fix(self):\n'
                              "  p=Path('m.py'); t=Path(__file__)\n"
                              "  old=int(Path('original_inode.txt').read_text())\n"
                              + ''.join('  '+line+'\n' for line in body.splitlines()))
        self.suite.chmod(0o750)
        return self.suite.read_bytes()

    def invoke(self):
        return apply.run({'source_root': '.', 'output_path': 'report.json',
                          'timeout_s': 3, 'mutations_per_file': 12,
                          'max_pair_candidates': 100}, self.root)

    def assert_refusal(self, mutation, phase='final', fixed=False):
        original = self.prepare(mutation, phase, fixed)
        with self.assertRaisesRegex(apply.RepairApplyError, '^TEST_INPUT_CHANGED:test_m.py$'):
            self.invoke()
        self.assertFalse(self.suite.is_symlink())
        self.assertEqual(self.suite.read_bytes(), original)
        self.assertEqual(stat.S_IMODE(self.suite.stat().st_mode), 0o750)
        self.assertEqual(self.source.read_text(), FIXED if fixed else BROKEN)
        self.assertEqual(stat.S_IMODE(self.source.stat().st_mode), 0o751)
        self.assertEqual(self.victim.read_bytes(), b'user data, not a test')
        self.assertEqual(self.report.read_bytes(), b'prior report must survive')
        self.assertEqual(list(self.root.rglob('*.brain_apply_tmp.*')), [])
        self.assertEqual(list((self.root / '__pycache__').glob('test_m.*.pyc')), [])

    def test_already_passing_baseline_cannot_rewrite_its_test_and_claim_success(self):
        self.assert_refusal(f't.write_text({REPLACEMENT!r})', phase='baseline', fixed=True)

    def test_real_search_trial_cannot_replace_selected_test_oracle(self):
        self.assert_refusal(f't.write_text({REPLACEMENT!r})', phase='search')

    def test_final_test_cannot_rewrite_itself_and_authorize_delivery(self):
        self.assert_refusal(f't.write_text({REPLACEMENT!r})')

    def test_final_test_deletion_is_restored_with_original_permissions(self):
        self.assert_refusal('t.unlink()')

    def test_final_test_symlink_cannot_redirect_input_restoration(self):
        self.assert_refusal("t.unlink()\nt.symlink_to('user_data.txt')")

    def test_final_test_hardlink_cannot_clobber_unrelated_data(self):
        self.assert_refusal("t.unlink()\nos.link('user_data.txt',t)")

    def test_final_test_permission_changes_are_restored(self):
        self.assert_refusal('t.chmod(0o600)')

    def test_final_test_fifo_is_restored_without_blocking_readback(self):
        self.assert_refusal('t.unlink()\nos.mkfifo(t)')

    def test_real_runner_overflow_still_restores_test_and_source(self):
        self.assert_refusal(f't.write_text({REPLACEMENT!r})\n'
                            "for _ in range(150): os.write(1,b'x'*65536)")

    def test_baseline_failure_still_restores_a_corrupted_selected_test(self):
        self.assert_refusal(f't.write_text({REPLACEMENT!r})', phase='baseline_failure')

    def test_same_length_source_restoration_invalidates_candidate_bytecode(self):
        original = 'def f(x):\n    return x + 2\n'
        self.source.write_text(original)
        self.suite.write_text('from pathlib import Path\nimport unittest\nfrom m import f\n'
                              'class T(unittest.TestCase):\n def test_fix(self):\n'
                              '  assert f(0)==3\n  assert f(1)==4\n  assert f(100)==103\n'
                              "  if Path('m.py').stat().st_ino!=int(Path('original_inode.txt').read_text()):\n"
                              + f'   Path(__file__).write_text({REPLACEMENT!r})\n')
        self.suite.chmod(0o750)
        before = self.suite.read_bytes()
        with self.assertRaisesRegex(apply.RepairApplyError, '^TEST_INPUT_CHANGED:test_m.py$'):
            apply.run({'source_root': '.', 'output_path': 'report.json',
                       'timeout_s': 3, 'mutations_per_file': 24,
                       'max_pair_candidates': 100}, self.root)
        self.assertEqual(self.source.read_text(), original)
        self.assertEqual(self.suite.read_bytes(), before)
        self.assertEqual(list((self.root / '__pycache__').glob('m.*.pyc')), [])
        fresh = subprocess.run([sys.executable, '-B', '-c', 'from m import f;assert f(0)==2'],
                               cwd=self.root, capture_output=True, timeout=5)
        self.assertEqual(fresh.returncode, 0, fresh.stderr)

    def test_unrelated_artifact_is_not_a_selected_test_mutation(self):
        original = self.prepare("Path('generated.txt').write_text('permitted artifact')")
        result = self.invoke()
        self.assertTrue(result['pass'], result)
        self.assertTrue(result['applied'])
        self.assertEqual(self.suite.read_bytes(), original)
        self.assertEqual(self.source.read_text(), FIXED)
        self.assertEqual((self.root / 'generated.txt').read_text(), 'permitted artifact')


if __name__ == '__main__':
    unittest.main()
