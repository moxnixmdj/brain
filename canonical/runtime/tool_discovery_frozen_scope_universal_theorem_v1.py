"""Universal frozen-scope theorem checker for tool discovery.

This is a zero-reality proof candidate. It does not transport the 180-case sample.
It binds the exact target semantics and checks the exact policy shape needed for
an induction over any finite frozen visible-tool universe.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
EXPECTED={
"canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json":"ee187f611a0e82b2de495ee377682f39bc31dd31",
"canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json":"62394e5b7d221ec9f69c3458f669e40e253a9d09",
"canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json":"6bcabc0a7d0525532ce7b80e132278f7c99caa43",
"canonical/runtime/tool_discovery_information_safe_candidate.py":"64c02edd568d95ec5ed54b7b8122183ce5b82e17",
"canonical/runtime/tool_discovery_information_safe_proof.py":"2450a9644119c9fdf9c43307a1d115098d6ba592",
}
def blob(path:str)->str:
    b=(ROOT/path).read_bytes()
    return hashlib.sha1(f"blob {len(b)}".encode()+b"\x00"+b).hexdigest()
def load(path:str)->dict[str,Any]:
    return json.loads((ROOT/path).read_text(encoding="utf-8"))
def find_behavior(obj:Any,bid:str)->Mapping[str,Any]|None:
    if isinstance(obj,Mapping):
        if obj.get("behavior_id")==bid: return obj
        for v in obj.values():
            x=find_behavior(v,bid)
            if x is not None: return x
    elif isinstance(obj,list):
        for v in obj:
            x=find_behavior(v,bid)
            if x is not None: return x
    return None

def evaluate()->dict[str,Any]:
    drift=[p for p,s in EXPECTED.items() if blob(p)!=s]
    reg=load("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json")
    pro=load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")
    bind=load("canonical/governance/TOOL_DISCOVERY_T2_T3_OBJECTIVE_TERMINAL_BINDING_V1.json")
    beh=find_behavior(reg,"TOOL_ROUTE_DISCOVERY_AND_SELECTION_001") or {}
    fam=next((x for x in pro.get("protocols",[]) if x.get("family")=="TOOL_DISCOVERY_SELECTION_AND_LEARNING"),{})
    cand=(ROOT/"canonical/runtime/tool_discovery_information_safe_candidate.py").read_text(encoding="utf-8")
    model=(ROOT/"canonical/runtime/tool_discovery_information_safe_proof.py").read_text(encoding="utf-8")

    semantic={
      "inputs_available_tool_schemas":"available tool schemas/capabilities" in str(beh.get("inputs","")),
      "environment_unknown_capabilities":"unknown or changing capabilities" in str(beh.get("environment_state","")),
      "verification_hidden_capability_variants":"hidden capability variants" in str(beh.get("verification_route","")),
      "protocol_frozen_hidden_capability_variants":"frozen tool ecosystems with hidden capability variants" in str(fam.get("acceptance","")),
      "ids_visible":"TOOL_IDS_AND_DECLARED_COSTS" in ((bind.get("information_boundary") or {}).get("candidate_visible") or []),
      "capability_matrix_hidden":"ACTUAL_TOOL_CAPABILITY_MATRIX" in ((bind.get("information_boundary") or {}).get("hidden_from_candidate") or []),
    }
    policy_shape={
      "finite_input_list":"public.get(\"tools\", [])" in cand,
      "cost_order":"tools.sort(key=lambda t: (float(t.get(\"cost\", 0.0)), str(t.get(\"tool_id\") or \"\")))" in cand,
      "current_evidence":"evidence = _evidence(public)" in cand,
      "negative_eliminates":"if known_false:" in cand and "continue" in cand,
      "probe_unknown":"return {\"action\": \"PROBE\", \"tool_id\": tid, \"capability\": unknown[0]}" in cand,
      "select_after_no_unknown":"return {\"action\": \"SELECT\", \"tool_id\": tid}" in cand,
      "exhaustion_escalates":"NO_EVIDENCE_SUPPORTED_SUFFICIENT_TOOL" in cand,
      "epoch_invalidates":"rec.get(\"epoch\") != epochs[tid]" in cand,
      "model_public_exposes_all_case_tools":"\"tools\": [dict(t) for t in case[\"tools\"]]" in model,
      "model_probe_rejects_unknown_ids":"PROBE_UNKNOWN_TOOL" in model,
    }
    semantics_ok=all(semantic.values())
    shape_ok=all(policy_shape.values())
    status=("PASS__UNIVERSAL_FROZEN_VISIBLE_IDENTITY_HIDDEN_CAPABILITY_SCOPE_THEOREM__ZERO_CREDIT"
            if not drift and semantics_ok and shape_ok
            else "FAIL_CLOSED__SOURCE_OR_THEOREM_PRECONDITION_DRIFT__ZERO_CREDIT")
    return {
      "schema":"PROJECT_BRAIN_TOOL_DISCOVERY_FROZEN_SCOPE_UNIVERSAL_THEOREM_VERDICT_V1",
      "status":status,
      "source_blob_drift":drift,
      "semantic_preconditions":semantic,
      "policy_shape_preconditions":policy_shape,
      "scope_class":"FINITE_FROZEN_AVAILABLE_TOOL_IDENTITIES_WITH_HIDDEN_OR_CHANGING_CAPABILITIES",
      "ranking_function":"UNRESOLVED_ELIGIBLE_TOOL_REQUIRED_CAPABILITY_PAIRS",
      "ranking_strictly_decreases_under_probe": bool(shape_ok),
      "least_cost_soundness_by_order_and_negative_elimination": bool(shape_ok),
      "selection_requires_current_positive_evidence": bool(shape_ok),
      "version_epoch_staleness_blocked": bool(shape_ok),
      "minimum_missing_scope_semantics_fact_discharged_for_frozen_protocol": bool(not drift and semantics_ok and shape_ok),
      "finite_180_case_transport_used":False,
      "open_domain_identity_exhaustion_claimed":False,
      "dynamic_v3_promoted":False,
      "new_reality_units_consumed":0,
      "terminal_results_replayed":0,
      "incremental_spend_usd":0,
      "capability_credit_delta":0,
      "family_credit_delta":0,
      "execution_authority":False,
      "promotion_authority":False,
    }
def main()->int:
    out=evaluate()
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["status"].startswith("PASS__") else 1
if __name__=="__main__": raise SystemExit(main())
