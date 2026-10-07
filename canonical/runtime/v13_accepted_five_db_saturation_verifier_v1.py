from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BUNDLE="canonical/governance/V13_ACCEPTED_FIVE_DB_SATURATION_20261007_V1.json"
EXPECTED={
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V13.json":"0d18488b51a222e5da414329ccd9d33cbc1fc31c",
 "canonical/governance/DIRECT_END_TO_END_SELECTED_CELL_CERTIFICATE_THEOREM_20261007_V1.json":"ecb52ca25fa14a60b7c34206fea25d8d3cfdcf0d",
 "canonical/verification/ACCEPTED_THREE_OWNERSHIP_PROMOTION_PROOF_20261003_V1.json":"4711fb5eed330990edea369725de6eaedfd3bc70",
 "canonical/governance/CURRENT_ACCEPTED_FIVE_D_REDUCTION_20261007_V1.json":"a1d2dac1ab98462c3505543f8047442a60017d19",
 "canonical/verification/DELEGATION_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"d04f2a8c5594d261158835db1cae3822411b6b23",
 "canonical/verification/DELEGATION_V4_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"955ac8f4bd0db2527bfbb465fc8252df6d916156",
 "canonical/verification/RECOVERY_OPUS55_ZERO_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json":"981c8ac9b66ee7fccf5b531525849e29df9be483",
 "canonical/verification/P1_UNIVERSAL_SCOPE_RESTORATION_V9_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"2c6bb594d353e4c6a169821da5f84a91be212ca7",
 "canonical/verification/TOOL_DISCOVERY_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"913d171b3c855000d322e183b142b3200eeaf0a9",
 "canonical/verification/TOOL_DISCOVERY_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"f44e2378cf00f86a59159cb9d8edb35f0a7c27f4",
 "canonical/capabilities/obsolescence/EXACT_SYMBOLIC_COMPUTATION_V1_ADJUDICATION.json":"a691d49ef377fa216bbbeff70183112d65445463",
 "canonical/governance/EXACT_SYMBOLIC_SELECTED_LEAF_ROUTE_20261007_V1.json":"ba48f9024787e25308f9ad1dd74a83064f467865",
 "canonical/capabilities/opus55/OPUS55_LONG_HORIZON_MEMORY_AND_CONTINUITY_V1.json":"2d912cf8df64bd806fffb6a1070d95644d005470",
 "canonical/governance/CONTINUITY_CREDITED_REBIND_20261007_V1.json":"839af46fd8ef214251b44bd1398fa2d1543f00c5",
 "canonical/runtime/delegation_whole_scope_candidate_v2.py":"f1a93ee66d90093de61dc17c6ebf2e24073df522",
 "canonical/runtime/trajectory_failure_typed_ir_candidate_v7.py":"28940387bd6c11671035ad9201e37bba13fd9bc9",
 "canonical/runtime/tool_discovery_information_safe_candidate.py":"64c02edd568d95ec5ed54b7b8122183ce5b82e17",
 "canonical/obsolescence/run_exact_symbolic_v1.py":"8f6f04fee00664b26ddf1a45a65698399c7ca6c3",
 "canonical/runtime/same_identity_supervisor_credited_v1.py":"47c461f502e840def0c38728e1bfd7c6401cb804",
}
def blob(data:bytes)->str:
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def load(path:str):
 return json.loads((ROOT/path).read_text())
def verify():
 errors=[]
 for p,w in EXPECTED.items():
  q=ROOT/p
  if not q.is_file():
   errors.append("SOURCE_MISSING:"+p); continue
  if blob(q.read_bytes())!=w: errors.append("SOURCE_DRIFT:"+p)

 theorem=load("canonical/governance/DIRECT_END_TO_END_SELECTED_CELL_CERTIFICATE_THEOREM_20261007_V1.json")
 suff=((theorem.get("theorem") or {}).get("cell_sufficiency") or "")
 if "E2E_OR_PC" not in suff: errors.append("DIRECT_E2E_RULE_NOT_BOUND")

 own=load("canonical/verification/ACCEPTED_THREE_OWNERSHIP_PROMOTION_PROOF_20261003_V1.json")
 expected_routes={
  "SUBAGENT_DELEGATION_AND_COORDINATION":("canonical/runtime/delegation_whole_scope_candidate_v2.py","f1a93ee66d90093de61dc17c6ebf2e24073df522"),
  "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY":("canonical/runtime/trajectory_failure_typed_ir_candidate_v7.py","28940387bd6c11671035ad9201e37bba13fd9bc9"),
  "TOOL_DISCOVERY_SELECTION_AND_LEARNING":("canonical/runtime/tool_discovery_information_safe_candidate.py","64c02edd568d95ec5ed54b7b8122183ce5b82e17"),
 }
 rows={x.get("family"):x for x in own.get("families",[])}
 for fam,(p,s) in expected_routes.items():
  x=rows.get(fam) or {}
  art=x.get("operative_artifact") or {}
  if not (x.get("acceptance")=="PASS" and x.get("exact_receipt_binding") is True and
          x.get("promotion")=="VERIFIED_OWNED_EQUAL_OR_BETTER" and
          x.get("external_target_capability_provider") is False and
          art.get("path")==p and art.get("git_blob_sha")==s):
   errors.append("OWNERSHIP_BINDING_INVALID:"+fam)

 d=load("canonical/verification/DELEGATION_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")
 dv=d.get("verified_result") or {}
 if not (dv.get("closure_mode")=="ABSOLUTE_DOMINANCE" and
         dv.get("witness_reason")=="THEORETICAL_CEILING_DOMINANCE" and
         dv.get("scope_completeness_basis")=="UNIVERSAL_FORMAL_SCOPE_PROOF"):
  errors.append("DELEGATION_E2E_INVALID")
 ds=load("canonical/verification/DELEGATION_V4_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")
 if not ("UNIVERSAL_SCOPE_PROVED_TRUE" in (ds.get("verified") or []) and
         "NO_EMPIRICAL_GENERALIZATION" in (ds.get("verified") or [])):
  errors.append("DELEGATION_SCOPE_INVALID")

 r=load("canonical/verification/RECOVERY_OPUS55_ZERO_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json")
 rv=r.get("verified") or {}; bounds=rv.get("universal_achieved_bounds") or {}
 if not (rv.get("scope_complete") is True and rv.get("objective_ceiling_or_floor") is True and
         bounds.get("causal_localization")==1 and bounds.get("terminal_recovery")==1 and
         bounds.get("critical_fail_closed_misses")==0):
  errors.append("RECOVERY_E2E_INVALID")

 t=load("canonical/verification/TOOL_DISCOVERY_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")
 tv=t.get("verified") or {}
 if not (tv.get("scope_complete") is True and tv.get("objective_ceiling") is True and
         tv.get("brain_value")==1 and tv.get("objective_ceiling_value")==1 and
         tv.get("proof_kind")=="ABSOLUTE_CEILING_WITH_UNIVERSAL_FORMAL_SCOPE_COMPLETENESS"):
  errors.append("TOOL_DISCOVERY_E2E_INVALID")
 ts=load("canonical/verification/TOOL_DISCOVERY_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")
 if (ts.get("verified") or {}).get("universal_scope_proved") is not True:
  errors.append("TOOL_DISCOVERY_SCOPE_INVALID")

 e=load("canonical/capabilities/obsolescence/EXACT_SYMBOLIC_COMPUTATION_V1_ADJUDICATION.json")
 if not (e.get("scope")=="Bounded exact symbolic computation represented by frozen suite OBS-EXACT-SYMBOLIC-001 only." and
         (e.get("producer_execution") or {}).get("pass_count")==12 and
         (e.get("producer_execution") or {}).get("fail_count")==0 and
         (e.get("independent_adjudication") or {}).get("all_pass") is True and
         (e.get("frontier_bar") or {}).get("basis")=="THEORETICAL_CEILING" and
         (e.get("decision") or {}).get("obsolescence_status")=="OBSOLETE_VERIFIED"):
  errors.append("EXACT_SYMBOLIC_E2E_INVALID")
 er=load("canonical/governance/EXACT_SYMBOLIC_SELECTED_LEAF_ROUTE_20261007_V1.json")
 if not ((er.get("selected_route") or {}).get("runner_git_blob_sha")=="8f6f04fee00664b26ddf1a45a65698399c7ca6c3" and
         (er.get("selected_route") or {}).get("selected_entry")=="run_task"):
  errors.append("EXACT_SYMBOLIC_ROUTE_INVALID")

 c=load("canonical/capabilities/opus55/OPUS55_LONG_HORIZON_MEMORY_AND_CONTINUITY_V1.json")
 if not (c.get("status")=="VERIFIED_OWNED_EQUAL_OR_BETTER" and
         (c.get("brain_owned_route") or {}).get("external_hidden_capability_provider_required") is False and
         (c.get("frontier_bar") or {}).get("basis")=="OBJECTIVE_BEHAVIORAL_CEILING" and
         (c.get("decision") or {}).get("parent_family_closed_for_claim_scope") is True):
  errors.append("CONTINUITY_E2E_INVALID")
 cr=load("canonical/governance/CONTINUITY_CREDITED_REBIND_20261007_V1.json")
 if not (cr.get("accepted_blob")=="47c461f502e840def0c38728e1bfd7c6401cb804" and
         cr.get("credited_path_blob")=="47c461f502e840def0c38728e1bfd7c6401cb804"):
  errors.append("CONTINUITY_ROUTE_INVALID")

 dr=load("canonical/governance/CURRENT_ACCEPTED_FIVE_D_REDUCTION_20261007_V1.json")
 if (dr.get("current_D_effect_frontier") or {}).get("current_accepted_family_effect_mediator_residual_count") != 0:
  errors.append("CURRENT_ACCEPTED_D_RESIDUAL_NONZERO")

 b=load(BUNDLE)
 regions=b.get("regions") or []
 if len(regions)!=5 or any(x.get("add_to_D_B") is not True for x in regions):
  errors.append("REGION_SET_INVALID")
 if (b.get("v13_effect") or {}).get("abc_global_state")!="OPEN":
  errors.append("ABC_FALSELY_CLOSED")
 if (b.get("v13_effect") or {}).get("D_finality_state")!="OPEN":
  errors.append("D_FALSELY_CLOSED")
 if b.get("hard_nonclaims") is None or "NO_TERMINAL_CREDIT" not in b.get("hard_nonclaims"):
  errors.append("TERMINAL_OVERCLAIM_GUARD_MISSING")
 return {
  "schema":"PROJECT_BRAIN_V13_ACCEPTED_FIVE_DB_SATURATION_VERIFY_V1",
  "status":"PASS__FIVE_ACCEPTED_CLAIM_SCOPES_SOUNDLY_ADDED_TO_D_B__ZERO_GLOBAL_CREDIT" if not errors else "FAIL_CLOSED",
  "pass":not errors,
  "errors":errors,
  "db_region_count":5 if not errors else 0,
  "abc_closed":False,
  "d_finality_closed":False,
  "terminal":False,
  "terminal_credit_delta":0,
 }
if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
