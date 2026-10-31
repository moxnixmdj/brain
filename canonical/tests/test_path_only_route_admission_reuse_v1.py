"""Existing semantic evidence must constrain typed-contract admission too."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime import goal_compiler as compiler
from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.runtime import capability_selection_retrieval_v1 as selection
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry

ROOT=Path(__file__).resolve().parents[2]
DECISION='decision.synthesis.typed.stdlib'
INDEX='python.source.symbols.index.ast'


class PathOnlyRouteAdmissionReuseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory(dir=ROOT/'canonical/astra_runtime/tmp',prefix='route_boundary_')
        self.addCleanup(self.tmp.cleanup)
        self.work=Path(self.tmp.name)
        self.task_prefix=self.work.name
        self.addCleanup(self.cleanup_checkpoints)
        self.registry=compiler._platform_admissible_registry(dict(load_verified_registry()))
        self.body='def add(a,b): return a+b\ndef caller(): return add(1,2)\n'

    def cleanup_checkpoints(self):
        for path in (ROOT/'canonical/astra_runtime/state').glob(self.task_prefix+'__*'):
            if path.is_file():
                path.unlink()

    def fixture(self,name):
        directory=self.work/name;directory.mkdir(exist_ok=True)
        source=directory/'core.py';source.write_text(self.body)
        output=directory/'summary.txt'
        goal=f'Summarize the file {source.relative_to(ROOT)} into three sentences and save the summary to {output.relative_to(ROOT)}.'
        return source,output,goal

    def test_bound_file_slots_are_not_semantic_intent(self):
        for name in ('typed','decision','synthesis'):
            with self.subTest(name=name):
                source,output,goal=self.fixture(name)
                typed=selection.admit(goal,DECISION,self.registry[DECISION],ROOT)
                self.assertTrue(typed['admitted'],typed)
                self.assertTrue(typed['specific'])
                verdict=door.route_admission(goal,{'selected_capability':DECISION},self.registry)
                self.assertEqual(verdict['semantic_matched_tokens'],[])
                self.assertTrue(verdict['matched_from_paths_only'])
                self.assertFalse(verdict['admitted'],verdict)
                self.assertEqual(verdict['rule'],'R1_PATH_TOKENS_ONLY')
                self.assertEqual(source.read_text(),self.body)
                self.assertFalse(output.exists())

    def test_absolute_path_and_quoted_path_do_not_create_intent(self):
        source,output,_=self.fixture('typed')
        for spelling in (str(source),json.dumps(str(source))):
            goal=f'Summarize the file {spelling} into three sentences and save the summary to {output}.'
            verdict=door.route_admission(goal,{'selected_capability':DECISION},self.registry)
            self.assertFalse(verdict['admitted'],verdict)
            self.assertEqual(verdict['rule'],'R1_PATH_TOKENS_ONLY')

    def test_public_summary_does_not_execute_or_write(self):
        source,output,goal=self.fixture('typed')
        result=door.solve({'task_id':self.task_prefix+'__summary','goal':goal})
        self.assertFalse(result['pass'],result.get('status'))
        self.assertIs(result.get('executed'),False,result.get('route_admission'))
        self.assertFalse(output.exists())
        self.assertEqual(source.read_text(),self.body)

    def test_explicit_identifier_keeps_existing_authority(self):
        source,_,_=self.fixture('typed')
        goal=f'Run {INDEX} with source_root "{source.relative_to(ROOT)}".'
        compiled={'selected_capability':INDEX,
                  'front_compiler':{'rules_applied':['F15_EXPLICIT_CAPABILITY_ID_NAMED']}}
        verdict=door.route_admission(goal,compiled,self.registry)
        self.assertTrue(verdict['admitted'],verdict)
        self.assertEqual(verdict['admission_basis'],'EXPLICIT_CAPABILITY_ID_IN_GOAL')

    def test_structured_function_call_selects_and_executes_the_real_invoker(self):
        from canonical.runtime import goal_front_compiler_v1 as front
        payload=self.work/'payload.json';output=self.work/'result.json'
        data={'claim_text':'Orion budget is 40.',
              'evidence_text':'The audited ledger reports that Orion budget is 40.'}
        payload.write_text(json.dumps(data));before=payload.read_bytes()
        goal=('Call the function classify_support in canonical/runtime/bounded_claim_support.py '
              f'with the payload {payload.relative_to(ROOT)} and save the result to {output.relative_to(ROOT)}')
        compiled=front.compile_goal(goal,self.registry,ROOT)
        self.assertEqual(compiled['selected_capability'],'brain.module.function.invoke')
        self.assertIn('F17_RETRIEVAL_FIRST_TYPED_ADMISSION',compiled['front_compiler']['rules_applied'])
        result=door.solve({'task_id':self.task_prefix+'__function','goal':goal})
        self.assertTrue(result['pass'],result.get('status'))
        self.assertEqual(result['compiled_capability_id'],'brain.module.function.invoke')
        self.assertEqual(json.loads(output.read_text())['result']['relation'],'SUPPORTS')
        self.assertEqual(payload.read_bytes(),before)

    def test_supported_caller_analysis_still_executes(self):
        source,_,_=self.fixture('typed')
        goal=f'Find every caller of the function add in {source.relative_to(ROOT)}.'
        result=door.solve({'task_id':self.task_prefix+'__callers','goal':goal})
        self.assertTrue(result['pass'],result.get('status'))
        self.assertIs(result.get('executed'),True)
        self.assertEqual(source.read_text(),self.body)
        callers=set()
        for report in source.parent.glob('*.json'):
            callers.update(json.loads(report.read_text()).get('callers_of',{}).get('add',[]))
        self.assertEqual(callers,{'caller'})


if __name__=='__main__': unittest.main()
