"""Actual compatibility entrypoint versus its existing change-impact kernel."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime.bound_capabilities import test_slice_never_miss_v1 as alias
from canonical.runtime.bound_capabilities import python_change_impact_testselect as kernel

ROOT=Path(__file__).resolve().parents[2]
CID='test.slice.never_miss.v1'


class TestSliceKernelReuseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory(prefix='test-slice-kernel-')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        for name,text in {
            'pkg/__init__.py':'',
            'pkg/core.py':'def helper(x): return x+1\n',
            'tests/test_core.py':'from pkg.core import helper\ndef test_helper(): assert helper(1)==2\n',
            'tests/test_other.py':'def test_other(): assert 2+2==4\n',
        }.items():
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
        # The old wrapper needs only this metadata, not a functioning kernel.
        registry=self.root/'canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json'
        registry.parent.mkdir(parents=True)
        registry.write_text(json.dumps({'capabilities':{'python.source.change_impact.testselect.v1':{}}}))
        self.args={'source_root':'.','changed_paths':['pkg/core.py'],'output_path':'reports/selection.json'}

    def source_bytes(self):
        return {p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*.py')}

    def test_registry_inventory_alone_cannot_claim_a_successful_slice(self):
        with self.assertRaisesRegex(RuntimeError,'CHANGE_IMPACT_SOURCE_ROOT_MISSING'):
            alias.run({'source_root':'absent','output_path':'reports/selection.json'},self.root)
        self.assertFalse((self.root/'reports/selection.json').exists())

    def test_actual_selection_matches_kernel_and_preserves_source(self):
        before=self.source_bytes()
        result=alias.run(self.args,self.root)
        payload=(self.root/self.args['output_path']).read_bytes()
        report=json.loads(payload)
        self.assertEqual(result['candidate_test_count'],2)
        self.assertEqual(result['selected_test_count'],1)
        self.assertEqual(report['selected_tests'],['tests/test_core.py'])
        self.assertEqual(result['output_sha256'],hashlib.sha256(payload).hexdigest())
        self.assertTrue(result['output_verified'])
        for unsupported in ('speedup','selected_vs_candidate_ratio','never_miss','verified'):
            self.assertNotIn(unsupported,report)
        expected=kernel.run(self.args,self.root)
        self.assertEqual(result,expected)
        self.assertEqual((self.root/self.args['output_path']).read_bytes(),payload)
        self.assertEqual(self.source_bytes(),before)

    def test_replay_is_identical(self):
        first=alias.run(self.args,self.root)
        before=(self.root/self.args['output_path']).read_bytes()
        self.assertEqual(alias.run(self.args,self.root),first)
        self.assertEqual((self.root/self.args['output_path']).read_bytes(),before)

    def test_missing_change_input_refuses(self):
        with self.assertRaisesRegex(RuntimeError,'CHANGE_IMPACT_INPUT_REQUIRED'):
            alias.run({'source_root':'.','output_path':'reports/selection.json'},self.root)
        self.assertFalse((self.root/'reports/selection.json').exists())

    def test_source_and_hardlink_report_aliases_refuse_before_writes(self):
        import os
        source=self.root/'pkg/core.py'
        linked=self.root/'linked.json';os.link(source,linked)
        before=source.read_bytes()
        for output in ('pkg/core.py','linked.json'):
            with self.subTest(output=output), self.assertRaises(RuntimeError):
                alias.run(dict(self.args,output_path=output),self.root)
            self.assertEqual(source.read_bytes(),before)
            self.assertEqual(linked.read_bytes(),before)

    def test_changed_path_escape_refuses(self):
        with self.assertRaisesRegex(RuntimeError,'PATH_OUTSIDE_REPOSITORY'):
            alias.run(dict(self.args,changed_paths=['../outside.py']),self.root)
        self.assertFalse((self.root/'reports/selection.json').exists())

    def test_real_native_dispatch_returns_measured_selection(self):
        import shutil
        from canonical.runtime.live_brain_route_admission_v1 import run_adapter_locally
        with TemporaryDirectory(dir=ROOT/'canonical/astra_runtime/tmp',prefix='slice-dispatch-') as directory:
            work=Path(directory)
            for name in ('pkg','tests'):
                shutil.copytree(self.root/name,work/name)
            registry=json.loads((ROOT/'canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json').read_text())['capabilities']
            action={'type':'invoke_capability','args':{
                'capability_id':CID,'source_root':str(work),
                'changed_paths':[str(work/'pkg/core.py')],
                'output_path':str(work/'selection.json')},
                'expect':registry[CID]['action_template']['expect']}
            result=run_adapter_locally(registry[CID],action)
            self.assertEqual(result['candidate_test_count'],2)
            self.assertEqual(result['selected_test_count'],1)
            report=json.loads((work/'selection.json').read_text())
            self.assertEqual(report['selected_tests'],[(work/'tests/test_core.py').relative_to(ROOT).as_posix()])
            self.assertTrue(result['output_verified'])
            self.assertNotIn('verified',result)

    def test_live_registry_matches_real_kernel_contract(self):
        registry=json.loads((ROOT/'canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json').read_text())['capabilities']
        entry=registry[CID];real=registry['python.source.change_impact.testselect.v1']
        self.assertEqual(entry['requires'],[])
        self.assertEqual(entry['provides'],real['provides'])
        self.assertEqual(entry['result_fields'],real['result_fields'])
        self.assertEqual(entry['action_template']['expect'],real['action_template']['expect'])
        self.assertEqual(entry['action_template']['args'],dict(real['action_template']['args'],capability_id=CID))


if __name__=='__main__': unittest.main()
