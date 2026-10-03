from __future__ import annotations
import copy, unittest
from canonical.runtime import terminal_scheduling_v14_post_tool_discovery_v1 as v

class TerminalSchedulingV14PostToolDiscoveryTests(unittest.TestCase):
    def inputs(self):
        return dict(
          candidate=v.load(v.CANDIDATE),
          registry=v.load(v.PATHS["registry"]),
          evidence=v.load(v.PATHS["evidence"]),
          frontier=v.load(v.PATHS["frontier"]),
          hypergraph=v.load(v.PATHS["hypergraph"]),
          scheduling=v.load(v.PATHS["scheduling"]),
          authority=v.load(v.PATHS["authority"]),
          promotion=v.load(v.PATHS["promotion"]),
          receipt=v.load(v.PATHS["promotion_receipt"]),
        )
    def test_live_26_world(self):
        out=v.verify_repository()
        self.assertTrue(out["pass"],out)
        self.assertEqual((out["proved_predicates"],out["unresolved_predicates"]),(12,26))
        self.assertEqual((out["live_actions"],out["live_action_coverage"]),(20,26))
        self.assertEqual(out["uncovered_predicates"],[])
        self.assertEqual(out["tool_learning_success_route_noninferior"],"PROVED")
    def test_reopening_tool_discovery_fails_closed(self):
        x=self.inputs(); x["evidence"]=copy.deepcopy(x["evidence"])
        row=next(r for r in x["evidence"]["claims"] if r["predicate_id"]==v.TARGET)
        row["state"]="EXTERNAL_BLOCKED"
        out=v.evaluate_documents(**x)
        self.assertFalse(out["pass"],out)
    def test_live_tool_action_reintroduction_fails_closed(self):
        x=self.inputs(); x["hypergraph"]=copy.deepcopy(x["hypergraph"])
        x["hypergraph"]["actions"].append({"id":"ILLEGAL_TOOL_REPLAY","target_predicates":[v.TARGET],"preconditions":[]})
        out=v.evaluate_documents(**x)
        self.assertTrue(out["pass"],out)  # compiler must strip terminal target
        live={p for a in out["live_world"]["live_actions"] for p in a.get("target_predicates",[])}
        self.assertNotIn(v.TARGET,live)
    def test_failed_promotion_receipt_fails_closed(self):
        x=self.inputs(); x["receipt"]=copy.deepcopy(x["receipt"])
        x["receipt"]["public_runner"]["conclusion"]="failure"
        self.assertFalse(v.evaluate_documents(**x)["pass"])
    def test_no_execution_or_credit(self):
        out=v.verify_repository(); self.assertTrue(out["pass"],out)
        self.assertFalse(out["execution_authority"]); self.assertFalse(out["promotion_authority"]); self.assertFalse(out["fresh_reality_authority"])
        self.assertEqual(out["new_reality_units_consumed"],0)
        self.assertEqual(out["ownership_credit_delta"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
