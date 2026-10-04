#!/usr/bin/env python3
"""Fail-closed acceptance reducer for Unknown-Domain V6.

This reducer grants exactly one atomic predicate and no family/capability/
ownership credit. It is intentionally incapable of inferring success from a
finite sample or from an unbound/mismatched verifier receipt.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_UNKNOWN_DOMAIN_V6_ACCEPTANCE_REDUCER_V1"
TARGET="UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
EXPECTED_RECEIPT_SCHEMA="PROJECT_BRAIN_UNKNOWN_DOMAIN_V6_INDEPENDENT_VERIFICATION_V1"
EXPECTED_RECEIPT_STATUS=(
    "PASS__CONTENT_BOUND_TOTAL_STRING_STRUCTURAL_ID_EXACT_FLOAT_"
    "AND_3888_CASE_FALSIFICATION__ZERO_REALITY"
)
EXPECTED_SUBJECT_BLOBS={
    "canonical/runtime/unknown_domain_direct_candidate_v1.py":"a2a77269a8175ce315b466035049da0f761b8734",
    "canonical/runtime/unknown_domain_direct_candidate_v2.py":"4470716f95a559a700e461262df909ae19a41651",
    "canonical/runtime/unknown_domain_direct_candidate_v3.py":"8df7f13455b710623806a8219174b397a2c3c442",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":"f974a4594c78e74693c7ba5a19f131dfa481b937",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":"d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v4.py":"e52858b9fef2d795f72b45cd3ae82ad04344aa91",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v5.py":"a97459fe407ea4852f57f12f504fbc0121db9824",
    "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
    "canonical/runtime/unknown_domain_direct_execution_harness_v1.py":"04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
    "canonical/tests/test_unknown_domain_direct_v5.py":"81cd6ecabec51029175f6036a13eac7667fccd03",
}
EXPECTED_PROOF_BLOB="58410966e17c1bc546db8cab039891f3ab2bf8a8"
EXPECTED_BINDINGS_BLOB="25bc947e9f4b71b46dff13405cf231602cdeff1f"


def git_blob(path:Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()


def _root()->Path:
    return Path(__file__).resolve().parents[2]


def reduce(receipt:Mapping[str,Any],root:Path|None=None)->dict[str,Any]:
    root=_root() if root is None else Path(root).resolve()
    checks:dict[str,bool]={}
    try:
        checks["receipt_schema"]=receipt.get("schema")==EXPECTED_RECEIPT_SCHEMA
        checks["receipt_status"]=receipt.get("status")==EXPECTED_RECEIPT_STATUS
        checks["target"]=receipt.get("target_predicate")==TARGET
        checks["subject_map"]=dict(receipt.get("exact_subject_blobs") or {})==EXPECTED_SUBJECT_BLOBS
        checks["surrogates"]=receipt.get("surrogate_codepoints_exhausted")==2048
        checks["forced_collision"]=receipt.get("forced_total_token_collision_survives") is True
        checks["falsification_cases"]=receipt.get("nonproduction_falsification_cases")==3888
        checks["zero_production"]=receipt.get("production_or_terminal_cases_generated")==0
        checks["zero_credit_in_verifier"]=receipt.get("acceptance_credit_delta")==0

        got_subject={rel:git_blob(root/rel) for rel in EXPECTED_SUBJECT_BLOBS}
        checks["canonical_subject_bytes"]=got_subject==EXPECTED_SUBJECT_BLOBS
        checks["canonical_v6_proof_byte"]=(
            git_blob(root/"canonical/runtime/unknown_domain_direct_v6_universal_proof_v1.py")
            == EXPECTED_PROOF_BLOB
        )
        checks["current_acceptance_binding_byte"]=(
            git_blob(root/"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
            == EXPECTED_BINDINGS_BLOB
        )
    except Exception as exc:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "target_predicate":TARGET,
            "error":type(exc).__name__+":"+str(exc),
            "checks":checks,
            "proved_predicate_count_delta":0,
            "unresolved_predicate_count_delta":0,
            "family_credit_delta":0,
            "capability_credit_delta":0,
            "ownership_credit_delta":0,
        }

    if not all(checks.values()):
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "target_predicate":TARGET,
            "checks":checks,
            "proved_predicate_count_delta":0,
            "unresolved_predicate_count_delta":0,
            "family_credit_delta":0,
            "capability_credit_delta":0,
            "ownership_credit_delta":0,
        }

    return {
        "schema":SCHEMA,
        "status":"PROVED",
        "target_predicate":TARGET,
        "proof_kind":"INDEPENDENT_CONTENT_BOUND_UNIVERSAL_FORMAL_SCOPE_PROOF",
        "checks":checks,
        "proved_predicate_count_delta":1,
        "unresolved_predicate_count_delta":-1,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "new_reality_units_consumed":0,
        "terminal_cases_consumed":0,
        "production_cases_generated":0,
    }


if __name__=="__main__":
    import sys
    receipt=json.load(sys.stdin)
    print(json.dumps(reduce(receipt),indent=2,sort_keys=True))
