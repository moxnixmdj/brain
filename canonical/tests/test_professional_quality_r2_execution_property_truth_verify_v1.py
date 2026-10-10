from __future__ import annotations
import copy,json
from pathlib import Path
import unittest
from canonical.runtime import professional_quality_r2_execution_property_truth_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]

def docs():
 out={}
 for key,(rel,_) in v.PINS.items():
  if key in {"manifest","catalog","scope_batch_verify","retrieval_authority","v19_verify"}:
   out[key]=json.loads((ROOT/rel).read_text(encoding="utf-8"))
 return out

class R2ExecutionPropertyTruthV1Tests(unittest.TestCase):
 def test_exact_current_r2_execution_acceptance_passes_one_leaf_only(self):
  out=v.verify()
  self.assertTrue(out["pass"],out)
  self.assertTrue(out["leaf_property_truth_authority"])
  self.assertTrue(all(out["checks"].values()))
  self.assertFalse(out["search_completeness_proved"])
  self.assertFalse(out["open_world_completeness_proved"])
  self.assertFalse(out["r2_semantic_leaf_closed"])
  self.assertFalse(out["r2_root_closed"])
  self.assertFalse(out["quality_authority"])
  self.assertFalse(out["terminal_authority"])

 def test_manifest_acceptance_drift_fails_closed(self):
  d=docs()
  row=next(x for x in d["manifest"]["roots"] if x["root_id"]==v.ROOT_ID)
  row["execution_leaf"]["acceptance"]="WEAKER"
  out=v.evaluate_documents(d["manifest"],d["catalog"],d["scope_batch_verify"],d["retrieval_authority"],d["v19_verify"])
  self.assertFalse(out["pass"])
  self.assertEqual(out["reason"],"R2_EXECUTION_ACCEPTANCE_DRIFT")

 def test_catalog_drift_fails_closed(self):
  d=docs()
  row=next(x for x in d["catalog"]["challenges"] if x["id"]=="C05_SEARCH_LINEAGE_FIXATION")
  row["root_ids"]=[]
  out=v.evaluate_documents(d["manifest"],d["catalog"],d["scope_batch_verify"],d["retrieval_authority"],d["v19_verify"])
  self.assertFalse(out["pass"])
  self.assertEqual(out["reason"],"R2_DEFEATER_CATALOG_DRIFT")

 def test_v19_answer_key_guard_is_load_bearing(self):
  d=docs()
  d["retrieval_authority"]=copy.deepcopy(d["retrieval_authority"])
  d["retrieval_authority"]["v19_verified_route_portfolio"]["answer_key_identity_permitted"]=True
  out=v.evaluate_documents(d["manifest"],d["catalog"],d["scope_batch_verify"],d["retrieval_authority"],d["v19_verify"])
  self.assertFalse(out["pass"])
  self.assertEqual(out["reason"],"CURRENT_RETRIEVAL_V19_AUTHORITY_NOT_BOUND")

 def test_empty_open_world_search_stays_unknown(self):
  program=v.core.compile_residual(v._residual())
  state=v.core.initial_state(program)
  for cell in list(state["cells"]):
   state=v.core.update_cell(state,query_id=cell["query_id"],surface=cell["surface"],cell_state="QUERIED_NO_CANDIDATE")
  out=v.core.terminal_status(state)
  self.assertEqual(out["status"],"UNKNOWN_CONTINUE_RETRIEVAL")
  self.assertFalse(out["stop"])
  self.assertFalse(out["nonexistence_claim_authorized"])

 def test_answer_key_identity_cannot_change_recovery_routes(self):
  action={"action_id":"A1","source_id":"MAVEN_CENTRAL","query":"decode legacy telemetry binary envelope with checksum support","language_variants":["bridge"]}
  sources=[{"source_id":"MAVEN_CENTRAL","source_class":"MAVEN","script":"ARABIC"}]
  a=v.portfolio.compile_portfolio([action],sources)
  poisoned=dict(action);poisoned["answer_key_identity"]="secret-perfect-candidate"
  b=v.portfolio.compile_portfolio([poisoned],sources)
  self.assertEqual(a,b)
  self.assertFalse(a["answer_key_identity_permitted"])
  self.assertFalse(a["open_world_nonexistence_claim_authorized"])

if __name__=="__main__":
 unittest.main(verbosity=2)
