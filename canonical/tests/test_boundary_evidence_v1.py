"""Finite behavioral checks, not a proof of equivalence or a containment test."""
import base64
import os
import shlex
import time
import unittest
import zlib

from canonical.swe_kernel.harbor_epistemic_controller_v1 import solve_harbor_cycle
from canonical.swe_kernel.harbor_in_container_runner_v1 import _instruction_text
from canonical.swe_kernel.petri_cow_splicing_engine_v1 import CoWDifferentialBoundaryFuzzer as Fuzzer


@unittest.skipUnless(hasattr(os, 'fork'), 'requires fork workers')
class DifferentialEvidenceTests(unittest.TestCase):
    def test_same_sort_and_mutated_argument_are_observable_differences(self):
        def reference(x):
            return [True]

        result = Fuzzer.verify_differential_invariance(reference, lambda x: [1], [(0,)])
        self.assertFalse(result['ok'])
        self.assertEqual(result['cases_tested'], result['cases_generated'])
        self.assertTrue(result['regressions'])
        self.assertEqual({r['kind'] for r in result['regressions']}, {'VALUE_DRIFT'})

        def mutates(x):
            if type(x) is list:
                x.append(0)
            return [True]

        r = Fuzzer.verify_differential_invariance(reference, mutates, [([],)], workers=2)
        self.assertFalse(r['ok'])
        self.assertIn('ARGUMENT_EFFECT_DRIFT', {v['kind'] for v in r['regressions']})
        equal = Fuzzer.verify_differential_invariance(mutates, mutates, [([],)], failing_inputs=[([],)], workers=2)
        self.assertTrue(equal['ok'])
        self.assertEqual(equal['excluded_intended_change'], 1)
        self.assertEqual(equal['cases_tested'], equal['cases_generated'] - 1)

    def test_absent_worker_payload_and_noncomparisons_never_verify(self):
        for exit_code in (0, 7):
            r = Fuzzer.verify_differential_invariance(lambda x: x, lambda x: os._exit(exit_code), [(7,)])
            self.assertFalse(r['ok'])
            self.assertEqual(r['missing'], r['cases_generated'])
            self.assertEqual(r['cases_tested'], 0)
        r = Fuzzer.verify_differential_invariance(lambda x: 1 / 0, lambda x: 0, [(7,)])
        self.assertFalse(r['ok'])
        self.assertEqual(r['original_raised'], r['cases_generated'])
        r = Fuzzer.verify_differential_invariance(lambda x: x, lambda x: time.sleep(5), [(7,)], timeout_s=.1)
        self.assertEqual(r['worker_errors'], ['TIMEOUT'])
        self.assertFalse(r['ok'])
        r = Fuzzer.verify_differential_invariance(lambda x: object(), lambda x: object(), [(7,)])
        self.assertFalse(r['ok'])
        self.assertEqual(r['unobservable'], r['cases_generated'])


class InstructionTransportTests(unittest.TestCase):
    def test_discovery_gets_the_entire_instruction_or_a_refusal(self):
        for text in ('Short task.', 'Long task description. ' * 1100 + 'Required suffix: π.'):
            res = solve_harbor_cycle(text, inputs={'harbor_task': text, 'cycle': 1, 'observations': []})
            self.assertTrue(res['pass'])
            argv = shlex.split(res['actions'][0]['args']['command'])
            self.assertEqual(_instruction_text(argv[-1], compressed=argv[-2] == '--instruction-zlib-b64'), text)
        with self.assertRaises(ValueError):
            _instruction_text(base64.b64encode(zlib.compress(b'x' * 64_001)).decode(), compressed=True)
        bad = 'x' * 64_001
        res = solve_harbor_cycle(bad, inputs={'harbor_task': bad, 'cycle': 1, 'observations': []})
        self.assertFalse(res['pass'])
        self.assertNotIn('actions', res)


def test_legacy_fuzzer_counts_observations_not_a_padded_budget(tmp_path):
    import sys
    from canonical.swe_kernel import angelic_lens_cow_repair_v1 as lens

    name, rel = 'trial_rates_92aa', 'trial_rates_92aa.py'
    original = 'def f(x): return x\n'
    (tmp_path / rel).write_text(original)
    original_path = sys.path[:]
    try:
        lens._load_modules_from_sources(tmp_path, {rel: original})
        def check(src, frames, parent=original):
            return lens.fuzz_verify_patch_cow(project_root=tmp_path, rel_path=rel, func_name='f',
                                              orig_source=parent, patched_source=src, pass_envs=frames)
        for frames in ([], [{'other': 1}]):
            r = check(original, frames)
            assert r['status'] == 'UNMEASURED' and r['fuzz_passed'] is False
            assert r['exact_calls_tested'] == r['boundary_cases_tested'] == 0
        dead = check('import os\ndef f(x): os._exit(0)\n', [{'x': 0}])
        assert dead['status'] == 'UNMEASURED' and dead['fuzz_passed'] is False
        assert dead['boundary_cases_tested'] == 0 < dead['boundary_cases_generated']
        drift = check('def f(x): return False\n', [{'x': 0}])
        assert (drift['status'], drift['failure_reason']) == ('COUNTEREXAMPLE', 'PASS_ENV_REGRESSION')
        drift = check('def f(x): x.append(1); return 1\n', [{'x': []}], 'def f(x): return 1\n')
        assert drift['status'] == 'COUNTEREXAMPLE'
        untestable = check(original, [{'x': 0}], 'def f(x): raise ValueError()\n')
        assert untestable['fuzz_passed'] is False and untestable['boundary_cases_tested'] == 0
        identical = check(original, [{'x': True}, {'x': True}])
        assert identical['status'] == 'PASSED_FINITE_CHECKS'
        assert identical['boundary_cases_generated'] == identical['boundary_cases_tested'] == 1
        assert identical['exact_calls_tested'] == 1
    finally:
        sys.path[:] = original_path
        sys.modules.pop(name, None)
