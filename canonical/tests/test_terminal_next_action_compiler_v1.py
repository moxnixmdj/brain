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
            load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V1.json"),
        )

    def test_live_frontier_fails_closed_on_semantic_gate(self):
        registry, evidence, hypergraph = self.docs()
        out = compile_next_frontier(registry, evidence, hypergraph)
        self.assertEqual(out["status"], "PASS__DETERMINISTIC_FRONTIER__ZERO_CREDIT")

        # The counts used to be pinned as 7 and 31. They are a snapshot of how
        # much of the frontier has been discharged, so they went stale the
        # moment more predicates were proved. Derive them from the evidence
        # bindings instead: that keeps the real invariant -- the compiler must
        # account for every registered predicate exactly once, splitting them
        # into proved and unresolved -- without going red as the repo advances.
        proved = {c["predicate_id"] for c in evidence["claims"] if c.get("state") == "PROVED"}
        self.assertEqual(out["proved_predicate_count"], len(proved))
        self.assertEqual(
            out["proved_predicate_count"] + out["unresolved_predicate_count"],
            len(registry["predicates"]),
        )

        # the primary action must actually be available: no unsatisfied
        # preconditions, and listed among the zero-reality critical actions
        self.assertEqual(out["primary_action_state"], "AVAILABLE_ZERO_REALITY")
        self.assertEqual(out["primary_unsatisfied_preconditions"], [])
        self.assertIn(out["primary_action_id"], out["available_zero_reality_critical_actions"])

        # and the highest-leverage blocked action must genuinely be blocked
        self.assertGreater(out["highest_leverage_blocked_action_target_count"], 0)
        self.assertNotEqual(out["highest_leverage_blocked_action_id"], out["primary_action_id"])
        self.assertTrue(
            out["highest_leverage_blocked_action_preconditions"],
            "the highest-leverage blocked action reports no precondition blocking it",
        )

        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_primary_becomes_available_only_after_atom_metric_binding_gate_passes(self):
        registry, evidence, hypergraph = self.docs()
        mutated = copy.deepcopy(hypergraph)
        action = next(a for a in mutated["actions"] if a["id"] == "RUN_PROTOCOL_IMPLICATION_SCOPE_ALGEBRA")
        for p in action["preconditions"]:
            if p["id"] in {"MATCHED_BRAIN_WITNESS_TARGET_ATOM_METRIC_BINDINGS_INDEPENDENT_PASS", "MATCHED_BRAIN_WITNESS_SCOPE_RELATIONS_INDEPENDENT_PASS"}:
                p["satisfied"] = True
        out = compile_next_frontier(registry, evidence, mutated)
        self.assertEqual(out["primary_action_id"], "RUN_PROTOCOL_IMPLICATION_SCOPE_ALGEBRA")
        self.assertEqual(out["primary_action_state"], "AVAILABLE_ZERO_REALITY")
        self.assertEqual(out["primary_unsatisfied_preconditions"], [])
        self.assertNotEqual(out["highest_leverage_blocked_action_id"], "RUN_PROTOCOL_IMPLICATION_SCOPE_ALGEBRA")


if __name__ == "__main__":
    unittest.main(verbosity=2)
