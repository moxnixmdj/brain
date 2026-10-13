from __future__ import annotations
import json,re
from hashlib import sha1
from pathlib import Path
from typing import Any,Mapping
from canonical.runtime import capability_parallel_frontier_v2 as core

SCHEMA="PROJECT_BRAIN_POST_COMPOSITION_PARALLEL_FRONTIER_V3"
PROF="canonical/governance/CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json"
ASSURANCE="canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json"
BYTES="canonical/research/bytes/BYTES_ACTIVE_STATE_20261010_V1.json"
R2="canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
R2_V91_RECEIPT="canonical/verification/R2_POST_V91_EXTERNALITY_RECLASSIFICATION_VERIFY_20261011_V1.json"
RESIDUAL="canonical/governance/CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1.json"
TERMINAL="canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
WAKE="canonical/governance/CURRENT_ALL_OPEN_CHECKPOINT_WAKE_GATE_RECONCILIATION_20261011_V1.json"
PROF_WORK="PROFESSIONAL_QUALITY_V7_PROPERTY_TRUTH_DEPLETION"
ASSURANCE_WORK="ASSURANCE_UVCK_V2_PROMOTION_GATES"
R2_WORK="R2_FINANCE_SEMANTIC_ADEQUACY_TAIL"
GAP_A_WORK="ESCAPE_GAP_A_AUTHENTICATED_ROW_PROOFS"
GAP_B_WORK="ESCAPE_GAP_B_STRICT_PROGRESS_ROW_PROOFS"
TERMINAL_WORK="REPOSITORY_PROMOTION_ENFORCEMENT"
ONLY_PROMOTION_GATE="FULL_PRIVATE_CURRENT_MAIN_FULL_SYSTEM_REGRESSION"

class PostCompositionFrontierV3Error(ValueError): pass

def _git_blob_sha(path:Path)->str:
 raw=path.read_bytes()
 return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def _load(root:Path,rel:str):
 p=root/rel
 if not p.is_file() or p.is_symlink(): raise PostCompositionFrontierV3Error("SOURCE_UNAVAILABLE:"+rel)
 try:d=json.loads(p.read_text())
 except Exception as e: raise PostCompositionFrontierV3Error("SOURCE_INVALID:"+rel) from e
 if not isinstance(d,dict): raise PostCompositionFrontierV3Error("SOURCE_NOT_OBJECT:"+rel)
 return d,_git_blob_sha(p)

def _source(f:dict,rel:str):
 rows=[x for x in f.get("scope",{}).get("source_set",[]) if isinstance(x,dict) and x.get("path")==rel]
 if len(rows)!=1: raise PostCompositionFrontierV3Error("SOURCE_CARDINALITY:"+rel)
 return rows[0]

def _ensure_source(f:dict,rel:str,sha:str):
 rows=[x for x in f.get("scope",{}).get("source_set",[]) if isinstance(x,dict) and x.get("path")==rel]
 if len(rows)>1: raise PostCompositionFrontierV3Error("SOURCE_CARDINALITY:"+rel)
 if rows:
  rows[0]["git_blob_sha"]=sha
 else:
  source_set=f.get("scope",{}).get("source_set")
  if not isinstance(source_set,list): raise PostCompositionFrontierV3Error("SOURCE_SET_MISSING")
  source_set.append({"path":rel,"git_blob_sha":sha})

def _cand_source(f:dict,rel:str):
 rows=[x for x in f.get("candidates",[]) if isinstance(x,dict) and x.get("source")==rel]
 if len(rows)!=1: raise PostCompositionFrontierV3Error("CANDIDATE_CARDINALITY:"+rel)
 return rows[0]

def _cand_id(f:dict,wid:str):
 rows=[x for x in f.get("candidates",[]) if isinstance(x,dict) and x.get("work_id")==wid]
 if len(rows)!=1: raise PostCompositionFrontierV3Error("CANDIDATE_CARDINALITY:"+wid)
 return rows[0]

def _prof(f:dict,root:Path):
 # V3 repair contract point: require the exact current V10 24/24 partition
 # (12 execution + 12 semantic, zero open). The retired pre-V10 branch
 # (12/12 composed, semantic verified == 0) is deleted as a retired invariant.
 d,sha=_load(root,PROF); status=str(d.get("status") or "")
 if "V10_PROPERTY_TRUTH_24_OF_24" not in status: raise PostCompositionFrontierV3Error("PROF_PHASE")
 comp=d.get("same_subject_composition"); pf=d.get("property_truth_frontier")
 if not isinstance(comp,Mapping) or comp.get("composition_admissible") is not True or comp.get("verified_root_subject_binding_count")!=12: raise PostCompositionFrontierV3Error("PROF_COMPOSITION")
 if not isinstance(pf,Mapping): raise PostCompositionFrontierV3Error("PROF_FRONTIER")
 keys=("total_leaf_count","verified_leaf_count","verified_execution_leaf_count","open_execution_leaf_count","verified_semantic_leaf_count","open_semantic_leaf_count")
 vals=[pf.get(k) for k in keys]
 if any(isinstance(x,bool) or not isinstance(x,int) or x<0 for x in vals): raise PostCompositionFrontierV3Error("PROF_COUNTS")
 total,v,ve,oe,vs,osem=vals; ids=pf.get("verified_leaf_ids")
 if total!=24 or v!=24 or ve!=12 or oe!=0 or vs!=12 or osem!=0: raise PostCompositionFrontierV3Error("PROF_PARTITION")
 if not isinstance(ids,list) or len(ids)!=v or len(set(ids))!=v or any(not isinstance(x,str) or not (x.endswith("::EXECUTION") or x.endswith("::SEMANTIC")) for x in ids): raise PostCompositionFrontierV3Error("PROF_IDS")
 _source(f,PROF)["git_blob_sha"]=sha
 row=_cand_source(f,PROF); row["work_id"]=PROF_WORK; row["scheduler_state"]="BLOCKED"; row["prerequisites_satisfied"]=True; row["evidence_acquisition_mode"]="READ_ONLY"
 row["readiness"]="PROPERTY_TRUTH_24_OF_24__ZERO_OPEN_LEAVES__FULL_PRIVATE_CURRENT_MAIN_REGRESSION_GATE_ONLY__ZERO_QUALITY_PROMOTION_TERMINAL_AUTHORITY"
 ev=dict(row.get("read_only_evidence") or {}); ev.update({"source":PROF,"source_git_blob_sha":sha,"whole_leaf_scope_complete_count":24,"property_truth_closed_count":v,"verified_property_truth_leaf_count":v,"verified_property_truth_leaf_ids":ids,"open_execution_leaf_count":oe,"open_semantic_leaf_count":osem,"only_promotion_gate":ONLY_PROMOTION_GATE,"vector_bounds_complete":False,"dynamic_current_pointer_follow":True}); row["read_only_evidence"]=ev
 return {"git_blob_sha":sha,"property_truth_closed_count":v,"open_execution_leaf_count":oe}

def _assurance(f:dict,prof:Mapping[str,Any],root:Path):
 # V3 repair contract point: require property truth 24/24 and ONLY the full
 # private current-main full-system regression before promotion; not live default.
 d,sha=_load(root,ASSURANCE)
 if d.get("terminal_authority") is not False or d.get("live_default") is not False: raise PostCompositionFrontierV3Error("ASSURANCE_AUTHORITY_BOUNDARY")
 act=d.get("activation")
 if not isinstance(act,Mapping) or act.get("live_default") is not False: raise PostCompositionFrontierV3Error("ASSURANCE_ACTIVATION")
 if act.get("property_truth_closed_count")!=24: raise PostCompositionFrontierV3Error("ASSURANCE_PROPERTY_TRUTH")
 blockers=act.get("required_before_promotion")
 if blockers!=[ONLY_PROMOTION_GATE]: raise PostCompositionFrontierV3Error("ASSURANCE_ONLY_GATE")
 _source(f,ASSURANCE)["git_blob_sha"]=sha
 row=_cand_id(f,ASSURANCE_WORK); row["scheduler_state"]="BLOCKED"; row["evidence_acquisition_mode"]="READ_ONLY"
 ev=dict(row.get("read_only_evidence") or {}); ev.update({"source":ASSURANCE,"source_git_blob_sha":sha,"professional_current_git_blob_sha":prof["git_blob_sha"],"professional_property_truth_closed_count":prof["property_truth_closed_count"],"professional_open_execution_leaf_count":prof["open_execution_leaf_count"],"property_truth_closed_count":24,"only_remaining_promotion_gate":ONLY_PROMOTION_GATE,"live_default":False,"embedded_professional_snapshot_lags_live_frontier":True,"dynamic_current_pointer_follow":True,"vector_bounds_complete":False}); row["read_only_evidence"]=ev
 return {"git_blob_sha":sha,"property_truth_closed_count":24}

def _bytes(f:dict,root:Path):
 d,sha=_load(root,BYTES); m=re.search(r"_V(\d+)_(?:REPAIRED_)?FRONTIER",str(d.get("status") or ""))
 st=d.get("exact_symbolic_state"); bn=d.get("current_bottleneck"); fr=d.get("next_frozen_qualification")
 if not m or not all(isinstance(x,Mapping) for x in (st,bn,fr)): raise PostCompositionFrontierV3Error("BYTES_STATE")
 ver=int(m.group(1)); raw=st.get("raw_python_source_bytes"); be=st.get("B_exec_raw_python_source_bytes"); q=st.get("final_untouched_qualification")
 cr=st.get("clean_room_execution"); ar=st.get("archive_replay")
 if any(isinstance(x,bool) or not isinstance(x,int) or x<=0 for x in (raw,be)) or not all(isinstance(x,str) and x for x in (q,cr,ar)): raise PostCompositionFrontierV3Error("BYTES_VERIFY")
 if fr.get("spent") is not False or not isinstance(fr.get("id"),str): raise PostCompositionFrontierV3Error("BYTES_FROZEN")
 _source(f,BYTES)["git_blob_sha"]=sha; row=_cand_source(f,BYTES); row["work_id"]=f"BYTES_EXACT_SYMBOLIC_V{ver}_NEXT_PHYSICAL_CUT"; row["readiness"]=f"ACTIONABLE__V{ver}_CURRENT"
 ev=dict(row.get("read_only_evidence") or {}); ev.update({"source":BYTES,"source_git_blob_sha":sha,"raw_python_source_bytes":raw,"B_exec_raw_python_source_bytes":be,"qualification":q,"next_action":bn.get("next_action"),"next_frozen_qualification":fr.get("id"),"next_frozen_spent":False,"vector_bounds_complete":False,"dynamic_current_pointer_follow":True}); row["read_only_evidence"]=ev
 return {"git_blob_sha":sha,"version":ver,"raw_python_source_bytes":raw}

def _r2(f:dict,root:Path):
 # V3 repair contract point: require zero internal mechanism residuals and
 # exactly one task-specific external observation frontier, keyed to the
 # independently verified V91 reclassification receipt. The R2 document's
 # legacy scheduler_result block predates V91 reclassification and is not
 # load-bearing for currentness in V3.
 d,sha=_load(root,R2); s=str(d.get("status") or ""); m=re.search(r"__V(\d+)__",s)
 if not m or "GENERAL_MECHANISM_CLOSED" not in s: raise PostCompositionFrontierV3Error("R2_BOUNDARY")
 if d.get("general_mechanism_missing") is not False or d.get("global_open_world_closure_claimed") is not False: raise PostCompositionFrontierV3Error("R2_BOUNDARY")
 if "ZERO_INTERNAL_R2_MECHANISM_RESIDUALS" not in s or "ONE_TASK_SPECIFIC_EXTERNAL_FINANCE_OBSERVATION_FRONTIER_REMAINS" not in s: raise PostCompositionFrontierV3Error("R2_V91_STATUS")
 r,sha_r=_load(root,R2_V91_RECEIPT)
 rs=str(r.get("status") or "")
 if "PASS" not in rs or "ZERO_INTERNAL_R2_MECHANISM_RESIDUALS" not in rs: raise PostCompositionFrontierV3Error("R2_V91_RECEIPT_STATUS")
 cls=r.get("classification")
 if not isinstance(cls,Mapping) or cls.get("internal_r2_mechanism_unsolved_count")!=0 or cls.get("task_specific_external_observation_frontier_count")!=1 or cls.get("task_specific_frontier")!="FINANCE_SEMANTIC_ADEQUACY_TAIL": raise PostCompositionFrontierV3Error("R2_V91_CLASSIFICATION")
 ver=int(m.group(1))
 _source(f,R2)["git_blob_sha"]=sha; _ensure_source(f,R2_V91_RECEIPT,sha_r)
 row=_cand_id(f,R2_WORK); row["scheduler_state"]="SLEEPING"; row["prerequisites_satisfied"]=False; row["evidence_acquisition_mode"]="NONE"
 row["readiness"]=f"SLEEPING_UNLESS_TASK_LOCAL_COUNTEREXAMPLE_OR_VERIFIED_DEFECT_WAKES_IT__V{ver}_ZERO_INTERNAL_RESIDUALS__ONE_TASK_SPECIFIC_EXTERNAL_OBSERVATION_FRONTIER"
 ev=dict(row.get("read_only_evidence") or {}); ev.update({"source":R2,"source_git_blob_sha":sha,"v91_reclassification_receipt":R2_V91_RECEIPT,"v91_reclassification_receipt_git_blob_sha":sha_r,"internal_r2_mechanism_unsolved_count":0,"task_specific_external_observation_frontier_count":1,"task_specific_frontier":"FINANCE_SEMANTIC_ADEQUACY_TAIL","general_mechanism_closed":True,"finance_tail_closed":False,"wake_gate":False,"vector_bounds_complete":False,"dynamic_current_pointer_follow":True}); row["read_only_evidence"]=ev
 return {"git_blob_sha":sha,"version":ver,"internal_r2_mechanism_unsolved_count":0,"task_specific_external_observation_frontier_count":1,"v91_reclassification_receipt_git_blob_sha":sha_r}

def _wake(f:dict,root:Path):
 d,sha=_load(root,WAKE)
 if d.get("schema")!="PROJECT_BRAIN_ALL_OPEN_CHECKPOINT_ROWS_WAKE_GATE_RECONCILIATION_20261011_V1": raise PostCompositionFrontierV3Error("WAKE_SCHEMA")
 rec=d.get("scheduler_reconciliation")
 if not isinstance(rec,Mapping): raise PostCompositionFrontierV3Error("WAKE_RECONCILIATION")
 keys=("open_checkpoint_obligation_count","row_specific_same_information_runnable_count","wake_gated_open_checkpoint_count","parked_checkpoint_count")
 vals=[rec.get(k) for k in keys]
 if any(isinstance(x,bool) or not isinstance(x,int) or x<0 for x in vals): raise PostCompositionFrontierV3Error("WAKE_COUNTS")
 open_n,runnable,wake_n,parked=vals
 if runnable+wake_n!=open_n: raise PostCompositionFrontierV3Error("WAKE_PARTITION")
 if rec.get("primary_when_no_wake_event")!="CAPABILITY_FIRST_GENERAL_DEVELOPMENT_AND_RESOURCE_PARETO_IMPROVEMENT": raise PostCompositionFrontierV3Error("WAKE_PRIMARY")
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

def _residual(f:dict,root:Path):
 # V3 repair contract point: follow residual reuse only while topology is
 # 12 Gap-A / 0 active Gap-B / 1 parked TB.
 d,sha=_load(root,RESIDUAL); top=d.get("escape_current_topology")
 if not isinstance(top,Mapping): raise PostCompositionFrontierV3Error("RESIDUAL_TOPOLOGY")
 keys=("logically_open_checkpoint_rows","active_gap_b_strict_progress_rows","parked_unresolved_rows")
 vals=[top.get(k) for k in keys]
 if any(isinstance(x,bool) or not isinstance(x,int) or x<0 for x in vals): raise PostCompositionFrontierV3Error("RESIDUAL_TOPOLOGY")
 gap_a,gap_b,parked=vals
 if gap_a!=12 or gap_b!=0 or parked!=1: raise PostCompositionFrontierV3Error("RESIDUAL_TOPOLOGY_DRIFT")
 if top.get("parked_obligation_ids")!=["TB_SCIENCE_GE_58_7"]: raise PostCompositionFrontierV3Error("RESIDUAL_PARKED_IDENTITY")
 _source(f,RESIDUAL)["git_blob_sha"]=sha
 row=_cand_id(f,GAP_B_WORK)
 ev=dict(row.get("read_only_evidence") or {}); ev.update({"source":RESIDUAL,"source_git_blob_sha":sha,"logically_open_checkpoint_rows":gap_a,"active_gap_b_strict_progress_rows":gap_b,"parked_unresolved_rows":parked,"parked_obligation_ids":["TB_SCIENCE_GE_58_7"],"topology_follow_rule":"12_GAP_A__0_ACTIVE_GAP_B__1_PARKED_TB","dynamic_current_pointer_follow":True,"vector_bounds_complete":False}); row["read_only_evidence"]=ev
 return {"git_blob_sha":sha,"logically_open_checkpoint_rows":gap_a,"active_gap_b_strict_progress_rows":gap_b,"parked_unresolved_rows":parked}

def _terminal(f:dict,root:Path):
 # V3 repair contract point: follow the terminal lane only while terminal is
 # false and no capability deficit is admitted.
 d,sha=_load(root,TERMINAL); lt=d.get("live_truth")
 if not isinstance(lt,Mapping) or lt.get("terminal") is not False: raise PostCompositionFrontierV3Error("TERMINAL_FOLLOW_BOUNDARY")
 if lt.get("tournament_failure_current_admitted_capability_deficit_count")!=0: raise PostCompositionFrontierV3Error("TERMINAL_ADMITTED_DEFICIT")
 _source(f,TERMINAL)["git_blob_sha"]=sha
 row=_cand_id(f,TERMINAL_WORK)
 ev=dict(row.get("read_only_evidence") or {}); ev.update({"source":TERMINAL,"source_git_blob_sha":sha,"terminal":False,"admitted_capability_deficit_count":0,"follow_rule":"FOLLOW_ONLY_WHILE_TERMINAL_FALSE_AND_NO_ADMITTED_CAPABILITY_DEFICIT","dynamic_current_pointer_follow":True,"vector_bounds_complete":False}); row["read_only_evidence"]=ev
 return {"git_blob_sha":sha,"terminal":False,"admitted_capability_deficit_count":0}

def refresh_post_composition_currentness(frontier:Mapping[str,Any],*,root:Path=core.ROOT):
 f=json.loads(json.dumps(frontier)); p=_prof(f,root); a=_assurance(f,p,root); b=_bytes(f,root); r=_r2(f,root); w=_wake(f,root); ru=_residual(f,root); t=_terminal(f,root)
 for row in f.get("candidates",[]):
  if isinstance(row,dict) and row.get("scheduler_state")=="PARKED":
   row["original_scheduler_state"]="PARKED"; row["scheduler_state"]="BLOCKED"
 f["dynamic_currentness"]={"professional_pointer_follow":True,"assurance_pointer_follow":True,"bytes_pointer_follow":True,"r2_pointer_follow":True,"r2_v91_reclassification_receipt_follow":True,"checkpoint_wake_gate_follow":True,"residual_reuse_topology_follow":True,"terminal_follow":True,"parked_normalized_to_nonprimary":True,"professional":p,"assurance":a,"bytes":b,"r2":r,"checkpoint_wake_gate":w,"residual_reuse":ru,"terminal":t,"other_source_families_dynamic_follow":False}
 return f

def plan_current_post_composition_frontier():
 f=refresh_post_composition_currentness(core.load_current_frontier())
 row=_cand_id(f,PROF_WORK); ev=row.get("read_only_evidence")
 if not isinstance(ev,Mapping) or ev.get("whole_leaf_scope_complete_count")!=24 or ev.get("property_truth_closed_count")!=24 or row.get("evidence_acquisition_mode")!="READ_ONLY": raise PostCompositionFrontierV3Error("POST_COMPOSITION_ASSERTION")
 out=core.plan_parallel_frontier(f)
 return {**out,"adapter_schema":SCHEMA,"post_composition_phase_verified":True,"dynamic_currentness":f["dynamic_currentness"],"execution_authority":False,"promotion_authority":False,"terminal_credit_delta":0}
