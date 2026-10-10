"""Verify frozen professional whole-leaf claim scopes against the authoritative leaf manifest.

This verifier proves only domain-definition identity:
the claim scope is exactly the frozen manifest leaf contract/obligation/acceptance
for the exact V7 declared system and behavior. It does not prove scope coverage,
leaf property truth, domain execution, quality, promotion, or terminal authority.
"""
from __future__ import annotations
from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_whole_leaf_claim_scope_gate_v2 as gate
from canonical.runtime.coverage_claim_scope_guard_v1 import validate_claim

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF_DOMAIN_SCOPE_VERIFY_V1"
DOMAIN_SCHEMA_ID="PROJECT_BRAIN_PROFESSIONAL_QUALITY_MANIFEST_LEAF_DOMAIN_V1"
MANIFEST_PATH=gate.MANIFEST_PATH
MANIFEST_BLOB=gate.MANIFEST_BLOB
SUBJECT_PATH=gate.SUBJECT_PATH
SUBJECT_BLOB=gate.SUBJECT_BLOB
MISSION_PATH=gate.MISSION_PATH
MISSION_BLOB=gate.MISSION_BLOB
CLAIM_GUARD_PATH=gate.CLAIM_GUARD_PATH
CLAIM_GUARD_BLOB=gate.CLAIM_GUARD_BLOB
GATE_PATH="canonical/runtime/professional_quality_whole_leaf_claim_scope_gate_v2.py"
GATE_BLOB="d76b922e8d5c86f10568a3582759f8c23e69b2e0"
BEHAVIOR_ID="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
MEMBERSHIP_RULE=(
    "INPUT_IS_IN_THE_WHOLE_LEAF_DOMAIN_IFF_IT_IS_ADMISSIBLE_UNDER_THE_EXACT_"
    "FROZEN_MANIFEST_LEAF_CONTRACT_OBLIGATION_AND_ACCEPTANCE_FOR_THE_BOUND_V7_SUBJECT"
)
EXCLUSION_RULE="EXCLUDE_ONLY_INPUTS_NOT_ADMISSIBLE_UNDER_THE_FROZEN_MANIFEST_LEAF_DEFINITION"

def _blob(path:Path)->str:
    raw=path.read_bytes()
    return sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _canon_sha(value:Any)->str:
    raw=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    return sha256(raw).hexdigest()

def _text_sha(value:Any)->str:
    return sha256((value if isinstance(value,str) else "").encode("utf-8")).hexdigest()

def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
        "whole_leaf_domain_equivalence_proved":False,
        "whole_leaf_scope_complete":False,
        "leaf_property_truth_authority":False,
        "semantic_truth_authority":False,"execution_authority":False,
        "quality_authority":False,"acceptance_authority":False,
        "promotion_authority":False,"terminal_authority":False,
        "terminal_credit_delta":0,"incremental_spend_usd":0,**extra,
    }

def _load(path:Path)->dict[str,Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict):
        raise ValueError("NOT_OBJECT")
    return value

def expected_scope_definition(meta:Mapping[str,Any])->dict[str,Any]:
    return {
        "domain_schema_id":DOMAIN_SCHEMA_ID,
        "entire_admissible_leaf_domain":True,
        "domain_definition":{
            "authority":{
                "path":MANIFEST_PATH,
                "git_blob_sha":MANIFEST_BLOB,
            },
            "leaf_id":meta["leaf_id"],
            "root_id":meta["root_id"],
            "kind":meta["kind"],
            "behavior_id":BEHAVIOR_ID,
            "subject_kind":gate.SUBJECT_KIND,
            "subject_id":gate.SUBJECT_ID,
            "subject_sha256":gate.SUBJECT_SHA256,
            "leaf_contract_sha256":_text_sha(meta["contract"]),
            "leaf_obligation_sha256":_text_sha(meta["obligation"]),
            "leaf_acceptance_sha256":_text_sha(meta["acceptance"]),
            "membership_rule":MEMBERSHIP_RULE,
            "exclusion_rule":EXCLUSION_RULE,
        },
    }

def build_claim_scope(meta:Mapping[str,Any],*,epoch:str)->dict[str,Any]:
    scope=expected_scope_definition(meta)
    claim=gate.build_claim(meta,scope,epoch=epoch)
    return {
        "schema":gate.CLAIM_SCOPE_SCHEMA,
        "leaf_id":meta["leaf_id"],
        "root_id":meta["root_id"],
        "kind":meta["kind"],
        "behavior_id":BEHAVIOR_ID,
        "subject_kind":gate.SUBJECT_KIND,
        "subject_id":gate.SUBJECT_ID,
        "subject_sha256":gate.SUBJECT_SHA256,
        "leaf_acceptance":meta["acceptance"],
        "scope_definition":scope,
        "epoch":epoch,
        "claim":claim,
        "domain_equivalence_authority":False,
        "whole_leaf_scope_complete":False,
        "leaf_property_truth_authority":False,
        "semantic_truth_authority":False,
        "execution_authority":False,
        "quality_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }

def verify_document(doc:Mapping[str,Any],*,repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else ROOT
    fixed=(
        (MANIFEST_PATH,MANIFEST_BLOB,"MANIFEST"),
        (SUBJECT_PATH,SUBJECT_BLOB,"SUBJECT"),
        (MISSION_PATH,MISSION_BLOB,"MISSION"),
        (CLAIM_GUARD_PATH,CLAIM_GUARD_BLOB,"CLAIM_GUARD"),
        (GATE_PATH,GATE_BLOB,"GATE_V2"),
    )
    for rel,expected,label in fixed:
        path=root/rel
        if not path.is_file() or path.is_symlink():
            return _fail(label+"_MISSING")
        if _blob(path)!=expected:
            return _fail(label+"_STALE")

    manifest=_load(root/MANIFEST_PATH)
    leaf_id=doc.get("leaf_id")
    if not isinstance(leaf_id,str) or not leaf_id:
        return _fail("LEAF_ID_REQUIRED")
    meta=gate._manifest_leaf(manifest,leaf_id)
    if meta is None:
        return _fail("LEAF_NOT_IN_MANIFEST")

    if doc.get("schema")!=gate.CLAIM_SCOPE_SCHEMA:
        return _fail("CLAIM_SCOPE_SCHEMA_INVALID")
    if doc.get("root_id")!=meta["root_id"] or doc.get("kind")!=meta["kind"]:
        return _fail("LEAF_METADATA_DRIFT")
    if doc.get("behavior_id")!=BEHAVIOR_ID:
        return _fail("BEHAVIOR_DRIFT")
    if (doc.get("subject_kind"),doc.get("subject_id"),doc.get("subject_sha256")) != (
        gate.SUBJECT_KIND,gate.SUBJECT_ID,gate.SUBJECT_SHA256
    ):
        return _fail("SUBJECT_DRIFT")
    if doc.get("leaf_acceptance")!=meta["acceptance"]:
        return _fail("LEAF_ACCEPTANCE_DRIFT")

    scope=doc.get("scope_definition")
    expected_scope=expected_scope_definition(meta)
    if scope!=expected_scope:
        return _fail("SCOPE_DEFINITION_NOT_IDENTICAL_TO_AUTHORITATIVE_MANIFEST_LEAF_DOMAIN",
                     expected_scope_definition_sha256=_canon_sha(expected_scope))
    if scope.get("entire_admissible_leaf_domain") is not True:
        return _fail("ENTIRE_LEAF_DOMAIN_ASSERTION_REQUIRED")

    epoch=doc.get("epoch")
    if not isinstance(epoch,str) or not epoch:
        return _fail("EPOCH_REQUIRED")
    expected_claim=gate.build_claim(meta,expected_scope,epoch=epoch)
    if doc.get("claim")!=expected_claim:
        return _fail("CLAIM_CONTENT_ADDRESS_MISMATCH",expected_claim_id=expected_claim["claim_id"])
    claim_check=validate_claim(expected_claim,current_mission_blob_sha=MISSION_BLOB)
    if claim_check.get("pass") is not True:
        return _fail("CLAIM_GUARD_REJECTED",claim_guard=claim_check)

    for field in (
        "domain_equivalence_authority","whole_leaf_scope_complete",
        "leaf_property_truth_authority","semantic_truth_authority","execution_authority",
        "quality_authority","acceptance_authority","promotion_authority","terminal_authority",
    ):
        if doc.get(field) is not False:
            return _fail("SELF_AUTHORITY_FORBIDDEN:"+field)
    if doc.get("terminal_credit_delta")!=0:
        return _fail("TERMINAL_CREDIT_FORBIDDEN")

    return {
        "schema":SCHEMA,"pass":True,
        "status":"PASS__CLAIM_SCOPE_DEFINITION_IDENTICAL_TO_AUTHORITATIVE_WHOLE_LEAF_DOMAIN__SCOPE_COVER_AND_PROPERTY_TRUTH_SEPARATE",
        "leaf_id":leaf_id,"root_id":meta["root_id"],"kind":meta["kind"],
        "claim_id":expected_claim["claim_id"],
        "scope_definition_sha256":_canon_sha(expected_scope),
        "leaf_acceptance_sha256":_text_sha(meta["acceptance"]),
        "whole_leaf_domain_equivalence_proved":True,
        "whole_leaf_scope_complete":False,
        "leaf_property_truth_authority":False,
        "semantic_truth_authority":False,"execution_authority":False,
        "quality_authority":False,"acceptance_authority":False,
        "promotion_authority":False,"terminal_authority":False,
        "terminal_credit_delta":0,"incremental_spend_usd":0,
    }

def verify_path(path:str|Path,*,repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else ROOT
    target=Path(path)
    if not target.is_absolute():
        target=root/target
    target=target.resolve()
    try: target.relative_to(root)
    except ValueError: return _fail("CLAIM_SCOPE_PATH_ESCAPE")
    if not target.is_file() or target.is_symlink():
        return _fail("CLAIM_SCOPE_MISSING")
    try: doc=_load(target)
    except Exception: return _fail("CLAIM_SCOPE_JSON_INVALID")
    out=verify_document(doc,repo_root=root)
    out["claim_scope_git_blob_sha"]=_blob(target)
    return out

if __name__=="__main__":
    import sys
    if len(sys.argv)!=2:
        raise SystemExit("usage: python -m canonical.runtime.professional_quality_whole_leaf_domain_scope_verify_v1 <claim-scope-path>")
    print(json.dumps(verify_path(sys.argv[1]),indent=2,sort_keys=True))
