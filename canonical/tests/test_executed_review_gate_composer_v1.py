"""Orchestration controls plus actual analyzer integration (when installed)."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime.bound_capabilities import software_review_gate_composer_v1 as review


class ReviewComposerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='review-composer-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'anchor').mkdir()
        (self.root / 'anchor/calc.py').write_text('def add(a: int, b: int) -> int:\n    return sum((a, -b))\n')
        (self.root / 'anchor/test_calc.py').write_text('from calc import add\ndef test_add():\n    assert add(2,3)==5\n    assert add(0,0)==0\n    assert add(-2,1)==-1\n')
        (self.root / 'anchor/bench.py').write_text('from calc import add\ndef bench():\n    for i in range(100000):\n        add(i, 1)\n')
        (self.root / 'change.diff').write_text('--- a/calc.py\n+++ b/calc.py\n@@ -1,2 +1,2 @@\n def add(a: int, b: int) -> int:\n-    return sum((a, -b))\n+    return a + b\n')
        self.args = dict(anchor_path='anchor', diff_path='change.diff', bench_path='bench.py', output_path='review.json', timeout_s=30)

    def delegates(self, changed=None):
        """Controlled gate reports test orchestration, NOT analyzer correctness."""
        calls = []
        def gate(args, root):
            name = Path(args['output_path']).stem
            calls.append(name)
            report = dict(gate='PASS', complete=True, verified=True,
                          diff_sha256=hashlib.sha256((root / args['diff_path']).read_bytes()).hexdigest())
            if changed:
                changed(name, report)
            out = root / args['output_path']
            out.write_text(json.dumps(report))
            return dict(report, output_path=args['output_path'], output_verified=True,
                        output_sha256=hashlib.sha256(out.read_bytes()).hexdigest())
        return {name: gate for name in ('static', 'type', 'coverage', 'performance', 'security', 'mutation')}, calls

    def test_missing_diff_cannot_report_success(self):
        with self.assertRaisesRegex(RuntimeError, 'REVIEW_INPUT_REQUIRED'):
            review.run({'output_path':'review.json'}, self.root)
        self.assertFalse((self.root / 'review.json').exists())

    def test_all_six_executions_and_reports_are_required(self):
        functions, calls = self.delegates()
        before = (self.root / 'anchor/calc.py').read_bytes()
        with patch.object(review, '_gate_functions', return_value=functions):
            result = review.run(self.args, self.root)
        self.assertTrue(result['verified'])
        self.assertEqual(set(calls), set(functions))
        self.assertEqual(len(calls), 6)
        self.assertEqual((self.root / 'anchor/calc.py').read_bytes(), before)
        report = json.loads((self.root / 'review.json').read_text())
        self.assertEqual(len(report['executions']), 6)

    def test_failure_partial_and_wrong_diff_never_pass(self):
        for fields in ({'gate':'FAIL'}, {'gate':'PASS_BLIND'}, {'complete':False},
                       {'verified':False}, {'diff_sha256':'0'*64}):
            with self.subTest(fields=fields):
                def alter(name, report):
                    if name == 'mutation': report.update(fields)
                functions, _ = self.delegates(alter)
                with patch.object(review, '_gate_functions', return_value=functions):
                    result = review.run(self.args, self.root)
                self.assertFalse(result['verified'])
                self.assertFalse(result['gates_verified'])
                self.assertEqual(result['status'], 'FAIL__REVIEW_GATES_NOT_PASSED')

    def test_gate_exception_is_recorded_as_failure(self):
        functions, _ = self.delegates()
        def raises(args, root): raise SystemExit('TOOL_UNAVAILABLE')
        functions['static'] = raises
        with patch.object(review, '_gate_functions', return_value=functions):
            result = review.run(self.args, self.root)
        self.assertFalse(result['verified'])
        self.assertEqual(len(json.loads((self.root/'review.json').read_text())['executions']), 6)

    def test_report_cannot_overwrite_anchor_source(self):
        args = dict(self.args, output_path='anchor/calc.py')
        before = (self.root/'anchor/calc.py').read_bytes()
        with self.assertRaisesRegex(RuntimeError, 'REVIEW_OUTPUT_OVERLAPS_ANCHOR'):
            review.run(args, self.root)
        self.assertEqual((self.root/'anchor/calc.py').read_bytes(), before)

    def test_real_gates_do_not_accept_missing_analyzers_as_full_review(self):
        # Executes real delegates. On a minimal interpreter the partial static,
        # type and security outcomes must not be promoted into complete review.
        import importlib.util
        if all(importlib.util.find_spec(n) for n in ('ruff','mypy','coverage','bandit','pytest')):
            self.skipTest('full-toolchain positive integration is run separately')
        result = review.run(self.args, self.root)
        self.assertFalse(result['verified'])

    def test_mutated_diff_cannot_be_accepted(self):
        functions, _ = self.delegates()
        good = functions['mutation']
        def changes_diff(args, root):
            result = good(args, root)
            (root/args['diff_path']).write_text('changed after gate execution')
            return result
        functions['mutation'] = changes_diff
        with patch.object(review, '_gate_functions', return_value=functions):
            result = review.run(self.args, self.root)
        self.assertFalse(result['verified'])

    def test_report_hardlink_to_source_is_refused(self):
        source = self.root/'anchor/calc.py'
        before = source.read_bytes()
        (self.root/'review.json').hardlink_to(source)
        with self.assertRaisesRegex(RuntimeError, 'REPORT_OVERWRITES_INPUT'):
            review.run(self.args, self.root)
        self.assertEqual(source.read_bytes(), before)

    def test_report_hash_or_verdict_disagreement_is_rejected(self):
        for mode in ('hash', 'verdict', 'missing_report'):
            with self.subTest(mode=mode):
                functions, _ = self.delegates()
                good = functions['static']
                def inconsistent(args, root):
                    result = good(args, root)
                    if mode == 'hash':
                        result['output_sha256'] = '0'*64
                    elif mode == 'verdict':
                        result['gate'] = 'FAIL'
                    else:
                        (root / args['output_path']).unlink()
                    return result
                functions['static'] = inconsistent
                with patch.object(review, '_gate_functions', return_value=functions):
                    result = review.run(self.args, self.root)
                self.assertFalse(result['verified'])

    def test_registry_expects_acceptance_not_report_creation(self):
        registry = Path(__file__).resolve().parents[2] / 'canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json'
        entry = json.loads(registry.read_text())['capabilities'][review.CAPABILITY_ID]
        args = entry['action_template']['args']
        for role in ('anchor_path', 'diff_path', 'bench_path'):
            self.assertEqual(args[role], '${input.' + role + '}')
        self.assertEqual(entry['action_template']['expect']['field'], 'verified')
        from canonical.runtime.live_brain_route_admission_v1 import _check_expectation, LocalExecutionFailure
        with self.assertRaises(LocalExecutionFailure):
            _check_expectation(entry['action_template']['expect'], {'output_verified':True, 'verified':False})

    def test_real_full_toolchain_passes_and_preserves_inputs(self):
        import importlib.util
        if not all(importlib.util.find_spec(n) for n in ('ruff','mypy','coverage','bandit','pytest')):
            self.skipTest('requires actual analyzer toolchain installed outside tests')
        before = {p.name:p.read_bytes() for p in (self.root/'anchor').iterdir()}
        result = review.run(self.args, self.root)
        artifact = json.loads((self.root/'review.json').read_text())
        self.assertTrue(result['verified'], artifact['executions'])
        self.assertEqual([row['report']['gate'] for row in artifact['executions']], ['PASS']*6)
        self.assertEqual(before, {p.name:p.read_bytes() for p in (self.root/'anchor').iterdir()})
        self.assertEqual(list(self.root.glob('.review_*')), [])

    def test_real_weak_tests_cannot_pass_mutation_gate(self):
        import importlib.util
        if not all(importlib.util.find_spec(n) for n in ('ruff','mypy','coverage','bandit','pytest')):
            self.skipTest('requires actual analyzer toolchain installed outside tests')
        (self.root/'anchor/test_calc.py').write_text('from calc import add\ndef test_add():\n    assert add(0,0)==0\n')
        result = review.run(self.args, self.root)
        self.assertFalse(result['verified'])
        artifact = json.loads((self.root/'review.json').read_text())
        mutation = next(row for row in artifact['executions'] if row['gate']=='mutation')
        self.assertEqual(mutation['report']['gate'], 'FAIL')
        self.assertGreater(mutation['report']['mutants_survived'], 0)
