from __future__ import annotations
import json,re
from hashlib import sha1
from pathlib import Path
from typing import Any,Mapping
from canonical.runtime import capability_parallel_frontier_v2 as core

SCHEMA="PROJECT_BRAIN_POST_COMPOSITION_PARALLEL_FRONTIER_V2"
PROF="canonical/governance/CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json"
ASSURANCE="canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json"
BYTES="canonical/research/bytes/BYTES_ACTIVE_STATE_20261010_V1.json"
R2="canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
RESIDUAL="canonical/governance/CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1.json"
RESIDUAL_SCHEMA="PROJECT_BRAIN_CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1"
GAP_A_WORK="ESCAPE_GAP_A_AUTHENTICATED_ROW_PROOFS"
GAP_B_WORK="ESCAPE_GAP_B_STRICT_PROGRESS_ROW_PROOFS"
OQ_WORK="ESCAPE_OQ_SCOPE_COMPLETE_ACCEPTANCE_INSTANTIATION"
PARKED_TB=["TB_SCIENCE_GE_58_7"]
PROF_WORK="PROFESSIONAL_QUALITY_V7_PROPERTY_TRUTH_DEPLETION"
ASSURANCE_WORK="ASSURANCE_UVCK_V2_PROMOTION_GATES"
R2_WORK="R2_FINANCE_SEMANTIC_ADEQUACY_TAIL"

class PostCompositionFrontierV2Error(ValueError): pass

def _git_blob_sha(path:Path)->str:
 raw=path.read_bytes()
 return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def _load(root:Path,rel:str):
 p=root/rel
 if not p.is_file() or p.is_symlink(): raise PostCompositionFrontierV2Error("SOURCE_UNAVAILABLE:"+rel)
 try:d=json.loads(p.read_text())
 except Exception as e: raise PostCompositionFrontierV2Error("SOURCE_INVALID:"+rel) from e
 if not isinstance(d,dict): raise PostCompositionFrontierV2Error("SOURCE_NOT_OBJECT:"+rel)
 return d,_git_blob_sha(p)

def _source(f:dict,rel:str):
 rows=[x for x in f.get("scope",{}).get("source_set",[]) if isinstance(x,dict) and x.get("path")==rel]
 if len(rows)!=1: raise PostCompositionFrontierV2Error("SOURCE_CARDINALITY:"+rel)
 return rows[0]

def _cand_source(f:dict,rel:str):
 rows=[x for x in f.get("candidates",[]) if isinstance(x,dict) and x.get("source")==rel]
 if len(rows)!=1: raise PostCompositionFrontierV2Error("CANDIDATE_CARDINALITY:"+rel)
 return rows[0]

def _cand_id(f:dict,wid:str):
 rows=[x for x in f.get("candidates",[]) if isinstance(x,dict) and x.get("work_id")==wid]
 if len(rows)!=1: raise PostCompositionFrontierV2Error("CANDIDATE_CARDINALITY:"+wid)
 return rows[0]

def _prof(f:dict,root:Path):
 d,sha=_load(root,PROF); status=str(d.get("status") or "")
 comp=d.get("same_subject_composition"); pf=d.get("property_truth_frontier")
 if "12_OF_12_COMPOSED" not in status or "24_OF_24_SCOPE_VERIFIED" not in status: raise PostCompositionFrontierV2Error("PROF_PHASE")
 if not isinstance(comp,Mapping) or comp.get("composition_admissible") is not True or comp.get("verified_root_subject_binding_count")!=12: raise PostCompositionFrontierV2Error("PROF_COMPOSITION")
 if not isinstance(pf,Mapping): raise PostCompositionFrontierV2Error("PROF_FRONTIER")
 vals=[pf.get(k) for k in ("total_leaf_count","verified_leaf_count","verified_execution_leaf_count","open_execution_leaf_count","verified_semantic_leaf_count","open_semantic_leaf_count")]
 if any(isinstance(x,bool) or not isinstance(x,int) or x<0 for x in vals): raise PostCompositionFrontierV2Error("PROF_COUNTS")
 total,v,ve,oe,vs,os=vals; ids=pf.get("verified_leaf_ids")
 if total!=24 or v!=ve or vs!=0 or ve+oe!=12 or vs+os!=12: raise PostCompositionFrontierV2Error("PROF_PARTITION")
 if not isinstance(ids,list) or len(ids)!=v or len(set(ids))!=v or any(not isinstance(x,str) or not x.endswith("::EXECUTION") for x in ids): raise PostCompositionFrontierV2Error("PROF_IDS")
 _source(f,PROF)["git_blob_sha"]=sha
 row=_cand_source(f,PROF); row["work_id"]=PROF_WORK; row["scheduler_state"]="READY_EVIDENCE"; row["evidence_acquisition_mode"]="READ_ONLY"
 row["readiness"]=f"PROPERTY_TRUTH_{v}_OF_24__{oe}_EXECUTION_LEAVES_OPEN__TWELVE_SEMANTIC_TOTALITY_REUSE"
 ev=dict(row.get("read_only_evidence") or {}); ev.update({"source":PROF,"source_git_blob_sha":sha,"whole_leaf_scope_complete_count":24,"property_truth_closed_count":v,"verified_property_truth_leaf_count":v,"verified_property_truth_leaf_ids":ids,"open_execution_leaf_count":oe,"open_semantic_leaf_count":os,"vector_bounds_complete":False,"dynamic_current_pointer_follow":True}); row["read_only_evidence"]=ev
 return {"git_blob_sha":sha,"property_truth_closed_count":v,"open_execution_leaf_count":oe}

def _assurance(f:dict,prof:Mapping[str,Any],root:Path):
 d,sha=_load(root,ASSURANCE)
 if d.get("terminal_authority") is not False or d.get("live_default") is not False: raise PostCompositionFrontierV2Error("ASSURANCE_AUTHORITY_BOUNDARY")
 act=d.get("activation")
 if not isinstance(act,Mapping) or act.get("live_default") is not False: raise PostCompositionFrontierV2Error("ASSURANCE_ACTIVATION")
 blockers=act.get("required_before_promotion")
 if not isinstance(blockers,list) or "FULL_PRIVATE_CURRENT_MAIN_FULL_SYSTEM_REGRESSION" not in blockers: raise PostCompositionFrontierV2Error("ASSURANCE_BLOCKERS")
 _source(f,ASSURANCE)["git_blob_sha"]=sha
 row=_cand_id(f,ASSURANCE_WORK)
 ev=dict(row.get("read_only_evidence") or {}); ev.update({"source":ASSURANCE,"source_git_blob_sha":sha,"professional_current_git_blob_sha":prof["git_blob_sha"],"professional_property_truth_closed_count":prof["property_truth_closed_count"],"professional_open_execution_leaf_count":prof["open_execution_leaf_count"],"embedded_professional_snapshot_lags_live_frontier":True,"dynamic_current_pointer_follow":True,"vector_bounds_complete":False}); row["read_only_evidence"]=ev
 return {"git_blob_sha":sha}

def _bytes(f:dict,root:Path):
 d,sha=_load(root,BYTES); m=re.search(r"_V(\d+)_FRONTIER",str(d.get("status") or ""))
 st=d.get("exact_symbolic_state"); bn=d.get("current_bottleneck"); fr=d.get("next_frozen_qualification")
 if not m or not all(isinstance(x,Mapping) for x in (st,bn,fr)): raise PostCompositionFrontierV2Error("BYTES_STATE")
 ver=int(m.group(1)); raw=st.get("raw_python_source_bytes"); be=st.get("B_exec_raw_python_source_bytes"); q=st.get("final_untouched_qualification")
 if any(isinstance(x,bool) or not isinstance(x,int) or x<=0 for x in (raw,be)) or not isinstance(q,str) or st.get("clean_room_execution")!=q or st.get("archive_replay")!=q: raise PostCompositionFrontierV2Error("BYTES_VERIFY")
 if fr.get("spent") is not False or not isinstance(fr.get("id"),str): raise PostCompositionFrontierV2Error("BYTES_FROZEN")
 _source(f,BYTES)["git_blob_sha"]=sha; row=_cand_source(f,BYTES); row["work_id"]=f"BYTES_EXACT_SYMBOLIC_V{ver}_NEXT_PHYSICAL_CUT"; row["readiness"]=f"ACTIONABLE__V{ver}_CURRENT"
 ev=dict(row.get("read_only_evidence") or {}); ev.update({"source":BYTES,"source_git_blob_sha":sha,"raw_python_source_bytes":raw,"B_exec_raw_python_source_bytes":be,"qualification":q,"next_action":bn.get("next_action"),"next_frozen_qualification":fr.get("id"),"next_frozen_spent":False,"vector_bounds_complete":False,"dynamic_current_pointer_follow":True}); row["read_only_evidence"]=ev
 return {"git_blob_sha":sha,"version":ver,"raw_python_source_bytes":raw}

def _r2(f:dict,root:Path):
 d,sha=_load(root,R2); s=str(d.get("status") or ""); m=re.search(r"__V(\d+)__",s); sr=d.get("scheduler_result"); cells=d.get("current_cell_classifications")
 if not m or "GENERAL_MECHANISM_CLOSED" not in s or d.get("general_mechanism_missing") is not False or d.get("global_open_world_closure_claimed") is not False: raise PostCompositionFrontierV2Error("R2_BOUNDARY")
 if not isinstance(sr,Mapping) or not isinstance(cells,Mapping) or sr.get("primary_cell")!="FINANCE_SEMANTIC_ADEQUACY_TAIL" or sr.get("primary_internal_unsolved_pending_acquisition_or_experiment_cell_count")!=1: raise PostCompositionFrontierV2Error("R2_SCHEDULER")
 c=cells.get("FINANCE_SEMANTIC_ADEQUACY_TAIL")
 if not isinstance(c,Mapping) or c.get("state")!="INTERNAL_UNSOLVED__PENDING_ACQUISITION_OR_EXPERIMENT" or c.get("information_theoretic_externality_proved") is not False: raise PostCompositionFrontierV2Error("R2_CELL")
 ver=int(m.group(1)); _source(f,R2)["git_blob_sha"]=sha; row=_cand_id(f,R2_WORK); row["readiness"]=f"SLEEPING_UNLESS_TASK_LOCAL_COUNTEREXAMPLE_OR_VERIFIED_DEFECT_WAKES_IT__V{ver}_GENERAL_MECHANISM_CLOSED"
 ev=dict(row.get("read_only_evidence") or {}); ev.update({"source":R2,"source_git_blob_sha":sha,"general_mechanism_closed":True,"finance_tail_closed":False,"wake_gate":False,"vector_bounds_complete":False,"dynamic_current_pointer_follow":True}); row["read_only_evidence"]=ev
 return {"git_blob_sha":sha,"version":ver}

def _class(d:Mapping[str,Any],rid:str):
 rows=d.get("classifications")
 if not isinstance(rows,list): raise PostCompositionFrontierV2Error("RESIDUAL_CLASSIFICATIONS")
 hit=[x for x in rows if isinstance(x,Mapping) and x.get("residual_id")==rid]
 if len(hit)!=1: raise PostCompositionFrontierV2Error("RESIDUAL_CLASS_CARDINALITY:"+rid)
 return hit[0]

def _residual(f:dict,root:Path):
 d,sha=_load(root,RESIDUAL)
 if d.get("schema")!=RESIDUAL_SCHEMA: raise PostCompositionFrontierV2Error("RESIDUAL_SCHEMA")
 a=_class(d,"ESCAPE_GAP_A_ACQUISITION_TOTALITY"); b=_class(d,"ESCAPE_GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS"); oq=_class(d,"ESCAPE_OQ_SHARED_ACCEPTANCE_LAWS")
 if a.get("active_gap_a_count")!=12 or a.get("parked_unresolved_count")!=1 or a.get("parked_unresolved_rows")!=PARKED_TB: raise PostCompositionFrontierV2Error("RESIDUAL_GAP_A_TOPOLOGY")
 latest=a.get("latest_causal_reclassification"); bridge=a.get("gap_a_policy_cover_adapter")
 if not isinstance(latest,Mapping) or (latest.get("effective_gap_a_active_count"),latest.get("effective_gap_b_active_count"),latest.get("parked_unresolved_count"))!=(12,0,1): raise PostCompositionFrontierV2Error("RESIDUAL_CAUSAL_TOPOLOGY")
 if not isinstance(bridge,Mapping) or bridge.get("real_row_proofs")!=0: raise PostCompositionFrontierV2Error("RESIDUAL_GAP_A_PROOF_STATE")
 if b.get("active_gap_b_count")!=0 or b.get("parked_unresolved_count")!=1 or b.get("parked_rows")!=PARKED_TB: raise PostCompositionFrontierV2Error("RESIDUAL_GAP_B_TOPOLOGY")
 laws=oq.get("shared_laws_bound")
 if not isinstance(laws,Mapping) or laws.get("objective_acceptance") is not True or laws.get("qualitative_acceptance") is not True or oq.get("current_row_acceptance_closed")!={"O":0,"Q":0}: raise PostCompositionFrontierV2Error("RESIDUAL_OQ_TOPOLOGY")
 rows={GAP_A_WORK:"READY_EVIDENCE",GAP_B_WORK:"PARKED",OQ_WORK:"AUDIT_ONLY"}
 for wid,state in rows.items():
  row=_cand_id(f,wid)
  if row.get("source")!=RESIDUAL or row.get("scheduler_state")!=state: raise PostCompositionFrontierV2Error("RESIDUAL_CANDIDATE_STATE:"+wid)
  ev=row.get("read_only_evidence")
  if isinstance(ev,Mapping):
   ev=dict(ev); ev.update({"source":RESIDUAL,"source_git_blob_sha":sha,"dynamic_current_pointer_follow":True}); row["read_only_evidence"]=ev
 _source(f,RESIDUAL)["git_blob_sha"]=sha
 return {"git_blob_sha":sha,"active_gap_a_count":12,"active_gap_b_count":0,"parked_unresolved_count":1}

def refresh_post_composition_currentness(frontier:Mapping[str,Any],*,root:Path=core.ROOT):
 f=json.loads(json.dumps(frontier)); p=_prof(f,root); a=_assurance(f,p,root); b=_bytes(f,root); r=_r2(f,root); q=_residual(f,root)
 for row in f.get("candidates",[]):
  if isinstance(row,dict) and row.get("scheduler_state")=="PARKED":
   row["original_scheduler_state"]="PARKED"; row["scheduler_state"]="BLOCKED"
 f["dynamic_currentness"]={"professional_pointer_follow":True,"assurance_pointer_follow":True,"bytes_pointer_follow":True,"r2_pointer_follow":True,"residual_pointer_follow":True,"parked_normalized_to_nonprimary":True,"professional":p,"assurance":a,"bytes":b,"r2":r,"residual":q,"other_source_families_dynamic_follow":False}
 return f

def plan_current_post_composition_frontier():
 f=refresh_post_composition_currentness(core.load_current_frontier())
 row=_cand_id(f,PROF_WORK); ev=row.get("read_only_evidence")
 if not isinstance(ev,Mapping) or ev.get("whole_leaf_scope_complete_count")!=24 or row.get("evidence_acquisition_mode")!="READ_ONLY": raise PostCompositionFrontierV2Error("POST_COMPOSITION_ASSERTION")
 out=core.plan_parallel_frontier(f)
 return {**out,"adapter_schema":SCHEMA,"post_composition_phase_verified":True,"dynamic_currentness":f["dynamic_currentness"],"execution_authority":False,"promotion_authority":False,"terminal_credit_delta":0}
