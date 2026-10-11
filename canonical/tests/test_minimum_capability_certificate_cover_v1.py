from __future__ import annotations

import unittest

from canonical.runtime import minimum_capability_certificate_cover_v1 as m


class MinimumCapabilityCertificateCoverV1Tests(unittest.TestCase):
    def test_literal_score_and_capability_are_distinct(self):
        out = m.compile_benchmark_claim({
            "id": "MM",
            "claim_kind": "LITERAL_BENCHMARK_SCORE",
            "benchmark": "MysteryMechanism",
            "benchmark_is_parent_objective": False,
            "capability_propositions": [
                "BRAIN_BOUNDED_UNSEEN_MECHANISM_RECOVERY_GE_OPUS55"
            ],
            "literal_score_predicate":
                "BRAIN_MYSTERYMECHANISM_MATCHED_SUCCESS_GE_109_OF_222",
        })
        self.assertEqual(
            out["required_propositions"],
            ["BRAIN_MYSTERYMECHANISM_MATCHED_SUCCESS_GE_109_OF_222"],
        )
        self.assertFalse(out["reverse_inference_from_capability_to_literal_score"])

    def test_capability_claim_requires_capability_proposition(self):
        with self.assertRaises(m.CertificateCoverError):
            m.compile_benchmark_claim({
                "id": "x",
                "claim_kind": "CAPABILITY_COMPARISON",
                "benchmark_is_parent_objective": False,
                "capability_propositions": [],
            })

    def test_benchmark_parent_objective_is_rejected(self):
        with self.assertRaises(m.CertificateCoverError):
            m.compile_benchmark_claim({
                "id": "x",
                "claim_kind": "CAPABILITY_COMPARISON",
                "benchmark_is_parent_objective": True,
                "capability_propositions": ["P"],
            })

    def test_shared_certificate_beats_separate_more_expensive_routes(self):
        obligations = [
            {"id": "A", "required_propositions": ["P_A"]},
            {"id": "B", "required_propositions": ["P_B"]},
        ]
        certs = [
            {
                "id": "shared",
                "proves": ["P_A", "P_B"],
                "valid": True,
                "scope_bound": True,
                "donor_free": True,
                "incremental_spend_usd": 0,
                "wall_clock_cost": 1,
                "compute_cost": 1,
                "evidence_risk": 0,
                "complexity_cost": 0,
            },
            {
                "id": "a_only",
                "proves": ["P_A"],
                "valid": True,
                "scope_bound": True,
                "donor_free": True,
                "incremental_spend_usd": 0,
                "wall_clock_cost": 2,
                "compute_cost": 0,
                "evidence_risk": 0,
                "complexity_cost": 0,
            },
            {
                "id": "b_only",
                "proves": ["P_B"],
                "valid": True,
                "scope_bound": True,
                "donor_free": True,
                "incremental_spend_usd": 0,
                "wall_clock_cost": 2,
                "compute_cost": 0,
                "evidence_risk": 0,
                "complexity_cost": 0,
            },
        ]
        out = m.select_minimum_certificate_cover(obligations, certs)
        self.assertEqual(out["status"], "COMPLETE_MINIMUM_COVER")
        self.assertEqual(out["selected_certificate_ids"], ["shared"])

    def test_external_model_or_unbound_certificate_is_inadmissible(self):
        obligations = [{"id": "A", "required_propositions": ["P"]}]
        certs = [
            {
                "id": "external_model",
                "proves": ["P"],
                "valid": True,
                "scope_bound": True,
                "donor_free": False,
                "incremental_spend_usd": 0,
            },
            {
                "id": "unbound",
                "proves": ["P"],
                "valid": True,
                "scope_bound": False,
                "donor_free": True,
                "incremental_spend_usd": 0,
            },
        ]
        out = m.select_minimum_certificate_cover(obligations, certs)
        self.assertEqual(out["status"], "INCOMPLETE_NO_SUFFICIENT_COVER")
        self.assertEqual(out["unresolved_propositions"], ["P"])

    def test_hard_zero_spend_excludes_paid_route(self):
        obligations = [{"id": "A", "required_propositions": ["P"]}]
        certs = [{
            "id": "paid",
            "proves": ["P"],
            "valid": True,
            "scope_bound": True,
            "donor_free": True,
            "incremental_spend_usd": 0.01,
        }]
        out = m.select_minimum_certificate_cover(
            obligations, certs, max_incremental_spend_usd=0.0
        )
        self.assertEqual(out["status"], "INCOMPLETE_NO_SUFFICIENT_COVER")

    def test_implication_happens_only_when_explicitly_declared(self):
        obligations = [
            {"id": "literal", "required_propositions": ["LITERAL_SCORE"]},
        ]
        certs = [{
            "id": "capability",
            "proves": ["CAPABILITY"],
            "valid": True,
            "scope_bound": True,
            "donor_free": True,
            "incremental_spend_usd": 0,
        }]

        without_edge = m.select_minimum_certificate_cover(obligations, certs)
        self.assertEqual(
            without_edge["status"], "INCOMPLETE_NO_SUFFICIENT_COVER"
        )

        with_edge = m.select_minimum_certificate_cover(
            obligations,
            certs,
            implication_edges={"CAPABILITY": ["LITERAL_SCORE"]},
        )
        self.assertEqual(with_edge["status"], "COMPLETE_MINIMUM_COVER")

    def test_already_proved_returns_zero_new_certificates(self):
        out = m.select_minimum_certificate_cover(
            [{"id": "A", "required_propositions": ["P"]}],
            [],
            already_proved=["P"],
        )
        self.assertEqual(out["status"], "COMPLETE_ZERO_NEW_CERTIFICATES")
        self.assertEqual(out["selected_certificate_ids"], [])

    def test_too_many_candidates_fails_closed(self):
        certs = []
        for i in range(21):
            certs.append({
                "id": f"c{i}",
                "proves": ["P"],
                "valid": True,
                "scope_bound": True,
                "donor_free": True,
                "incremental_spend_usd": 0,
            })
        with self.assertRaises(m.CertificateCoverError):
            m.select_minimum_certificate_cover(
                [{"id": "A", "required_propositions": ["P"]}],
                certs,
                exact_certificate_limit=20,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
