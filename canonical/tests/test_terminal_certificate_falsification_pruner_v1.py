from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.terminal_certificate_falsification_pruner_v1 import (
    apply_falsification_overlay,
)

ROOT = Path(__file__).resolve().parents[2]


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class Tests(unittest.TestCase):
    def test_live_tb4_falsification_prunes_impossible_route_and_preserves_target(self):
        frontier = load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json")
        overlay = load("canonical/governance/TERMINAL_CERTIFICATE_FALSIFICATION_OVERLAY_V1.json")
        refinement = load("canonical/governance/PROOF_ATOM_REFINEMENT_OVERLAY_V1.json")
        out = apply_falsification_overlay(
            frontier, overlay, refinement_overlay=refinement
        )
        self.assertTrue(out["status"].startswith("PASS"), out)
        self.assertEqual(out["input_unresolved_predicate_count"], 31)
        self.assertEqual(out["input_certificate_count"], 17)
        self.assertEqual(out["active_certificate_count"], 16)
        self.assertEqual(out["pruned_certificate_ids"], ["TB4_ATTAINABLE_ROUTE_CERTIFICATE"])
        self.assertEqual(out["covered_predicate_count_after_pruning"], 30)
        self.assertEqual(
            out["uncovered_predicates_after_pruning"], ["CODING_TB4_GE_66_4"]
        )
        self.assertNotIn(
            "TB4_ATTAINABLE_ROUTE_CERTIFICATE",
            out["selected_certificate_ids_after_pruning"],
        )
        self.assertEqual(out["executable_leaf_atom_count_after_pruning"], 39)
        self.assertEqual(
            out["executable_leaf_requirement_occurrence_count_after_pruning"], 39
        )
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_requirement_mismatch_fails_closed(self):
        frontier = load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json")
        overlay = load("canonical/governance/TERMINAL_CERTIFICATE_FALSIFICATION_OVERLAY_V1.json")
        bad = copy.deepcopy(overlay)
        bad["falsified_certificate_routes"][0]["falsified_requirement"] = "NOT_THE_TB4_REQUIREMENT"
        out = apply_falsification_overlay(frontier, bad)
        self.assertEqual(out["status"], "FAIL_CLOSED")

    def test_target_mismatch_fails_closed(self):
        frontier = load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json")
        overlay = load("canonical/governance/TERMINAL_CERTIFICATE_FALSIFICATION_OVERLAY_V1.json")
        bad = copy.deepcopy(overlay)
        bad["falsified_certificate_routes"][0]["target_predicates"] = ["HLE_TOOLS_GE_67_7"]
        out = apply_falsification_overlay(frontier, bad)
        self.assertEqual(out["status"], "FAIL_CLOSED")

    def test_route_falsification_cannot_claim_target_falsification(self):
        frontier = load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json")
        overlay = load("canonical/governance/TERMINAL_CERTIFICATE_FALSIFICATION_OVERLAY_V1.json")
        bad = copy.deepcopy(overlay)
        bad["falsified_certificate_routes"][0]["target_predicate_falsified"] = True
        out = apply_falsification_overlay(frontier, bad)
        self.assertEqual(out["status"], "FAIL_CLOSED")

    def test_independent_verification_is_mandatory(self):
        frontier = load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json")
        overlay = load("canonical/governance/TERMINAL_CERTIFICATE_FALSIFICATION_OVERLAY_V1.json")
        bad = copy.deepcopy(overlay)
        bad["falsified_certificate_routes"][0]["independent_verified"] = False
        out = apply_falsification_overlay(frontier, bad)
        self.assertEqual(out["status"], "FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
