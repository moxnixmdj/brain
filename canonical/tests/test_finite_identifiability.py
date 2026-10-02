import unittest
from canonical.runtime.finite_identifiability import (
    Hypothesis,Experiment,filter_version_space,select_discriminator,equivalence_classes
)

class Tests(unittest.TestCase):
    def setUp(self):
        self.hs=[Hypothesis("h1"),Hypothesis("h2"),Hypothesis("h3"),Hypothesis("h4")]

    def test_balanced_beats_weaker(self):
        ex=[
            Experiment("split",{"h1":"x","h2":"x","h3":"y","h4":"y"},1),
            Experiment("weak",{"h1":"x","h2":"y","h3":"y","h4":"y"},1),
        ]
        self.assertEqual(select_discriminator(self.hs,ex)["experiment_id"],"split")

    def test_equal_information_prefers_cheaper(self):
        outcomes={"h1":"x","h2":"x","h3":"y","h4":"y"}
        ex=[Experiment("expensive",outcomes,100),Experiment("cheap",outcomes,1)]
        out=select_discriminator(self.hs,ex)
        self.assertEqual(out["experiment_id"],"cheap")
        self.assertEqual(out["experiment_cost"],1.0)

    def test_diagnostic_power_precedes_cost(self):
        ex=[
            Experiment("cheap_weak",{"h1":"x","h2":"y","h3":"y","h4":"y"},0.01),
            Experiment("strong",{"h1":"a","h2":"b","h3":"c","h4":"d"},5),
        ]
        self.assertEqual(select_discriminator(self.hs,ex)["experiment_id"],"strong")

    def test_filter_resolves(self):
        ex=[Experiment("p",{"h1":"a","h2":"b","h3":"c","h4":"d"},1)]
        out=filter_version_space(self.hs,ex,{"p":"c"})
        self.assertEqual(out["status"],"RESOLVED")
        self.assertEqual(out["remaining_hypotheses"],["h3"])

    def test_unmodeled_observation_falsifies_model(self):
        ex=[Experiment("p",{"h1":"a","h2":"b","h3":"c","h4":"d"},1)]
        out=filter_version_space(self.hs,ex,{"p":"z"})
        self.assertEqual(out["status"],"MODEL_FALSIFIED")

    def test_nonidentifiable_returns_witness(self):
        ex=[
            Experiment("p",{"h1":"x","h2":"x","h3":"y","h4":"y"},1),
        ]
        out=select_discriminator(self.hs,ex,{"p":"x"})
        self.assertEqual(out["status"],"NONIDENTIFIABLE_UNDER_AUTHORIZED_EXPERIMENTS")
        self.assertEqual(out["remaining_hypotheses"],["h1","h2"])
        self.assertIn(["h1","h2"],out["equivalence_classes"])

    def test_incomplete_outcome_model_fails_closed(self):
        ex=[Experiment("p",{"h1":"x"},1)]
        self.assertEqual(select_discriminator(self.hs,ex)["status"],"FAIL_CLOSED")

    def test_duplicate_hypothesis_fails_closed(self):
        hs=[Hypothesis("h1"),Hypothesis("h1")]
        ex=[Experiment("p",{"h1":"x"},1)]
        self.assertEqual(select_discriminator(hs,ex)["status"],"FAIL_CLOSED")

    def test_used_experiment_not_selected_again(self):
        ex=[
            Experiment("p1",{"h1":"a","h2":"a","h3":"b","h4":"b"},1),
            Experiment("p2",{"h1":"x","h2":"y","h3":"x","h4":"y"},1),
        ]
        out=select_discriminator(self.hs,ex,{"p1":"a"})
        self.assertEqual(out["experiment_id"],"p2")
        self.assertEqual(out["remaining_hypotheses"],["h1","h2"])

if __name__=="__main__":
    unittest.main()
