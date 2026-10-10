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
 rels=(p.RESIDUAL,p.PROF,p.ASSURANCE,p.BYTES,p.R2,"canonical/governance/ESCAPE_PROGRESS_SHARED_GAP_REUSE_BINDING_20261010_V7.json")
 for rel in rels:
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


 def test_residual_reuse_current_pointer_is_followed_under_topology_invariants(self):
  f=p.refresh_post_composition_currentness(core.load_current_frontier())
  bound={x["path"]:x["git_blob_sha"] for x in f["scope"]["source_set"]}
  self.assertEqual(bound[p.RESIDUAL],p._git_blob_sha(ROOT/p.RESIDUAL))
  self.assertTrue(f["dynamic_currentness"]["residual_reuse_pointer_follow"])
  rr=f["dynamic_currentness"]["residual_reuse"]
  a=next(x for x in f["candidates"] if x.get("work_id")==p.GAP_A_WORK)
  b=next(x for x in f["candidates"] if x.get("work_id")==p.GAP_B_WORK)
  self.assertEqual(a["read_only_evidence"]["active_gap_a_count"],rr["active_gap_a_count"])
  self.assertEqual(b["read_only_evidence"]["active_gap_b_count"],rr["active_gap_b_count"])
  self.assertFalse(b["read_only_evidence"]["strict_progress_witness_required_now"])
  self.assertEqual(b["original_scheduler_state"],"PARKED")

 def test_residual_nonzero_credit_fails_closed(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)
   for rel in (p.RESIDUAL,p.PROF,p.ASSURANCE,p.BYTES,p.R2):
    src=ROOT/rel; dst=root/rel; dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(src.read_bytes())
   bind="canonical/governance/ESCAPE_PROGRESS_SHARED_GAP_REUSE_BINDING_20261010_V7.json"
   src=ROOT/bind; dst=root/bind; dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(src.read_bytes())
   q=root/p.RESIDUAL; d=json.loads(q.read_text()); d["accounting"]["terminal_credit_delta"]=1; q.write_text(json.dumps(d))
   with self.assertRaisesRegex(p.PostCompositionFrontierV2Error,"RESIDUAL_CREDIT"):
    p.refresh_post_composition_currentness(core.load_current_frontier(),root=root)

 def test_residual_parked_topology_mismatch_fails_closed(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)
   for rel in (p.RESIDUAL,p.PROF,p.ASSURANCE,p.BYTES,p.R2):
    src=ROOT/rel; dst=root/rel; dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(src.read_bytes())
   bind="canonical/governance/ESCAPE_PROGRESS_SHARED_GAP_REUSE_BINDING_20261010_V7.json"
   src=ROOT/bind; dst=root/bind; dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(src.read_bytes())
   q=root/p.RESIDUAL; d=json.loads(q.read_text())
   b=next(x for x in d["classifications"] if x["residual_id"]=="ESCAPE_GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS")
   b["parked_rows"]=[]
   q.write_text(json.dumps(d))
   with self.assertRaisesRegex(p.PostCompositionFrontierV2Error,"RESIDUAL_PARKED_ROWS"):
    p.refresh_post_composition_currentness(core.load_current_frontier(),root=root)

 def test_residual_binding_hash_mismatch_fails_closed(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)
   for rel in (p.RESIDUAL,p.PROF,p.ASSURANCE,p.BYTES,p.R2):
    src=ROOT/rel; dst=root/rel; dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(src.read_bytes())
   bind="canonical/governance/ESCAPE_PROGRESS_SHARED_GAP_REUSE_BINDING_20261010_V7.json"
   src=ROOT/bind; dst=root/bind; dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(src.read_bytes())
   q=root/p.RESIDUAL; d=json.loads(q.read_text())
   for rid in ("ESCAPE_GAP_A_ACQUISITION_TOTALITY","ESCAPE_GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS"):
    row=next(x for x in d["classifications"] if x["residual_id"]==rid)
    row["binding_reconciliation"]["git_blob_sha"]="0"*40
   q.write_text(json.dumps(d))
   with self.assertRaisesRegex(p.PostCompositionFrontierV2Error,"RESIDUAL_BINDING_HASH"):
    p.refresh_post_composition_currentness(core.load_current_frontier(),root=root)

if __name__=="__main__":
 unittest.main(verbosity=2)
