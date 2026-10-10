from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any,Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_OBSERVABLE_TRACE_SCOPE_SUPERSET_VERIFY_V1"
CANDIDATE="canonical/governance/PROFESSIONAL_OBSERVABLE_TRACE_SCOPE_SUPERSET_THEOREM_20261010_V1.json"
SOURCE_THEOREM=("canonical/governance/OPUS55_OBSERVABLE_TRACE_SCOPE_SUPERSET_THEOREM_20261006_V1.json","333bdc8306a19f005a600a47b415a4bd9cf9868c")
SOURCE_VERIFY=("canonical/verification/OPUS55_OBSERVABLE_TRACE_SCOPE_SUPERSET_SPRITE_VERIFICATION_20261006_V1.json","954ed383aa79fd8838249e58b0c848e338ea44de")
CONTRACTS=("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V2.json","ae250d5bc5da73b23600670be354ffba31e65e53")
GRAPH=("canonical/governance/PROFESSIONAL_QUALITY_ASSURANCE_GRAPH_20261009_V2.json","03530e29d70206b46b690b33a04c66765ff86ad7")
MANIFEST=("canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json","a7cad32c9fd969ff2c3857bb924c7bd746237ec2")
BEHAVIOR="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
EXPECTED_BASIS={
"OBSERVATION__OPAQUE_PAYLOAD_PLUS_MEDIA_PROVENANCE_AND_ENVIRONMENT_METADATA",
"ACTION__OPAQUE_TOOL_OR_COMPUTER_OR_API_OR_FILE_OPERATION",
"EMISSION__TEXT_ARTIFACT_DIAGRAM_OR_OTHER_SERIALIZABLE_OUTPUT",
"RESOURCE__TIME_COST_COMPUTE_CONTEXT_STORAGE_AND_FAILURE_STATUS",
"SAFETY_AUTHORITY__ABSTENTION_BOUNDARY_PERMISSION_AND_IRREVERSIBILITY_STATUS",
"STATE_TRANSITION__PERSISTENT_OR_EXTERNAL_STATE_CHANGE_VISIBLE_TO_FUTURE_INTERACTION",
}
FORBIDDEN_TRUE={
"per_leaf_positive_adequacy_over_carrier_proved",
"whole_leaf_scope_transport_complete",
"domain_semantic_closure","domain_execution_closure","professional_quality_closed",
}
REQUIRED_NONCLAIMS={
"NO_CLAIM_CURRENT_SCOPED_CAPABILITIES_COVER_ALL_OBSERVABLE_PROFESSIONAL_TRACES",
"NO_GLOBAL_LEAF_CLOSURE","NO_DOMAIN_SEMANTIC_CLOSURE","NO_DOMAIN_EXECUTION_CLOSURE",
"NO_UNKNOWN_DEFEATER_COMPLETENESS","NO_PROFESSIONAL_QUALITY_CLOSURE",
"NO_LIVE_DEFAULT_PROMOTION","NO_QUALITY_ACCEPTANCE_PROMOTION_OR_TERMINAL_AUTHORITY",
}

def blob(p:Path)->str:
 d=p.read_bytes();return sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
def read(root:Path,ref):
 p=(root/ref[0]).resolve()
 try:p.relative_to(root.resolve())
 except ValueError:return None
 if not p.is_file() or p.is_symlink() or blob(p)!=ref[1]:return None
 try:o=json.loads(p.read_text(encoding="utf-8"))
 except Exception:return None
 return o if isinstance(o,dict) else None
def fail(reason:str,**more:Any):
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
 "professional_domain_trace_containment_verified":False,
 "leaf_adequacy_authority":False,"quality_authority":False,"terminal_authority":False,
 "terminal_credit_delta":0,**more}

def evaluate_documents(c:Mapping[str,Any],source:Mapping[str,Any],sv:Mapping[str,Any],contracts:Mapping[str,Any],graph:Mapping[str,Any],manifest:Mapping[str,Any]):
 if c.get("schema")!="PROJECT_BRAIN_PROFESSIONAL_OBSERVABLE_TRACE_SCOPE_SUPERSET_THEOREM_V1":return fail("CANDIDATE_SCHEMA_INVALID")
 if c.get("professional_behavior_id")!=BEHAVIOR:return fail("BEHAVIOR_ID_INVALID")
 rows=(contracts.get("active_contracted_residuals") or contracts.get("contracts") or contracts.get("entries") or [])
 row=next((x for x in rows if isinstance(x,Mapping) and x.get("behavior_id")==BEHAVIOR),None)
 if row is None:return fail("PROFESSIONAL_CONTRACT_MISSING")
 frozen=c.get("frozen_professional_contract")
 if not isinstance(frozen,Mapping):return fail("FROZEN_CONTRACT_INVALID")
 for k in ("inputs","environment_state","allowed_information","required_output_or_action","success_condition","failure_condition","scope"):
  if frozen.get(k)!=row.get(k):return fail("CONTRACT_DRIFT:"+k)
 if graph.get("domain")!=BEHAVIOR:return fail("ASSURANCE_GRAPH_DOMAIN_MISMATCH")
 if manifest.get("root_count")!=12 or manifest.get("total_leaf_count")!=24:return fail("LEAF_MANIFEST_CARDINALITY_INVALID")
 src_basis=set(((source.get("first_principles_definition") or {}).get("trace_event_basis") or []))
 cand_basis=set(((c.get("trace_superdomain") or {}).get("event_basis") or []))
 if src_basis!=EXPECTED_BASIS or cand_basis!=EXPECTED_BASIS:return fail("TRACE_EVENT_BASIS_MISMATCH")
 if ((source.get("critical_split") or {}).get("current_acceptance_basis_universal_dominance_state"))!="OPEN":
  return fail("SOURCE_DOMINANCE_BOUNDARY_INVALID")
 if sv.get("conclusion")!="PASS__STRUCTURAL_SCOPE_SUPERSET_SURVIVES_POST_BASE_SOURCE_DELTA__UNIVERSAL_DOMINANCE_AND_OWNERSHIP_REMAIN_OPEN":
  return fail("SOURCE_INDEPENDENT_VERIFICATION_INVALID")
 checks=sv.get("checks") or {}
 if checks.get("scope_theorem_present") is not True or checks.get("dominance_explicitly_open") is not True or checks.get("no_brain_dominance_claim") is not True:
  return fail("SOURCE_VERIFICATION_BOUNDARY_INVALID")
 effect=c.get("current_effect") or {}
 if effect.get("observable_trace_carrier_contains_professional_domain") is not True:return fail("CONTAINMENT_CLAIM_MISSING")
 if effect.get("professional_scope_family_enumeration_required_for_domain_containment") is not False:return fail("ENUMERATION_BYPASS_NOT_BOUND")
 for k in FORBIDDEN_TRUE:
  if effect.get(k) is not False:return fail("OVERCLAIM:"+k)
 if effect.get("exact_leaf_receipts_proved")!=0:return fail("LEAF_RECEIPT_CREDIT_FORBIDDEN")
 theorem=c.get("theorem") or {}
 if theorem.get("closes")!="PROFESSIONAL_REAL_TASK_DOMAIN_TO_OBSERVABLE_TRACE_CARRIER_CONTAINMENT":return fail("THEOREM_SCOPE_INVALID")
 if not REQUIRED_NONCLAIMS<=set(c.get("hard_nonclaims") or []):return fail("HARD_NONCLAIMS_INCOMPLETE")
 for field in ("execution_authority","promotion_authority","quality_authority","terminal_authority"):
  if c.get(field) is not False:return fail("SELF_AUTHORITY_FORBIDDEN:"+field)
 return {"schema":SCHEMA,"pass":True,
 "status":"PASS__PROFESSIONAL_DOMAIN_STRUCTURALLY_CONTAINED_IN_OBSERVABLE_TRACE_SUPERDOMAIN__LEAF_ADEQUACY_OPEN",
 "professional_domain_trace_containment_verified":True,
 "artifact_or_domain_label_enumeration_required_for_scope_containment":False,
 "trace_event_basis":sorted(EXPECTED_BASIS),"professional_leaf_count":24,
 "per_leaf_positive_adequacy_proved":False,"verified_global_leaf_count":0,
 "domain_semantic_closure":False,"domain_execution_closure":False,
 "professional_quality_closed":False,"leaf_adequacy_authority":False,
 "quality_authority":False,"terminal_authority":False,"terminal_credit_delta":0}

def verify(*,repo_root:str|Path|None=None):
 root=Path(repo_root).resolve() if repo_root else Path(__file__).resolve().parents[2]
 cp=root/CANDIDATE
 if not cp.is_file() or cp.is_symlink():return fail("CANDIDATE_FILE_INVALID")
 try:c=json.loads(cp.read_text(encoding="utf-8"))
 except Exception:return fail("CANDIDATE_JSON_INVALID")
 docs=[read(root,x) for x in (SOURCE_THEOREM,SOURCE_VERIFY,CONTRACTS,GRAPH,MANIFEST)]
 if any(x is None for x in docs):return fail("AUTHORITY_BYTES_INVALID")
 return evaluate_documents(c,*docs)
if __name__=="__main__":print(json.dumps(verify(),indent=2,sort_keys=True))
