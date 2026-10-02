from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.terminal_next_action_compiler_v2 import compile_next_frontier_v2

ROOT = Path(__file__).resolve().parents[2]


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class TerminalNextActionCompilerV2Tests(unittest.TestCase):
    def docs(self):
        return (
            load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
            load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
            load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json"),
        )

    def test_live_v2_frontier_does_not_schedule_exhausted_synthesis(self):
        registry, evidence, hypergraph = self.docs()
        out = compile_next_frontier_v2(registry, evidence, hypergraph)
        self.assertEqual(out["status"], "PASS__DETERMINISTIC_FRONTIER__ZERO_CREDIT")
        self.assertEqual(out["source_hypergraph"], "OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2")
        self.assertEqual(out["proved_predicate_count"], 7)
        self.assertEqual(out["unresolved_predicate_count"], 31)
        self.assertEqual(out["primary_action_id"], "BUILD_DELEGATION_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE")
        self.assertEqual(out["primary_action_state"], "AVAILABLE_ZERO_REALITY")
        self.assertEqual(out["primary_unsatisfied_preconditions"], [])
        self.assertNotIn(
            "DISCHARGE_SYNTHESIS_EXACT_PROOF_DELTA",
            out["available_zero_reality_critical_actions"],
        )
        self.assertIn(
            "BUILD_DELEGATION_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE",
            out["available_zero_reality_critical_actions"],
        )
        self.assertIn(
            "BUILD_TOOL_DISCOVERY_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE",
            out["available_zero_reality_critical_actions"],
        )
        self.assertIn(
            "RAISE_TB4_ATTAINABILITY_UPPER_BOUND_WITHOUT_CASE_EXPOSURE",
            out["available_zero_reality_critical_actions"],
        )
        self.assertIn(
            "RUN_COMPOSITION_COMPONENT_PROOF_SLICER",
            out["available_zero_reality_critical_actions"],
        )
        blocked = {x["id"]: x for x in out["blocked_critical_actions"]}
        self.assertEqual(
            set(blocked["DISCHARGE_SYNTHESIS_EXACT_PROOF_DELTA"]["unsatisfied_preconditions"]),
            {
                "SYNTHESIS_MATCHED_TARGET_SCOPE_DISCHARGE_AVAILABLE",
                "SYNTHESIS_MATCHED_QUALITY_AND_NONINFERIORITY_BINDINGS_INDEPENDENT_PASS",
            },
        )
        self.assertEqual(out["highest_leverage_blocked_action_id"], "RUN_PROTOCOL_IMPLICATION_SCOPE_ALGEBRA")
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_synthesis_reopens_only_when_both_live_v2_preconditions_pass(self):
        registry, evidence, hypergraph = self.docs()
        mutated = copy.deepcopy(hypergraph)
        action = next(a for a in mutated["actions"] if a["id"] == "DISCHARGE_SYNTHESIS_EXACT_PROOF_DELTA")
        for p in action["preconditions"]:
            if p["id"] in {
                "SYNTHESIS_MATCHED_TARGET_SCOPE_DISCHARGE_AVAILABLE",
                "SYNTHESIS_MATCHED_QUALITY_AND_NONINFERIORITY_BINDINGS_INDEPENDENT_PASS",
            }:
                p["satisfied"] = True
        out = compile_next_frontier_v2(registry, evidence, mutated)
        self.assertIn("DISCHARGE_SYNTHESIS_EXACT_PROOF_DELTA", out["available_zero_reality_critical_actions"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
