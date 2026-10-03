"""Fail-closed V14 scheduling reconciliation after Tool Discovery acceptance promotion."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any, Mapping
from canonical.runtime.current_terminal_scheduling_world_v2 import evaluate as compile_world

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_TERMINAL_SCHEDULING_V14_POST_TOOL_DISCOVERY_VERIFIER_V1"
CANDIDATE="canonical/governance/TERMINAL_SCHEDULING_V14_POST_TOOL_DISCOVERY_CANDIDATE_V1.json"
PATHS={
 "registry":"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json",
 "evidence":"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json",
 "frontier":"canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json",
 "hypergraph":"canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json",
 "scheduling":"canonical/governance/TERMINAL_SCHEDULING_ACTIVATION_V6.json",
 "authority":"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json",
 "promotion":"canonical/governance/TOOL_DISCOVERY_ACCEPTANCE_PROMOTION_ACTIVATION_V1.json",
 "promotion_receipt":"canonical/verification/TOOL_DISCOVERY_ACCEPTANCE_PROMOTION_INTEGRATOR_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
}
TARGET="TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"

def load(rel:str)->dict[str,Any]:
    x=json.loads((ROOT/rel).read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise ValueError(rel+":NOT_OBJECT")
    return x

def blob(rel:str)->str:
    raw=(ROOT/rel).read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def evaluate_documents(candidate:Mapping[str,Any], registry:Mapping[str,Any], evidence:Mapping[str,Any],
                       frontier:Mapping[str,Any], hypergraph:Mapping[str,Any], scheduling:Mapping[str,Any],
                       authority:Mapping[str,Any], promotion:Mapping[str,Any], receipt:Mapping[str,Any])->dict[str,Any]:
    errors=[]
    def req(cond:bool, code:str):
        if not cond: errors.append(code)

    world=compile_world(registry,evidence,frontier,hypergraph,scheduling,authority)
    req(world.get("pass") is True,"LIVE_COMPILER_NOT_PASS")
    exp=candidate.get("expected_live_world") or {}
    req(world.get("registry_predicate_count")==exp.get("registry_predicates"),"REGISTRY_COUNT")
    req(world.get("proved_predicate_count")==exp.get("proved_predicates"),"PROVED_COUNT")
    req(world.get("refuted_predicate_count")==exp.get("refuted_predicates"),"REFUTED_COUNT")
    req(world.get("unresolved_predicate_count")==exp.get("unresolved_predicates"),"UNRESOLVED_COUNT")
    req(world.get("live_certificate_count")==exp.get("live_certificates"),"LIVE_CERTIFICATE_COUNT")
    req(world.get("live_action_count")==exp.get("live_actions"),"LIVE_ACTION_COUNT")
    req(world.get("live_action_coverage_count")==exp.get("live_action_coverage"),"LIVE_ACTION_COVERAGE")
    req(world.get("uncovered_predicates")==exp.get("uncovered_predicates"),"UNCOVERED_PREDICATES")
    req((authority.get("truth") or {}).get("opus55_acceptance")==exp.get("opus55_acceptance"),"ACCEPTANCE_WORLD")
    req(TARGET in set(world.get("proved_predicates") or []),"TOOL_TARGET_NOT_PROVED")
    req(TARGET not in set(world.get("unresolved_predicates") or []),"TOOL_TARGET_STILL_UNRESOLVED")
    live_targets={p for a in world.get("live_actions",[]) for p in a.get("target_predicates",[])}
    req(TARGET not in live_targets,"TOOL_TARGET_STILL_LIVE_ACTION")

    stale=candidate.get("expected_stale_source_filter") or {}
    req(len(world.get("removed_terminal_certificate_targets") or [])==stale.get("removed_terminal_certificate_target_count"),"REMOVED_CERT_COUNT")
    req(len(world.get("removed_terminal_action_targets") or [])==stale.get("removed_terminal_action_target_count"),"REMOVED_ACTION_COUNT")
    removed={x.get("predicate_id") for x in (world.get("removed_terminal_certificate_targets") or [])}
    removed|={x.get("predicate_id") for x in (world.get("removed_terminal_action_targets") or [])}
    for pid in stale.get("mandatory_removed_predicates") or []:
        req(pid in removed,"TERMINAL_TARGET_NOT_REMOVED:"+str(pid))
    req(world.get("source_scheduling_world_stale") is True,"STALE_SOURCE_NOT_DETECTED")

    req(promotion.get("status","").startswith("ACTIVE__CANONICAL_ACCEPTANCE_PROMOTED__5_OF_19__12_OF_38"),"PROMOTION_NOT_ACTIVE")
    pr=receipt.get("public_runner") or {}
    vr=receipt.get("verified_result") or {}
    req(pr.get("conclusion")=="success","PROMOTION_RECEIPT_NOT_SUCCESS")
    req(vr.get("tool_discovery_only_delta") is True,"PROMOTION_NOT_TOOL_ONLY")
    req(vr.get("ownership_credit_delta")==0,"PROMOTION_OWNERSHIP_OVERCLAIM")

    req(world.get("execution_authority") is False,"WORLD_EXECUTION_AUTHORITY")
    req(world.get("promotion_authority") is False,"WORLD_PROMOTION_AUTHORITY")
    req(world.get("fresh_reality_authority") is False,"WORLD_FRESH_REALITY_AUTHORITY")
    ok=not errors
    return {
      "schema":SCHEMA,
      "status":"PASS__V14_LIVE_26_PREDICATE_WORLD__TOOL_DISCOVERY_TERMINAL_TARGET_REMOVED__ZERO_CREDIT" if ok else "FAIL_CLOSED",
      "pass":ok,"errors":sorted(set(errors)),
      "live_world":world if ok else None,
      "registry_predicates":38,
      "proved_predicates":12 if ok else None,
      "unresolved_predicates":26 if ok else None,
      "live_certificates":15 if ok else None,
      "live_actions":20 if ok else None,
      "live_action_coverage":26 if ok else None,
      "uncovered_predicates":[] if ok else None,
      "tool_learning_success_route_noninferior":"PROVED" if ok else "UNKNOWN",
      "new_reality_units_consumed":0,"incremental_spend_usd":0,
      "capability_credit_delta":0,"family_credit_delta":0,"ownership_credit_delta":0,
      "execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False,
    }

def verify_repository()->dict[str,Any]:
    candidate=load(CANDIDATE)
    errors=[]
    for rel,want in (candidate.get("exact_inputs") or {}).items():
        got=blob(rel)
        if got!=want: errors.append("BLOB_DRIFT:"+rel+":"+got+":"+str(want))
    if errors:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"errors":errors,
                "execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False}
    return evaluate_documents(candidate,load(PATHS["registry"]),load(PATHS["evidence"]),load(PATHS["frontier"]),
                              load(PATHS["hypergraph"]),load(PATHS["scheduling"]),load(PATHS["authority"]),
                              load(PATHS["promotion"]),load(PATHS["promotion_receipt"]))

if __name__=="__main__":
    print(json.dumps(verify_repository(),indent=2,sort_keys=True))
