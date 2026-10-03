"""Candidate scope/interface certificate for converged Tool Discovery V5 + common matched authority V3.

This proves a construction theorem, not Opus acceptance:
for any finite frozen matched authority R whose decision-relevant hidden capability
facts are either already current-evidenced or explicitly safe-probe decidable,
the same route-neutral authority can supply Contract V3 to both BRAIN and OPUS55,
while converged V5 discovers all identities before selecting and fails closed on
unobservable cheaper routes.

Independent exact-byte public verification is mandatory before activation.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.common_frozen_tool_authority_v3 import (
    AuthorityError,
    CommonFrozenToolAuthorityV3,
    execute_v5,
    prove_instance,
)

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_COMMON_AUTHORITY_V5_V3_CERTIFICATE_V1"

PROTOCOL="canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
REGISTRY="canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
V5="canonical/runtime/tool_discovery_dynamic_candidate_v5.py"
CONTRACT="canonical/governance/TOOL_DISCOVERY_COMPLETE_INTERFACE_CONTRACT_V3.json"
AUTHORITY="canonical/runtime/common_frozen_tool_authority_v3.py"
TESTS="canonical/tests/test_common_frozen_tool_authority_v3.py"

EXPECTED={
 PROTOCOL:"62394e5b7d221ec9f69c3458f669e40e253a9d09",
 REGISTRY:"ee187f611a0e82b2de495ee377682f39bc31dd31",
 V5:"42d096ef93e8ad06c4d1d5dfe730881bf45a2a72",
 CONTRACT:"e39912efd13b6aeb70a9e22b9e6dac55823c0324",
 AUTHORITY:"b09677cf0f46176e827cd4f910d0f85717c39477",
 TESTS:"f82338351f491fdfa6c87fab350c0aaeb4026b1d",
}

CONTRACT_V3_PROPERTIES={
 "FINITE_EXPLICITLY_CLASSIFIED_DISCOVERY_SOURCE_SET_PER_DECISION_EPOCH",
 "POLICY_COMPUTES_SOURCE_SET_DIGEST_FROM_EXACT_SOURCE_METADATA",
 "EACH_SOURCE_HAS_STABLE_SOURCE_EPOCH_AND_CANONICAL_EXPECTED_RESULT_CONTENT_DIGEST_OR_EPISODE_RESTARTS",
 "DISCOVERY_RECEIPT_IS_COMPLETE_CURRENT_DECISION_EPOCH_CURRENT_SOURCE_EPOCH_EXACT_REQUIREMENT_QUERY_AND_EXACT_RESULT_CONTENT_BOUND",
 "UNION_OF_CURRENT_COMPLETE_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE",
 "DISCOVERED_TOOL_METADATA_IS_CORRECT_AND_SAME_ID_METADATA_IS_CONSISTENT_WITHIN_EPOCH",
 "EVERY_ADMISSIBLE_REQUIRED_CAPABILITY_IS_CURRENTLY_EVIDENCED_OR_EXPLICITLY_SAFE_PROBE_DECIDABLE",
 "SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_AND_TOOL_EPOCH_BOUND",
 "UNRESOLVED_CHEAPER_ADMISSIBLE_ROUTE_WITHOUT_SAFE_PROBE_BLOCKS_MORE_EXPENSIVE_SELECTION",
 "VERSION_OR_AUTHORITY_CHANGE_RESTARTS_OR_INVALIDATES_STALE_EVIDENCE",
}

def _blob(rel:str)->str:
 data=(ROOT/rel).read_bytes()
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def _load(rel:str)->dict[str,Any]:
 v=json.loads((ROOT/rel).read_text(encoding="utf-8"))
 if not isinstance(v,dict): raise ValueError(rel+":NOT_OBJECT")
 return v

def _find_behavior(v:Any)->dict[str,Any]|None:
 if isinstance(v,dict):
  if v.get("behavior_id")=="TOOL_ROUTE_DISCOVERY_AND_SELECTION_001": return v
  for x in v.values():
   y=_find_behavior(x)
   if y is not None: return y
 elif isinstance(v,list):
  for x in v:
   y=_find_behavior(x)
   if y is not None: return y
 return None

def _row(tid,cost,source,supported,*,safe=True,region="GLOBAL"):
 return {
  "tool_id":tid,"source_id":source,"cost":float(cost),
  "available":True,"authorized":True,
  "safe_probe_capabilities":["CAP_X"] if safe else [],
  "capabilities":["CAP_X"] if supported else [],
  "region":region,
 }

def evaluate()->dict[str,Any]:
 drift={p:{"expected":want,"actual":_blob(p)} for p,want in EXPECTED.items() if _blob(p)!=want}
 if drift:
  return _fail("SOURCE_BLOB_DRIFT",source_blob_drift=drift)

 protocol=_load(PROTOCOL)
 contract=_load(CONTRACT)
 behavior=_find_behavior(_load(REGISTRY))
 row=next((x for x in protocol.get("protocols",[]) if x.get("family")=="TOOL_DISCOVERY_SELECTION_AND_LEARNING"),None)
 if row is None or behavior is None:
  return _fail("FROZEN_TARGET_NOT_FOUND")

 target_preserved=all([
  row.get("proof_mode")=="MATCHED_HIDDEN_TOOL_ECOSYSTEM_TRANSFER",
  "unknown tool discovery" in list(row.get("task_dimensions") or []),
  "schema/authority filtering" in list(row.get("task_dimensions") or []),
  "route selection under incomplete evidence" in list(row.get("task_dimensions") or []),
  "safe probe choice" in list(row.get("task_dimensions") or []),
  "capability-state update" in list(row.get("task_dimensions") or []),
  "later-task transfer without rediscovery" in list(row.get("task_dimensions") or []),
  "Discover candidate tools if needed" in str(behavior.get("required_output_or_action") or ""),
  "fresh unseen tool sets" in str(behavior.get("success_condition") or ""),
  "Unknown/changing tool ecosystem" in str(behavior.get("scope") or ""),
 ])
 contract_exact=set(contract.get("required_properties") or [])==CONTRACT_V3_PROPERTIES

 entries=[
  _row("opaque-expensive",10,"S0",True),
  _row("opaque-cheap",1,"S1",True),
  _row("opaque-negative",0.5,"S1",False),
 ]
 authority=CommonFrozenToolAuthorityV3(entries,epoch=9)
 instance=prove_instance(authority)
 brain=execute_v5(authority,"BRAIN",required_capabilities=["CAP_X"])
 opus=execute_v5(authority,"OPUS55",required_capabilities=["CAP_X"])
 route_equivalent=brain["actions"]==opus["actions"] and brain["final"]==opus["final"]
 global_choice=brain["final"]=={"action":"SELECT","tool_id":"opaque-cheap"}
 discovery_first=(
  any(x.get("action")=="DISCOVER" for x in brain["actions"])
  and next(i for i,x in enumerate(brain["actions"]) if x.get("action") in {"PROBE","SELECT","ESCALATE"})
      >= len(authority.source_ids())
 )

 # Hidden truth is not encoded into source or authority public commitments.
 yes=CommonFrozenToolAuthorityV3([_row("same",1,"S0",True)],epoch=4)
 no=CommonFrozenToolAuthorityV3([_row("same",1,"S0",False)],epoch=4)
 hidden_noninterference=all([
  yes.authority_digest_sha256()==no.authority_digest_sha256(),
  yes.source_descriptors("BRAIN",episode_epoch=4)==no.source_descriptors("BRAIN",episode_epoch=4),
 ])

 # Contract V3's observability premise is load-bearing. The interface does not
 # claim completeness when a decision-relevant cheaper route is unobservable.
 blocked=CommonFrozenToolAuthorityV3([
  _row("unknown-cheap",1,"S0",True,safe=False),
  _row("known-expensive",2,"S0",True,safe=True),
 ])
 blocked_out=execute_v5(blocked,"BRAIN",required_capabilities=["CAP_X"])
 observability_fail_closed=(
  blocked_out["final"].get("action")=="ESCALATE"
  and blocked_out["final"].get("reason")=="CHEAPER_ADMISSIBLE_ROUTE_UNRESOLVED_NO_SAFE_PROBE"
 )

 old_epoch=authority.epoch
 authority.replace_authority(entries)
 stale_blocked=False
 try:
  authority.discover("BRAIN","S0","CAP_X",episode_epoch=old_epoch)
 except AuthorityError as exc:
  stale_blocked="EPOCH_CHANGED_RESTART_EPISODE" in str(exc)

 facts={
  "FROZEN_TARGET_PRESERVED":target_preserved,
  "CONTRACT_V3_PROPERTY_SET_EXACT":contract_exact,
  "COMMON_MATCHED_AUTHORITY_INSTANCE_VALID":instance.get("status","").startswith("PASS__"),
  "BRAIN_OPUS_PUBLIC_INTERFACE_IDENTICAL":instance.get("brain_opus_views_identical") is True,
  "SOURCE_UNION_EXACT_AUTHORITY":instance.get("source_union_exact_authority") is True,
  "HIDDEN_CAPABILITY_TRUTH_NOT_DISCLOSED":instance.get("hidden_capability_truth_not_disclosed") is True,
  "HIDDEN_TRUTH_PUBLIC_COMMITMENT_NONINTERFERENCE":hidden_noninterference,
  "CONVERGED_V5_ROUTE_EQUIVALENT_ACROSS_MATCHED_AUTHORITY":route_equivalent,
  "CONVERGED_V5_DISCOVERY_FIRST":discovery_first,
  "CONVERGED_V5_GLOBAL_LEAST_COST_ON_FULLY_OBSERVABLE_INSTANCE":global_choice,
  "UNOBSERVABLE_CHEAPER_ROUTE_FAILS_CLOSED":observability_fail_closed,
  "AUTHORITY_REPLACEMENT_INVALIDATES_STALE_EPISODE":stale_blocked,
 }
 missing=sorted(k for k,v in facts.items() if v is not True)
 if missing:
  return _fail("COMMON_AUTHORITY_V5_V3_PREMISE_MISSING",facts=facts,missing=missing)

 return {
  "schema":SCHEMA,
  "status":"PASS__COMMON_MATCHED_AUTHORITY_V5_CONTRACT_V3_SCOPE_INTERFACE_CANDIDATE__INDEPENDENT_PUBLIC_RUNNER_REQUIRED__ZERO_CREDIT",
  "facts":facts,"missing":[],
  "target_family":"TOOL_DISCOVERY_SELECTION_AND_LEARNING",
  "target_predicate":"TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR",
  "basis_kind":"UNIVERSAL_CONSTRUCTION_OVER_ARBITRARY_FINITE_MATCHED_AUTHORITY",
  "quantified_domain":"ANY_FINITE_FROZEN_COMMON_BRAIN_OPUS_TOOL_AUTHORITY_R",
  "observability_condition":"EVERY_DECISION_RELEVANT_REQUIRED_CAPABILITY_OF_AN_UNELIMINATED_ADMISSIBLE_ROUTE_IS_CURRENTLY_EVIDENCED_OR_EXPLICITLY_SAFE_PROBE_DECIDABLE",
  "scope_relation_candidate":"FOR_EACH_ADMISSIBLE_FROZEN_MATCHED_AUTHORITY_R__BOTH_ROUTES_RECEIVE_THE_SAME_CONTENT_BOUND_COMPLETE_DISCOVERY_INTERFACE__V5_EXHAUSTS_DISCOVERY_BEFORE_ROUTE_COMMITMENT",
  "not_claimed_when_observability_missing":"GLOBAL_LEAST_COST_OR_NO_ROUTE_PROOF",
  "residual_after_independent_verification":"SEPARATE_FAIL_CLOSED_ACCEPTANCE_REDUCTION_MUST_ESTABLISH_THE_MATCHED_NONINFERIORITY_METRICS_AND_FAMILY_CREDIT_FROM_ADMISSIBLE_EVIDENCE",
  "terminal_results_replayed":0,"new_reality_units_consumed":0,"incremental_spend_usd":0,
  "capability_credit_delta":0,"family_credit_delta":0,
  "execution_authority":False,"promotion_authority":False,
 }

def _fail(reason:str,**kw:Any)->dict[str,Any]:
 out={
  "schema":SCHEMA,"status":"FAIL_CLOSED__"+reason,
  "terminal_results_replayed":0,"new_reality_units_consumed":0,"incremental_spend_usd":0,
  "capability_credit_delta":0,"family_credit_delta":0,
  "execution_authority":False,"promotion_authority":False,
 }
 out.update(kw); return out

if __name__=="__main__":
 print(json.dumps(evaluate(),indent=2,sort_keys=True))
