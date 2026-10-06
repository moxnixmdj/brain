import math
import unittest
from canonical.runtime import h100_provenance_invariant_learned_information_v1 as p

class H100ProvenanceInvariantLearnedInformationTests(unittest.TestCase):
    def test_bijective_recode_preserves_entropy(self):
        states=["A","B","C","A","B","C"]
        out=p.bijective_recode_entropy(states,{"A":"x","B":"y","C":"z"})
        self.assertTrue(out["preserved"])
        self.assertAlmostEqual(out["entropy_before_bits"],math.log2(3),places=12)
        self.assertAlmostEqual(out["entropy_after_bits"],math.log2(3),places=12)

    def test_constant_preexposure_state_has_zero_data_information(self):
        self.assertEqual(p.shannon_entropy_uniform_ensemble(["FIXED"]*8),0.0)

    def test_noninjective_recode_rejected_as_not_lossless(self):
        with self.assertRaises(p.ProvenanceAccountingError):
            p.bijective_recode_entropy(["A","B"],{"A":"x","B":"x"})

    def test_source_literal_weight_reencoding_stays_learned_origin(self):
        out=p.learned_origin_classification(
            data_dependent_value=False,
            persisted_for_future_use=True,
            container="SOURCE_LITERAL",
            losslessly_recovers_prior_learned_state=True,
        )
        self.assertTrue(out["learned_origin_state"])

    def test_fixed_world_independent_algorithm_is_not_learned_origin(self):
        out=p.learned_origin_classification(
            data_dependent_value=False,
            persisted_for_future_use=True,
            container="FIXED_ALGORITHM",
            losslessly_recovers_prior_learned_state=False,
        )
        self.assertFalse(out["learned_origin_state"])

    def test_data_selected_symbolic_structure_is_learned_origin(self):
        out=p.learned_origin_classification(
            data_dependent_value=True,
            persisted_for_future_use=True,
            container="DETERMINISTIC_REGISTRY_CODE",
        )
        self.assertTrue(out["learned_origin_state"])

    def test_cubic_three_way_selection_capacity(self):
        out=p.audit_compiled_selection(
            capability_id="CAP_AFFINE_CUBIC_V1",
            candidate_count=3,
            selected_after_observing_development_data=True,
            persisted_in_registry=True,
        )
        self.assertTrue(out["provenance"]["learned_origin_state"])
        self.assertEqual(out["selection_capacity"]["fixed_length_selection_index_bits"],2)
        self.assertAlmostEqual(out["selection_capacity"]["max_selection_entropy_bits"],math.log2(3),places=12)

    def test_depth4_chain_selection_capacity(self):
        out=p.selection_capacity_bits(1554)
        self.assertEqual(out["fixed_length_selection_index_bits"],11)
        self.assertGreater(out["max_selection_entropy_bits"],10)
        self.assertLess(out["max_selection_entropy_bits"],11)

    def test_certificate(self):
        c=p.certificate()
        self.assertTrue(c["bijective_recode_demo"]["preserved"])
        self.assertTrue(c["losslessly_embedded_weights"]["learned_origin_state"])
        self.assertFalse(c["preexposure_fixed_code"]["learned_origin_state"])
        self.assertEqual(c["h100_terminal_credit_delta"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
