from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from canonical.runtime import current_terminal_information_dominance_v2 as subject
from canonical.runtime import tool_discovery_retrieval_authority_gate_v1 as retrieval_gate_module

ROOT = Path(__file__).resolve().parents[2]


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def args():
    return (
        load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
        load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
        load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"),
        load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json"),
        load("canonical/governance/TERMINAL_SCHEDULING_ACTIVATION_V6.json"),
        load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"),
        retrieval_gate_module.evaluate_repository(ROOT),
        load("canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V1.json"),
    )


class CurrentTerminalInformationDominanceV2Tests(unittest.TestCase):
    def test_current_repository_passes_38_11_27(self):
        out = subject.evaluate(*args())
        self.assertTrue(out["pass"], out)
        s = out["live_world_summary"]
        self.assertEqual(
            (s["frozen_predicates"], s["proved_predicates"], s["unresolved_predicates"]),
            (38, 11, 27),
        )
        self.assertEqual(s["live_action_coverage_count"], 27)
        self.assertTrue(s["tool_discovery_retrieval_gate_required"])
        self.assertTrue(s["tool_discovery_retrieval_gate_pass"])
        self.assertTrue(out["tool_discovery_target_open"])

    def test_recovery_and_delegation_are_absent_from_live_dominance(self):
        out = subject.evaluate(*args())
        self.assertTrue(out["pass"], out)
        front = out["dominance"]["single_certificate_structural_front"]
        covered = {
            p
            for row in front
            for p in row["covered_predicates"]
        }
        for pid in subject.RECOVERY_PROVED | {subject.DELEGATION_PROVED}:
            self.assertNotIn(pid, covered)
        self.assertIn(subject.TOOL_TARGET, covered)
        ids = {row["certificate_id"] for row in front}
        self.assertNotIn("DELEGATION_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE", ids)

    def test_full_bundle_covers_exact_live_27(self):
        out = subject.evaluate(*args())
        self.assertTrue(out["pass"], out)
        d = out["dominance"]
        self.assertEqual(d["status"], "EXACT_INFORMATION_DOMINANCE_COMPUTED")
        self.assertEqual(d["unresolved_predicate_count"], 27)
        self.assertEqual(d["best_full_frontier_bundle"]["covered_predicate_count"], 27)

    def test_missing_retrieval_gate_fails_closed(self):
        a = list(args())
        a[6] = {
            "schema": retrieval_gate_module.SCHEMA,
            "pass": False,
            "target_predicate": retrieval_gate_module.TARGET,
        }
        out = subject.evaluate(*a)
        self.assertFalse(out["pass"], out)
        self.assertIn("MANDATORY_TOOL_DISCOVERY_RETRIEVAL_GATE_NOT_PASS", out["errors"])

    def test_scheduler_pointer_without_mandatory_gate_fails_closed(self):
        a = list(args())
        sched = copy.deepcopy(a[7])
        sched["mandatory_tool_discovery_retrieval"]["mandatory"] = False
        a[7] = sched
        out = subject.evaluate(*a)
        self.assertFalse(out["pass"], out)
        self.assertIn("CURRENT_SCHEDULING_RETRIEVAL_NOT_MANDATORY", out["errors"])

    def test_scheduler_pointer_allowing_bypass_fails_closed(self):
        a = list(args())
        sched = copy.deepcopy(a[7])
        sched["mandatory_tool_discovery_retrieval"]["direct_bypass_allowed"] = True
        a[7] = sched
        out = subject.evaluate(*a)
        self.assertFalse(out["pass"], out)
        self.assertIn("CURRENT_SCHEDULING_DIRECT_BYPASS_NOT_DISABLED", out["errors"])

    def test_consumed_epoch_replay_permission_fails_closed(self):
        a = list(args())
        sched = copy.deepcopy(a[7])
        sched["mandatory_tool_discovery_retrieval"]["consumed_source_epoch_replay_allowed"] = True
        a[7] = sched
        out = subject.evaluate(*a)
        self.assertFalse(out["pass"], out)
        self.assertIn("CURRENT_SCHEDULING_EPOCH_REPLAY_NOT_DISABLED", out["errors"])

    def test_no_credit_no_reality(self):
        out = subject.evaluate(*args())
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["new_reality_units_consumed"], 0)
        self.assertEqual(out["incremental_spend_usd"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["fresh_reality_authority"])
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
