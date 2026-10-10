from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
PINS={
 "professional":("canonical/governance/CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json","c1ae0b905f6e6df7648be4c04e4a940a88c4704a"),
 "assurance":("canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json","1883431d44ea57ff254aa43a8d6bfc84e0fb8226"),
 "residual":("canonical/governance/CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1.json","cccc8989c96c1cc19818501e16a49c9417e3ccc0"),
 "frontier":("canonical/governance/CURRENT_LIVE_WORK_FRONTIER.json","b07125773b0d7496e8009ee0e766ecf0c55c199e"),
 "scheduler":("canonical/governance/CURRENT_DEVELOPMENT_SCHEDULER.json","a1690631882b53ce1fd12bc19f3d9f20d5f9a8eb"),
 "mission":("canonical/governance/CURRENT_MISSION_OBJECTIVE.json","3d78caf9d569b12f17c240fbf3a9d53341ba4204"),
 "registry":("canonical/governance/PROFESSIONAL_QUALITY_LEAF_EVIDENCE_REGISTRY_20261010_V1.json","57c30b7417a445d1510414f7dc492493827a5b17"),
 "registry_verify":("canonical/verification/PROFESSIONAL_QUALITY_LEAF_REGISTRY_PROPERTY_TRUTH_VERIFY_20261010_V3.json","f491a215fee5310b54c37eea694af642bbe12d6e"),
 "r4_verify":("canonical/verification/PROFESSIONAL_QUALITY_R4_EXECUTION_PROPERTY_TRUTH_INDEPENDENT_VERIFY_20261010_V1.json","c8aa4e42188aae521678e0507e211831676dcf5b"),
 "bytes":("canonical/research/bytes/BYTES_ACTIVE_STATE_20261010_V1.json","c612a238884f13ba79e96b087d1d999635ec183f"),
 "r2":("canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json","ee03f3fe71383d1bf12e0797bf568e6b5eeeaca4"),
 "tb":("canonical/governance/CURRENT_TB_SCIENCE_EXECUTION.json","7678d9a56461b121ffd52dd4c9c8df464fda08d2"),
 "terminal":("canonical/governance/CURRENT_TERMINAL_AUTHORITY.json","2f4c0900bb5c0d5b4e3b5831f13e951ad75fe859"),
}
LEAVES={
 "PQ::R1_TARGET_SPECIFICATION::EXECUTION",
 "PQ::R4_MEASUREMENT_CONSTRUCT::EXECUTION",
 "PQ::R7_CAUSAL_PRESCRIPTIVE::EXECUTION",
 "PQ::R10_ANALYSIS_DECISION::EXECUTION",
 "PQ::R12_META_COMPOSITION_CLOSURE::EXECUTION",
}

def blob(path:Path)->str:
 raw=path.read_bytes()
 return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def load(name:str):
 path,expected=PINS[name]
 p=ROOT/path
 assert p.is_file() and not p.is_symlink(), name
 assert blob(p)==expected,(name,blob(p),expected)
 return json.loads(p.read_text(encoding="utf-8"))

class TestProfessionalR4Currentness(unittest.TestCase):
 def test_exact_blob_chain_and_professional_counts(self):
  p=load("professional")
  self.assertIn("PROPERTY_TRUTH_5_OF_24",p["status"])
  self.assertEqual(p["leaf_coverage_projection"]["property_truth_closed_count"],5)
  self.assertEqual(p["leaf_coverage_projection"]["open_global_leaf_count"],19)
  self.assertEqual(set(p["leaf_coverage_projection"]["verified_property_truth_leaf_ids"]),LEAVES)
  f=p["property_truth_frontier"]
  self.assertEqual((f["verified_leaf_count"],f["open_leaf_count"],f["open_execution_leaf_count"],f["open_semantic_leaf_count"]),(5,19,7,12))
  self.assertEqual(set(f["verified_leaf_ids"]),LEAVES)
  self.assertEqual(f["registry_verification"]["git_blob_sha"],PINS["registry_verify"][1])
  self.assertEqual(f["r4_execution"]["verification_git_blob_sha"],PINS["r4_verify"][1])
  self.assertFalse(p["quality_authority"]); self.assertFalse(p["terminal_authority"])

 def test_independent_registry_evidence_is_exact_and_scoped(self):
  v=load("registry_verify"); r=load("registry"); rv=load("r4_verify")
  replay=v["independent_replay"]
  self.assertEqual(replay["verified_leaf_count"],5)
  self.assertEqual(replay["open_leaf_count"],19)
  self.assertEqual(set(replay["verified_execution_leaf_ids"]),LEAVES)
  self.assertEqual(replay["verified_semantic_leaf_ids"],[])
  self.assertTrue(replay["stale_r4_receipt_rejected"])
  self.assertEqual(v["subject"]["registry"]["git_blob_sha"],PINS["registry"][1])
  self.assertTrue(rv["leaf_property_truth_authority"])
  self.assertFalse(rv["semantic_leaf_closed"]); self.assertFalse(rv["root_closed"])
  self.assertFalse(v["promotion_authority"]); self.assertFalse(v["terminal_authority"])
  self.assertIn("PQ::R4_MEASUREMENT_CONSTRUCT::EXECUTION",r["leaf_receipts"])

 def test_assurance_residual_frontier_scheduler_mission_are_coherent(self):
  a=load("assurance"); rr=load("residual"); f=load("frontier"); s=load("scheduler"); m=load("mission")
  self.assertIn("PROPERTY_TRUTH_5_OF_24",a["status"])
  self.assertEqual(a["professional_property_truth_currentness"]["current_professional_execution_git_blob_sha"],PINS["professional"][1])
  self.assertEqual(a["professional_property_truth_currentness"]["verified_leaf_count"],5)
  prow=next(x for x in rr["classifications"] if x["residual_id"]=="PROFESSIONAL_QUALITY_BROAD_EXECUTION")
  self.assertIn("PROPERTY_TRUTH_5_OF_24",prow["current_truth"])
  self.assertEqual(prow["property_truth_frontier"]["open_execution_leaf_count"],7)
  self.assertEqual(prow["currentness_reconciliation"]["observed_git_blob_sha"],PINS["professional"][1])

  sources={x["path"]:x["git_blob_sha"] for x in f["scope"]["source_set"]}
  self.assertEqual(sources[PINS["professional"][0]],PINS["professional"][1])
  self.assertEqual(sources[PINS["assurance"][0]],PINS["assurance"][1])
  self.assertEqual(sources[PINS["residual"][0]],PINS["residual"][1])
  self.assertEqual(sources[PINS["bytes"][0]],PINS["bytes"][1])
  self.assertEqual(sources[PINS["r2"][0]],PINS["r2"][1])
  self.assertEqual(sources[PINS["tb"][0]],PINS["tb"][1])
  self.assertEqual(sources[PINS["terminal"][0]],PINS["terminal"][1])
  self.assertIn("PROPERTY_TRUTH_5_OF_24",f["status"])
  self.assertFalse(any(x["work_id"]=="ESCAPE_GAP_B_STRICT_PROGRESS_ROW_PROOFS" for x in f["candidates"]))
  pc=next(x for x in f["candidates"] if x["work_id"]=="PROFESSIONAL_QUALITY_V7_PROPERTY_TRUTH_DEPLETION")
  self.assertEqual(pc["read_only_evidence"]["property_truth_closed_count"],5)
  self.assertEqual(pc["read_only_evidence"]["open_execution_leaf_count"],7)
  bc=next(x for x in f["candidates"] if x["work_id"]=="BYTES_EXACT_SYMBOLIC_V30_NEXT_PHYSICAL_CUT")
  self.assertEqual(bc["read_only_evidence"]["raw_python_source_bytes"],1912465)
  ga=next(x for x in f["candidates"] if x["work_id"]=="ESCAPE_GAP_A_AUTHENTICATED_ROW_PROOFS")
  self.assertEqual(ga["read_only_evidence"]["effective_gap_a_count"],12)

  self.assertEqual(s["current_live_work_frontier"]["git_blob_sha"],PINS["frontier"][1])
  self.assertEqual(s["post_composition"]["professional_property_truth_closed_count"],5)
  self.assertEqual(s["whole_leaf_residual_control"]["property_truth_closed_count"],5)
  self.assertEqual(m["current_development_scheduler"]["observed_git_blob_sha"],PINS["scheduler"][1])
  self.assertEqual(m["current_professional_quality_execution"]["observed_git_blob_sha"],PINS["professional"][1])
  self.assertEqual(m["current_assurance_closure_compiler"]["observed_git_blob_sha"],PINS["assurance"][1])
  self.assertEqual(m["current_parallel_frontier_control"]["observed_git_blob_sha"],PINS["frontier"][1])
  self.assertEqual(m["current_residual_reuse_classification"]["observed_git_blob_sha"],PINS["residual"][1])
  self.assertEqual(m["property_truth_reconciliation"]["verified_leaf_count"],5)
  self.assertEqual(set(m["property_truth_reconciliation"]["verified_leaf_ids"]),LEAVES)

if __name__=="__main__":
 unittest.main(verbosity=2)
