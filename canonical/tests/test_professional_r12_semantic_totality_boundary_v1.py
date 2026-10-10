import unittest

from canonical.runtime.professional_r12_semantic_totality_boundary_v1 import (
    TotalityBoundaryError,
    current_boundary,
    evaluate_closure_routes,
    finite_catalog_countermodel,
)


class R12SemanticTotalityBoundaryTests(unittest.TestCase):
    def test_finite_catalog_plus_eight_clauses_has_open_world_countermodel(self):
        out=finite_catalog_countermodel(
            observed_challenge_ids=[f"C{i:02d}" for i in range(1,81)],
            all_eight_root_contract_clauses_verified=True,
            latent_material_mechanism_id="E_UNSEEN",
        )
        self.assertTrue(out["finite_catalog_plus_eight_clauses_insufficient_for_open_world_totality"])

    def test_latent_mechanism_cannot_already_be_observed(self):
        with self.assertRaises(TotalityBoundaryError):
            finite_catalog_countermodel(
                observed_challenge_ids=["E1"],
                all_eight_root_contract_clauses_verified=True,
                latent_material_mechanism_id="E1",
            )

    def test_current_boundary_remains_open(self):
        out=current_boundary()
        self.assertFalse(out["stronger_material_defeater_totality_proved"])
        self.assertIsNone(out["closure_basis"])
        self.assertFalse(out["cc_r3_terminal_closure_proved"])
        self.assertFalse(out["semantic_property_truth_authority"])

    def test_complete_materiality_decider_is_sound_closure_route(self):
        out=evaluate_closure_routes(
            complete_materiality_decider=True,
            finite_characteristic_partition_proved=False,
            positive_certification_gate_complete_mediation=False,
            every_positive_certificate_has_claim_scoped_complete_local_totality_basis=False,
            unknown_or_unproved_local_totality_blocks_positive_certification=False,
            nonvacuous_positive_route_proved=False,
        )
        self.assertTrue(out["stronger_material_defeater_totality_proved"])
        self.assertEqual(out["closure_basis"],"COMPLETE_MATERIALITY_DECIDER")

    def test_finite_characteristic_partition_is_sound_closure_route(self):
        out=evaluate_closure_routes(
            complete_materiality_decider=False,
            finite_characteristic_partition_proved=True,
            positive_certification_gate_complete_mediation=False,
            every_positive_certificate_has_claim_scoped_complete_local_totality_basis=False,
            unknown_or_unproved_local_totality_blocks_positive_certification=False,
            nonvacuous_positive_route_proved=False,
        )
        self.assertTrue(out["stronger_material_defeater_totality_proved"])
        self.assertEqual(out["closure_basis"],"PROVED_FINITE_CHARACTERISTIC_PARTITION")

    def test_complete_proof_carrying_positive_mediation_is_sound_route(self):
        out=evaluate_closure_routes(
            complete_materiality_decider=False,
            finite_characteristic_partition_proved=False,
            positive_certification_gate_complete_mediation=True,
            every_positive_certificate_has_claim_scoped_complete_local_totality_basis=True,
            unknown_or_unproved_local_totality_blocks_positive_certification=True,
            nonvacuous_positive_route_proved=True,
        )
        self.assertTrue(out["stronger_material_defeater_totality_proved"])
        self.assertEqual(out["closure_basis"],"COMPLETE_PROOF_CARRYING_POSITIVE_CERTIFICATION_MEDIATION")

    def test_always_abstain_vacuity_cannot_close_proof_carrying_route(self):
        out=evaluate_closure_routes(
            complete_materiality_decider=False,
            finite_characteristic_partition_proved=False,
            positive_certification_gate_complete_mediation=True,
            every_positive_certificate_has_claim_scoped_complete_local_totality_basis=True,
            unknown_or_unproved_local_totality_blocks_positive_certification=True,
            nonvacuous_positive_route_proved=False,
        )
        self.assertFalse(out["stronger_material_defeater_totality_proved"])

    def test_partial_positive_mediation_cannot_close(self):
        out=evaluate_closure_routes(
            complete_materiality_decider=False,
            finite_characteristic_partition_proved=False,
            positive_certification_gate_complete_mediation=False,
            every_positive_certificate_has_claim_scoped_complete_local_totality_basis=True,
            unknown_or_unproved_local_totality_blocks_positive_certification=True,
            nonvacuous_positive_route_proved=True,
        )
        self.assertFalse(out["stronger_material_defeater_totality_proved"])


if __name__=="__main__":
    unittest.main(verbosity=2)
