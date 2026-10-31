"""Real-tree regressions: execution evidence is not inventory or search success."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime.bound_capabilities import evidence_oracle_hypothesis_v1 as hyp
from canonical.runtime.bound_capabilities import software_patch_cegis_z3_v1 as synthesis
from canonical.runtime.bound_capabilities import software_repair_loop_cegis_hypothesis_v1 as loop


class OracleExecutionTruthTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)

    def oracle(self, source, **extra):
        return hyp.run({'source': source, 'output_path': 'report.json', **extra}, self.root)

    def test_zero_budget_cannot_verify_an_unexecuted_repair(self):
        source = self.root / 'broken.py'
        source.write_text('def f(x):\n    return x - 5\n')
        before = source.read_bytes()
        result = loop.run({'budget': 0, 'source_path': 'broken.py',
                           'output_path': 'report.json'}, self.root)
        self.assertIs(result['verified'], False)
        self.assertIs(result['execution_performed'], False)
        self.assertEqual(result['iterations'], 0)
        self.assertEqual(source.read_bytes(), before)
        self.assertIs(json.loads((self.root / 'report.json').read_text())['verified'], False)

    def test_default_budget_does_not_run_unrelated_examples(self):
        result = loop.run({'output_path': 'report.json'}, self.root)
        self.assertIs(result['verified'], False)
        self.assertEqual(result['iterations'], 0)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['report.json'])

    def test_available_kernels_are_still_not_execution(self):
        p = self.root / 'canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json'
        p.parent.mkdir(parents=True)
        ids = ['software.patch.synthesize.cegis.z3.v1', 'evidence.oracle.hypothesis_property.v1',
               'evidence.oracle.concrete_execution.v1', 'software.repair.choreograph.crossfile.v1']
        p.write_text(json.dumps({'capabilities': {cid: {} for cid in ids}}))
        result = loop.run({'output_path': 'report.json'}, self.root)
        self.assertIs(result['inventory_ready'], True)
        self.assertIs(result['verified'], False)

    def test_exhausted_frontier_is_not_verified_patch(self):
        result = synthesis.run({'output_path': 'report.json'}, self.root)
        self.assertIs(result['verified'], False)
        self.assertIs(result['candidate_found'], False)
        self.assertEqual(result['status'], 'NEW_PRIMITIVE_REQUIRED')
        self.assertIs(result['output_verified'], True)

    def test_found_architecture_is_only_a_candidate(self):
        component = {'id': 'm', 'kind': 'MECHANISM', 'requires': [], 'provides': ['done'],
                     'verified': True, 'brain_owned': True, 'donor_independent': True,
                     'cost': {'wall_clock': 1, 'incremental_spend_usd': 0,
                              'persistent_bits': 0, 'risk': 0}}
        manifest = {'components': [component], 'initial_facts': [], 'counterexamples': [],
                    'target': {'required_effects': ['done'], 'max_components': 1, 'top_k': 1}}
        result = synthesis.run({'manifest': manifest, 'output_path': 'report.json'}, self.root)
        self.assertIs(result['candidate_found'], True)
        self.assertIs(result['verified'], False)
        self.assertIs(result['execution_performed'], False)

    def test_invalid_python_does_not_publish_checks(self):
        with self.assertRaises(SyntaxError):
            self.oracle('def f(:\n')
        self.assertFalse((self.root / 'report.json').exists())

    def test_source_is_required_not_replaced_by_default_example(self):
        with self.assertRaisesRegex(ValueError, '^SOURCE_REQUIRED$'):
            hyp.run({'output_path': 'report.json'}, self.root)
        self.assertFalse((self.root / 'report.json').exists())

    def test_missing_contract_does_not_publish_checks(self):
        with self.assertRaisesRegex(ValueError, '^POSTCONDITION_REQUIRED$'):
            self.oracle('def f(x):\n    return abs(x)\n')
        self.assertFalse((self.root / 'report.json').exists())

    def test_actual_contract_is_checked_not_hardcoded_nonnegative(self):
        result = self.oracle('def f(x):\n    """post: _ < 0"""\n    return abs(x)\n')
        self.assertGreater(result['checked'], 0)
        self.assertTrue(result['violations'])
        self.assertIs(result['verified'], False)
        self.assertEqual(result['status'], 'CONTRACT_VIOLATION_FOUND')

    def test_real_positive_sample_distinguishes_backend_availability(self):
        result = self.oracle('def f(x):\n    """post: _ >= 0"""\n    return abs(x)\n')
        available = importlib.util.find_spec('hypothesis') is not None
        self.assertEqual(result['hypothesis_available'], available)
        self.assertEqual(result['verified'], available)
        self.assertEqual(result['violations'], [])
        self.assertGreater(result['checked'], 0)
        if not available:
            self.assertEqual(result['checked'], 13)
            self.assertEqual(result['status'], 'OPEN__HYPOTHESIS_UNAVAILABLE')

    def test_source_report_alias_is_refused(self):
        p = self.root / 'source.py'
        p.write_text('def f(x):\n    """post: _ >= 0"""\n    return abs(x)\n')
        before = p.read_bytes()
        with self.assertRaises(RuntimeError):
            hyp.run({'source_path': 'source.py', 'output_path': 'source.py'}, self.root)
        self.assertEqual(p.read_bytes(), before)

    def test_inventory_cannot_overwrite_python(self):
        p = self.root / 'source.py'
        p.write_text('original = 1\n')
        with self.assertRaises(RuntimeError):
            loop.run({'budget': 0, 'output_path': 'source.py'}, self.root)
        self.assertEqual(p.read_text(), 'original = 1\n')


if __name__ == '__main__':
    unittest.main()
