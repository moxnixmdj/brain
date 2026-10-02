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
    def test_equal_information_prefers_cheaper_probe(self):
        same={"h1":"x","h2":"x","h3":"y","h4":"y"}
        ps=[Probe("expensive",same,100),Probe("cheap",same,1)]
        out=select_probe(self.hs,ps)
        self.assertEqual(out["probe_id"],"cheap")
        self.assertEqual(out["probe_cost"],1.0)

    def test_more_informative_probe_beats_cheaper_weaker_probe(self):
        ps=[
          Probe("cheap_weak",{"h1":"x","h2":"y","h3":"y","h4":"y"},0.01),
          Probe("strong",{"h1":"x","h2":"x","h3":"y","h4":"y"},1),
        ]
        self.assertEqual(select_probe(self.hs,ps)["probe_id"],"strong")

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
