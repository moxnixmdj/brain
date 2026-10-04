from __future__ import annotations
import unittest
from canonical.runtime.root3_scope_certificate_compiler_v1 import evaluate_certificate, compile_state

class TestRoot3ScopeCertificateCompilerV1(unittest.TestCase):
    def test_inductive_certificate_closes(self):
        c={"target_id":"AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION","mode":"INDUCTIVE_INVARIANT",
           "initial_implies_invariant":True,"invariant_preserved_by_all_allowed_transitions":True,
           "invariant_implies_target_property":True,"transition_scope_exact_or_superset":True}
        self.assertTrue(evaluate_certificate(c)["closed"])

    def test_examples_do_not_close(self):
        c={"target_id":"AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION","mode":"INDUCTIVE_INVARIANT",
           "initial_implies_invariant":True,"invariant_preserved_by_all_allowed_transitions":True,
           "invariant_implies_target_property":True,"transition_scope_exact_or_superset":True,
           "representative_examples_only":True}
        self.assertFalse(evaluate_certificate(c)["closed"])

    def test_residual_observation_requires_authority(self):
        c={"target_id":"FINANCE_UNCOVERED_SCOPE_AUDIT","mode":"EXACT_RESIDUAL_OBSERVATION",
           "residual_content_addressed_exhaustive":True,"zero_reality_fixed_point_reached":True,
           "fresh_reality_authorized":False,"all_residual_leaves_independently_verified":True}
        self.assertFalse(evaluate_certificate(c)["closed"])

    def test_empty_state_preserves_all_current_targets(self):
        out=compile_state([])
        self.assertEqual(out["target_count"],10)
        self.assertEqual(out["closed_count"],0)
        self.assertEqual(out["unresolved_count"],10)

if __name__=="__main__":
    unittest.main()
