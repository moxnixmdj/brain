from __future__ import annotations

import json
import unittest
from pathlib import Path

from canonical.runtime.current_terminal_scheduling_world_v1 import evaluate

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
        )

    def test_live_world_is_38_11_27(self):
        out = self.live()
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["registry_predicate_count"], 38)
        self.assertEqual(out["proved_predicate_count"], 11)
        self.assertEqual(out["unresolved_predicate_count"], 27)
        self.assertEqual(out["live_action_coverage_count"], 27)
        self.assertEqual(out["uncovered_predicates"], [])
        self.assertEqual(out["authority_opus55_acceptance"], "4/19_PASS__15/19_OPEN")

    def test_recovery_and_delegation_are_removed_but_tool_learning_remains_open(self):
        out = self.live()
        closed = {
            "DELEGATION_TERMINAL_SUCCESS_NONINFERIOR",
            "RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR",
            "RECOVERY_TERMINAL_NONINFERIOR",
            "RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES",
        }
        for pid in closed:
            self.assertIn(pid, out["proved_predicates"])
            self.assertNotIn(pid, out["unresolved_predicates"])
        self.assertIn("TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR", out["unresolved_predicates"])
        live_targets = {
            pid
            for action in out["live_actions"]
            for pid in action.get("target_predicates", [])
        }
        self.assertTrue(closed.isdisjoint(live_targets))
        self.assertIn("TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR", live_targets)

    def test_historical_world_is_explicitly_stale(self):
        out = self.live()
        self.assertTrue(out["source_scheduling_world_stale"])
        reasons = out["source_scheduling_world_stale_reasons"]
        self.assertTrue(any("31" in x and "27" in x for x in reasons), reasons)
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

    def test_mutation_reopening_recovery_fails_authority_crosscheck(self):
        registry = load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json")
        evidence = load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
        frontier = load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json")
        hypergraph = load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json")
        scheduling = load("canonical/governance/TERMINAL_SCHEDULING_ACTIVATION_V6.json")
        authority = load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
        for claim in evidence["claims"]:
            if claim.get("predicate_id") == "RECOVERY_TERMINAL_NONINFERIOR":
                claim["state"] = "EXTERNAL_BLOCKED"
                break
        out = evaluate(registry, evidence, frontier, hypergraph, scheduling, authority)
        self.assertFalse(out["pass"])
        self.assertIn("AUTHORITY_ATOMIC_PROVED_11_NE_LIVE_10", out["errors"])
        self.assertIn("AUTHORITY_ATOMIC_UNRESOLVED_27_NE_LIVE_28", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
