import hashlib,json,unittest
from pathlib import Path
from unittest.mock import patch
from canonical.runtime import capability_parallel_frontier_post_composition_v1 as adapter

ROOT=Path(__file__).resolve().parents[2]
def load(rel): return json.loads((ROOT/rel).read_text(encoding="utf-8"))
def blob(rel):
 raw=(ROOT/rel).read_bytes()
 return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

class T(unittest.TestCase):
 def test_current_scheduler_chain_is_coherent(self):
  pp="canonical/governance/CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json"
  rp="canonical/governance/CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1.json"
  fp="canonical/governance/CURRENT_LIVE_WORK_FRONTIER.json"
  sp="canonical/governance/CURRENT_DEVELOPMENT_SCHEDULER.json"
  mp="canonical/governance/CURRENT_MISSION_OBJECTIVE.json"
  p,r,f,s,m=map(load,[pp,rp,fp,sp,mp]); pf=p["property_truth_frontier"]
  ids=pf["verified_leaf_ids"]; closed=pf["verified_leaf_count"]; oe=pf["open_execution_leaf_count"]; os=pf["open_semantic_leaf_count"]
  rc=next(x for x in r["classifications"] if x["residual_id"]=="PROFESSIONAL_QUALITY_BROAD_EXECUTION")["property_truth_frontier"]
  self.assertEqual((rc["verified_leaf_count"],rc["open_execution_leaf_count"],rc["open_semantic_leaf_count"],rc["verified_leaf_ids"]),(closed,oe,os,ids))
  row=next(x for x in f["candidates"] if x.get("source")==pp and "canonical:professional-quality" in x.get("mutation_keys",[]))
  ev=row["read_only_evidence"]
  self.assertEqual((ev["property_truth_closed_count"],ev["open_execution_leaf_count"],ev["open_semantic_leaf_count"],ev["verified_property_truth_leaf_ids"]),(closed,oe,os,ids))
  self.assertEqual(s["current_live_work_frontier"]["git_blob_sha"],blob(fp))
  self.assertEqual(s["current_live_work_frontier"]["professional_property_truth_closed_count"],closed)
  self.assertEqual(s["whole_leaf_residual_control"]["property_truth_closed_count"],closed)
  pairs=[("current_assurance_closure_compiler","canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json"),("current_development_scheduler",sp),("current_professional_quality_execution",pp),("current_parallel_frontier_control",fp),("current_residual_reuse_classification",rp),("bytes_current_frontier","canonical/research/bytes/BYTES_ACTIVE_STATE_20261010_V1.json")]
  for key,path in pairs: self.assertEqual(m[key]["observed_git_blob_sha"],blob(path),key)
  with patch.object(adapter.core,"ROOT",ROOT):
   out=adapter._assert_post_composition(f)
  self.assertEqual((out["property_truth_closed_count"],out["open_execution_leaf_count"],out["open_semantic_leaf_count"]),(closed,oe,os))
