import unittest
from canonical.runtime.acceptance_capability_source_gate_v1 import evaluate

class Tests(unittest.TestCase):
    def test_fully_owned_route_passes(self):
        out=evaluate({
          "benchmark_harness_zero_cost":True,
          "scorer_frozen":True,
          "brain_candidate_bound":True,
          "candidate_donor_independent":True,
          "opaque_external_capability_provider":False,
          "model_dependency_count":0,
          "incremental_spend_usd":0,
        })
        self.assertTrue(out["pass"],out)

    def test_external_model_dependency_blocks(self):
        out=evaluate({
          "benchmark_harness_zero_cost":True,
          "scorer_frozen":True,
          "brain_candidate_bound":True,
          "candidate_donor_independent":False,
          "opaque_external_capability_provider":True,
          "model_dependency_count":1,
          "incremental_spend_usd":0,
        })
        self.assertFalse(out["pass"])
        self.assertIn("MODEL_DEPENDENCY_COUNT_NOT_ZERO",out["errors"])
        self.assertIn("CANDIDATE_DONOR_INDEPENDENCE_NOT_PROVEN",out["errors"])

    def test_free_harness_without_candidate_blocks(self):
        out=evaluate({
          "benchmark_harness_zero_cost":True,
          "scorer_frozen":True,
          "brain_candidate_bound":False,
          "candidate_donor_independent":False,
          "opaque_external_capability_provider":False,
          "model_dependency_count":None,
          "incremental_spend_usd":0,
        })
        self.assertFalse(out["pass"])
        self.assertIn("BRAIN_CANDIDATE_NOT_BOUND",out["errors"])

    def test_nonzero_spend_blocks(self):
        out=evaluate({
          "benchmark_harness_zero_cost":True,
          "scorer_frozen":True,
          "brain_candidate_bound":True,
          "candidate_donor_independent":True,
          "opaque_external_capability_provider":False,
          "model_dependency_count":0,
          "incremental_spend_usd":0.01,
        })
        self.assertFalse(out["pass"])
        self.assertIn("INCREMENTAL_SPEND_NOT_ZERO",out["errors"])

if __name__=="__main__": unittest.main()
