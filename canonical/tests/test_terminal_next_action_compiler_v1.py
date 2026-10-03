from __future__ import annotations
import copy,json,unittest
from pathlib import Path
from canonical.runtime.terminal_next_action_compiler_v1 import compile_next_frontier

ROOT=Path(__file__).resolve().parents[2]
def load(rel): return json.loads((ROOT/rel).read_text(encoding="utf-8"))

class TerminalNextActionCompilerTests(unittest.TestCase):
    def docs(self):
        return (
          load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
          load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
          load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V1.json"),
        )
    def test_live_frontier_matches_current_evidence(self):
        registry,evidence,hypergraph=self.docs()
        out=compile_next_frontier(registry,evidence,hypergraph)
        self.assertTrue(out["status"].startswith("PASS"),out)
        proved={c["predicate_id"] for c in evidence["claims"] if c.get("state")=="PROVED"}
        self.assertEqual(out["proved_predicate_count"],len(proved))
        self.assertEqual(out["unresolved_predicate_count"],len(registry["predicates"])-len(proved))
        if out["primary_action_id"] is not None:
            self.assertIn(out["primary_action_state"],{"AVAILABLE_ZERO_REALITY","AVAILABLE"})
            self.assertEqual(out["primary_unsatisfied_preconditions"],[])
            self.assertTrue(set(out["primary_unresolved_targets"]).isdisjoint(proved))
        if out["available_zero_reality_actions"]:
            self.assertIn(out["primary_action_id"],out["available_zero_reality_actions"])
        self.assertFalse(out["execution_authority"]); self.assertFalse(out["promotion_authority"])
    def test_closed_recovery_and_delegation_never_remain_action_targets(self):
        registry,evidence,hypergraph=self.docs()
        out=compile_next_frontier(registry,evidence,hypergraph)
        closed={
          "DELEGATION_TERMINAL_SUCCESS_NONINFERIOR",
          "RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR",
          "RECOVERY_TERMINAL_NONINFERIOR",
          "RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES",
        }
        self.assertTrue(closed.issubset({c["predicate_id"] for c in evidence["claims"] if c.get("state")=="PROVED"}))
        self.assertTrue(closed.isdisjoint(out["primary_unresolved_targets"]))
    def test_proving_an_open_predicate_removes_it_from_live_targets(self):
        registry,evidence,hypergraph=self.docs()
        baseline=compile_next_frontier(registry,evidence,hypergraph)
        mutated=copy.deepcopy(evidence)
        pid="TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
        row=next(c for c in mutated["claims"] if c.get("predicate_id")==pid)
        self.assertNotEqual(row.get("state"),"PROVED")
        row["state"]="PROVED"
        out=compile_next_frontier(registry,mutated,hypergraph)
        self.assertEqual(out["proved_predicate_count"],baseline["proved_predicate_count"]+1)
        self.assertEqual(out["unresolved_predicate_count"],baseline["unresolved_predicate_count"]-1)
        for action_id in out["available_zero_reality_actions"]:
            action=next(a for a in compile_next_frontier(registry,mutated,hypergraph).get("available_zero_reality_actions",[]) if a==action_id)
            self.assertIsInstance(action,str)
        self.assertNotIn(pid,out["primary_unresolved_targets"])
    def test_blocked_action_is_never_reported_as_executable_primary(self):
        registry,evidence,hypergraph=self.docs()
        out=compile_next_frontier(registry,evidence,hypergraph)
        if out["primary_action_id"] is not None:
            blocked={x["id"] for x in out["blocked_critical_actions"]}
            self.assertNotIn(out["primary_action_id"],blocked)

if __name__=="__main__": unittest.main(verbosity=2)
