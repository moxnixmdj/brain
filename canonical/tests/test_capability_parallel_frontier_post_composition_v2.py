from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import capability_parallel_frontier_post_composition_v2 as p
from canonical.runtime import capability_parallel_frontier_v2 as core

ROOT=Path(__file__).resolve().parents[2]

def _copy_sources(tmp:Path):
 for rel in (p.PROF,p.ASSURANCE,p.BYTES,p.R2):
  src=ROOT/rel; dst=tmp/rel; dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(src.read_bytes())

class PostCompositionFrontierV2Tests(unittest.TestCase):
 def test_current_stale_snapshot_refreshes_moving_sources_and_plans(self):
  out=p.plan_current_post_composition_frontier()
  self.assertTrue(out["frontier_currentness"]["currentness_verified"])
  self.assertTrue(out["dynamic_currentness"]["professional_pointer_follow"])
  self.assertTrue(out["dynamic_currentness"]["assurance_pointer_follow"])
  self.assertTrue(out["dynamic_currentness"]["bytes_pointer_follow"])
  self.assertTrue(out["dynamic_currentness"]["r2_pointer_follow"])
  self.assertTrue(out["dynamic_currentness"]["parked_normalized_to_nonprimary"])
  self.assertFalse(out["execution_authority"])
  self.assertFalse(out["promotion_authority"])
  self.assertEqual(out["terminal_credit_delta"],0)

 def test_refresh_binds_exact_current_four_source_hashes(self):
  f=p.refresh_post_composition_currentness(core.load_current_frontier())
  bound={x["path"]:x["git_blob_sha"] for x in f["scope"]["source_set"]}
  for rel in (p.PROF,p.ASSURANCE,p.BYTES,p.R2):
   self.assertEqual(bound[rel],p._git_blob_sha(ROOT/rel),rel)
  prow=next(x for x in f["candidates"] if x.get("work_id")==p.PROF_WORK)
  arow=next(x for x in f["candidates"] if x.get("work_id")==p.ASSURANCE_WORK)
  cur=json.loads((ROOT/p.PROF).read_text())
  count=cur["property_truth_frontier"]["verified_leaf_count"]
  self.assertEqual(prow["read_only_evidence"]["property_truth_closed_count"],count)
  self.assertEqual(prow["read_only_evidence"]["verified_property_truth_leaf_ids"],cur["property_truth_frontier"]["verified_leaf_ids"])
  self.assertEqual(arow["read_only_evidence"]["professional_property_truth_closed_count"],count)

 def test_parked_is_preserved_as_nonprimary_not_execution(self):
  f=p.refresh_post_composition_currentness(core.load_current_frontier())
  parked=[x for x in f["candidates"] if x.get("original_scheduler_state")=="PARKED"]
  self.assertTrue(parked)
  self.assertTrue(all(x["scheduler_state"]=="BLOCKED" for x in parked))

 def test_professional_incoherent_ids_fail_closed(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); _copy_sources(root)
   q=root/p.PROF; d=json.loads(q.read_text()); d["property_truth_frontier"]["verified_leaf_ids"]=[]; q.write_text(json.dumps(d))
   with self.assertRaisesRegex(p.PostCompositionFrontierV2Error,"PROF_IDS"):
    p.refresh_post_composition_currentness(core.load_current_frontier(),root=root)

 def test_assurance_authority_boundary_change_fails_closed(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); _copy_sources(root)
   q=root/p.ASSURANCE; d=json.loads(q.read_text()); d["terminal_authority"]=True; q.write_text(json.dumps(d))
   with self.assertRaisesRegex(p.PostCompositionFrontierV2Error,"ASSURANCE_AUTHORITY_BOUNDARY"):
    p.refresh_post_composition_currentness(core.load_current_frontier(),root=root)

 def test_assurance_harmless_blob_drift_is_followed(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); _copy_sources(root)
   q=root/p.ASSURANCE; d=json.loads(q.read_text()); d["observation_only_test_marker"]="changed"; q.write_text(json.dumps(d))
   f=p.refresh_post_composition_currentness(core.load_current_frontier(),root=root)
   bound={x["path"]:x["git_blob_sha"] for x in f["scope"]["source_set"]}
   self.assertEqual(bound[p.ASSURANCE],p._git_blob_sha(q))

 def test_bytes_spent_next_frozen_fails_closed(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); _copy_sources(root)
   q=root/p.BYTES; d=json.loads(q.read_text()); d["next_frozen_qualification"]["spent"]=True; q.write_text(json.dumps(d))
   with self.assertRaisesRegex(p.PostCompositionFrontierV2Error,"BYTES_FROZEN"):
    p.refresh_post_composition_currentness(core.load_current_frontier(),root=root)

 def test_r2_primary_cell_change_fails_closed(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); _copy_sources(root)
   q=root/p.R2; d=json.loads(q.read_text()); d["scheduler_result"]["primary_cell"]="OTHER"; q.write_text(json.dumps(d))
   with self.assertRaisesRegex(p.PostCompositionFrontierV2Error,"R2_SCHEDULER"):
    p.refresh_post_composition_currentness(core.load_current_frontier(),root=root)

 def test_unrelated_source_drift_still_fails_closed(self):
  f=deepcopy(core.load_current_frontier())
  row=next(x for x in f["scope"]["source_set"] if x["path"]=="canonical/governance/CURRENT_TERMINAL_AUTHORITY.json")
  row["git_blob_sha"]="0"*40
  f=p.refresh_post_composition_currentness(f)
  with self.assertRaisesRegex(core.ParallelFrontierError,"LIVE_WORK_FRONTIER_STALE"):
   core.plan_parallel_frontier(f)

 def test_v10_24_of_24_professional_and_assurance_are_regression_blocked(self):
  f=p.refresh_post_composition_currentness(core.load_current_frontier())
  prow=next(x for x in f["candidates"] if x.get("work_id")==p.PROF_WORK)
  arow=next(x for x in f["candidates"] if x.get("work_id")==p.ASSURANCE_WORK)
  self.assertEqual(prow["scheduler_state"],"BLOCKED")
  self.assertIn("24_OF_24_COMPLETE",prow["readiness"])
  pev=prow["read_only_evidence"]
  self.assertEqual(pev["property_truth_closed_count"],24)
  self.assertEqual(pev["verified_execution_leaf_count"],12)
  self.assertEqual(pev["verified_semantic_leaf_count"],12)
  self.assertEqual(pev["open_execution_leaf_count"],0)
  self.assertEqual(pev["open_semantic_leaf_count"],0)
  self.assertEqual(arow["scheduler_state"],"BLOCKED")
  self.assertIn("FULL_PRIVATE_CURRENT_MAIN_REGRESSION_WAKE_GATED",arow["readiness"])
  aev=arow["read_only_evidence"]
  self.assertTrue(aev["professional_live_counts_reconciled"])
  self.assertEqual(aev["professional_property_truth_closed_count"],24)
  self.assertEqual(aev["professional_verified_semantic_leaf_count"],12)

 def test_assurance_live_professional_count_mismatch_fails_closed(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); _copy_sources(root)
   q=root/p.ASSURANCE
   d=json.loads(q.read_text())
   d["professional_property_truth_current"]["verified_semantic_leaf_count"]=11
   q.write_text(json.dumps(d))
   with self.assertRaisesRegex(p.PostCompositionFrontierV2Error,"ASSURANCE_PROFESSIONAL_BINDING"):
    p.refresh_post_composition_currentness(core.load_current_frontier(),root=root)

if __name__=="__main__":
 unittest.main(verbosity=2)
