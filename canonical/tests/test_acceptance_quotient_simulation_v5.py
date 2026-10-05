from __future__ import annotations

import copy
import unittest

from canonical.runtime.acceptance_quotient_simulation_v4 import (
    verify_acceptance_quotient_certificate_v4,
)
from canonical.runtime.acceptance_quotient_simulation_v5 import (
    verify_acceptance_quotient_certificate_v5,
)


def receipt(seed: str, **truths):
    return {
        "path": f"canonical/verification/{seed}.json",
        "git_blob_sha": (seed[0] if seed else "a") * 40,
        **truths,
    }


def base(two_actions: bool = False):
    policy_id = "POLICY_ALPHA"
    scope = receipt(
        "s",
        invariant_holds=True,
        scope_complete=True,
        universal_over_realizations=True,
        independent_or_objective=True,
    )

    def edge_policy(seed: str):
        return receipt(
            seed,
            policy_id=policy_id,
            induced_by_bound_policy=True,
            choice_uses_current_or_past_information_only=True,
            no_target_edge_or_future_branch_oracle=True,
            scope_complete=True,
            independent_or_objective=True,
        )

    cert = {
        "policy_id": policy_id,
        "policy_table": [
            {"brain_state": "B0", "policy_action_id": "A"},
        ],
        "target_states": ["T0", "T1", "T2"],
        "brain_states": ["B0", "B1", "B2"],
        "initial_target_states": ["T0"],
        "initial_brain_states": ["B0"],
        "terminal_target_states": ["T1", "T2"],
        "terminal_brain_states": ["B1", "B2"],
        "relation": [["T0", "B0"], ["T1", "B1"], ["T2", "B2"]],
        "target_cut_edges": [
            {"id": "E1", "from": "T0", "to": "T1"},
            {"id": "E2", "from": "T0", "to": "T2"},
        ],
        "brain_macro_edges": [
            {
                "from": "B0",
                "to": "B1",
                "policy_action_id": "A",
                "covers_target_edge_ids": ["E1"],
                "scope_authority_receipt": scope,
                "scope_authority_invariant": False,
                "causal_policy_binding_receipt": edge_policy("p1"),
                "realizability_receipt": receipt(
                    "r1",
                    scope_complete=True,
                    universal_from_abstract_class=True,
                    independent_or_objective=True,
                ),
            },
            {
                "from": "B0",
                "to": "B2",
                "policy_action_id": "B" if two_actions else "A",
                "covers_target_edge_ids": ["E2"],
                "scope_authority_receipt": scope,
                "scope_authority_invariant": False,
                "causal_policy_binding_receipt": edge_policy("p2"),
                "realizability_receipt": receipt(
                    "r2",
                    scope_complete=True,
                    universal_from_abstract_class=True,
                    independent_or_objective=True,
                ),
            },
        ],
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
            policy_id=policy_id,
            single_owned_policy=True,
            complete_on_claimed_domain=True,
            history_adapted=True,
            no_future_or_target_oracle=True,
            existential_matches_induced_by_policy=True,
            independent_or_objective=True,
        ),
        "acceptance_semantics_class": "UNIVERSAL_TOP_SUPPORT",
        "distribution_free_dominance_receipt": receipt(
            "d",
            class_wide_top_support_dominance_proved=True,
            scope_complete=True,
            target_distribution_irrelevant=True,
            independent_or_objective=True,
        ),
    }
    return cert


class Tests(unittest.TestCase):
    def test_uniform_single_action_passes(self):
        verdict = verify_acceptance_quotient_certificate_v5(base())
        self.assertEqual(verdict["status"], "PASS", verdict)
        self.assertTrue(
            verdict["finite_quotient_uniform_action_quantifier_mechanically_proved"]
        )

    def test_v4_accepts_target_edge_conditioned_action_switch_but_v5_rejects(self):
        cert = base(two_actions=True)
        old = verify_acceptance_quotient_certificate_v4(cert)
        self.assertEqual(old["status"], "PASS", old)

        hardened = verify_acceptance_quotient_certificate_v5(cert)
        self.assertEqual(hardened["status"], "FAIL_CLOSED", hardened)
        self.assertIn("UNIFORM_POLICY_SIMULATION_MISSING:E2", hardened["reason"])

    def test_strategy_policy_identity_mismatch_fails(self):
        cert = base()
        cert["causal_strategy_receipt"]["policy_id"] = "OTHER"
        verdict = verify_acceptance_quotient_certificate_v5(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("CAUSAL_STRATEGY_POLICY_ID_MISMATCH", verdict["reason"])

    def test_edge_policy_identity_mismatch_fails(self):
        cert = base()
        cert["brain_macro_edges"][1]["causal_policy_binding_receipt"]["policy_id"] = "OTHER"
        verdict = verify_acceptance_quotient_certificate_v5(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("BRAIN_EDGE_1_POLICY_ID_MISMATCH", verdict["reason"])

    def test_duplicate_policy_state_fails(self):
        cert = base()
        cert["policy_table"].append(
            {"brain_state": "B0", "policy_action_id": "A"}
        )
        verdict = verify_acceptance_quotient_certificate_v5(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("POLICY_TABLE_DUPLICATE_BRAIN_STATE", verdict["reason"])

    def test_selected_action_must_exist_at_state(self):
        cert = base()
        cert["policy_table"][0]["policy_action_id"] = "NO_SUCH_ACTION"
        verdict = verify_acceptance_quotient_certificate_v5(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("POLICY_ACTION_HAS_NO_DECLARED_MACROEDGE", verdict["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
