from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_r10_semantic_property_truth_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]

def docs():
 out={}
 for key in ("manifest","scope_batch_verify","semantic_source","semantic_history","constitution","catalog","profile"):
  rel,_=v.PINS[key]
  out[key]=json.loads((ROOT/rel).read_text(encoding="utf-8"))
 return out

def evaluate(d):
 return v.evaluate_documents(
  d["manifest"],d["scope_batch_verify"],d["semantic_source"],d["semantic_history"],
  d["constitution"],d["catalog"],d["profile"],
 )

class R10SemanticPropertyTruthV1Tests(unittest.TestCase):
 def test_real_exact_bound_r10_semantic_acceptance_passes_one_leaf_only(self):
  out=v.verify()
  self.assertTrue(out["pass"],out)
  self.assertTrue(out["leaf_property_truth_authority"])
  self.assertTrue(out["r10_semantic_leaf_closed"])
  self.assertEqual(out["typed_defeater_resolution_count"],17)
  self.assertFalse(out["detection_completeness_proved"])
  self.assertFalse(out["r10_root_closed"])
  self.assertFalse(out["quality_authority"])
  self.assertFalse(out["terminal_authority"])

 def test_manifest_acceptance_drift_fails_closed(self):
  d=docs()
  row=next(x for x in d["manifest"]["roots"] if x["root_id"]==v.ROOT_ID)
  row["semantic_leaf"]["acceptance"]="WEAKER_ACCEPTANCE"
  out=evaluate(d)
  self.assertFalse(out["pass"])
  self.assertEqual(out["reason"],"R10_SEMANTIC_ACCEPTANCE_DRIFT")

 def test_scope_batch_must_cover_all_24(self):
  d=docs()
  d["scope_batch_verify"]["independent_replay"]["scope_complete_count"]=23
  out=evaluate(d)
  self.assertFalse(out["pass"])
  self.assertEqual(out["reason"],"WHOLE_LEAF_SCOPE_BATCH_NOT_ADMISSIBLE")

 def test_catalog_loss_fails_closed(self):
  d=docs()
  rows=d["catalog"].get("defeaters") or []
  target=next(x for x in rows if x.get("id")=="C48_ANALYSIS_CHERRY_PICK")
  target["root_ids"]=[x for x in target["root_ids"] if x!=v.ROOT_ID]
  out=evaluate(d)
  self.assertFalse(out["pass"])
  self.assertEqual(out["reason"],"R10_DEFEATER_CATALOG_NOT_EXACT")

 def test_risk_policy_weakening_fails_closed(self):
  d=docs()
  d["constitution"]["safe_default_modes"]["unbound_risk_policy"]="INVENT_THRESHOLD"
  out=evaluate(d)
  self.assertFalse(out["pass"])
  self.assertEqual(out["reason"],"R10_CONSTITUTION_SEMANTICS_INCOMPLETE")

 def test_normative_weights_cannot_be_invented(self):
  d=docs()
  d["constitution"]["authority_boundary"]["policy_file_can_invent_normative_weights"]=True
  out=evaluate(d)
  self.assertFalse(out["pass"])
  self.assertEqual(out["reason"],"R10_CONSTITUTION_SEMANTICS_INCOMPLETE")

if __name__=="__main__":
 unittest.main(verbosity=2)
