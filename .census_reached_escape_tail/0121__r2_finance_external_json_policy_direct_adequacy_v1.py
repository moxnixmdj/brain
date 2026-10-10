"""R2 direct adequacy for state-keyed externally observed finance JSON policy.

Composition:
1. validate one task-bound finance policy case;
2. use the already-verified state-keyed HTTPS JSON observation direct route;
3. require its producer-independent semantic-equality receipt;
4. compute an exact Boolean/decimal predicate over one JSON path;
5. independently recompute the policy result;
6. commit only after readback verification.

The external endpoint is observed, not declared authoritative or globally true.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime import r2_http_json_observation_direct_adequacy_v1 as http_observation
from canonical.runtime import finance_external_json_policy_v1 as producer
from canonical.runtime import finance_external_json_policy_verify_v1 as verifier

SCHEMA="PROJECT_BRAIN_R2_FINANCE_EXTERNAL_JSON_POLICY_DIRECT_ADEQUACY_V1"
ROUTE_ID="DIRECT_ADEQUACY::FINANCE_STATE_KEYED_EXTERNAL_JSON_POLICY_FAMILY_V1"
CAPABILITY_ID="finance.external_json_policy.stdlib"
VERIFIER_CAPABILITY_ID="finance.external_json_policy.verify.stdlib"
ROOT=Path(__file__).resolve().parents[2]
GRAMMAR=re.compile(
 r"Using the authenticated finance external JSON case at "
 r"(?P<input>canonical/[A-Za-z0-9_.\-/]+\.json), fetch and independently "
 r"verify the external observation, select the action, and save it to "
 r"(?P<output>canonical/[A-Za-z0-9_.\-/]+\.json)\.?",
 re.I,
)


def _base(status,passed=False):
 return {"schema":SCHEMA,"status":status,"pass":passed,"matched":False,
 "semantic_acceptance_complete":False,"actual_goal_satisfaction_verified":False,
 "direct_adequacy_authority":False,"terminal_authority":False,
 "terminal_credit_delta":0,"incremental_spend_usd":0}


def _safe(root,rel,file=False):
 root=Path(root).resolve(); p=Path(str(rel or "").strip())
 if p.is_absolute() or ".." in p.parts or not p.as_posix().startswith("canonical/"):
  raise ValueError("PATH_INVALID")
 q=(root/p).resolve()
 if q==root or root not in q.parents: raise ValueError("PATH_OUTSIDE_REPOSITORY")
 if file and (not q.is_file() or q.is_symlink()): raise ValueError("FILE_REQUIRED")
 return q


def _sha(path):
 return sha256(Path(path).read_bytes()).hexdigest()


def _contract(goal):
 out=compile_contract(goal,source_id="user",routing_target_effects=["finance.external_json_policy"])
 if out.get("pass") is not True: raise ValueError("RAW_TASK_CONTRACT_FAIL_CLOSED")
 ids=list((out.get("acceptance_contract") or {}).get("required_obligation_ids") or [])
 if not ids: raise ValueError("RAW_ACCEPTANCE_OBLIGATIONS_MISSING")
 return out


def _nested_request(case):
 goal=(
  "Fetch JSON from URL key "+case["url_key"]+" in "+case["state_path"]
  +" and save the verified result to "+case["observation_output_path"]+"."
 )
 return {"task_id":"finance-external-observation::"+str(case["case_id"]),"goal":goal}


def preflight(request:Mapping[str,Any],*,repo_root=None):
 root=Path(repo_root).resolve() if repo_root is not None else ROOT
 if not isinstance(request,Mapping): return {**_base("FAIL_CLOSED"),"reason":"REQUEST_NOT_OBJECT"}
 goal=str(request.get("goal") or "").strip(); task=str(request.get("task_id") or "").strip()
 if not goal or not task: return {**_base("FAIL_CLOSED"),"reason":"TASK_ID_AND_GOAL_REQUIRED"}
 m=GRAMMAR.fullmatch(goal)
 if not m: return {**_base("NOT_APPLICABLE"),"matched":False}
 try:
  inp,out=m.group("input"),m.group("output")
  ip=_safe(root,inp,True); op=_safe(root,out)
  if ip==op: raise ValueError("INPUT_OUTPUT_COLLISION")
  raw=ip.read_bytes(); case=json.loads(raw.decode("utf-8"))
  spec=producer.validate_case(case)
  state=_safe(root,spec["state_path"],True)
  obs=_safe(root,spec["observation_output_path"])
  if len({str(ip),str(op),str(state),str(obs)})!=4:
   raise ValueError("CASE_STATE_OBSERVATION_OUTPUT_COLLISION")
  nested=_nested_request(spec)
  hp=http_observation.preflight(nested,repo_root=root)
  if hp.get("matched") is not True or hp.get("status")=="FAIL_CLOSED":
   raise ValueError("HTTP_OBSERVATION_PREFLIGHT_FAILED:"+str(hp.get("reason") or hp.get("status")))
  if hp.get("output_path")!=spec["observation_output_path"]:
   raise ValueError("HTTP_OBSERVATION_OUTPUT_BINDING_MISMATCH")
  contract=_contract(goal)
  gsha=sha256(goal.encode()).hexdigest()
  return {**_base("DIRECT_ADEQUACY_ROUTE_MATCHED"),"matched":True,"route_id":ROUTE_ID,
   "capability_id":CAPABILITY_ID,"verifier_capability_id":VERIFIER_CAPABILITY_ID,
   "goal_sha256":gsha,"policy_id":"R2_FINANCE_EXTERNAL_JSON_POLICY::"+gsha+"::"+sha256(raw).hexdigest(),
   "input_path":inp,"input_sha256":sha256(raw).hexdigest(),"output_path":out,
   "state_path":spec["state_path"],"state_sha256":_sha(state),
   "observation_output_path":spec["observation_output_path"],
   "nested_http_request":nested,
   "nested_http_route_id":hp.get("route_id"),
   "nested_http_requested_url":hp.get("requested_url"),
   "raw_acceptance_obligation_ids":list(contract["acceptance_contract"]["required_obligation_ids"]),
   "semantic_scope":"STATE_KEYED_INDEPENDENTLY_REFETCHED_HTTPS_JSON_VALUE_TO_EXACT_BOOLEAN_OR_DECIMAL_FINANCE_POLICY",
   "preflight_execution_authority":False}
 except Exception as exc:
  return {**_base("FAIL_CLOSED"),"matched":True,"route_id":ROUTE_ID,
   "reason":type(exc).__name__+":"+str(exc)}


def _restore(path,existed,raw):
 if existed:
  path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(raw or b"")
 else:
  try:path.unlink()
  except FileNotFoundError:pass


def run(request:Mapping[str,Any],*,repo_root=None,http_runner=None):
 root=Path(repo_root).resolve() if repo_root is not None else ROOT
 pf=preflight(request,repo_root=root)
 if pf.get("matched") is not True or pf.get("status")=="FAIL_CLOSED": return pf
 ip=_safe(root,pf["input_path"],True); state=_safe(root,pf["state_path"],True)
 obs=_safe(root,pf["observation_output_path"]); op=_safe(root,pf["output_path"])
 obs_existed=obs.is_file(); obs_old=obs.read_bytes() if obs_existed else None
 out_existed=op.is_file(); out_old=op.read_bytes() if out_existed else None
 try:
  case_before=ip.read_bytes(); state_before=state.read_bytes()
  if sha256(case_before).hexdigest()!=pf["input_sha256"]: raise RuntimeError("CASE_DRIFT_BEFORE_EXECUTION")
  if sha256(state_before).hexdigest()!=pf["state_sha256"]: raise RuntimeError("STATE_DRIFT_BEFORE_EXECUTION")
  case=json.loads(case_before.decode("utf-8"))
  runner=http_runner or http_observation.run
  h=runner(pf["nested_http_request"],repo_root=root)
  if not isinstance(h,Mapping) or h.get("pass") is not True:
   raise RuntimeError("HTTP_OBSERVATION_DID_NOT_VERIFY:"+str(h.get("reason") if isinstance(h,Mapping) else h))
  receipt=h.get("acceptance_receipt")
  if (
   not isinstance(receipt,Mapping)
   or receipt.get("verified") is not True
   or receipt.get("producer_independent") is not True
   or receipt.get("semantic_json_equal") is not True
  ):
   raise RuntimeError("HTTP_OBSERVATION_INDEPENDENT_RECEIPT_REQUIRED")
  if h.get("output_path")!=pf["observation_output_path"] or not obs.is_file():
   raise RuntimeError("HTTP_OBSERVATION_OUTPUT_MISSING_OR_MISMATCH")
  observation=json.loads(obs.read_text(encoding="utf-8"))
  result=producer.compute(case,observation)
  check=verifier.verify(case,observation,result)
  if check.get("verified") is not True:
   raise RuntimeError("EXTERNAL_JSON_POLICY_VERIFICATION_FAILED:"+",".join(check.get("errors") or []))
  if ip.read_bytes()!=case_before or state.read_bytes()!=state_before:
   raise RuntimeError("INPUT_MUTATION_DETECTED")
  op.parent.mkdir(parents=True,exist_ok=True)
  op.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
  reread=json.loads(op.read_text(encoding="utf-8"))
  check2=verifier.verify(case,observation,reread)
  if check2.get("verified") is not True: raise RuntimeError("OUTPUT_READBACK_VERIFICATION_FAILED")
  contract=_contract(str(request["goal"])); ids=list(contract["acceptance_contract"]["required_obligation_ids"])
  if ids!=pf["raw_acceptance_obligation_ids"]: raise RuntimeError("RAW_ACCEPTANCE_SET_DRIFT")
  return {**_base("PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED",True),"matched":True,
   "route_id":ROUTE_ID,"capability_id":CAPABILITY_ID,"verifier_capability_id":VERIFIER_CAPABILITY_ID,
   "selected_policy_id":pf["policy_id"],"goal_sha256":pf["goal_sha256"],
   "input_path":pf["input_path"],"input_sha256":pf["input_sha256"],
   "state_path":pf["state_path"],"state_sha256":pf["state_sha256"],
   "observation_output_path":pf["observation_output_path"],
   "observation_output_sha256":_sha(obs),"output_path":pf["output_path"],"output_sha256":_sha(op),
   "nested_http_route_id":pf["nested_http_route_id"],
   "nested_http_requested_url":pf["nested_http_requested_url"],
   "external_observation_receipt":deepcopy(dict(receipt)),
   "predicate_holds":result["predicate_holds"],"selected_action":result["selected_action"],
   "policy_binding_sha256":result["policy_binding_sha256"],
   "semantic_scope":pf["semantic_scope"],"semantic_acceptance_complete":True,
   "actual_goal_satisfaction_verified":True,"direct_adequacy_authority":True,
   "accepted_raw_obligation_ids":ids,"raw_acceptance_obligation_count":len(ids),
   "acceptance_receipt":deepcopy(dict(check2)),"execution_attempted":True,
   "retry_by_other_route_authorized":False,"source_immutability_verified":True,
   "endpoint_authority_claimed":False,"external_world_truth_claimed":False,
   "authority_boundary":"STATE_KEYED_HTTPS_JSON_OBSERVATION_MUST_ALREADY_PASS_PRODUCER_INDEPENDENT_SEMANTIC_REFETCH__POLICY_IS_EXACT_JSON_PATH_BOOLEAN_OR_DECIMAL_PREDICATE_ONLY__NO_ENDPOINT_AUTHORITY_CAUSALITY_COMPLETENESS_OR_GLOBAL_TRUTH"}
 except Exception as exc:
  _restore(op,out_existed,out_old); _restore(obs,obs_existed,obs_old)
  return {**_base("OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY"),"matched":True,
   "route_id":ROUTE_ID,"capability_id":CAPABILITY_ID,"goal_sha256":pf.get("goal_sha256"),
   "execution_attempted":True,"retry_by_other_route_authorized":False,
   "rollback_complete":(
    ((op.is_file() and out_existed and op.read_bytes()==(out_old or b"")) if out_existed else not op.exists())
    and ((obs.is_file() and obs_existed and obs.read_bytes()==(obs_old or b"")) if obs_existed else not obs.exists())
   ),
   "reason":type(exc).__name__+":"+str(exc)}
