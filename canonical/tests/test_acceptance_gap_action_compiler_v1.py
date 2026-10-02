from __future__ import annotations
import unittest
from canonical.runtime.acceptance_gap_action_compiler_v1 import evaluate

def fixture():
    families=[f"F{i}" for i in range(17)]
    preds=[{"id":f"P{i}","family":f,"kind":"PUBLIC_FIXED_BAR","surface":f"S{i}","acceptance":"x"} for i,f in enumerate(families)]
    registry={"residual_families":families,"predicates":preds}
    evidence={"saturation":{"status":"COMPLETE","source_snapshot_sha":"a"*40},"claims":[]}
    comparator={"exact_opus55_zero_incremental_route":False}
    readiness={"rows":[{"surface":f"S{i}","score_producing_route_ready":i==0} for i in range(17)]}
    actions={"actions":[
      {"id":"VERIFY","action_class":"VERIFY_GATE","effect":"UNLOCKS","critical_path":True,"new_reality_units":0,
       "target_predicates":["P0"],"preconditions":[{"id":"frozen","satisfied":True}]},
      {"id":"RUN","action_class":"REALITY_QUERY","effect":"ADVANCES","critical_path":True,"new_reality_units":1,
       "consumes_acceptance_case":True,"target_predicates":["P0"],"preconditions":[{"id":"verify","satisfied":False}]},
      {"id":"SEARCH","action_class":"PROOF_SEARCH","effect":"UNLOCKS","critical_path":False,"new_reality_units":0,
       "target_predicates":["P1","P2"],"preconditions":[]},
    ]}
    return registry,evidence,comparator,readiness,actions

class Tests(unittest.TestCase):
    def test_live_recompute_and_gap_states(self):
        out=evaluate(*fixture())
        self.assertTrue(out["pass"],out)
        g={x["predicate_id"]:x for x in out["gap_certificates"]}
        self.assertEqual(g["P0"]["gap_state"],"OPEN_EXECUTION_AUTHORIZED")
        self.assertEqual(g["P1"]["gap_state"],"BLOCKED")

    def test_critical_zero_reality_gate_selected(self):
        out=evaluate(*fixture())
        self.assertEqual(out["selected_action"]["id"],"VERIFY")
        self.assertEqual(out["selected_action"]["new_reality_units"],0)

    def test_reality_action_blocked_on_unsatisfied_precondition(self):
        out=evaluate(*fixture())
        run=next(a for a in out["actions"] if a["id"]=="RUN")
        self.assertFalse(run["executable"])

    def test_reality_action_requires_live_residual_authority(self):
        reg,ev,cmp,ready,actions=fixture()
        actions["actions"][1]["target_predicates"]=["P1"]
        actions["actions"][1]["preconditions"][0]["satisfied"]=True
        out=evaluate(reg,ev,cmp,ready,actions)
        run=next(a for a in out["actions"] if a["id"]=="RUN")
        self.assertFalse(run["executable"])
        self.assertIn("NO_OPEN_TARGET_FOR_REALITY_ACTION",run["authorization_errors"])

    def test_unknown_target_fails_closed(self):
        reg,ev,cmp,ready,actions=fixture()
        actions["actions"][0]["target_predicates"]=["NOPE"]
        out=evaluate(reg,ev,cmp,ready,actions)
        self.assertFalse(out["pass"])
        self.assertIn("ACTION_TARGET_INVALID:VERIFY",out["errors"])

if __name__=="__main__": unittest.main(verbosity=2)
