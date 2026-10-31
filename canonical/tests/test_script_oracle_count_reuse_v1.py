"""Count executed script oracles with existing unittest, not assertion estimates."""
import pathlib
import sys
import tempfile
import unittest
from canonical.runtime.bound_capabilities import python_repository_acceptance_measurement_v1 as measurement
from canonical.runtime.bound_capabilities import python_test_guided_patch_search_v1 as engine


class ScriptOracleCountTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = pathlib.Path(td.name)

    def write(self, name, source):
        path = self.root / name
        path.write_text(source)
        return path

    def run_suite(self, *paths):
        result = engine._run_tests(self.root, engine.suite_argv(sys.executable, *paths), 5)
        count = measurement._test_count(result['stdout'] + '\n' + result['stderr'])
        return result, count

    def test_completed_assertion_script_counts_as_one_case_not_each_assertion(self):
        path = self.write('test_script.py', 'assert 2 + 2 == 4\nassert 3 * 3 == 9\n')
        result, count = self.run_suite(path)
        self.assertEqual(result['returncode'], 0, result)
        self.assertEqual(count, 1)

    def test_two_script_oracles_aggregate_two_cases(self):
        first = self.write('test_a.py', 'assert 2 + 2 == 4\n')
        second = self.write('test_b.py', 'assert 3 * 3 == 9\n')
        result, count = self.run_suite(first, second)
        self.assertEqual(result['returncode'], 0, result)
        self.assertEqual(count, 2)

    def test_multiple_unittest_suites_aggregate_all_cases(self):
        first = self.write('test_a.py', 'import unittest\nclass A(unittest.TestCase):\n def test_a(self): self.assertEqual(2+2,4)\n')
        second = self.write('test_b.py', 'import unittest\nclass B(unittest.TestCase):\n def test_b(self): self.assertEqual(3*3,9)\n def test_c(self): self.assertEqual(4*4,16)\n')
        result, count = self.run_suite(first, second)
        self.assertEqual(result['returncode'], 0, result)
        self.assertEqual(count, 3)

    def test_guarded_script_failure_is_counted_and_remains_failure(self):
        path = self.write('test_script.py', 'if __name__ == "__main__":\n raise ValueError("SCRIPT_SENTINEL")\n')
        result, count = self.run_suite(path)
        self.assertNotEqual(result['returncode'], 0)
        self.assertEqual(count, 1)
        self.assertIn('SCRIPT_SENTINEL', result['stderr'])
        self.assertIn('test_script.py', result['stderr'])

    def test_script_successful_exit_is_counted_without_changing_exit_contract(self):
        path = self.write('test_script.py', 'if __name__ == "__main__":\n raise SystemExit(0)\n')
        result, count = self.run_suite(path)
        self.assertEqual(result['returncode'], 0, result)
        self.assertEqual(count, 1)

    def test_no_oracle_is_not_counted_or_accepted(self):
        path = self.write('test_empty.py', 'value = 42\n')
        result, count = self.run_suite(path)
        self.assertNotEqual(result['returncode'], 0)
        self.assertEqual(count, 0)
        self.assertIn('NO_TESTS_COLLECTED', result['stderr'])

    def test_semantic_repair_acceptance_counts_realized_script_oracle(self):
        from canonical.runtime.bound_capabilities import python_repair_semantic_acceptance_controller_v1 as controller
        source = self.write('m.py', 'def f(x):\n    return x < 3\n')
        oracle = self.write('test_all.py', 'from m import f\nassert f(3)\nassert f(2)\nassert not f(4)\n')
        before_source, before_oracle = source.read_bytes(), oracle.read_bytes()
        out = controller.run({'source_root': '.', 'output_path': 'receipt.json',
                              'task_text': 'tests_pass must be true. File "m.py" must contain "return x <= 3".',
                              'test_argv': [sys.executable, '-c', 'pass'],
                              'timeout_s': 3, 'mutations_per_file': 12}, self.root)
        self.assertTrue(out['acceptance_stop_authorized'], out)
        self.assertEqual(out['measured_fields']['test_count'], 1)
        self.assertEqual(source.read_bytes(), before_source)
        self.assertEqual(oracle.read_bytes(), before_oracle)

    def test_actual_repository_measurement_counts_script_and_preserves_bytes(self):
        path = self.write('test_script.py', 'assert 2 + 2 == 4\n')
        before = path.read_bytes()
        out = measurement.run({'source_root': '.', 'test_paths': ['test_script.py'],
                               'output_path': 'receipt.json', 'timeout_s': 5}, self.root)
        self.assertTrue(out['measurements']['tests_pass'], out)
        self.assertEqual(out['measurements']['test_count'], 1)
        self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
