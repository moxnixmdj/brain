import unittest
from canonical.runtime.finite_capability_diagnosis import Hypothesis,Probe,select_probe,update_version_space

class FiniteCapabilityDiagnosisTests(unittest.TestCase):
    def setUp(self):
        self.hs=[Hypothesis("h1",frozenset({"a"})),Hypothesis("h2",frozenset({"b"})),Hypothesis("h3",frozenset({"c"})),Hypothesis("h4",frozenset({"d"}))]
    def test_balanced_probe_preferred(self):
        ps=[
          Probe("split",{"h1":"x","h2":"x","h3":"y","h4":"y"},1),
          Probe("one_vs_rest",{"h1":"x","h2":"y","h3":"y","h4":"y"},1),
        ]
        self.assertEqual(select_probe(self.hs,ps)["probe_id"],"split")
    def test_nondiscriminating_probe_rejected(self):
        p=Probe("p",{"h1":"x","h2":"x","h3":"x","h4":"x"},1)
        self.assertEqual(select_probe(self.hs,[p])["status"],"ESCALATE")
    def test_update_resolves(self):
        p=Probe("p",{"h1":"x","h2":"y","h3":"z","h4":"w"},1)
        o=update_version_space(self.hs,p,"z")
        self.assertEqual(o["status"],"RESOLVED"); self.assertEqual(o["remaining_hypotheses"],["h3"])
    def test_unmodeled_outcome_falsifies_model(self):
        p=Probe("p",{"h1":"x","h2":"y","h3":"z","h4":"w"},1)
        self.assertEqual(update_version_space(self.hs,p,"new")["status"],"MODEL_FALSIFIED")
    def test_incomplete_outcome_model_fails_closed(self):
        p=Probe("p",{"h1":"x"},1)
        self.assertEqual(update_version_space(self.hs,p,"x")["status"],"FAIL_CLOSED")
if __name__=="__main__": unittest.main()
