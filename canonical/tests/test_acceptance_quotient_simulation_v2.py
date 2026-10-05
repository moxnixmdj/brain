from __future__ import annotations

import copy
import unittest

from canonical.runtime.acceptance_quotient_simulation_v2 import (
    verify_acceptance_quotient_certificate_v2,
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
            # A naked Boolean is deliberately not load-bearing in V2.
            "scope_authority_invariant": False,
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
    }


class Tests(unittest.TestCase):
    def test_pass_with_semantic_receipts(self):
        verdict = verify_acceptance_quotient_certificate_v2(base())
        self.assertEqual(verdict["status"], "PASS", verdict)

    def test_relation_soundness_is_load_bearing(self):
        cert = base()
        cert.pop("relation_soundness_receipt")
        verdict = verify_acceptance_quotient_certificate_v2(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("RELATION_SOUNDNESS_RECEIPT_INVALID", verdict["reason"])

    def test_relation_cannot_self_declare_wrong_preorder(self):
        cert = base()
        cert["relation_soundness_receipt"]["acceptance_preorder_sound"] = False
        verdict = verify_acceptance_quotient_certificate_v2(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("ACCEPTANCE_PREORDER_SOUND_NOT_TRUE", verdict["reason"])

    def test_terminal_semantics_is_load_bearing(self):
        cert = base()
        cert["terminal_acceptance_receipt"]["terminal_noninferiority_sound"] = False
        verdict = verify_acceptance_quotient_certificate_v2(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("TERMINAL_NONINFERIORITY_SOUND_NOT_TRUE", verdict["reason"])

    def test_naked_scope_boolean_cannot_replace_receipt(self):
        cert = base()
        cert["brain_macro_edges"][0].pop("scope_authority_receipt")
        cert["brain_macro_edges"][0]["scope_authority_invariant"] = True
        verdict = verify_acceptance_quotient_certificate_v2(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("SCOPE_AUTHORITY_RECEIPT_INVALID", verdict["reason"])

    def test_scope_receipt_must_be_universal(self):
        cert = base()
        cert["brain_macro_edges"][0]["scope_authority_receipt"]["universal_over_realizations"] = False
        verdict = verify_acceptance_quotient_certificate_v2(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("UNIVERSAL_OVER_REALIZATIONS_NOT_TRUE", verdict["reason"])

    def test_v1_graph_failure_still_fails(self):
        cert = base()
        cert["brain_macro_edges"] = []
        verdict = verify_acceptance_quotient_certificate_v2(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
