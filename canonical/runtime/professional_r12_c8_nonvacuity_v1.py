"""R12 C8 nonvacuity proof by shared scoped-runtime positive-route reuse.

C8 is existential only: prove at least one real supported positive R12 route
exists. This module does not prove semantic totality. It binds the same scoped
UVCK capability to both R12 semantic and execution leaves, then requires an
independently replayed execution receipt with observed positive paths on the
exact same runtime/current-generation/order-verification bytes.

Unknown-defeater completeness, CC_R3, semantic property truth, quality,
acceptance, promotion, and terminal authority remain false.
"""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_C8_NONVACUITY_V1"
ROOT_ID="R12_META_COMPOSITION_CLOSURE"
SEMANTIC_LEAF="PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC"
EXECUTION_LEAF="PQ::R12_META_COMPOSITION_CLOSURE::EXECUTION"
SCOPE_ID="PQ::R12::UVCK::FAIL_CLOSED_META_COMPOSITION"
CLAIM_KIND="FAIL_CLOSED_ASSURANCE_GRAPH_META_COMPOSITION_AND_ORDER_INDEPENDENT_DEFEATER_ROUTING"
REGISTRY_PATH="canonical/governance/PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_REGISTRY_20261010_V1.json"
REGISTRY_BLOB="b9ddf7cbe7fbfad0e81fe068a0c19b48703b5aba"
SCOPE_PATH="canonical/governance/PROFESSIONAL_QUALITY_R12_META_COMPOSITION_SCOPE_20261010_V1.json"
SCOPE_BLOB="4c69313ae31905f6aa379361d515dffdfb41efae"
EXECUTION_VERIFY_PATH="canonical/verification/PROFESSIONAL_QUALITY_R12_EXECUTION_PROPERTY_TRUTH_INDEPENDENT_VERIFY_20261010_V1.json"
EXECUTION_VERIFY_BLOB="b2b9365ad4e7d34628d74f328507eecf01a13804"
CURRENTGEN_PATH="canonical/verification/UVCK_V2_CURRENT_GENERATION_INDEPENDENT_REPLAY_VERIFY_20261009_V1.json"
CURRENTGEN_BLOB="81f7f070233b6aa1c4b491949a4c3e7aedfafd10"
RUNTIME_PATH="canonical/runtime/assurance_closure_compiler_v1.py"
RUNTIME_BLOB="b4274a48edbe626a9ae9fd33da2f2227ca4dd5e8"
ORDER_PATH="canonical/verification/UVCK_V2_DEFEATER_ORDER_VERIFY_20261009_V1.json"
ORDER_BLOB="1c3428b10a1205e928a87f41a7c16a8a3d17b7ca"

def _blob(path:Path)->str:
    raw=path.read_bytes()
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {
      "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
      "c8_nonvacuity_proved":False,"positive_supported_route_count":0,
      "stronger_material_defeater_totality_proved":False,
      "cc_r3_terminal_closure_proved":False,
      "semantic_property_truth_authority":False,
      "quality_authority":False,"acceptance_authority":False,
      "promotion_authority":False,"terminal_authority":False,
      "terminal_credit_delta":0,"incremental_spend_usd":0,**extra,
    }

def _r12_entry(registry:Mapping[str,Any])->Mapping[str,Any]|None:
    rows=registry.get("entries")
    if not isinstance(rows,list): return None
    found=[
      x for x in rows
      if isinstance(x,Mapping)
      and x.get("scope_id")==SCOPE_ID
      and x.get("root_id")==ROOT_ID
    ]
    return found[0] if len(found)==1 else None

def evaluate_documents(
    registry:Mapping[str,Any],
    scope:Mapping[str,Any],
    execution_verify:Mapping[str,Any],
)->dict[str,Any]:
    if not all(isinstance(x,Mapping) for x in (registry,scope,execution_verify)):
        return _fail("INPUT_NOT_MAPPING")

    row=_r12_entry(registry)
    if row is None:
        return _fail("R12_SCOPED_EVIDENCE_ENTRY_MISSING_OR_NONUNIQUE")
    leaves=row.get("contributes_to_leaf_ids")
    if not isinstance(leaves,list) or {SEMANTIC_LEAF,EXECUTION_LEAF} - set(leaves):
        return _fail("R12_SCOPE_DOES_NOT_BIND_BOTH_LEAVES")
    if row.get("claim_kind")!=CLAIM_KIND:
        return _fail("R12_SCOPE_CLAIM_KIND_DRIFT")
    if any(row.get(k) is not False for k in ("global_leaf_closure","global_root_closure","semantic_leaf_credit")):
        return _fail("R12_SCOPE_AUTHORITY_INFLATION")

    expected_links={
      "source_receipt":(CURRENTGEN_PATH,CURRENTGEN_BLOB),
      "reusable_compiler":(RUNTIME_PATH,RUNTIME_BLOB),
      "compiler_verification":(ORDER_PATH,ORDER_BLOB),
      "scope_governance":(SCOPE_PATH,SCOPE_BLOB),
    }
    for field,(path,blob) in expected_links.items():
        link=row.get(field)
        if not isinstance(link,Mapping) or link.get("path")!=path or link.get("git_blob_sha")!=blob:
            return _fail("R12_SCOPE_LINK_DRIFT:"+field)

    if scope.get("root_id")!=ROOT_ID or scope.get("claim_kind")!=CLAIM_KIND:
        return _fail("R12_SCOPE_GOVERNANCE_IDENTITY_DRIFT")
    components=scope.get("exact_components")
    if not isinstance(components,Mapping):
        return _fail("R12_SCOPE_COMPONENTS_MISSING")
    required_components={
      "runtime":(RUNTIME_PATH,RUNTIME_BLOB),
      "current_generation_replay":(CURRENTGEN_PATH,CURRENTGEN_BLOB),
      "order_soundness_verification":(ORDER_PATH,ORDER_BLOB),
    }
    for field,(path,blob) in required_components.items():
        link=components.get(field)
        if not isinstance(link,Mapping) or link.get("path")!=path or link.get("git_blob_sha")!=blob:
            return _fail("R12_SCOPE_COMPONENT_DRIFT:"+field)
    limits=set(scope.get("limitations") or [])
    if "NO_UNKNOWN_DEFEATER_COMPLETENESS" not in limits:
        return _fail("UNKNOWN_DEFEATER_BOUNDARY_MISSING")
    if "NO_DOMAIN_SEMANTIC_CLOSURE" not in limits:
        return _fail("SEMANTIC_CLOSURE_BOUNDARY_MISSING")
    if scope.get("global_leaf_closure") is not False or scope.get("global_root_closure") is not False:
        return _fail("R12_SCOPE_GOVERNANCE_AUTHORITY_INFLATION")

    if not str(execution_verify.get("status") or "").startswith("PASS__INDEPENDENT_SPRITE"):
        return _fail("R12_EXECUTION_RECEIPT_NOT_INDEPENDENT_PASS")
    subject=execution_verify.get("subject")
    if not isinstance(subject,Mapping) or subject.get("leaf_id")!=EXECUTION_LEAF or subject.get("root_id")!=ROOT_ID:
        return _fail("R12_EXECUTION_SUBJECT_DRIFT")
    blobs=execution_verify.get("exact_blobs")
    if not isinstance(blobs,Mapping):
        return _fail("R12_EXECUTION_BLOBS_MISSING")
    if blobs.get("uvck_runtime")!=RUNTIME_BLOB:
        return _fail("EXECUTION_RUNTIME_BINDING_DRIFT")
    if blobs.get("uvck_current_generation_verification")!=CURRENTGEN_BLOB:
        return _fail("EXECUTION_CURRENTGEN_BINDING_DRIFT")
    if blobs.get("uvck_defeater_order_verification")!=ORDER_BLOB:
        return _fail("EXECUTION_ORDER_BINDING_DRIFT")
    replay=execution_verify.get("independent_replay")
    counts=(replay or {}).get("observed_case_counts") if isinstance(replay,Mapping) else None
    if not isinstance(counts,Mapping):
        return _fail("R12_EXECUTION_CASE_COUNTS_MISSING")
    positive=counts.get("positive")
    if not isinstance(positive,int) or isinstance(positive,bool) or positive<1:
        return _fail("NO_OBSERVED_POSITIVE_R12_ROUTE")
    hard=set(execution_verify.get("hard_nonclaims") or [])
    if "NO_R12_SEMANTIC_LEAF_CLOSURE" not in hard or "NO_UNKNOWN_DEFEATER_COMPLETENESS" not in hard:
        return _fail("R12_EXECUTION_BOUNDARY_MISSING")
    if execution_verify.get("r12_semantic_leaf_closed") is not False:
        return _fail("R12_EXECUTION_SEMANTIC_AUTHORITY_INFLATION")
    if execution_verify.get("unknown_defeater_completeness_proved") is not False:
        return _fail("R12_EXECUTION_UNKNOWN_DEFEATER_OVERCLAIM")

    return {
      "schema":SCHEMA,"pass":True,
      "status":"PASS__R12_C8_REAL_SUPPORTED_POSITIVE_ROUTE_NONVACUITY__STRONGER_TOTALITY_OPEN",
      "root_id":ROOT_ID,"semantic_leaf_id":SEMANTIC_LEAF,"execution_leaf_id":EXECUTION_LEAF,
      "scope_id":SCOPE_ID,"claim_kind":CLAIM_KIND,
      "route_basis":{
        "shared_scoped_capability_binds_semantic_and_execution_leaves":True,
        "exact_uvck_runtime_blob":RUNTIME_BLOB,
        "exact_current_generation_receipt_blob":CURRENTGEN_BLOB,
        "exact_order_verification_blob":ORDER_BLOB,
        "independently_observed_positive_execution_paths":positive,
        "interpretation":"EXISTENCE_OF_REAL_SUPPORTED_POSITIVE_ROUTE_ONLY__NOT_UNIVERSAL_SEMANTIC_TOTALITY",
      },
      "c8_nonvacuity_proved":True,
      "positive_supported_route_count":positive,
      "stronger_material_defeater_totality_proved":False,
      "cc_r3_terminal_closure_proved":False,
      "semantic_property_truth_authority":False,
      "quality_authority":False,"acceptance_authority":False,
      "promotion_authority":False,"terminal_authority":False,
      "terminal_credit_delta":0,"incremental_spend_usd":0,
    }

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root else ROOT
    pins={
      REGISTRY_PATH:REGISTRY_BLOB,
      SCOPE_PATH:SCOPE_BLOB,
      EXECUTION_VERIFY_PATH:EXECUTION_VERIFY_BLOB,
    }
    docs={}
    try:
        for rel,expected in pins.items():
            p=root/rel
            if not p.is_file() or p.is_symlink(): return _fail("PIN_MISSING",path=rel)
            observed=_blob(p)
            if observed!=expected: return _fail("PIN_BLOB_DRIFT",path=rel,observed_blob=observed)
            docs[rel]=json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        return _fail("PIN_LOAD_FAILED",detail=type(exc).__name__+":"+str(exc))
    return evaluate_documents(docs[REGISTRY_PATH],docs[SCOPE_PATH],docs[EXECUTION_VERIFY_PATH])

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
