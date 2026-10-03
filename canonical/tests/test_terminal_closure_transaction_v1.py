from __future__ import annotations
import unittest
from canonical.runtime.terminal_closure_supertransaction_guard_v1 import SCHEMA,REQUIRED_STAGES,evaluate
A="a"*40; B="b"*40
def base():
    tx="TX1"
    return {"schema":SCHEMA,"source_root":A,"transaction_id":tx,
      "before":{"atomic_proved":8,"families_accepted":3,"composition_interfaces_proved":2,"protected_terminal_facts":["RAW_3352_PASS"]},
      "after":{"atomic_proved":9,"families_accepted":4,"composition_interfaces_proved":3,"composition_interaction_pass":False,"terminal_goal_achieved":False,"protected_terminal_facts":["RAW_3352_PASS"]},
      "stage_receipts":[{"stage":s,"path":"canonical/verification/"+s+".json","git_blob_sha":B,"status":"INDEPENDENT_PUBLIC_RUNNER_PASS","independent":True,"source_root":A,"transaction_id":tx} for s in sorted(REQUIRED_STAGES)]}
class T(unittest.TestCase):
    def test_partial_progress_can_commit_atomically(self):
        o=evaluate(base()); self.assertTrue(o["transaction_admissible"],o); self.assertFalse(o["terminal_goal_achieved"])
    def test_missing_stage_fails_closed(self):
        d=base(); d["stage_receipts"]=d["stage_receipts"][:-1]; self.assertEqual(evaluate(d)["status"],"FAIL_CLOSED")
    def test_mixed_root_fails_closed(self):
        d=base(); d["stage_receipts"][0]["source_root"]=B; self.assertEqual(evaluate(d)["status"],"FAIL_CLOSED")
    def test_regression_fails_closed(self):
        d=base(); d["after"]["atomic_proved"]=7; self.assertIn("ATOMIC_REGRESSION",evaluate(d)["errors"])
    def test_premature_terminal_true_fails_closed(self):
        d=base(); d["after"]["terminal_goal_achieved"]=True; self.assertIn("PREMATURE_TERMINAL_TRUE",evaluate(d)["errors"])
    def test_complete_closure_is_terminal(self):
        d=base(); d["after"].update({"atomic_proved":38,"families_accepted":19,"composition_interfaces_proved":12,"composition_interaction_pass":True,"terminal_goal_achieved":True})
        o=evaluate(d); self.assertTrue(o["transaction_admissible"],o); self.assertTrue(o["terminal_goal_achieved"])
    def test_complete_closure_cannot_stay_false(self):
        d=base(); d["after"].update({"atomic_proved":38,"families_accepted":19,"composition_interfaces_proved":12,"composition_interaction_pass":True,"terminal_goal_achieved":False})
        self.assertIn("TERMINAL_FALSE_DESPITE_COMPLETE_CLOSURE",evaluate(d)["errors"])
if __name__=="__main__": unittest.main(verbosity=2)
