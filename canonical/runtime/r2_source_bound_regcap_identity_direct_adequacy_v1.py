from __future__ import annotations
from hashlib import sha256
import json,re
from pathlib import Path
from typing import Any,Mapping
from canonical.runtime import nyfed_loss_cushion_ccob_source_identity_v1 as identity
from canonical.runtime import https_source_fragment_projection_authority_v2 as projection
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.r2_grounded_candidate_policy_frontier_v1 import goal_scoped_policy_id

SCHEMA="PROJECT_BRAIN_R2_SOURCE_BOUND_REGCAP_IDENTITY_DIRECT_ADEQUACY_V1"
ROUTE_ID="DIRECT_ADEQUACY::SOURCE_BOUND_REGCAP_IDENTITY_NYFED_CCOB_V1"
CAPABILITY_ID="finance.regcap.source_bound_identity.nyfed_ccob"
ROOT=Path(__file__).resolve().parents[2]
PATH_RE=r"canonical/[A-Za-z0-9_.\-/]+"
GRAMMAR=re.compile(
 r'^Identify the regulatory-capital concept for "loss-absorbing cushion" in source '
 r'NYFED_DUDLEY_BASEL_2010_10_10 and save the verified concept identity to '
 r'(?P<output>'+PATH_RE+r'\.json)\.?$',re.IGNORECASE)

def _base(status,passed=False):
 return {"schema":SCHEMA,"status":status,"pass":passed,"matched":False,
 "semantic_acceptance_complete":False,"actual_goal_satisfaction_verified":False,
 "direct_adequacy_authority":False,"terminal_authority":False,
 "terminal_credit_delta":0,"incremental_spend_usd":0}

def _safe(root,rel):
 root=root.resolve(); p=(root/rel).resolve()
 if p==root or root not in p.parents or p.is_symlink(): raise ValueError("OUTPUT_PATH_INVALID")
 return p

def _contract(goal):
 out=compile_contract(goal,source_id="user",
  routing_target_effects=["finance.regcap.source_bound_concept_identity"])
 ids=list((out.get("acceptance_contract") or {}).get("required_obligation_ids") or [])
 if out.get("pass") is not True or not ids: raise ValueError("RAW_TASK_CONTRACT_INVALID")
 return out,ids

def _independent(root,opener=None):
 pack=identity.load_pack(repo_root=root)
 src=projection.verify_projection_pack(pack,opener=opener)
 if src.get("pass") is not True: raise RuntimeError("SOURCE_PROJECTION_FAILED")
 rows={str(x.get("fragment_id") or ""):x for x in src.get("matched_fragments") or [] if isinstance(x,Mapping)}
 if identity.IDENTITY_FRAGMENT_ID not in rows or identity.LOSS_CUSHION_FRAGMENT_ID not in rows:
  raise RuntimeError("REQUIRED_FRAGMENT_MISSING")
 a=rows[identity.IDENTITY_FRAGMENT_ID]; b=rows[identity.LOSS_CUSHION_FRAGMENT_ID]
 gap=int(b.get("fragment_index"))-int(a.get("fragment_index"))
 if gap<=0 or gap>identity.MAX_RELATION_GAP_CHARS: raise RuntimeError("FRAGMENT_RELATION_INVALID")
 if a.get("section_anchor")!=b.get("section_anchor"): raise RuntimeError("SECTION_RELATION_INVALID")
 receipt=src.get("receipt") or {}
 if receipt.get("pass") is not True: raise RuntimeError("SOURCE_RECEIPT_INVALID")
 return {"producer_independent":True,"verified":True,"mapped_concept_id":regcap.CCOB,
  "source_id":identity.SOURCE_ID,"exact_surface":identity.EXACT_SURFACE,
  "relation_gap_chars":gap,"source_receipt_sha256":receipt.get("receipt_sha256")}

def preflight(request:Mapping[str,Any],*,repo_root=None):
 root=Path(repo_root).resolve() if repo_root is not None else ROOT
 if not isinstance(request,Mapping): return {**_base("FAIL_CLOSED"),"reason":"REQUEST_NOT_OBJECT"}
 task=str(request.get("task_id") or "").strip(); goal=str(request.get("goal") or "").strip()
 if not task or not goal: return {**_base("FAIL_CLOSED"),"reason":"TASK_ID_AND_GOAL_REQUIRED"}
 m=GRAMMAR.fullmatch(goal)
 if m is None: return {**_base("NOT_APPLICABLE"),"matched":False}
 try:
  output=m.group("output"); _safe(root,output); contract,ids=_contract(goal)
  return {**_base("DIRECT_ADEQUACY_ROUTE_MATCHED"),"matched":True,"route_id":ROUTE_ID,
   "capability_id":CAPABILITY_ID,"task_id":task,"goal":goal,
   "goal_sha256":sha256(goal.encode()).hexdigest(),
   "policy_id":goal_scoped_policy_id(CAPABILITY_ID,goal),"output_path":output,
   "source_id":identity.SOURCE_ID,"exact_surface":identity.EXACT_SURFACE,
   "expected_concept_id":regcap.CCOB,"raw_task_contract_sha256":contract["task_contract_sha256"],
   "raw_acceptance_obligation_ids":ids,"preflight_execution_authority":False}
 except Exception as exc:
  return {**_base("FAIL_CLOSED"),"matched":True,"route_id":ROUTE_ID,
   "reason":type(exc).__name__+":"+str(exc)}

def _restore(path,existed,original):
 if existed: path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(original or b"")
 elif path.exists(): path.unlink()

def run(request:Mapping[str,Any],*,repo_root=None,independent_provider=None):
 root=Path(repo_root).resolve() if repo_root is not None else ROOT
 pf=preflight(request,repo_root=root)
 if pf.get("matched") is not True or pf.get("status")=="FAIL_CLOSED": return pf
 output=_safe(root,pf["output_path"]); existed=output.is_file(); original=output.read_bytes() if existed else None
 try:
  produced=identity.verify(repo_root=root)
  if produced.get("pass") is not True or produced.get("mapped_concept_id")!=regcap.CCOB:
   raise RuntimeError("PRODUCER_IDENTITY_NOT_VERIFIED")
  independent=(independent_provider(root) if independent_provider else _independent(root))
  if (not isinstance(independent,Mapping) or independent.get("producer_independent") is not True
      or independent.get("verified") is not True or independent.get("mapped_concept_id")!=regcap.CCOB
      or independent.get("source_id")!=identity.SOURCE_ID
      or str(independent.get("exact_surface") or "").casefold()!=identity.EXACT_SURFACE):
   raise RuntimeError("INDEPENDENT_IDENTITY_MISMATCH")
  payload={"schema":SCHEMA,"status":"SOURCE_BOUND_REGCAP_IDENTITY_VERIFIED",
   "source_id":identity.SOURCE_ID,"exact_surface":identity.EXACT_SURFACE,
   "mapped_concept_id":regcap.CCOB,"global_phrase_identity_authority":False,
   "open_world_ontology_complete":False,"output_verified":True}
  output.parent.mkdir(parents=True,exist_ok=True)
  output.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
  readback=json.loads(output.read_text(encoding="utf-8"))
  if readback!=payload: raise RuntimeError("OUTPUT_READBACK_MISMATCH")
  _,accepted=_contract(str(request["goal"]))
  if accepted!=pf["raw_acceptance_obligation_ids"]: raise RuntimeError("RAW_ACCEPTANCE_SET_DRIFT")
  return {**_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED",True),"matched":True,
   "route_id":ROUTE_ID,"capability_id":CAPABILITY_ID,"selected_policy_id":pf["policy_id"],
   "goal_sha256":pf["goal_sha256"],"mapped_concept_id":regcap.CCOB,
   "output_path":pf["output_path"],"output_sha256":sha256(output.read_bytes()).hexdigest(),
   "semantic_acceptance_complete":True,"actual_goal_satisfaction_verified":True,
   "direct_adequacy_authority":True,"accepted_raw_obligation_ids":accepted,
   "acceptance_receipt":{"verified":True,"producer_independent":True,
    "verifier":"INDEPENDENT_HTTPS_FRAGMENT_RELATION_REDERIVATION_V1",
    "mapped_concept_id":regcap.CCOB,"global_phrase_identity_authority":False},
   "execution_attempted":True,"retry_by_other_route_authorized":False,
   "authority_boundary":"EXACT_AUTHENTICATED_NYFED_SOURCE_CONTEXT_ONLY__NO_GLOBAL_SYNONYMY_OR_OPEN_WORLD_ONTOLOGY"}
 except Exception as exc:
  _restore(output,existed,original)
  rollback=(output.is_file() and existed and output.read_bytes()==(original or b"")) if existed else not output.exists()
  return {**_base("OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY"),"matched":True,
   "route_id":ROUTE_ID,"capability_id":CAPABILITY_ID,"goal_sha256":pf.get("goal_sha256"),
   "execution_attempted":True,"retry_by_other_route_authorized":False,
   "rollback_complete":rollback,"reason":type(exc).__name__+":"+str(exc)}
