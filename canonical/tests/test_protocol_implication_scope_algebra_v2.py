from __future__ import annotations

import unittest

from canonical.runtime.protocol_implication_scope_algebra_v2 import evaluate


def base():
    return {
        "target": {
            "scope_ref": "scope://target",
            "required_atoms": ["A", "B"],
            "metric_requirements": [
                {"metric": "score", "direction": "higher", "threshold": 0},
                {"metric": "misses", "direction": "lower", "threshold": 0},
            ],
        },
        "witness": {
            "scope_ref": "scope://witness",
            "verified": True,
            "independent": True,
            "contamination_clean": True,
            "proved_atoms": ["A"],
            "metric_bounds": {
                "score": {"lower": 0},
                "misses": {"upper": 0},
            },
        },
        "verified_implications": [
            {
                "if_all": ["A"],
                "then": ["B"],
                "verified": True,
                "independent": True,
                "receipt": "receipt://implication/a_to_b",
            }
        ],
        "verified_scope_relations": [
            {
                "witness_scope": "scope://witness",
                "target_scope": "scope://target",
                "relation": "SUPERSET",
                "verified": True,
                "independent": True,
                "receipt": "receipt://scope/witness_superset_target",
            }
        ],
    }


class Tests(unittest.TestCase):
    def test_verified_superset_scope_can_pass(self):
        out = evaluate(base())
        self.assertEqual(out["status"], "PASS")
        self.assertTrue(out["implies_target"])
        self.assertEqual(out["candidate_scope_relation"], "PROVEN_STRONGER")
        self.assertEqual(out["verified_scope_relation"], "SUPERSET")

    def test_exact_scope_exact_atoms_can_be_exact(self):
        d = base()
        d["witness"]["scope_ref"] = "scope://target"
        d["witness"]["proved_atoms"] = ["A", "B"]
        d["verified_implications"] = []
        d["verified_scope_relations"] = [{
            "witness_scope": "scope://target",
            "target_scope": "scope://target",
            "relation": "EXACT",
            "verified": True,
            "independent": True,
            "receipt": "receipt://scope/exact",
        }]
        out = evaluate(d)
        self.assertEqual(out["status"], "PASS")
        self.assertEqual(out["candidate_scope_relation"], "EXACT")

    def test_atom_and_metric_match_without_scope_relation_is_blocked(self):
        d = base()
        d["verified_scope_relations"] = []
        out = evaluate(d)
        self.assertEqual(out["status"], "TARGET_SCOPE_NOT_COVERED")
        self.assertFalse(out["implies_target"])

    def test_subset_scope_is_not_enough(self):
        d = base()
        d["verified_scope_relations"][0]["relation"] = "SUBSET"
        out = evaluate(d)
        self.assertEqual(out["status"], "TARGET_SCOPE_NOT_COVERED")
        self.assertFalse(out["implies_target"])

    def test_unverified_scope_relation_fails_closed(self):
        d = base()
        d["verified_scope_relations"][0]["verified"] = False
        out = evaluate(d)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("SCOPE_RELATION_0_NOT_INDEPENDENTLY_VERIFIED", out["errors"])

    def test_nonindependent_implication_fails_closed(self):
        d = base()
        d["verified_implications"][0]["independent"] = False
        out = evaluate(d)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("IMPLICATION_0_NOT_INDEPENDENTLY_VERIFIED", out["errors"])

    def test_missing_metric_stays_unproved_even_with_scope(self):
        d = base()
        del d["witness"]["metric_bounds"]["score"]
        out = evaluate(d)
        self.assertEqual(out["status"], "TARGET_NOT_IMPLIED")
        self.assertFalse(out["implies_target"])

    def test_narrow_realistic_witness_cannot_leak_into_broader_recovery_scope(self):
        d = {
            "target": {
                "scope_ref": "opus55://recovery/frozen_intervention_portfolio",
                "required_atoms": ["invariant:zero_critical_fail_closed_misses"],
                "metric_requirements": [
                    {"metric": "critical_fail_closed_misses", "direction": "lower", "threshold": 0}
                ],
            },
            "witness": {
                "scope_ref": "brain://execution_guard/13_case_deterministic_scope",
                "verified": True,
                "independent": True,
                "contamination_clean": True,
                "proved_atoms": ["invariant:zero_critical_fail_closed_misses"],
                "metric_bounds": {"critical_fail_closed_misses": {"upper": 0}},
            },
            "verified_implications": [],
            "verified_scope_relations": [],
        }
        out = evaluate(d)
        self.assertEqual(out["status"], "TARGET_SCOPE_NOT_COVERED")
        self.assertFalse(out["implies_target"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
