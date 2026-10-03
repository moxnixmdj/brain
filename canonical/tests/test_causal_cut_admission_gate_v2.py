from __future__ import annotations

import unittest

from canonical.runtime.causal_cut_admission_gate_v2 import evaluate


BASE = {
    "unresolved_atomic_predicates": 31,
    "accepted_families": 2,
    "minimum_remaining_work_lower_bound": 40,
    "proved_impossible_branches": ["TB4_FROZEN_ROUTE"],
    "formally_owned_domain_atoms": ["D1"],
    "protected_terminal_facts": ["F1", "F2"],
    "primitive_residual_facts": ["PA1", "PA2", "PA3"],
    "verified_terminal_evidence_ids": ["E1", "E2", "E3"],
}


def link(
    primitive: str = "PA1",
    blocker: str = "B1",
    evidence: str = "E1",
    effect: str = "DISCHARGES_PRIMITIVE_FACT",
):
    return [{
        "edge_id": f"EDGE:{primitive}:{blocker}:{effect}",
        "primitive_fact_id": primitive,
        "blocker_id": blocker,
        "verified_evidence_id": evidence,
        "effect": effect,
    }]


class Tests(unittest.TestCase):
    def test_rejects_no_delta_even_with_valid_link(self):
        out = evaluate(BASE, dict(BASE), blocker_ids=["B1"], causal_links=link())
        self.assertFalse(out["admit"])
        self.assertEqual(out["status"], "PASS__REJECT_NO_CAUSALLY_BOUND_TERMINAL_DELTA")

    def test_rejects_owned_domain_gain_without_causal_links(self):
        after = dict(BASE)
        after["formally_owned_domain_atoms"] = ["D1", "D2"]
        out = evaluate(BASE, after, blocker_ids=["B1"], causal_links=[])
        self.assertFalse(out["admit"])

    def test_rejects_unverified_causal_evidence(self):
        after = dict(BASE)
        after["formally_owned_domain_atoms"] = ["D1", "D2"]
        out = evaluate(
            BASE,
            after,
            blocker_ids=["B1"],
            causal_links=link(evidence="NOT_VERIFIED", effect="CREATES_VERIFIED_IMPLICATION"),
        )
        self.assertFalse(out["admit"])
        self.assertIn("UNVERIFIED_CAUSAL_EVIDENCE", " ".join(out["errors"]))

    def test_rejects_off_cut_primitive(self):
        after = dict(BASE)
        after["minimum_remaining_work_lower_bound"] = 39
        out = evaluate(
            BASE,
            after,
            blocker_ids=["B1"],
            causal_links=link(primitive="NOT_ON_CUT"),
        )
        self.assertFalse(out["admit"])
        self.assertIn("OFF_CUT_PRIMITIVE_FACT", " ".join(out["errors"]))

    def test_rejects_undeclared_blocker(self):
        after = dict(BASE)
        after["minimum_remaining_work_lower_bound"] = 39
        out = evaluate(BASE, after, blocker_ids=["B1"], causal_links=link(blocker="B2"))
        self.assertFalse(out["admit"])
        self.assertIn("UNDECLARED_BLOCKER", " ".join(out["errors"]))

    def test_admits_bound_primitive_cut_reduction(self):
        after = dict(BASE)
        after["primitive_residual_facts"] = ["PA2", "PA3"]
        after["minimum_remaining_work_lower_bound"] = 39
        out = evaluate(BASE, after, blocker_ids=["B1"], causal_links=link())
        self.assertTrue(out["admit"])
        self.assertEqual(out["observed_terminal_delta"]["primitive_cut_reduction"], ["PA1"])

    def test_rejects_unbound_primitive_cut_reduction(self):
        after = dict(BASE)
        after["primitive_residual_facts"] = ["PA2", "PA3"]
        after["minimum_remaining_work_lower_bound"] = 39
        out = evaluate(
            BASE,
            after,
            blocker_ids=["B2"],
            causal_links=link(primitive="PA2", blocker="B2", evidence="E2"),
        )
        self.assertFalse(out["admit"])
        self.assertIn("UNBOUND_PRIMITIVE_CUT_REDUCTION", out["regressions"])

    def test_admits_causally_bound_owned_domain_gain(self):
        after = dict(BASE)
        after["formally_owned_domain_atoms"] = ["D1", "D2"]
        out = evaluate(
            BASE,
            after,
            blocker_ids=["B1"],
            causal_links=link(effect="CREATES_VERIFIED_IMPLICATION"),
        )
        self.assertTrue(out["admit"])

    def test_admits_new_impossibility_with_cut_binding(self):
        after = dict(BASE)
        after["proved_impossible_branches"] = ["TB4_FROZEN_ROUTE", "ROUTE_X"]
        out = evaluate(
            BASE,
            after,
            blocker_ids=["B1"],
            causal_links=link(effect="PROVES_ROUTE_IMPOSSIBLE"),
        )
        self.assertTrue(out["admit"])

    def test_blocks_regression_even_with_causal_delta(self):
        after = dict(BASE)
        after["primitive_residual_facts"] = ["PA2", "PA3"]
        after["minimum_remaining_work_lower_bound"] = 39
        after["protected_terminal_facts"] = ["F1"]
        out = evaluate(BASE, after, blocker_ids=["B1"], causal_links=link())
        self.assertFalse(out["admit"])
        self.assertIn("PROTECTED_TERMINAL_FACT_LOST", out["regressions"])

    def test_zero_authority(self):
        after = dict(BASE)
        after["primitive_residual_facts"] = ["PA2", "PA3"]
        after["minimum_remaining_work_lower_bound"] = 39
        out = evaluate(BASE, after, blocker_ids=["B1"], causal_links=link())
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
