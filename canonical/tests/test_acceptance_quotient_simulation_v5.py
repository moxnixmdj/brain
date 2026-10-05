from __future__ import annotations

import unittest

from canonical.runtime.acceptance_quotient_simulation_v5 import (
    verify_acceptance_quotient_certificate_v5,
)


POLICY_A = "a" * 64
POLICY_B = "b" * 64


def receipt(seed: str, **fields):
    return {
        "path": f"canonical/verification/{seed}.json",
        "git_blob_sha": (seed[0] if seed else "a") * 40,
        **fields,
    }


def base():
    scope = receipt(
        "s",
        invariant_holds=True,
        scope_complete=True,
        universal_over_realizations=True,
        independent_or_objective=True,
    )
    edge_policy = receipt(
        "p",
        induced_by_bound_policy=True,
        choice_uses_current_or_past_information_only=True,
        no_target_edge_or_future_branch_oracle=True,
        scope_complete=True,
        independent_or_objective=True,
        policy_commitment_sha256=POLICY_A,
    )
    return {
        "target_states": ["T0", "T1"],
        "brain_states": ["B0", "B1"],
        "initial_target_states": ["T0"],
        "initial_brain_states": ["B0"],
        "terminal_target_states": ["T1"],
        "terminal_brain_states": ["B1"],
        "relation": [["T0", "B0"], ["T1", "B1"]],
        "target_cut_edges": [{"id": "E", "from": "T0", "to": "T1"}],
        "brain_macro_edges": [{
            "from": "B0",
            "to": "B1",
            "covers_target_edge_ids": ["E"],
            "scope_authority_receipt": scope,
            "scope_authority_invariant": False,
            "causal_policy_binding_receipt": edge_policy,
            "realizability_receipt": receipt(
                "r",
                scope_complete=True,
                universal_from_abstract_class=True,
                independent_or_objective=True,
            ),
        }],
        "abstraction_receipt": receipt(
            "a",
            acceptance_complete=True,
            load_bearing_observations_complete=True,
            target_conservative_coverage=True,
            independent_or_objective=True,
        ),
        "relation_soundness_receipt": receipt(
            "q",
            acceptance_preorder_sound=True,
            load_bearing_dimensions_complete=True,
            scope_complete=True,
            independent_or_objective=True,
        ),
        "terminal_acceptance_receipt": receipt(
            "t",
            terminal_noninferiority_sound=True,
            scope_complete=True,
            independent_or_objective=True,
        ),
        "causal_strategy_receipt": receipt(
            "c",
            single_owned_policy=True,
            complete_on_claimed_domain=True,
            history_adapted=True,
            no_future_or_target_oracle=True,
            existential_matches_induced_by_policy=True,
            independent_or_objective=True,
            policy_commitment_sha256=POLICY_A,
        ),
    }


class Tests(unittest.TestCase):
    def test_distribution_free_universal_receipt_passes(self):
        cert = base()
        cert["acceptance_semantics_class"] = "UNIVERSAL_TOP_SUPPORT"
        cert["distribution_free_dominance_receipt"] = receipt(
            "d",
            class_wide_top_support_dominance_proved=True,
            scope_complete=True,
            target_distribution_irrelevant=True,
            independent_or_objective=True,
            universal_over_all_admissible_brain_policies=True,
        )
        verdict = verify_acceptance_quotient_certificate_v5(cert)
        self.assertEqual(verdict["status"], "PASS", verdict)
        self.assertEqual(verdict["policy_commitment_sha256"], POLICY_A)
        self.assertEqual(
            verdict["acceptance_policy_binding"]["mode"],
            "UNIVERSAL_OVER_ALL_ADMISSIBLE_BRAIN_POLICIES",
        )

    def test_missing_strategy_commitment_fails(self):
        cert = base()
        cert["acceptance_semantics_class"] = "UNIVERSAL_TOP_SUPPORT"
        cert["causal_strategy_receipt"].pop("policy_commitment_sha256")
        cert["distribution_free_dominance_receipt"] = receipt(
            "d",
            class_wide_top_support_dominance_proved=True,
            scope_complete=True,
            target_distribution_irrelevant=True,
            independent_or_objective=True,
            universal_over_all_admissible_brain_policies=True,
        )
        verdict = verify_acceptance_quotient_certificate_v5(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("CAUSAL_STRATEGY_RECEIPT_POLICY_COMMITMENT_INVALID", verdict["reason"])

    def test_edge_commitment_mismatch_fails(self):
        cert = base()
        cert["acceptance_semantics_class"] = "UNIVERSAL_TOP_SUPPORT"
        cert["brain_macro_edges"][0]["causal_policy_binding_receipt"][
            "policy_commitment_sha256"
        ] = POLICY_B
        cert["distribution_free_dominance_receipt"] = receipt(
            "d",
            class_wide_top_support_dominance_proved=True,
            scope_complete=True,
            target_distribution_irrelevant=True,
            independent_or_objective=True,
            universal_over_all_admissible_brain_policies=True,
        )
        verdict = verify_acceptance_quotient_certificate_v5(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("POLICY_COMMITMENT_MISMATCH", verdict["reason"])

    def test_stochastic_distribution_receipt_must_bind_same_policy(self):
        cert = base()
        cert["acceptance_semantics_class"] = "STOCHASTIC_MATCHED_NONINFERIORITY"
        cert["policy_distribution_bridge_receipt"] = receipt(
            "d",
            policy_choice_coherent=True,
            scope_complete=True,
            distribution_or_expected_utility_order_proved=True,
            independent_or_objective=True,
            policy_commitment_sha256=POLICY_B,
        )
        verdict = verify_acceptance_quotient_certificate_v5(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn(
            "POLICY_DISTRIBUTION_BRIDGE_RECEIPT_POLICY_COMMITMENT_MISMATCH",
            verdict["reason"],
        )

    def test_stochastic_distribution_receipt_same_policy_passes(self):
        cert = base()
        cert["acceptance_semantics_class"] = "STOCHASTIC_MATCHED_NONINFERIORITY"
        cert["policy_distribution_bridge_receipt"] = receipt(
            "d",
            policy_choice_coherent=True,
            scope_complete=True,
            distribution_or_expected_utility_order_proved=True,
            independent_or_objective=True,
            policy_commitment_sha256=POLICY_A,
        )
        verdict = verify_acceptance_quotient_certificate_v5(cert)
        self.assertEqual(verdict["status"], "PASS", verdict)
        self.assertEqual(
            verdict["acceptance_policy_binding"]["policy_commitment_sha256"],
            POLICY_A,
        )

    def test_distribution_free_bound_policy_mismatch_fails(self):
        cert = base()
        cert["acceptance_semantics_class"] = "OBJECTIVE_CEILING"
        cert["distribution_free_dominance_receipt"] = receipt(
            "d",
            objective_ceiling_proved=True,
            scope_complete=True,
            target_distribution_irrelevant=True,
            independent_or_objective=True,
            policy_commitment_sha256=POLICY_B,
        )
        verdict = verify_acceptance_quotient_certificate_v5(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn(
            "DISTRIBUTION_FREE_DOMINANCE_RECEIPT_POLICY_COMMITMENT_MISMATCH",
            verdict["reason"],
        )

    def test_v4_failure_is_preserved(self):
        cert = base()
        cert["acceptance_semantics_class"] = "UNCLASSIFIED"
        verdict = verify_acceptance_quotient_certificate_v5(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("V4_ACCEPTANCE_CAUSAL_SEMANTIC_CHECK_FAILED", verdict["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
