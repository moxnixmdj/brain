from __future__ import annotations
import unittest

from canonical.runtime.terminal_causal_cut_admission_gate_v2 import evaluate

BASE = {
    "unresolved_atomic_predicates": 31,
    "accepted_families": 2,
    "minimum_remaining_work_lower_bound": 40,
    "unresolved_primitive_facts": ["F1", "F2"],
    "proved_impossible_branches": ["TB4_FROZEN_ROUTE"],
    "verified_implication_edges": ["E0"],
    "formally_owned_domain_atoms": ["D1"],
    "protected_terminal_facts": ["T1", "T2"],
}
MAP = {"F1": ["P1"], "F2": ["P2"]}


def link(blocker: str, fact: str, **extra):
    out = {
        "blocker_id": blocker,
        "primitive_fact_ids": [fact],
        "evidence_ids": ["receipt:1"],
    }
    out.update(extra)
    return out


class Tests(unittest.TestCase):
    def test_rejects_no_delta(self):
        o = evaluate(BASE, dict(BASE), blocker_ids=["P1"], primitive_to_blockers=MAP, causal_links=[link("P1", "F1")])
        self.assertFalse(o["admit"])

    def test_rejects_unrelated_owned_domain_expansion(self):
        a = dict(BASE)
        a["formally_owned_domain_atoms"] = ["D1", "D2"]
        o = evaluate(
            BASE,
            a,
            blocker_ids=["P1"],
            primitive_to_blockers=MAP,
            causal_links=[link("P1", "F1", owned_domain_atom_ids=["D2"])],
        )
        self.assertFalse(o["admit"])
        self.assertIn("OWNED_DOMAIN_GAIN_WITHOUT_CAUSAL_CUT_EVENT", o["causal_link_errors"])

    def test_admits_linked_primitive_closure(self):
        a = dict(BASE)
        a["unresolved_primitive_facts"] = ["F2"]
        a["minimum_remaining_work_lower_bound"] = 39
        o = evaluate(BASE, a, blocker_ids=["P1"], primitive_to_blockers=MAP, causal_links=[link("P1", "F1")])
        self.assertTrue(o["admit"])
        self.assertEqual(o["observed_terminal_delta"]["closed_primitive_facts"], ["F1"])

    def test_rejects_unlinked_primitive_closure(self):
        a = dict(BASE)
        a["unresolved_primitive_facts"] = ["F2"]
        o = evaluate(BASE, a, blocker_ids=["P1"], primitive_to_blockers=MAP, causal_links=[link("P1", "F2")])
        self.assertFalse(o["admit"])
        self.assertTrue(any(x.startswith("UNLINKED_CLOSED_PRIMITIVES") for x in o["causal_link_errors"]))

    def test_rejects_wrong_blocker_to_fact_binding(self):
        a = dict(BASE)
        a["unresolved_primitive_facts"] = ["F2"]
        o = evaluate(BASE, a, blocker_ids=["P2"], primitive_to_blockers=MAP, causal_links=[link("P2", "F1")])
        self.assertFalse(o["admit"])
        self.assertTrue(any("BLOCKER_NOT_BOUND_TO_FACT" in x for x in o["causal_link_errors"]))

    def test_admits_linked_new_impossibility(self):
        a = dict(BASE)
        a["proved_impossible_branches"] = ["TB4_FROZEN_ROUTE", "R1"]
        o = evaluate(
            BASE,
            a,
            blocker_ids=["P1"],
            primitive_to_blockers=MAP,
            causal_links=[link("P1", "F1", impossible_branch_ids=["R1"])],
        )
        self.assertTrue(o["admit"])

    def test_admits_linked_new_edge_with_lower_bound_reduction(self):
        a = dict(BASE)
        a["verified_implication_edges"] = ["E0", "E1"]
        a["minimum_remaining_work_lower_bound"] = 39
        o = evaluate(
            BASE,
            a,
            blocker_ids=["P1"],
            primitive_to_blockers=MAP,
            causal_links=[link("P1", "F1", implication_edge_ids=["E1"])],
        )
        self.assertTrue(o["admit"])

    def test_rejects_lower_bound_reduction_without_causal_event(self):
        a = dict(BASE)
        a["minimum_remaining_work_lower_bound"] = 39
        o = evaluate(BASE, a, blocker_ids=["P1"], primitive_to_blockers=MAP, causal_links=[link("P1", "F1")])
        self.assertFalse(o["admit"])
        self.assertIn("LOWER_BOUND_REDUCTION_WITHOUT_CAUSAL_CUT_EVENT", o["causal_link_errors"])

    def test_blocks_protected_regression_even_with_closure(self):
        a = dict(BASE)
        a["unresolved_primitive_facts"] = ["F2"]
        a["protected_terminal_facts"] = ["T1"]
        o = evaluate(BASE, a, blocker_ids=["P1"], primitive_to_blockers=MAP, causal_links=[link("P1", "F1")])
        self.assertFalse(o["admit"])
        self.assertIn("PROTECTED_TERMINAL_FACT_LOST", o["regressions"])

    def test_zero_authority(self):
        a = dict(BASE)
        a["unresolved_primitive_facts"] = ["F2"]
        o = evaluate(BASE, a, blocker_ids=["P1"], primitive_to_blockers=MAP, causal_links=[link("P1", "F1")])
        self.assertEqual(o["capability_credit_delta"], 0)
        self.assertFalse(o["execution_authority"])
        self.assertFalse(o["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
