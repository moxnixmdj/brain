from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.terminal_next_action_compiler_v1 import compile_next_frontier

ROOT = Path(__file__).resolve().parents[2]


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class TerminalNextActionCompilerTests(unittest.TestCase):
    def docs(self):
        return (
            load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
            load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
            load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json"),
            load("canonical/governance/TOOL_DISCOVERY_SCOPE_FORMALISM_CUT_ACTIVATION_V1.json"),
        )

    def test_live_frontier_fails_closed_on_semantic_gate(self):
        registry, evidence, hypergraph, tool_discovery_scope_cut = self.docs()
        out = compile_next_frontier(registry, evidence, hypergraph, tool_discovery_scope_cut)
        self.assertEqual(out["status"], "PASS__DETERMINISTIC_FRONTIER__ZERO_CREDIT")
        self.assertEqual(out["proved_predicate_count"], 8)
        self.assertEqual(out["unresolved_predicate_count"], 30)
        self.assertEqual(out["primary_action_id"], "RAISE_TB4_ATTAINABILITY_UPPER_BOUND_WITHOUT_CASE_EXPOSURE")
        self.assertEqual(out["primary_action_state"], "AVAILABLE_ZERO_REALITY")
        self.assertEqual(out["primary_unsatisfied_preconditions"], [])
        self.assertEqual(out["highest_leverage_blocked_action_id"], "RUN_PROTOCOL_IMPLICATION_SCOPE_ALGEBRA")
        self.assertEqual(out["highest_leverage_blocked_action_target_count"], 11)
        self.assertEqual(
            set(out["highest_leverage_blocked_action_preconditions"]),
            {
                "MATCHED_BRAIN_WITNESS_TARGET_ATOM_METRIC_BINDINGS_INDEPENDENT_PASS",
                "MATCHED_BRAIN_WITNESS_SCOPE_RELATIONS_INDEPENDENT_PASS",
            },
        )
        self.assertNotIn("DISCHARGE_SYNTHESIS_EXACT_PROOF_DELTA", out["available_zero_reality_critical_actions"])
        self.assertIn("RUN_COMPOSITION_COMPONENT_PROOF_SLICER", out["available_zero_reality_critical_actions"])
        self.assertIn("RAISE_TB4_ATTAINABILITY_UPPER_BOUND_WITHOUT_CASE_EXPOSURE", out["available_zero_reality_critical_actions"])
        self.assertNotIn("BUILD_TOOL_DISCOVERY_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE", out["available_zero_reality_critical_actions"])
        self.assertEqual(out["active_action_cuts"], {"BUILD_TOOL_DISCOVERY_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE": "TOOL_DISCOVERY_SCOPE_FORMALISM_CUT_20261003"})
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_primary_becomes_available_only_after_atom_metric_binding_gate_passes(self):
        registry, evidence, hypergraph, tool_discovery_scope_cut = self.docs()
        mutated = copy.deepcopy(hypergraph)
        action = next(a for a in mutated["actions"] if a["id"] == "RUN_PROTOCOL_IMPLICATION_SCOPE_ALGEBRA")
        for p in action["preconditions"]:
            if p["id"] in {"MATCHED_BRAIN_WITNESS_TARGET_ATOM_METRIC_BINDINGS_INDEPENDENT_PASS", "MATCHED_BRAIN_WITNESS_SCOPE_RELATIONS_INDEPENDENT_PASS"}:
                p["satisfied"] = True
        out = compile_next_frontier(registry, evidence, mutated, tool_discovery_scope_cut)
        self.assertEqual(out["primary_action_id"], "RUN_PROTOCOL_IMPLICATION_SCOPE_ALGEBRA")
        self.assertEqual(out["primary_action_state"], "AVAILABLE_ZERO_REALITY")
        self.assertEqual(out["primary_unsatisfied_preconditions"], [])
        self.assertNotEqual(out["highest_leverage_blocked_action_id"], "RUN_PROTOCOL_IMPLICATION_SCOPE_ALGEBRA")


if __name__ == "__main__":
    unittest.main(verbosity=2)
