"""Fail-closed bridge from 12 behavioral terminal contracts to 19 family accounting rows.

The Opus-family rows are accounting labels; the behavioral contract registry is
the measurable semantic basis. Prewave evaluation proves only structural
sufficiency: every open family maps to active contracts, every active contract is
load-bearing in at least one family, and the independently verified V6
dominance proof deletes named benchmark surfaces as mandatory execution routes
without inheriting their scores.

Postwave reduction consumes an already-normalized 12-contract terminal verdict
set. It derives provisional family verdicts but grants zero family credit.
Donor-deletion, contamination, resource/authority, acceptance, and proof-bundle
postconditions remain the responsibility of the terminal closure manifest and
its independently verified closure reducer.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_TERMINAL_FAMILY_ADJUDICATION_REDUCER_V1"
PREWAVE_SCHEMA="PROJECT_BRAIN_TERMINAL_FAMILY_PREWAVE_SUFFICIENCY_V1"
RESULT_SCHEMA="PROJECT_BRAIN_TERMINAL_FAMILY_VERDICT_SET_V1"

REGISTRY="canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
BASIS="canonical/governance/ACTIVE_TERMINAL_PROOF_BASIS_V1.json"
PROTOCOLS="canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
CLOSURE="canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json"
DOMINANCE="canonical/governance/GLOBAL_TERMINAL_SURFACE_DOMINANCE_INPUT_V6.json"
DOMINANCE_RECEIPT="canonical/verification/GLOBAL_TERMINAL_SURFACE_DOMINANCE_V6_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"

REQUIRED_CONTRACT_FIELDS=(
    "behavior_id","source","inputs","environment_state","allowed_information",
    "required_output_or_action","success_condition","failure_condition",
    "terminal_consequence","verification_route","dependency_boundary","scope",
)


def _blob(root:Path, rel:str)->str:
    data=(root/rel).read_bytes()
    header=b"blob "+str(len(data)).encode()+bytes([0])
    return hashlib.sha1(header+data).hexdigest()


def _load(root:Path, rel:str)->dict[str,Any]:
    obj=json.loads((root/rel).read_text(encoding="utf-8"))
    if not isinstance(obj,dict):
        raise ValueError(rel+":NOT_OBJECT")
    return obj


def _fail(errors:list[str])->dict[str,Any]:
    return {
        "schema":PREWAVE_SCHEMA,
        "status":"FAIL_CLOSED",
        "pass":False,
        "family_adjudication_ready":False,
        "terminal_wave_structurally_sufficient_for_family_adjudication":False,
        "errors":sorted(set(errors)),
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }


def evaluate_documents(
    registry:Mapping[str,Any],
    basis:Mapping[str,Any],
    protocols:Mapping[str,Any],
    closure:Mapping[str,Any],
    dominance:Mapping[str,Any],
    dominance_receipt:Mapping[str,Any],
    *,
    current_blobs:Mapping[str,str],
)->dict[str,Any]:
    errors:list[str]=[]

    active_rows=registry.get("active_contracted_residuals")
    fmap=registry.get("family_to_residual_contracts")
    if not isinstance(active_rows,list) or not isinstance(fmap,Mapping):
        return _fail(["REGISTRY_STRUCTURE_INVALID"])

    active_ids:list[str]=[]
    for i,row in enumerate(active_rows):
        if not isinstance(row,Mapping):
            errors.append(f"ACTIVE_CONTRACT_NOT_OBJECT:{i}"); continue
        bid=row.get("behavior_id")
        if not isinstance(bid,str) or not bid:
            errors.append(f"ACTIVE_CONTRACT_ID_INVALID:{i}"); continue
        if bid in active_ids:
            errors.append("ACTIVE_CONTRACT_DUPLICATE:"+bid); continue
        active_ids.append(bid)
        missing=[k for k in REQUIRED_CONTRACT_FIELDS if not row.get(k)]
        if missing:
            errors.append("ACTIVE_CONTRACT_FIELDS_MISSING:"+bid+":"+",".join(missing))
    active=set(active_ids)
    if len(active)!=12:
        errors.append(f"ACTIVE_CONTRACT_COUNT_NOT_12:{len(active)}")

    basis_rows=basis.get("contracts")
    if not isinstance(basis_rows,list):
        errors.append("BASIS_CONTRACTS_INVALID")
        basis_ids=set()
    else:
        basis_ids=set()
        for row in basis_rows:
            if not isinstance(row,Mapping) or not isinstance(row.get("behavior_id"),str):
                errors.append("BASIS_ROW_INVALID"); continue
            bid=row["behavior_id"]; basis_ids.add(bid)
            if row.get("proof_state")!="TERMINAL_ROUTE_FROZEN_ADMISSIBLE":
                errors.append("BASIS_ROUTE_NOT_ADMISSIBLE:"+bid)
            if row.get("blockers") != []:
                errors.append("BASIS_ROUTE_HAS_BLOCKERS:"+bid)
    if basis_ids != active:
        errors.append("BASIS_ACTIVE_SET_MISMATCH")

    prows=protocols.get("protocols")
    crows=closure.get("families")
    if not isinstance(prows,list) or not isinstance(crows,list):
        errors.append("FAMILY_INPUTS_INVALID")
        prows=[]; crows=[]
    pmap={r.get("family"):r for r in prows if isinstance(r,Mapping) and isinstance(r.get("family"),str)}
    cmap={r.get("id"):r for r in crows if isinstance(r,Mapping) and isinstance(r.get("id"),str)}
    if len(pmap)!=19 or len(cmap)!=19 or set(pmap)!=set(cmap):
        errors.append("FAMILY_SET_NOT_EXACT_19")

    preexisting={fid for fid,row in pmap.items() if row.get("status")=="PASS"}
    closure_preexisting={fid for fid,row in cmap.items() if row.get("closure_state")=="PASS"}
    if preexisting != closure_preexisting:
        errors.append("PREEXISTING_PASS_FAMILY_MISMATCH")
    open_families=set(pmap)-preexisting
    if set(fmap) != open_families:
        errors.append(
            "FAMILY_MAPPING_SET_MISMATCH:missing="+",".join(sorted(open_families-set(fmap)))
            +";extra="+",".join(sorted(set(fmap)-open_families))
        )

    referenced:set[str]=set()
    family_contracts:dict[str,list[str]]={}
    for family in sorted(open_families):
        rows=fmap.get(family)
        if not isinstance(rows,list) or not rows or any(not isinstance(x,str) or not x for x in rows):
            errors.append("FAMILY_MAPPING_INVALID:"+family); continue
        if len(set(rows)) != len(rows):
            errors.append("FAMILY_MAPPING_DUPLICATE:"+family)
        unknown=sorted(set(rows)-active)
        if unknown:
            errors.append("FAMILY_MAPPING_UNKNOWN_CONTRACT:"+family+":"+",".join(unknown))
        referenced.update(x for x in rows if x in active)
        family_contracts[family]=list(rows)
    orphan=sorted(active-referenced)
    if orphan:
        errors.append("ORPHAN_ACTIVE_CONTRACTS:"+",".join(orphan))

    if dominance.get("schema")!="PROJECT_BRAIN_GLOBAL_TERMINAL_SURFACE_DOMINANCE_INPUT_V6":
        errors.append("DOMINANCE_SCHEMA_NOT_V6")
    obligations=dominance.get("obligations")
    if not isinstance(obligations,list):
        errors.append("DOMINANCE_OBLIGATIONS_INVALID")
        dids=set()
    else:
        dids={r.get("id") for r in obligations if isinstance(r,Mapping) and isinstance(r.get("id"),str)}
        if dids != active:
            errors.append("DOMINANCE_OBLIGATION_SET_MISMATCH")

    authority=dominance.get("authority")
    if not isinstance(authority,Mapping):
        errors.append("DOMINANCE_AUTHORITY_INVALID")
    else:
        rr=authority.get("behavioral_contract_registry")
        bb=authority.get("active_terminal_proof_basis")
        if not isinstance(rr,Mapping) or rr.get("blob_sha") != current_blobs.get(REGISTRY):
            errors.append("DOMINANCE_REGISTRY_BLOB_NOT_CURRENT")
        if not isinstance(bb,Mapping) or bb.get("blob_sha") != current_blobs.get(BASIS):
            errors.append("DOMINANCE_BASIS_BLOB_NOT_CURRENT")

    smap=dominance.get("surface_family_mapping")
    if not isinstance(smap,list):
        errors.append("SURFACE_FAMILY_MAPPING_INVALID")
    else:
        for i,row in enumerate(smap):
            if not isinstance(row,Mapping):
                errors.append(f"SURFACE_MAPPING_ROW_INVALID:{i}"); continue
            family=row.get("represented_family"); contracts=row.get("contracts")
            if family not in open_families or not isinstance(contracts,list):
                errors.append(f"SURFACE_MAPPING_INVALID:{i}"); continue
            allowed=set(family_contracts.get(family,[]))
            extra=sorted(set(contracts)-allowed)
            if extra:
                errors.append("SURFACE_MAPPING_EXCEEDS_FAMILY_CONTRACTS:"+family+":"+",".join(extra))

    status=str(dominance_receipt.get("status",""))
    if "INDEPENDENT_PUBLIC_RUNNER_PASS" not in status or "V6" not in status:
        errors.append("DOMINANCE_RECEIPT_NOT_CURRENT_INDEPENDENT_V6_PASS")
    exact=dominance_receipt.get("exact_brain_blobs")
    if not isinstance(exact,Mapping):
        errors.append("DOMINANCE_RECEIPT_EXACT_BLOBS_MISSING")
    else:
        if exact.get(DOMINANCE) != current_blobs.get(DOMINANCE):
            errors.append("DOMINANCE_RECEIPT_INPUT_BLOB_NOT_CURRENT")
        compiler="canonical/runtime/proof_route_dominance.py"
        if exact.get(compiler) != current_blobs.get(compiler):
            errors.append("DOMINANCE_RECEIPT_COMPILER_BLOB_NOT_CURRENT")
    verified=dominance_receipt.get("verified")
    if not isinstance(verified,list):
        verified=[]
    for required in (
        "DOMINANCE_STATUS_COMPLETE",
        "GLOBAL_UNCOVERED_BEHAVIORAL_OBLIGATIONS_ZERO",
        "ALL_14_NAMED_SURFACES_REDUNDANT",
        "ZERO_TERMINAL_CASES_CONSUMED",
    ):
        if required not in verified:
            errors.append("DOMINANCE_RECEIPT_MISSING_ASSERTION:"+required)
    if dominance_receipt.get("terminal_results_observed",0)!=0:
        errors.append("DOMINANCE_RECEIPT_TERMINAL_RESULTS_NONZERO")
    if dominance_receipt.get("fresh_terminal_evidence_consumed",0)!=0:
        errors.append("DOMINANCE_RECEIPT_FRESH_EVIDENCE_NONZERO")

    if errors:
        return _fail(errors)

    return {
        "schema":PREWAVE_SCHEMA,
        "status":"PASS__12_OF_12_CONTRACTS_LOAD_BEARING__19_FAMILY_ACCOUNTING_STRUCTURALLY_CLOSED__ZERO_TERMINAL_RESULTS",
        "pass":True,
        "family_adjudication_ready":True,
        "terminal_wave_structurally_sufficient_for_family_adjudication":True,
        "active_contract_count":12,
        "mapped_open_family_count":len(open_families),
        "preexisting_pass_family_count":len(preexisting),
        "terminal_family_count":19,
        "orphan_active_contracts":[],
        "family_to_contracts":family_contracts,
        "preexisting_pass_families":sorted(preexisting),
        "errors":[],
        "rule":(
            "FAMILY_ROWS_ARE_ACCOUNTING_LABELS_OVER_CURRENT_MEASURABLE_BEHAVIORAL_CONTRACTS__"
            "V6_DOMINANCE_DELETES_NAMED_SURFACES_AS_REQUIRED_EXECUTION_ROUTES_WITHOUT_SCORE_INHERITANCE__"
            "TERMINAL_CONTRACT_RESULTS_MAY_ADJUDICATE_FAMILIES_ONLY_AFTER_ONE_SHOT_WAVE__"
            "GLOBAL_DONOR_CONTAMINATION_RESOURCE_AND_PROOF_BUNDLE_POSTCONDITIONS_REMAIN_SEPARATE"
        ),
        "terminal_results_observed":0,
        "fresh_terminal_evidence_consumed":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }


def evaluate(root:Path=Path("."))->dict[str,Any]:
    try:
        docs={
            REGISTRY:_load(root,REGISTRY),
            BASIS:_load(root,BASIS),
            PROTOCOLS:_load(root,PROTOCOLS),
            CLOSURE:_load(root,CLOSURE),
            DOMINANCE:_load(root,DOMINANCE),
            DOMINANCE_RECEIPT:_load(root,DOMINANCE_RECEIPT),
        }
        current={
            REGISTRY:_blob(root,REGISTRY),
            BASIS:_blob(root,BASIS),
            DOMINANCE:_blob(root,DOMINANCE),
            "canonical/runtime/proof_route_dominance.py":_blob(root,"canonical/runtime/proof_route_dominance.py"),
        }
    except (OSError,ValueError,json.JSONDecodeError) as exc:
        return _fail(["INPUT_READ_FAILURE:"+type(exc).__name__])
    return evaluate_documents(
        docs[REGISTRY],docs[BASIS],docs[PROTOCOLS],docs[CLOSURE],
        docs[DOMINANCE],docs[DOMINANCE_RECEIPT],current_blobs=current,
    )


def reduce_family_verdicts(
    normalized_contracts:Mapping[str,Any],
    registry:Mapping[str,Any],
    protocols:Mapping[str,Any],
    closure:Mapping[str,Any],
)->dict[str,Any]:
    errors:list[str]=[]
    if not isinstance(normalized_contracts,Mapping) or normalized_contracts.get("valid") is not True:
        return {
            "schema":RESULT_SCHEMA,"status":"FAIL_CLOSED_INVALID_CONTRACT_VERDICT_SET",
            "valid":False,"errors":["NORMALIZED_CONTRACT_VERDICTS_NOT_VALID"],
            "family_verdicts":{},"all_families_pass":False,
            "capability_credit_delta":0,"family_credit_delta":0,
        }
    if normalized_contracts.get("terminal_result") is not True or normalized_contracts.get("contract_count")!=12:
        errors.append("NORMALIZED_TERMINAL_RESULT_NOT_EXACT_12")
    verdicts=normalized_contracts.get("contract_verdicts")
    if not isinstance(verdicts,Mapping):
        errors.append("CONTRACT_VERDICTS_NOT_MAPPING"); verdicts={}

    fmap=registry.get("family_to_residual_contracts")
    prows=protocols.get("protocols")
    crows=closure.get("families")
    if not isinstance(fmap,Mapping) or not isinstance(prows,list) or not isinstance(crows,list):
        errors.append("FAMILY_ACCOUNTING_INPUT_INVALID")
        fmap={}; prows=[]; crows=[]
    pmap={r.get("family"):r for r in prows if isinstance(r,Mapping) and isinstance(r.get("family"),str)}
    cmap={r.get("id"):r for r in crows if isinstance(r,Mapping) and isinstance(r.get("id"),str)}
    if set(pmap)!=set(cmap) or len(pmap)!=19:
        errors.append("FAMILY_SET_NOT_EXACT_19")

    out:dict[str,Any]={}
    for family in sorted(pmap):
        if pmap[family].get("status")=="PASS":
            if cmap.get(family,{}).get("closure_state")!="PASS":
                errors.append("PREEXISTING_PASS_NOT_CLOSED:"+family)
                continue
            out[family]={
                "family":family,"status":"PASS","pass":True,
                "basis":"PREEXISTING_VERIFIED_PASS","required_contracts":[],
            }
            continue

        required=fmap.get(family)
        if not isinstance(required,list) or not required:
            errors.append("OPEN_FAMILY_MAPPING_MISSING:"+family); continue
        missing=[bid for bid in required if bid not in verdicts]
        if missing:
            errors.append("FAMILY_CONTRACT_RESULTS_MISSING:"+family+":"+",".join(sorted(missing)))
            continue
        rows=[verdicts[bid] for bid in required]
        if any(not isinstance(r,Mapping) or r.get("terminal_result") is not True for r in rows):
            errors.append("FAMILY_NONTERMINAL_CONTRACT_RESULT:"+family); continue
        passed=all(r.get("pass") is True for r in rows)
        out[family]={
            "family":family,
            "status":"PASS" if passed else "FAIL",
            "pass":passed,
            "basis":"CONJUNCTION_OF_MAPPED_TERMINAL_BEHAVIORAL_CONTRACTS",
            "required_contracts":list(required),
            "failed_contracts":[bid for bid in required if verdicts[bid].get("pass") is not True],
            "protocol_mode":pmap[family].get("proof_mode"),
        }

    if errors or len(out)!=19:
        return {
            "schema":RESULT_SCHEMA,"status":"FAIL_CLOSED_INVALID_FAMILY_ADJUDICATION",
            "valid":False,"errors":sorted(set(errors)),
            "family_verdicts":out,"all_families_pass":False,
            "capability_credit_delta":0,"family_credit_delta":0,
        }

    all_pass=all(r["pass"] is True for r in out.values())
    return {
        "schema":RESULT_SCHEMA,
        "status":"VALID_FAMILY_VERDICT_SET",
        "valid":True,
        "family_verdicts":out,
        "family_count":19,
        "family_pass_count":sum(1 for r in out.values() if r["pass"] is True),
        "all_families_pass":all_pass,
        "candidate_package_commitment":normalized_contracts.get("candidate_package_commitment"),
        "post_freeze_beacon":normalized_contracts.get("post_freeze_beacon"),
        "terminal_result":True,
        "global_ownership_postconditions_still_required":[
            "DONOR_DEPENDENT_REQUIRED_BEHAVIORS_ZERO",
            "UNRESOLVED_VERIFIER_MUTATIONS_ZERO",
            "UNRESOLVED_COMPOSITION_FAILURES_ZERO",
            "CONTAMINATED_PROMOTION_EVIDENCE_ZERO",
            "RESOURCE_OR_AUTHORITY_VIOLATIONS_ZERO",
            "FINAL_DONOR_DELETION_CLEANROOM_PASS",
            "PROOF_BUNDLE_FROZEN",
        ],
        "rule":"FAMILY_PASS_IS_PROVISIONAL_BEHAVIORAL_ADJUDICATION__CANONICAL_TERMINAL_OWNERSHIP_REQUIRES_GLOBAL_CLOSURE_REDUCER_PASS",
        "capability_credit_delta":0,
        "family_credit_delta":0,
    }
