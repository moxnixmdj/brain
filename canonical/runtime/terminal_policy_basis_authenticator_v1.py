"""Authenticate a complete positive policy basis over the bound behavioral registry.

This composes the existing structural contract/extension gates with the existing
Project Brain policy-adequacy certificate protocol. A pass means every behavior
in the exact bound registry has one selected policy with:
  * a structurally complete policy manifest,
  * all current ABC extension membership bound,
  * a content-addressed Brain-owned adequacy certificate for the exact condition,
  * a content-addressed independent verification receipt for that certificate.

It deliberately does not infer universal target-trace coverage, U-empty, ABC
closure, D finality, or terminal success from registry closure alone.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from canonical.runtime.effect_broker_receipt_resolver_v2 import resolve_receipt_bytes
from canonical.runtime.adequacy_basis_structural_completeness_gate_v1 import verify_policy_manifest
from canonical.runtime.behavioral_contract_extension_gate_v1 import verify_abc_extension_admission

SCHEMA="PROJECT_BRAIN_TERMINAL_POLICY_BASIS_AUTHENTICATOR_V2"
ADEQUACY_SCHEMA="PROJECT_BRAIN_POLICY_ADEQUACY_CERTIFICATE_V1"
VERIFY_SCHEMA="PROJECT_BRAIN_POLICY_ADEQUACY_INDEPENDENT_VERIFICATION_V1"
CLOSURE_FIELDS={
    "behavior_id","selected_policy_id","policy_manifest_ref","policy_condition",
    "adequacy_certificate_ref","adequacy_verification_ref","abc_extension_atom_ids",
}

def _canon(x:Any)->str:
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def _condition_sha256(x:Mapping[str,Any])->str:
    return sha256(_canon(x).encode("utf-8")).hexdigest()

def _base(**more:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED",
        "all_current_registry_behavior_edges_authenticated":False,
        "u_empty_authorized":False,"abc_closed_authorized":False,
        "terminal_authority":False,"terminal_credit_delta":0,**more,
    }

def _resolve(ref:Any,root:Path):
    if not isinstance(ref,Mapping): raise ValueError("REFERENCE_REQUIRED")
    return resolve_receipt_bytes(ref,repo_root=root)

def evaluate(payload:Mapping[str,Any],*,repo_root:str|Path)->dict[str,Any]:
    if not isinstance(payload,Mapping): return _base(reason="PAYLOAD_MAPPING_REQUIRED")
    try:
        root=Path(repo_root).resolve(strict=True)
        registry_bound=_resolve(payload.get("registry_ref"),root)
        schema_bound=_resolve(payload.get("contract_schema_ref"),root)
    except Exception as exc:
        return _base(reason="REGISTRY_OR_SCHEMA_BINDING_INVALID",
                     exception_type=type(exc).__name__,detail=str(exc)[:180])

    registry=registry_bound["document"]; contract_schema=schema_bound["document"]
    contracts=registry.get("active_contracted_residuals")
    if not isinstance(contracts,Sequence) or isinstance(contracts,(str,bytes)) or not contracts:
        return _base(reason="REGISTRY_ACTIVE_CONTRACTS_INVALID")

    contract_by_id={}
    for i,c in enumerate(contracts):
        if not isinstance(c,Mapping): return _base(reason="REGISTRY_CONTRACT_INVALID",index=i)
        bid=c.get("behavior_id")
        if not isinstance(bid,str) or not bid or bid in contract_by_id:
            return _base(reason="REGISTRY_BEHAVIOR_ID_INVALID_OR_DUPLICATE",index=i)
        contract_by_id[bid]=c

    closures=payload.get("closures")
    if not isinstance(closures,Sequence) or isinstance(closures,(str,bytes)):
        return _base(reason="CLOSURES_INVALID")
    closure_by_id={}; field_errors=[]
    for i,row in enumerate(closures):
        if not isinstance(row,Mapping):
            field_errors.append(f"CLOSURE_NOT_OBJECT:{i}"); continue
        bid=row.get("behavior_id")
        if set(row)!=CLOSURE_FIELDS:
            field_errors.append(f"CLOSURE_FIELDS_INVALID:{bid or i}"); continue
        if not isinstance(bid,str) or not bid or bid in closure_by_id:
            field_errors.append(f"CLOSURE_BEHAVIOR_ID_INVALID_OR_DUPLICATE:{i}"); continue
        closure_by_id[bid]=row

    expected=set(contract_by_id); supplied=set(closure_by_id)
    missing=sorted(expected-supplied); extra=sorted(supplied-expected)
    if field_errors or missing or extra:
        return _base(reason="CONTRACT_CLOSURE_DOMAIN_MISMATCH",errors=sorted(field_errors),
                     open_behavior_ids=missing,extra_behavior_ids=extra,
                     authenticated_behavior_count=0,registry_behavior_count=len(expected),
                     registry_git_blob_sha=registry_bound["git_blob_sha"],
                     contract_schema_git_blob_sha=schema_bound["git_blob_sha"])

    errors=[]; authenticated=[]; details=[]
    for bid in sorted(expected):
        row=closure_by_id[bid]; contract=contract_by_id[bid]
        selected=row.get("selected_policy_id"); condition=row.get("policy_condition")
        if not isinstance(selected,str) or not selected:
            errors.append(f"SELECTED_POLICY_ID_INVALID:{bid}"); continue
        if not isinstance(condition,Mapping):
            errors.append(f"POLICY_CONDITION_INVALID:{bid}"); continue

        try: manifest_bound=_resolve(row.get("policy_manifest_ref"),root)
        except Exception:
            errors.append(f"POLICY_MANIFEST_BINDING_INVALID:{bid}"); continue
        manifest=manifest_bound["document"]
        structural=verify_policy_manifest(contract,contract_schema,manifest)
        if structural.get("pass") is not True:
            errors.append(f"POLICY_MANIFEST_STRUCTURAL_INCOMPLETE:{bid}")
            details.append({"behavior_id":bid,"structural_errors":structural.get("errors",[])})
            continue
        policies=manifest.get("policies") or []
        if selected not in {p.get("policy_id") for p in policies if isinstance(p,Mapping)}:
            errors.append(f"SELECTED_POLICY_NOT_IN_MANIFEST:{bid}"); continue

        extension=verify_abc_extension_admission(contract,row.get("abc_extension_atom_ids"))
        if extension.get("pass") is not True:
            errors.append(f"ABC_EXTENSION_ADMISSION_INCOMPLETE:{bid}")
            details.append({"behavior_id":bid,"extension_errors":extension.get("errors",[])})
            continue

        try: cert_bound=_resolve(row.get("adequacy_certificate_ref"),root)
        except Exception:
            errors.append(f"ADEQUACY_CERTIFICATE_BINDING_INVALID:{bid}"); continue
        cert=cert_bound["document"]
        if cert.get("schema")!=ADEQUACY_SCHEMA:
            errors.append(f"ADEQUACY_CERTIFICATE_SCHEMA_INVALID:{bid}"); continue
        if cert.get("policy_id")!=selected:
            errors.append(f"ADEQUACY_POLICY_ID_MISMATCH:{bid}"); continue
        if cert.get("policy_condition_sha256")!=_condition_sha256(condition):
            errors.append(f"ADEQUACY_CONDITION_MISMATCH:{bid}"); continue
        if cert.get("adequacy_proved") is not True:
            errors.append(f"ADEQUACY_NOT_PROVED:{bid}"); continue
        if cert.get("brain_owned") is not True:
            errors.append(f"POLICY_NOT_BRAIN_OWNED:{bid}"); continue
        if cert.get("load_bearing_constraints_preserved") is not True:
            errors.append(f"LOAD_BEARING_CONSTRAINTS_NOT_PRESERVED:{bid}"); continue

        try: verify_bound=_resolve(row.get("adequacy_verification_ref"),root)
        except Exception:
            errors.append(f"ADEQUACY_VERIFICATION_BINDING_INVALID:{bid}"); continue
        verification=verify_bound["document"]
        if verification.get("schema")!=VERIFY_SCHEMA:
            errors.append(f"ADEQUACY_VERIFICATION_SCHEMA_INVALID:{bid}"); continue
        if verification.get("policy_id")!=selected:
            errors.append(f"ADEQUACY_VERIFICATION_POLICY_ID_MISMATCH:{bid}"); continue
        if verification.get("subject_git_blob_sha")!=cert_bound["git_blob_sha"]:
            errors.append(f"ADEQUACY_VERIFICATION_SUBJECT_MISMATCH:{bid}"); continue
        if verification.get("pass") is not True:
            errors.append(f"ADEQUACY_INDEPENDENT_VERIFICATION_NOT_PASS:{bid}"); continue

        authenticated.append(bid)
        details.append({
            "behavior_id":bid,"selected_policy_id":selected,
            "policy_condition_sha256":_condition_sha256(condition),
            "policy_manifest_git_blob_sha":manifest_bound["git_blob_sha"],
            "adequacy_certificate_git_blob_sha":cert_bound["git_blob_sha"],
            "adequacy_verification_git_blob_sha":verify_bound["git_blob_sha"],
            "abc_extension_atom_count":len(row.get("abc_extension_atom_ids") or []),
        })

    open_ids=sorted(expected-set(authenticated))
    if errors:
        return _base(reason="ONE_OR_MORE_POLICY_EDGES_UNAUTHENTICATED",
                     errors=sorted(set(errors)),open_behavior_ids=open_ids,
                     authenticated_behavior_ids=sorted(authenticated),
                     authenticated_behavior_count=len(authenticated),
                     registry_behavior_count=len(expected),
                     registry_git_blob_sha=registry_bound["git_blob_sha"],
                     contract_schema_git_blob_sha=schema_bound["git_blob_sha"],
                     behavior_results=details)

    return {
        "schema":SCHEMA,"pass":True,
        "status":"PASS__ALL_BOUND_REGISTRY_BEHAVIORS_HAVE_AUTHENTICATED_POSITIVE_POLICY_EDGES",
        "registry_git_blob_sha":registry_bound["git_blob_sha"],
        "contract_schema_git_blob_sha":schema_bound["git_blob_sha"],
        "registry_behavior_count":len(expected),
        "authenticated_behavior_count":len(authenticated),
        "authenticated_behavior_ids":sorted(authenticated),"open_behavior_ids":[],
        "behavior_results":details,
        "all_current_registry_behavior_edges_authenticated":True,
        "scope_boundary":"EXACT_BOUND_BEHAVIORAL_REGISTRY_ONLY__UNIVERSAL_TARGET_TRACE_COVERAGE_AND_SELECTED_DISCRIMINATOR_TOTALITY_REMAIN_SEPARATE",
        "u_empty_authorized":False,"abc_closed_authorized":False,
        "terminal_authority":False,"terminal_credit_delta":0,
    }
