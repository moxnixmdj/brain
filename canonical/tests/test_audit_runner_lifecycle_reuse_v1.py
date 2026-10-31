"""The corpus report reuses bounded execution without hiding red files."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import time
import unittest

from canonical.runtime.bound_capabilities import python_test_audit as audit

GREEN = ('import unittest,os\nos.write(2,b\'log:\\xff\\n\')\n'
         'class T(unittest.TestCase):\n def test_one(self): self.assertTrue(True)\n')


@unittest.skipUnless(os.name == 'posix', 'owned POSIX processes and diagnostic cap')
class AuditRunnerLifecycleReuseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix='brain_audit_lifecycle_')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def invoke(self, timeout=2):
        result = audit.run({'source_root': '.', 'output_path': 'report.json',
                            'timeout_s': timeout}, self.root)
        report = json.loads((self.root / 'report.json').read_bytes())
        return result, report

    def test_noisy_file_is_red_but_audit_continues_and_reinspects_report(self):
        loud = self.root / 'test_a_loud.py'
        loud.write_text("import os\nfor _ in range(150): os.write(1,b'x'*65536)\n"
                        "os.write(1,b'\\n')\n" + GREEN)
        (self.root / 'test_z_green.py').write_text(GREEN)
        original = loud.read_bytes()
        result, report = self.invoke()
        self.assertTrue(result['report_verified'])
        self.assertFalse(result['output_verified'])
        self.assertEqual(result['file_count'], 2)
        self.assertEqual(result['test_count'], 1)
        self.assertEqual(result['passed_count'], 1)
        self.assertEqual(result['crashed_count'], 1)
        self.assertEqual(result['timed_out_count'], 0)
        self.assertEqual(result['pass_rate'], .5)
        red, green = report['records']
        self.assertNotEqual(red['exit_code'], 0)
        self.assertTrue(red['crashed'])
        self.assertIn('TEST_OUTPUT_LIMIT_EXCEEDED', red['failure_tail'])
        self.assertEqual(green['exit_code'], 0)
        self.assertEqual(loud.read_bytes(), original)

    def test_successful_audit_cleans_background_writer(self):
        child = ("import time;from pathlib import Path;time.sleep(.5);"
                 "Path('late_success').write_text('escaped')")
        (self.root / 'test_green.py').write_text(
            "import subprocess,sys\n"
            f"subprocess.Popen([sys.executable,'-c',{child!r}],"
            "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\n" + GREEN)
        result, report = self.invoke()
        self.assertTrue(result['report_verified'])
        self.assertTrue(result['output_verified'])
        self.assertEqual(report['totals']['tests'], 1)
        time.sleep(.7)
        self.assertFalse((self.root / 'late_success').exists())

    def test_timeout_cleans_descendant_retains_diagnostics_and_continues(self):
        child = ("import time;from pathlib import Path;time.sleep(1.4);"
                 "Path('late_timeout').write_text('escaped')")
        (self.root / 'test_a_hang.py').write_text(
            "import subprocess,sys,time\n"
            f"subprocess.Popen([sys.executable,'-c',{child!r}],"
            "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\n"
            "print('before_timeout',flush=True)\ntime.sleep(5)\n")
        (self.root / 'test_z_green.py').write_text(GREEN)
        result, report = self.invoke(timeout=1)
        self.assertTrue(result['report_verified'])
        self.assertFalse(result['output_verified'])
        self.assertEqual(result['file_count'], 2)
        self.assertEqual(result['timed_out_count'], 1)
        self.assertEqual(result['passed_count'], 1)
        self.assertEqual(result['crashed_count'], 1)
        self.assertIn('before_timeout', report['records'][0]['failure_tail'])
        self.assertIn('TIMED_OUT_AFTER_1s', report['records'][0]['failure_tail'])
        time.sleep(.7)
        self.assertFalse((self.root / 'late_timeout').exists())

    def test_report_reinspection_rejects_erasing_a_real_red_file(self):
        (self.root / 'test_red.py').write_text(GREEN.replace('assertTrue(True)', 'assertTrue(False)'))
        result, report = self.invoke()
        self.assertTrue(result['report_verified'])
        self.assertFalse(result['output_verified'])
        records, totals = report['records'], dict(report['totals'])
        forged = json.loads(json.dumps(report))
        forged['totals']['failed'] = 0
        self.assertFalse(audit._report_is_consistent(json.dumps(forged).encode(), records, totals))


if __name__ == '__main__':
    unittest.main()
