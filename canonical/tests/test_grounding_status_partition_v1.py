"""Unbound candidates are diagnostic, not grounded effects or discovery blockers."""
import copy
import json
from pathlib import Path
import unittest
from canonical.tests import test_grounding_proposal_binding_contract as fixtures

ROOT=Path(__file__).resolve().parents[2]
GOAL='Fetch JSON from canonical/astra_runtime/state/example.json using url key source_url.'


class GroundingStatusPartitionTests(unittest.TestCase):
    def registry(self):
        live=json.loads((ROOT/'canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json').read_text())['capabilities']
        producer=copy.deepcopy(live['source.candidates.enumerate.stdlib'])
        producer['keywords']=['source']
        producer['action_template']['args']['capability_id']='unit.producer'
        consumer={
            'status':'VERIFIED_BOUND_CAPABILITY','incremental_spend_usd':0,
            'keywords':['consolidate'],'requires':['source.candidates.available'],
            'provides':['unit.consolidated'],'result_fields':['output_path'],
            'action_template':{'type':'invoke_capability','args':{
                'capability_id':'unit.consumer', 'input_path':'${input.input_path}',
                'output_path':'${input.output_path}',
            }},
            'proposal_bindings':{
                'input_path':{'type':'effect_result','effect':'source.candidates.available','field':'output_path','container':'scalar'},
                'output_path':{'type':'auto_path','suffix':'.json'},
            },
        }
        return {'unit.producer':producer,'unit.consumer':consumer}

    def ground(self,goal,registry):
        return fixtures.grounder.ground(goal,registry,compiler=fixtures.compiler,
            proposal_binder=fixtures.proposal_binder,root=ROOT,enforce_bindability=True)

    def test_unbound_candidate_does_not_count_or_block_discovery(self):
        result=self.ground(GOAL,self.registry())
        self.assertEqual(result['clauses'][0]['status'],'UNBOUND_INPUTS_NOT_GROUNDED')
        self.assertEqual(result['grounded_clause_count'],0)
        self.assertEqual(result['unresolved_clause_indexes'],[0])
        self.assertFalse(result['whole_goal_external_discovery_forbidden_if_any_bound_grounding'])

    def test_unbound_candidate_does_not_supply_downstream_effect(self):
        result=self.ground(GOAL+' Consolidate enumeration.',self.registry())
        self.assertEqual(result['clauses'][0]['status'],'UNBOUND_INPUTS_NOT_GROUNDED')
        second=result['clauses'][1]
        self.assertEqual(second['status'],'UNRESOLVED')
        self.assertEqual(second['candidates'],[])
        self.assertTrue(any('PROPOSAL_EFFECT_PROVIDER_MISSING' in row['error']
                            for row in second['rejected_unbindable_candidates']))
        self.assertEqual(result['grounded_clause_count'],0)
        self.assertEqual(result['unresolved_clause_indexes'],[0,1])

    def test_ready_producer_still_supplies_downstream_effect(self):
        registry=self.registry()
        registry['unit.producer']['proposal_bindings']={
            'goal':{'type':'literal','value':GOAL},
            'output_path':{'type':'auto_path','suffix':'.json'},
        }
        result=self.ground(GOAL+' Consolidate enumeration.',registry)
        self.assertEqual([row['status'] for row in result['clauses']],['GROUNDED','GROUNDED'])
        self.assertEqual(result['grounded_clause_count'],2)
        self.assertEqual(result['unresolved_clause_indexes'],[])
        self.assertTrue(result['whole_goal_external_discovery_forbidden_if_any_bound_grounding'])


if __name__=='__main__': unittest.main()
