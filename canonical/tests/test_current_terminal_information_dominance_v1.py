from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.current_terminal_information_dominance_v1 import evaluate
from canonical.runtime import tool_discovery_retrieval_authority_gate_v1 as retrieval_gate

ROOT = Path(__file__).resolve().parents[2]


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class Tests(unittest.TestCase):
    def result(self):
        return evaluate(
            load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
            load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
            load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"),
            load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json"),
            load("canonical/governance/TERMINAL_SCHEDULING_ACTIVATION_V6.json"),
            load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"),
            load("canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V1.json"),
            retrieval_gate.evaluate_repository(ROOT),
        )

    def test_exact_live_world(self):
        x = self.result()
        self.assertTrue(x["pass"], x)
        s = x["live_world_summary"]
        self.assertEqual(
            (s["frozen_predicates"], s["proved_predicates"], s["unresolved_predicates"]),
            (38, 11, 27),
        )
        self.assertEqual(s["live_action_coverage_count"], 27)
        self.assertTrue(s["tool_discovery_retrieval_authority_gate_required"])
        self.assertTrue(s["tool_discovery_retrieval_authority_gate_pass"])

    def test_dominance_is_exact_and_current(self):
        x = self.result()
        d = x["dominance"]
        self.assertEqual(d["status"], "EXACT_INFORMATION_DOMINANCE_COMPUTED")
        self.assertEqual(d["unresolved_predicate_count"], 27)
        self.assertEqual(
            d["certificate_count"],
            x["live_world_summary"]["live_certificate_count"],
        )
        self.assertLessEqual(d["certificate_count"], 20)
        self.assertIsNotNone(d["best_full_frontier_bundle"])
        self.assertEqual(d["best_full_frontier_bundle"]["covered_predicate_count"], 27)

    def test_closed_targets_are_absent(self):
        x = self.result()
        ids = set(x["dominance"]["nondominated_certificate_ids"]) | set(
            x["dominance"]["dominated_certificate_ids"]
        )
        self.assertNotIn("DELEGATION_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE", ids)
        covered = {
            p
            for row in x["dominance"]["single_certificate_structural_front"]
            for p in row["covered_predicates"]
        }
        closed = {
            "DELEGATION_TERMINAL_SUCCESS_NONINFERIOR",
            "RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR",
            "RECOVERY_TERMINAL_NONINFERIOR",
            "RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES",
        }
        self.assertTrue(closed.isdisjoint(covered))
        self.assertIn("TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR", covered)

    def test_current_v9_pointer_is_required(self):
        args = [
            load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
            load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
            load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"),
            load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json"),
            load("canonical/governance/TERMINAL_SCHEDULING_ACTIVATION_V6.json"),
            load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"),
        ]
        bad = copy.deepcopy(load("canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V1.json"))
        bad["status"] = "HISTORICAL"
        out = evaluate(*args, bad, retrieval_gate.evaluate_repository(ROOT))
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__CURRENT_SCHEDULING_AUTHORITY_INVALID",
        )

    def test_missing_retrieval_gate_fails_closed(self):
        out = evaluate(
            load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
            load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
            load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"),
            load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json"),
            load("canonical/governance/TERMINAL_SCHEDULING_ACTIVATION_V6.json"),
            load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"),
            load("canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V1.json"),
            None,
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["status"], "FAIL_CLOSED__LIVE_WORLD_INVALID")
        self.assertIn(
            "TOOL_DISCOVERY_RETRIEVAL_AUTHORITY_GATE_NOT_PASS",
            out["live_world"]["errors"],
        )

    def test_zero_credit_zero_reality(self):
        x = self.result()
        self.assertEqual(x["new_reality_units_consumed"], 0)
        self.assertEqual(x["incremental_spend_usd"], 0)
        self.assertFalse(x["execution_authority"])
        self.assertFalse(x["promotion_authority"])
        self.assertFalse(x["fresh_reality_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
