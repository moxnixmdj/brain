"""Actual copied-repository measurements reuse existing execution/identity guards."""
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import time
import unittest

from canonical.runtime.bound_capabilities import python_repository_acceptance_measurement_v1 as measure
from canonical.runtime.write_authority_v1 import WriteAuthorityViolation

GREEN = ('import unittest,os\nfrom m import f\n'
         'class T(unittest.TestCase):\n'
         ' def test_f(self):\n'
         '  self.assertTrue(f())\n'
         '  self.assertEqual(os.environ["PYTHONHASHSEED"],"0")\n'
         '  self.assertEqual(os.environ["PYTHONDONTWRITEBYTECODE"],"1")\n')


class RepositoryMeasurementBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix='brain_measure_boundary_')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root / 'project'
        self.project.mkdir()
        self.source = self.project / 'm.py'
        self.source.write_text('def f():\n    return True\n')
        self.test = self.project / 'test_m.py'
        self.test.write_text(GREEN)
        self.original = self.source.read_bytes()

    def invoke(self, **extra):
        return measure.run({'source_root': 'project', 'output_path': 'report.json',
                            'timeout_s': 2, **extra}, self.root)

    def spawn(self, marker, delay):
        child = (f'import time;from pathlib import Path;time.sleep({delay});'
                 f'Path({str(self.root / marker)!r}).write_text("escaped")')
        return ('import subprocess,sys\n'
                f'subprocess.Popen([sys.executable,"-c",{child!r}],'
                'stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\n')

    def assert_receipt(self, result):
        raw = (self.root / result['output_path']).read_bytes()
        self.assertEqual(result['output_sha256'], hashlib.sha256(raw).hexdigest())
        payload = json.loads(raw)
        digest = payload.pop('receipt_payload_sha256')
        self.assertEqual(digest, measure._sha_obj(payload))
        self.assertTrue(result['pass'])  # measurement completed, not task accepted
        self.assertTrue(result['output_verified'])
        self.assertTrue(result['measurements']['repository_source_unchanged'])
        self.assertEqual(self.source.read_bytes(), self.original)

    @unittest.skipUnless(os.name == 'posix', 'owned POSIX descendants')
    def test_success_cleans_descendant_and_preserves_measurement_contract(self):
        self.test.write_text(self.spawn('late_success', .5) + GREEN)
        result = self.invoke()
        self.assert_receipt(result)
        self.assertTrue(result['measurements']['tests_pass'])
        self.assertEqual(result['measurements']['test_count'], 1)
        self.assertEqual(result['measurement_spec']['test_paths_source'], 'discovered_under_source_root')
        time.sleep(.7)
        self.assertFalse((self.root / 'late_success').exists())

    @unittest.skipUnless(os.name == 'posix', 'owned POSIX descendants')
    def test_timeout_retains_diagnostics_as_red_measurement_and_cleans_descendant(self):
        self.test.write_text(self.spawn('late_timeout', 1.4) +
                             "import time\nprint('before_timeout',flush=True)\ntime.sleep(5)\n")
        try:
            result = self.invoke(timeout_s=1)
        finally:
            time.sleep(.7)  # let the pre-fix finite late writer settle even on error
        self.assert_receipt(result)
        self.assertFalse(result['measurements']['tests_pass'])
        self.assertEqual(result['measurements']['test_returncode'], 124)
        self.assertEqual(result['measurements']['test_count'], 0)
        self.assertTrue(result['test_evidence']['timed_out'])
        self.assertEqual(result['test_evidence']['stdout_sha256'],
                         hashlib.sha256(b'before_timeout\n').hexdigest())
        self.assertFalse((self.root / 'late_timeout').exists())

    def test_invalid_utf8_is_normalized_without_losing_real_test_verdict(self):
        self.test.write_text("import os\nos.write(1,b'\\xff\\r\\n')\n" + GREEN)
        result = self.invoke()
        self.assert_receipt(result)
        self.assertTrue(result['measurements']['tests_pass'])
        self.assertEqual(result['measurements']['test_count'], 1)
        self.assertEqual(result['test_evidence']['stdout_sha256'],
                         hashlib.sha256('\ufffd\n'.encode()).hexdigest())

    @unittest.skipUnless(os.name == 'posix', 'bounded POSIX diagnostic capture')
    def test_overflow_is_typed_cleans_descendant_and_preserves_prior_report(self):
        self.test.write_text(self.spawn('late_overflow', .5) +
                             "import os\nfor _ in range(150): os.write(1,b'x'*65536)\n" + GREEN)
        report = self.root / 'report.json'
        report.write_bytes(b'previous-report')
        try:
            with self.assertRaisesRegex(measure.MeasurementError, '^TEST_OUTPUT_LIMIT_EXCEEDED$'):
                self.invoke()
        finally:
            time.sleep(.7)
        self.assertEqual(report.read_bytes(), b'previous-report')
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertFalse((self.root / 'late_overflow').exists())

    def assert_alias_refused(self, output, protected):
        # An external sentinel tells us whether the copied test was executed.
        self.test.write_text(f'from pathlib import Path\nPath({str(self.root / "executed")!r}).touch()\n' + GREEN)
        original = protected.read_bytes()
        with self.assertRaisesRegex(WriteAuthorityViolation, '^REPORT_OVERWRITES_INPUT:'):
            self.invoke(output_path=str(output.relative_to(self.root)))
        self.assertEqual(protected.read_bytes(), original)
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertFalse((self.root / 'executed').exists())

    def test_direct_source_report_alias_refuses_before_execution(self):
        self.assert_alias_refused(self.source, self.source)

    def test_report_hardlink_to_source_refuses_before_execution(self):
        alias = self.root / 'report.json'
        os.link(self.source, alias)
        self.assert_alias_refused(alias, self.source)

    def test_report_hardlink_to_measured_data_refuses_before_execution(self):
        data = self.project / 'settings.json'
        data.write_text('{"required":true}')
        alias = self.root / 'report.json'
        os.link(data, alias)
        self.assert_alias_refused(alias, data)


if __name__ == '__main__':
    unittest.main()
