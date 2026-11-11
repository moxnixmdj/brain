from __future__ import annotations

import copy
import unittest

from canonical.runtime.tool_discovery_matched_route_graph_v1 import (
    ACTION_ID,
    CERT_ID,
    TARGET_FAMILY,
    _find_by_key_value,
    _load,
    CORRECTION,
    FRONTIER,
    HYPERGRAPH,
    PROTOCOLS,
    TOOLATHLON,
    evaluate,
)


class ToolDiscoveryMatchedRouteGraphV1Tests(unittest.TestCase):
    def setUp(self):
        self.protocols = _load(PROTOCOLS)
        self.frontier = _load(FRONTIER)
        self.hypergraph = _load(HYPERGRAPH)
        self.toolathlon = _load(TOOLATHLON)
        self.correction = _load(CORRECTION)

    def test_live_sources_prove_graph_omission_without_granting_acceptance(self):
        out = evaluate(
            self.protocols,
            self.frontier,
            self.hypergraph,
            self.toolathlon,
            self.correction,
        )
        self.assertTrue(out["matched_noninferiority_semantics_proved"])
        self.assertTrue(out["active_graph_absolute_route_only"])
        self.assertTrue(out["scheduler_note_preserves_later_frozen_target_instantiation"])
        self.assertTrue(out["graph_correction_proved"])
        self.assertTrue(out["matched_route_logically_available"])
        self.assertFalse(out["matched_route_satisfied"])
        self.assertEqual(out["new_reality_units_consumed"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_matched_acceptance_semantics_are_load_bearing(self):
        mutant = copy.deepcopy(self.protocols)
        protocol = _find_by_key_value(mutant, "family", TARGET_FAMILY)
        self.assertIsNotNone(protocol)
        protocol["acceptance"] = "UNRELATED_ACCEPTANCE"
        out = evaluate(mutant, self.frontier, self.hypergraph, self.toolathlon, self.correction)
        self.assertFalse(out["graph_correction_proved"])
        self.assertIn(
            "MATCHED_NONINFERIORITY_SEMANTICS_NOT_PROVED_FROM_FROZEN_PROTOCOL",
            out["errors"],
        )

    def test_existing_absolute_route_must_not_be_deleted(self):
        mutant = copy.deepcopy(self.correction)
        mutant["proof_routes"] = [
            row
            for row in mutant["proof_routes"]
            if row.get("route_id") != "ABSOLUTE_DOMINANCE_SCOPE_ROUTE"
        ]
        out = evaluate(self.protocols, self.frontier, self.hypergraph, self.toolathlon, mutant)
        self.assertFalse(out["graph_correction_proved"])
        self.assertIn("CORRECTION_DROPS_EXISTING_ABSOLUTE_ROUTE", out["errors"])

    def test_scheduler_admission_of_later_target_is_load_bearing(self):
        mutant = copy.deepcopy(self.hypergraph)
        action = _find_by_key_value(mutant, "id", ACTION_ID)
        self.assertIsNotNone(action)
        action["notes"] = "Search only for universal formal scope proof."
        out = evaluate(self.protocols, self.frontier, mutant, self.toolathlon, self.correction)
        self.assertFalse(out["graph_correction_proved"])
        self.assertIn(
            "SCHEDULER_DOES_NOT_PRESERVE_LATER_FROZEN_TARGET_ROUTE",
            out["errors"],
        )

    def test_current_certificate_really_is_absolute_only(self):
        mutant = copy.deepcopy(self.frontier)
        cert = _find_by_key_value(mutant, "id", CERT_ID)
        self.assertIsNotNone(cert)
        cert["certificate_class"] = "MATCHED_TARGET"
        out = evaluate(self.protocols, mutant, self.hypergraph, self.toolathlon, self.correction)
        self.assertFalse(out["graph_correction_proved"])
        self.assertIn(
            "ACTIVE_CERTIFICATE_IS_NOT_THE_EXPECTED_ABSOLUTE_ONLY_ROUTE",
            out["errors"],
        )

    def test_existing_toolathlon_freeze_is_only_candidate_input_not_credit(self):
        out = evaluate(
            self.protocols,
            self.frontier,
            self.hypergraph,
            self.toolathlon,
            self.correction,
        )
        self.assertTrue(out["existing_candidate_frozen_target"]["pre_task_freeze_bound"])
        self.assertGreater(out["existing_candidate_frozen_target"]["open_precondition_count"], 0)
        self.assertFalse(out["matched_route_satisfied"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
