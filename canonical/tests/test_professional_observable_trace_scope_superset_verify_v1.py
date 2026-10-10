from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_observable_trace_scope_superset_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]
def load(path): return json.loads((ROOT/path).read_text(encoding="utf-8"))
def docs():
 c=load(v.CANDIDATE)
 return c,load(v.SOURCE_THEOREM[0]),load(v.SOURCE_VERIFY[0]),load(v.CONTRACTS[0]),load(v.GRAPH[0]),load(v.MANIFEST[0])

class Tests(unittest.TestCase):
 def test_current_exact_professional_domain_passes_scope_only(self):
  o=v.verify()
  self.assertTrue(o["pass"],o)
  self.assertTrue(o["professional_domain_trace_containment_verified"])
  self.assertFalse(o["per_leaf_positive_adequacy_proved"])
  self.assertEqual(o["verified_global_leaf_count"],0)
  self.assertFalse(o["professional_quality_closed"])
  self.assertFalse(o["terminal_authority"])

 def test_contract_drift_fails_closed(self):
  c,s,sv,r,g,m=docs();r=deepcopy(r)
  row=next(x for x in r["active_contracted_residuals"] if x["behavior_id"]==v.BEHAVIOR)
  row["scope"]="DIFFERENT"
  self.assertTrue(v.evaluate_documents(c,s,sv,r,g,m)["reason"].startswith("CONTRACT_DRIFT:"))

 def test_missing_trace_event_fails_closed(self):
  c,s,sv,r,g,m=docs();c=deepcopy(c)
  c["trace_superdomain"]["event_basis"]=c["trace_superdomain"]["event_basis"][:-1]
  self.assertEqual(v.evaluate_documents(c,s,sv,r,g,m)["reason"],"TRACE_EVENT_BASIS_MISMATCH")

 def test_source_dominance_may_not_be_falsely_closed(self):
  c,s,sv,r,g,m=docs();s=deepcopy(s)
  s["critical_split"]["current_acceptance_basis_universal_dominance_state"]="CLOSED"
  self.assertEqual(v.evaluate_documents(c,s,sv,r,g,m)["reason"],"SOURCE_DOMINANCE_BOUNDARY_INVALID")

 def test_leaf_adequacy_overclaim_fails(self):
  c,s,sv,r,g,m=docs();c=deepcopy(c)
  c["current_effect"]["per_leaf_positive_adequacy_over_carrier_proved"]=True
  self.assertEqual(v.evaluate_documents(c,s,sv,r,g,m)["reason"],"OVERCLAIM:per_leaf_positive_adequacy_over_carrier_proved")

 def test_quality_closure_overclaim_fails(self):
  c,s,sv,r,g,m=docs();c=deepcopy(c)
  c["current_effect"]["professional_quality_closed"]=True
  self.assertEqual(v.evaluate_documents(c,s,sv,r,g,m)["reason"],"OVERCLAIM:professional_quality_closed")

 def test_wrong_professional_domain_fails(self):
  c,s,sv,r,g,m=docs();g=deepcopy(g);g["domain"]="OTHER"
  self.assertEqual(v.evaluate_documents(c,s,sv,r,g,m)["reason"],"ASSURANCE_GRAPH_DOMAIN_MISMATCH")

 def test_self_authority_fails(self):
  c,s,sv,r,g,m=docs();c=deepcopy(c);c["quality_authority"]=True
  self.assertEqual(v.evaluate_documents(c,s,sv,r,g,m)["reason"],"SELF_AUTHORITY_FORBIDDEN:quality_authority")

 def test_leaf_receipt_credit_cannot_appear_from_scope_theorem(self):
  c,s,sv,r,g,m=docs();c=deepcopy(c);c["current_effect"]["exact_leaf_receipts_proved"]=1
  self.assertEqual(v.evaluate_documents(c,s,sv,r,g,m)["reason"],"LEAF_RECEIPT_CREDIT_FORBIDDEN")

if __name__=="__main__":unittest.main(verbosity=2)
