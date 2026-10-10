import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from canonical.runtime import capability_parallel_frontier_post_composition_v1 as m

IDS7=[f"PQ::R{i}::EXECUTION" for i in range(1,8)]
IDS9=IDS7+["PQ::R8::EXECUTION","PQ::R9::EXECUTION"]

def write_json(root,rel,obj):
 p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj),encoding="utf-8")

def professional(ids=IDS9):
 return {"schema":m.PROF_SCHEMA,"live_default":False,"terminal_authority":False,
 "property_truth_frontier":{"verified_leaf_count":len(ids),"total_leaf_count":24,"verified_leaf_ids":ids,
 "open_execution_leaf_count":12-len(ids),"open_semantic_leaf_count":12,
 "shared_semantic_blocker":{"independently_verified":True,"catalog_alone_can_authorize_semantic_property_truth":False}}}

def bytes_doc():
 return {"schema":m.BYTES_SCHEMA,"status":"ACTIVE_RESEARCH__TOPLEVEL_FACADE_V32_FRONTIER__SUCCESSOR_READY",
 "exact_symbolic_state":{"raw_python_source_bytes":1844477,"B_exec_raw_python_source_bytes":1847237,
 "final_untouched_qualification":"10350/10350","clean_room_execution":"10350/10350","archive_replay":"10350/10350",
 "promotion_credit_from_this_record":0},"current_bottleneck":{"next_action":"rerank V32"},
 "next_frozen_qualification":{"id":"QUAL_NEXT38","spent":False}}

def frontier():
 return {"frontier_id":"F","scope":{"source_set":[
 {"path":m.PROF_SOURCE,"git_blob_sha":"old-prof"},{"path":m.BYTES_SOURCE,"git_blob_sha":"old-bytes"}]},
 "candidates":[
 {"work_id":"PROFESSIONAL_QUALITY_V7_PROPERTY_TRUTH_DEPLETION","source":m.PROF_SOURCE,
 "mutation_keys":[m.PROF_MUTATION_KEY],"authority_keys":[m.PROF_AUTHORITY_KEY],"evidence_acquisition_mode":"READ_ONLY",
 "read_only_evidence":{"property_truth_closed_count":7,"verified_property_truth_leaf_ids":IDS7,
 "open_execution_leaf_count":5,"open_semantic_leaf_count":12}},
 {"work_id":"BYTES_EXACT_SYMBOLIC_V31_NEXT_PHYSICAL_CUT","source":m.BYTES_SOURCE,
 "mutation_keys":[m.BYTES_MUTATION_KEY],"authority_keys":["authority:bytes-secondary-profile"],
 "evidence_acquisition_mode":"READ_ONLY","read_only_evidence":{"source_git_blob_sha":"old","raw_python_source_bytes":1909906}}
 ]}

class T(unittest.TestCase):
 def test_supported_drift_refreshes_and_unsupported_drift_still_fails(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);write_json(root,m.PROF_SOURCE,professional());write_json(root,m.BYTES_SOURCE,bytes_doc())
   with patch.object(m.core,"ROOT",root):
    out,p,b=m._refresh_supported_sources(frontier())
    self.assertEqual((p["closed"],p["open_exec"],b["version"],b["raw"]),(9,3,32,1844477))
    self.assertEqual(out["candidates"][0]["read_only_evidence"]["verified_property_truth_leaf_ids"],IDS9)
    self.assertEqual(out["candidates"][1]["work_id"],"BYTES_EXACT_SYMBOLIC_V32_NEXT_PHYSICAL_CUT")
    self.assertEqual(m._assert_post_composition(out)["closed"],9)
    other="canonical/governance/UNSUPPORTED.json";write_json(root,other,{"x":1})
    out["scope"]["source_set"].append({"path":other,"git_blob_sha":"stale"})
    with self.assertRaisesRegex(m.core.ParallelFrontierError,"LIVE_WORK_FRONTIER_STALE"):
     m.core.verify_frontier_currentness(out,root=root)

 def test_authority_and_replay_boundaries_fail_closed(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);p=professional();p["terminal_authority"]=True
   write_json(root,m.PROF_SOURCE,p);write_json(root,m.BYTES_SOURCE,bytes_doc())
   with patch.object(m.core,"ROOT",root):
    with self.assertRaisesRegex(m.PostCompositionFrontierError,"AUTHORITY_BOUNDARY"):
     m._refresh_supported_sources(frontier())
   p=professional();write_json(root,m.PROF_SOURCE,p);b=bytes_doc();b["exact_symbolic_state"]["clean_room_execution"]="10349/10350";write_json(root,m.BYTES_SOURCE,b)
   with patch.object(m.core,"ROOT",root):
    with self.assertRaisesRegex(m.PostCompositionFrontierError,"CLEAN_ROOM"):
     m._refresh_supported_sources(frontier())
