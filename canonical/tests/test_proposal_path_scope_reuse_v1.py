"""Reuse the existing typed scope binder; do not broaden file requests to trees."""
import copy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime import capability_proposal_generators as binder
from canonical.runtime import goal_compiler as compiler
from canonical.runtime import capability_planner as planner
from canonical.runtime.bound_capabilities import grounded_executable_composition as composer
from canonical.runtime.bound_capabilities import grounded_executable_composition_verify as verifier
from canonical.runtime.live_brain_route_admission_v1 import run_adapter_locally

ROOT=Path(__file__).resolve().parents[2]
IDS=('python.source.audit.ast','python.source.complexity.v1',
     'python.source.dead_code.v1','python.source.secret_scan.v1',
     'python.source.symbols.index.ast')


class ProposalPathScopeReuseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory(dir=ROOT/'canonical/astra_runtime/tmp',prefix='proposal_scope_')
        self.addCleanup(self.tmp.cleanup)
        self.work=Path(self.tmp.name)
        self.src=self.work/'src';self.src.mkdir()
        (self.src/'calc.py').write_text('def add(a,b): return a+b\n')
        (self.src/'neighbor.py').write_text('def neighbor(): return 9\n')
        self.registry=json.loads((ROOT/'canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json').read_text())['capabilities']
        self.output=(self.work/'report.json').relative_to(ROOT).as_posix()

    def goal(self,scope):
        return 'Index the Python source '+scope+' and write output to '+self.output

    def bind(self,goal,cid=IDS[-1]):
        return binder._bind_planned_inputs(goal,ROOT,compiler,'scope',cid,self.registry[cid],{})

    def compose(self,scope):
        goal=self.goal(scope)
        grounding={
            'schema':'PROJECT_BRAIN_PLAIN_GOAL_BOUND_GROUNDING_V1',
            'goal':goal,'goal_sha256':hashlib.sha256(goal.encode()).hexdigest(),
            'input_contract_bindability_enforced':True,'model_dependency_count':0,
            'unresolved_clause_indexes':[],
            'clauses':[{'index':0,'text':goal,'status':'GROUNDED',
                        'candidates':[{'capability_id':IDS[-1]}],
                        'output_contract':{'paths':[self.output]}}],
        }
        plan=composer.compose(goal,grounding,self.registry,compiler,ROOT)
        return goal,grounding,plan

    def test_five_registered_tools_bind_exact_file_or_directory(self):
        for cid in IDS:
            for path in (self.src/'calc.py',self.src):
                scope=path.relative_to(ROOT).as_posix()
                with self.subTest(cid=cid,scope=scope):
                    inputs,evidence=self.bind(self.goal(scope),cid)
                    self.assertEqual(inputs['source_root'],scope)
                    self.assertEqual(inputs['output_path'],self.output)
                    self.assertEqual(evidence['source_root']['type'],'path_file_or_dir')

    def test_actual_composed_index_execution_preserves_requested_scope(self):
        original=(self.src/'calc.py').read_bytes()
        for path,count in ((self.src/'calc.py',1),(self.src/'calc.py',1),(self.src,2)):
            scope=path.relative_to(ROOT).as_posix()
            with self.subTest(scope=scope):
                goal,grounding,plan=self.compose(scope)
                self.assertEqual(verifier.verify(goal,plan,grounding,self.registry,root=ROOT),(True,'VERIFIED'))
                actions=planner.plan_actions(plan['problem'])['actions']
                action=next(row for row in actions if row.get('type')=='invoke_capability')
                result=run_adapter_locally(self.registry[IDS[-1]],action)
                self.assertTrue(result['output_verified'])
                artifact=json.loads((ROOT/self.output).read_text())
                self.assertEqual(artifact['totals']['files'],count)
                if count==1:
                    self.assertEqual([row['path'] for row in artifact['modules']],[scope])
        self.assertEqual((self.src/'calc.py').read_bytes(),original)

    def test_absent_scope_is_not_invented_from_the_filesystem(self):
        with self.assertRaisesRegex(binder.CapabilityProposalFailure,'PROPOSAL_PATH_SCOPE_BINDING_FAILED'):
            self.bind(self.goal(''))

    def test_ambiguous_files_and_directories_are_refused(self):
        other=self.work/'other';other.mkdir()
        for paths in ((self.src/'calc.py',self.src/'neighbor.py'),(self.src,other)):
            scope=' and '.join(path.relative_to(ROOT).as_posix() for path in paths)
            with self.subTest(scope=scope):
                with self.assertRaisesRegex(binder.CapabilityProposalFailure,'PROPOSAL_PATH_SCOPE_BINDING_FAILED'):
                    self.bind(self.goal(scope))

    def test_outside_repository_scope_is_refused(self):
        with TemporaryDirectory(prefix='outside-scope-') as outside:
            path=Path(outside)/'secret.py';path.write_text('x=1\n')
            with self.assertRaisesRegex(binder.CapabilityProposalFailure,'PROPOSAL_PATH_SCOPE_BINDING_FAILED'):
                self.bind(self.goal(str(path)))

    def test_rehashed_plan_cannot_broaden_a_file_to_its_parent(self):
        goal,grounding,plan=self.compose((self.src/'calc.py').relative_to(ROOT).as_posix())
        plan=copy.deepcopy(plan)
        cap=plan['problem']['capabilities'][0]
        cap['inputs']['source_root']=self.src.relative_to(ROOT).as_posix()
        cap['proposal_binding_evidence']={}
        cap['action']=verifier._render(self.registry[IDS[-1]]['action_template'],cap['inputs'])
        cap['action_sha256']=verifier._sha(cap['action'])
        ok,reason=verifier.verify(goal,plan,grounding,self.registry,root=ROOT)
        self.assertFalse(ok)
        self.assertIn('PROPOSAL_PATH_SCOPE_MISMATCH',reason)

    def test_structural_scope_validation_uses_explicit_trusted_root(self):
        with TemporaryDirectory(prefix='trusted-scope-') as directory:
            base=Path(directory)
            source=base/base.name/'calc.py'
            source.parent.mkdir();source.write_text('x=1\n')
            relative=source.relative_to(base).as_posix()
            goal='Index the Python source '+relative
            entry=dict(self.registry[IDS[-1]])
            entry['proposal_bindings']={'source_root':entry['proposal_bindings']['source_root']}
            inputs={'source_root':relative}
            self.assertEqual(verifier._validate_declared_bindings(
                goal,'scope',entry,inputs,root=base),(True,'VERIFIED'))
            ok,reason=verifier._validate_declared_bindings(
                goal,'scope',entry,inputs,root=ROOT)
            self.assertFalse(ok)
            self.assertIn('PROPOSAL_PATH_SCOPE_BINDING_FAILED',reason)

    def test_scope_cannot_also_be_the_report_destination(self):
        scope=(self.src/'calc.py').relative_to(ROOT).as_posix()
        goal=self.goal(scope).replace(self.output,scope)
        with self.assertRaisesRegex(binder.CapabilityProposalFailure,'PROPOSAL_PATH_SCOPE_BINDING_FAILED'):
            self.bind(goal)


if __name__=='__main__': unittest.main()
