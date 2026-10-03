from __future__ import annotations
import copy,json,unittest
from pathlib import Path
from canonical.runtime.current_terminal_scheduling_world_v1 import evaluate

ROOT=Path(__file__).resolve().parents[2]
def load(rel): return json.loads((ROOT/rel).read_text(encoding="utf-8"))

class CurrentTerminalSchedulingWorldV1Tests(unittest.TestCase):
    def docs(self):
        return [
          load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
          load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
          load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"),
          load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json"),
          load("canonical/governance/TERMINAL_SCHEDULING_ACTIVATION_V6.json"),
          load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"),
        ]
    def live(self): return evaluate(*self.docs())
    def test_live_world_matches_current_authority(self):
        out=self.live(); self.assertTrue(out["pass"],out)
        authority=self.docs()[-1]["atomic_acceptance_frontier"]
        self.assertEqual(out["registry_predicate_count"],authority["total"])
        self.assertEqual(out["proved_predicate_count"],authority["proved"])
        self.assertEqual(out["unresolved_predicate_count"],authority["unresolved"])
        self.assertEqual(out["live_action_coverage_count"],authority["unresolved"])
        self.assertEqual(out["uncovered_predicates"],[])
    def test_closed_delegation_and_recovery_are_removed(self):
        out=self.live()
        closed={"DELEGATION_TERMINAL_SUCCESS_NONINFERIOR","RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR","RECOVERY_TERMINAL_NONINFERIOR","RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES"}
        for pid in closed:
            self.assertIn(pid,out["proved_predicates"]); self.assertNotIn(pid,out["unresolved_predicates"])
        self.assertIn("TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",out["unresolved_predicates"])
        live_targets={p for a in out["live_actions"] for p in a.get("target_predicates",[])}
        self.assertTrue(closed.isdisjoint(live_targets))
    def test_historical_world_is_explicitly_filtered(self):
        out=self.live(); self.assertTrue(out["source_scheduling_world_stale"])
        self.assertTrue(any("HISTORICAL" in x or "TERMINAL_TARGETS" in x for x in out["source_scheduling_world_stale_reasons"]))
    def test_compiler_cannot_grant_execution_or_credit(self):
        out=self.live(); self.assertFalse(out["execution_authority"]); self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["fresh_reality_authority"]); self.assertEqual(out["new_reality_units_consumed"],0)
        self.assertEqual(out["capability_credit_delta"],0); self.assertEqual(out["family_credit_delta"],0)
    def test_mutation_reopening_proved_predicate_fails_authority_crosscheck(self):
        docs=self.docs(); evidence=copy.deepcopy(docs[1])
        for claim in evidence["claims"]:
            if claim.get("predicate_id")=="RECOVERY_TERMINAL_NONINFERIOR":
                claim["state"]="EXTERNAL_BLOCKED"; break
        docs[1]=evidence; out=evaluate(*docs); self.assertFalse(out["pass"])
        self.assertTrue(any(x.startswith("PROVED_COUNT_NE_AUTHORITY") or x.startswith("UNRESOLVED_COUNT_NE_AUTHORITY") for x in out["errors"]))

if __name__=="__main__": unittest.main(verbosity=2)
