"""Reuse the real guard/selector; never retry a dispatched or unknown outcome."""
import json
import pathlib
import tempfile
import unittest
from time import perf_counter_ns
from unittest.mock import patch

from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.runtime import live_integrated_brain_v1 as live
from canonical.runtime import swe_typed_plan_v1 as typed

ROOT = pathlib.Path(__file__).resolve().parents[2]
CID = 'python.source.symbols.index.ast'


class WritePreflightRetryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT/'canonical/astra_runtime/tmp', prefix='swe_preflight_')
        self.addCleanup(self.tmp.cleanup)
        self.base = pathlib.Path(self.tmp.name)
        self.source = self.base/'mod.py'
        self.body = 'def add(a, b): return a+b\ndef caller(): return add(1, 2)\ndef other(): return add(3, 4)\n'
        self.source.write_text(self.body)
        self.registry = live.load_verified_registry()

    def _compiled(self, output):
        return {'selected_capability':CID, 'inputs':{
            'source_root':str(self.base.relative_to(ROOT)),
            'output_path':str(output.relative_to(ROOT))},
            'target_effects':self.registry[CID]['provides']}

    def test_alias_refusal_precedes_local_adapter_and_controller_dispatch(self):
        with patch.object(door, '_execute_locally', return_value={'pass':False}) as local, \
             patch.object(live, 'drive_controller', return_value=(None, 'DISPATCH_TRAP')) as controller:
            result = door._execute('preflight_alias', 'Index the Python source symbols',
                                   self._compiled(self.source), self.registry, perf_counter_ns())
        self.assertFalse(result['pass'])
        self.assertEqual(result['status'], 'FAIL_CLOSED__WRITE_AUTHORITY_REFUSED')
        self.assertIs(result['executed'], False)
        local.assert_not_called()
        controller.assert_not_called()
        self.assertEqual(self.source.read_text(), self.body)

    def test_safe_report_still_reaches_the_existing_adapter(self):
        report = self.base/'index.json'
        result = door._execute('preflight_safe', 'Index the Python source symbols',
                               self._compiled(report), self.registry, perf_counter_ns())
        self.assertTrue(result['pass'], result)
        self.assertEqual(set(json.loads(report.read_text())['callers_of']['add']), {'caller','other'})
        self.assertEqual(self.source.read_text(), self.body)

    def test_public_caller_analysis_reuses_typed_plan_and_preserves_source(self):
        goal = f'Find every caller of the function add in {self.source.relative_to(ROOT)}.'
        result = door.solve({'task_id':'preflight_public', 'goal':goal})
        self.assertTrue(result['pass'], result)
        self.assertEqual(result['typed_swe_retry']['selected_capability'], CID)
        callers = set()
        for report in self.base.glob('*.json'):
            callers.update(json.loads(report.read_text()).get('callers_of', {}).get('add', []))
        self.assertEqual(callers, {'caller','other'})
        self.assertEqual(self.source.read_text(), self.body)

    def test_bare_repair_reuses_existing_engine_and_changes_the_actual_source(self):
        broken = 'def add(a, b):\n    return a - b\n'
        self.source.write_text(broken)
        test = self.base/'test_mod.py'
        test.write_text('import unittest, mod\nclass Tests(unittest.TestCase):\n'
                        '    def test_add(self): self.assertEqual(mod.add(2, 3), 5)\n'
                        "if __name__ == '__main__': unittest.main()\n")
        test_bytes = test.read_bytes()
        result = door.solve({'task_id':'preflight_real_repair',
                             'goal':'fix '+str(self.source.relative_to(ROOT))})
        self.assertTrue(result['pass'], result)
        self.assertEqual(self.source.read_text(), 'def add(a, b):\n    return a + b\n')
        self.assertEqual(test.read_bytes(), test_bytes)
        # Re-run the unchanged original oracle, not the adapter's verdict.
        import subprocess, sys
        proc = subprocess.run([sys.executable, str(test)], cwd=self.base,
                              capture_output=True, timeout=10)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_named_edit_words_are_operands_not_source_mutation_promises(self):
        source = str(self.source.relative_to(ROOT))
        directory = str(self.base.relative_to(ROOT))
        for name in ('add','update','rename','fix','extract','patch'):
            with self.subTest(name=name):
                read = f'Find every caller of the function {name} in {source}.'
                self.assertEqual(door._promised_source_files(read), [])
                self.assertEqual(door._promised_source_roots(f'Find callers of function {name} in {directory}'), [])
                self.assertEqual(door._promised_source_files(f'Repair the function {name} in {source}'), [source])
                self.assertEqual(door._promised_source_roots(f'Repair the function {name} in {directory}'), [directory])
        self.assertEqual(door._promised_source_files(f'Add a parameter to {source}'), [source])

    def test_replacement_plan_uses_selected_capability_effects(self):
        goal = f'Find every caller of the function add in {self.source.relative_to(ROOT)}.'
        plan = typed.build_plan(goal, ROOT)
        self.assertIsNotNone(plan)
        cid = plan[2]['selected_capability']
        self.assertEqual(plan[2]['target_effects'], plan[1][cid]['provides'])

    def test_executed_retry_failure_is_reported_not_discarded(self):
        primary = {'pass':False,'executed':False,'status':'FAIL_CLOSED__WRITE_AUTHORITY_REFUSED'}
        failed = {'pass':False,'executed':True,'status':'FAIL__REAL_ADAPTER_FAILURE'}
        plan = ({}, {}, {'selected_capability':CID})
        with patch.object(door, '_solve_body', side_effect=[primary, failed]), \
             patch.object(typed, 'is_swe_request', return_value=True), \
             patch.object(typed, 'build_plan', return_value=plan):
            result = door.solve({'task_id':'preflight_failure','goal':'Repair Python code'})
        self.assertIs(result, failed)
        self.assertFalse(result['pass'])
        self.assertTrue(result['executed'])
        self.assertEqual(result['typed_swe_retry']['primary_status'], primary['status'])

    def test_dispatched_refusal_or_failure_never_retries(self):
        for status in ('FAIL_CLOSED__WRITE_AUTHORITY_REFUSED', 'FAIL__LIVE_CONTROLLER_EXECUTION'):
            result = {'pass':False,'executed':True,'status':status}
            with self.subTest(status=status), patch.object(door, '_solve_body', return_value=result), \
                 patch.object(typed, 'build_plan') as build:
                self.assertIs(door.solve({'task_id':'preflight_no_retry','goal':'Repair Python code'}), result)
                build.assert_not_called()

    def test_unplanned_refusal_does_not_dispatch_any_alternative(self):
        result = {'pass':False,'executed':False,'status':'FAIL_CLOSED__WRITE_AUTHORITY_REFUSED'}
        with patch.object(door, '_solve_body', return_value=result) as execute, \
             patch.object(typed, 'is_swe_request', return_value=True), \
             patch.object(typed, 'build_plan', return_value=None):
            self.assertIs(door.solve({'task_id':'preflight_no_plan','goal':'Repair Python code'}), result)
        self.assertEqual(execute.call_count, 1)


if __name__ == '__main__':
    unittest.main()
