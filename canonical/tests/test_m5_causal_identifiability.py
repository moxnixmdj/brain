import unittest
from canonical.runtime.m5_causal_identifiability import construct_nonidentifiability_witness, verify_nonidentifiability_witness

class Tests(unittest.TestCase):
    def test_same_observations_distinct_causes(self):
        a,b=construct_nonidentifiability_witness()
        self.assertEqual(a.observable_trace,b.observable_trace)
        self.assertNotEqual(a.root_cause,b.root_cause)

    def test_no_extra_causal_information(self):
        a,b=construct_nonidentifiability_witness()
        self.assertFalse(a.validated_causal_graph_available)
        self.assertFalse(b.validated_causal_graph_available)
        self.assertFalse(a.intervention_or_replay_available)
        self.assertFalse(b.intervention_or_replay_available)

    def test_counterexample_verifies(self):
        out=verify_nonidentifiability_witness()
        self.assertEqual(out["status"],"PASS",out)
        self.assertTrue(out["same_observable_trace"])
        self.assertTrue(out["distinct_root_causes"])

if __name__=="__main__":
    unittest.main(verbosity=2)
