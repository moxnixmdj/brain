"""Receipt-driven acceptance reduction for Tool Discovery V1.

Precompiled before the independent scope receipt exists. It fails closed unless
that receipt binds Brain PR 1133 exact scope-certificate bytes and reports a
successful universal formal-scope proof. Only then is the historical 180/180
absolute-ceiling witness upgraded with scope completeness and composed with the
already accepted Delegation evidence. This module never promotes canonical state.
"""
from __future__ import annotations
from copy import deepcopy
from typing import Any,Mapping

from canonical.runtime.acceptance_proof_transmuter_v1 import evaluate as transmute

SCHEMA="PROJECT_BRAIN_TOOL_DISCOVERY_ACCEPTANCE_REDUCTION_V1"
EXPECTED_SCOPE_BLOBS={
 "canonical/runtime/tool_discovery_universal_scope_certificate_v1.py":"e8806284397876734a9a51c07fe83c7da8b30601",
 "canonical/tests/test_tool_discovery_universal_scope_certificate_v1.py":"eb790708222f84959207e6309c0ffc3cb6b2217f",
 "canonical/governance/TOOL_DISCOVERY_UNIVERSAL_SCOPE_CERTIFICATE_V1.json":"f6e3ed4f08f193576db2ce9dc62a0c68b3f00894",
}
BASELINE_CLOSED={
 "EXACT_SYMBOLIC_COMPUTATION",
 "LONG_HORIZON_MEMORY_AND_CONTINUITY",
 "SUBAGENT_DELEGATION_AND_COORDINATION",
}
TARGET="TOOL_DISCOVERY_SELECTION_AND_LEARNING"


def _valid_scope_receipt(r:Mapping[str,Any])->tuple[bool,list[str]]:
 e=[]
 if r.get("source_brain_pr")!=1133:e.append("WRONG_SOURCE_BRAIN_PR")
 if r.get("target_predicate")!="TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR":e.append("WRONG_TARGET_PREDICATE")
 if r.get("target_proof_atom")!="INDEPENDENT_EXACT_COMPLETE_TARGET_CASE_UNIVERSE_OR_EXHAUSTIVE_FINITE_SUPERSET_OR_UNIVERSAL_FORMAL_SCOPE_PROOF_FOR_TOOL_DISCOVERY_PROTOCOL":e.append("WRONG_TARGET_PROOF_ATOM")
 if not str(r.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):e.append("SCOPE_STATUS_NOT_INDEPENDENT_PASS")
 pr=r.get("public_runner")
 if not isinstance(pr,Mapping) or pr.get("conclusion")!="success":e.append("PUBLIC_RUNNER_NOT_SUCCESS")
 result=r.get("result")
 if not isinstance(result,Mapping) or result.get("universal_scope_proved") is not True:e.append("UNIVERSAL_SCOPE_NOT_PROVED")
 if not isinstance(result,Mapping) or result.get("scope_atom_satisfied_candidate") is not True:e.append("SCOPE_ATOM_NOT_SATISFIED")
 if not isinstance(result,Mapping) or result.get("basis_kind")!="UNIVERSAL_FORMAL_SCOPE_PROOF":e.append("WRONG_SCOPE_BASIS")
 blobs=r.get("exact_brain_blobs")
 if not isinstance(blobs,Mapping):e.append("EXACT_BLOBS_MISSING")
 else:
  for p,w in EXPECTED_SCOPE_BLOBS.items():
   if blobs.get(p)!=w:e.append("BLOB_MISMATCH:"+p)
 for k in ("terminal_results_replayed","new_reality_units_consumed","incremental_spend_usd","capability_credit_delta","family_credit_delta"):
  if r.get(k)!=0:e.append("NONZERO_"+k.upper())
 if r.get("execution_authority") is not False:e.append("SCOPE_RECEIPT_EXECUTION_AUTHORITY")
 if r.get("promotion_authority") is not False:e.append("SCOPE_RECEIPT_PROMOTION_AUTHORITY")
 return not e,sorted(set(e))


def evaluate(
 scope_receipt:Mapping[str,Any],
 protocols:Mapping[str,Any],
 tool_witness:Mapping[str,Any],
 delegation_acceptance_input:Mapping[str,Any],
)->dict[str,Any]:
 ok,errors=_valid_scope_receipt(scope_receipt)
 if not ok:
  return {"schema":SCHEMA,"status":"FAIL_CLOSED__SCOPE_RECEIPT_INVALID","errors":errors,
   "promotion_eligible":False,"capability_credit_delta":0,"family_credit_delta":0,
   "execution_authority":False,"promotion_authority":False}
 tool=deepcopy(dict(tool_witness))
 tool["scope_completeness"]={
  "verified":True,"independent":True,"basis":"UNIVERSAL_FORMAL_SCOPE_PROOF",
  "all_admissible_target_inputs_proved":True,"formal_completeness":True,
  "receipt":"canonical/verification/TOOL_DISCOVERY_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
 }
 delegation=list(delegation_acceptance_input.get("evidence") or [])
 compiled=transmute(protocols,{"evidence":delegation+[tool]})
 if compiled.get("status")!="PASS":
  return {"schema":SCHEMA,"status":"FAIL_CLOSED__TRANSMUTER_FAILED","errors":compiled.get("errors",[]),
   "compiled":compiled,"promotion_eligible":False,"capability_credit_delta":0,"family_credit_delta":0,
   "execution_authority":False,"promotion_authority":False}
 closed={x["family"] for x in compiled["families"] if x.get("result_status")=="PASS"}
 expected=BASELINE_CLOSED|{TARGET}
 target=next(x for x in compiled["families"] if x["family"]==TARGET)
 delegation_row=next(x for x in compiled["families"] if x["family"]=="SUBAGENT_DELEGATION_AND_COORDINATION")
 exact=(closed==expected and compiled.get("closed_family_count")==4 and compiled.get("open_family_count")==15)
 target_ok=(target.get("result_status")=="PASS" and target.get("closure_mode")=="ABSOLUTE_DOMINANCE"
            and target.get("witness_reason")=="THEORETICAL_CEILING_DOMINANCE")
 preserved=delegation_row.get("result_status")=="PASS"
 passed=exact and target_ok and preserved
 return {
  "schema":SCHEMA,
  "status":"PASS__TOOL_DISCOVERY_ONLY_NEW_FAMILY_CLOSURE_ELIGIBLE__4_OF_19_COMPILED__ZERO_CREDIT_FROM_REDUCER" if passed else "FAIL_CLOSED__UNEXPECTED_ACCEPTANCE_DELTA",
  "errors":[] if passed else ["ACCEPTANCE_DELTA_NOT_EXACT"],
  "compiled":compiled,
  "closed_families":sorted(closed),
  "newly_closed_families":[TARGET] if passed else [],
  "preserved_closed_families":sorted(BASELINE_CLOSED) if passed else [],
  "promotion_eligible":passed,
  "promotion_scope":[TARGET,"TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"] if passed else [],
  "terminal_results_replayed":0,"new_reality_units_consumed":0,"incremental_spend_usd":0,
  "capability_credit_delta":0,"family_credit_delta":0,
  "execution_authority":False,"promotion_authority":False,
 }
