"""Discovered acceptance corpora must execute, not inherit a stale argv."""
import pathlib
import sys
import tempfile
import unittest
from canonical.runtime.bound_capabilities import python_repair_measured_acceptance_controller_v1 as measured
from canonical.runtime.bound_capabilities import python_repair_semantic_acceptance_controller_v1 as semantic


class DiscoveredAcceptanceCorpusTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = pathlib.Path(td.name)
        (self.root / 'm.py').write_text('def f(x):\n    return x < 3\n')
        (self.root / 'test_all.py').write_text(
            'import unittest\nfrom m import f\nclass Edges(unittest.TestCase):\n'
            '    def test_edges(self):\n        self.assertTrue(f(3))\n'
            '        self.assertTrue(f(2))\n        self.assertFalse(f(4))\n')
        self.originals = {p.name: p.read_bytes() for p in self.root.iterdir()}

    def args(self, **extra):
        result = {'source_root': '.', 'test_argv': [sys.executable, '-c', 'pass'],
                  'task_text': 'tests_pass must be true.', 'output_path': 'report.json',
                  'timeout_s': 3, 'mutations_per_file': 12}
        result.update(extra)
        return result

    def assert_originals(self):
        for name, content in self.originals.items():
            self.assertEqual((self.root / name).read_bytes(), content)

    def test_measured_controller_executes_discovered_suite(self):
        out = measured.run(self.args(), self.root)
        self.assertTrue(out['pass'], out)
        self.assertGreater(out['measured_fields']['test_count'], 0)
        self.assertTrue(out['measured_fields']['tests_pass'])
        self.assert_originals()

    def test_semantic_controller_executes_discovered_suite(self):
        out = semantic.run(self.args(task_text='tests_pass must be true. File "m.py" must contain "return x <= 3". Only modify "m.py".'), self.root)
        self.assertTrue(out['acceptance_stop_authorized'], out)
        self.assertGreater(out['measured_fields']['test_count'], 0)
        self.assertTrue(out['measured_fields']['tests_pass'])
        self.assert_originals()

    def test_explicit_empty_paths_also_derives_actual_suite(self):
        out = semantic.run(self.args(test_paths=[]), self.root)
        self.assertTrue(out['pass'], out)
        self.assertGreater(out['measured_fields']['test_count'], 0)
        self.assert_originals()

    def test_stated_paths_keep_the_stated_failing_command(self):
        out = semantic.run(self.args(test_paths=['test_all.py'],
                          test_argv=[sys.executable, '-c', 'raise SystemExit(73)', 'test_all.py']), self.root)
        self.assertFalse(out['pass'], out)
        self.assertFalse(out['acceptance_stop_authorized'])
        self.assert_originals()

    def test_successful_repair_does_not_clear_unsupported_requirements(self):
        out = semantic.run(self.args(task_text='tests_pass must be true. Preserve compatibility with unspecified clients.'), self.root)
        self.assertTrue(out['repair_pass'], out)
        self.assertFalse(out['acceptance_stop_authorized'])
        self.assertFalse(out['pass'])
        self.assertTrue(out['unbound_obligation_ids'])
        self.assert_originals()

    def test_missing_corpus_still_refuses_without_report(self):
        (self.root / 'test_all.py').unlink()
        with self.assertRaisesRegex(semantic.SemanticRepairError, '^NO_TEST_FILES_UNDER_SOURCE_ROOT$'):
            semantic.run(self.args(), self.root)
        self.assertFalse((self.root / 'report.json').exists())
        self.assertEqual((self.root / 'm.py').read_bytes(), self.originals['m.py'])


if __name__ == '__main__':
    unittest.main()
