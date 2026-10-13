from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import capability_parallel_frontier_post_composition_v3 as p
from canonical.runtime import capability_parallel_frontier_v2 as core

ROOT=Path(__file__).resolve().parents[2]

def _copy_sources(tmp:Path):
 for rel in (p.PROF,p.ASSURANCE,p.BYTES,p.R2,p.R2_V91_RECEIPT,p.RESIDUAL,p.TERMINAL,p.WAKE):
  src=ROOT/rel; dst=tmp/rel; dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(src.read_bytes())

class PostCompositionFrontierV3Tests(unittest.TestCase):
 def test_current_exact_files_refresh_and_plan(self):
  out=p.plan_current_post_composition_frontier()
  self.assertTrue(out["frontier_currentness"]["currentness_verified"])
  self.assertTrue(out["dynamic_currentness"]["professional_pointer_follow"])
  self.assertTrue(out["dynamic_currentness"]["assurance_pointer_follow"])
  self.assertTrue(out["dynamic_currentness"]["bytes_pointer_follow"])
  self.assertTrue(out["dynamic_currentness"]["r2_pointer_follow"])
  self.assertTrue(out["dynamic_currentness"]["r2_v91_reclassification_receipt_follow"])
  self.assertTrue(out["dynamic_currentness"]["residual_reuse_topology_follow"])
  self.assertTrue(out["dynamic_currentness"]["terminal_follow"])
  self.assertEqual(out["dynamic_currentness"]["r2"]["internal_r2_mechanism_unsolved_count"],0)
  self.assertEqual(out["dynamic_currentness"]["r2"]["task_specific_external_observation_frontier_count"],1)
  self.assertEqual(out["dynamic_currentness"]["checkpoint_wake_gate"]["row_specific_same_information_runnable_count"],0)
  self.assertEqual(out["dynamic_currentness"]["residual_reuse"]["logically_open_checkpoint_rows"],12)
  self.assertEqual(out["dynamic_currentness"]["residual_reuse"]["active_gap_b_strict_progress_rows"],0)
  self.assertEqual(out["dynamic_currentness"]["residual_reuse"]["parked_unresolved_rows"],1)
  self.assertFalse(out["dynamic_currentness"]["terminal"]["terminal"])
  self.assertEqual(out["dynamic_currentness"]["terminal"]["admitted_capability_deficit_count"],0)
  self.assertIn(p.GAP_A_WORK,out["nonprimary_candidate_ids"])
  self.assertNotIn(p.GAP_A_WORK,out["parallel_read_only_evidence_work_ids"])
  bytes_work=f"BYTES_EXACT_SYMBOLIC_V{out['dynamic_currentness']['bytes']['version']}_NEXT_PHYSICAL_CUT"
  self.assertIn(bytes_work,out["parallel_read_only_evidence_work_ids"])
  self.assertTrue(out["dynamic_currentness"]["parked_normalized_to_nonprimary"])
  self.assertFalse(out["execution_authority"])
  self.assertFalse(out["promotion_authority"])
  self.assertEqual(out["terminal_credit_delta"],0)

 def test_refresh_binds_exact_current_seven_source_hashes(self):
  f=p.refresh_post_composition_currentness(core.load_current_frontier())
  bound={x["path"]:x["git_blob_sha"] for x in f["scope"]["source_set"]}
  for rel in (p.PROF,p.ASSURANCE,p.BYTES,p.R2,p.R2_V91_RECEIPT,p.RESIDUAL,p.TERMINAL,p.WAKE):
   self.assertEqual(bound[rel],p._git_blob_sha(ROOT/rel),rel)
  prow=next(x for x in f["candidates"] if x.get("work_id")==p.PROF_WORK)
  rrow=next(x for x in f["candidates"] if x.get("work_id")==p.R2_WORK)
  cur=json.loads((ROOT/p.PROF).read_text())
  count=cur["property_truth_frontier"]["verified_leaf_count"]
  self.assertEqual(prow["read_only_evidence"]["property_truth_closed_count"],count)
  self.assertEqual(prow["read_only_evidence"]["verified_property_truth_leaf_ids"],cur["property_truth_frontier"]["verified_leaf_ids"])
  self.assertEqual(rrow["read_only_evidence"]["internal_r2_mechanism_unsolved_count"],0)
  self.assertEqual(rrow["read_only_evidence"]["task_specific_external_observation_frontier_count"],1)

 def test_pre_v10_professional_projection_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); _copy_sources(root)
   q=root/p.PROF; d=json.loads(q.read_text()); d["status"]="P1_V3_LIVE_UNCHANGED__12_OF_12_COMPOSED__24_OF_24_SCOPE_VERIFIED__OLD_PROJECTION"; q.write_text(json.dumps(d))
   with self.assertRaisesRegex(p.PostCompositionFrontierV3Error,"PROF_PHASE"):
    p.refresh_post_composition_currentness(core.load_current_frontier(),root=root)

 def test_r2_internal_unsolved_shape_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); _copy_sources(root)
   q=root/p.R2_V91_RECEIPT; d=json.loads(q.read_text()); d["classification"]["internal_r2_mechanism_unsolved_count"]=1; q.write_text(json.dumps(d))
   with self.assertRaisesRegex(p.PostCompositionFrontierV3Error,"R2_V91_CLASSIFICATION"):
    p.refresh_post_composition_currentness(core.load_current_frontier(),root=root)

 def test_r2_general_mechanism_missing_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); _copy_sources(root)
   q=root/p.R2; d=json.loads(q.read_text()); d["general_mechanism_missing"]=True; q.write_text(json.dumps(d))
   with self.assertRaisesRegex(p.PostCompositionFrontierV3Error,"R2_BOUNDARY"):
    p.refresh_post_composition_currentness(core.load_current_frontier(),root=root)

 def test_residual_topology_drift_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); _copy_sources(root)
   q=root/p.RESIDUAL; d=json.loads(q.read_text()); d["escape_current_topology"]["parked_unresolved_rows"]=2; q.write_text(json.dumps(d))
   with self.assertRaisesRegex(p.PostCompositionFrontierV3Error,"RESIDUAL_TOPOLOGY_DRIFT"):
    p.refresh_post_composition_currentness(core.load_current_frontier(),root=root)

 def test_terminal_true_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); _copy_sources(root)
   q=root/p.TERMINAL; d=json.loads(q.read_text()); d["live_truth"]["terminal"]=True; q.write_text(json.dumps(d))
   with self.assertRaisesRegex(p.PostCompositionFrontierV3Error,"TERMINAL_FOLLOW_BOUNDARY"):
    p.refresh_post_composition_currentness(core.load_current_frontier(),root=root)

 def test_assurance_property_truth_below_24_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); _copy_sources(root)
   q=root/p.ASSURANCE; d=json.loads(q.read_text()); d["activation"]["property_truth_closed_count"]=12; q.write_text(json.dumps(d))
   with self.assertRaisesRegex(p.PostCompositionFrontierV3Error,"ASSURANCE_PROPERTY_TRUTH"):
    p.refresh_post_composition_currentness(core.load_current_frontier(),root=root)

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

if __name__=="__main__":
 unittest.main(verbosity=2)
