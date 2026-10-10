"""Compose verified scope-complete acceptance evidence into Escape Gap A V3 terminal-policy row proofs.

This module is an inference adapter, not an authority source. It composes:
1) the existing acceptance proof transmuter, which proves full frozen-scope
   acceptance from stronger target-free evidence; and
2) a separately independently verified exact-byte binding for the currently
   available Brain-owned policy that the protocol names.

It never grants execution, promotion, acceptance, capability, ownership, or
terminal credit.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime.acceptance_proof_transmuter_v1 import evaluate as transmute

SCHEMA="PROJECT_BRAIN_ESCAPE_PROGRESS_TERMINAL_COMMON_POLICY_COMPILER_V1"
GAP_A="GAP_A_ACQUISITION_TOTALITY"
POLICY_BINDING_SCHEMA="PROJECT_BRAIN_ESCAPE_PROGRESS_COMMON_POLICY_BINDING_V1"
TARGET_FREE_MODES=frozenset({"UNIVERSAL","EXHAUSTIVE_FINITE","ABSOLUTE_DOMINANCE"})


def _canon(value: Any) -> bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _hex(value: Any,n: int) -> bool:
    return isinstance(value,str) and len(value)==n and all(c in "0123456789abcdef" for c in value)


def _fail(reason: str, **extra: Any) -> dict[str,Any]:
    return {
        "schema":SCHEMA,
        "pass":False,
        "status":"FAIL_CLOSED",
        "reason":reason,
        "row_proof":None,
        "execution_authority":False,
        "promotion_authority":False,
        "acceptance_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "terminal_credit_delta":0,
        **extra,
    }


def compile_candidate(
    row: Mapping[str,Any],
    protocol: Mapping[str,Any],
    evidence: Mapping[str,Any],
    policy_binding: Mapping[str,Any],
) -> dict[str,Any]:
    if not all(isinstance(x,Mapping) for x in (row,protocol,evidence,policy_binding)):
        return _fail("MAPPING_INPUTS_REQUIRED")

    oid=str(row.get("obligation_id") or "")
    if not oid:
        return _fail("OBLIGATION_ID_REQUIRED")
    if row.get("route_group")!=GAP_A:
        return _fail("GAP_A_ROW_REQUIRED")
    if protocol.get("family")!=oid or evidence.get("family")!=oid or policy_binding.get("obligation_id")!=oid:
        return _fail("OBLIGATION_PROTOCOL_EVIDENCE_POLICY_BINDING_MISMATCH")

    if policy_binding.get("schema")!=POLICY_BINDING_SCHEMA:
        return _fail("POLICY_BINDING_SCHEMA_INVALID")
    if policy_binding.get("independently_verified") is not True:
        return _fail("POLICY_BINDING_NOT_INDEPENDENTLY_VERIFIED")
    if policy_binding.get("exact_byte_bound") is not True:
        return _fail("POLICY_BINDING_NOT_EXACT_BYTE_BOUND")
    receipt_path=policy_binding.get("verification_receipt_path")
    if not isinstance(receipt_path,str) or not receipt_path.startswith("canonical/verification/"):
        return _fail("POLICY_BINDING_VERIFICATION_RECEIPT_PATH_INVALID")
    if not _hex(policy_binding.get("verification_receipt_git_blob_sha"),40):
        return _fail("POLICY_BINDING_VERIFICATION_RECEIPT_BLOB_INVALID")

    policy_id=policy_binding.get("common_policy_id")
    if not isinstance(policy_id,str) or not policy_id:
        return _fail("COMMON_POLICY_ID_REQUIRED")
    if protocol.get("common_policy_id")!=policy_id:
        return _fail("COMMON_POLICY_ID_BINDING_MISMATCH")
    if policy_binding.get("currently_available") is not True:
        return _fail("COMMON_POLICY_CURRENT_AVAILABILITY_NOT_PROVED")
    if policy_binding.get("brain_owned") is not True:
        return _fail("COMMON_POLICY_BRAIN_OWNERSHIP_NOT_PROVED")
    if policy_binding.get("resource_admissible") is not True:
        return _fail("COMMON_POLICY_RESOURCE_ADMISSIBILITY_NOT_PROVED")

    mode=evidence.get("mode")
    if mode not in TARGET_FREE_MODES:
        return _fail("TARGET_FREE_SCOPE_COMPLETE_MODE_REQUIRED")
    if evidence.get("safe") is not True:
        return _fail("REGION_WIDE_SAFETY_PROOF_REQUIRED")

    verdict=transmute({"protocols":[dict(protocol)]},{"evidence":[dict(evidence)]})
    families=verdict.get("families")
    if verdict.get("status")!="PASS" or not isinstance(families,list) or len(families)!=1:
        return _fail("ACCEPTANCE_TRANSMUTER_FAIL_CLOSED",transmuter_result=verdict)
    family=families[0]
    if (
        family.get("family")!=oid
        or family.get("result_status")!="PASS"
        or family.get("closure_mode")!=mode
    ):
        return _fail("SCOPE_COMPLETE_ACCEPTANCE_NOT_PROVED",transmuter_result=verdict)

    proof={
        "obligation_id":oid,
        "route_group":GAP_A,
        "resolution_mode":"TERMINAL_COMMON_POLICY",
        "currently_available":True,
        "common_policy_id":policy_id,
        "authenticated_scope_complete_certificate":True,
        "brain_owned":True,
        "adequate_over_entire_current_decision_region":True,
        "safe_over_entire_current_decision_region":True,
        "resource_admissible":True,
        "certificate_mode":mode,
        "acceptance_witness_id":family.get("witness_id"),
        "acceptance_witness_reason":family.get("witness_reason"),
        "policy_binding_sha256":_sha(policy_binding),
        "protocol_sha256":_sha(protocol),
        "evidence_sha256":_sha(evidence),
        "transmuter_result_sha256":_sha(verdict),
        "policy_binding_verification_receipt_path":receipt_path,
        "policy_binding_verification_receipt_git_blob_sha":policy_binding["verification_receipt_git_blob_sha"],
    }
    proof["proof_sha256"]=_sha(proof)
    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__V3_TERMINAL_COMMON_POLICY_ROW_PROOF_COMPOSED",
        "obligation_id":oid,
        "row_proof":proof,
        "composed_from_independent_premises":True,
        "execution_authority":False,
        "promotion_authority":False,
        "acceptance_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "terminal_credit_delta":0,
        "boundary":"PROOF_COMPOSITION_ONLY__CURRENT_ROW_CLOSURE_REMAINS_SUBJECT_TO_V3_AUDIT_AND_GOVERNED_ROW_PROOF_BINDING",
    }
