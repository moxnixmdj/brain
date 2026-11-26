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
