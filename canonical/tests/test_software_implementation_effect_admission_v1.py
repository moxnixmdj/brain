"""Task-effect and preservation regressions against the current runtime."""
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.runtime import live_integrated_brain_v1 as live
from canonical.runtime import swe_typed_plan_v1 as plans
from canonical.runtime import composer_route_v1 as composer
from canonical.runtime.bound_capabilities import python_change_impact_testselect as impact

ROOT = pathlib.Path(__file__).resolve().parents[2]
CID = 'python.source.audit.ast'


class ImplementationEffectAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='implementation_effect_', dir=ROOT/'canonical/astra_runtime/tmp')
        self.addCleanup(self.tmp.cleanup)
        self.base = pathlib.Path(self.tmp.name)
        self.source = self.base/'calc.py'
        self.source.write_text('def add(a, b):\n    return a + b\n')
        self.test = self.base/'test_calc.py'
        self.test.write_text('import unittest\nclass Tests(unittest.TestCase):\n    def test_existing(self): self.assertEqual(1+2,3)\n')
        self.report = self.base/'report.json'
        self.goal = f'Implement a subtract feature in the python source root {self.base} and write the report to {self.report}'

    def test_public_feature_request_does_not_execute_analysis(self):
        before = {p.name:p.read_bytes() for p in self.base.iterdir()}
        result = door.solve({'task_id':'feature_effect_guard', 'goal':self.goal})
        self.assertFalse(result.get('pass'), result)
        self.assertFalse(result.get('executed'), result)
        self.assertIn('IMPLEMENTATION_EFFECT_UNSERVED', str(result))
        self.assertEqual({p.name:p.read_bytes() for p in self.base.iterdir()}, before)

    def test_feature_request_without_tests_refuses_without_writes(self):
        self.test.unlink()
        before = {p.name:p.read_bytes() for p in self.base.iterdir()}
        result = door.solve({'task_id':'feature_without_tests', 'goal':self.goal})
        self.assertFalse(result.get('pass'), result)
        self.assertFalse(result.get('executed'), result)
        self.assertEqual({p.name:p.read_bytes() for p in self.base.iterdir()}, before)

    def test_impact_report_cannot_create_fake_python_source(self):
        output = self.base/'new_test.py'
        with self.assertRaisesRegex(RuntimeError, 'REPORT_DESTINATION_IS_SOURCE'):
            impact.run({'source_root':str(self.base.relative_to(ROOT)),
                        'changed_paths':[str(self.source.relative_to(ROOT))],
                        'output_path':str(output.relative_to(ROOT))}, ROOT)
        self.assertFalse(output.exists())

    def test_implementation_paraphrases_cannot_use_an_audit(self):
        registry = live.load_verified_registry()
        for goal in [f'Implement subtract(a,b) in {self.source}',
                     f'Please implement a subtraction feature in {self.base}',
                     f'Can you implement a Python feature in {self.base}?',
                     f'Add a subtract function to the python source root {self.base}']:
            with self.subTest(goal=goal):
                self.assertEqual(plans.implementation_effect_error(goal, [CID], registry),
                                 'R10_SOFTWARE_IMPLEMENTATION_EFFECT_UNSERVED')

    def test_real_impact_analysis_still_writes_repeatable_reports(self):
        args = {'source_root':str(self.base.relative_to(ROOT)),
                'changed_paths':[str(self.source.relative_to(ROOT))],
                'output_path':str(self.report.relative_to(ROOT))}
        first = impact.run(args, ROOT)
        second = impact.run(args, ROOT)
        self.assertTrue(first['output_verified'])
        self.assertEqual(first['output_sha256'], second['output_sha256'])
        self.assertEqual(self.source.read_text(), 'def add(a, b):\n    return a + b\n')

    def test_explicit_capability_id_cannot_override_task_effect(self):
        registry = live.load_verified_registry()
        compiled = {'selected_capability':CID, 'front_compiler':{'rules_applied':['F15_EXPLICIT_CAPABILITY_ID_NAMED']}}
        result = door.route_admission(self.goal+' using '+CID, compiled, registry)
        self.assertFalse(result['admitted'])
        self.assertEqual(result['rule'], 'R10_SOFTWARE_IMPLEMENTATION_EFFECT_UNSERVED')

    def test_analysis_only_composed_chain_does_not_dispatch(self):
        with patch.object(door, 'run_adapter_locally', side_effect=AssertionError('must not dispatch')):
            result = composer.execute_chain([CID], self.goal, registry=live.load_verified_registry())
        self.assertFalse(result['pass'])
        self.assertEqual(result['steps'], [])
        self.assertIn('IMPLEMENTATION_EFFECT_UNSERVED', result['status'])

    def test_analysis_only_dag_does_not_admit(self):
        dag = {'schema':door.front.DAG_SCHEMA, 'steps':[{'cycle':0,'capability_id':CID,'clause':self.goal}]}
        result = door.route_admission(self.goal, {'capability_dag':dag}, live.load_verified_registry())
        self.assertFalse(result['admitted'])
        self.assertIn('IMPLEMENTATION_EFFECT_UNSERVED', result['rule'])

    def test_read_only_audit_remains_executable(self):
        result = door.solve({'task_id':'feature_effect_audit_control', 'goal':f'Count the functions defined in the python source root {self.base} and write the report to {self.report}'})
        self.assertTrue(result.get('pass'), result)
        self.assertTrue(self.report.is_file())
        self.assertEqual(self.source.read_text(), 'def add(a, b):\n    return a + b\n')

    def test_effect_detector_ignores_paths_and_quoted_literals(self):
        for goal in ['Audit python source /tmp/implement/feature.py', 'Search python files for exact text "implement a feature"', 'Explain how to implement a Python feature']:
            with self.subTest(goal=goal):
                self.assertIsNone(plans.implementation_effect_error(goal, [CID], live.load_verified_registry()))

    def test_source_write_contract_is_necessary_not_declared_complete(self):
        result = plans.implementation_effect_error(self.goal, ['python.software.repair.apply.verified.v1'], live.load_verified_registry())
        self.assertIsNone(result)

    def test_impact_report_cannot_alias_any_source_or_index(self):
        for kind in ('source', 'test', 'hardlink', 'index', 'diff'):
            with self.subTest(kind=kind):
                index = self.base/'index.json';index.write_text('{}')
                diff = self.base/'change.diff';diff.write_text('not a diff')
                output = {'source':self.source,'test':self.test,'index':index,'diff':diff}.get(kind, self.base/'alias.json')
                if kind == 'hardlink': output.hardlink_to(self.source)
                before = self.source.read_bytes(),self.test.read_bytes(),index.read_bytes(),diff.read_bytes()
                args = {'source_root':str(self.base.relative_to(ROOT)), 'changed_paths':[str(self.source.relative_to(ROOT))], 'output_path':str(output.relative_to(ROOT))}
                if kind == 'index': args['index_path']=str(index.relative_to(ROOT))
                if kind == 'diff': args['diff_path']=str(diff.relative_to(ROOT))
                with self.assertRaisesRegex(RuntimeError, 'REPORT_OVERWRITES_INPUT'):
                    impact.run(args, ROOT)
                self.assertEqual((self.source.read_bytes(),self.test.read_bytes(),index.read_bytes(),diff.read_bytes()), before)
