"""Real trace execution must not confuse suite stdout with its result channel."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime.bound_capabilities import python_dynamic_fault_localizer_v1 as localizer
from canonical.runtime.bound_capabilities import python_interprocedural_value_provenance_v1 as provenance


class ResultChannelControls:
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix='brain_trace_channel_control_')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'm.py'
        self.source.write_text('def f():\n    return False\n')
        self.test = self.root / 'test_m.py'

    def trace(self):
        env = self.tool._source_env(self.source, self.test)
        if self.tool is provenance:
            return self.tool._trace_one(self.root, self.test, 3, 3000, 128, env)
        return self.tool._trace_one(self.root, self.test, 3, 3000, env)

    def fake_marker(self):
        marker = '__BRAIN_PROVENANCE__' if self.tool is provenance else '__BRAIN_TRACE__'
        return marker + json.dumps({'pass': True, 'events': [], 'traceback': [], 'event_count': 0})

    def assert_real_failure(self):
        original = self.test.read_bytes()
        result = self.trace()
        self.assertEqual(result['returncode'], 0)  # wrapper is not the test verdict
        self.assertIs(result['pass'], False)
        self.assertGreater(result['event_count'], 0)
        self.assertTrue(result['traceback'])
        self.assertEqual(self.test.read_bytes(), original)
        self.assertEqual(self.source.read_text(), 'def f():\n    return False\n')

    def test_unterminated_stdout_does_not_hide_real_failing_trace(self):
        self.test.write_text("print('progress without newline',end='')\nfrom m import f\nassert f()\n")
        self.assert_real_failure()

    def test_redirected_stdout_does_not_hide_real_failing_trace(self):
        self.test.write_text("import sys,os\nsys.stdout=open(os.devnull,'w')\n"
                             "from m import f\nassert f()\n")
        self.assert_real_failure()

    def test_shutdown_marker_cannot_replace_real_failing_verdict(self):
        self.test.write_text("import atexit\n"
                             f"atexit.register(lambda:print({self.fake_marker()!r}))\n"
                             "from m import f\nassert f()\n")
        self.assert_real_failure()

    def test_early_exit_marker_cannot_substitute_for_missing_trace_artifact(self):
        self.test.write_text("import os\n"
                             f"print({self.fake_marker()!r},flush=True)\nos._exit(0)\n")
        with self.assertRaisesRegex(self.error, '^TRACE_OUTPUT_MISSING$'):
            self.tool.run({'source_root': '.', 'test_paths': ['test_m.py'],
                           'output_path': 'report.json', 'timeout_s': 3}, self.root)
        self.assertFalse((self.root / 'report.json').exists())

    def assert_bad_artifact(self, mutation, reason):
        # Negative fault injection inside a real traced child. This explicitly
        # exercises transport refusal, not a fabricated successful trace.
        self.test.write_text("import os,sys,json\nfrom pathlib import Path\n"
                             "p=Path(sys.argv[-1])\n"
                             "Path('channel_path.txt').write_text(str(p))\n"
                             + mutation + "\nos._exit(0)\n")
        with self.assertRaisesRegex(self.error, '^' + reason + '$'):
            self.trace()
        channel = Path((self.root / 'channel_path.txt').read_text())
        self.assertFalse(channel.parent.exists(), 'owned artifact must be cleaned on refusal')

    def test_malformed_artifacts_are_typed_refusals_and_cleaned(self):
        for mutation in ("p.write_text('{')", "p.write_bytes(b'\\xff')",
                         "p.write_text('[]')", "p.write_text('{}')"):
            with self.subTest(mutation=mutation):
                self.assert_bad_artifact(mutation, 'TRACE_OUTPUT_INVALID')

    def test_nonregular_artifacts_are_refused_without_pipe_blocking(self):
        mutations = ["p.mkdir()", "p.symlink_to(Path('m.py').resolve())"]
        if os.name == 'posix':
            mutations.append('os.mkfifo(p)')
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.assert_bad_artifact(mutation, 'TRACE_OUTPUT_INVALID')
        self.assertEqual(self.source.read_text(), 'def f():\n    return False\n')

    @unittest.skipUnless(Path('/proc/self/fd').is_dir(), 'Linux descriptor accounting')
    def test_repeated_directory_refusal_does_not_leak_parent_descriptors(self):
        before = len(os.listdir('/proc/self/fd'))
        for _ in range(4):
            self.assert_bad_artifact('p.mkdir()', 'TRACE_OUTPUT_INVALID')
        self.assertEqual(len(os.listdir('/proc/self/fd')), before)

    def test_oversized_artifact_is_refused_before_json_parsing(self):
        limit = self.tool._PATCH.MAX_TEST_OUTPUT_BYTES
        self.assert_bad_artifact(f"p.write_bytes(b' '*{limit + 1})", 'TEST_OUTPUT_LIMIT_EXCEEDED')

    @unittest.skipUnless(os.name == 'posix', 'POSIX aggregate raw diagnostic budget')
    def test_diagnostics_and_result_share_one_raw_budget(self):
        limit = self.tool._PATCH.MAX_TEST_OUTPUT_BYTES
        mutation = (f"os.write(1,b'x'*{limit - 200})\n"
                    "p.write_text(json.dumps({'pass':True,'events':[],'traceback':[],"
                    "'event_count':0,'padding':'y'*400}))")
        self.assert_bad_artifact(mutation, 'TEST_OUTPUT_LIMIT_EXCEEDED')

    @unittest.skipUnless(os.name == 'posix', 'POSIX raw-byte accounting')
    def test_utf8_replacement_does_not_overcharge_raw_diagnostic_budget(self):
        self.test.write_text("import os\nos.write(1,b'\\xff'*3000000)\n"
                             "from m import f\nassert f()\n")
        self.assert_real_failure()

    def test_private_artifact_is_cleaned_after_real_failing_trace(self):
        self.test.write_text("import sys\nfrom pathlib import Path\n"
                             "Path('channel_path.txt').write_text(sys.argv[-1])\n"
                             "from m import f\nassert f()\n")
        self.assert_real_failure()
        channel = Path((self.root / 'channel_path.txt').read_text())
        self.assertFalse(channel.parent.exists())


class LocalizerResultChannelTests(ResultChannelControls, unittest.TestCase):
    tool = localizer
    error = localizer.FaultLocalizerError


class ProvenanceResultChannelTests(ResultChannelControls, unittest.TestCase):
    tool = provenance
    error = provenance.ProvenanceError


if __name__ == '__main__':
    unittest.main()
