from __future__ import annotations

import unittest

from canonical.runtime.acceptance_quotient_simulation_v5 import (
    verify_acceptance_quotient_certificate_v5,
)


def receipt(seed: str, **truths):
    return {
        "path": f"canonical/verification/{seed}.json",
        "git_blob_sha": (seed[0] if seed else "a") * 40,
        **truths,
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
        ),
    }


def semantics_binding(bound_class: str, **extra):
    return receipt(
        "b",
        acceptance_obligation_bound=True,
        behavioral_contract_bound=True,
        class_assignment_sound=True,
        classification_complete_on_claimed_scope=True,
        distribution_dependence_decided=True,
        scope_complete=True,
        independent_or_objective=True,
        acceptance_obligation_id="A1",
        behavioral_contract_id="B1",
        bound_acceptance_semantics_class=bound_class,
        **extra,
    )


class Tests(unittest.TestCase):
    def test_stochastic_bound_class_passes_with_distribution_bridge(self):
        cert = base()
        cert["acceptance_semantics_class"] = "STOCHASTIC_MATCHED_NONINFERIORITY"
        cert["acceptance_semantics_binding_receipt"] = semantics_binding(
            "STOCHASTIC_MATCHED_NONINFERIORITY",
            requires_distributional_comparison=True,
        )
        cert["policy_distribution_bridge_receipt"] = receipt(
            "d",
            policy_choice_coherent=True,
            scope_complete=True,
            distribution_or_expected_utility_order_proved=True,
            independent_or_objective=True,
        )
        verdict = verify_acceptance_quotient_certificate_v5(cert)
        self.assertEqual(verdict["status"], "PASS", verdict)

    def test_missing_semantics_binding_fails_closed(self):
        cert = base()
        cert["acceptance_semantics_class"] = "UNIVERSAL_TOP_SUPPORT"
        cert["distribution_free_dominance_receipt"] = receipt(
            "d",
            class_wide_top_support_dominance_proved=True,
            scope_complete=True,
            target_distribution_irrelevant=True,
            independent_or_objective=True,
        )
        verdict = verify_acceptance_quotient_certificate_v5(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("ACCEPTANCE_SEMANTICS_BINDING_RECEIPT_INVALID", verdict["reason"])

    def test_stochastic_relabel_to_distribution_free_is_rejected(self):
        cert = base()
        cert["acceptance_semantics_class"] = "UNIVERSAL_TOP_SUPPORT"
        cert["acceptance_semantics_binding_receipt"] = semantics_binding(
            "STOCHASTIC_MATCHED_NONINFERIORITY",
            requires_distributional_comparison=True,
        )
        cert["distribution_free_dominance_receipt"] = receipt(
            "d",
            class_wide_top_support_dominance_proved=True,
            scope_complete=True,
            target_distribution_irrelevant=True,
            independent_or_objective=True,
        )
        verdict = verify_acceptance_quotient_certificate_v5(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("ACCEPTANCE_SEMANTICS_BINDING_CLASS_MISMATCH", verdict["reason"])

    def test_distribution_free_class_requires_classification_proof(self):
        cert = base()
        cert["acceptance_semantics_class"] = "UNIVERSAL_TOP_SUPPORT"
        cert["acceptance_semantics_binding_receipt"] = semantics_binding(
            "UNIVERSAL_TOP_SUPPORT"
        )
        cert["distribution_free_dominance_receipt"] = receipt(
            "d",
            class_wide_top_support_dominance_proved=True,
            scope_complete=True,
            target_distribution_irrelevant=True,
            independent_or_objective=True,
        )
        verdict = verify_acceptance_quotient_certificate_v5(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn(
            "ACCEPTANCE_SEMANTICS_BINDING_DISTRIBUTION_FREE_CLASS_NOT_PROVED",
            verdict["reason"],
        )

    def test_distribution_free_bound_class_passes_with_proof(self):
        cert = base()
        cert["acceptance_semantics_class"] = "UNIVERSAL_TOP_SUPPORT"
        cert["acceptance_semantics_binding_receipt"] = semantics_binding(
            "UNIVERSAL_TOP_SUPPORT",
            distribution_free_class_proved=True,
        )
        cert["distribution_free_dominance_receipt"] = receipt(
            "d",
            class_wide_top_support_dominance_proved=True,
            scope_complete=True,
            target_distribution_irrelevant=True,
            independent_or_objective=True,
        )
        verdict = verify_acceptance_quotient_certificate_v5(cert)
        self.assertEqual(verdict["status"], "PASS", verdict)


if __name__ == "__main__":
    unittest.main(verbosity=2)
