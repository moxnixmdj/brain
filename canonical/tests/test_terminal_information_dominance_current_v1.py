import json
from pathlib import Path
import unittest

from canonical.runtime.terminal_certificate_cut_v1 import evaluate as certificate_cut
from canonical.runtime.terminal_information_dominance_v1 import evaluate as information_dominance

ROOT = Path(__file__).resolve().parents[2]


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class Tests(unittest.TestCase):
    def test_reconciled_v3_frontier_and_stale_v2_quarantine(self):
        frontier = load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V3.json")
        self.assertEqual(len(frontier["unresolved_predicates"]), 31)
        self.assertEqual(len(frontier["certificates"]), 15)

        cut = certificate_cut(frontier)
        self.assertEqual(cut["status"], "EXACT_TERMINAL_CERTIFICATE_CUT_COMPUTED", cut)
        self.assertEqual(cut["unresolved_predicate_count"], 31, cut)
        self.assertEqual(cut["certificate_candidate_count"], 15, cut)
        self.assertEqual(cut["covered_predicate_count"], 31, cut)
        self.assertEqual(cut["uncovered_predicates"], [], cut)
        self.assertEqual(cut["selected_certificate_count"], 15, cut)
        self.assertEqual(cut["selected_new_reality_units"], 0, cut)

        info = information_dominance(frontier)
        self.assertEqual(info["status"], "EXACT_INFORMATION_DOMINANCE_COMPUTED", info)
        self.assertEqual(info["unresolved_predicate_count"], 31, info)
        self.assertEqual(info["certificate_count"], 15, info)
        self.assertTrue(info["reality_cost_degenerate_for_ordering"], info)
        self.assertEqual(info["highest_direct_coverage_count"], 11, info)
        self.assertEqual(
            info["highest_direct_coverage_certificate_ids"],
            ["MATCHED_SCOPE_BINDING_CERTIFICATE"],
            info,
        )
        self.assertEqual(info["capability_credit_delta"], 0)
        self.assertEqual(info["family_credit_delta"], 0)
        self.assertFalse(info["execution_authority"])
        self.assertFalse(info["promotion_authority"])

        activation = load("canonical/governance/TERMINAL_CERTIFICATE_CUT_ACTIVATION_V2.json")
        self.assertTrue(activation["status"].startswith("FAIL_CLOSED"), activation)
        self.assertEqual(
            activation["replacement_candidate"],
            "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V3.json",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
