"""Real registry dataflow: index -> cached edit intent, without invented inputs."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime import goal_compiler as compiler
from canonical.runtime import capability_proposal_generators as binder
from canonical.runtime import capability_planner as planner
from canonical.runtime import astra_runtime as runtime
from canonical.runtime.bound_capabilities import plain_goal_bound_grounding as grounder
from canonical.runtime.bound_capabilities import grounded_executable_composition as composer
from canonical.runtime.bound_capabilities import grounded_executable_composition_verify as verifier
from canonical.runtime.live_brain_route_admission_v1 import run_adapter_locally

ROOT=Path(__file__).resolve().parents[2]
INDEX='python.source.symbols.index.ast'
INTENT='python.issue.natural_language.parse_edit_intent.v1'


class IndexIntentCompositionReuseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory(dir=ROOT/'canonical/astra_runtime/tmp',prefix='index_intent_chain_')
        self.addCleanup(self.tmp.cleanup)
        self.work=Path(self.tmp.name)
        self.src=self.work/'src'
        (self.src/'pkg').mkdir(parents=True)
        (self.src/'pkg/core.py').write_text('def helper(x): return x+1\n')
        self.issue=self.work/'issue.json'
        self.issue.write_text(json.dumps({'issue_id':'CHAIN','title':'Rename helper to compute in pkg/core.py'}))
        self.issue_bytes=self.issue.read_bytes()
        self.raw=json.loads((ROOT/'canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json').read_text())['capabilities']
        self.registry=self.raw
        self.source=self.src.relative_to(ROOT).as_posix()
        self.issue_rel=self.issue.relative_to(ROOT).as_posix()

    def parser_goal(self):
        return f'Run {INTENT} with issue_path "{self.issue_rel}" and source_root "{self.source}"'

    def build(self,explicit=False,quoted=False,absolute=False):
        first=f'Run {INDEX} with source_root "{self.source}"'
        second=self.parser_goal()
        if explicit:
            def destination(name):
                path=self.work/name
                value=str(path) if absolute else path.relative_to(ROOT).as_posix()
                return json.dumps(value) if quoted else value
            first+=' with output to '+destination('index.json')
            second+=' with output to '+destination('intent.json')
        goal=first+'. '+second+'.'
        grounding=grounder.ground(goal,self.registry,compiler=compiler,
            proposal_binder=binder,root=ROOT,enforce_bindability=True)
        self.assertEqual([c['status'] for c in grounding['clauses']],['GROUNDED','GROUNDED'],grounding)
        plan=composer.compose(goal,grounding,self.registry,compiler,ROOT)
        self.assertEqual(verifier.verify(goal,plan,grounding,self.registry,root=ROOT),(True,'VERIFIED'))
        actions=[a for a in planner.plan_actions(plan['problem'])['actions'] if a.get('type')!='finish']
        self.assertEqual([a['args']['capability_id'] for a in actions],[INDEX,INTENT])
        for action in actions:
            path=ROOT/action['args']['output_path']
            self.addCleanup(lambda path=path:path.unlink(missing_ok=True))
        return goal,grounding,plan,actions

    def execute(self,actions):
        trace=[]
        index_bytes=None
        for action in actions:
            bound=runtime._resolve_result_refs(action,trace)
            result=run_adapter_locally(self.registry[bound['args']['capability_id']],bound)
            trace.append({'result':result})
            if len(trace)==1:
                index_bytes=(ROOT/result['output_path']).read_bytes()
        self.assertEqual((ROOT/trace[0]['result']['output_path']).read_bytes(),index_bytes)
        self.assertTrue(trace[-1]['result']['complete'])
        self.assertTrue(trace[-1]['result']['cache_used'])
        artifact=json.loads((ROOT/trace[-1]['result']['output_path']).read_text())
        self.assertEqual(artifact['edits'],[{'op':'rename_symbol','module':'pkg/core.py','name':'helper','new_name':'compute'}])
        self.assertEqual(self.issue.read_bytes(),self.issue_bytes)
        self.assertEqual((self.src/'pkg/core.py').read_text(),'def helper(x): return x+1\n')
        return trace

    def test_real_registry_declares_exact_index_provenance(self):
        spec=self.registry[INTENT].get('proposal_bindings',{}).get('index_path')
        self.assertEqual(spec,{'type':'effect_result','effect':INDEX,'field':'output_path','container':'scalar'})

    def test_generated_reports_execute_and_replay_without_overwriting_issue(self):
        _,_,_,actions=self.build()
        first=self.execute(actions)
        before=(ROOT/first[-1]['result']['output_path']).read_bytes()
        _,_,_,replayed=self.build()
        self.assertEqual(replayed,actions)
        second=self.execute(replayed)
        self.assertEqual((ROOT/second[-1]['result']['output_path']).read_bytes(),before)

    def test_explicit_output_roles_are_preserved_and_verified(self):
        _,_,_,actions=self.build(explicit=True)
        self.assertEqual(actions[0]['args']['output_path'],(self.work/'index.json').relative_to(ROOT).as_posix())
        self.assertEqual(actions[1]['args']['output_path'],(self.work/'intent.json').relative_to(ROOT).as_posix())
        self.execute(actions)

    def test_quoted_absolute_destinations_execute_and_recompose(self):
        _,_,_,actions=self.build(explicit=True,quoted=True,absolute=True)
        self.assertEqual(actions[0]['args']['output_path'],(self.work/'index.json').relative_to(ROOT).as_posix())
        self.assertEqual(actions[1]['args']['output_path'],(self.work/'intent.json').relative_to(ROOT).as_posix())
        self.execute(actions)
        _,_,_,replayed=self.build(explicit=True,quoted=True,absolute=True)
        self.assertEqual(replayed,actions)
        self.execute(replayed)

    def test_missing_producer_cannot_be_replaced_by_a_guessed_cache(self):
        result=grounder.ground(self.parser_goal(),{INTENT:self.registry[INTENT]},
            compiler=compiler,proposal_binder=binder,root=ROOT,enforce_bindability=True)
        self.assertEqual(result['grounded_clause_count'],0)
        self.assertEqual(result['clauses'][0]['candidates'],[])
        self.assertTrue(any('PROPOSAL_EFFECT_PROVIDER_MISSING' in row['error']
            for row in result['clauses'][0]['rejected_unbindable_candidates']))

    def test_ambiguous_stated_outputs_refuse_instead_of_choosing(self):
        goal=f'Run {INDEX} with source_root "{self.source}"'
        goal+=' with output to '+(self.work/'one.json').relative_to(ROOT).as_posix()
        goal+=' with output to '+(self.work/'two.json').relative_to(ROOT).as_posix()
        with self.assertRaisesRegex(binder.CapabilityProposalFailure,'PROPOSAL_OUTPUT_SCOPE_AMBIGUOUS'):
            binder._bind_planned_inputs(goal,ROOT,compiler,'ambiguous',INDEX,self.registry[INDEX],{})
        inputs={'source_root':self.source,'output_path':(self.work/'one.json').relative_to(ROOT).as_posix()}
        self.assertEqual(verifier._validate_declared_bindings(goal,'ambiguous',self.registry[INDEX],inputs,root=ROOT),
            (False,'PROPOSAL_OUTPUT_SCOPE_AMBIGUOUS:ambiguous:output_path'))

    def test_filename_containing_input_key_does_not_state_index_role(self):
        named=self.work/'index_path_demo'
        named.mkdir()
        issue=named/'issue.json'
        issue.write_bytes(self.issue_bytes)
        self.issue_rel=issue.relative_to(ROOT).as_posix()
        self.test_missing_producer_cannot_be_replaced_by_a_guessed_cache()

    def test_source_change_between_stages_refuses_the_cached_index(self):
        _,_,_,actions=self.build()
        first=run_adapter_locally(self.registry[INDEX],actions[0])
        (self.src/'pkg/core.py').write_text('def other(): return 2\n')
        second=runtime._resolve_result_refs(actions[1],[{'result':first}])
        with self.assertRaisesRegex(SystemExit,'INDEX_CACHE_SOURCE_STALE'):
            run_adapter_locally(self.registry[INTENT],second)
        self.assertFalse((ROOT/second['args']['output_path']).exists())
        self.assertEqual(self.issue.read_bytes(),self.issue_bytes)

    def test_rehashed_literal_cannot_replace_the_required_index_reference(self):
        goal,grounding,plan,_=self.build()
        cap=plan['problem']['capabilities'][-1]
        cap['inputs']['index_path']=self.issue_rel
        cap['proposal_binding_evidence']={}
        cap['action']=verifier._render(self.registry[INTENT]['action_template'],cap['inputs'])
        cap['action_sha256']=verifier._sha(cap['action'])
        ok,reason=verifier.verify(goal,plan,grounding,self.registry,root=ROOT)
        self.assertFalse(ok)
        self.assertIn('PROPOSAL_EFFECT_RESULT_MISSING',reason)

    def test_auto_output_does_not_treat_an_input_as_a_stated_destination(self):
        # Controlled declaration fixture isolates the output-role bug before
        # the real registry is wired. It does not register or execute a tool.
        entry=copy.deepcopy(self.registry[INTENT])
        entry['proposal_bindings']={
            'issue_path':{'type':'path_file_or_dir'},
            'source_root':{'type':'path_file_or_dir'},
            'index_path':{'type':'effect_result','effect':INDEX,'field':'output_path','container':'scalar'},
            'output_path':{'type':'auto_path','suffix':'.json'},
        }
        entry['proposal_bindings']['source_root']={'type':'literal','value':self.source}
        goal=f'Run {INTENT} with issue_path "{self.issue_rel}"'
        inputs,_=binder._bind_planned_inputs(goal,ROOT,compiler,'isolated',INTENT,
            entry,{INDEX:('index',self.registry[INDEX])})
        self.assertNotEqual(inputs['output_path'],self.issue_rel)
        self.assertTrue(inputs['output_path'].startswith('canonical/astra_runtime/tmp/auto_proposal/'))


if __name__=='__main__': unittest.main()
