"""Real output budgets on the existing owned test runner; no fake subprocesses."""
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time
import unittest

from canonical.runtime.bound_capabilities import python_test_guided_patch_search_v1 as runner
from canonical.runtime.bound_capabilities import python_repair_apply_verified_v1 as apply

FLOOD = "import os\nfor _ in range(150): os.write(1,b'x'*65536)\n"


@unittest.skipUnless(os.name == 'posix', 'POSIX bounded diagnostic capture')
class BoundedTestCaptureReuseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix='brain_bounded_capture_')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def invoke(self, code, timeout=3):
        return runner._run_tests(self.root, [sys.executable, '-c', code], timeout)

    def test_stdout_overflow_cannot_return_a_passing_verdict(self):
        with self.assertRaisesRegex(runner.PatchSearchError, 'TEST_OUTPUT_LIMIT_EXCEEDED'):
            self.invoke(FLOOD)

    def test_budget_is_aggregate_across_stdout_and_stderr(self):
        code = "import os\nfor _ in range(80):\n os.write(1,b'o'*65536)\n os.write(2,b'e'*65536)\n"
        with self.assertRaisesRegex(runner.PatchSearchError, 'TEST_OUTPUT_LIMIT_EXCEEDED'):
            self.invoke(code)

    def test_exited_parent_does_not_wait_for_inherited_pipe_child(self):
        for status in (0, 7):
            with self.subTest(status=status):
                marker = 'late_' + str(status)
                child = ("import time;from pathlib import Path;time.sleep(1.3);"
                         f"Path({marker!r}).write_text('escaped')")
                parent = ("import subprocess,sys;"
                          f"subprocess.Popen([sys.executable,'-c',{child!r}]);"
                          f"print('finished',flush=True);sys.exit({status})")
                result = self.invoke(parent)
                self.assertEqual(result['returncode'], status)
                self.assertFalse(result['timed_out'])
                self.assertIn('finished', result['stdout'])
                self.assertLess(result['elapsed_s'], 1)
                time.sleep(1.4)
                self.assertFalse((self.root / marker).exists())

    def test_overflow_cleanup_stops_background_writer(self):
        child = ("import time;from pathlib import Path;time.sleep(.5);"
                 "Path('late_overflow').write_text('escaped')")
        code = ("import subprocess,sys\n"
                f"subprocess.Popen([sys.executable,'-c',{child!r}])\n" + FLOOD)
        with self.assertRaisesRegex(runner.PatchSearchError, 'TEST_OUTPUT_LIMIT_EXCEEDED'):
            self.invoke(code)
        time.sleep(.7)
        self.assertFalse((self.root / 'late_overflow').exists())

    def test_below_budget_keeps_output_newlines_unicode_and_failure(self):
        code = ("import os,sys;os.write(1,b'x'*1048576);"
                "os.write(1,'résumé'.encode()+b'\\r\\n');"
                "os.write(2,b'bad:\\xff\\r\\n');sys.exit(9)")
        result = self.invoke(code)
        self.assertEqual(result['returncode'], 9)
        self.assertFalse(result['timed_out'])
        self.assertEqual(result['stdout'], 'x'*1048576 + 'résumé\n')
        self.assertEqual(result['stderr'], 'bad:\ufffd\n')

    def test_timeout_still_retains_partial_diagnostics(self):
        result = self.invoke("import os,time;os.write(2,b'partial:\\xff');time.sleep(5)", .2)
        self.assertIsNone(result['returncode'])
        self.assertTrue(result['timed_out'])
        self.assertIn('partial:\ufffd', result['stderr'])

    def test_candidate_overflow_restores_original_source_and_tests(self):
        source = self.root / 'm.py'
        original = b'def f(x):\n    return x < 3\n'
        source.write_bytes(original)
        tests = self.root / 'test_m.py'
        tests.write_text("from m import f\nassert f(3)\n" + FLOOD)
        before_tests = tests.read_bytes()
        with self.assertRaisesRegex(runner.PatchSearchError, 'TEST_OUTPUT_LIMIT_EXCEEDED'):
            runner.run({'source_path': 'm.py', 'test_paths': ['test_m.py'],
                        'test_argv': [sys.executable, str(tests)],
                        'output_path': 'search.json', 'max_candidates': 30,
                        'timeout_s': 3}, self.root)
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual(tests.read_bytes(), before_tests)
        self.assertFalse((self.root / 'search.json').exists())

    def test_native_apply_gate_overflow_cannot_report_success(self):
        source = self.root / 'm.py'
        original = b'def f(x): return x <= 3\n'
        source.write_bytes(original)
        tests = self.root / 'test_m.py'
        tests.write_text("from m import f\nassert f(3)\n" + FLOOD)
        before_tests = tests.read_bytes()
        # The adapter loads the same runner by path, with its own error class.
        with self.assertRaisesRegex(RuntimeError, 'TEST_OUTPUT_LIMIT_EXCEEDED'):
            apply.run({'source_root': '.', 'test_paths': ['test_m.py'],
                       'test_argv': [sys.executable, str(tests)],
                       'output_path': 'apply.json', 'timeout_s': 3}, self.root)
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual(tests.read_bytes(), before_tests)
        self.assertFalse((self.root / 'apply.json').exists())


if __name__ == '__main__':
    unittest.main()
