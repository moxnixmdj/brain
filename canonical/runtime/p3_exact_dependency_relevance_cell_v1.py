"""P3 exact decision-dependency relevance cell v1.

Uses an independently verified exact/complete decision-relevance dependency graph
over current claim IDs. Optional claim IDs inside the reachable goal dependency
cone are RELEVANT; optional IDs outside it are IRRELEVANT. Required claims remain
included. The verification receipt is byte-authenticated from canonical
verification storage. No global P3/U/terminal authority is granted.
"""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping
from canonical.runtime.effect_broker_receipt_resolver_v2 import resolve_receipt_bytes
from canonical.runtime import goal_dependency_delta_v4 as delta
from canonical.runtime.p3_required_claim_grounded_realization_cell_v3 import evaluate as realize

SCHEMA="PROJECT_BRAIN_P3_EXACT_DEPENDENCY_RELEVANCE_CELL_V1"

def _fail(reason:str,**detail:Any)->dict[str,Any]:
    out={"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
      "p3_contract_cell_authorized":False,"truthful_precommitment_relevance_bit_bound":False,
      "source_authorization_verified":False,"policy_adequacy_authority":False,
      "db_admission_authority":False,"u_subtraction_authority":False,
      "terminal_authority":False,"terminal_credit_delta":0}
    if detail: out["detail"]=detail
    return out

def _claim_set_digest(ids:list[str])->str:
    raw=json.dumps(sorted(ids),separators=(",",":"),ensure_ascii=False).encode()
    return "sha256:"+sha256(raw).hexdigest()

def evaluate(payload:Mapping[str,Any],*,repo_root:str|Path)->dict[str,Any]:
    try:
        if not isinstance(payload,Mapping): return _fail("PAYLOAD_MAPPING_REQUIRED")
        public=payload.get("v3_input"); contract=payload.get("decision_dependency_contract")
        if not isinstance(public,Mapping): return _fail("V3_INPUT_REQUIRED")
        if not isinstance(contract,Mapping): return _fail("DECISION_DEPENDENCY_CONTRACT_REQUIRED")
        task=public.get("task")
        if not isinstance(task,Mapping): return _fail("TASK_REQUIRED")
        claims=task.get("claims")
        if not isinstance(claims,list) or not claims: return _fail("CLAIMS_REQUIRED")
        claim_ids=[];required_ids=[];optional_ids=[]
        for row in claims:
            if not isinstance(row,Mapping): return _fail("CLAIM_ROW_INVALID")
            cid=row.get("claim_id"); req=row.get("required")
            if not isinstance(cid,str) or not cid or cid in claim_ids: return _fail("CLAIM_ID_INVALID_OR_DUPLICATE")
            if req not in (True,False): return _fail("CLAIM_REQUIRED_FLAG_INVALID",claim_id=cid)
            if "include" in row: return _fail("CALLER_INCLUDE_FORBIDDEN",claim_id=cid)
            claim_ids.append(cid); (required_ids if req else optional_ids).append(cid)

        environment_id=contract.get("environment_id"); goal_id=contract.get("goal_id")
        goals=contract.get("goal_nodes"); dependencies=contract.get("dependencies")
        ref=contract.get("dependency_verification_ref")
        if not isinstance(environment_id,str) or not environment_id: return _fail("ENVIRONMENT_ID_REQUIRED")
        if not isinstance(goal_id,str) or not goal_id: return _fail("GOAL_ID_REQUIRED")
        if not isinstance(goals,list) or not goals or any(not isinstance(x,str) or not x for x in goals): return _fail("GOAL_NODES_INVALID")
        if not isinstance(dependencies,Mapping): return _fail("DEPENDENCIES_REQUIRED")
        if not isinstance(ref,Mapping): return _fail("DEPENDENCY_VERIFICATION_REF_REQUIRED")
        path=ref.get("path")
        if not isinstance(path,str) or not path.startswith("canonical/verification/"):
            return _fail("DEPENDENCY_VERIFICATION_MUST_BE_CANONICAL_VERIFICATION")

        bound=resolve_receipt_bytes(ref,repo_root=repo_root); receipt=bound["document"]
        if receipt.get("independent_verified") is not True: return _fail("DEPENDENCY_VERIFICATION_NOT_INDEPENDENT")
        if receipt.get("exact_byte_bound") is not True or receipt.get("conclusion")!="success":
            return _fail("DEPENDENCY_VERIFICATION_NOT_SUCCESSFULLY_BYTE_BOUND")
        if receipt.get("decision_relevant_dependency_graph_complete") is not True:
            return _fail("DECISION_RELEVANT_GRAPH_COMPLETENESS_UNPROVED")
        if receipt.get("claim_id_set_sha256") != _claim_set_digest(claim_ids):
            return _fail("CLAIM_ID_UNIVERSE_BINDING_MISMATCH")
        expected_graph=delta.dependency_digest(goals=goals,dependencies=dependencies)
        if receipt.get("dependency_graph_sha256") != expected_graph: return _fail("DEPENDENCY_GRAPH_DIGEST_MISMATCH")
        if receipt.get("environment_id") != environment_id or receipt.get("goal_id") != goal_id:
            return _fail("DEPENDENCY_SCOPE_MISMATCH")

        novelty=delta.minimum_goal_delta(environment_id=environment_id,goal_id=goal_id,goals=goals,
          verified_facts=[],dependencies=dependencies,dependency_receipt=receipt)
        reachable=set(novelty["missing"])
        relevant=[cid for cid in optional_ids if cid in reachable]
        irrelevant=[cid for cid in optional_ids if cid not in reachable]
        selected=set(required_ids)|set(relevant)

        compiled=deepcopy(dict(public)); ctask=compiled["task"]; selected_rows=[]
        for row in ctask["claims"]:
            if row["claim_id"] not in selected: continue
            nr=dict(row);nr["required"]=True;selected_rows.append(nr)
        if not selected_rows: return _fail("NO_SELECTED_CLAIMS")
        ctask["claims"]=selected_rows;ctask.pop("claim_order",None)
        realized=realize({"v3_input":compiled})
        if realized.get("pass") is not True: return _fail("SELECTED_GROUNDED_REALIZATION_FAILED",realization=realized)
        if any((realized.get(k) is not False) for k in ("source_authorization_verified","policy_adequacy_authority","db_admission_authority","u_subtraction_authority","terminal_authority")) or realized.get("terminal_credit_delta")!=0:
            return _fail("DOWNSTREAM_AUTHORITY_BOUNDARY_INVALID")
        return {"schema":SCHEMA,"pass":True,
          "status":"PASS__EXACT_COMPLETE_DEPENDENCY_GRAPH_OPTIONAL_RELEVANCE_CELL",
          "environment_id":environment_id,"goal_id":goal_id,
          "dependency_verification_path":bound["path"],"dependency_verification_git_blob_sha":bound["git_blob_sha"],
          "dependency_graph_sha256":expected_graph,"decision_relevant_dependency_graph_complete":True,
          "required_claim_ids":required_ids,"optional_relevant_claim_ids":relevant,
          "optional_irrelevant_claim_ids":irrelevant,"selected_claim_ids":[cid for cid in claim_ids if cid in selected],
          "relevance_bits":{cid:("RELEVANT" if cid in relevant else "IRRELEVANT") for cid in optional_ids},
          "truthful_precommitment_relevance_bit_bound":True,"p3_contract_cell_authorized":True,
          "rendered_text":realized.get("rendered_text"),"render_trace":realized.get("render_trace"),
          "realization_receipt":realized,"source_authorization_verified":False,
          "policy_adequacy_authority":False,"db_admission_authority":False,
          "u_subtraction_authority":False,"terminal_authority":False,"terminal_credit_delta":0,
          "boundary":"EXACT_COMPLETE_INDEPENDENTLY_VERIFIED_DECISION_RELEVANCE_DEPENDENCY_GRAPH_OVER_CURRENT_CLAIM_ID_UNIVERSE_ONLY"}
    except Exception as exc:
        return _fail("INVALID_INPUT",exception_type=type(exc).__name__,detail_text=str(exc)[:200])

def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
    return evaluate(args or {},repo_root=root or Path(__file__).resolve().parents[2])
