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
WAKE="canonical/governance/CURRENT_ALL_OPEN_CHECKPOINT_WAKE_GATE_RECONCILIATION_20261011_V1.json"
PROF_WORK="PROFESSIONAL_QUALITY_V7_PROPERTY_TRUTH_DEPLETION"
ASSURANCE_WORK="ASSURANCE_UVCK_V2_PROMOTION_GATES"
R2_WORK="R2_FINANCE_SEMANTIC_ADEQUACY_TAIL"
GAP_A_WORK="ESCAPE_GAP_A_AUTHENTICATED_ROW_PROOFS"

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

def _ensure_source(f:dict,rel:str,sha:str):
 rows=[x for x in f.get("scope",{}).get("source_set",[]) if isinstance(x,dict) and x.get("path")==rel]
 if len(rows)>1: raise PostCompositionFrontierV2Error("SOURCE_CARDINALITY:"+rel)
 if rows:
  rows[0]["git_blob_sha"]=sha
 else:
  source_set=f.get("scope",{}).get("source_set")
  if not isinstance(source_set,list): raise PostCompositionFrontierV2Error("SOURCE_SET_MISSING")
  source_set.append({"path":rel,"git_blob_sha":sha})

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
 is_v10="V10_PROPERTY_TRUTH_24_OF_24" in status
 if not is_v10 and ("12_OF_12_COMPOSED" not in status or "24_OF_24_SCOPE_VERIFIED" not in status): raise PostCompositionFrontierV2Error("PROF_PHASE")
 if not isinstance(comp,Mapping) or comp.get("composition_admissible") is not True or comp.get("verified_root_subject_binding_count")!=12: raise PostCompositionFrontierV2Error("PROF_COMPOSITION")
 if not isinstance(pf,Mapping): raise PostCompositionFrontierV2Error("PROF_FRONTIER")
 vals=[pf.get(k) for k in ("total_leaf_count","verified_leaf_count","verified_execution_leaf_count","open_execution_leaf_count","verified_semantic_leaf_count","open_semantic_leaf_count")]
 if any(isinstance(x,bool) or not isinstance(x,int) or x<0 for x in vals): raise PostCompositionFrontierV2Error("PROF_COUNTS")
 total,v,ve,oe,vs,os=vals; ids=pf.get("verified_leaf_ids")
 if is_v10:
  if total!=24 or v!=24 or ve!=12 or oe!=0 or vs!=12 or os!=0: raise PostCompositionFrontierV2Error("PROF_PARTITION")
  if not isinstance(ids,list) or len(ids)!=v or len(set(ids))!=v or any(not isinstance(x,str) or not (x.endswith("::EXECUTION") or x.endswith("::SEMANTIC")) for x in ids): raise PostCompositionFrontierV2Error("PROF_IDS")
 else:
  if total!=24 or v!=ve or vs!=0 or ve+oe!=12 or vs+os!=12: raise PostCompositionFrontierV2Error("PROF_PARTITION")
  if not isinstance(ids,list) or len(ids)!=v or len(set(ids))!=v or any(not isinstance(x,str) or not x.endswith("::EXECUTION") for x in ids): raise PostCompositionFrontierV2Error("PROF_IDS")
 _source(f,PROF)["git_blob_sha"]=sha
 row=_cand_source(f,PROF); row["work_id"]=PROF_WORK; row["scheduler_state"]="READY_EVIDENCE"; row["prerequisites_satisfied"]=True; row["evidence_acquisition_mode"]="READ_ONLY"
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
 d,sha=_load(root,BYTES); m=re.search(r"_V(\d+)_(?:REPAIRED_)?FRONTIER",str(d.get("status") or ""))
 st=d.get("exact_symbolic_state"); bn=d.get("current_bottleneck"); fr=d.get("next_frozen_qualification")
 if not m or not all(isinstance(x,Mapping) for x in (st,bn,fr)): raise PostCompositionFrontierV2Error("BYTES_STATE")
 ver=int(m.group(1)); raw=st.get("raw_python_source_bytes"); be=st.get("B_exec_raw_python_source_bytes"); q=st.get("final_untouched_qualification")
 cr=st.get("clean_room_execution"); ar=st.get("archive_replay")
 if any(isinstance(x,bool) or not isinstance(x,int) or x<=0 for x in (raw,be)) or not all(isinstance(x,str) and x for x in (q,cr,ar)): raise PostCompositionFrontierV2Error("BYTES_VERIFY")
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

def _wake(f:dict,root:Path):
 d,sha=_load(root,WAKE)
 if d.get("schema")!="PROJECT_BRAIN_ALL_OPEN_CHECKPOINT_ROWS_WAKE_GATE_RECONCILIATION_20261011_V1": raise PostCompositionFrontierV2Error("WAKE_SCHEMA")
 rec=d.get("scheduler_reconciliation")
 if not isinstance(rec,Mapping): raise PostCompositionFrontierV2Error("WAKE_RECONCILIATION")
 keys=("open_checkpoint_obligation_count","row_specific_same_information_runnable_count","wake_gated_open_checkpoint_count","parked_checkpoint_count")
 vals=[rec.get(k) for k in keys]
 if any(isinstance(x,bool) or not isinstance(x,int) or x<0 for x in vals): raise PostCompositionFrontierV2Error("WAKE_COUNTS")
 open_n,runnable,wake_n,parked=vals
 if runnable+wake_n!=open_n: raise PostCompositionFrontierV2Error("WAKE_PARTITION")
 if rec.get("primary_when_no_wake_event")!="CAPABILITY_FIRST_GENERAL_DEVELOPMENT_AND_RESOURCE_PARETO_IMPROVEMENT": raise PostCompositionFrontierV2Error("WAKE_PRIMARY")
 _ensure_source(f,WAKE,sha)
 row=_cand_id(f,GAP_A_WORK)
 ev=dict(row.get("read_only_evidence") or {})
 ev.update({"source":WAKE,"source_git_blob_sha":sha,"open_checkpoint_obligation_count":open_n,"row_specific_same_information_runnable_count":runnable,"wake_gated_open_checkpoint_count":wake_n,"parked_checkpoint_count":parked,"dynamic_current_pointer_follow":True,"vector_bounds_complete":False})
 row["read_only_evidence"]=ev
 if runnable==0:
  row["scheduler_state"]="SLEEPING"; row["prerequisites_satisfied"]=False; row["evidence_acquisition_mode"]="NONE"
  row["readiness"]=f"WAKE_GATED__{open_n}_OPEN__0_SAME_INFORMATION_RUNNABLE__WAIT_FOR_POLICY_CHANGING_REALITY_OR_STRONGER_CERTIFICATE"
 else:
  row["scheduler_state"]="READY_EVIDENCE"; row["prerequisites_satisfied"]=True; row["evidence_acquisition_mode"]="READ_ONLY"
  row["readiness"]=f"WAKE_EVENT_PRESENT__{runnable}_POLICY_CHANGING_ROW_PATHS_RUNNABLE__REENTER_EXISTING_VERIFIERS_ONLY"
 return {"git_blob_sha":sha,"open_checkpoint_obligation_count":open_n,"row_specific_same_information_runnable_count":runnable,"wake_gated_open_checkpoint_count":wake_n,"parked_checkpoint_count":parked}

def refresh_post_composition_currentness(frontier:Mapping[str,Any],*,root:Path=core.ROOT):
 f=json.loads(json.dumps(frontier)); p=_prof(f,root); a=_assurance(f,p,root); b=_bytes(f,root); r=_r2(f,root); w=_wake(f,root)
 for row in f.get("candidates",[]):
  if isinstance(row,dict) and row.get("scheduler_state")=="PARKED":
   row["original_scheduler_state"]="PARKED"; row["scheduler_state"]="BLOCKED"
 f["dynamic_currentness"]={"professional_pointer_follow":True,"assurance_pointer_follow":True,"bytes_pointer_follow":True,"r2_pointer_follow":True,"checkpoint_wake_gate_follow":True,"parked_normalized_to_nonprimary":True,"professional":p,"assurance":a,"bytes":b,"r2":r,"checkpoint_wake_gate":w,"other_source_families_dynamic_follow":False}
 return f

def plan_current_post_composition_frontier():
 f=refresh_post_composition_currentness(core.load_current_frontier())
 row=_cand_id(f,PROF_WORK); ev=row.get("read_only_evidence")
 if not isinstance(ev,Mapping) or ev.get("whole_leaf_scope_complete_count")!=24 or row.get("evidence_acquisition_mode")!="READ_ONLY": raise PostCompositionFrontierV2Error("POST_COMPOSITION_ASSERTION")
 out=core.plan_parallel_frontier(f)
 return {**out,"adapter_schema":SCHEMA,"post_composition_phase_verified":True,"dynamic_currentness":f["dynamic_currentness"],"execution_authority":False,"promotion_authority":False,"terminal_credit_delta":0}
