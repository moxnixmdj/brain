import unittest
from canonical.runtime.m5_finite_causal_intervention import (
    CauseHypothesis,Intervention,select_intervention,update_after_intervention
)

class Tests(unittest.TestCase):
    def setUp(self):
        self.hs=[
            CauseHypothesis("h1","step1","repair1"),
            CauseHypothesis("h2","step2","repair2"),
            CauseHypothesis("h3","step3","repair3"),
            CauseHypothesis("h4","step4","repair4"),
        ]

    def test_balanced_intervention_preferred(self):
        interventions=[
            Intervention("split",{"h1":"rescue","h2":"rescue","h3":"no","h4":"no"},1),
            Intervention("one",{"h1":"rescue","h2":"no","h3":"no","h4":"no"},1),
        ]
        out=select_intervention(self.hs,interventions)
        self.assertEqual(out["status"],"SELECT")
        self.assertEqual(out["intervention_id"],"split")
        self.assertFalse(out["causal_authority"])

    def test_unauthorized_or_irreversible_intervention_is_not_used(self):
        out=select_intervention(self.hs,[
            Intervention("bad",{"h1":"a","h2":"b","h3":"c","h4":"d"},.1,authorized=False),
            Intervention("bad2",{"h1":"a","h2":"b","h3":"c","h4":"d"},.1,reversible=False),
        ])
        self.assertEqual(out["status"],"ESCALATE")

    def test_observation_can_reduce_model(self):
        p=Intervention("split",{"h1":"rescue","h2":"rescue","h3":"no","h4":"no"},1)
        out=update_after_intervention(self.hs,p,"rescue")
        self.assertEqual(out["status"],"CAUSAL_VERSION_SPACE_REDUCED")
        self.assertEqual(out["remaining_hypotheses"],["h1","h2"])

    def test_unique_outcome_identifies_relative_cause(self):
        p=Intervention("unique",{"h1":"a","h2":"b","h3":"c","h4":"d"},1)
        out=update_after_intervention(self.hs,p,"c")
        self.assertEqual(out["status"],"RELATIVE_CAUSE_IDENTIFIED")
        self.assertEqual(out["candidate_event_id"],"step3")
        self.assertEqual(out["repair_action_id"],"repair3")
        self.assertEqual(out["causal_authority"],"RELATIVE_TO_FROZEN_FINITE_MODEL_ONLY")

    def test_unmodeled_outcome_falsifies_causal_model(self):
        p=Intervention("p",{"h1":"a","h2":"b","h3":"c","h4":"d"},1)
        out=update_after_intervention(self.hs,p,"new")
        self.assertEqual(out["status"],"MODEL_FALSIFIED")
        self.assertFalse(out["causal_authority"])

    def test_incomplete_outcome_model_fails_closed(self):
        p=Intervention("p",{"h1":"a"},1)
        out=update_after_intervention(self.hs,p,"a")
        self.assertEqual(out["status"],"FAIL_CLOSED")

    def test_duplicate_hypothesis_or_intervention_fails_closed(self):
        dup=[CauseHypothesis("h","a"),CauseHypothesis("h","b")]
        self.assertEqual(select_intervention(dup,[])["status"],"FAIL_CLOSED")
        self.assertEqual(select_intervention(self.hs,[
            Intervention("x",{"h1":"a","h2":"b","h3":"c","h4":"d"}),
            Intervention("x",{"h1":"a","h2":"b","h3":"c","h4":"d"}),
        ])["status"],"FAIL_CLOSED")

if __name__=="__main__":
    unittest.main(verbosity=2)
