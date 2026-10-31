"""Adversarial structural-plan checks using the existing composer and real binder.

Registry fixtures describe unit-test contracts, not executed software work.
"""
import copy
import unittest
from canonical.tests import test_grounded_executable_composition as fixtures


class CompositionBindingEvidenceTests(unittest.TestCase):
    def build(self, ambiguous=False):
        base=fixtures.GroundedExecutableCompositionTests()
        registry=base.registry()
        for cid in ('produce.alpha','produce.alpha.fast'):
            registry[cid]['provides'].append('artifact.beta.ready')
            registry[cid]['proposal_bindings']={
                'output_path':{'type':'literal','value':'out/a.json'},
            }
        consumer=registry['verify.alpha']
        consumer['requires'].append('artifact.beta.ready')
        consumer['proposal_bindings']={key:{
            'type':'effect_result','effect':effect,'field':'output_path',
            'container':'list' if ambiguous else 'scalar',
        } for key,effect in (
            ('input_path','artifact.alpha.ready'),
            ('other_path','artifact.beta.ready'),
        )}
        consumer['proposal_bindings']['output_path']={'type':'auto_path','suffix':'.json'}
        consumer['action_template']['args'].update({
            key:'${input.'+key+'}' for key in consumer['proposal_bindings']
        })
        grounding=base.grounding(ambiguous=ambiguous)
        plan=fixtures.composition.compose(
            grounding['goal'],grounding,registry,fixtures.real_compiler,fixtures.REPO_ROOT,
        )
        return registry,grounding,plan

    def check(self,registry,grounding,plan):
        return fixtures.verifier.verify(grounding['goal'],plan,grounding,registry)

    def rerender(self,registry,cap):
        cap['action']=fixtures.verifier._render(
            registry[cap['source_capability_id']]['action_template'],cap['inputs'],
        )
        cap['action_sha256']=fixtures.verifier._sha(cap['action'])

    def test_honest_declared_bindings_are_accepted(self):
        self.assertEqual(self.check(*self.build()),(True,'VERIFIED'))

    def test_valid_requirement_aliases_are_accepted(self):
        self.assertEqual(self.check(*self.build(ambiguous=True)),(True,'VERIFIED'))

    def test_missing_trace_does_not_invalidate_honest_bindings(self):
        registry,grounding,plan=self.build()
        for cap in plan['problem']['capabilities']:
            cap.pop('proposal_binding_evidence',None)
        self.assertEqual(self.check(registry,grounding,plan),(True,'VERIFIED'))

    def test_missing_or_empty_trace_cannot_hide_changed_generated_path(self):
        registry,grounding,original=self.build()
        for trace in ('absent',{},None,False):
            with self.subTest(trace=trace):
                plan=copy.deepcopy(original)
                cap=plan['problem']['capabilities'][-1]
                if trace=='absent': cap.pop('proposal_binding_evidence',None)
                else: cap['proposal_binding_evidence']=trace
                cap['inputs']['output_path']='arbitrary.json'
                self.rerender(registry,cap)
                ok,reason=self.check(registry,grounding,plan)
                self.assertFalse(ok)
                self.assertIn('PROPOSAL_AUTO_PATH_MISMATCH',reason)

    def test_missing_trace_cannot_hide_changed_literal(self):
        registry,grounding,plan=self.build()
        cap=plan['problem']['capabilities'][0]
        cap['proposal_binding_evidence']={}
        cap['inputs']['output_path']='arbitrary.json'
        self.rerender(registry,cap)
        ok,reason=self.check(registry,grounding,plan)
        self.assertFalse(ok)
        self.assertIn('PROPOSAL_LITERAL_MISMATCH',reason)

    def test_other_required_effect_is_not_the_declared_input_effect(self):
        for ambiguous in (False,True):
            with self.subTest(ambiguous=ambiguous):
                registry,grounding,plan=self.build(ambiguous=ambiguous)
                cap=plan['problem']['capabilities'][-1]
                source=cap['inputs']['input_path']
                other=cap['inputs']['other_path']
                if ambiguous: source,other=source[0],other[0]
                source['$effect_result']['effect']=other['$effect_result']['effect']
                self.rerender(registry,cap)
                ok,reason=self.check(registry,grounding,plan)
                self.assertFalse(ok)
                self.assertIn('PROPOSAL_EFFECT_RESULT_EFFECT_MISMATCH',reason)


if __name__=='__main__': unittest.main()
