"""Bridge the verified R12 C5 whole-leaf coverage proof to the stable V3 semantic claim.

This transports no property/root authority from V2. It proves only that the
current V3 R12 semantic claim binds the same exact whole-leaf scope claim and
scope digest already covered by the independently verified C5 proof.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_semantic_totality_claim_pack_v3 as pack_v3
from canonical.runtime import professional_r12_semantic_c5_claim_bound_verify_v1 as c5

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_SEMANTIC_V3_C5_BRIDGE_V1"
LEAF_ID="PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC"
V3_CLAIM_ID="11870f850b46bcfcc31094f764fc4f45c911aaac413979ceb62679ff19a53162"
V2_PROPERTY_CLAIM_ID="97ff74650749db87f378d5926ed820e004f3f792583c2c8455e51c3ccacbe7f7"
WHOLE_LEAF_SCOPE_CLAIM_ID="05b74983836dd1f6a13a0db72443246fb74f99548f0d982a769a6a7e572e9e85"
SCOPE_SHA256="3958f259dba6bc6d4dfe1dad0b3ec26ecb1b8d92ea4763985f52ce96cfc55a1d"

def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
        "leaf_id":LEAF_ID,"v3_claim_id":V3_CLAIM_ID,
        "c5_coverage_accounting_proved_for_v3_claim":False,
        "cc_r3_terminal_closure_proved":False,
        "semantic_property_truth_authority":False,
        "quality_authority":False,"acceptance_authority":False,
        "promotion_authority":False,"terminal_authority":False,
        "property_truth_credit_delta":0,"terminal_credit_delta":0,
        "incremental_spend_usd":0,**extra,
    }

def evaluate(v3_pack:Mapping[str,Any],c5_verdict:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(v3_pack,Mapping) or v3_pack.get("pass") is not True:
        return _fail("V3_PACK_NOT_PASS")
    if not isinstance(c5_verdict,Mapping) or c5_verdict.get("pass") is not True:
        return _fail("PRIOR_C5_VERIFICATION_NOT_PASS")
    rows=v3_pack.get("claims")
    if not isinstance(rows,list):
        return _fail("V3_CLAIMS_INVALID")
    matches=[x for x in rows if isinstance(x,Mapping) and x.get("leaf_id")==LEAF_ID]
    if len(matches)!=1:
        return _fail("V3_R12_ROW_NOT_UNIQUE")
    row=matches[0]
    claim=row.get("frozen_claim")
    if not isinstance(claim,Mapping):
        return _fail("V3_R12_FROZEN_CLAIM_MISSING")
    if claim.get("claim_id")!=V3_CLAIM_ID:
        return _fail("V3_R12_CLAIM_ID_DRIFT",observed=claim.get("claim_id"))
    if row.get("source_v2_claim_id")!=V2_PROPERTY_CLAIM_ID:
        return _fail("V3_SOURCE_V2_ID_DRIFT",observed=row.get("source_v2_claim_id"))
    if row.get("source_v2_claim_authority_transported") is not False:
        return _fail("V2_PROPERTY_AUTHORITY_TRANSPORT_FORBIDDEN")
    if row.get("whole_leaf_scope_claim_id")!=WHOLE_LEAF_SCOPE_CLAIM_ID:
        return _fail("WHOLE_LEAF_SCOPE_CLAIM_ID_DRIFT",observed=row.get("whole_leaf_scope_claim_id"))
    if row.get("scope_definition_sha256")!=SCOPE_SHA256:
        return _fail("ROW_SCOPE_DIGEST_DRIFT",observed=row.get("scope_definition_sha256"))
    if claim.get("scope_sha256")!=SCOPE_SHA256:
        return _fail("V3_CLAIM_SCOPE_DIGEST_DRIFT",observed=claim.get("scope_sha256"))
    if c5_verdict.get("claim_id")!=WHOLE_LEAF_SCOPE_CLAIM_ID:
        return _fail("PRIOR_C5_SCOPE_CLAIM_ID_DRIFT",observed=c5_verdict.get("claim_id"))
    if c5_verdict.get("scope_sha256")!=SCOPE_SHA256:
        return _fail("PRIOR_C5_SCOPE_DIGEST_DRIFT",observed=c5_verdict.get("scope_sha256"))
    if c5_verdict.get("c5_coverage_accounting_proved") is not True:
        return _fail("PRIOR_C5_COVERAGE_NOT_PROVED")
    if c5_verdict.get("whole_leaf_scope_complete") is not True:
        return _fail("PRIOR_C5_SCOPE_NOT_COMPLETE")
    if c5_verdict.get("semantic_property_truth_authority") is not False:
        return _fail("PRIOR_C5_PROPERTY_AUTHORITY_FORBIDDEN")
    if c5_verdict.get("cc_r3_terminal_closure") is not False:
        return _fail("PRIOR_C5_CC_R3_OVERCLAIM")

    return {
        "schema":SCHEMA,"pass":True,
        "status":"PASS__R12_V3_SEMANTIC_CLAIM_REUSES_EXACT_WHOLE_LEAF_C5_COVERAGE_ACCOUNTING__ZERO_PROPERTY_TRUTH_CREDIT",
        "leaf_id":LEAF_ID,
        "v3_claim_id":V3_CLAIM_ID,
        "source_v2_property_claim_id":V2_PROPERTY_CLAIM_ID,
        "source_v2_property_authority_transported":False,
        "whole_leaf_scope_claim_id":WHOLE_LEAF_SCOPE_CLAIM_ID,
        "scope_sha256":SCOPE_SHA256,
        "c5_coverage_accounting_proved_for_v3_claim":True,
        "reuse_basis":"IDENTICAL_WHOLE_LEAF_SCOPE_CLAIM_ID_AND_SCOPE_SHA256__PRIOR_C5_PROOF_REVERIFIED",
        "cc_r3_terminal_closure_proved":False,
        "stronger_material_defeater_totality_proved":False,
        "semantic_property_truth_authority":False,
        "quality_authority":False,"acceptance_authority":False,
        "promotion_authority":False,"terminal_authority":False,
        "property_truth_credit_delta":0,"terminal_credit_delta":0,
        "incremental_spend_usd":0,
        "next":"REUSE_CURRENT_R12_C2_C3_AND_V3_C5__ATTACK_R12C6_PROOF_SEARCH_HONESTY_THEN_C1_C4_C7_C8__DO_NOT_CLAIM_CC_R3_UNTIL_ALL_REQUIRED_CLAUSES_CLOSE",
    }

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root else ROOT
    pack=pack_v3.verify(repo_root=root)
    if pack.get("pass") is not True:
        return _fail("V3_PACK_VERIFY_FAILED",source_reason=pack.get("reason"))
    prior=c5.verify(repo_root=root)
    return evaluate(pack,prior)

if __name__=="__main__":
    print(json.dumps(verify(),indent=2,sort_keys=True))
