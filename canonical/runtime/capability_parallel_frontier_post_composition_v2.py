"""Post-composition live frontier adapter V2.

V1 was bound to the obsolete whole-leaf-domain-evidence lane. V2 binds the
current property-truth depletion phase after 24/24 scope closure, 4/24
content-addressed leaf admission, and 12/12 semantic identity-carrier
factorization. It delegates Pareto/currentness mechanics unchanged to the
verified interval-robust V2 core.
"""
from __future__ import annotations
from typing import Any, Mapping
from canonical.runtime import capability_parallel_frontier_v2 as core

SCHEMA="PROJECT_BRAIN_POST_COMPOSITION_PARALLEL_FRONTIER_V2"
PROF_WORK="PROFESSIONAL_QUALITY_V7_PROPERTY_TRUTH_DEPLETION"
REGISTRY_REL="canonical/governance/PROFESSIONAL_QUALITY_LEAF_EVIDENCE_REGISTRY_20261010_V1.json"
REGISTRY_SHA="71863cfbb47f9951eaf34e4e89692aee5c540560"
REGISTRY_VERIFY_REL="canonical/verification/PROFESSIONAL_QUALITY_LEAF_REGISTRY_PROPERTY_TRUTH_VERIFY_20261010_V2.json"
REGISTRY_VERIFY_SHA="bdde7b52793272623773b07bf774c0a74c6be7af"
SEMANTIC_CARRIER_ACTIVATION_REL="canonical/governance/PROFESSIONAL_SEMANTIC_IDENTITY_CARRIER_ACTIVATION_20261010_V1.json"
SEMANTIC_CARRIER_ACTIVATION_SHA="3e99ddbf25cd8e392c5a22a5c14ae5fea5dc3138"
SEMANTIC_CARRIER_VERIFY_REL="canonical/verification/PROFESSIONAL_SEMANTIC_IDENTITY_CARRIER_VERIFY_20261010_V1.json"
SEMANTIC_CARRIER_VERIFY_SHA="35a3ccf9ad454aa0318a4ed10edc065830c3874d"
EXPECTED_VERIFIED={
 "PQ::R1_TARGET_SPECIFICATION::EXECUTION",
 "PQ::R7_CAUSAL_PRESCRIPTIVE::EXECUTION",
 "PQ::R10_ANALYSIS_DECISION::EXECUTION",
 "PQ::R12_META_COMPOSITION_CLOSURE::EXECUTION",
}

class PostCompositionFrontierV2Error(ValueError):
    pass

def _require_blob(rel:str, sha:str)->None:
    path=core.ROOT / rel
    if not path.is_file() or core._git_blob_sha(path)!=sha:
        raise PostCompositionFrontierV2Error("BOUND_EVIDENCE_STALE:"+rel)

def _assert_current_phase(frontier:Mapping[str,Any])->None:
    candidates=frontier.get("candidates")
    if not isinstance(candidates,list):
        raise PostCompositionFrontierV2Error("CANDIDATES_INVALID")
    rows=[x for x in candidates if isinstance(x,Mapping) and x.get("work_id")==PROF_WORK]
    if len(rows)!=1:
        raise PostCompositionFrontierV2Error("PROFESSIONAL_PROPERTY_TRUTH_LANE_CARDINALITY")
    row=rows[0]
    if row.get("evidence_acquisition_mode")!="READ_ONLY":
        raise PostCompositionFrontierV2Error("PROFESSIONAL_PROPERTY_TRUTH_NOT_READ_ONLY")
    ev=row.get("read_only_evidence")
    if not isinstance(ev,Mapping):
        raise PostCompositionFrontierV2Error("PROFESSIONAL_EVIDENCE_MISSING")
    if ev.get("whole_leaf_scope_complete_count")!=24:
        raise PostCompositionFrontierV2Error("WHOLE_LEAF_SCOPE_COUNT_NOT_24")
    if ev.get("property_truth_closed_count")!=4:
        raise PostCompositionFrontierV2Error("PROPERTY_TRUTH_COUNT_NOT_4")
    if set(ev.get("verified_property_truth_leaf_ids") or [])!=EXPECTED_VERIFIED:
        raise PostCompositionFrontierV2Error("PROPERTY_TRUTH_LEAF_SET_MISMATCH")
    if ev.get("open_execution_leaf_count")!=8 or ev.get("open_semantic_leaf_count")!=12:
        raise PostCompositionFrontierV2Error("OPEN_LEAF_COUNTS_INVALID")
    if ev.get("semantic_identity_carrier_verified") is not True:
        raise PostCompositionFrontierV2Error("SEMANTIC_IDENTITY_CARRIER_NOT_VERIFIED")
    if ev.get("semantic_identity_carrier_count")!=12:
        raise PostCompositionFrontierV2Error("SEMANTIC_IDENTITY_CARRIER_COUNT_NOT_12")
    if ev.get("semantic_property_truth_closed_count")!=0:
        raise PostCompositionFrontierV2Error("SEMANTIC_PROPERTY_TRUTH_OVERCLAIM")
    if ev.get("vector_bounds_complete") is not False:
        raise PostCompositionFrontierV2Error("VECTOR_COMPLETENESS_OVERCLAIM")
    bindings=(
      (ev.get("leaf_registry_path"),ev.get("leaf_registry_git_blob_sha"),REGISTRY_REL,REGISTRY_SHA),
      (ev.get("leaf_registry_verification_path"),ev.get("leaf_registry_verification_git_blob_sha"),REGISTRY_VERIFY_REL,REGISTRY_VERIFY_SHA),
      (ev.get("semantic_identity_carrier_activation"),ev.get("semantic_identity_carrier_activation_git_blob_sha"),SEMANTIC_CARRIER_ACTIVATION_REL,SEMANTIC_CARRIER_ACTIVATION_SHA),
      (ev.get("semantic_identity_carrier_verification"),ev.get("semantic_identity_carrier_verification_git_blob_sha"),SEMANTIC_CARRIER_VERIFY_REL,SEMANTIC_CARRIER_VERIFY_SHA),
    )
    for got_rel,got_sha,exp_rel,exp_sha in bindings:
        if got_rel!=exp_rel or got_sha!=exp_sha:
            raise PostCompositionFrontierV2Error("PROFESSIONAL_EVIDENCE_BINDING_MISMATCH:"+exp_rel)
        _require_blob(exp_rel,exp_sha)

def plan_current_post_composition_frontier_v2()->dict[str,Any]:
    frontier=core.load_current_frontier()
    _assert_current_phase(frontier)
    out=core.plan_parallel_frontier(frontier)
    return {
      **out,
      "adapter_schema":SCHEMA,
      "post_composition_phase_verified":True,
      "property_truth_closed_count":4,
      "open_execution_leaf_count":8,
      "open_semantic_leaf_count":12,
      "semantic_identity_carrier_verified_count":12,
      "sequential_root_dynamic_refresh_bypassed":True,
      "execution_authority":False,
      "promotion_authority":False,
      "terminal_authority":False,
      "terminal_credit_delta":0,
    }

if __name__=="__main__":
    import json
    print(json.dumps(plan_current_post_composition_frontier_v2(),indent=2,sort_keys=True))
