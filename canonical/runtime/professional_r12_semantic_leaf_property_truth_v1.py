"""Property-truth verifier for the exact stable R12 semantic leaf.

This composes the already independently verified claim-scoped coverage roots:
  CC_R1: B_real[C] subseteq B_plus[C]
  CC_R3: B_plus[C] subseteq G_minus[C]
  CC_R2: G_minus[C] subseteq G_real[C]
with R4 proof/realization closure on one exact frozen claim.

By set-inclusion transitivity, B_real[C] subseteq G_real[C].  Because the
stable claim binds G_real/G_minus to the exact R12 semantic target predicate,
this proves the exact semantic leaf property for its frozen whole domain.

No quality, acceptance, promotion, live-default, checkpoint, or terminal
authority is granted by this leaf proof.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_r12_root_registry_verify_v3 as roots

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_SEMANTIC_LEAF_PROPERTY_TRUTH_V1"
LEAF_ID="PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC"
ROOT_ID="R12_META_COMPOSITION_CLOSURE"
CLAIM_ID="11870f850b46bcfcc31094f764fc4f45c911aaac413979ceb62679ff19a53162"
CLAIM_PATH="canonical/governance/COVERAGE_COMPLETENESS_FROZEN_CLAIM_PROFESSIONAL_R12_SEMANTIC_20261010_V2.json"
CLAIM_BLOB="7b26ddba501358d42d6fa342efd27d389bb30654"
REGISTRY_PATH="canonical/governance/COVERAGE_ROOT_REGISTRY_PROFESSIONAL_R12_SEMANTIC_20261011_V3.json"
REGISTRY_BLOB="f14486629e31420d639c7769e9b96ab44f3d31c8"
ROOT_RUNTIME_PATH="canonical/runtime/professional_r12_root_registry_verify_v3.py"
ROOT_RUNTIME_BLOB="c113d6f458f69d56ad7bb60f2c218f791d1beacf"
ROOT_RECEIPT_PATH="canonical/verification/PROFESSIONAL_R12_ROOT_REGISTRY_INDEPENDENT_VERIFY_20261011_V3.json"
ROOT_RECEIPT_BLOB="211ca40876bb45d72ccd6764a91d62a584721cb0"
ROOT_RESULT_SHA256="fe6a4861f2eac35b91e669e65cf88514727965082a2ff8b694bd42ee392403ca"
EXPECTED_ROOT_IDENTITIES={
    "CC_R1_REALITY_CONTAINMENT_V1":"B_real SUBSETEQ B_plus",
    "CC_R2_MISSION_SOUNDNESS_V1":"G_minus SUBSETEQ G_real",
    "CC_R3_TERMINAL_CLOSURE_V1":"B_plus SUBSETEQ G_minus",
}
TARGET_ACCEPTANCE="DOMAIN_SPECIFIC_CLAIM_SEMANTICS_GROUNDING_SCOPE_UNCERTAINTY_AND_ALL_ROOT_RELEVANT_DEFEATERS_RESOLVED_WITH_TYPED_EVIDENCE"
TARGET_QUANTIFICATION="FOR_ALL_ADMISSIBLE_INPUTS_IN_VERIFIED_WHOLE_LEAF_SCOPE"


def _blob(path:Path)->str:
    raw=path.read_bytes()
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def _load(root:Path,rel:str,expected:str)->Mapping[str,Any]:
    p=root/rel
    if not p.is_file() or p.is_symlink():
        raise ValueError("PIN_MISSING:"+rel)
    got=_blob(p)
    if got!=expected:
        raise ValueError("PIN_BLOB_DRIFT:"+rel+":"+got)
    obj=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(obj,Mapping):
        raise ValueError("PIN_NOT_OBJECT:"+rel)
    return obj


def _pin(root:Path,rel:str,expected:str)->None:
    p=root/rel
    if not p.is_file() or p.is_symlink():
        raise ValueError("PIN_MISSING:"+rel)
    got=_blob(p)
    if got!=expected:
        raise ValueError("PIN_BLOB_DRIFT:"+rel+":"+got)


def _zero()->dict[str,Any]:
    return {
        "quality_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }


def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "pass":False,
        "status":"FAIL_CLOSED",
        "reason":reason,
        "leaf_id":LEAF_ID,
        "root_id":ROOT_ID,
        "semantic_leaf_property_truth_proved":False,
        "claim_scoped_totality_proved":False,
        "cc_r1_reality_containment_proved":False,
        "cc_r2_mission_soundness_proved":False,
        "cc_r3_terminal_closure_proved":False,
        "r4_proof_realization_authority":False,
        **_zero(),
        **extra,
    }


def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    try:
        claim=_load(root,CLAIM_PATH,CLAIM_BLOB)
        registry=_load(root,REGISTRY_PATH,REGISTRY_BLOB)
        receipt=_load(root,ROOT_RECEIPT_PATH,ROOT_RECEIPT_BLOB)
        _pin(root,ROOT_RUNTIME_PATH,ROOT_RUNTIME_BLOB)
    except Exception as exc:
        return _fail(type(exc).__name__+":"+str(exc))

    if claim.get("claim_id")!=CLAIM_ID or claim.get("leaf_id")!=LEAF_ID:
        return _fail("FROZEN_CLAIM_IDENTITY_DRIFT")
    target=claim.get("target_predicate") or {}
    if target.get("acceptance")!=TARGET_ACCEPTANCE:
        return _fail("TARGET_ACCEPTANCE_DRIFT")
    if target.get("quantification")!=TARGET_QUANTIFICATION:
        return _fail("TARGET_QUANTIFICATION_DRIFT")

    active=registry.get("active_claim") or {}
    for key in (
        "claim_id","claim_kind","mission_blob_sha","scope_sha256",
        "target_predicate_sha256","semantics_sha256","epoch","authority_id",
    ):
        if active.get(key)!=claim.get(key):
            return _fail("REGISTRY_ACTIVE_CLAIM_MISMATCH:"+key)

    identities={}
    for row in registry.get("root_identities") or []:
        if isinstance(row,Mapping):
            identities[row.get("canonical_id")]=row.get("claim")
    if any(identities.get(k)!=v for k,v in EXPECTED_ROOT_IDENTITIES.items()):
        return _fail("ROOT_INCLUSION_IDENTITY_DRIFT",observed=identities)

    live=roots.verify(repo_root=root)
    if live.get("pass") is not True:
        return _fail("ROOT_REGISTRY_RUNTIME_REJECTED",root_registry_result=live)
    if live.get("claim_id")!=CLAIM_ID:
        return _fail("ROOT_REGISTRY_RUNTIME_CLAIM_DRIFT")
    if live.get("proved_root_ids")!=list(EXPECTED_ROOT_IDENTITIES):
        return _fail("ROOT_REGISTRY_PROVED_SET_DRIFT")
    if live.get("open_root_ids")!=[]:
        return _fail("ROOT_REGISTRY_OPEN_ROOTS_REMAIN")
    if live.get("r4_proof_closure") is not True:
        return _fail("R4_PROOF_REALIZATION_NOT_CLOSED")

    if receipt.get("pass") is not True or not str(receipt.get("status") or "").startswith("PASS__INDEPENDENT_SPRITE"):
        return _fail("ROOT_REGISTRY_INDEPENDENT_RECEIPT_NOT_PASS")
    replay=receipt.get("independent_replay") or {}
    if replay.get("tests_failed")!=0 or replay.get("tests_passed")!=7 or replay.get("py_compile")!="PASS":
        return _fail("ROOT_REGISTRY_INDEPENDENT_REPLAY_NOT_COMPLETE")
    if replay.get("verifier_result_sha256")!=ROOT_RESULT_SHA256:
        return _fail("ROOT_REGISTRY_RERUN_RESULT_HASH_DRIFT")
    truth=receipt.get("truth") or {}
    if truth.get("claim_id")!=CLAIM_ID:
        return _fail("ROOT_REGISTRY_RECEIPT_CLAIM_DRIFT")
    if truth.get("proved_root_ids")!=list(EXPECTED_ROOT_IDENTITIES):
        return _fail("ROOT_REGISTRY_RECEIPT_PROVED_SET_DRIFT")
    if truth.get("open_root_ids")!=[]:
        return _fail("ROOT_REGISTRY_RECEIPT_OPEN_ROOTS_REMAIN")
    if truth.get("r4_proof_closure") is not True:
        return _fail("ROOT_REGISTRY_RECEIPT_R4_NOT_CLOSED")
    if truth.get("semantic_property_truth_authority") is not False:
        return _fail("ROOT_RECEIPT_PREMATURE_PROPERTY_AUTHORITY")

    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__R12_SEMANTIC_LEAF_PROPERTY_TRUTH__EXACT_FROZEN_CLAIM__ZERO_GLOBAL_QUALITY_OR_TERMINAL_AUTHORITY",
        "leaf_id":LEAF_ID,
        "root_id":ROOT_ID,
        "semantic_claim_id":CLAIM_ID,
        "semantic_scope_sha256":claim.get("scope_sha256"),
        "semantic_target_predicate_sha256":claim.get("target_predicate_sha256"),
        "semantic_semantics_sha256":claim.get("semantics_sha256"),
        "proof_mode":"SET_INCLUSION_TRANSITIVITY_WITH_EXECUTABLE_R4",
        "proof_chain":[
            "B_real SUBSETEQ B_plus",
            "B_plus SUBSETEQ G_minus",
            "G_minus SUBSETEQ G_real",
            "THEREFORE B_real SUBSETEQ G_real",
        ],
        "semantic_leaf_property_truth_proved":True,
        "leaf_semantic_satisfied":True,
        "claim_scoped_totality_proved":True,
        "cc_r1_reality_containment_proved":True,
        "cc_r2_mission_soundness_proved":True,
        "cc_r3_terminal_closure_proved":True,
        "r4_proof_realization_authority":True,
        "cross_claim_transport":False,
        "finite_catalog_completeness_claim":False,
        **_zero(),
    }
