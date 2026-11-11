"""Structured professional semantic-obligation scope compiler V1.

Compiles the complete declared semantic-fulfillment slice for an already
structured professional target. It deliberately does not parse arbitrary
natural language and grants no presentation/owner/benchmark authority.
"""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha1,sha256
import json
from pathlib import Path
from typing import Any,Mapping
from canonical.runtime import requirement_graph_kernel as req_kernel

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_STRUCTURED_TASK_OBLIGATION_SCOPE_V1"
CAPABILITY_ID="professional.task.structured_obligation_scope.v1"
BEHAVIOR_ID="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
CONTRACT_REGISTRY_PATH="canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V2.json"
CONTRACT_REGISTRY_BLOB="ae250d5bc5da73b23600670be354ffba31e65e53"
REQUIREMENT_KERNEL_PATH="canonical/runtime/requirement_graph_kernel.py"
REQUIREMENT_KERNEL_BLOB="18001b4b7ace6fe77497c7fb92dd8d9dd2d0f607"
TARGET_FIELDS=("objective","audience","source_evidence","artifact_type","constraints","current_draft_or_render")
FAILURE_ATOMS=("Polished but unsupported content","wrong audience emphasis","omitted required analysis","layout choice obscures information","revisions do not improve independent quality")

class StructuredTaskScopeError(ValueError): pass

def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)

def _digest(v:Any)->str:
    return sha256(_canon(v).encode()).hexdigest()

def _blob(p:Path)->str:
    d=p.read_bytes()
    return sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

def _root(root:str|Path|None)->Path:
    return Path(root).resolve() if root is not None else Path(__file__).resolve().parents[2]

def _bound_json(root:Path,rel:str,blob:str)->dict[str,Any]:
    p=(root/rel).resolve();p.relative_to(root)
    if not p.is_file() or p.is_symlink(): raise StructuredTaskScopeError("BOUND_FILE_INVALID:"+rel)
    if _blob(p)!=blob: raise StructuredTaskScopeError("BOUND_BLOB_DRIFT:"+rel)
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise StructuredTaskScopeError("BOUND_JSON_INVALID:"+rel)
    return x

def _contract(root:Path)->dict[str,Any]:
    kp=(root/REQUIREMENT_KERNEL_PATH).resolve();kp.relative_to(root)
    if not kp.is_file() or kp.is_symlink() or _blob(kp)!=REQUIREMENT_KERNEL_BLOB:
        raise StructuredTaskScopeError("REQUIREMENT_KERNEL_BLOB_DRIFT")
    reg=_bound_json(root,CONTRACT_REGISTRY_PATH,CONTRACT_REGISTRY_BLOB)
    rows=reg.get("active_contracted_residuals")
    if not isinstance(rows,list): raise StructuredTaskScopeError("CONTRACT_ROWS_INVALID")
    hits=[dict(x) for x in rows if isinstance(x,Mapping) and x.get("behavior_id")==BEHAVIOR_ID]
    if len(hits)!=1: raise StructuredTaskScopeError("TARGET_CONTRACT_NOT_UNIQUE")
    failure=str(hits[0].get("failure_condition") or "")
    for atom in FAILURE_ATOMS:
        if atom.casefold() not in failure.casefold():
            raise StructuredTaskScopeError("CONTRACT_FAILURE_ATOM_DRIFT:"+atom)
    return hits[0]

def _target(v:Any)->dict[str,Any]:
    if not isinstance(v,Mapping): raise StructuredTaskScopeError("TARGET_INSTANCE_NOT_OBJECT")
    extra=sorted(set(v)-set(TARGET_FIELDS));missing=[k for k in TARGET_FIELDS if k not in v]
    if extra: raise StructuredTaskScopeError("TARGET_INSTANCE_UNKNOWN_FIELDS:"+",".join(extra))
    if missing: raise StructuredTaskScopeError("TARGET_INSTANCE_MISSING_FIELDS:"+",".join(missing))
    out={k:deepcopy(v[k]) for k in TARGET_FIELDS}
    for k in ("objective","audience","artifact_type"):
        if not isinstance(out[k],str) or not out[k].strip():
            raise StructuredTaskScopeError("TARGET_REQUIRED_TEXT_INVALID:"+k)
    for k in ("source_evidence","constraints"):
        if out[k] is None: raise StructuredTaskScopeError("TARGET_REQUIRED_VALUE_MISSING:"+k)
    return out

def _sem(kind:str,value:Any,**ctx:Any)->str:
    return _canon({"kind":kind,"value":value,**ctx})

def _obligations(t:Mapping[str,Any],c:Mapping[str,Any])->list[dict[str,Any]]:
    return [
      {"obligation_id":"SEM_OBJECTIVE_AND_REQUIRED_ACTION","semantics":_sem("OBJECTIVE_AND_REQUIRED_ACTION",t["objective"],required_output_or_action=c["required_output_or_action"]),"required":True},
      {"obligation_id":"SEM_AUDIENCE_FIT","semantics":_sem("AUDIENCE_FIT",t["audience"],negative_guard="wrong audience emphasis"),"required":True},
      {"obligation_id":"SEM_EVIDENCE_GROUNDING","semantics":_sem("EVIDENCE_GROUNDING",t["source_evidence"],allowed_information=c["allowed_information"],negative_guard="Polished but unsupported content"),"required":True},
      {"obligation_id":"SEM_ARTIFACT_TYPE","semantics":_sem("ARTIFACT_TYPE",t["artifact_type"]),"required":True},
      {"obligation_id":"SEM_DECLARED_CONSTRAINTS","semantics":_sem("DECLARED_CONSTRAINTS",t["constraints"]),"required":True},
      {"obligation_id":"SEM_REVISION_CONTEXT","semantics":_sem("CURRENT_DRAFT_OR_RENDER_CONTEXT",t["current_draft_or_render"],environment_state=c["environment_state"]),"required":True},
      {"obligation_id":"SEM_REQUIRED_ANALYSIS_COMPLETENESS","semantics":_sem("REQUIRED_ANALYSIS_COMPLETENESS",{"objective":t["objective"],"constraints":t["constraints"]},negative_guard="omitted required analysis"),"required":True},
    ]

def obligation_universe_digest(rows:Any)->str:
    if not isinstance(rows,list) or not rows: raise StructuredTaskScopeError("OBLIGATIONS_INVALID")
    out=[];seen=set()
    for x in rows:
        if not isinstance(x,Mapping): raise StructuredTaskScopeError("OBLIGATION_NOT_OBJECT")
        oid=str(x.get("obligation_id") or "").strip();sem=str(x.get("semantics") or "").strip()
        if not oid or oid in seen or not sem or x.get("required") is not True:
            raise StructuredTaskScopeError("OBLIGATION_INVALID:"+oid)
        seen.add(oid);out.append({"obligation_id":oid,"semantics_sha256":sha256(sem.encode()).hexdigest(),"required":True})
    out.sort(key=lambda z:z["obligation_id"])
    return sha256(_canon(out).encode()).hexdigest()

def task_scope_id(*,task_id:str,task_sha256:str,obligation_digest:str)->str:
    m={"task_id":task_id,"task_sha256":task_sha256,"obligation_universe_digest":obligation_digest}
    return "scope://professional-task-fulfillment/"+sha256(_canon(m).encode()).hexdigest()

def _requirements(obs:list[dict[str,Any]])->list[dict[str,Any]]:
    rows=[]
    for o in obs:
        oid=o["obligation_id"];sid="SCENARIO_"+oid
        rows.append({"id":oid,"description":o["semantics"],"critical":True,"dependencies":[],"children":[],"open_questions":[],
          "scenarios":[{"id":sid,"given":["EXACT_STRUCTURED_PROFESSIONAL_TARGET_BOUND"],"when":["ASSESS_EXACT_REALIZED_ARTIFACT"],"then":["INDEPENDENT_SEMANTIC_SATISFACTION_RECEIPT_REQUIRED:"+oid]}],
          "clauses":[{"id":"CLAUSE_"+oid,"keyword":"MUST","covered_by_scenarios":[sid]}]})
    return rows

def compile_scope(task_id:str,target_instance:Any,*,repo_root:str|Path|None=None)->dict[str,Any]:
    task_id=str(task_id or "").strip()
    if not task_id: raise StructuredTaskScopeError("TASK_ID_REQUIRED")
    root=_root(repo_root);contract=_contract(root);target=_target(target_instance);target_sha=_digest(target)
    obs=_obligations(target,contract);ids=[x["obligation_id"] for x in obs];reqs=_requirements(obs)
    compiled=req_kernel.compile_requirement_contract(reqs,expected_required_ids=ids)
    mutation=req_kernel.requirement_mutation_score(reqs)
    if compiled.get("pass") is not True: raise StructuredTaskScopeError("REQUIREMENT_GRAPH_FAIL_CLOSED")
    if mutation.get("pass") is not True or mutation.get("kill_fraction")!=1.0:
        raise StructuredTaskScopeError("REQUIREMENT_MUTATION_COVERAGE_INCOMPLETE")
    od=obligation_universe_digest(obs);sid=task_scope_id(task_id=task_id,task_sha256=target_sha,obligation_digest=od)
    cert={"id":"professional-structured-semantic-scope:"+target_sha,"target_scope_id":sid,"basis":"EXACT_COMPLETE_TARGET_CASE_UNIVERSE",
      "verified":False,"independent":False,"scope_relation":"EXACT","complete_target_case_set":True,"universe_identity_bound":True,
      "case_universe_digest":od,"obligation_universe_digest":od,"producer_id":CAPABILITY_ID,
      "scope_kind":"DECLARED_STRUCTURED_PROFESSIONAL_SEMANTIC_FULFILLMENT_SLICE"}
    return {"schema":SCHEMA,"capability_id":CAPABILITY_ID,"status":"PASS__STRUCTURED_DECLARED_SEMANTIC_OBLIGATION_SCOPE_COMPILED","pass":True,
      "task_id":task_id,"task_sha256":target_sha,"target_instance_sha256":target_sha,"contract_sha256":_digest(contract),
      "contract_registry_git_blob_sha":CONTRACT_REGISTRY_BLOB,"requirement_kernel_git_blob_sha":REQUIREMENT_KERNEL_BLOB,
      "obligations":obs,"obligation_count":len(obs),"obligation_universe_digest":od,"target_scope_id":sid,"scope_certificate":cert,
      "requirement_graph":compiled,"requirement_mutation_score":mutation,
      "covered_failure_atoms":["Polished but unsupported content","wrong audience emphasis","omitted required analysis"],
      "excluded_nonsemantic_or_comparative_atoms":["layout choice obscures information","revisions do not improve independent quality"],
      "arbitrary_prompt_semantic_completeness":False,"source_extraction_completeness":False,"presentation_quality_authority":False,
      "owner_evaluator_authority":False,"quality_authority":False,"benchmark_score_authority":False,"terminal_authority":False,
      "external_general_purpose_model_runtime_dependency_count":0,"incremental_spend_usd":0,
      "hard_nonclaims":["NO_ARBITRARY_NATURAL_LANGUAGE_REQUIREMENT_EXTRACTION","NO_SOURCE_EXTRACTION_COMPLETENESS",
        "NO_HOLISTIC_PRESENTATION_QUALITY_TOP","NO_COMPARATIVE_QUALITY_IMPROVEMENT_PROOF","NO_OWNER_EVALUATOR_CONTAINMENT",
        "NO_GLOBAL_PROFESSIONAL_SCOPE_COMPLETENESS","NO_GDPVAL_OR_BRAIN_GE_OPUS_CLAIM"]}

if __name__=="__main__":
    print(json.dumps({"schema":SCHEMA,"status":"NOT_EXECUTED"},indent=2,sort_keys=True))
