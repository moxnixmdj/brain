"""Real apply-gate processes must reuse the existing owned test lifecycle."""
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest

from canonical.runtime.bound_capabilities import python_repair_apply_verified_v1 as apply


class RepairDeliveryProcessCleanupReuseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix='brain_apply_cleanup_')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    @unittest.skipUnless(os.name == 'posix', 'owned POSIX process groups')
    def test_completion_cleans_background_descendants_on_success_and_failure(self):
        for status in (0, 7):
            with self.subTest(status=status):
                marker = 'late_' + str(status)
                child = ("import time;from pathlib import Path;time.sleep(.5);"
                         f"Path({marker!r}).write_text('escaped')")
                parent = ("import subprocess,sys;"
                          f"subprocess.Popen([sys.executable,'-c',{child!r}],"
                          "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);"
                          f"print('finished');sys.exit({status})")
                rc, tail = apply._run_test([sys.executable, '-c', parent], self.root, 2)
                self.assertEqual(rc, status)
                self.assertIn(b'finished', tail)
                time.sleep(.65)
                self.assertFalse((self.root / marker).exists())

    @unittest.skipUnless(os.name == 'posix', 'owned POSIX process groups')
    def test_timeout_cleans_descendant_and_retains_timeout_verdict(self):
        child = ("import time;from pathlib import Path;time.sleep(.6);"
                 "Path('late_timeout').write_text('escaped')")
        parent = ("import subprocess,sys,time;"
                  f"subprocess.Popen([sys.executable,'-c',{child!r}]);"
                  "print('started',flush=True);time.sleep(5)")
        rc, tail = apply._run_test([sys.executable, '-c', parent], self.root, .2)
        self.assertIsNone(rc)
        self.assertIn(b'TIMEOUT', tail)
        time.sleep(.75)
        self.assertFalse((self.root / 'late_timeout').exists())

    @unittest.skipUnless(os.name == 'posix', 'owned POSIX process groups')
    def test_actual_already_correct_apply_gate_leaves_no_background_writer(self):
        source = self.root / 'm.py'
        body = 'def f(x): return x <= 3\n'
        source.write_text(body)
        child = ("import time;from pathlib import Path;time.sleep(.5);"
                 "Path('late_apply').write_text('escaped')")
        tests = self.root / 'test_all.py'
        tests.write_text("from m import f\nassert f(3)\n"
                         "import subprocess,sys\n"
                         f"subprocess.Popen([sys.executable,'-c',{child!r}],"
                         "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\n")
        result = apply.run({'source_root': '.', 'test_paths': ['test_all.py'],
                            'test_argv': [sys.executable, str(tests)],
                            'output_path': 'report.json', 'timeout_s': 2}, self.root)
        self.assertTrue(result['pass'], result.get('status'))
        self.assertEqual(result['status'], 'PASS__STATED_TEST_ALREADY_PASSES_NOTHING_TO_REPAIR')
        self.assertFalse(result['applied'])
        time.sleep(.65)
        self.assertFalse((self.root / 'late_apply').exists())
        self.assertEqual(source.read_text(), body)

    def test_returncode_and_byte_diagnostics_contract_is_preserved(self):
        rc, tail = apply._run_test([sys.executable, '-c',
                                   "import sys;print('out');print('err',file=sys.stderr);sys.exit(9)"],
                                  self.root, 2)
        self.assertEqual(rc, 9)
        self.assertIsInstance(tail, bytes)
        self.assertIn(b'out', tail)
        self.assertIn(b'err', tail)

    def test_launch_error_is_not_reported_as_a_passing_test(self):
        rc, tail = apply._run_test([sys.executable, '-c', 'pass'],
                                  self.root / 'missing_directory', 2)
        self.assertIsNone(rc)
        self.assertIsInstance(tail, bytes)
        self.assertTrue(tail)


if __name__ == '__main__':
    unittest.main()
