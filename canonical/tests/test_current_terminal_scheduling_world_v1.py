from __future__ import annotations

import json
import unittest
from pathlib import Path

from canonical.runtime.current_terminal_scheduling_world_v1 import evaluate
from canonical.runtime import tool_discovery_retrieval_authority_gate_v1 as retrieval_gate

ROOT = Path(__file__).resolve().parents[2]


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class CurrentTerminalSchedulingWorldV1Tests(unittest.TestCase):
    def live(self):
        return evaluate(
            load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
            load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
            load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"),
            load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json"),
            load("canonical/governance/TERMINAL_SCHEDULING_ACTIVATION_V6.json"),
            load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"),
            retrieval_gate.evaluate_repository(ROOT),
        )

    def test_live_world_is_38_8_30(self):
        out = self.live()
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["registry_predicate_count"], 38)
        self.assertEqual(out["proved_predicate_count"], 8)
        self.assertEqual(out["unresolved_predicate_count"], 30)
        self.assertEqual(out["live_action_coverage_count"], 30)
        self.assertEqual(out["uncovered_predicates"], [])

    def test_delegation_is_removed_but_tool_learning_remains_open(self):
        out = self.live()
        self.assertIn("DELEGATION_TERMINAL_SUCCESS_NONINFERIOR", out["proved_predicates"])
        self.assertNotIn("DELEGATION_TERMINAL_SUCCESS_NONINFERIOR", out["unresolved_predicates"])
        self.assertIn("TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR", out["unresolved_predicates"])
        live_targets = {
            pid
            for action in out["live_actions"]
            for pid in action.get("target_predicates", [])
        }
        self.assertNotIn("DELEGATION_TERMINAL_SUCCESS_NONINFERIOR", live_targets)
        self.assertIn("TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR", live_targets)

    def test_historical_31_world_is_explicitly_stale(self):
        out = self.live()
        self.assertTrue(out["source_scheduling_world_stale"])
        reasons = out["source_scheduling_world_stale_reasons"]
        self.assertTrue(any("31" in x and "30" in x for x in reasons), reasons)
        self.assertTrue(any("TERMINAL_TARGETS" in x for x in reasons), reasons)

    def test_compiler_cannot_grant_execution_or_credit(self):
        out = self.live()
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["fresh_reality_authority"])
        self.assertEqual(out["new_reality_units_consumed"], 0)
        self.assertEqual(out["incremental_spend_usd"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)

    def test_tool_discovery_retrieval_gate_is_mandatory(self):
        registry = load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")
        evidence = load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
        frontier = load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json")
        hypergraph = load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json")
        scheduling = load("canonical/governance/TERMINAL_SCHEDULING_ACTIVATION_V6.json")
        authority = load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
        out = evaluate(registry, evidence, frontier, hypergraph, scheduling, authority)
        self.assertFalse(out["pass"], out)
        self.assertIn("TOOL_DISCOVERY_RETRIEVAL_AUTHORITY_GATE_NOT_PASS", out["errors"])

    def test_live_world_reports_verified_tool_discovery_retrieval_gate(self):
        out = self.live()
        self.assertTrue(out["tool_discovery_retrieval_authority_gate_required"], out)
        self.assertTrue(out["tool_discovery_retrieval_authority_gate_pass"], out)
        self.assertIn(
            "PASS__LIVE_TOOL_DISCOVERY_EDGE_MECHANICALLY_BOUND",
            out["tool_discovery_retrieval_authority_gate_status"],
        )

    def test_mutation_reopening_delegation_changes_world_and_fails_expected_count(self):
        registry = load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")
        evidence = load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
        frontier = load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json")
        hypergraph = load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json")
        scheduling = load("canonical/governance/TERMINAL_SCHEDULING_ACTIVATION_V6.json")
        authority = load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
        for claim in evidence["claims"]:
            if claim.get("predicate_id") == "DELEGATION_TERMINAL_SUCCESS_NONINFERIOR":
                claim["state"] = "EXTERNAL_BLOCKED"
                break
        out = evaluate(
            registry,
            evidence,
            frontier,
            hypergraph,
            scheduling,
            authority,
            retrieval_gate.evaluate_repository(ROOT),
        )
        self.assertFalse(out["pass"])
        self.assertIn("UNRESOLVED_COUNT_NOT_30:31", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
