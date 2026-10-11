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
 for rel in (p.PROF,p.ASSURANCE,p.BYTES,p.R2,p.WAKE):
  src=ROOT/rel; dst=tmp/rel; dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(src.read_bytes())

class PostCompositionFrontierV2Tests(unittest.TestCase):
 def test_current_stale_snapshot_refreshes_moving_sources_and_plans(self):
  out=p.plan_current_post_composition_frontier()
  self.assertTrue(out["frontier_currentness"]["currentness_verified"])
  self.assertTrue(out["dynamic_currentness"]["professional_pointer_follow"])
  self.assertTrue(out["dynamic_currentness"]["assurance_pointer_follow"])
  self.assertTrue(out["dynamic_currentness"]["bytes_pointer_follow"])
  self.assertTrue(out["dynamic_currentness"]["r2_pointer_follow"])
  self.assertTrue(out["dynamic_currentness"]["checkpoint_wake_gate_follow"])
  self.assertEqual(out["dynamic_currentness"]["checkpoint_wake_gate"]["row_specific_same_information_runnable_count"],0)
  self.assertIn(p.GAP_A_WORK,out["nonprimary_candidate_ids"])
  self.assertNotIn(p.GAP_A_WORK,out["parallel_read_only_evidence_work_ids"])
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

 def test_checkpoint_same_information_work_is_mechanically_sleeping(self):
  f=p.refresh_post_composition_currentness(core.load_current_frontier())
  row=next(x for x in f["candidates"] if x.get("work_id")==p.GAP_A_WORK)
  self.assertEqual(row["scheduler_state"],"SLEEPING")
  self.assertFalse(row["prerequisites_satisfied"])
  self.assertEqual(row["evidence_acquisition_mode"],"NONE")
  self.assertEqual(row["read_only_evidence"]["row_specific_same_information_runnable_count"],0)
  bound={x["path"]:x["git_blob_sha"] for x in f["scope"]["source_set"]}
  self.assertEqual(bound[p.WAKE],p._git_blob_sha(ROOT/p.WAKE))

 def test_checkpoint_wake_event_reenables_only_existing_evidence_path(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); _copy_sources(root)
   q=root/p.WAKE; d=json.loads(q.read_text()); rec=d["scheduler_reconciliation"]
   rec["row_specific_same_information_runnable_count"]=1
   rec["wake_gated_open_checkpoint_count"]=rec["open_checkpoint_obligation_count"]-1
   q.write_text(json.dumps(d))
   f=p.refresh_post_composition_currentness(core.load_current_frontier(),root=root)
   row=next(x for x in f["candidates"] if x.get("work_id")==p.GAP_A_WORK)
   self.assertEqual(row["scheduler_state"],"READY_EVIDENCE")
   self.assertTrue(row["prerequisites_satisfied"])
   self.assertEqual(row["evidence_acquisition_mode"],"READ_ONLY")

 def test_incoherent_wake_partition_fails_closed(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); _copy_sources(root)
   q=root/p.WAKE; d=json.loads(q.read_text()); d["scheduler_reconciliation"]["wake_gated_open_checkpoint_count"]=11; q.write_text(json.dumps(d))
   with self.assertRaisesRegex(p.PostCompositionFrontierV2Error,"WAKE_PARTITION"):
    p.refresh_post_composition_currentness(core.load_current_frontier(),root=root)

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

if __name__=="__main__":
 unittest.main(verbosity=2)
