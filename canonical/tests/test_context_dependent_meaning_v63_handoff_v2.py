from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
P={
 "r2":ROOT/"canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json",
 "root2":ROOT/"canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V59.json",
 "terminal":ROOT/"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json",
 "semrec":ROOT/"canonical/governance/R2_SEMANTIC_ACQUISITION_RESEARCH_RECONCILIATION_20261009_V7.json",
 "intent":ROOT/"canonical/action_intents/ACTION_INTENT_CONTEXT_DEPENDENT_MEANING_POSITIVE_COVERAGE_20261009_V7.json",
 "ledger":ROOT/"canonical/reasoning/2026-10-09_CONTEXT_DEPENDENT_MEANING_SUCCESSOR_EXECUTION_LEDGER_V4.json",
 "handoff":ROOT/"canonical/reasoning/2026-10-09_CONTEXT_DEPENDENT_MEANING_RESEARCH_HANDOFF_V8.json",
}
def load(k): return json.loads(P[k].read_text(encoding="utf-8"))
def blob(path):
 raw=path.read_bytes()
 return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.d={k:load(k) for k in P}

 def test_load_bearing_r2_root_are_exact(self):
  h=self.d["handoff"]["semantic_load_bearing_authority"]
  self.assertEqual(h["r2_pointer_git_blob_sha"],blob(P["r2"]))
  self.assertEqual(h["scheduler_cut_git_blob_sha"],blob(P["root2"]))
  self.assertIn("ACTIVE_CURRENT_R2_AUTHORITY__V63__",self.d["r2"]["status"])
  self.assertEqual(self.d["r2"]["scheduler_cut"]["git_blob_sha"],blob(P["root2"]))

 def test_terminal_projection_not_terminal_blob_is_required(self):
  term=self.d["terminal"]
  handoff=self.d["handoff"]
  self.assertFalse(handoff["terminal_projection_observation"]["load_bearing_for_context_dependent_meaning"])
  cur=term["authoritative_sources"]["current_r2_decision_intelligence"]
  self.assertEqual(cur["status"],self.d["r2"]["status"])
  self.assertEqual(cur["scheduler_cut"]["git_blob_sha"],blob(P["root2"]))
  self.assertEqual(term["live_truth"]["current_r2_pointer_git_blob_sha"],blob(P["r2"]))
  self.assertEqual(term["live_truth"]["current_r2_scheduler_cut"],"ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V59")

 def test_semantic_reconciliation_declares_mutable_terminal_policy(self):
  s=self.d["semrec"]
  pol=s["terminal_projection_policy"]
  self.assertFalse(pol["load_bearing_for_semantic_handoff"])
  self.assertEqual(s["semantic_load_bearing_authority"]["current_r2"]["git_blob_sha"],blob(P["r2"]))
  self.assertEqual(s["semantic_load_bearing_authority"]["scheduler_cut"]["git_blob_sha"],blob(P["root2"]))

 def test_action_intent_does_not_chase_terminal_revision(self):
  intent=self.d["intent"]
  self.assertFalse(intent["terminal_projection"]["load_bearing_for_context_meaning"])
  self.assertIn("SEMANTIC_RECONCILIATION_TRIGGERED_ONLY_BY_UNRELATED_TERMINAL_POINTER_REVISION",intent["forbidden_duplicate_work"])
  self.assertEqual(intent["semantic_reconciliation"]["git_blob_sha"],blob(P["semrec"]))

 def test_ledger_records_policy_repair(self):
  event=self.d["ledger"]["events"][0]
  self.assertEqual(event["order"],21)
  self.assertEqual(event["load_bearing_semantic_authority"]["current_r2_git_blob_sha"],blob(P["r2"]))
  self.assertEqual(event["load_bearing_semantic_authority"]["root2_v59_git_blob_sha"],blob(P["root2"]))

 def test_handoff_control_chain_is_content_addressed(self):
  controls=self.d["handoff"]["successor_controls"]
  self.assertEqual(controls["semantic_reconciliation"]["git_blob_sha"],blob(P["semrec"]))
  self.assertEqual(controls["action_intent"]["git_blob_sha"],blob(P["intent"]))
  self.assertEqual(controls["successor_execution_ledger"]["git_blob_sha"],blob(P["ledger"]))

 def test_zero_credit_and_open_residual_preserved(self):
  for k in ("semrec","intent","ledger","handoff"):
   acc=self.d[k]["accounting"]
   self.assertEqual(acc["acceptance_credit_delta"],0,k)
   self.assertEqual(acc["terminal_credit_delta"],0,k)
  self.assertIn("NO_CLAIM_FINANCE_SEMANTIC_TAIL_CLOSED",self.d["handoff"]["hard_nonclaims"])

if __name__=="__main__":
 unittest.main(verbosity=2)
