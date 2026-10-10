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

def assurance(ids=IDS9):
 return {"schema":m.ASSURANCE_SCHEMA,"live_default":False,"terminal_authority":False,
 "activation":{"live_default":False,"required_before_promotion":sorted(m.EXPECTED_ASSURANCE_BLOCKERS)},
 "professional_quality_same_subject_frontier":{"property_truth_closed_count":len(ids),
 "open_execution_leaf_count":12-len(ids),"open_semantic_leaf_count":12,
 "verified_property_truth_leaf_ids":list(reversed(ids)),"next":"deplete remaining"}}

def residual():
 return {"schema":m.RESIDUAL_SCHEMA,"classifications":[
 {"residual_id":"ESCAPE_GAP_A_ACQUISITION_TOTALITY","active_gap_a_count":12,"parked_unresolved_count":1,
 "parked_unresolved_rows":m.PARKED_TB_ROWS,"latest_causal_reclassification":{"effective_gap_a_active_count":12,
 "effective_gap_b_active_count":0,"parked_unresolved_count":1},"gap_a_policy_cover_adapter":{"real_row_proofs":0}},
 {"residual_id":"ESCAPE_GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS","active_gap_b_count":0,"parked_unresolved_count":1,
 "parked_rows":m.PARKED_TB_ROWS},
 {"residual_id":"ESCAPE_OQ_SHARED_ACCEPTANCE_LAWS","shared_laws_bound":{"objective_acceptance":True,"qualitative_acceptance":True},
 "current_row_acceptance_closed":{"O":0,"Q":0}}]}

def bytes_doc():
 return {"schema":m.BYTES_SCHEMA,"status":"ACTIVE_RESEARCH__TOPLEVEL_FACADE_V32_FRONTIER__SUCCESSOR_READY",
 "exact_symbolic_state":{"raw_python_source_bytes":1844477,"B_exec_raw_python_source_bytes":1847237,
 "final_untouched_qualification":"10350/10350","clean_room_execution":"10350/10350","archive_replay":"10350/10350",
 "promotion_credit_from_this_record":0},"current_bottleneck":{"next_action":"rerank V32"},
 "next_frozen_qualification":{"id":"QUAL_NEXT38","spent":False}}

def seed(root,p=None,a=None,r=None,b=None):
 write_json(root,m.PROF_SOURCE,p or professional());write_json(root,m.ASSURANCE_SOURCE,a or assurance())
 write_json(root,m.RESIDUAL_SOURCE,r or residual());write_json(root,m.BYTES_SOURCE,b or bytes_doc())

def frontier():
 src=[m.PROF_SOURCE,m.ASSURANCE_SOURCE,m.RESIDUAL_SOURCE,m.BYTES_SOURCE]
 return {"frontier_id":"F","scope":{"source_set":[{"path":x,"git_blob_sha":"old"} for x in src]},
 "candidates":[
 {"work_id":"PROFESSIONAL","source":m.PROF_SOURCE,"mutation_keys":[m.PROF_MUTATION_KEY],"authority_keys":[m.PROF_AUTHORITY_KEY],
 "evidence_acquisition_mode":"READ_ONLY","scheduler_state":"READY_EVIDENCE","prerequisites_satisfied":True,
 "read_only_evidence":{"property_truth_closed_count":7,"verified_property_truth_leaf_ids":IDS7,"open_execution_leaf_count":5,"open_semantic_leaf_count":12}},
 {"work_id":"ASSURANCE_UVCK_V2_PROMOTION_GATES","source":m.ASSURANCE_SOURCE,"mutation_keys":[],"authority_keys":[],
 "evidence_acquisition_mode":"READ_ONLY","scheduler_state":"BLOCKED","prerequisites_satisfied":False,"read_only_evidence":{}},
 {"work_id":"BYTES_EXACT_SYMBOLIC_V31_NEXT_PHYSICAL_CUT","source":m.BYTES_SOURCE,"mutation_keys":[m.BYTES_MUTATION_KEY],
 "authority_keys":[],"evidence_acquisition_mode":"READ_ONLY","scheduler_state":"READY_EXECUTION","prerequisites_satisfied":True,
 "read_only_evidence":{"raw_python_source_bytes":1909906}},
 {"work_id":"ESCAPE_OQ_SCOPE_COMPLETE_ACCEPTANCE_INSTANTIATION","source":m.RESIDUAL_SOURCE,"mutation_keys":[],"authority_keys":[],
 "evidence_acquisition_mode":"READ_ONLY","scheduler_state":"AUDIT_ONLY","prerequisites_satisfied":False},
 {"work_id":"ESCAPE_GAP_A_AUTHENTICATED_ROW_PROOFS","source":m.RESIDUAL_SOURCE,"mutation_keys":[],"authority_keys":[],
 "evidence_acquisition_mode":"READ_ONLY","scheduler_state":"READY_EVIDENCE","prerequisites_satisfied":True,"read_only_evidence":{}},
 {"work_id":"ESCAPE_GAP_B_STRICT_PROGRESS_ROW_PROOFS","source":m.RESIDUAL_SOURCE,"mutation_keys":[],"authority_keys":[],
 "evidence_acquisition_mode":"READ_ONLY","scheduler_state":"PARKED","prerequisites_satisfied":False,"read_only_evidence":{}}
 ]}

class T(unittest.TestCase):
 def test_supported_drift_refreshes_and_unsupported_drift_still_fails(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);seed(root)
   with patch.object(m.core,"ROOT",root):
    out,p,b=m._refresh_supported_sources(frontier())
    self.assertEqual((p["closed"],p["open_exec"],b["version"],b["raw"]),(9,3,32,1844477))
    self.assertEqual(out["candidates"][0]["read_only_evidence"]["verified_property_truth_leaf_ids"],IDS9)
    self.assertEqual(out["candidates"][2]["work_id"],"BYTES_EXACT_SYMBOLIC_V32_NEXT_PHYSICAL_CUT")
    self.assertEqual(m._assert_post_composition(out)["closed"],9)
    other="canonical/governance/UNSUPPORTED.json";write_json(root,other,{"x":1})
    out["scope"]["source_set"].append({"path":other,"git_blob_sha":"stale"})
    with self.assertRaisesRegex(m.core.ParallelFrontierError,"LIVE_WORK_FRONTIER_STALE"):
     m.core.verify_frontier_currentness(out,root=root)

 def test_authority_replay_and_topology_boundaries_fail_closed(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);p=professional();p["terminal_authority"]=True;seed(root,p=p)
   with patch.object(m.core,"ROOT",root):
    with self.assertRaisesRegex(m.PostCompositionFrontierError,"AUTHORITY_BOUNDARY"):
     m._refresh_supported_sources(frontier())
   seed(root);b=bytes_doc();b["exact_symbolic_state"]["clean_room_execution"]="10349/10350";write_json(root,m.BYTES_SOURCE,b)
   with patch.object(m.core,"ROOT",root):
    with self.assertRaisesRegex(m.PostCompositionFrontierError,"CLEAN_ROOM"):
     m._refresh_supported_sources(frontier())
   seed(root);r=residual();r["classifications"][0]["active_gap_a_count"]=11;write_json(root,m.RESIDUAL_SOURCE,r)
   with patch.object(m.core,"ROOT",root):
    with self.assertRaisesRegex(m.PostCompositionFrontierError,"GAP_A_TOPOLOGY"):
     m._refresh_supported_sources(frontier())
