from __future__ import annotations
import copy, unittest
from canonical.runtime.synthesis_proof_obligation_delta_application_v1 import evaluate, load

class SynthesisProofObligationDeltaApplicationTests(unittest.TestCase):
    def test_live_input_matches_exact_residual(self):
        out=evaluate(load())
        self.assertTrue(out["pass"],out)
        self.assertIsNone(out["scope_relation"])
        self.assertEqual(out["covered_atom_count"],7)
        self.assertEqual(out["residual"]["missing_scope_components"],["population:frozen_matched_synthesis_portfolio"])
        self.assertEqual(out["residual"]["missing_atoms"],["metric:matched_quality"])
        self.assertEqual(set(out["residual"]["missing_metric_bindings"]),{"matched_quality_noninferiority","required_claim_coverage_noninferiority"})

    def test_plain_receipt_string_fails_hardened_compiler(self):
        d=copy.deepcopy(load())
        d["atom_bindings"][0]["receipt"]="canonical/verification/fake.json"
        out=evaluate(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["raw_compiler_result"]["status"],"FAIL_CLOSED")

    def test_fake_scope_binding_fails_without_content_addressed_receipt(self):
        d=copy.deepcopy(load())
        d["scope_bindings"]=[{
          "witness_component":"population:p3_t1_t3_terminal_observations",
          "target_component":"population:frozen_matched_synthesis_portfolio",
          "relation":"EXACT","verified":True,"independent":True,
          "receipt":"receipt://fake"
        }]
        out=evaluate(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["raw_compiler_result"]["status"],"FAIL_CLOSED")

    def test_invented_metric_binding_fails_endpoint_check(self):
        d=copy.deepcopy(load())
        d["metric_bindings"]=[{
          "witness_metric":"invented_quality",
          "target_metric":"matched_quality_noninferiority",
          "verified":True,"independent":True,
          "receipt":{"path":"canonical/verification/fake.json","git_blob_sha":"a"*40}
        }]
        out=evaluate(d)
        self.assertFalse(out["pass"])
        self.assertEqual(out["raw_compiler_result"]["status"],"FAIL_CLOSED")

if __name__=="__main__": unittest.main(verbosity=2)
