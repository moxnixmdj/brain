"""Recompute zero-reality frontier after verified Tool Discovery acceptance promotion."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_CURRENT_26_ZERO_REALITY_FRONTIER_V1"
PATHS={
 "prior":"canonical/governance/CURRENT_27_ZERO_REALITY_FRONTIER_V2.json",
 "evidence":"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json",
 "registry":"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json",
 "matched":"canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_INPUT_V2.json",
 "promotion":"canonical/governance/TOOL_DISCOVERY_ACCEPTANCE_PROMOTION_ACTIVATION_V1.json",
}
EXPECTED={
 PATHS["prior"]:"bab3876a1c4bd6a065d20d42b320df4b4b3fa519",
 PATHS["evidence"]:"e5888b0f03ddd3a7fbfdfd74d11b4680abc9f0dd",
 PATHS["registry"]:"562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
 PATHS["matched"]:"438e2775b64bee5ed6e792522ab35ebd0d6e1771",
 PATHS["promotion"]:"0b14d28e356e3d730cfb6615dcde4c9f00bafdd4",
}
TOOL_PRED="TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
TOOL_CERT="TOOL_DISCOVERY_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE"
TOOL_REQ="INDEPENDENT_EXACT_COMPLETE_TARGET_CASE_UNIVERSE_OR_EXHAUSTIVE_FINITE_SUPERSET_OR_UNIVERSAL_FORMAL_SCOPE_PROOF_FOR_TOOL_DISCOVERY_PROTOCOL"
DIRECT={"FINANCE_UNCOVERED_SCOPE_AUDIT","UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"}
MATCHED_AGG={"MATCHED_BRAIN_WITNESS_SCOPE_RELATIONS_INDEPENDENT_PASS","MATCHED_BRAIN_WITNESS_TARGET_ATOM_METRIC_BINDINGS_INDEPENDENT_PASS"}

def _blob(p):
 d=(ROOT/p).read_bytes()
 return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

def _load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))

def evaluate():
 drift={p:{"expected":h,"actual":_blob(p)} for p,h in EXPECTED.items() if _blob(p)!=h}
 if drift:
  return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED__SOURCE_BLOB_DRIFT","errors":["SOURCE_BLOB_DRIFT"],"drift":drift,
          "execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False}
 prior,evidence,registry,matched,promotion=(_load(PATHS[k]) for k in ("prior","evidence","registry","matched","promotion"))
 errors=[]
 if promotion.get("after")!={"accepted_families":5,"open_families":14,"proved_atomic":12,"unresolved_atomic":26}:
  errors.append("PROMOTION_STATE_NOT_5_19_12_38")
 claims=evidence.get("claims") or []
 proved={str(x.get("predicate_id")) for x in claims if x.get("state")=="PROVED"}
 ids={str(x.get("id")) for x in (registry.get("predicates") or [])}
 unresolved=ids-proved
 if (len(ids),len(proved),len(unresolved))!=(38,12,26): errors.append("LIVE_WORLD_NOT_38_12_26")
 tool=[x for x in claims if x.get("predicate_id")==TOOL_PRED]
 if len(tool)!=1 or tool[0].get("state")!="PROVED" or tool[0].get("scope_complete") is not True:
  errors.append("TOOL_DISCOVERY_NOT_SCOPE_COMPLETE_PROVED")
 active_certs=list(prior.get("active_nondominated_certificate_ids") or [])
 active_reqs=set(prior.get("active_required_propositions") or [])
 if TOOL_CERT not in active_certs: errors.append("TOOL_CERT_NOT_IN_PRIOR_ACTIVE_SET")
 if TOOL_REQ not in active_reqs: errors.append("TOOL_REQ_NOT_IN_PRIOR_ACTIVE_SET")
 active_certs=[x for x in active_certs if x!=TOOL_CERT]
 active_reqs.discard(TOOL_REQ)
 if len(active_certs)!=13: errors.append("ACTIVE_CERT_COUNT_NOT_13")
 if len(active_reqs)!=16: errors.append("ACTIVE_REQUIREMENT_COUNT_NOT_16")
 expected_matched=matched.get("expected") or {}
 child_count=expected_matched.get("primitive_residual_fact_count")
 if child_count!=16 or expected_matched.get("shared_residual_group_count")!=0:
  errors.append("MATCHED_RESIDUAL_NOT_16_PRIMITIVE_ZERO_SHARED")
 if not MATCHED_AGG.issubset(active_reqs): errors.append("MATCHED_AGGREGATES_MISSING")
 primitive=len(active_reqs-MATCHED_AGG)+int(child_count or 0)
 if primitive!=30: errors.append("PRIMITIVE_WORK_UNITS_NOT_30")
 zero_covered=unresolved-DIRECT
 if len(zero_covered)!=24: errors.append("ZERO_REALITY_COVERED_NOT_24")
 if DIRECT-unresolved: errors.append("DIRECT_REALITY_TARGET_ALREADY_PROVED_OR_MISSING")
 ok=not errors
 return {
  "schema":SCHEMA,
  "pass":ok,
  "status":"PASS__POST_TOOL_DISCOVERY_26_UNRESOLVED__16_ZERO_REALITY_REQUIREMENTS__13_CERTIFICATES__30_PRIMITIVE_WORK_UNITS__2_DIRECT_REALITY_BLOCKED" if ok else "FAIL_CLOSED",
  "errors":sorted(set(errors)),
  "live_world":{"registry_predicates":38,"proved_predicates":12,"unresolved_predicates":26,"opus55_acceptance":"5/19_PASS__14/19_OPEN"},
  "retired":{"certificate":TOOL_CERT,"requirement":TOOL_REQ,"predicate":TOOL_PRED},
  "zero_reality_frontier":{"active_nondominated_certificate_ids":sorted(active_certs) if ok else [],
    "active_nondominated_certificate_count":len(active_certs) if ok else 0,
    "active_required_propositions":sorted(active_reqs) if ok else [],
    "active_zero_reality_requirement_count":len(active_reqs) if ok else 0,
    "covered_predicates":sorted(zero_covered) if ok else [],
    "covered_predicate_count":len(zero_covered) if ok else 0,
    "primitive_zero_reality_work_units":primitive if ok else 0,
    "matched_priority_child_facts":16 if ok else 0},
  "direct_reality_blocked_predicates":sorted(DIRECT) if ok else [],
  "execution_policy":{"run_all_30_zero_reality_work_units_concurrently":True,"matched_16_first_resource_priority_without_serialization":True,
    "recompute_after_every_independently_verified_delta":True,"cancel_newly_dominated_branches":True,"fresh_reality_before_zero_reality_fixed_point":False},
  "new_reality_units_consumed":0,"incremental_spend_usd":0,"acceptance_credit_delta":0,"family_credit_delta":0,"ownership_credit_delta":0,
  "execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False,
 }
if __name__=="__main__":
 print(json.dumps(evaluate(),indent=2,sort_keys=True))
