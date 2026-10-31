"""Trace adapters reuse the existing test runner without losing inner test truth."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import time
import unittest

from canonical.runtime.bound_capabilities import python_dynamic_fault_localizer_v1 as localizer
from canonical.runtime.bound_capabilities import python_interprocedural_value_provenance_v1 as provenance


class TraceLifecycleControls:
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix='brain_trace_lifecycle_')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'm.py'
        self.source.write_text('def f():\n    return False\n')
        self.tests = self.root / 'test_m.py'

    def trace(self, timeout=2):
        env = self.tool._source_env(self.source, self.tests)
        if self.tool is provenance:
            return self.tool._trace_one(self.root, self.tests, timeout, 3000, 128, env)
        return self.tool._trace_one(self.root, self.tests, timeout, 3000, env)

    def test_public_trace_cleans_background_writer_and_keeps_failing_evidence(self):
        child = ("import time;from pathlib import Path;time.sleep(.5);"
                 "Path('late_success').write_text('escaped')")
        self.tests.write_text("import subprocess,sys\n"
                              f"subprocess.Popen([sys.executable,'-c',{child!r}],"
                              "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\n"
                              "from m import f\nassert f()\n")
        original_source, original_tests = self.source.read_bytes(), self.tests.read_bytes()
        result = self.tool.run({'source_root': '.', 'test_paths': ['test_m.py'],
                                'output_path': 'trace.json', 'timeout_s': 2,
                                'max_trace_events': 3000}, self.root)
        self.assertTrue(result['pass'])
        self.assertEqual(result['failing_test_count'], 1)
        self.assertFalse(result['test_traces'][0]['pass'])
        self.assertTrue((self.root / 'trace.json').is_file())
        time.sleep(.7)
        self.assertFalse((self.root / 'late_success').exists())
        self.assertEqual(self.source.read_bytes(), original_source)
        self.assertEqual(self.tests.read_bytes(), original_tests)

    def test_timeout_preserves_typed_error_and_cleans_descendant(self):
        child = ("import time;from pathlib import Path;time.sleep(.5);"
                 "Path('late_timeout').write_text('escaped')")
        self.tests.write_text("import subprocess,sys,time\n"
                              f"subprocess.Popen([sys.executable,'-c',{child!r}],"
                              "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\n"
                              "time.sleep(5)\n")
        with self.assertRaisesRegex(self.error, 'TEST_TIMEOUT'):
            self.trace(.2)
        time.sleep(.7)
        self.assertFalse((self.root / 'late_timeout').exists())

    def test_public_trace_overflow_is_typed_failure_not_a_report(self):
        self.tests.write_text("import os\nfor _ in range(150): os.write(1,b'x'*65536)\n"
                              "os.write(1,b'\u005cn')\nfrom m import f\nassert f()\n")
        with self.assertRaisesRegex(self.error, 'TEST_OUTPUT_LIMIT_EXCEEDED'):
            self.tool.run({'source_root': '.', 'test_paths': ['test_m.py'],
                           'output_path': 'trace.json', 'timeout_s': 2,
                           'max_trace_events': 3000}, self.root)
        self.assertFalse((self.root / 'trace.json').exists())

    def test_wrapper_exit_zero_is_not_inner_test_success(self):
        self.tests.write_text("import os\nos.write(2,b'log:\\xff\\r\\n')\n"
                              "from m import f\nassert f()\n")
        result = self.trace()
        self.assertEqual(result['returncode'], 0)
        self.assertFalse(result['pass'])
        self.assertGreater(result['event_count'], 0)
        self.assertTrue(result['traceback'])


@unittest.skipUnless(os.name == 'posix', 'owned POSIX groups and bounded capture')
class LocalizerLifecycleReuseTests(TraceLifecycleControls, unittest.TestCase):
    tool = localizer
    error = localizer.FaultLocalizerError


@unittest.skipUnless(os.name == 'posix', 'owned POSIX groups and bounded capture')
class ProvenanceLifecycleReuseTests(TraceLifecycleControls, unittest.TestCase):
    tool = provenance
    error = provenance.ProvenanceError


if __name__ == '__main__':
    unittest.main()
