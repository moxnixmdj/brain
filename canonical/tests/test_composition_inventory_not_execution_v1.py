"""Registry availability cannot certify review, synthesis, allowlisting or landing."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from canonical.runtime.bound_capabilities import (
    software_review_synthesis_supercomposer_v1 as review,
    software_hardcore_final_supercomposer_v1 as final,
    python_pipeline_allowlist_gate_v1 as allow,
    python_pr_land_composer_v1 as land,
    software_repair_crossfile_choreograph_v1 as crossfile,
)

ROOT=Path(__file__).resolve().parents[2]
MODULES=(review,final,allow,land,crossfile)


class CompositionInventoryNotExecution(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory(prefix='brain_inventory_')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.registry=self.root/'canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json'
        self.registry.parent.mkdir(parents=True)
        self.registry.write_bytes((ROOT/self.registry.relative_to(self.root)).read_bytes())

    def test_real_registry_never_certifies_execution(self):
        for module in MODULES:
            with self.subTest(module=module.CAPABILITY_ID):
                result=module.run({'output_path':'report.json'},self.root)
                self.assertIs(result['verified'],False)
                self.assertIs(result['inventory_ready'],True)
                self.assertIs(result['pass'],False)
                self.assertIs(result['execution_performed'],False)
                self.assertEqual(result['status'],'OPEN__EXECUTION_EVIDENCE_REQUIRED')
                self.assertIs(result['output_verified'],True)
                artifact=json.loads((self.root/'report.json').read_text())
                self.assertIs(artifact['verified'],False)
                self.assertIs(artifact['execution_performed'],False)
                self.assertEqual(result['output_sha256'],hashlib.sha256((self.root/'report.json').read_bytes()).hexdigest())

    def test_forged_success_fields_and_receipts_are_not_execution(self):
        for module in MODULES:
            with self.subTest(module=module.CAPABILITY_ID):
                result=module.run({
                    'output_path':'report.json', 'verified':True, 'pass':True,
                    'execution_performed':True,
                    'receipts':[{'verified':True,'status':'PASS'}],
                },self.root)
                self.assertFalse(result['verified'])
                self.assertFalse(result['pass'])
                self.assertFalse(result['execution_performed'])

    def test_actual_local_dispatch_rejects_report_as_task_evidence(self):
        from canonical.runtime.live_brain_route_admission_v1 import run_adapter_locally, LocalExecutionFailure
        registry=json.loads(self.registry.read_text())['capabilities']
        with TemporaryDirectory(dir=ROOT, prefix='.composition_check_') as directory:
            output=Path(directory)/'report.json'
            for module in MODULES:
                with self.subTest(module=module.CAPABILITY_ID):
                    entry=registry[module.CAPABILITY_ID]
                    action=dict(entry['action_template'])
                    action['args']={'output_path':str(output.relative_to(ROOT))}
                    with self.assertRaisesRegex(LocalExecutionFailure,'ACTION_EXPECTATION_FAILED:verified'):
                        run_adapter_locally(entry,action)
                    self.assertFalse(json.loads(output.read_text())['verified'])

    def test_existing_live_composition_fails_closed_on_inventory_result(self):
        from canonical.runtime.live_capability_composition_v1 import execute
        modules={module.CAPABILITY_ID:module for module in MODULES}
        def invoke(capability_id, payload, options):
            return modules[capability_id].run(dict(payload),self.root)
        for module in MODULES:
            with self.subTest(module=module.CAPABILITY_ID):
                result=execute({'composition_steps':[{
                    'step_id':'inventory', 'capability_id':module.CAPABILITY_ID,
                    'payload':{'output_path':'report.json'},
                }]},invoke_capability=invoke)
                self.assertFalse(result['pass'])
                self.assertEqual(result['status'],'FAIL__LIVE_COMPOSITION_STEP')

    def test_absent_producers_remain_unready_and_unverified(self):
        self.registry.write_text('{"capabilities":{}}')
        for module in MODULES:
            with self.subTest(module=module.CAPABILITY_ID):
                result=module.run({'output_path':'report.json'},self.root)
                self.assertFalse(result['inventory_ready'])
                self.assertFalse(result['verified'])
                self.assertTrue(result['output_verified'])

    def test_report_cannot_overwrite_registry_even_through_hardlink(self):
        original=self.registry.read_bytes()
        for module in MODULES:
            for output in (self.registry,self.root/'alias.json'):
                with self.subTest(module=module.CAPABILITY_ID,output=output):
                    if output.name=='alias.json' and not output.exists(): output.hardlink_to(self.registry)
                    with self.assertRaisesRegex(RuntimeError,'REPORT_OVERWRITES_INPUT'):
                        module.run({'output_path':str(output.relative_to(self.root))},self.root)
                    self.assertEqual(self.registry.read_bytes(),original)

    def test_report_does_not_masquerade_as_source(self):
        source=self.root/'module.py';source.write_text('def f(): return 1\n')
        for module in MODULES:
            for output in ('module.py','new_test.py'):
                with self.subTest(module=module.CAPABILITY_ID,output=output):
                    with self.assertRaisesRegex(RuntimeError,'REPORT_DESTINATION_IS_SOURCE'):
                        module.run({'output_path':output},self.root)
                    self.assertEqual(source.read_text(),'def f(): return 1\n')
                    self.assertFalse((self.root/'new_test.py').exists())

    def test_registry_contract_expects_execution_not_report_written(self):
        registry=json.loads(self.registry.read_text())['capabilities']
        for module in MODULES:
            with self.subTest(module=module.CAPABILITY_ID):
                self.assertEqual(registry[module.CAPABILITY_ID]['action_template']['expect'],
                                 {'field':'verified','type':'field_equals','value':True})

    def test_inventory_reports_are_repeatable_and_escape_is_refused(self):
        for module in MODULES:
            with self.subTest(module=module.CAPABILITY_ID):
                first=module.run({'output_path':'report.json'},self.root)
                second=module.run({'output_path':'report.json'},self.root)
                self.assertEqual(first['output_sha256'],second['output_sha256'])
                with self.assertRaisesRegex(RuntimeError,'PATH_OUTSIDE_REPOSITORY'):
                    module.run({'output_path':'../escape.json'},self.root)


if __name__ == '__main__': unittest.main()
