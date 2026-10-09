from copy import deepcopy
from typing import Any, Mapping
from canonical.runtime import loss_absorbing_cushion_regcap_grounding_v2 as v2
from canonical.runtime import regcap_candidate_ambiguity_control_v2 as ambiguity

SCHEMA="PROJECT_BRAIN_LOSS_ABSORBING_CUSHION_REGCAP_GROUNDING_V3"

def ground(source_text:str,*,source_id:str,start:int,end:int,mapping_scope:Mapping[str,Any]|None=None,observation_cost_units:Mapping[str,float]|None=None,information_owner:str="SYSTEM_MODEL",source_scope:Mapping[str,Any]|None=None,discovery_delegated:bool=False,repo_root:Any=None)->dict[str,Any]:
    base=v2.ground(source_text,source_id=source_id,start=start,end=end,repo_root=repo_root)
    out=deepcopy(dict(base)); out["schema"]=SCHEMA
    out["ambiguity_control_attempted"]=False; out["authenticated_matrix_reused"]=False
    out.setdefault("terminal_authority",False); out.setdefault("terminal_credit_delta",0)
    if base.get("status")=="FAIL_CLOSED": return out
    if base.get("pass") is True and base.get("fully_semantically_bound") is True and base.get("mapped_concept_id"):
        out["status"]="PASS__SOURCE_LOCAL_REGCAP_IDENTITY_PRECEDENCE"
        return out
    candidates=base.get("candidate_discovery")
    if not isinstance(candidates,Mapping) or mapping_scope is None: return out
    plan=ambiguity.plan_with_authenticated_matrix(
        candidates,mapping_scope=mapping_scope,
        observation_cost_units=observation_cost_units,information_owner=information_owner,
        source_scope=source_scope,discovery_delegated=discovery_delegated,
        repo_root=repo_root)
    out["ambiguity_control_attempted"]=True
    out["ambiguity_control"]=deepcopy(dict(plan))
    out["authenticated_matrix_reused"]=plan.get("authenticated_matrix_reused") is True
    out["next_observation_id"]=plan.get("next_observation_id")
    out["minimum_worst_case_cost_units"]=plan.get("minimum_worst_case_cost_units")
    out["minimum_information_action"]=plan.get("action")
    if plan.get("status")=="FAIL_CLOSED":
        out["status"]="FAIL_CLOSED"; out["pass"]=False
        out["reason"]="REGCAP_AMBIGUITY_CONTROL_FAIL_CLOSED:"+str(plan.get("reason") or "UNKNOWN")
    else:
        out["status"]=str(plan.get("status") or base.get("status"))
        out["pass"]=plan.get("pass") is True
        out["semantic_identity_authority"]=plan.get("semantic_identity_authority") is True
        out["semantic_truth_authority"]=plan.get("semantic_truth_authority") is True
    out["policy_adequacy_authority"]=False; out["execution_authority"]=False
    out["acceptance_authority"]=False; out["promotion_authority"]=False
    out["terminal_authority"]=False; out["terminal_credit_delta"]=0
    out["open_world_ontology_complete"]=False
    return out
