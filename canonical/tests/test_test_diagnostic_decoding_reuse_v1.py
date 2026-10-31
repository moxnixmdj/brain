"""Real binary tool diagnostics must not change test execution verdicts."""
import sys
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime.bound_capabilities import python_repair_apply_verified_v1 as apply
from canonical.runtime.bound_capabilities import python_test_audit as audit


class TestDiagnosticDecodingReuse(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix='brain_binary_diagnostics_')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def invoke(self, code, timeout=2):
        return apply._REPAIR._PATCH._run_tests(self.root, [sys.executable, '-c', code], timeout)

    def test_binary_stdout_and_stderr_preserve_success(self):
        result = self.invoke("import os;os.write(1,b'out:\\xff');os.write(2,b'err:\\xfe')")
        self.assertEqual(result['returncode'], 0)
        self.assertFalse(result['timed_out'])
        self.assertIn('out:\ufffd', result['stdout'])
        self.assertIn('err:\ufffd', result['stderr'])

    def test_binary_diagnostics_cannot_turn_failure_into_success(self):
        result = self.invoke("import os,sys;os.write(1,b'bad:\\xff');sys.exit(9)")
        self.assertEqual(result['returncode'], 9)
        self.assertFalse(result['timed_out'])
        self.assertIn('bad:', result['stdout'])

    def test_timeout_with_binary_partial_diagnostics_keeps_timeout_verdict(self):
        result = self.invoke("import os,time;os.write(2,b'partial:\\xfe');time.sleep(5)", .2)
        self.assertIsNone(result['returncode'])
        self.assertTrue(result['timed_out'])
        self.assertIn('partial:', result['stderr'])

    def test_valid_utf8_is_preserved(self):
        text = 'résumé — δοκιμή — اختبار'
        result = self.invoke(f'import os;os.write(1,{text.encode("utf-8")!r})')
        self.assertEqual(result['returncode'], 0)
        self.assertEqual(result['stdout'], text)

    def test_corpus_audit_records_real_pass_and_failure_despite_binary_logs(self):
        for name, verdict in [('pass', 'True'), ('fail', 'False')]:
            (self.root / ('test_' + name + '.py')).write_text(
                "import unittest,os\nos.write(2,b'log:\\xff\\n')\n"
                "class T(unittest.TestCase):\n"
                f" def test_one(self): self.assertTrue({verdict})\n")
        result = audit.run({'source_root': '.', 'output_path': 'audit.json'}, self.root)
        self.assertTrue(result['report_verified'])
        self.assertFalse(result['output_verified'])
        self.assertEqual(result['test_count'], 2)
        self.assertEqual(result['passed_count'], 1)
        self.assertEqual(result['failed_count'], 1)
        self.assertEqual(result['crashed_count'], 0)
        report = json.loads((self.root / 'audit.json').read_text())
        red = next(row for row in report['records'] if row['exit_code'] != 0)
        self.assertIn('log:', red['failure_tail'])
        self.assertIn('\ufffd', red['failure_tail'])

    def test_native_repair_persists_fix_despite_binary_test_diagnostics(self):
        source = self.root / 'm.py'
        original = 'def f(x): return x < 3\n'
        source.write_text(original)
        tests = self.root / 'test_all.py'
        tests.write_text("import os\nos.write(1,b'log:\\xff\\n')\nfrom m import f\nassert f(3)\n")
        before_tests = tests.read_bytes()
        result = apply.run({'source_root': '.', 'test_paths': ['test_all.py'],
                            'test_argv': [sys.executable, str(tests)],
                            'output_path': 'report.json', 'timeout_s': 3}, self.root)
        self.assertTrue(result['pass'], result.get('status'))
        self.assertTrue(result['applied'])
        self.assertNotEqual(source.read_text(), original)
        self.assertEqual(tests.read_bytes(), before_tests)
        code, diagnostics = apply._run_test([sys.executable, str(tests)], self.root, 2)
        self.assertEqual(code, 0)
        self.assertIn(b'log:', diagnostics)


if __name__ == '__main__':
    unittest.main()
