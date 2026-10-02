"""Compile the verified P1 V5 carrier into the smallest truthful terminal residual.

V5 independently verifies first-class SCOPE handling and heterogeneous intervention
rescue mechanics. This compiler deliberately refuses to transport that proof into
the three frozen terminal surfaces without an explicit exact-or-superset scope
relation for each surface.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_P1_V5_SCOPE_TRANSPORT_CUT_V1"
BINDING="canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"
QUARANTINE="canonical/governance/P1_TERMINAL_EXECUTION_SCOPE_MISMATCH_QUARANTINE_V1.json"
V4="canonical/verification/P1_V4_SCOPE_SAFE_RESIDUAL_DISCHARGE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
V5="canonical/verification/P1_TYPED_INTERVENTION_V5_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"

EXPECTED_SURFACES={
 "T0/FRONTIERCODE_V1_1::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
 "T0/CURSORBENCH_4_0::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
 "T2/RECOVERY_SCOPE_COMPOSITION::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
}
EXPECTED_V4={"P1_EXPLICIT_SCOPE_FAILURE_CLASS","P1_HETEROGENEOUS_INTERVENTION_RESCUE"}

def _load(p:str)->dict[str,Any]:
    v=json.loads((ROOT/p).read_text(encoding="utf-8"))
    if not isinstance(v,dict): raise ValueError(p+":NOT_OBJECT")
    return v

def _evaluate(binding:Mapping[str,Any], quarantine:Mapping[str,Any], v4:Mapping[str,Any], v5:Mapping[str,Any])->dict[str,Any]:
    errors=[]
    surfaces=set(binding.get("direct_surface_bindings") or [])
    if surfaces!=EXPECTED_SURFACES: errors.append("DIRECT_SURFACE_SET_DRIFT")
    if "QUARANTIN" not in str(quarantine.get("status") or ""): errors.append("P1_QUARANTINE_NOT_ACTIVE")
    if not str(v4.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS__"):
        errors.append("V4_RESIDUAL_RECEIPT_NOT_INDEPENDENT_PASS")
    if set((v4.get("result") or {}).get("residual_obligations") or [])!=EXPECTED_V4:
        errors.append("V4_RESIDUAL_SET_DRIFT")
    if (v4.get("result") or {}).get("can_clear_p1_scope_quarantine") is not False:
        errors.append("V4_UNEXPECTED_CLEARANCE")
    if not str(v5.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS__"):
        errors.append("V5_NOT_INDEPENDENT_PASS")
    vv=v5.get("verified") or {}
    if vv.get("typed_case_count")!=192: errors.append("V5_TYPED_CASE_COUNT_DRIFT")
    if vv.get("explicit_scope_case_count")!=24: errors.append("V5_SCOPE_CASE_COUNT_DRIFT")
    if vv.get("identifiable_or_interaction_rescue_count")!=144: errors.append("V5_RESCUE_COUNT_DRIFT")
    if vv.get("drop_provenance_mutation_killed") is not True: errors.append("V5_PROVENANCE_MUTATION_NOT_KILLED")
    if vv.get("unfalsifiable_output_injection_killed") is not True: errors.append("V5_UNFALSIFIABLE_MUTATION_NOT_KILLED")
    if vv.get("hidden_intervention_state_candidate_visible") is not False: errors.append("V5_HIDDEN_STATE_LEAK")
    for k in ("capability_credit_delta","family_credit_delta"):
        if v5.get(k)!=0: errors.append("V5_NONZERO_CREDIT:"+k)
    if v5.get("execution_authority") is not False or v5.get("promotion_authority") is not False:
        errors.append("V5_UNEXPECTED_AUTHORITY")
    if errors:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED__SOURCE_DRIFT","errors":sorted(set(errors)),
                "can_clear_p1_scope_quarantine":False,"new_reality_units_consumed":0,
                "capability_credit_delta":0,"family_credit_delta":0,"execution_authority":False,"promotion_authority":False}
    atoms=[
      {"surface":s,"required_proposition":"V5_EXACT_OR_SUPERSET_SCOPE_RELATION_INDEPENDENT_PASS::"+s}
      for s in sorted(EXPECTED_SURFACES)
    ]
    return {
      "schema":SCHEMA,
      "status":"PASS__V5_MECHANISM_RESIDUALS_DISCHARGED_IN_VERIFIED_CARRIER__THREE_DIRECT_SURFACE_SCOPE_TRANSPORT_ATOMS_REMAIN",
      "errors":[],
      "carrier_discharge":{
        "P1_EXPLICIT_SCOPE_FAILURE_CLASS":"VERIFIED_IN_V5_CARRIER_ONLY",
        "P1_HETEROGENEOUS_INTERVENTION_RESCUE":"VERIFIED_IN_V5_CARRIER_ONLY",
        "typed_case_count":192,
        "explicit_scope_case_count":24,
        "identifiable_or_interaction_rescue_count":144
      },
      "transport_atoms":atoms,
      "transport_atom_count":len(atoms),
      "can_clear_p1_scope_quarantine":False,
      "proof_rule":"CARRIER_MECHANISM_PROOF_CANNOT_CROSS_INTO_A_FROZEN_TERMINAL_SURFACE_UNTIL_THAT_SURFACE_HAS_AN_INDEPENDENT_EXACT_OR_SUPERSET_SCOPE_RELATION_TO_V5",
      "next_proof_cut":{
        "first":"SEARCH_IMMUTABLE_FROZEN_SURFACE_BINDINGS_AND_RECEIPTS_FOR_EACH_OF_THE_THREE_TRANSPORT_ATOMS",
        "if_missing":"ACQUIRE_ONLY_THE_MISSING_SURFACE_SCOPE_RELATION_EVIDENCE__DO_NOT_REPLAY_UNRELATED_TERMINAL_CASES",
        "full_terminal_replay_authorized":False
      },
      "new_reality_units_consumed":0,"terminal_results_replayed":0,"incremental_spend_usd":0,
      "capability_credit_delta":0,"family_credit_delta":0,"execution_authority":False,"promotion_authority":False
    }

def evaluate()->dict[str,Any]:
    return _evaluate(_load(BINDING),_load(QUARANTINE),_load(V4),_load(V5))

if __name__=="__main__":
    print(json.dumps(evaluate(),indent=2,sort_keys=True))
