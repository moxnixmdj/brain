import inspect
import unittest

from canonical.runtime import trajectory_failure_typed_ir_candidate_v5 as c
from canonical.runtime import trajectory_failure_typed_ir_proof_v5 as p

class TrajectoryFailureTypedIRV5Tests(unittest.TestCase):
    def test_full_cross_product_scope_and_intervention_suite(self):
        cases=p.suite_cases()
        self.assertEqual(len(cases),6*8*4)
        domains=set()
        kinds=set()
        patterns=set()
        rescue_passes=0
        for case in cases:
            public=p.public_task(case)
            self.assertNotIn("_oracle",public)
            out=c.solve(public)
            verdict=p.score_case(case,out)
            self.assertTrue(verdict["pass"],(case["seed"],case["_oracle"],out,verdict))
            domains.add(case["task"]["domain"])
            patterns.add(case["_oracle"]["status"])
            for ks in case["_oracle"]["mechanisms"].values():
                kinds.update(ks)
            if case["_oracle"]["status"]!="AMBIGUOUS":
                self.assertTrue(verdict["post_intervention_terminal_rescue"])
                rescue_passes+=1
        self.assertEqual(domains,set(p.DOMAINS))
        self.assertEqual(kinds,set(p.KINDS))
        self.assertIn("SCOPE",kinds)
        self.assertEqual(patterns,{"IDENTIFIED","INTERACTION","AMBIGUOUS"})
        self.assertEqual(rescue_passes,6*8*3)

    def test_scope_is_first_class_not_authority_alias(self):
        case=p.generate_case(3001,pattern="DELAYED",domain="BROWSER",kind="SCOPE")
        out=c.solve(p.public_task(case))
        self.assertEqual(out["status"],"IDENTIFIED")
        self.assertEqual(out["mechanism_classes"],["SCOPE"])
        self.assertNotIn("AUTHORITY",out["mechanism_classes"])
        verdict=p.score_case(case,out)
        self.assertTrue(verdict["pass"],verdict)
        self.assertTrue(verdict["post_intervention_terminal_rescue"])

    def test_delayed_scope_repair_rescues_but_symptom_does_not(self):
        case=p.generate_case(3002,pattern="DELAYED",domain="TOOL_API",kind="SCOPE")
        out=c.solve(p.public_task(case))
        verdict=p.score_case(case,out)
        self.assertTrue(verdict["pass"],verdict)
        self.assertTrue(p.execute_hidden_intervention(case,out["repair_targets"])["terminal_success"])
        symptom=case["_oracle"]["symptom_repairs"]
        self.assertFalse(p.execute_hidden_intervention(case,symptom)["terminal_success"])

    def test_interaction_requires_full_joint_repair_set(self):
        case=p.generate_case(3003,pattern="INTERACTION",domain="RESEARCH",kind="SCOPE")
        out=c.solve(p.public_task(case))
        self.assertEqual(out["status"],"INTERACTION")
        verdict=p.score_case(case,out)
        self.assertTrue(verdict["pass"],verdict)
        repairs=out["repair_targets"]
        self.assertGreaterEqual(len(repairs),2)
        self.assertTrue(p.execute_hidden_intervention(case,repairs)["terminal_success"])
        for i in range(len(repairs)):
            partial=repairs[:i]+repairs[i+1:]
            self.assertFalse(p.execute_hidden_intervention(case,partial)["terminal_success"])

    def test_hidden_intervention_oracle_not_candidate_visible(self):
        case=p.generate_case(3004,pattern="SINGLE",domain="FILESYSTEM",kind="SCOPE")
        public=p.public_task(case)
        self.assertNotIn("_oracle",public)
        self.assertNotIn("causal_repairs",repr(public))
        src=inspect.getsource(c)
        self.assertNotIn("trajectory_failure_typed_ir_proof_v5",src)
        self.assertNotIn("_oracle",src)

    def test_wrong_scope_repair_fails_hidden_rescue(self):
        case=p.generate_case(3005,pattern="SINGLE",domain="ARTIFACT",kind="SCOPE")
        out=c.solve(p.public_task(case))
        bad=dict(out)
        bad["repair_targets"]=["restore:A1:AUTHORITY"]
        verdict=p.score_case(case,bad)
        self.assertFalse(verdict["pass"])
        self.assertEqual(verdict["reason"],"FALSIFIABLE_REPAIR_TARGET_WRONG")

    def test_ambiguous_world_preserves_nonidentifiability(self):
        case=p.generate_case(3006,pattern="AMBIGUOUS",domain="CODE",kind="SCOPE")
        out=c.solve(p.public_task(case))
        verdict=p.score_case(case,out)
        self.assertTrue(verdict["pass"],verdict)
        self.assertEqual(out["status"],"AMBIGUOUS")
        self.assertIsNone(out["cause_action_id"])
        self.assertIsNone(verdict["post_intervention_terminal_rescue"])

if __name__=="__main__":
    unittest.main(verbosity=2)
