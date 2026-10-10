"""Fail-closed falsifier for current R10 property-truth sufficiency.

This module does not prove an R10 execution failure. It proves a narrower and
load-bearing fact: the current property-truth evidence is insufficient whenever
the whole admissible domain is claimed, enforcement is conditional on externally
supplied detection signals, and no independently verified observation-to-defeater
totality certificate is bound.

The countermodel is epistemic: two admissible latent worlds can induce the same
guard-visible detection inputs while differing on whether a material
false-certification defeater exists. If the current evidence does not rule that
pair out, enforcement-after-detection cannot imply detection completeness.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R10_DETECTION_COMPLETENESS_FALSIFIER_V1"
LEAF_ID="PQ::R10_ANALYSIS_DECISION::EXECUTION"
CLAIM_ID="205a864e7d7a56a14a46bb75923cc9b11126d479676d26d88803831da1197294"
GUARD_ENTRYPOINT="evaluate"
DETECTION_PARAMETERS=frozenset({
    "detected_defeater_ids",
    "near_miss_signals",
    "unmapped_material_false_certification_defeater",
})
TOTALITY_SCHEMA="PROJECT_BRAIN_R10_OBSERVATION_TO_DEFEATER_TOTALITY_CERTIFICATE_V1"
TOTALITY_VERIFY_SCHEMA="PROJECT_BRAIN_R10_OBSERVATION_TO_DEFEATER_TOTALITY_INDEPENDENT_VERIFY_V1"


def _base(status:str,passed:bool)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":status,
        "pass":passed,
        "leaf_id":LEAF_ID,
        "claim_id":CLAIM_ID,
        "property_truth_proved":False,
        "detection_completeness_proved":False,
        "quality_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }


def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {**_base("FAIL_CLOSED",False),"reason":reason,**extra}


def _guard_detection_inputs(path:Path)->set[str]:
    tree=ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
    for node in tree.body:
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name==GUARD_ENTRYPOINT:
            return {a.arg for a in (*node.args.posonlyargs,*node.args.args,*node.args.kwonlyargs)}
    return set()


def _totality_bound(
    certificate:Mapping[str,Any]|None,
    verification:Mapping[str,Any]|None,
)->bool:
    if not isinstance(certificate,Mapping) or not isinstance(verification,Mapping):
        return False
    if certificate.get("schema")!=TOTALITY_SCHEMA:
        return False
    if certificate.get("leaf_id")!=LEAF_ID or certificate.get("claim_id")!=CLAIM_ID:
        return False
    if certificate.get("all_material_false_certification_states_observable_or_safe") is not True:
        return False
    if verification.get("schema")!=TOTALITY_VERIFY_SCHEMA:
        return False
    if verification.get("leaf_id")!=LEAF_ID or verification.get("claim_id")!=CLAIM_ID:
        return False
    if verification.get("pass") is not True or verification.get("independent") is not True:
        return False
    if verification.get("semantic_totality_verified") is not True:
        return False
    return True


def evaluate(
    *,
    guard_path:str|Path,
    whole_leaf_scope_verification:Mapping[str,Any],
    enforcement_verification:Mapping[str,Any],
    totality_certificate:Mapping[str,Any]|None=None,
    totality_verification:Mapping[str,Any]|None=None,
)->dict[str,Any]:
    scope=whole_leaf_scope_verification
    if scope.get("leaf_id")!=LEAF_ID or scope.get("claim_id")!=CLAIM_ID:
        return _fail("WHOLE_LEAF_SCOPE_IDENTITY_MISMATCH")
    consequence=scope.get("consequence")
    if not isinstance(consequence,Mapping):
        return _fail("WHOLE_LEAF_SCOPE_CONSEQUENCE_INVALID")
    if consequence.get("whole_leaf_domain_equivalence_proved") is not True:
        return _fail("WHOLE_LEAF_DOMAIN_EQUIVALENCE_REQUIRED")
    if consequence.get("whole_leaf_scope_complete") is not True:
        return _fail("WHOLE_LEAF_SCOPE_COMPLETE_REQUIRED")

    enforcement=enforcement_verification
    if enforcement.get("leaf_id")!=LEAF_ID or enforcement.get("claim_id")!=CLAIM_ID:
        return _fail("ENFORCEMENT_IDENTITY_MISMATCH")
    if enforcement.get("leaf_property_truth_authority") is not False:
        return _fail("ENFORCEMENT_RECEIPT_SELF_PROPERTY_AUTHORITY_FORBIDDEN")
    residual=enforcement.get("open_residual")
    if not isinstance(residual,Mapping):
        return _fail("ENFORCEMENT_OPEN_RESIDUAL_REQUIRED")
    if residual.get("detection_completeness_proved") is not False:
        return _fail("ENFORCEMENT_DETECTION_COMPLETENESS_STATE_UNEXPECTED")

    p=Path(guard_path)
    if not p.is_file():
        return _fail("GUARD_FILE_MISSING")
    try:
        params=_guard_detection_inputs(p)
    except Exception as exc:
        return _fail("GUARD_AST_INVALID",error=type(exc).__name__)
    missing=sorted(DETECTION_PARAMETERS-params)
    if missing:
        return _fail("GUARD_DETECTION_INTERFACE_DRIFT",missing_parameters=missing)

    if _totality_bound(totality_certificate,totality_verification):
        return {
            **_base("NOT_FALSIFIED__INDEPENDENT_DETECTION_TOTALITY_BOUND",False),
            "falsified":False,
            "required_next":"RERUN_PROPERTY_TRUTH_WITH_BOUND_TOTALITY_CERTIFICATE",
        }

    witness={
        "world_0":{
            "latent_material_false_certification_defeater":False,
            "guard_visible_detected_defeater_ids":[],
            "guard_visible_near_miss_signals":{},
            "guard_visible_unmapped_material_false_certification_defeater":False,
        },
        "world_1":{
            "latent_material_false_certification_defeater":True,
            "guard_visible_detected_defeater_ids":[],
            "guard_visible_near_miss_signals":{},
            "guard_visible_unmapped_material_false_certification_defeater":False,
        },
        "same_guard_visible_observation":True,
        "different_property_truth":True,
        "current_evidence_excludes_world_1":False,
    }
    return {
        **_base("FALSIFIED__CURRENT_R10_PROPERTY_TRUTH_PROOF_INSUFFICIENT",True),
        "falsified":True,
        "countermodel_kind":"OBSERVATIONALLY_INDISTINGUISHABLE_LATENT_DEFEATER_PAIR",
        "countermodel":witness,
        "reason":"ENFORCEMENT_AFTER_DETECTION_DOES_NOT_PROVE_DETECTION_TOTALITY",
        "exact_missing_certificate":"R10_OBSERVATION_TO_DEFEATER_TOTALITY_CERTIFICATE",
        "minimum_required_semantics":[
            "EVERY_MATERIAL_FALSE_CERTIFICATION_STATE_IN_THE_EXACT_WHOLE_LEAF_DOMAIN_IS_EITHER_OBSERVABLY_MAPPED_TO_A_BLOCKING_OR_ESCALATING_SIGNAL_OR_PROVED_DECISION_IRRELEVANT_SAFE",
            "OBSERVATION_CHANNEL_AND_MAPPING_ARE_BOUND_TO_EXACT_BYTES_OR_AUTHENTICATED_EXTERNAL_EVIDENCE",
            "UNKNOWN_OR_UNMAPPED_MATERIAL_STATES_CANNOT_SILENTLY_ENTER_THE_CLEAN_CERTIFICATE_PATH",
            "INDEPENDENT_VERIFICATION_BINDS_THE_SAME_CLAIM_AND_LEAF",
        ],
        "new_primitive_required":False,
        "reuse_candidates":[
            "COVERAGE_COMPLETENESS_ROOT_CERTIFICATES",
            "EFFECT_BROKER_RECEIPT_RESOLVER_V2",
            "MINIMUM_POLICY_CHANGING_INFORMATION_ROUTING",
            "PROFESSIONAL_DOMAIN_DEFEATER_CATALOG",
        ],
    }
