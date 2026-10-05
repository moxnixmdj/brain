from __future__ import annotations

import unittest

from canonical.runtime.acceptance_quotient_simulation_v3 import (
    verify_acceptance_quotient_certificate_v3,
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


class Tests(unittest.TestCase):
    def test_pass_with_causal_policy_binding(self):
        verdict = verify_acceptance_quotient_certificate_v3(base())
        self.assertEqual(verdict["status"], "PASS", verdict)

    def test_missing_strategy_receipt_fails(self):
        cert = base()
        cert.pop("causal_strategy_receipt")
        verdict = verify_acceptance_quotient_certificate_v3(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("CAUSAL_STRATEGY_RECEIPT_INVALID", verdict["reason"])

    def test_single_owned_policy_is_load_bearing(self):
        cert = base()
        cert["causal_strategy_receipt"]["single_owned_policy"] = False
        verdict = verify_acceptance_quotient_certificate_v3(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("SINGLE_OWNED_POLICY_NOT_TRUE", verdict["reason"])

    def test_history_adaptation_is_load_bearing(self):
        cert = base()
        cert["causal_strategy_receipt"]["history_adapted"] = False
        verdict = verify_acceptance_quotient_certificate_v3(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("HISTORY_ADAPTED_NOT_TRUE", verdict["reason"])

    def test_future_or_target_oracle_is_forbidden(self):
        cert = base()
        cert["causal_strategy_receipt"]["no_future_or_target_oracle"] = False
        verdict = verify_acceptance_quotient_certificate_v3(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("NO_FUTURE_OR_TARGET_ORACLE_NOT_TRUE", verdict["reason"])

    def test_pointwise_graph_match_cannot_replace_policy_binding(self):
        cert = base()
        cert["brain_macro_edges"][0].pop("causal_policy_binding_receipt")
        verdict = verify_acceptance_quotient_certificate_v3(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("CAUSAL_POLICY_BINDING_RECEIPT_INVALID", verdict["reason"])

    def test_each_edge_must_be_induced_by_bound_policy(self):
        cert = base()
        cert["brain_macro_edges"][0]["causal_policy_binding_receipt"]["induced_by_bound_policy"] = False
        verdict = verify_acceptance_quotient_certificate_v3(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("INDUCED_BY_BOUND_POLICY_NOT_TRUE", verdict["reason"])

    def test_v2_semantic_failure_still_fails(self):
        cert = base()
        cert["relation_soundness_receipt"]["acceptance_preorder_sound"] = False
        verdict = verify_acceptance_quotient_certificate_v3(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("V2_SEMANTIC_OR_GRAPH_CHECK_FAILED", verdict["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
