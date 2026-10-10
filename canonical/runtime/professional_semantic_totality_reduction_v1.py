"""Fail-closed reuse reduction for professional semantic totality.

This module does not prove semantic property truth. It recognizes the current
twelve semantic leaves, preserves the bounded-witness/non-totality boundary,
and reduces their shared residual to claim-scoped totality instances using the
already-owned completeness architecture.

The domain defeater catalog is evidence input only. Enumeration, including a
future self-claim of catalog completeness, is never accepted as totality
authority by this reducer.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_TOTALITY_REDUCTION_V1"
LEDGER_PATH="canonical/governance/PROFESSIONAL_QUALITY_WHOLE_LEAF_RESIDUAL_LEDGER_20261010_V1.json"
CATALOG_PATH="canonical/governance/PROFESSIONAL_QUALITY_DOMAIN_DEFEATER_CATALOG_20261009_V2.json"
CLAIM_SCOPE_PATH="canonical/governance/COVERAGE_COMPLETENESS_CLAIM_SCOPE_V1.json"
ROOT_THEOREM_PATH="canonical/governance/COVERAGE_COMPLETENESS_ROOT_THEOREM_V1.json"
SCOPE_COMPILER_PATH="canonical/runtime/universal_scope_closure_compiler_v1.py"
SHARED_RESIDUAL="WHOLE_LEAF_INPUT_DOMAIN_TOTALITY_OR_INDEPENDENT_CERTIFIED_COMPLETE_UNION"
SEMANTIC_SUFFIX="::SEMANTIC"
EXPECTED_ROOTS=(
    "R1_TARGET_SPECIFICATION",
    "R2_CANDIDATE_SEARCH",
    "R3_REALIZATION_OBSERVATION",
    "R4_MEASUREMENT_CONSTRUCT",
    "R5_EVALUATOR_REFERENCE",
    "R6_EVIDENCE_GROUNDING_DEPENDENCE",
    "R7_CAUSAL_PRESCRIPTIVE",
    "R8_POPULATION_CONTEXT_OPERATOR",
    "R9_TEMPORAL_DEPLOYMENT",
    "R10_ANALYSIS_DECISION",
    "R11_ADAPTIVE_INTEGRITY_SECURITY",
    "R12_META_COMPOSITION_CLOSURE",
)
EXPECTED_LEAVES=frozenset(f"PQ::{root}::SEMANTIC" for root in EXPECTED_ROOTS)

def _fail(reason:str, **extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "pass":False,
        "status":"FAIL_CLOSED",
        "reason":reason,
        "semantic_leaf_count":0,
        "claim_scoped_instance_count":0,
        "shared_adapter_count":1,
        "catalog_enumeration_sufficient":False,
        "current_totality_proved":False,
        "property_truth_authority":False,
        "quality_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
        "new_primitive_required":False,
        **extra,
    }

def analyze(ledger:Mapping[str,Any], catalog:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(ledger,Mapping):
        return _fail("LEDGER_NOT_MAPPING")
    if not isinstance(catalog,Mapping):
        return _fail("CATALOG_NOT_MAPPING")
    if ledger.get("shared_residual_class")!=SHARED_RESIDUAL:
        return _fail("SHARED_RESIDUAL_CLASS_DRIFT")

    rows=ledger.get("leaves")
    if not isinstance(rows,list):
        return _fail("LEDGER_LEAVES_INVALID")
    semantic=[x for x in rows if isinstance(x,Mapping) and str(x.get("leaf_id","")).endswith(SEMANTIC_SUFFIX)]
    ids=[x.get("leaf_id") for x in semantic]
    if len(ids)!=12 or set(ids)!=EXPECTED_LEAVES or len(ids)!=len(set(ids)):
        return _fail("SEMANTIC_LEAF_SET_NOT_12",observed_leaf_ids=sorted(str(x) for x in ids))

    # The current catalog is explicitly non-complete. If that flag disappears,
    # enumeration still does not become proof authority merely by self-claim.
    hard=catalog.get("hard_nonclaims")
    if (
        not isinstance(hard,list)
        or "NO_CLAIM_DEFEATER_SET_COMPLETE" not in hard
        or catalog.get("closure_state")!="OPEN"
    ):
        return _fail("CATALOG_COMPLETENESS_SELF_CLAIM_NOT_AUTHORITY")

    out=[]
    for row in sorted(semantic,key=lambda x:str(x.get("leaf_id"))):
        leaf=str(row["leaf_id"])
        witnesses=row.get("bounded_witnesses")
        if not isinstance(witnesses,list) or not witnesses:
            return _fail("SEMANTIC_LEAF_BOUNDED_WITNESS_REQUIRED",leaf_id=leaf)
        if row.get("residual")!="PROVE_TOTALITY_OVER_ALL_ADMISSIBLE_LEAF_INPUTS_OR_BIND_INDEPENDENT_CERTIFIED_COMPLETE_UNION":
            return _fail("SEMANTIC_LEAF_RESIDUAL_DRIFT",leaf_id=leaf)
        for witness in witnesses:
            if not isinstance(witness,Mapping):
                return _fail("BOUNDED_WITNESS_INVALID",leaf_id=leaf)
            if witness.get("global_leaf_closure") is not False:
                return _fail("BOUNDED_WITNESS_GLOBAL_PROMOTION_FORBIDDEN",leaf_id=leaf)
            scope_id=witness.get("scope_id")
            receipt=witness.get("source_receipt")
            if not isinstance(scope_id,str) or not scope_id:
                return _fail("BOUNDED_WITNESS_SCOPE_ID_REQUIRED",leaf_id=leaf)
            if not isinstance(receipt,Mapping):
                return _fail("BOUNDED_WITNESS_RECEIPT_REQUIRED",leaf_id=leaf)
            if not isinstance(receipt.get("path"),str) or not isinstance(receipt.get("git_blob_sha"),str):
                return _fail("BOUNDED_WITNESS_RECEIPT_BINDING_INVALID",leaf_id=leaf)
        root=leaf[len("PQ::"):-len(SEMANTIC_SUFFIX)]
        out.append({
            "leaf_id":leaf,
            "root_id":root,
            "bounded_witness_scope_count":len(witnesses),
            "bounded_witness_scope_ids":[str(w["scope_id"]) for w in witnesses],
            "claim_scoped_totality_required":True,
            "required_route":"FROZEN_CLAIM_SCOPE__MISSION_SUFFICIENT_SEMANTIC_CARRIER__FOUR_ROOT_COVERAGE_CERTIFICATES__UNIVERSAL_SCOPE_TOTALITY_OR_CERTIFIED_COMPLETE_UNION",
            "catalog_role":"ADVERSARIAL_EVIDENCE_ONLY__NOT_COMPLETENESS_AUTHORITY",
            "current_totality_proved":False,
            "property_truth_authority":False,
        })

    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__TWELVE_SEMANTIC_LEAVES_REDUCED_TO_CLAIM_SCOPED_TOTALITY_INSTANCES__ZERO_PROPERTY_TRUTH_CREDIT",
        "semantic_leaf_count":12,
        "claim_scoped_instance_count":12,
        "shared_adapter_count":1,
        "shared_residual_class":SHARED_RESIDUAL,
        "shared_reuse_stack":{
            "claim_scope":CLAIM_SCOPE_PATH,
            "coverage_root_theorem":ROOT_THEOREM_PATH,
            "scope_compiler":SCOPE_COMPILER_PATH,
        },
        "catalog_enumeration_sufficient":False,
        "current_totality_proved":False,
        "property_truth_authority":False,
        "quality_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
        "new_primitive_required":False,
        "next":"INSTANTIATE_ONE_CONTENT_ADDRESSED_CLAIM_SCOPED_TOTALITY_CERTIFICATE_PER_SEMANTIC_LEAF__REUSE_ONE_SHARED_ADAPTER__DO_NOT_EXPAND_DEFEATER_CATALOG_AS_COMPLETENESS_PROOF",
        "leaves":out,
    }
